from fastapi import APIRouter, Depends, HTTPException, Request, status , Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_db
from app.schemas.user import UserResponse, UserPatch, UserUpdate
from app.models.users import User
from app.dependencies.auth import get_current_user
from app.core.supabase_client import supabase_service
import logging
from datetime import datetime, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.sessions import UserSession
from app.core.cookie_utils import CookieManager
from app.core.errors import (
    ResourceNotFoundException,
    BusinessLogicException,
    ErrorCode,
    AuthorizationException
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])
security = HTTPBearer(auto_error=False)


@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    logger.info(f"Fetching profile for user: {current_user.id}")
    return current_user


@router.put("/profile", response_model=UserResponse )
def update_profile(updated_user: UserUpdate,current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    
    logger.info(f"Updating profile for user: {current_user.id}")
    
    try:
        current_user.first_name = updated_user.first_name
        current_user.last_name = updated_user.last_name
        current_user.phone_number = updated_user.phone_number
        
        current_user.name = f"{updated_user.first_name} {updated_user.last_name}"
        current_user.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(current_user)
        logger.info(f"Profile updated for user: {current_user.id}")
        return current_user
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Profile update failed: {str(e)}")
        raise BusinessLogicException(ErrorCode.INTERNAL_ERROR,"Failed to update profile")


@router.patch("/profile", response_model=UserResponse)
def patch_profile(patch_data: UserPatch,current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):

    logger.info(f"Patching profile for user: {current_user.id}")
    
    try:
        update_data = patch_data.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            setattr(current_user, key, value)
            
        if "first_name" in update_data or "last_name" in update_data:
            first = current_user.first_name or ""
            last = current_user.last_name or ""
            current_user.name = f"{first} {last}".strip()

        current_user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(current_user)
        logger.info(f"Profile patched for user: {current_user.id}")
        return current_user
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Profile patch failed: {str(e)}")
        raise BusinessLogicException(ErrorCode.INTERNAL_ERROR,"Failed to update profile")


@router.delete("/profile", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(    request: Request,response: Response,current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    
    logger.warning(f"User requesting account deletion: {current_user.id}")

    if not current_user:
        raise ResourceNotFoundException("User")

    try:
        user_id = current_user.id
        
        try:
            supabase_service.auth.admin.delete_user(str(user_id))
            logger.info(f"User deleted from Supabase Auth: {user_id}")
        except Exception as e:
            logger.warning(f"Failed to delete from Supabase Auth: {str(e)}")
        
        db.delete(current_user)
        db.commit()
        logger.warning(f"User account deleted from DB: {user_id}")

        CookieManager.clear_auth_cookies(response)
        logger.info(f"Auth cookies cleared for deleted user: {user_id}")
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"User deletion failed: {str(e)}")
        raise BusinessLogicException(ErrorCode.INTERNAL_ERROR,"Failed to delete account")
        
