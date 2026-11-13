from datetime import UTC, datetime, timedelta

import pyotp

from app.core import two_factor

NOW = datetime(2026, 11, 13, 10, 0, 0, tzinfo=UTC)


def code_at(secret: str, when: datetime) -> str:
    return pyotp.TOTP(secret).at(when)


def test_secrets_are_encrypted_and_come_back() -> None:
    secret = two_factor.new_secret()
    stored = two_factor.encrypt(secret)
    assert secret not in stored
    assert two_factor.decrypt(stored) == secret
    assert two_factor.decrypt("not-a-token") is None


def test_a_current_code_is_accepted_once() -> None:
    secret = two_factor.new_secret()
    code = code_at(secret, NOW)
    accepted = two_factor.verify(secret, code, None, NOW)
    assert accepted is not None
    assert two_factor.verify(secret, code, accepted.step, NOW) is None


def test_codes_from_a_neighbouring_step_pass_but_older_ones_do_not() -> None:
    secret = two_factor.new_secret()
    assert two_factor.verify(secret, code_at(secret, NOW - timedelta(seconds=30)), None, NOW)
    assert two_factor.verify(secret, code_at(secret, NOW + timedelta(seconds=30)), None, NOW)
    assert two_factor.verify(secret, code_at(secret, NOW - timedelta(minutes=2)), None, NOW) is None


def test_malformed_codes_are_refused() -> None:
    secret = two_factor.new_secret()
    for code in ("", "12345", "1234567", "abcdef"):
        assert two_factor.verify(secret, code, None, NOW) is None
    spaced = code_at(secret, NOW)
    assert two_factor.verify(secret, f"{spaced[:3]} {spaced[3:]}", None, NOW)


def test_the_qr_code_carries_the_provisioning_uri() -> None:
    uri = two_factor.provisioning_uri("JBSWY3DPEHPK3PXP", "ana@example.com")
    assert uri.startswith(
        "otpauth://totp/FinnancialSystem:ana%40example.com?secret=JBSWY3DPEHPK3PXP"
    )
    assert two_factor.qr_svg(uri).startswith("<svg")


def test_recovery_codes() -> None:
    codes = two_factor.new_recovery_codes()
    assert len(codes) == len(set(codes)) == 10
    assert all(len(c) == 11 and c[5] == "-" for c in codes)
    code = codes[0]
    assert two_factor.hash_recovery_code(code) == two_factor.hash_recovery_code(
        " " + code.upper().replace("-", "") + " "
    )
