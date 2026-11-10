"""Receipt files: which types are accepted and how their names are kept.

The type is read from the file's first bytes, never from its name or the browser's
claim, so a renamed executable cannot pass as a PDF.
"""

import unicodedata
from pathlib import PurePath

from app.domain.errors import ValidationError

MAX_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_FILENAME = 200

_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}


def detect_type(head: bytes) -> str | None:
    """MIME type of a receipt from its magic bytes; None when it is not accepted."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def validate(data: bytes) -> str:
    """Check size and type; returns the MIME type."""
    if not data:
        raise ValidationError("The file is empty")
    if len(data) > MAX_SIZE:
        raise ValidationError("The file is larger than 10 MB")
    mime = detect_type(data[:16])
    if mime is None:
        raise ValidationError("Only JPEG, PNG, WebP images and PDF files are accepted")
    return mime


def clean_filename(name: str | None, mime: str) -> str:
    """A safe display name: no folders or control characters, the right extension."""
    base = PurePath((name or "").replace("\\", "/")).name
    base = "".join(c for c in base if unicodedata.category(c)[0] != "C").strip(" .")
    extension = _EXTENSIONS[mime]
    stem = base[: -len(PurePath(base).suffix)] if PurePath(base).suffix else base
    stem = stem[: MAX_FILENAME - len(extension)] or "receipt"
    return stem + extension
