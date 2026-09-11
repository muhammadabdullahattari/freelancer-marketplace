import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.security import hash_token
from app.models.sessions import UserSession
from app.models.users import User

def _utc_now():
    return datetime.now(timezone.utc)

def test_signup_success_client(client: TestClient, db_session: Session, mock_supabase):
    supabase_id = str(uuid.uuid4())
    mock_supabase['admin'].create_user.return_value.user.id = supabase_id
    payload = {'first_name': 'John', 'last_name': 'Doe', 'username': 'johndoe', 'email': 'john.doe@example.com', 'password': 'Password123!', 'role': 'CLIENT'}
    response = client.post('/auth/signup', json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data['email'] == 'john.doe@example.com'
    assert data['username'] == 'johndoe'
    assert data['role'] == 'CLIENT'
    assert data['id'] == supabase_id
    assert data['is_active'] is True
    assert data['is_verified'] is True
    db_user = db_session.query(User).filter(User.username == 'johndoe').first()
    assert db_user is not None
    assert db_user.email == 'john.doe@example.com'

def test_signup_success_freelancer(client: TestClient, db_session: Session, mock_supabase):
    supabase_id = str(uuid.uuid4())
    mock_supabase['admin'].create_user.return_value.user.id = supabase_id
    payload = {'first_name': 'Jane', 'last_name': 'Smith', 'username': 'janesmith', 'email': 'jane.smith@example.com', 'password': 'SecurePass123$', 'role': 'FREELANCER'}
    response = client.post('/auth/signup', json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data['role'] == 'FREELANCER'
    assert data['username'] == 'janesmith'

def test_signup_duplicate_email(client: TestClient, client_user: User, mock_supabase):
    payload = {'first_name': 'Duplicate', 'last_name': 'Email', 'username': 'uniqueuser', 'email': client_user.email, 'password': 'Password123!', 'role': 'CLIENT'}
    response = client.post('/auth/signup', json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data['success'] is False
    assert 'Email already registered' in data['message']

def test_signup_duplicate_username(client: TestClient, client_user: User, mock_supabase):
    payload = {'first_name': 'Duplicate', 'last_name': 'Username', 'username': client_user.username, 'email': 'newemail@example.com', 'password': 'Password123!', 'role': 'CLIENT'}
    response = client.post('/auth/signup', json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data['success'] is False
    assert 'Username is already taken' in data['message']

@pytest.mark.parametrize('field,value,error_substr', [('email', 'not-an-email', 'Validation failed'), ('password', 'short1!', 'Password must be at least 8 characters long'), ('password', 'nodigitshere!', 'Password must contain at least one number'), ('password', '12345678!', 'Password must contain at least one letter'), ('password', 'NoSpecial1234', 'Password must contain at least one special character'), ('role', 'INVALID_ROLE', "Input should be 'CLIENT' or 'FREELANCER'"), ('username', 'user@invalid', 'Username can contain only letters, numbers and underscores'), ('first_name', ' ', 'Name cannot be empty')])
def test_signup_validation_edge_cases(client: TestClient, field: str, value: str, error_substr: str):
    payload = {'first_name': 'Test', 'last_name': 'User', 'username': 'valid_user', 'email': 'valid@example.com', 'password': 'Password123!', 'role': 'CLIENT'}
    payload[field] = value
    response = client.post('/auth/signup', json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data['success'] is False
    assert data['status_code'] == 422

def test_signup_supabase_auth_failure(client: TestClient, mock_supabase):
    mock_supabase['admin'].create_user.side_effect = Exception('Supabase Auth Error')
    payload = {'first_name': 'Supa', 'last_name': 'Fail', 'username': 'supafail', 'email': 'supafail@example.com', 'password': 'Password123!', 'role': 'CLIENT'}
    response = client.post('/auth/signup', json=payload)
    assert response.status_code == 500
    data = response.json()
    assert 'Failed to create user in authentication service' in data['message']

def test_signup_local_db_failure_cleans_up_supabase(client: TestClient, mock_supabase):
    supabase_id = str(uuid.uuid4())
    mock_supabase['admin'].create_user.return_value.user.id = supabase_id
    with pytest.MonkeyPatch.context() as m:

        def mock_add_error(*args, **kwargs):
            raise SQLAlchemyError('DB connection dropped')
        m.setattr(Session, 'add', mock_add_error)
        payload = {'first_name': 'DB', 'last_name': 'Fail', 'username': 'dbfailuser', 'email': 'dbfail@example.com', 'password': 'Password123!', 'role': 'CLIENT'}
        response = client.post('/auth/signup', json=payload)
        assert response.status_code == 500
        mock_supabase['admin'].delete_user.assert_called_with(supabase_id)

def test_login_success(client: TestClient, client_user: User, db_session: Session, mock_supabase):
    mock_supabase['service'].auth.sign_in_with_password.return_value.user.id = client_user.id
    mock_supabase['service'].auth.sign_in_with_password.return_value.session.access_token = 'valid_access_token'
    mock_supabase['service'].auth.sign_in_with_password.return_value.session.refresh_token = 'valid_refresh_token'
    payload = {'email': client_user.email, 'password': 'Password123!'}
    response = client.post('/auth/login', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['access_token'] == 'valid_access_token'
    assert data['refresh_token'] == 'valid_refresh_token'
    assert data['token_type'] == 'bearer'
    session = db_session.query(UserSession).filter(UserSession.user_id == client_user.id).first()
    assert session is not None
    assert session.refresh_token_hash == hash_token('valid_refresh_token')

def test_login_invalid_credentials(client: TestClient, mock_supabase):
    mock_supabase['service'].auth.sign_in_with_password.side_effect = Exception('Invalid login')
    payload = {'email': 'nonexistent@example.com', 'password': 'WrongPassword123!'}
    response = client.post('/auth/login', json=payload)
    assert response.status_code == 401
    data = response.json()
    assert 'Invalid credentials' in data['message']

def test_login_user_not_found_in_local_db(client: TestClient, mock_supabase):
    non_existent_id = uuid.uuid4()
    mock_supabase['service'].auth.sign_in_with_password.return_value.user.id = non_existent_id
    payload = {'email': 'orphan@example.com', 'password': 'Password123!'}
    response = client.post('/auth/login', json=payload)
    assert response.status_code == 401
    data = response.json()
    assert 'User profile not found' in data['message']

def test_login_inactive_user(client: TestClient, inactive_user: User, mock_supabase):
    mock_supabase['service'].auth.sign_in_with_password.return_value.user.id = inactive_user.id
    payload = {'email': inactive_user.email, 'password': 'Password123!'}
    response = client.post('/auth/login', json=payload)
    assert response.status_code == 403
    data = response.json()
    assert 'User account is inactive' in data['message']

def test_logout_success(client: TestClient, client_user: User, db_session: Session, mock_supabase):
    mock_supabase['public']._current_mock_user_id = str(client_user.id)
    active_session = UserSession(user_id=client_user.id, refresh_token_hash='hash_123', expires_at=_utc_now() + timedelta(days=7))
    db_session.add(active_session)
    db_session.commit()
    headers = {'Authorization': 'Bearer mock_valid_token'}
    response = client.post('/auth/logout', headers=headers)
    assert response.status_code == 204
    db_session.refresh(active_session)
    assert active_session.revoked_at is not None

def test_logout_unauthenticated(client: TestClient):
    response = client.post('/auth/logout')
    assert response.status_code == 401

def test_logout_supabase_signout_warning_tolerant(client: TestClient, client_user: User, db_session: Session, mock_supabase):
    mock_supabase['public']._current_mock_user_id = str(client_user.id)
    mock_supabase['service'].auth.sign_out.side_effect = Exception('Supabase network error')
    headers = {'Authorization': 'Bearer mock_valid_token'}
    response = client.post('/auth/logout', headers=headers)
    assert response.status_code == 204

def test_logout_all_devices_success(client: TestClient, client_user: User, db_session: Session, mock_supabase):
    mock_supabase['public']._current_mock_user_id = str(client_user.id)
    s1 = UserSession(user_id=client_user.id, refresh_token_hash='hash_1', expires_at=_utc_now() + timedelta(days=7))
    s2 = UserSession(user_id=client_user.id, refresh_token_hash='hash_2', expires_at=_utc_now() + timedelta(days=7))
    db_session.add_all([s1, s2])
    db_session.commit()
    headers = {'Authorization': 'Bearer mock_valid_token'}
    response = client.post('/auth/logout-all-devices', headers=headers)
    assert response.status_code == 204
    db_session.refresh(s1)
    db_session.refresh(s2)
    assert s1.revoked_at is not None
    assert s2.revoked_at is not None

def test_refresh_token_success(client: TestClient, client_user: User, db_session: Session, mock_supabase):
    raw_refresh = 'valid_refresh_token_xyz'
    session = UserSession(user_id=client_user.id, refresh_token_hash=hash_token(raw_refresh), expires_at=_utc_now() + timedelta(days=7))
    db_session.add(session)
    db_session.commit()
    mock_supabase['service'].auth.refresh_session.return_value.session.access_token = 'new_access_token_abc'
    headers = {'Authorization': f'Bearer {raw_refresh}'}
    response = client.post('/auth/refresh', headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data['access_token'] == 'new_access_token_abc'
    assert data['token_type'] == 'bearer'

def test_refresh_token_missing_header(client: TestClient):
    response = client.post('/auth/refresh')
    assert response.status_code == 401

def test_refresh_token_unknown(client: TestClient):
    headers = {'Authorization': 'Bearer unknown_refresh_token'}
    response = client.post('/auth/refresh', headers=headers)
    assert response.status_code == 401
    assert 'Unknown refresh token' in response.json()['message']

def test_refresh_token_revoked(client: TestClient, client_user: User, db_session: Session):
    raw_refresh = 'revoked_token_123'
    session = UserSession(user_id=client_user.id, refresh_token_hash=hash_token(raw_refresh), expires_at=_utc_now() + timedelta(days=7), revoked_at=_utc_now())
    db_session.add(session)
    db_session.commit()
    headers = {'Authorization': f'Bearer {raw_refresh}'}
    response = client.post('/auth/refresh', headers=headers)
    assert response.status_code == 401
    assert 'Refresh token has been revoked' in response.json()['message']

def test_refresh_token_expired(client: TestClient, client_user: User, db_session: Session):
    raw_refresh = 'expired_token_123'
    session = UserSession(user_id=client_user.id, refresh_token_hash=hash_token(raw_refresh), expires_at=_utc_now() - timedelta(days=1))
    db_session.add(session)
    db_session.commit()
    headers = {'Authorization': f'Bearer {raw_refresh}'}
    response = client.post('/auth/refresh', headers=headers)
    assert response.status_code == 401
    assert 'Refresh token expired' in response.json()['message']

def test_refresh_token_supabase_failure(client: TestClient, client_user: User, db_session: Session, mock_supabase):
    raw_refresh = 'valid_in_db_but_supa_fails'
    session = UserSession(user_id=client_user.id, refresh_token_hash=hash_token(raw_refresh), expires_at=_utc_now() + timedelta(days=7))
    db_session.add(session)
    db_session.commit()
    mock_supabase['service'].auth.refresh_session.side_effect = Exception('Supabase refresh error')
    headers = {'Authorization': f'Bearer {raw_refresh}'}
    response = client.post('/auth/refresh', headers=headers)
    assert response.status_code == 401
    assert 'Failed to refresh token' in response.json()['message']
