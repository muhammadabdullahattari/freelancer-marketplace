import pytest
from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from app.core.security import get_token_from_header, get_user_id_from_token, hash_password, hash_token, verify_password
from app.dependencies.auth import get_current_client_user, get_current_freelancer_user, is_freelancer
from app.exceptions.handlers import general_exception_handler, http_exception_handler, validation_exception_handler
from app.models.users import User

def test_get_current_freelancer_user_success(freelancer_user: User):
    result = get_current_freelancer_user(current_user=freelancer_user)
    assert result == freelancer_user

def test_get_current_freelancer_user_forbidden(client_user: User):
    with pytest.raises(HTTPException) as exc_info:
        get_current_freelancer_user(current_user=client_user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert 'This action requires FREELANCER role' in exc_info.value.detail

def test_get_current_client_user_success(client_user: User):
    result = get_current_client_user(current_user=client_user)
    assert result == client_user

def test_get_current_client_user_forbidden(freelancer_user: User):
    with pytest.raises(HTTPException) as exc_info:
        get_current_client_user(current_user=freelancer_user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert 'This action requires CLIENT role' in exc_info.value.detail

def test_is_freelancer_success(freelancer_user: User):
    result = is_freelancer(current_user=freelancer_user)
    assert result == freelancer_user

def test_is_freelancer_forbidden(client_user: User):
    with pytest.raises(HTTPException) as exc_info:
        is_freelancer(current_user=client_user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert 'Not authorized for this action' in exc_info.value.detail

@pytest.mark.asyncio
async def test_http_exception_handler():
    exc = HTTPException(status_code=404, detail='Resource not found')
    response = await http_exception_handler(request=None, exc=exc)
    assert response.status_code == 404
    body = response.body.decode()
    assert '"success":false' in body
    assert '"status_code":404' in body
    assert '"message":"Resource not found"' in body

@pytest.mark.asyncio
async def test_validation_exception_handler():
    exc = RequestValidationError(errors=[{'loc': ['body', 'email'], 'msg': 'field required', 'type': 'value_error'}])
    response = await validation_exception_handler(request=None, exc=exc)
    assert response.status_code == 422
    body = response.body.decode()
    assert '"success":false' in body
    assert '"status_code":422' in body
    assert '"message":"Validation failed"' in body
    assert '"errors":' in body

@pytest.mark.asyncio
async def test_general_exception_handler():
    exc = Exception('Unexpected error')
    response = await general_exception_handler(request=None, exc=exc)
    assert response.status_code == 500
    body = response.body.decode()
    assert '"success":false' in body
    assert '"status_code":500' in body
    assert '"message":"Internal Server Error"' in body

def test_password_hashing_and_verification():
    raw_pass = 'MySecretPass123!'
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password('WrongPassword123!', hashed) is False

def test_hash_token():
    token = 'some_token_string'
    hashed = hash_token(token)
    assert isinstance(hashed, str)
    assert len(hashed) == 64
    assert hash_token(token) == hashed

def test_get_token_from_header_valid():
    auth_header = 'Bearer my_secret_token_123'
    token = get_token_from_header(auth_header)
    assert token == 'my_secret_token_123'

@pytest.mark.parametrize('header,expected_detail', [(None, 'Missing authorization header'), ('', 'Missing authorization header'), ('Basic xyz123', 'Invalid authorization header format'), ('Bearer', 'Invalid authorization header format'), ('Bearer token1 token2', 'Invalid authorization header format')])
def test_get_token_from_header_invalid(header: str | None, expected_detail: str):
    with pytest.raises(HTTPException) as exc_info:
        get_token_from_header(header)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert expected_detail in exc_info.value.detail
