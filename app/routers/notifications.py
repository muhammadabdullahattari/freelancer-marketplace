from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.users import User
from app.models.notification import Notification, NotificationStatus
from app.models.notification_preference import NotificationPreference
from app.services.notification import NotificationService
from app.schemas.notification import (
    NotificationResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationHistoryPaginatedResponse
)
from app.core.config import settings
from app.dependencies.pagination import get_pagination_params, PaginationParams
from app.core.errors import ResourceNotFoundException
import logging
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.get("/", response_model=NotificationHistoryPaginatedResponse)
def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(get_pagination_params),
    status: str | None = Query(None, description="Filter by status (pending, sent, failed)")):

    logger.info(f"Fetching notifications for user {current_user.id}")
    query = db.query(Notification).filter(Notification.recipient_user_id == current_user.id)

    if status:
        query = query.filter(Notification.status == status)
    
    total = query.count()
    notifications = query.order_by(Notification.created_at.desc()).offset(pagination.skip).limit(pagination.limit).all()
    
    return {
        "items": [
            {
                "id": n.id,
                "event_type": n.event_type,
                "subject": n.email_subject,
                "status": n.status,
                "created_at": n.created_at,
                "delivered_at": n.delivered_at,
                "skip_reason": n.skip_reason
            }
            for n in notifications
        ],
        "total": total,
        "pages": (total + pagination.limit - 1) // pagination.limit,
        "skip": pagination.skip,
        "limit": pagination.limit
    }

@router.get("/preferences", response_model=NotificationPreferenceResponse)
def get_notification_preferences(current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    
    logger.info(f"Fetching notification preferences for user {current_user.id}")
    prefs = NotificationService.get_user_preferences(db, current_user.id)
    
    return {
        "id": prefs.id,
        "email_enabled": prefs.email_enabled,
        "transactional_emails": prefs.transactional_emails,
        "proposal_notifications": prefs.proposal_notifications,
        "contract_notifications": prefs.contract_notifications,
        "milestone_notifications": prefs.milestone_notifications,
        "review_notifications": prefs.review_notifications,
        "marketing_emails": prefs.marketing_emails,
        "digest_frequency": prefs.digest_frequency,
        "updated_at": prefs.updated_at
    }

@router.patch("/preferences", response_model=NotificationPreferenceResponse)
def update_notification_preferences(prefs_data: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):

    logger.info(f"Updating notification preferences for user {current_user.id}")
    prefs = NotificationService.get_user_preferences(db, current_user.id)
 
    if prefs_data.email_enabled is not None:
        prefs.email_enabled = prefs_data.email_enabled
    if prefs_data.transactional_emails is not None:
        prefs.transactional_emails = prefs_data.transactional_emails
    if prefs_data.proposal_notifications is not None:
        prefs.proposal_notifications = prefs_data.proposal_notifications
    if prefs_data.contract_notifications is not None:
        prefs.contract_notifications = prefs_data.contract_notifications
    if prefs_data.milestone_notifications is not None:
        prefs.milestone_notifications = prefs_data.milestone_notifications
    if prefs_data.review_notifications is not None:
        prefs.review_notifications = prefs_data.review_notifications
    if prefs_data.marketing_emails is not None:
        prefs.marketing_emails = prefs_data.marketing_emails
    if prefs_data.digest_frequency is not None:
        prefs.digest_frequency = prefs_data.digest_frequency
    
    prefs.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(prefs)
    
    logger.info(f"Notification preferences updated for user {current_user.id}")
    
    return {
        "id": prefs.id,
        "email_enabled": prefs.email_enabled,
        "transactional_emails": prefs.transactional_emails,
        "proposal_notifications": prefs.proposal_notifications,
        "contract_notifications": prefs.contract_notifications,
        "milestone_notifications": prefs.milestone_notifications,
        "review_notifications": prefs.review_notifications,
        "marketing_emails": prefs.marketing_emails,
        "digest_frequency": prefs.digest_frequency,
        "updated_at": prefs.updated_at
    }

@router.post("/test")
def test_notification(current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    
    if settings.DEBUG:
        logger.warning(f"Test notification triggered by user {current_user.id}")
        
        try:
            notification = NotificationService.queue_notification(
                db=db,
                event_type="test_event",
                recipient_user_id=current_user.id,
                email_subject="Test Notification",
                email_body_html="""
                <html>
                <body>
                    <h2>Test Notification</h2>
                    <p>This is a test email. If you received this, the notification system is working!</p>
                </body>
                </html>
                """,
                event_payload={"test": True}
            )
            
            return {
                "status": "sent",
                "notification_id": str(notification.id),
                "message": "Test notification queued"
            }
        except Exception as e:
            logger.error(f"Test notification failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    else:
        return {
            "status": "disabled",
            "message": "Test endpoint only available in DEBUG mode"
        }

@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)):
    
    try:
        uuid_obj = UUID(notification_id)
    except ValueError:
        raise ResourceNotFoundException("Notification")

    notification = db.query(Notification).filter(Notification.id == uuid_obj,
        Notification.recipient_user_id == current_user.id).first()
    
    if not notification:
        raise ResourceNotFoundException("Notification")
    
    return {
        "id": notification.id,
        "event_type": notification.event_type,
        "subject": notification.email_subject,
        "body_html": notification.email_body_html,
        "status": notification.status,
        "created_at": notification.created_at,
        "delivered_at": notification.delivered_at,
        "delivery_attempts": notification.delivery_attempts,
        "last_error": notification.last_error_message
    }