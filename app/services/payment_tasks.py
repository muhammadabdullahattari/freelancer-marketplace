from task_engine import task
from app.database import SessionLocal
from app.services.stripe_payment import StripePaymentService
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


@task(
    name="reconcile_pending_payments_task",
    queue="payments",
    max_attempts=3,
    retry_delay_seconds=60,
    timeout_seconds=300,
)
def reconcile_pending_payments_task(*args, **kwargs):
    """
    Task Engine periodic task to reconcile pending payments against Stripe.
    """
    logger.info("Executing Task Engine payment reconciliation task")
    db = SessionLocal()
    try:
        stats = StripePaymentService.reconcile_pending_payments(
            db=db,
            batch_size=settings.PAYMENT_RECONCILIATION_BATCH_SIZE
        )
        logger.info(f"Payment reconciliation completed successfully: {stats}")
        return stats
    except Exception as exc:
        logger.error(f"Error in payment reconciliation task: {exc}", exc_info=True)
        raise exc
    finally:
        db.close()
