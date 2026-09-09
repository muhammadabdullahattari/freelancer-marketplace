from fastapi import APIRouter, Depends, HTTPException, Request, status , Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_db
from app.schemas.user import UserResponse, UserPatch, UserUpdate
from app.schemas.auth import UserCreate, UserLogin, Token, Refresh_Token
from app.services.auth import create_user, authenticate_user ,refresh_access_token
from app.models.users import User
from app.dependencies.auth import get_current_user
from app.core.security import get_token_from_header
from app.core.supabase_client import supabase_service
import logging
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.sessions import UserSession
from datetime import datetime, timezone
from app.core.cookie_utils import CookieManager
from app.core.errors import APIException, AuthenticationException, AuthorizationException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"New user signup: {user.email}")
    return create_user(db, user)

@router.post("/login", response_model=Token)
def login(user_data: UserLogin, request: Request, response : Response ,db: Session = Depends(get_db)):
    
    logger.info(f"User login attempt: {user_data.email}")
    auth_response = authenticate_user(user_data, request, db)
    
    CookieManager.set_access_token_cookie(response, auth_response["access_token"])
    CookieManager.set_refresh_token_cookie(response, auth_response["refresh_token"])
    
    logger.info(f"User logged in successfully: {auth_response['user_id']}")
    
    return auth_response
    
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request,response: Response,current_user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    
    logger.info(f"User logout: {current_user.id}")
    credentials = request.headers.get("authorization")
    access_token = None

    if credentials and credentials.startswith("Bearer "):
        access_token = credentials[7:]
    else:
        access_token = CookieManager.get_access_token_from_cookies(request)

    if not access_token:
        CookieManager.clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Missing access token")

    try:
        supabase_service.auth.admin.sign_out(access_token, scope="local")
        logger.info(f"User signed out from Supabase: {current_user.id}")
    except Exception as e:
        logger.warning(f"Supabase sign_out failed (non-critical): {str(e)}")

    try:
        current_session = db.query(UserSession).filter(UserSession.user_id == current_user.id,
            UserSession.revoked_at == None).order_by(UserSession.created_at.desc()).first()

        if current_session:
            current_session.revoked_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Session revoked for user: {current_user.id}, session_id: {current_session.id}")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to revoke session: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to logout")

    CookieManager.clear_auth_cookies(response)
    logger.info(f"Auth cookies cleared for user: {current_user.id}")


@router.post("/logout-all-devices", status_code=status.HTTP_204_NO_CONTENT)
def logout_all_devices(request: Request,response: Response,
                       current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    
    logger.info(f"User logout all devices: {current_user.id}")
    credentials = request.headers.get("authorization")
    access_token = None

    if credentials and credentials.startswith("Bearer "):
        access_token = credentials[7:]
    else:
        access_token = CookieManager.get_access_token_from_cookies(request)

    if not access_token:
        CookieManager.clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Missing access token")

    try:
        supabase_service.auth.admin.sign_out(access_token, scope="global")
        logger.info(f"User signed out from Supabase: {current_user.id}")
    except Exception as e:
        logger.warning(f"Supabase sign_out failed (non-critical): {str(e)}")

    try:
        active_sessions = db.query(UserSession).filter(UserSession.user_id == current_user.id,UserSession.revoked_at == None).all()

        if active_sessions:
            now = datetime.now(timezone.utc)
            
            for session in active_sessions:
                session.revoked_at = now

            db.commit()
            logger.info(f"All {len(active_sessions)} sessions revoked for user: {current_user.id}")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to revoke all sessions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to logout from all devices")

    CookieManager.clear_auth_cookies(response)
    logger.info(f"Auth cookies cleared for user: {current_user.id}")


@router.post("/refresh", response_model=Refresh_Token)
def refresh(request: Request,response: Response,credentials: HTTPAuthorizationCredentials = Depends(security),
                  db: Session = Depends(get_db)):
    
    logger.info("Token refresh attempt")
    refresh_token = None
    
    if credentials:
        refresh_token = credentials.credentials
    else:
        refresh_token = CookieManager.get_refresh_token_from_cookies(request)

    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Missing refresh token")

    result = refresh_access_token(refresh_token, db)
    CookieManager.set_access_token_cookie(response, result["access_token"])
    logger.info("Token refreshed successfully")

    return result