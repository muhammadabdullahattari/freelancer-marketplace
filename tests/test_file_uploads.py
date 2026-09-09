import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.users import User
from app.models.freelancer_profile import FreelancerProfile
from app.models.job import Job
from app.models.proposal import Proposal
from app.models.contract import Contract, ContractStatus
from app.models.milestone import Milestone, MilestoneStatus
from app.models.file_upload import FileUpload
from app.core.file_config import FileType


@pytest.fixture(autouse=True)
def setup_storage_mocks(mock_supabase):
    """Setup mock Supabase storage methods across all file upload tests."""
    storage_mock = MagicMock()
    storage_mock.upload.return_value = {"path": "mock_path"}
    storage_mock.get_public_url.return_value = "https://mock.supabase.co/storage/v1/object/public/test.jpg"
    storage_mock.create_signed_url.return_value = {"signedURL": "https://mock.supabase.co/storage/v1/object/sign/test.pdf?token=123"}
    storage_mock.remove.return_value = True

    mock_supabase["service"].storage.from_.return_value = storage_mock

    with patch("app.services.file_storage.supabase_service", mock_supabase["service"]):
        yield


# Helper headers
def get_auth_headers(user: User, mock_supabase) -> dict:
    mock_supabase["public"]._current_mock_user_id = str(user.id)
    return {"Authorization": f"Bearer mock_token_{user.id}"}


# ==========================================
# 1. PROFILE PICTURE ENDPOINTS
# ==========================================

def test_upload_profile_picture_success(client: TestClient, freelancer_user: User, mock_supabase):
    """Test uploading a valid JPEG profile picture succeeds (201 Created)."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("avatar.jpg", b"fake jpeg image content", "image/jpeg")}

    res = client.post("/api/v1/uploads/profile-picture", headers=headers, files=files)
    assert res.status_code == 201
    data = res.json()
    assert data["filename"] == "avatar.jpg"
    assert data["file_size_bytes"] == len(b"fake jpeg image content")
    assert "url" in data


def test_upload_profile_picture_invalid_mime_type(client: TestClient, freelancer_user: User, mock_supabase):
    """Test uploading an invalid MIME type for profile picture returns 400 Bad Request."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("document.pdf", b"fake pdf content", "application/pdf")}

    res = client.post("/api/v1/uploads/profile-picture", headers=headers, files=files)
    assert res.status_code == 400
    assert "not allowed for profile_picture" in res.json()["error"]["message"]


def test_upload_profile_picture_exceeds_max_size(client: TestClient, freelancer_user: User, mock_supabase):
    """Test uploading a file exceeding 5MB max size limit returns 400 Bad Request."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    # 5MB + 10 bytes
    large_content = b"0" * (5 * 1024 * 1024 + 10)
    files = {"file": ("huge_avatar.png", large_content, "image/png")}

    res = client.post("/api/v1/uploads/profile-picture", headers=headers, files=files)
    assert res.status_code == 400
    assert "exceeds maximum 5MB" in res.json()["error"]["message"]


def test_upload_profile_picture_unauthenticated(client: TestClient):
    """Test uploading profile picture without auth header returns 401 Unauthorized."""
    files = {"file": ("avatar.jpg", b"content", "image/jpeg")}
    res = client.post("/api/v1/uploads/profile-picture", files=files)
    assert res.status_code == 401


def test_upload_profile_picture_missing_file(client: TestClient, freelancer_user: User, mock_supabase):
    """Test uploading profile picture without file body returns 422 Unprocessable Entity."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    res = client.post("/api/v1/uploads/profile-picture", headers=headers)
    assert res.status_code == 422


