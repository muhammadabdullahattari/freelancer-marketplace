import uuid
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.file_config import FileType
from app.models.contract import Contract, ContractStatus
from app.models.file_upload import FileUpload
from app.models.freelancer_profile import FreelancerProfile
from app.models.job import Job, JobStatus
from app.models.milestone import Milestone
from app.models.proposal import Proposal, ProposalStatus
from app.models.users import User


@pytest.fixture(autouse=True)
def setup_storage_mocks(mock_supabase):
    storage_mock = MagicMock()
    storage_mock.upload.return_value = {'path': 'mock_path'}
    storage_mock.get_public_url.return_value = 'https://mock.supabase.co/storage/v1/object/public/test.jpg'
    storage_mock.create_signed_url.return_value = {'signedURL': 'https://mock.supabase.co/storage/v1/object/sign/test.pdf?token=123'}
    storage_mock.remove.return_value = True
    mock_supabase['service'].storage.from_.return_value = storage_mock
    with patch('app.services.file_storage.supabase_service', mock_supabase['service']):
        yield


def get_auth_headers(user: User, mock_supabase) -> dict:
    mock_supabase['public']._current_mock_user_id = str(user.id)
    return {'Authorization': f'Bearer mock_token_{user.id}'}


def test_proposal_attachments_requires_auth(client: TestClient):
    """Unauthenticated users cannot list proposal attachments"""
    proposal_id = uuid.uuid4()
    response = client.get(f"/uploads/proposal/{proposal_id}/attachments")
    assert response.status_code == 401


def test_proposal_attachments_auth_check_freelancer(client: TestClient, db_session: Session, client_user: User, freelancer_user: User, mock_supabase):
    """Freelancer NOT on proposal cannot list attachments"""
    freelancer2 = User(id=uuid.uuid4(), email="freelancer2@test.com", username="freelancer2", name="Freelancer 2", role="FREELANCER", is_active=True)
    db_session.add(freelancer2)
    
    job = Job(id=uuid.uuid4(), client_id=client_user.id, title="Test Job", description="Test", status=JobStatus.OPEN)
    db_session.add(job)
    
    freelancer1_profile = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id)
    db_session.add(freelancer1_profile)
    db_session.commit()
    
    proposal = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer1_profile.id, cover_letter="Test", proposed_rate=100.0, status=ProposalStatus.SUBMITTED)
    db_session.add(proposal)
    db_session.commit()
    
    headers = get_auth_headers(freelancer2, mock_supabase)
    response = client.get(f"/uploads/proposal/{proposal.id}/attachments", headers=headers)
    
    assert response.status_code == 403


def test_list_attachments_no_storage_url_returned(client: TestClient, db_session: Session, client_user: User, freelancer_user: User, mock_supabase):
    """List endpoints should NOT return storage_url or url"""
    job = Job(id=uuid.uuid4(), client_id=client_user.id, title="Test Job", description="Test", status=JobStatus.OPEN)
    db_session.add(job)
    
    freelancer_profile = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id)
    db_session.add(freelancer_profile)
    db_session.commit()
    
    proposal = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_profile.id, cover_letter="Test", proposed_rate=100.0, status=ProposalStatus.SUBMITTED)
    db_session.add(proposal)
    db_session.commit()
    
    file = FileUpload(
        id=uuid.uuid4(),
        filename="test_doc.pdf",
        original_filename="document.pdf",
        file_type="proposal_attachment",
        mime_type="application/pdf",
        file_size_bytes=1000,
        storage_bucket="test-bucket",
        storage_path="test/path.pdf",
        storage_url="https://signed-url-that-should-not-be-returned",
        uploaded_by_user_id=freelancer_user.id,
        is_public=False,
        proposal_id=proposal.id
    )
    db_session.add(file)
    db_session.commit()
    
    headers = get_auth_headers(client_user, mock_supabase)
    response = client.get(f"/uploads/proposal/{proposal.id}/attachments", headers=headers)
    
    assert response.status_code == 200
    attachments = response.json()
    assert len(attachments) > 0
    for attachment in attachments:
        assert "url" not in attachment
        assert "storage_url" not in attachment
        assert "download_url" not in attachment


