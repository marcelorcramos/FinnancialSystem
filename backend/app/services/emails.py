"""The emails the app sends: built here, sent by the Celery worker."""

from dataclasses import dataclass
from urllib.parse import urlencode

from app.core.config import settings
from app.core.jobs import SEND_EMAIL, JobQueue


@dataclass(frozen=True, slots=True)
class Email:
    to: str
    subject: str
    body: str


def _link(path: str, token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}?{urlencode({'token': token})}"


def verification(to: str, name: str, token: str) -> Email:
    return Email(
        to=to,
        subject="Confirm your email",
        body=(
            f"Hi {name},\n\n"
            "Confirm this is your email address by opening the link below:\n\n"
            f"{_link('/verify-email', token)}\n\n"
            "The link works for 48 hours. If you did not create a FinnancialSystem account, "
            "ignore this email.\n"
        ),
    )


def password_reset(to: str, name: str, token: str) -> Email:
    return Email(
        to=to,
        subject="Reset your password",
        body=(
            f"Hi {name},\n\n"
            "Someone asked to reset the password of your FinnancialSystem account. "
            "Choose a new one here:\n\n"
            f"{_link('/reset-password', token)}\n\n"
            "The link works for 1 hour and only once. If it was not you, ignore this email: "
            "your password stays the same.\n"
        ),
    )


def account_deleted(to: str, name: str) -> Email:
    return Email(
        to=to,
        subject="Your account was deleted",
        body=(
            f"Hi {name},\n\n"
            "Your FinnancialSystem account and all of its data, receipts included, "
            "were deleted as you asked. This cannot be undone.\n\n"
            "You can create a new account with this email at any time.\n"
        ),
    )


async def send(jobs: JobQueue, email: Email) -> None:
    await jobs.enqueue(SEND_EMAIL, to=email.to, subject=email.subject, body=email.body)
