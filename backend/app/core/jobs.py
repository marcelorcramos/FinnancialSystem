"""Hands background work to Celery (emails, exports, storage cleanup).

The API never imports the task functions: it sends tasks by name, after its own
transaction has committed, so the worker always finds the rows it needs. If the
broker is down the job is logged and dropped; every job can be asked for again.
"""

from typing import Any

import structlog
from starlette.concurrency import run_in_threadpool

from app.workers.celery_app import celery_app

log = structlog.get_logger(__name__)

SEND_EMAIL = "app.workers.tasks.send_email"
RUN_EXPORT = "app.workers.tasks.run_export"
DELETE_USER_FILES = "app.workers.tasks.delete_user_files"


class JobQueue:
    async def enqueue(self, task: str, **kwargs: Any) -> None:
        try:
            await run_in_threadpool(celery_app.send_task, task, kwargs=kwargs, retry=False)
        except Exception as error:  # the request already succeeded; do not fail it
            log.warning("jobs.enqueue_failed", task=task, error=str(error))


def get_job_queue() -> JobQueue:
    return JobQueue()