def test_get_profile_picture_success(client: TestClient, freelancer_user: User, mock_supabase):
    """Test retrieving existing profile picture returns 200 OK."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("avatar.jpg", b"fake image content", "image/jpeg")}
    client.post("/api/v1/uploads/profile-picture", headers=headers, files=files)

    res = client.get(f"/api/v1/uploads/profile-picture/{freelancer_user.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "avatar.jpg"


def test_get_profile_picture_not_found(client: TestClient):
    """Test retrieving profile picture for user without one returns 404 Not Found."""
    random_user_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/uploads/profile-picture/{random_user_id}")
    assert res.status_code == 404


def test_delete_profile_picture_success(client: TestClient, freelancer_user: User, mock_supabase):
    """Test owner deleting profile picture returns 204 No Content."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("avatar.jpg", b"fake content", "image/jpeg")}
    upload_res = client.post("/api/v1/uploads/profile-picture", headers=headers, files=files)
    file_id = upload_res.json()["id"]

    del_res = client.delete(f"/api/v1/uploads/profile-picture/{file_id}", headers=headers)
    assert del_res.status_code == 204


def test_delete_profile_picture_unauthorized_user(client: TestClient, client_user: User, freelancer_user: User, mock_supabase):
    """Test non-owner attempting to delete another user's profile picture returns 404 Not Found."""
    headers_f = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("avatar.jpg", b"fake content", "image/jpeg")}
    upload_res = client.post("/api/v1/uploads/profile-picture", headers=headers_f, files=files)
    file_id = upload_res.json()["id"]

    headers_c = get_auth_headers(client_user, mock_supabase)
    del_res = client.delete(f"/api/v1/uploads/profile-picture/{file_id}", headers=headers_c)
    assert del_res.status_code == 404


# ==========================================
# 2. PROPOSAL ATTACHMENT ENDPOINTS
# ==========================================

@pytest.fixture
def sample_proposal(db_session: Session, client_user: User, freelancer_user: User) -> Proposal:
    freelancer_prof = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id, title="Python Dev")
    db_session.add(freelancer_prof)
    job = Job(id=uuid.uuid4(), client_id=client_user.id, title="Backend Dev", description="Build API endpoints")
    db_session.add(job)
    proposal = Proposal(
        id=uuid.uuid4(),
        job_id=job.id,
        freelancer_id=freelancer_prof.id,
        cover_letter="Cover letter text",
        proposed_rate=500.0,
    )
    db_session.add(proposal)
    db_session.commit()
    return proposal


def test_upload_proposal_attachment_success(client: TestClient, freelancer_user: User, sample_proposal: Proposal, mock_supabase):
    """Test assigned freelancer uploading valid PDF proposal attachment succeeds (201 Created)."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("resume.pdf", b"%PDF-1.4 mock pdf content", "application/pdf")}

    res = client.post(f"/api/v1/uploads/proposal/{sample_proposal.id}/attachment", headers=headers, files=files)
    assert res.status_code == 201
    data = res.json()
    assert data["original_filename"] == "resume.pdf"
    assert data["mime_type"] == "application/pdf"


def test_upload_proposal_attachment_unauthorized_user(client: TestClient, client_user: User, sample_proposal: Proposal, mock_supabase):
    """Test client or unassigned user uploading attachment to someone else's proposal returns 403 Forbidden."""
    headers = get_auth_headers(client_user, mock_supabase)
    files = {"file": ("resume.pdf", b"%PDF-1.4 content", "application/pdf")}

    res = client.post(f"/api/v1/uploads/proposal/{sample_proposal.id}/attachment", headers=headers, files=files)
    assert res.status_code == 403
    assert "You can only upload attachments to your own proposals" in res.json()["error"]["message"]


def test_upload_proposal_attachment_invalid_mime_type(client: TestClient, freelancer_user: User, sample_proposal: Proposal, mock_supabase):
    """Test uploading disallowed MIME type for proposal attachment returns 400 Bad Request."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("video.mp4", b"fake mp4 video bytes", "video/mp4")}

    res = client.post(f"/api/v1/uploads/proposal/{sample_proposal.id}/attachment", headers=headers, files=files)
    assert res.status_code == 400
    assert "not allowed for proposal_attachment" in res.json()["error"]["message"]


def test_upload_proposal_attachment_not_found(client: TestClient, freelancer_user: User, mock_supabase):
    """Test uploading attachment to non-existent proposal ID returns 404 Not Found."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    fake_id = str(uuid.uuid4())
    files = {"file": ("doc.pdf", b"pdf content", "application/pdf")}

    res = client.post(f"/api/v1/uploads/proposal/{fake_id}/attachment", headers=headers, files=files)
    assert res.status_code == 404


