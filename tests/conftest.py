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
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test_secret_key_for_jwt_testing_123456'
os.environ['ALGORITHM'] = 'HS256'
os.environ['ACCESS_TOKEN_EXPIRE_MINUTES'] = '30'
os.environ['REFRESH_TOKEN_EXPIRE_DAYS'] = '7'
os.environ['DEBUG'] = 'True'
os.environ['Test_DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SUPABASE_URL'] = 'https://mock.supabase.co'
os.environ['SUPABASE_KEY'] = 'mock-supabase-key'
os.environ['SUPABASE_SERVICE_KEY'] = 'mock-supabase-service-key'
os.environ['SUPABASE_JWT_SECRET'] = 'mock-jwt-secret'

class TestDatetime(datetime):

    @classmethod
    def now(cls, tz=None):
        return datetime.now(timezone.utc).replace(tzinfo=None)
import app.core.startup
with patch('app.core.startup.verify_supabase_connection', return_value=None):
    from app.database import Base, get_db
    from app.main import app
    from app.models.sessions import UserSession
    from app.models.users import User
SQLALCHEMY_DATABASE_URL = 'sqlite:///:memory:'
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope='session', autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session() -> Generator[Session, None, None]:
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
    with patch('app.services.auth.datetime', TestDatetime):
        yield

@pytest.fixture(autouse=True)
def mock_celery_tasks(request):
    if "test_send_notification_email_celery_task" in request.node.name:
        yield
    else:
        with patch('app.services.notification.send_notification_email.delay') as mock_delay:
            yield mock_delay

@pytest.fixture
def mock_supabase():
    mock_service = MagicMock()
    mock_pub = MagicMock()
    admin_mock = MagicMock()
    mock_service.auth.admin = admin_mock
    mock_create_res = MagicMock()
    mock_create_res.user.id = str(uuid.uuid4())
    admin_mock.create_user.return_value = mock_create_res
    admin_mock.delete_user.return_value = True
    mock_login_res = MagicMock()
    mock_login_res.session.access_token = 'mock_access_token_12345'
    mock_login_res.session.refresh_token = 'mock_refresh_token_12345'
    mock_login_res.user.id = str(uuid.uuid4())
    mock_service.auth.sign_in_with_password.return_value = mock_login_res
    mock_service.auth.sign_out.return_value = True
    mock_refresh_res = MagicMock()
    mock_refresh_res.session.access_token = 'mock_new_access_token_67890'
    mock_service.auth.refresh_session.return_value = mock_refresh_res

    def mock_get_user(token: str):
        if token == 'invalid_token':
            raise Exception('Invalid token')
        res = MagicMock()
        if hasattr(mock_pub, '_current_mock_user_id'):
            user_id = mock_pub._current_mock_user_id
        else:
            user_id = str(uuid.uuid4())
        res.user.id = user_id
        res.user.email = 'test@example.com'
        res.user.user_metadata = {}
        return res
    mock_pub.auth.get_user.side_effect = mock_get_user
    patches = [patch('app.core.supabase_client.supabase_service', mock_service), patch('app.core.supabase_client.supabase', mock_pub), patch('app.core.security.supabase', mock_pub), patch('app.services.auth.supabase_service', mock_service), patch('app.services.file_storage.supabase_service', mock_service), patch('app.routers.auth.supabase_service', mock_service), patch('app.routers.user.supabase_service', mock_service)]
    for p in patches:
        p.start()
    yield {'service': mock_service, 'public': mock_pub, 'admin': admin_mock}
    for p in patches:
        p.stop()

@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:

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
    user_id = uuid.uuid4()
    user = User(id=user_id, username='clientuser', name='Client User', first_name='Client', last_name='User', email='client@example.com', role='CLIENT', is_active=True, is_verified=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def freelancer_user(db_session: Session) -> User:
    user_id = uuid.uuid4()
    user = User(id=user_id, username='freelanceruser', name='Freelancer User', first_name='Freelancer', last_name='User', email='freelancer@example.com', role='FREELANCER', is_active=True, is_verified=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def inactive_user(db_session: Session) -> User:
    user_id = uuid.uuid4()
    user = User(id=user_id, username='inactiveuser', name='Inactive User', first_name='Inactive', last_name='User', email='inactive@example.com', role='CLIENT', is_active=False, is_verified=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
