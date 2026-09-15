import uuid
import pytest
from fastapi.testclient import TestClient
from app.models.users import User

def get_auth_headers(user: User, mock_supabase) -> dict:
    mock_supabase['public']._current_mock_user_id = str(user.id)
    return {'Authorization': f'Bearer mock_token_{user.id}'}

def test_create_job_missing_required_fields(client: TestClient, client_user: User, mock_supabase):
    headers = get_auth_headers(client_user, mock_supabase)
    res = client.post('/jobs/', headers=headers, json={})
    assert res.status_code == 422

def test_list_jobs_invalid_pagination_params(client: TestClient):
    res = client.get('/jobs/?skip=-5&limit=10')
    assert res.status_code == 422

def test_list_jobs_limit_exceeds_max(client: TestClient):
    res = client.get('/jobs/?skip=0&limit=500')
    assert res.status_code == 422

def test_uploads_invalid_uuid_returns_422(client: TestClient, freelancer_user: User, mock_supabase):
    headers = get_auth_headers(freelancer_user, mock_supabase)
    files = {'file': ('doc.pdf', b'pdf content', 'application/pdf')}
    res_post = client.post('/uploads/proposal/2222/attachment', headers=headers, files=files)
    assert res_post.status_code == 422
    res_get = client.get('/uploads/profile-picture/2222', headers=headers)
    assert res_get.status_code == 422

def test_resource_not_found_exception_format(client: TestClient):
    fake_uuid = str(uuid.uuid4())
    res = client.get(f'/jobs/{fake_uuid}')
    assert res.status_code == 404
    data = res.json()
    assert 'error' in data or 'message' in data or 'detail' in data

def test_unauthenticated_request_returns_401(client: TestClient):
    res = client.post('/jobs/', json={'title': 'Test Job'})
    assert res.status_code == 401