def test_get_proposal_attachments_success(client: TestClient, freelancer_user: User, sample_proposal: Proposal, mock_supabase):
    """Test getting attachments for proposal returns list (200 OK)."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("doc.pdf", b"pdf content", "application/pdf")}
    client.post(f"/api/v1/uploads/proposal/{sample_proposal.id}/attachment", headers=headers, files=files)

    res = client.get(f"/api/v1/uploads/proposal/{sample_proposal.id}/attachments", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["original_filename"] == "doc.pdf"


def test_delete_proposal_attachment_success(client: TestClient, freelancer_user: User, sample_proposal: Proposal, mock_supabase):
    """Test deleting proposal attachment by uploader returns 204 No Content."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("doc.pdf", b"pdf content", "application/pdf")}
    upload_res = client.post(f"/api/v1/uploads/proposal/{sample_proposal.id}/attachment", headers=headers, files=files)
    file_id = upload_res.json()["id"]

    del_res = client.delete(f"/api/v1/uploads/proposal/attachment/{file_id}", headers=headers)
    assert del_res.status_code == 204


def test_delete_proposal_attachment_unauthorized_user(client: TestClient, client_user: User, freelancer_user: User, sample_proposal: Proposal, mock_supabase):
    """Test non-uploader attempting to delete another user's proposal attachment returns 404 Not Found."""
    headers_f = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("doc.pdf", b"pdf content", "application/pdf")}
    upload_res = client.post(f"/api/v1/uploads/proposal/{sample_proposal.id}/attachment", headers=headers_f, files=files)
    file_id = upload_res.json()["id"]

    headers_c = get_auth_headers(client_user, mock_supabase)
    del_res = client.delete(f"/api/v1/uploads/proposal/attachment/{file_id}", headers=headers_c)
    assert del_res.status_code == 404


# ==========================================
# 3. CONTRACT DOCUMENT ENDPOINTS
# ==========================================

@pytest.fixture
def sample_contract(db_session: Session, client_user: User, freelancer_user: User, sample_proposal: Proposal) -> Contract:
    contract = Contract(
        id=uuid.uuid4(),
        job_id=sample_proposal.job_id,
        proposal_id=sample_proposal.id,
        client_id=client_user.id,
        freelancer_id=sample_proposal.freelancer_id,
        title="Full Stack Contract",
        total_amount=1000.0,
        status=ContractStatus.IN_PROGRESS,
    )
    db_session.add(contract)
    db_session.commit()
    return contract


def test_upload_contract_document_by_client_success(client: TestClient, client_user: User, sample_contract: Contract, mock_supabase):
    """Test client uploading PDF contract document succeeds (201 Created)."""
    headers = get_auth_headers(client_user, mock_supabase)
    files = {"file": ("contract_v1.pdf", b"%PDF contract", "application/pdf")}

    res = client.post(f"/api/v1/uploads/contract/{sample_contract.id}/document", headers=headers, files=files)
    assert res.status_code == 201
    assert res.json()["original_filename"] == "contract_v1.pdf"


