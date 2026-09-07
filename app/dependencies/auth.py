from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import verify_supabase_token, get_token_from_header
from app.database import get_db
from app.models.users import User
from typing import Optional
import logging
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),db: Session = Depends(get_db)) -> User:
    
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    payload = verify_supabase_token(token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID"
        )
    
    user = db.query(User).filter(User.id == UUID(user_id)).first()

    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


def get_current_freelancer_user(current_user: User = Depends(get_current_user)) -> User:

    if current_user.role != "FREELANCER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires FREELANCER role"
        )
    return current_user


def get_current_client_user(current_user: User = Depends(get_current_user)) -> User:

    if current_user.role != "CLIENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires CLIENT role"
        )
    return current_user


def is_freelancer(current_user: User = Depends(get_current_user)) -> User:

    if current_user.role not in ["FREELANCER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this action"
        )
    return current_user