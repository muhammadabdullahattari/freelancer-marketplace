import logging
from task_engine import TaskEngine, task
from app.core.config import settings

logger = logging.getLogger(__name__)

# Format asynchronous database URL for Task Engine PostgreSQL native broker
async_db_url = (
    settings.DATABASE_URL
    .replace("postgresql+psycopg://", "postgresql+asyncpg://")
    .replace("postgres+psycopg://", "postgresql+asyncpg://")
    .replace("postgresql://", "postgresql+asyncpg://")
    .replace("postgres://", "postgresql+asyncpg://")
)

engine = TaskEngine(
    name="freelancer_marketplace",
    broker="native",
    database_url=async_db_url,
    direct_mode=True,
)

# Register periodic schedules (replaces celery beat)
engine.add_cron_schedule(
    task_name="reconcile_pending_payments_task",
    cron_expression="30 2 * * *",
    schedule_name="reconcile-pending-payments",
    queue="payments",
)

engine.add_cron_schedule(
    task_name="cleanup_failed_notifications",
    cron_expression="0 2 * * *",
    schedule_name="cleanup-failed-notifications",
    queue="default",
)

@task(name="debug_task", queue="default", max_attempts=3, retry_delay_seconds=5)
def debug_task():
    logger.info("Debug task executed successfully via Task Engine Native Broker.")
    return "Task Engine is working!"

import app.services.notification  # noqa: F401
import app.services.payment_tasks  # noqa: F401
