from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.sessions import UserSession
from app.models.users import User
from uuid import UUID
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


def get_active_sessions(db: Session, user_id: UUID) -> list[UserSession]:
    return db.query(UserSession).filter(UserSession.user_id == user_id,UserSession.revoked_at == None,
        UserSession.expires_at > datetime.now(timezone.utc)).all()

def get_session_count(db: Session, user_id: UUID) -> int:
    return len(get_active_sessions(db, user_id))

def revoke_session(db: Session, session_id: int, user_id: UUID) -> UserSession:
    session = db.query(UserSession).filter(UserSession.id == session_id,UserSession.user_id == user_id).first()
    
    if not session:
        from app.core.errors import ResourceNotFoundException
        raise ResourceNotFoundException("Session")
    
    try:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
        logger.info(f"Session revoked: {session_id}")
        return session
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to revoke session: {str(e)}")
        raise


def cleanup_expired_sessions(db: Session, user_id: UUID) -> int:
    try:
        deleted_count = db.query(UserSession).filter(UserSession.user_id == user_id,
            UserSession.expires_at <= datetime.now(timezone.utc)).delete()
        
        db.commit()
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired sessions for user {user_id}")
        
        return deleted_count
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to cleanup sessions: {str(e)}")
        raise