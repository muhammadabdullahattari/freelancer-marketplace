from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationEventType, NotificationStatus
from app.models.notification_preference import NotificationPreference
from app.models.users import User
from app.core.errors import BusinessLogicException, ErrorCode, ValidationException
from app.core.config import settings
from app.celery_app import celery_app
from datetime import datetime, timezone
from uuid import UUID
import logging
import hashlib
from typing import Optional, Dict, Any
from app.database import SessionLocal
from app.services.email import EmailService

logger = logging.getLogger(__name__)

class NotificationService:
    
    @staticmethod
    def create_idempotency_key(event_type: str,resource_id: UUID,trigger_action: str = "default") -> str:
        
        key_base = f"evt_{event_type}_{str(resource_id)}_{trigger_action}"
        idempotency_key = f"evt_{hashlib.sha256(key_base.encode()).hexdigest()[:16]}"
        
        return idempotency_key
    
    @staticmethod
    def check_notification_exists(db: Session, idempotency_key: str) -> Optional[Notification]:

        return db.query(Notification).filter(Notification.idempotency_key == idempotency_key).first()
    
    @staticmethod
    def get_user_preferences(db: Session, user_id: UUID) -> NotificationPreference:
        
        prefs = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
        
        if not prefs:
            logger.info(f"Creating default notification preferences for user {user_id}")
            prefs = NotificationPreference(user_id=user_id)
            db.add(prefs)
            db.commit()
            db.refresh(prefs)
        
        return prefs
    
    @staticmethod
    def should_send_notification(db: Session, event_type: str, recipient_user_id: UUID) -> tuple[bool, str | None]:
        
        prefs = NotificationService.get_user_preferences(db, recipient_user_id)
        
        if not prefs.email_enabled:
            return False, "email_disabled"
        
        event_type_upper = event_type.upper()
        if event_type_upper in ["USER_REGISTERED", "SECURITY_EVENT"]:
            if not prefs.transactional_emails:
                return False, "transactional_disabled"
        
        elif event_type_upper in ["PROPOSAL_RECEIVED", "PROPOSAL_ACCEPTED", "PROPOSAL_REJECTED"]:
            if not prefs.proposal_notifications:
                return False, "proposal_notifications_disabled"
        
        elif event_type_upper in ["CONTRACT_CREATED", "CONTRACT_COMPLETED"]:
            if not prefs.contract_notifications:
                return False, "contract_notifications_disabled"
        
        elif event_type_upper in ["MILESTONE_SUBMITTED", "MILESTONE_APPROVED", "MILESTONE_REJECTED"]:
            if not prefs.milestone_notifications:
                return False, "milestone_notifications_disabled"
        
        elif event_type_upper == "REVIEW_SUBMITTED":
            if not prefs.review_notifications:
                return False, "review_notifications_disabled"
        
        return True, None
    
    @staticmethod
    def queue_notification(
        db: Session,
        event_type: str,
        recipient_user_id: UUID,
        email_subject: str,
        email_body_html: str,
        resource_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        triggered_by_user_id: Optional[UUID] = None,
        event_payload: Optional[Dict[str, Any]] = None,
        trigger_action: str = "default"
    ) -> Notification:
        
        logger.info(f"Queueing notification: {event_type} to user {recipient_user_id} for resource {resource_id}")
        
        try:
            recipient = db.query(User).filter(User.id == recipient_user_id).first()
            if not recipient:
                raise ValidationException(f"Recipient user {recipient_user_id} not found")
            
            idempotency_key = NotificationService.create_idempotency_key(event_type, resource_id or recipient_user_id, trigger_action)
            
            existing = NotificationService.check_notification_exists(db, idempotency_key)
            if existing:
                logger.info(f"Notification already exists (idempotency key: {idempotency_key}). Skipping duplicate. Status: {existing.status}")
                return existing
            
            should_send, skip_reason = NotificationService.should_send_notification(db, event_type, recipient_user_id)
            
            notification = Notification(
                event_type=event_type,
                event_name=event_type.replace("_", " ").title(),
                resource_id=resource_id,
                resource_type=resource_type,
                recipient_user_id=recipient_user_id,
                triggered_by_user_id=triggered_by_user_id,
                idempotency_key=idempotency_key,
                email_subject=email_subject,
                email_body_html=email_body_html,
                event_payload=event_payload or {},
                status=NotificationStatus.PENDING.value if should_send else NotificationStatus.DELIVERY_FAILED.value,
                was_preference_skipped=not should_send,
                skip_reason=skip_reason
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            logger.info(f"Notification created: {notification.id}")
            
            if should_send:
                try:
                    task = send_notification_email.delay(str(notification.id))
                    logger.info(f"Notification queued for delivery. Celery task: {task.id}")
                except Exception as celery_err:
                    logger.warning(f"Celery task dispatch skipped/failed for notification {notification.id}: {str(celery_err)}")
            else:
                logger.info(f"Notification skipped due to user preference: {skip_reason}")
            
            return notification
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Failed to queue notification: {str(e)}", exc_info=True)
            db.rollback()
            raise BusinessLogicException(
                ErrorCode.INTERNAL_ERROR,
                f"Failed to queue notification: {str(e)}"
            )

@celery_app.task(bind=True, max_retries=settings.NOTIFICATION_MAX_RETRIES)
def send_notification_email(self, notification_id: str):
    
    db = SessionLocal()
    
    try:
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        
        if not notification:
            logger.error(f"Notification {notification_id} not found!")
            return {"status": "error", "message": "Notification not found"}
        
        if notification.status == NotificationStatus.SENT.value:
            logger.info(f"Notification {notification_id} already sent, skipping")
            return {"status": "skipped", "message": "Already sent"}
        
        notification.delivery_attempts += 1
        notification.last_attempted_at = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(
            f"Sending notification {notification_id} "
            f"(attempt {notification.delivery_attempts}/{settings.NOTIFICATION_MAX_RETRIES})")
        
        try:
            response = EmailService.send_email(
                to=notification.recipient_user.email,
                subject=notification.email_subject,
                body_html=notification.email_body_html
            )
            
            notification.status = NotificationStatus.SENT.value
            notification.delivered_at = datetime.now(timezone.utc)
            notification.last_error_message = None
            notification.last_error_code = None
            db.commit()
            
            logger.info(f"Notification {notification_id} sent successfully")
            return {"status": "sent", "notification_id": notification_id}
            
        except Exception as email_error:
            logger.error(f"Email send failed for notification {notification_id}: {str(email_error)}")
            
            notification.last_error_message = str(email_error)[:500]
            notification.last_error_code = "EMAIL_SEND_FAILED"
            db.commit()
            
            if self.request.retries < settings.NOTIFICATION_MAX_RETRIES:
                countdown = settings.NOTIFICATION_RETRY_DELAY_SECONDS * (2 ** self.request.retries)
                logger.info(
                    f"Retrying notification {notification_id} "
                    f"in {countdown}s (attempt {self.request.retries + 1})")
                raise self.retry(exc=email_error, countdown=countdown)
            else:
                notification.status = NotificationStatus.FAILED.value
                db.commit()
                logger.error(f"Notification {notification_id} failed after max retries")
                return {"status": "failed", "notification_id": notification_id}
    
    except Exception as e:
        logger.error(f"Unexpected error in send_notification_email: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()