def test_upload_contract_document_by_freelancer_success(client: TestClient, freelancer_user: User, sample_contract: Contract, mock_supabase):
    """Test assigned freelancer uploading docx contract document succeeds (201 Created)."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("contract_signed.docx", b"docx bytes", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

    res = client.post(f"/api/v1/uploads/contract/{sample_contract.id}/document", headers=headers, files=files)
    assert res.status_code == 201
    assert res.json()["original_filename"] == "contract_signed.docx"


def test_upload_contract_document_unassigned_user_denied(client: TestClient, db_session: Session, sample_contract: Contract, mock_supabase):
    """Test unassigned user uploading contract document returns 403 Forbidden."""
    unassigned_user = User(
        id=uuid.uuid4(),
        email="unassigned_contract_user@example.com",
        username="unassigned_contract_user",
        name="Unassigned User",
        role="CLIENT",
        is_active=True,
    )
    db_session.add(unassigned_user)
    db_session.commit()

    headers = get_auth_headers(unassigned_user, mock_supabase)
    files = {"file": ("contract_doc.pdf", b"%PDF contract", "application/pdf")}

    res = client.post(f"/api/v1/uploads/contract/{sample_contract.id}/document", headers=headers, files=files)
    assert res.status_code == 403
    assert "not authorized to upload documents for this contract" in res.json()["error"]["message"]


def test_upload_contract_document_invalid_mime_type(client: TestClient, client_user: User, sample_contract: Contract, mock_supabase):
    """Test uploading invalid MIME type for contract document returns 400 Bad Request."""
    headers = get_auth_headers(client_user, mock_supabase)
    files = {"file": ("archive.zip", b"zip data", "application/zip")}

    res = client.post(f"/api/v1/uploads/contract/{sample_contract.id}/document", headers=headers, files=files)
    assert res.status_code == 400
    assert "not allowed for contract_document" in res.json()["error"]["message"]


def test_get_contract_documents_success(client: TestClient, client_user: User, sample_contract: Contract, mock_supabase):
    """Test getting documents for contract returns document list (200 OK)."""
    headers = get_auth_headers(client_user, mock_supabase)
    files = {"file": ("doc.pdf", b"pdf content", "application/pdf")}
    client.post(f"/api/v1/uploads/contract/{sample_contract.id}/document", headers=headers, files=files)

    res = client.get(f"/api/v1/uploads/contract/{sample_contract.id}/documents", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["original_filename"] == "doc.pdf"


# ==========================================
# 4. MILESTONE DELIVERABLE ENDPOINTS
# ==========================================

@pytest.fixture
def sample_milestone(db_session: Session, sample_contract: Contract) -> Milestone:
    milestone = Milestone(
        id=uuid.uuid4(),
        contract_id=sample_contract.id,
        title="Phase 1 MVP",
        amount=500.0,
        status=MilestoneStatus.PENDING,
    )
    db_session.add(milestone)
    db_session.commit()
    return milestone


def test_upload_milestone_deliverable_success(client: TestClient, freelancer_user: User, sample_milestone: Milestone, mock_supabase):
    """Test assigned freelancer uploading zip deliverable succeeds (201 Created)."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("deliverable.zip", b"PK zip file content", "application/zip")}

    res = client.post(f"/api/v1/uploads/milestone/{sample_milestone.id}/deliverable", headers=headers, files=files)
    assert res.status_code == 201
    assert res.json()["original_filename"] == "deliverable.zip"


def test_upload_milestone_deliverable_client_denied(client: TestClient, client_user: User, sample_milestone: Milestone, mock_supabase):
    """Test client attempting to upload milestone deliverable returns 403 Forbidden."""
    headers = get_auth_headers(client_user, mock_supabase)
    files = {"file": ("deliverable.zip", b"PK zip file content", "application/zip")}

    res = client.post(f"/api/v1/uploads/milestone/{sample_milestone.id}/deliverable", headers=headers, files=files)
    assert res.status_code == 403
    assert "Only the freelancer can upload deliverables for this milestone" in res.json()["error"]["message"]


def test_upload_milestone_deliverable_unassigned_freelancer_denied(client: TestClient, db_session: Session, sample_milestone: Milestone, mock_supabase):
    """Test unassigned freelancer attempting to upload deliverable returns 403 Forbidden."""
    other_freelancer = User(
        id=uuid.uuid4(),
        email="other_freelancer_deliv@example.com",
        username="other_freelancer_deliv",
        name="Other Freelancer",
        role="FREELANCER",
        is_active=True,
    )
    other_prof = FreelancerProfile(id=uuid.uuid4(), user_id=other_freelancer.id, title="Unassigned Freelancer")
    db_session.add_all([other_freelancer, other_prof])
    db_session.commit()

    headers = get_auth_headers(other_freelancer, mock_supabase)
    files = {"file": ("deliverable.zip", b"PK zip file content", "application/zip")}

    res = client.post(f"/api/v1/uploads/milestone/{sample_milestone.id}/deliverable", headers=headers, files=files)
    assert res.status_code == 403


