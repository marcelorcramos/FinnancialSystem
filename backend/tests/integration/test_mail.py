"""Sending email over SMTP to a real Mailpit, through the Celery task."""

import json
import time
import urllib.request
from collections.abc import Iterator
from typing import Any

import pytest
from testcontainers.core.container import DockerContainer

from app.core.config import settings
from app.workers.tasks import send_email


def _get(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310 (test container)
        return json.load(response)


@pytest.fixture(scope="module")
def mailpit() -> Iterator[str]:
    with DockerContainer("axllent/mailpit:v1.32.0").with_exposed_ports(1025, 8025) as container:
        host = container.get_container_host_ip()
        api = f"http://{host}:{container.get_exposed_port(8025)}/api/v1"
        for _ in range(100):
            try:
                _get(f"{api}/messages")
                break
            except OSError:
                time.sleep(0.1)
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(settings, "SMTP_HOST", host)
            patch.setattr(settings, "SMTP_PORT", int(container.get_exposed_port(1025)))
            yield api


def test_the_send_email_task_delivers_over_smtp(mailpit: str) -> None:
    send_email.run("alice@example.com", "Confirm your email", "Open the link.")
    [message] = _get(f"{mailpit}/messages")["messages"]
    assert message["To"][0]["Address"] == "alice@example.com"
    assert message["From"]["Address"] == "no-reply@finnancial.local"
    assert message["Subject"] == "Confirm your email"
    assert message["Snippet"] == "Open the link."
