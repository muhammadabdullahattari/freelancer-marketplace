import logging
from task_engine import task
from app.task_engine_app import engine, debug_task

logger = logging.getLogger(__name__)


class CeleryConfCompat:
    def __init__(self):
        self.task_always_eager = False

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if key == "task_always_eager":
            from task_engine.client import TaskEngineClient
            client = TaskEngineClient.get_default()
            client.always_eager = bool(value)

    def update(self, *args, **kwargs):
        pass


class CeleryCompat:
    def __init__(self):
        self.conf = CeleryConfCompat()

    def task(self, *args, **kwargs):
        max_attempts = kwargs.get("max_retries", 3)
        queue = kwargs.get("queue", "default")
        return task(queue=queue, max_attempts=max_attempts)

    def autodiscover_tasks(self, *args, **kwargs):
        pass


celery_app = CeleryCompat()

__all__ = ["celery_app", "engine", "debug_task"]