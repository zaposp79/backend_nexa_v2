"""Shared upload guard utilities used by all parametrization services."""

from __future__ import annotations

import re

from nexa_engine.modules.shared.exceptions import UploadError
from nexa_engine.modules.shared.config.config import MAX_EXCEL_UPLOAD_BYTES

_SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9._\- ]+$")
_MAX_FILENAME_LEN = 255


def check_file_size(file_bytes: bytes) -> None:
    """Raise :class:`UploadError` when *file_bytes* exceeds the configured limit."""
    if len(file_bytes) > MAX_EXCEL_UPLOAD_BYTES:
        raise UploadError(
            f"El archivo supera el tamaño máximo permitido de "
            f"{MAX_EXCEL_UPLOAD_BYTES // (1024 * 1024)} MB.",
            code="EXCEL_LIMIT_EXCEEDED",
        )


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
