import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Add project root directory to sys.path so app modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Set up test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test_secret_key_for_jwt_testing_123456"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
os.environ["DEBUG"] = "True"
os.environ["Test_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_KEY"] = "mock-supabase-key"
os.environ["SUPABASE_SERVICE_KEY"] = "mock-supabase-service-key"
os.environ["SUPABASE_JWT_SECRET"] = "mock-jwt-secret"


class TestDatetime(datetime):
    """Custom datetime subclass for tests that returns offset-naive UTC datetimes from now()."""

    @classmethod
    def now(cls, tz=None):
        return datetime.now(timezone.utc).replace(tzinfo=None)



# Mock startup event to avoid external Supabase connection during startup
with patch("app.core.startup.verify_supabase_connection", return_value=None):
    from app.database import Base, get_db
    from app.main import app
    from app.models.sessions import UserSession
    from app.models.users import User

# Create in-memory SQLite engine
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once for the test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a clean transactional database session for each test function."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def patch_auth_datetime():
    """Autouse fixture to patch app.services.auth.datetime with TestDatetime."""
    with patch("app.services.auth.datetime", TestDatetime):
        yield


@pytest.fixture
def mock_supabase():
    """Mock Supabase Auth clients across all services, routers, and security modules."""
    mock_service = MagicMock()
    mock_pub = MagicMock()

    # Set up default mock behavior for supabase_service.auth.admin
    admin_mock = MagicMock()
    mock_service.auth.admin = admin_mock

    # Set up default user response for admin.create_user
    mock_create_res = MagicMock()
    mock_create_res.user.id = str(uuid.uuid4())
    admin_mock.create_user.return_value = mock_create_res
    admin_mock.delete_user.return_value = True

    # Sign in mock response
    mock_login_res = MagicMock()
    mock_login_res.session.access_token = "mock_access_token_12345"
    mock_login_res.session.refresh_token = "mock_refresh_token_12345"
    mock_login_res.user.id = str(uuid.uuid4())
    mock_service.auth.sign_in_with_password.return_value = mock_login_res
    mock_service.auth.sign_out.return_value = True

    # Refresh session mock response
    mock_refresh_res = MagicMock()
    mock_refresh_res.session.access_token = "mock_new_access_token_67890"
    mock_service.auth.refresh_session.return_value = mock_refresh_res

    # Security verify token mock
    def mock_get_user(token: str):
        if token == "invalid_token":
            raise Exception("Invalid token")
        res = MagicMock()
        if hasattr(mock_pub, "_current_mock_user_id"):
            user_id = mock_pub._current_mock_user_id
        else:
            user_id = str(uuid.uuid4())
        res.user.id = user_id
        res.user.email = "test@example.com"
        res.user.user_metadata = {}
        return res

    mock_pub.auth.get_user.side_effect = mock_get_user

    # Apply patches across all locations where supabase or supabase_service are used
    patches = [
        patch("app.core.supabase_client.supabase_service", mock_service),
        patch("app.core.supabase_client.supabase", mock_pub),
        patch("app.core.security.supabase", mock_pub),
        patch("app.services.auth.supabase_service", mock_service),
        patch("app.routers.auth.supabase_service", mock_service),
        patch("app.routers.user.supabase_service", mock_service),
    ]

    for p in patches:
        p.start()

    yield {
        "service": mock_service,
        "public": mock_pub,
        "admin": admin_mock,
    }

    for p in patches:
        p.stop()



@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db dependency."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_user(db_session: Session) -> User:
    """Create a sample CLIENT user in the test DB."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        username="clientuser",
        name="Client User",
        first_name="Client",
        last_name="User",
        email="client@example.com",
        role="CLIENT",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def freelancer_user(db_session: Session) -> User:
    """Create a sample FREELANCER user in the test DB."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        username="freelanceruser",
        name="Freelancer User",
        first_name="Freelancer",
        last_name="User",
        email="freelancer@example.com",
        role="FREELANCER",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_user(db_session: Session) -> User:
    """Create an inactive user in the test DB."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        username="inactiveuser",
        name="Inactive User",
        first_name="Inactive",
        last_name="User",
        email="inactive@example.com",
        role="CLIENT",
        is_active=False,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
