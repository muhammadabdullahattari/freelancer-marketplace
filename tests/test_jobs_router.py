import uuid
import pytest
from fastapi.testclient import TestClient
from app.models.users import User
from app.models.job import Job, JobStatus

def test_create_job_success_client(client: TestClient, client_user: User, mock_supabase):
    mock_supabase['public']._current_mock_user_id = str(client_user.id)
    headers = {'Authorization': 'Bearer mock_client_token'}
    payload = {'title': 'Build a Full-Stack E-Commerce Platform', 'description': 'We need an experienced developer to build a modern e-commerce web application with FastAPI and React.', 'budget_type': 'FIXED', 'budget_min': 1000.0, 'budget_max': 2500.0, 'duration_estimate': '1 to 3 months', 'experience_level': 'INTERMEDIATE', 'skill_ids': []}
    response = client.post('/jobs/', json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data['title'] == payload['title']
    assert data['status'] == 'DRAFT'
    assert data['client_id'] == str(client_user.id)

def test_create_job_forbidden_freelancer(client: TestClient, freelancer_user: User, mock_supabase):
    mock_supabase['public']._current_mock_user_id = str(freelancer_user.id)
    headers = {'Authorization': 'Bearer mock_freelancer_token'}
    payload = {'title': 'Invalid Job Creation Request', 'description': 'Freelancers are not permitted to post job listings on the marketplace platform.', 'budget_type': 'FIXED', 'budget_max': 500.0}
    response = client.post('/jobs/', json=payload, headers=headers)
    assert response.status_code == 403
    err_text = str(response.json().get('detail') or response.json().get('message') or '')
    assert 'FREELANCER' in err_text or 'Forbidden' in err_text or 'CLIENT' in err_text or ('client' in err_text.lower())

def test_get_job_by_id(client: TestClient, client_user: User, mock_supabase):
    mock_supabase['public']._current_mock_user_id = str(client_user.id)
    headers = {'Authorization': 'Bearer mock_client_token'}
    payload = {'title': 'Python Backend API Development', 'description': 'Looking for a Python developer to create clean RESTful endpoints.', 'budget_type': 'HOURLY'}
    create_res = client.post('/jobs/', json=payload, headers=headers)
    job_id = create_res.json()['id']
    get_res = client.get(f'/jobs/{job_id}')
    assert get_res.status_code == 200
    assert get_res.json()['id'] == job_id

def test_update_publish_close_delete_job_flow(client: TestClient, client_user: User, mock_supabase):
    mock_supabase['public']._current_mock_user_id = str(client_user.id)
    headers = {'Authorization': 'Bearer mock_client_token'}
    create_res = client.post('/jobs/', json={'title': 'Draft Job Title Initial', 'description': 'Initial description with more than twenty characters long required for validation.', 'budget_max': 1000.0}, headers=headers)
    job_id = create_res.json()['id']
    update_res = client.patch(f'/jobs/{job_id}', json={'title': 'Updated Job Title Value'}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()['title'] == 'Updated Job Title Value'
    pub_res = client.post(f'/jobs/{job_id}/publish', headers=headers)
    assert pub_res.status_code == 200
    assert pub_res.json()['status'] == 'OPEN'
    close_res = client.post(f'/jobs/{job_id}/close', headers=headers)
    assert close_res.status_code == 200
    assert close_res.json()['status'] == 'CLOSED'

def test_list_jobs_with_filters(client: TestClient, client_user: User, mock_supabase):
    mock_supabase['public']._current_mock_user_id = str(client_user.id)
    headers = {'Authorization': 'Bearer mock_client_token'}
    for i in range(2):
        res = client.post('/jobs/', json={'title': f'Searchable Job Listing {i + 1}', 'description': f'Detailed job listing description number {i + 1} for test execution.', 'budget_max': 500.0 + i * 100}, headers=headers)
        j_id = res.json()['id']
        client.post(f'/jobs/{j_id}/publish', headers=headers)
    list_res = client.get('/jobs/?skip=0&limit=10')
    assert list_res.status_code == 200
    data = list_res.json()
    assert 'items' in data
    assert data['total'] >= 2
