from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.users import User
from app.models.sessions import UserSession
from app.services.sessions import get_active_sessions, get_session_count, revoke_session, cleanup_expired_sessions
from pydantic import BaseModel
import logging
from app.schemas.sessions import SessionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.get("/", response_model=list[SessionResponse])
def get_active_sessions_endpoint(current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    logger.info(f"Fetching active sessions for user: {current_user.id}")
    sessions = get_active_sessions(db, current_user.id)
    return [
        {**{k: v for k, v in s.__dict__.items() if not k.startswith('_')},
         "is_active": s.revoked_at is None} for s in sessions]

@router.get("/count")
def get_session_count_endpoint(current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    logger.info(f"Counting sessions for user: {current_user.id}")
    count = get_session_count(db, current_user.id)
    return {"active_sessions": count}

@router.delete("/{session_id}", status_code=204)
def revoke_session_endpoint(session_id: int,current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    logger.info(f"Revoking session {session_id} for user: {current_user.id}")
    revoke_session(db, session_id, current_user.id)

@router.post("/cleanup", status_code=204)
def cleanup_expired_sessions_endpoint(current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    logger.info(f"Cleaning up expired sessions for user: {current_user.id}")
    cleanup_expired_sessions(db, current_user.id)