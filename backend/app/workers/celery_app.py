"""Celery app: RabbitMQ is the broker, beat schedules the periodic tasks.

Worker: `celery -A app.workers.celery_app worker`; beat: `celery -A app.workers.celery_app beat`.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery("finance", broker=settings.RABBITMQ_URL, include=["app.workers.tasks"])
celery_app.conf.update(
    task_acks_late=True,  # a task that crashes mid-run is delivered again
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_ignore_result=True,
    # Remote control uses transient non-exclusive queues, which RabbitMQ 4 refuses.
    worker_enable_remote_control=False,
    # Our structlog lines go straight to stdout (JSON for Loki), not through Celery's
    # logger, which would wrap each one in a second, plain-text line.
    worker_redirect_stdouts=False,
    timezone="UTC",
    beat_schedule={
        # Hourly, so each user's month starts at midnight in their own time zone.
        "create-due-months": {
            "task": "app.workers.tasks.create_due_months",
            "schedule": crontab(minute=5),
        },
        "remove-expired-demos": {
            "task": "app.workers.tasks.remove_expired_demos",
            "schedule": crontab(minute=20),
        },
        "remove-expired-exports": {
            "task": "app.workers.tasks.remove_expired_exports",
            "schedule": crontab(hour=3, minute=15),
        },
    },
)

# Connects the worker's metrics, traces and error reporting (signal handlers).
from app.workers import observability  # noqa: E402, F401
