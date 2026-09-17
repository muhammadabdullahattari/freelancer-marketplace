import uuid
from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy.orm import Session
from app.models.users import User
from app.models.notifications import Notification, NotificationEventType, NotificationStatus
from app.models.notification_preference import NotificationPreference
from app.services.notification import NotificationService, send_notification_email
from app.services.notification_template import TemplateService
from app.services.email import EmailService
from app.celery_app import celery_app

def test_template_rendering():
    """Verify that Jinja2 templates render HTML dynamically."""
    template = TemplateService.get_template("user_registered")
    rendered = template.render({
        "user_name": "Alice Developer",
        "user_email": "alice@example.com",
        "user_role": "Freelancer",
        "platform_url": "https://marketplace.example.com"
    })
    
    assert "Welcome to Freelancer Marketplace, Alice Developer!" in rendered["subject"]
    assert "Alice Developer" in rendered["body"]
    assert "alice@example.com" in rendered["body"]
    assert "Freelancer" in rendered["body"]

def test_notification_idempotency(db_session: Session, client_user: User):
    """Verify that duplicate notifications with the same idempotency key are skipped."""
    resource_id = uuid.uuid4()
    
    notif1 = NotificationService.queue_notification(
        db=db_session,
        event_type=NotificationEventType.PROPOSAL_RECEIVED.value,
        recipient_user_id=client_user.id,
        email_subject="Test Idempotency Subject",
        email_body_html="<p>Test Body</p>",
        resource_id=resource_id,
        trigger_action="submit"
    )
    assert notif1 is not None
    assert notif1.status == NotificationStatus.PENDING.value

    # Attempt to queue identical notification second time
    notif2 = NotificationService.queue_notification(
        db=db_session,
        event_type=NotificationEventType.PROPOSAL_RECEIVED.value,
        recipient_user_id=client_user.id,
        email_subject="Test Idempotency Subject",
        email_body_html="<p>Test Body</p>",
        resource_id=resource_id,
        trigger_action="submit"
    )
    assert notif2.id == notif1.id  # Same notification object returned, duplicate prevented

def test_notification_preference_respect(db_session: Session, client_user: User):
    """Verify that user notification preferences are respected."""
    prefs = NotificationService.get_user_preferences(db_session, client_user.id)
    prefs.proposal_notifications = False
    db_session.flush()
    
    resource_id = uuid.uuid4()
    notif = NotificationService.queue_notification(
        db=db_session,
        event_type=NotificationEventType.PROPOSAL_RECEIVED.value,
        recipient_user_id=client_user.id,
        email_subject="Proposal Test",
        email_body_html="<p>Test</p>",
        resource_id=resource_id,
        trigger_action="submit_disabled"
    )
    
    assert notif.was_preference_skipped is True
    assert notif.skip_reason == "proposal_notifications_disabled"
    assert notif.status == NotificationStatus.DELIVERY_FAILED.value

@patch("app.services.notification.SessionLocal")
@patch("app.services.email.EmailService.send_email")
def test_send_notification_email_celery_task(mock_send_email, mock_session_local, db_session: Session, client_user: User):
    """Verify Celery task send_notification_email processes pending notifications and marks them sent."""
    # Intercept SessionLocal query filter for SQLite Uuid type compatibility with string IDs
    orig_query = db_session.query
    def patched_query(*args, **kwargs):
        q = orig_query(*args, **kwargs)
        if args and args[0] is Notification:
            orig_filter = q.filter
            def patched_filter(*criterion):
                new_criterion = []
                for c in criterion:
                    if hasattr(c, "right") and hasattr(c.right, "value") and isinstance(c.right.value, str):
                        try:
                            c.right.value = uuid.UUID(c.right.value)
                        except (ValueError, TypeError, AttributeError):
                            pass
                    new_criterion.append(c)
                return orig_filter(*new_criterion)
            q.filter = patched_filter
        return q

    mock_session_local.return_value.query = patched_query
    mock_send_email.return_value = {"status": "sent", "recipient": client_user.email}
    
    resource_id = uuid.uuid4()
    with patch("app.services.notification.send_notification_email.delay"):
        notif = NotificationService.queue_notification(
            db=db_session,
            event_type=NotificationEventType.CONTRACT_CREATED.value,
            recipient_user_id=client_user.id,
            email_subject="Contract Created Test",
            email_body_html="<p>Contract content</p>",
            resource_id=resource_id,
            trigger_action="celery_test"
        )
    
    celery_app.conf.task_always_eager = True
    # Run Celery task synchronously via delay() with task_always_eager=True passing string ID as Celery does
    task_res = send_notification_email.delay(str(notif.id))
    
    assert task_res.result["status"] == "sent"
    assert notif.status == NotificationStatus.SENT.value
    assert notif.delivered_at is not None
    assert mock_send_email.called
