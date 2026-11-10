import pytest

from app.domain.attachments import MAX_SIZE, clean_filename, detect_type, validate
from app.domain.errors import ValidationError

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 10
PDF = b"%PDF-1.7\n" + b"\x00" * 20


@pytest.mark.parametrize(
    ("data", "mime"),
    [
        (JPEG, "image/jpeg"),
        (PNG, "image/png"),
        (WEBP, "image/webp"),
        (PDF, "application/pdf"),
        (b"MZ\x90\x00 an executable", None),
        (b"<html><script>", None),
        (b"RIFF\x00\x00\x00\x00WAVE", None),
    ],
)
def test_the_type_comes_from_the_first_bytes(data: bytes, mime: str | None) -> None:
    assert detect_type(data[:16]) == mime


def test_validate_refuses_empty_large_and_unknown_files() -> None:
    assert validate(PDF) == "application/pdf"
    with pytest.raises(ValidationError, match="empty"):
        validate(b"")
    with pytest.raises(ValidationError, match="10 MB"):
        validate(PDF + b"\x00" * MAX_SIZE)
    with pytest.raises(ValidationError, match="Only JPEG"):
        validate(b"GIF89a" + b"\x00" * 20)


@pytest.mark.parametrize(
    ("name", "mime", "expected"),
    [
        ("Grocery receipt.pdf", "application/pdf", "Grocery receipt.pdf"),
        ("../../etc/passwd", "application/pdf", "passwd.pdf"),
        ("C:\\Users\\me\\scan.jpeg", "image/jpeg", "scan.jpg"),
        ("invoice.exe", "application/pdf", "invoice.pdf"),
        ("bad\x00name\n.png", "image/png", "badname.png"),
        ("", "image/webp", "receipt.webp"),
        (None, "image/png", "receipt.png"),
        ("...", "image/png", "receipt.png"),
        ("é" * 300 + ".pdf", "application/pdf", "é" * 196 + ".pdf"),
    ],
)
def test_filenames_are_cleaned(name: str | None, mime: str, expected: str) -> None:
    assert clean_filename(name, mime) == expected
