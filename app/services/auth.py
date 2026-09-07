from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.users import User
from app.schemas.auth import UserCreate, UserLogin
from app.core.security import hash_password, verify_password , hash_token
from app.core.supabase_client import supabase_service
from app.models.sessions import UserSession
from fastapi import HTTPException, status, Request
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

def create_user(db: Session, user_data: UserCreate):
    
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    
    if existing_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="Email already registered")
    
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    
    if existing_username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="Username is already taken")
    
    
    try:
        auth_response = supabase_service.auth.admin.create_user({
            "email":user_data.email,
            "password":user_data.password,
            "email_confirm":True,
            "user_metadata":{
                "username": user_data.username,
                "name": f"{user_data.first_name} {user_data.last_name}"}})
        
        supabase_user_id = auth_response.user.id
        logger.info(f"User created in Supabase Auth: {supabase_user_id}")
        
    except Exception as e:
        logger.error(f"Supabase Auth creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user in authentication service"
        )
    
    
    user = User(
        id=UUID(supabase_user_id),
        username=user_data.username,
        name=f"{user_data.first_name} {user_data.last_name}",
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        role=user_data.role,  
        is_active=True,
        is_verified=True,
        email_verified_at=None
    )
    
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"User created in local DB: {user.id}")
        return user
        
    except SQLAlchemyError as e:
        db.rollback()
        try:
            supabase_service.auth.admin.delete_user(supabase_user_id)
            logger.info(
            f"Supabase user deleted after local DB failure:{supabase_user_id}")
        except Exception as delete_error:
            logger.error(f"CRITICAL: Could not delete Supabase user {supabase_user_id}: {delete_error}")
        
        logger.error(f"Local DB creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user profile"
        )


def authenticate_user(user_data: UserLogin, request: Request, db: Session):
    
    try:
        auth_response = supabase_service.auth.sign_in_with_password({
            "email":user_data.email,
            "password":user_data.password
        })
        
        if not auth_response or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        access_token = auth_response.session.access_token
        refresh_token = auth_response.session.refresh_token
        user_id = auth_response.user.id
        
        logger.info(f"User authenticated: {user_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.warning(f"User not found in local DB after successful auth: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User profile not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DB lookup failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )
    
    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        session = UserSession(
            user_id=user.id,
            refresh_token_hash= hash_token(refresh_token),  
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=refresh_expires_at
        )
        
        db.add(session)
        db.commit()
        logger.info(f"Session created for user: {user.id}")
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.warning(f"Session creation failed (non-critical): {str(e)}")
    
    try:
        user.last_login_at = datetime.now(timezone.utc)
        user.last_login_ip = ip_address
        db.commit()
    except:
        db.rollback()
        logger.warning("Failed to update last_login info")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
    
def refresh_access_token(old_refresh_token: str, db: Session) -> dict:

    session = db.query(UserSession).filter(UserSession.refresh_token_hash == hash_token(old_refresh_token)).first()

    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown refresh token")

    if session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")

    if session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    try:
        response = supabase_service.auth.refresh_session(old_refresh_token)

        if not response or not response.session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

        logger.info(f"Access token refreshed for user: {session.user_id}")

        return {"access_token": response.session.access_token,"token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to refresh token")