def test_download_file_generates_fresh_url(client: TestClient, db_session: Session, freelancer_user: User, mock_supabase):
    """Download endpoint should generate fresh URL"""
    file = FileUpload(
        id=uuid.uuid4(),
        filename="private.pdf",
        original_filename="private.pdf",
        file_type="profile_picture",
        mime_type="application/pdf",
        file_size_bytes=1000,
        storage_bucket="bucket",
        storage_path="path.pdf",
        storage_url="old-signed-url-from-db",
        uploaded_by_user_id=freelancer_user.id,
        is_public=False,
        user_id=freelancer_user.id
    )
    db_session.add(file)
    db_session.commit()
    
    headers = get_auth_headers(freelancer_user, mock_supabase)
    response = client.get(f"/uploads/file/{file.id}/download", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "download_url" in data


def test_upload_filename_sanitization(client: TestClient, db_session: Session, freelancer_user: User, client_user: User, mock_supabase):
    """Filenames with ../ are sanitized"""
    freelancer_profile = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id)
    db_session.add(freelancer_profile)
    job = Job(id=uuid.uuid4(), client_id=client_user.id, title="Test Job", description="Test", status=JobStatus.OPEN)
    db_session.add(job)
    proposal = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_profile.id, cover_letter="Test", proposed_rate=100.0, status=ProposalStatus.SUBMITTED)
    db_session.add(proposal)
    db_session.commit()

    headers = get_auth_headers(freelancer_user, mock_supabase)
    file_content = b"test"
    files = {"file": ("../../etc/passwd.pdf", BytesIO(file_content), "application/pdf")}
    
    response = client.post(f"/uploads/proposal/{proposal.id}/attachment", headers=headers, files=files)
    
    assert response.status_code == 201
    file_data = response.json()
    assert ".." not in file_data.get("filename", "")


def test_contract_file_access_control(client: TestClient, db_session: Session, client_user: User, freelancer_user: User, mock_supabase):
    """User unrelated to contract cannot access files"""
    unrelated_user = User(id=uuid.uuid4(), email="unrelated@test.com", username="unrelated", name="Unrelated", role="CLIENT", is_active=True)
    db_session.add(unrelated_user)
    
    job = Job(id=uuid.uuid4(), client_id=client_user.id, title="Job", description="Test", status=JobStatus.OPEN)
    db_session.add(job)
    
    freelancer_profile = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id)
    db_session.add(freelancer_profile)
    
    proposal = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_profile.id, cover_letter="Test", proposed_rate=100.0, status=ProposalStatus.SUBMITTED)
    db_session.add(proposal)
    
    contract = Contract(id=uuid.uuid4(), job_id=job.id, proposal_id=proposal.id, client_id=client_user.id, freelancer_id=freelancer_profile.id, title="Contract", total_amount=100.0, status=ContractStatus.ACTIVE)
    db_session.add(contract)
    db_session.commit()
    
    file = FileUpload(
        id=uuid.uuid4(), filename="contract.pdf", original_filename="contract.pdf",
        file_type="contract_document", mime_type="application/pdf", file_size_bytes=1000,
        storage_bucket="bucket", storage_path="path.pdf", storage_url="url",
        uploaded_by_user_id=client_user.id, is_public=False, contract_id=contract.id
    )
    db_session.add(file)
    db_session.commit()
    
    headers = get_auth_headers(unrelated_user, mock_supabase)
    response = client.get(f"/uploads/file/{file.id}/download", headers=headers)
    
    assert response.status_code == 403


def test_contract_file_delete_authorization(client: TestClient, db_session: Session, client_user: User, freelancer_user: User, mock_supabase):
    """Only contract parties can delete contract files"""
    unrelated = User(id=uuid.uuid4(), email="unrelated_del@test.com", username="unrelated_del", name="Unrelated Del", role="CLIENT", is_active=True)
    db_session.add(unrelated)
    
    job = Job(id=uuid.uuid4(), client_id=client_user.id, title="Job", description="Test", status=JobStatus.OPEN)
    db_session.add(job)
    
    freelancer_profile = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id)
    db_session.add(freelancer_profile)
    
    proposal = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_profile.id, cover_letter="Test", proposed_rate=100.0, status=ProposalStatus.SUBMITTED)
    db_session.add(proposal)
    
    contract = Contract(id=uuid.uuid4(), job_id=job.id, proposal_id=proposal.id, client_id=client_user.id, freelancer_id=freelancer_profile.id, title="Contract", total_amount=100.0, status=ContractStatus.ACTIVE)
    db_session.add(contract)
    db_session.commit()
    
    file = FileUpload(
        id=uuid.uuid4(), filename="contract.pdf", original_filename="contract.pdf",
        file_type="contract_document", mime_type="application/pdf", file_size_bytes=1000,
        storage_bucket="bucket", storage_path="path.pdf", storage_url="url",
        uploaded_by_user_id=client_user.id, is_public=False, contract_id=contract.id
    )
    db_session.add(file)
    db_session.commit()
    
    # Unrelated user tries to delete
    headers_u = get_auth_headers(unrelated, mock_supabase)
    response = client.delete(f"/uploads/contract/document/{file.id}", headers=headers_u)
    assert response.status_code == 403
    
    # Client CAN delete
    headers_c = get_auth_headers(client_user, mock_supabase)
    response = client.delete(f"/uploads/contract/document/{file.id}", headers=headers_c)
    assert response.status_code == 204
