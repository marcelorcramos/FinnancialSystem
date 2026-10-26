import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core import security
from app.core.config import settings


def test_password_hash_roundtrip() -> None:
    hashed = security.hash_password("correct horse")
    assert hashed != "correct horse"
    assert security.verify_password("correct horse", hashed)
    assert not security.verify_password("wrong horse", hashed)


def test_verify_password_without_hash_is_false() -> None:
    assert not security.verify_password("anything", None)


def test_verify_password_with_garbage_hash_is_false() -> None:
    assert not security.verify_password("anything", "not-an-argon2-hash")


def test_access_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    token, expires_in = security.create_access_token(user_id)
    assert expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert security.decode_access_token(token) == user_id


def test_expired_access_token_is_rejected() -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    token, _ = security.create_access_token(uuid.uuid4(), now=past)
    assert security.decode_access_token(token) is None


def test_token_signed_with_other_key_is_rejected() -> None:
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "another-secret-key-0123456789abcdef0123",
        algorithm="HS256",
    )
    assert security.decode_access_token(token) is None


def test_token_of_other_type_is_rejected() -> None:
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": "refresh",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    assert security.decode_access_token(token) is None


def test_token_with_non_uuid_subject_is_rejected() -> None:
    token = jwt.encode(
        {"sub": "42", "type": "access", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    assert security.decode_access_token(token) is None


def test_refresh_tokens_are_random_and_hashed() -> None:
    a, b = security.generate_refresh_token(), security.generate_refresh_token()
    assert a != b
    assert len(security.hash_refresh_token(a)) == 64
    assert security.hash_refresh_token(a) == security.hash_refresh_token(a)
