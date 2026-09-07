from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.sessions import UserSession
from app.core.config import settings
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

def rotate_refresh_token(user_id: UUID,old_refresh_token: str,new_refresh_token: str,
                         user_agent: str | None,ip_address: str | None,db: Session) -> UserSession:

    try:
        old_session = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.refresh_token_hash == old_refresh_token,
            UserSession.revoked_at == None).first()
        
        if old_session:
            old_session.revoked_at = datetime.now(timezone.utc)
            logger.info(f"Old session revoked for user: {user_id}, session_id: {old_session.id}")
        
        refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        new_session = UserSession(
            user_id=user_id,
            refresh_token_hash=new_refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=refresh_expires_at
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        logger.info(f"New session created for user: {user_id}, session_id: {new_session.id}")
        return new_session
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Token rotation failed: {str(e)}")
        raise


def get_user_sessions(user_id: UUID, db: Session):
    return db.query(UserSession).filter(UserSession.user_id == user_id,UserSession.revoked_at == None).all()


def revoke_session(session_id: int, db: Session):
    try:
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Session revoked: {session_id}")
            return True
        return False
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to revoke session: {str(e)}")
        raise


def revoke_all_sessions(user_id: UUID, db: Session):
    try:
        sessions = db.query(UserSession).filter(UserSession.user_id == user_id,UserSession.revoked_at == None).all()
        
        now = datetime.now(timezone.utc)
        for session in sessions:
            session.revoked_at = now
        
        db.commit()
        logger.info(f"All sessions revoked for user: {user_id}, count: {len(sessions)}")
        return len(sessions)
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to revoke all sessions: {str(e)}")
        raise


def is_session_valid(session_id: int, user_id: UUID, db: Session) -> bool:
    session = db.query(UserSession).filter(UserSession.id == session_id,UserSession.user_id == user_id).first()
    
    if not session:
        return False
    
    if session.revoked_at is not None:
        return False
    
    if session.expires_at < datetime.now(timezone.utc):
        return False
    
    return True