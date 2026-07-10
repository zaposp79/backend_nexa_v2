"""Shared upload guard utilities used by all parametrization services."""

from __future__ import annotations

import re
from pathlib import Path

from nexa_engine.modules.shared.exceptions import UploadError
from nexa_engine.modules.shared.config.config import ALLOWED_EXCEL_EXTENSIONS, MAX_EXCEL_UPLOAD_BYTES

_SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9._\- ]+$")
_MAX_FILENAME_LEN = 255

# user_id: allow email-style identifiers (letters, digits, . _ @ -)
_SAFE_USER_ID_RE = re.compile(r"^[A-Za-z0-9._@\-]{1,64}$")


def check_filename_prefix(filename: str, expected_prefix: str) -> None:
    """Raise :class:`UploadError` if *filename* does not start with *expected_prefix* (case-insensitive)."""
    stem = Path(filename).name if filename else ""
    if not stem.upper().startswith(expected_prefix.upper()):
        raise UploadError(
            f"El nombre del archivo debe comenzar con '{expected_prefix.upper()}' "
            f"(recibido: '{filename}').",
            code="INVALID_FILENAME_PREFIX",
            sim_code="SIM-00202",
        )


def check_file_extension(filename: str) -> None:
    """Raise :class:`UploadError` if *filename* has a non-allowed extension."""
    ext = Path(filename).suffix.lower() if filename else ""
    allowed = ", ".join(sorted(ALLOWED_EXCEL_EXTENSIONS))
    if ext not in ALLOWED_EXCEL_EXTENSIONS:
        raise UploadError(
            f"Extensión de archivo no permitida ('{ext}'). "
            f"Solo se aceptan: {allowed}.",
            code="INVALID_FILE_EXTENSION",
            sim_code="SIM-00201",
        )


def check_file_size(file_bytes: bytes) -> None:
    """Raise :class:`UploadError` when *file_bytes* exceeds the configured limit."""
    if len(file_bytes) > MAX_EXCEL_UPLOAD_BYTES:
        raise UploadError(
            f"El archivo supera el tamaño máximo permitido de "
            f"{MAX_EXCEL_UPLOAD_BYTES // (1024 * 1024)} MB.",
            code="EXCEL_LIMIT_EXCEEDED",
            sim_code="SIM-00200",
        )


def sanitize_user_id(user_id: str | None) -> str:
    """Return a safe user_id for storage.

    Allows only [A-Za-z0-9._@-], max 64 chars (covers email addresses).
    Falls back to 'anonymous' on empty input or invalid characters.
    """
    if not user_id or not user_id.strip():
        return "anonymous"
    uid = user_id.strip()[:64]
    return uid if _SAFE_USER_ID_RE.match(uid) else "anonymous"


def sanitize_filename(filename: str | None) -> str:
    """Return a safe version of *filename* for storage.

    * Handles ``None`` — falls back to ``"upload.xlsx"``.
    * Strips path components (``/``, ``\\``, ``..``).
    * Truncates to :data:`_MAX_FILENAME_LEN` characters.
    * Replaces characters outside ``[A-Za-z0-9._- ]`` with ``_``.
    * Never returns an empty string.
    """
    if not filename:
        return "upload.xlsx"
    # Remove path separators and traversal sequences
    name = re.sub(r"[\\/]", "_", filename)
    name = name.replace("..", "_")

    # Replace unsafe characters
    name = re.sub(r"[^\w.\- ]", "_", name)

    # Truncate
    if len(name) > _MAX_FILENAME_LEN:
        name = name[:_MAX_FILENAME_LEN]

    return name.strip() or "upload.xlsx"
