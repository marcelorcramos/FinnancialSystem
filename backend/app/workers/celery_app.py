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
    timezone="UTC",
    beat_schedule={
        # Hourly, so each user's month starts at midnight in their own time zone.
        "create-due-months": {
            "task": "app.workers.tasks.create_due_months",
            "schedule": crontab(minute=5),
        },
    },
)
