from typing import Any

import pytest

from app.core import jobs
from app.core.jobs import SEND_EMAIL, JobQueue


async def test_jobs_are_sent_to_celery_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        jobs.celery_app, "send_task", lambda *args, **kwargs: sent.append((args, kwargs))
    )
    await JobQueue().enqueue(SEND_EMAIL, to="a@example.com")
    assert sent == [((SEND_EMAIL,), {"kwargs": {"to": "a@example.com"}, "retry": False})]


async def test_a_broker_failure_does_not_fail_the_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*_: Any, **__: Any) -> None:
        raise ConnectionError("broker down")

    monkeypatch.setattr(jobs.celery_app, "send_task", broken)
    await JobQueue().enqueue(SEND_EMAIL, to="a@example.com")  # no exception


def test_every_job_name_is_a_registered_task() -> None:
    import app.workers.tasks  # noqa: F401  (registers the tasks)

    for name in (jobs.SEND_EMAIL, jobs.RUN_EXPORT):
        assert name in jobs.celery_app.tasks, name
    schedule = jobs.celery_app.conf.beat_schedule["remove-expired-exports"]
    assert schedule["task"] in jobs.celery_app.tasks
