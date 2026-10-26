import pytest
from pydantic import ValidationError

from app.domain.passwords import password_problems
from app.schemas.user import PasswordChange, UserCreate


def test_strong_password_has_no_problems() -> None:
    assert password_problems("Segura#2026") == []


@pytest.mark.parametrize(
    ("password", "missing"),
    [
        ("Ab1!", "pelo menos 8 caracteres"),
        ("SEGURA#2026", "uma letra minúscula"),
        ("segura#2026", "uma letra maiúscula"),
        ("Segura#Senha", "um número"),
        ("Segura2026", "um caractere especial"),
        ("Segura 2026", "um caractere especial"),  # espaço não conta como símbolo
    ],
)
def test_each_rule_is_reported(password: str, missing: str) -> None:
    assert missing in password_problems(password)


def test_register_and_change_password_apply_the_policy() -> None:
    with pytest.raises(ValidationError, match="letra maiúscula"):
        UserCreate(email="a@example.com", password="fraca#2026", name="A")
    with pytest.raises(ValidationError, match="caractere especial"):
        PasswordChange(current_password="x", new_password="Fraca2026")
    UserCreate(email="a@example.com", password="Forte#2026", name="A")
