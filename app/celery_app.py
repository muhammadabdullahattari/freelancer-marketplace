from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

celery_app = Celery("freelancer_marketplace", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)

celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=[settings.CELERY_ACCEPT_CONTENT],
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    
    task_track_started=True,
    task_time_limit=30 * 60,  
    task_soft_time_limit=25 * 60, 
    
    result_expires=3600,  
    
    task_acks_late=True, 
    worker_prefetch_multiplier=1, 
    
    beat_schedule={
        "cleanup-failed-notifications": {
            "task": "app.services.notification.cleanup_failed_notifications",
            "schedule": crontab(hour=2, minute=0)}})

celery_app.autodiscover_tasks(["app.services"])

# Import notification service so tasks like send_notification_email are registered with Celery
import app.services.notification  # noqa: F401

@celery_app.on_after_configure.connect
def setup_celery_logging(sender, **kwargs):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@celery_app.task(bind=True)
def debug_task(self):
    logger.info(f"Debug task called. Request: {self.request}")
    return "Celery is working!"