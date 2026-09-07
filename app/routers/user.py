from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_db
from app.schemas.user import UserResponse, UserPatch, UserUpdate
from app.models.users import User
from app.dependencies.auth import get_current_user
from app.core.supabase_client import supabase_service
import logging
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.sessions import UserSession


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])
security = HTTPBearer(auto_error=False)


@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserResponse )
def update_profile(updated_user: UserUpdate,current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):

    current_user.name = updated_user.first_name + updated_user.last_name
    current_user.phone_number = updated_user.phone_number
    
    try:
        db.commit()
        db.refresh(current_user)
        logger.info(f"Profile updated for user: {current_user.id}")
        return current_user
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Profile update failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to update profile")


@router.patch("/profile", response_model=UserResponse)
def patch_profile(patch_data: UserPatch,current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):

    try:
        update_data = patch_data.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            setattr(current_user, key, value)
            
        if "first_name" in update_data or "last_name" in update_data:
            current_user.name = (f"{current_user.first_name} {current_user.last_name}")
    
        db.commit()
        db.refresh(current_user)
        logger.info(f"Profile patched for user: {current_user.id}")
        return current_user
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Profile patch failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to update profile")


@router.delete("/profile", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):

    if not current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")

    try:
        user_id = current_user.id
        
        try:
            supabase_service.auth.admin.delete_user(str(user_id))
            logger.info(f"User deleted from Supabase Auth: {user_id}")
        except Exception as e:
            logger.warning(f"Failed to delete from Supabase Auth: {str(e)}")
        
        db.delete(current_user)
        db.commit()
        logger.info(f"User deleted from local DB: {user_id}")
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"User deletion failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to delete account")

        
@router.get("/sessions")
def get_active_sessions(current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    
    sessions = db.query(UserSession).filter(UserSession.user_id == current_user.id,UserSession.revoked_at == None).all()
    
    return {
        "total_active_sessions": len(sessions),
        "sessions": [
            {
                "id": s.id,
                "device_name": s.device_name,
                "user_agent": s.user_agent,
                "ip_address": s.ip_address,
                "created_at": s.created_at,
                "last_used_at": s.last_used_at,
                "expires_at": s.expires_at
            }
            for s in sessions
        ]
    }