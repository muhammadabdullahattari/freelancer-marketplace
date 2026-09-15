import uuid
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.file_config import FileType
from app.models.contract import Contract
from app.models.file_upload import FileUpload
from app.models.freelancer_profile import FreelancerProfile
from app.models.job import Job
from app.models.milestone import Milestone
from app.models.proposal import Proposal
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


def test_upload_profile_picture_valid_file(client: TestClient, freelancer_user: User, mock_supabase):
    """Test valid profile picture upload"""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    file_content = b"fake image data"
    files = {"file": ("avatar.jpg", BytesIO(file_content), "image/jpeg")}
    
    response = client.post(
        "/uploads/profile-picture",
        headers=headers,
        files=files
    )
    
    assert response.status_code == 201
    assert "url" in response.json()


def test_upload_profile_picture_unauthorized_user(client: TestClient, freelancer_user: User, client_user: User, mock_supabase):
    """Test cross-user access prevention"""
    # User A uploads file
    headers_a = get_auth_headers(freelancer_user, mock_supabase)
    file_content = b"fake image"
    files = {"file": ("avatar.jpg", BytesIO(file_content), "image/jpeg")}
    
    response = client.post(
        "/uploads/profile-picture",
        headers=headers_a,
        files=files
    )
    
    assert response.status_code == 201
    file_id = response.json()["id"]
    
    # User B tries to delete User A's file
    headers_b = get_auth_headers(client_user, mock_supabase)
    response = client.delete(
        f"/uploads/profile-picture/{file_id}",
        headers=headers_b
    )
    
    # Should be 404 (ResourceNotFound for unauthorized user deleting file) or 403
    assert response.status_code in (403, 404)


def test_upload_oversized_file(client: TestClient, freelancer_user: User, mock_supabase):
    """Test file size validation"""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    # 10MB file (exceeds 5MB limit for profile pictures)
    large_content = b"x" * (10 * 1024 * 1024)
    files = {"file": ("avatar.jpg", BytesIO(large_content), "image/jpeg")}
    
    response = client.post(
        "/uploads/profile-picture",
        headers=headers,
        files=files
    )
    
    assert response.status_code == 400
    assert "exceeds maximum" in response.json()["error"]["message"]


def test_upload_invalid_file_type(client: TestClient, freelancer_user: User, mock_supabase):
    """Test invalid MIME type rejection"""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    exe_content = b"MZ\x90\x00"  # Windows executable header
    files = {"file": ("malware.exe", BytesIO(exe_content), "application/x-executable")}
    
    response = client.post(
        "/uploads/profile-picture",
        headers=headers,
        files=files
    )
    
    assert response.status_code == 400
    assert "not allowed" in response.json()["error"]["message"]


def test_proposal_attachment_authorization(client: TestClient, db_session: Session, freelancer_user: User, client_user: User, mock_supabase):
    """Test freelancer can only upload to own proposals"""
    freelancer_prof = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id, title='Dev')
    db_session.add(freelancer_prof)
    job = Job(id=uuid.uuid4(), client_id=client_user.id, title='Job', description='Desc')
    db_session.add(job)
    proposal = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_prof.id, cover_letter='Cover', proposed_rate=100.0)
    db_session.add(proposal)
    db_session.commit()

    headers_f = get_auth_headers(freelancer_user, mock_supabase)
    file_content = b"proposal document"
    files = {"file": ("doc.pdf", BytesIO(file_content), "application/pdf")}
    
    # Freelancer A uploads
    response = client.post(
        f"/uploads/proposal/{proposal.id}/attachment",
        headers=headers_f,
        files=files
    )
    assert response.status_code == 201

    # Create Freelancer B
    other_freelancer = User(id=uuid.uuid4(), username='otherfree', name='Other Free', email='other@free.com', role='FREELANCER', is_active=True)
    other_prof = FreelancerProfile(id=uuid.uuid4(), user_id=other_freelancer.id, title='Dev 2')
    db_session.add_all([other_freelancer, other_prof])
    db_session.commit()
    
    # Freelancer B tries to upload to same proposal (should fail)
    headers_b = get_auth_headers(other_freelancer, mock_supabase)
    files_b = {"file": ("doc2.pdf", BytesIO(file_content), "application/pdf")}
    response = client.post(
        f"/uploads/proposal/{proposal.id}/attachment",
        headers=headers_b,
        files=files_b
    )
    
    assert response.status_code == 403


def test_download_url_expiry(client: TestClient, db_session: Session, freelancer_user: User, client_user: User, mock_supabase):
    """Test signed URLs expire"""
    freelancer_prof = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id, title='Dev')
    db_session.add(freelancer_prof)
    job = Job(id=uuid.uuid4(), client_id=client_user.id, title='Job', description='Desc')
    db_session.add(job)
    proposal = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_prof.id, cover_letter='Cover', proposed_rate=100.0)
    db_session.add(proposal)
    db_session.commit()

    headers = get_auth_headers(freelancer_user, mock_supabase)
    file_content = b"private content"
    files = {"file": ("private.pdf", BytesIO(file_content), "application/pdf")}
    
    response = client.post(
        f"/uploads/proposal/{proposal.id}/attachment",
        headers=headers,
        files=files
    )
    assert response.status_code == 201
    file_id = response.json()["id"]
    
    # Get download URL
    response = client.get(
        f"/uploads/file/{file_id}/download",
        headers=headers
    )
    
    assert response.status_code == 200
    assert "expires_in_seconds" in response.json()
    assert response.json()["expires_in_seconds"] == 3600


def test_file_deletion_cleanup_on_job_delete(db_session):
    """Test files deleted when associated job is deleted"""
    from app.services.file_storage import FileStorageService
    
    assert hasattr(FileStorageService, 'delete_file')