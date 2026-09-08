import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.sessions import UserSession
from app.models.users import User


# ============================================================================
# GET PROFILE TESTS (/users/profile)
# ============================================================================

def test_get_profile_success(client: TestClient, client_user: User, mock_supabase):
    """Test retrieving profile of authenticated user."""
    mock_supabase["public"]._current_mock_user_id = str(client_user.id)

    headers = {"Authorization": "Bearer mock_valid_token"}
    response = client.get("/users/profile", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(client_user.id)
    assert data["username"] == client_user.username
    assert data["email"] == client_user.email
    assert data["role"] == "CLIENT"


def test_get_profile_unauthenticated(client: TestClient):
    """Test retrieving profile without token returns 401."""
    response = client.get("/users/profile")
    assert response.status_code == 401


def test_get_profile_inactive_user(client: TestClient, inactive_user: User, mock_supabase):
    """Test inactive user cannot access profile endpoint."""
    mock_supabase["public"]._current_mock_user_id = str(inactive_user.id)

    headers = {"Authorization": "Bearer mock_valid_token"}
    response = client.get("/users/profile", headers=headers)

    assert response.status_code == 403
    data = response.json()
    assert "User account is inactive" in data["message"]


def test_get_profile_user_not_found(client: TestClient, mock_supabase):
    """Test token pointing to a user not present in DB returns 401."""
    mock_supabase["public"]._current_mock_user_id = str(uuid.uuid4())

    headers = {"Authorization": "Bearer mock_valid_token"}
    response = client.get("/users/profile", headers=headers)

    assert response.status_code == 401
    assert "User not found" in response.json()["message"]


# ============================================================================
# PUT PROFILE TESTS (/users/profile)
# ============================================================================

def test_update_profile_success(client: TestClient, client_user: User, db_session: Session, mock_supabase):
    """Test updating user profile with valid full name and phone number."""
    mock_supabase["public"]._current_mock_user_id = str(client_user.id)

    payload = {
        "first_name": "UpdatedFirst",
        "last_name": "UpdatedLast",
        "phone_number": "03001234567",
    }

    headers = {"Authorization": "Bearer mock_valid_token"}
    response = client.put("/users/profile", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["phone_number"] == "03001234567"

    # Verify DB updated
    db_session.refresh(client_user)
    assert client_user.phone_number == "03001234567"


@pytest.mark.parametrize(
    "phone,error_reason",
    [
        ("04001234567", "Does not start with 03"),
        ("0300123456", "Length is less than 11"),
        ("030012345678", "Length is more than 11"),
        ("0300123456a", "Contains non-digit character"),
    ],
)
def test_update_profile_invalid_phone_number(
    client: TestClient, client_user: User, mock_supabase, phone: str, error_reason: str
):
    """Test profile update fails with invalid Pakistani phone numbers."""
    mock_supabase["public"]._current_mock_user_id = str(client_user.id)

    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": phone,
    }

    headers = {"Authorization": "Bearer mock_valid_token"}
    response = client.put("/users/profile", json=payload, headers=headers)

    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False


def test_update_profile_empty_name(client: TestClient, client_user: User, mock_supabase):
    """Test profile update fails when first or last name is empty whitespace."""
    mock_supabase["public"]._current_mock_user_id = str(client_user.id)

    payload = {
        "first_name": "   ",
        "last_name": "Doe",
        "phone_number": "03001234567",
    }

    headers = {"Authorization": "Bearer mock_valid_token"}
    response = client.put("/users/profile", json=payload, headers=headers)

    assert response.status_code == 422


# ============================================================================
# PATCH PROFILE TESTS (/users/profile)
# ============================================================================

def test_patch_profile_phone_only(client: TestClient, client_user: User, db_session: Session, mock_supabase):
    """Test partial profile update changing phone number."""
    mock_supabase["public"]._current_mock_user_id = str(client_user.id)

    payload = {"phone_number": "03129876543"}

    headers = {"Authorization": "Bearer mock_valid_token"}
    response = client.patch("/users/profile", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["phone_number"] == "03129876543"

    db_session.refresh(client_user)
    assert client_user.phone_number == "03129876543"


def test_patch_profile_first_name_and_phone(client: TestClient, client_user: User, db_session: Session, mock_supabase):
    """Test partial profile update changing first_name alongside required phone_number."""
    mock_supabase["public"]._current_mock_user_id = str(client_user.id)

    payload = {"first_name": "NewFirst", "phone_number": "03001234567"}

    headers = {"Authorization": "Bearer mock_valid_token"}
    response = client.patch("/users/profile", json=payload, headers=headers)

    assert response.status_code == 200

    db_session.refresh(client_user)
    assert client_user.first_name == "NewFirst"
    assert "NewFirst" in client_user.name


# ============================================================================
# DELETE PROFILE TESTS (/users/profile)
# ============================================================================

def test_delete_account_success(client: TestClient, client_user: User, db_session: Session, mock_supabase):
    """Test deleting account removes user from DB and Supabase Auth."""
    mock_supabase["public"]._current_mock_user_id = str(client_user.id)
    user_id = client_user.id

    headers = {"Authorization": "Bearer mock_valid_token"}
    response = client.delete("/users/profile", headers=headers)

    assert response.status_code == 204

    # Verify user deleted from local DB
    db_user = db_session.query(User).filter(User.id == user_id).first()
    assert db_user is None
    # Verify Supabase delete_user called
    mock_supabase["admin"].delete_user.assert_called_with(str(user_id))


def test_delete_account_supabase_error_handled(
    client: TestClient, client_user: User, db_session: Session, mock_supabase
):
    """Test deleting account proceeds with DB deletion even if Supabase throws error."""
    mock_supabase["public"]._current_mock_user_id = str(client_user.id)
    mock_supabase["admin"].delete_user.side_effect = Exception("Supabase delete failed")
    user_id = client_user.id

    headers = {"Authorization": "Bearer mock_valid_token"}
    response = client.delete("/users/profile", headers=headers)

    assert response.status_code == 204
    db_user = db_session.query(User).filter(User.id == user_id).first()
    assert db_user is None


# ============================================================================
# SESSIONS ENDPOINT TESTS (/users/sessions)
# ============================================================================

def test_get_active_sessions(client: TestClient, client_user: User, db_session: Session, mock_supabase):
    """Test retrieving active sessions returns active sessions and filters out revoked ones."""
    mock_supabase["public"]._current_mock_user_id = str(client_user.id)

    active_1 = UserSession(
        user_id=client_user.id,
        refresh_token_hash="h1",
        device_name="Chrome Desktop",
        user_agent="Mozilla/5.0",
        ip_address="127.0.0.1",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    revoked_1 = UserSession(
        user_id=client_user.id,
        refresh_token_hash="h2",
        device_name="Firefox Mobile",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked_at=datetime.now(timezone.utc),
    )
    db_session.add_all([active_1, revoked_1])
    db_session.commit()

    headers = {"Authorization": "Bearer mock_valid_token"}
    response = client.get("/users/sessions", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total_active_sessions"] == 1
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["id"] == active_1.id
    assert data["sessions"][0]["device_name"] == "Chrome Desktop"
