import uuid
import pytest
from fastapi.testclient import TestClient
from app.models.users import User
from app.models.freelancer_profile import FreelancerProfile

def test_create_freelancer_profile_success(client: TestClient, freelancer_user: User, mock_supabase):
    mock_supabase['public']._current_mock_user_id = str(freelancer_user.id)
    headers = {'Authorization': 'Bearer mock_freelancer_token'}
    payload = {'bio': 'Senior Full Stack Engineer with 7 years of Python and React experience.', 'title': 'Senior Python Developer', 'hourly_rate': 65.0, 'years_experience': 7, 'is_available': True}
    response = client.post('/freelancer/profile', json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data['title'] == payload['title']
    assert data['user_id'] == str(freelancer_user.id)

def test_create_freelancer_profile_forbidden_client(client: TestClient, client_user: User, mock_supabase):
    mock_supabase['public']._current_mock_user_id = str(client_user.id)
    headers = {'Authorization': 'Bearer mock_client_token'}
    payload = {'title': 'Invalid Freelancer Title', 'hourly_rate': 50.0}
    response = client.post('/freelancer/profile', json=payload, headers=headers)
    assert response.status_code == 403

def test_get_freelancer_profile_success(client: TestClient, freelancer_user: User, mock_supabase):
    mock_supabase['public']._current_mock_user_id = str(freelancer_user.id)
    headers = {'Authorization': 'Bearer mock_freelancer_token'}
    client.post('/freelancer/profile', json={'title': 'DevOps Engineer', 'hourly_rate': 80.0}, headers=headers)
    res = client.get('/freelancer/profile', headers=headers)
    assert res.status_code == 200
    assert res.json()['title'] == 'DevOps Engineer'

def test_duplicate_freelancer_profile_creation_conflict(client: TestClient, freelancer_user: User, mock_supabase):
    mock_supabase['public']._current_mock_user_id = str(freelancer_user.id)
    headers = {'Authorization': 'Bearer mock_freelancer_token'}
    client.post('/freelancer/profile', json={'title': 'Initial Profile'}, headers=headers)
    res = client.post('/freelancer/profile', json={'title': 'Duplicate Profile Attempt'}, headers=headers)
    assert res.status_code in [409, 400, 500]
