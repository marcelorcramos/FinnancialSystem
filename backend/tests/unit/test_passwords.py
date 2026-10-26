import pytest
from pydantic import ValidationError

from app.domain.passwords import password_problems
from app.schemas.user import PasswordChange, UserCreate


def test_strong_password_has_no_problems() -> None:
    assert password_problems("Secure#2026") == []


@pytest.mark.parametrize(
    ("password", "missing"),
    [
        ("Ab1!", "at least 8 characters"),
        ("SECURE#2026", "a lowercase letter"),
        ("secure#2026", "an uppercase letter"),
        ("Secure#Pass", "a digit"),
        ("Secure2026", "a special character"),
        ("Secure 2026", "a special character"),  # a space does not count as a symbol
    ],
)
def test_each_rule_is_reported(password: str, missing: str) -> None:
    assert missing in password_problems(password)


def test_register_and_change_password_apply_the_policy() -> None:
    with pytest.raises(ValidationError, match="uppercase letter"):
        UserCreate(email="a@example.com", password="weak#2026", name="A")
    with pytest.raises(ValidationError, match="special character"):
        PasswordChange(current_password="x", new_password="Weak2026")
    UserCreate(email="a@example.com", password="Strong#2026", name="A")