def test_get_milestone_deliverables_success(client: TestClient, freelancer_user: User, sample_milestone: Milestone, mock_supabase):
    """Test getting deliverables for milestone returns deliverable list (200 OK)."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("deliverable.zip", b"PK zip file content", "application/zip")}
    client.post(f"/api/v1/uploads/milestone/{sample_milestone.id}/deliverable", headers=headers, files=files)

    res = client.get(f"/api/v1/uploads/milestone/{sample_milestone.id}/deliverables", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["original_filename"] == "deliverable.zip"


# ==========================================
# 5. FILE DOWNLOAD PERMISSION ENDPOINTS
# ==========================================

def test_download_file_owner_success(client: TestClient, freelancer_user: User, sample_proposal: Proposal, mock_supabase):
    """Test file uploader can access private file download URL (200 OK)."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("doc.pdf", b"pdf content", "application/pdf")}
    upload_res = client.post(f"/api/v1/uploads/proposal/{sample_proposal.id}/attachment", headers=headers, files=files)
    file_id = upload_res.json()["id"]

    res = client.get(f"/api/v1/uploads/file/{file_id}/download", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "download_url" in data


def test_download_file_proposal_job_client_success(client: TestClient, client_user: User, freelancer_user: User, sample_proposal: Proposal, mock_supabase):
    """Test job client can access proposal attachment download URL (200 OK)."""
    headers_f = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("proposal_doc.pdf", b"pdf content", "application/pdf")}
    upload_res = client.post(f"/api/v1/uploads/proposal/{sample_proposal.id}/attachment", headers=headers_f, files=files)
    file_id = upload_res.json()["id"]

    headers_c = get_auth_headers(client_user, mock_supabase)
    res = client.get(f"/api/v1/uploads/file/{file_id}/download", headers=headers_c)
    assert res.status_code == 200
    assert "download_url" in res.json()


def test_download_file_unauthorized_user_denied(client: TestClient, db_session: Session, freelancer_user: User, sample_proposal: Proposal, mock_supabase):
    """Test third-party unauthorized user attempting to download private file returns 403 Forbidden."""
    headers_f = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("secret.pdf", b"pdf content", "application/pdf")}
    upload_res = client.post(f"/api/v1/uploads/proposal/{sample_proposal.id}/attachment", headers=headers_f, files=files)
    file_id = upload_res.json()["id"]

    unauthorized_user = User(
        id=uuid.uuid4(),
        email="unauthorized_downloader@example.com",
        username="unauthorized_downloader",
        name="Unauthorized User",
        role="CLIENT",
        is_active=True,
    )
    db_session.add(unauthorized_user)
    db_session.commit()

    headers_u = get_auth_headers(unauthorized_user, mock_supabase)
    res = client.get(f"/api/v1/uploads/file/{file_id}/download", headers=headers_u)
    assert res.status_code == 403
    assert "You are not authorized to access this file" in res.json()["error"]["message"]


def test_download_file_not_found(client: TestClient, freelancer_user: User, mock_supabase):
    """Test requesting download link for non-existent file ID returns 404 Not Found."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    fake_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/uploads/file/{fake_id}/download", headers=headers)
    assert res.status_code == 404


def test_invalid_uuid_format_handling(client: TestClient, freelancer_user: User, mock_supabase):
    """Test sending non-UUID string '2222' across endpoints returns 422 Unprocessable Entity instead of 500 Internal Server Error."""
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {"file": ("doc.pdf", b"pdf content", "application/pdf")}

    endpoints_post = [
        "/api/v1/uploads/proposal/2222/attachment",
        "/api/v1/uploads/contract/2222/document",
        "/api/v1/uploads/milestone/2222/deliverable",
    ]
    for url in endpoints_post:
        res = client.post(url, headers=headers, files=files)
        assert res.status_code == 422, f"Expected 422 for {url}, got {res.status_code}"

    endpoints_get = [
        "/api/v1/uploads/profile-picture/2222",
        "/api/v1/uploads/proposal/2222/attachments",
        "/api/v1/uploads/contract/2222/documents",
        "/api/v1/uploads/milestone/2222/deliverables",
        "/api/v1/uploads/file/2222/download",
    ]
    for url in endpoints_get:
        res = client.get(url, headers=headers)
        assert res.status_code == 422, f"Expected 422 for {url}, got {res.status_code}"
