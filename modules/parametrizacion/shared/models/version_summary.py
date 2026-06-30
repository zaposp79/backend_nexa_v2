"""Version metadata for parametrization uploads.

Extracted from ``shared/infrastructure/storage/base_repository.py`` in
FASE DB.6.5 (2026-06-04) — all consumers were exclusively in parametrizacion.
"""

from __future__ import annotations

from typing import Optional


class VersionSummary:
    """Lightweight metadata about a stored parametrization version."""

    def __init__(
        self,
        version_id: str,
        filename: str,
        uploaded_at: str,
        is_active: bool,
        sheet_count: int,
        total_rows: int,
        path: Optional[str] = None,
    ):
        self.version_id = version_id
        self.filename = filename
        self.uploaded_at = uploaded_at
        self.is_active = is_active
        self.sheet_count = sheet_count
        self.total_rows = total_rows
        self.path = path

    def to_dict(self) -> dict:
        d = {
            "version_id": self.version_id,
            "filename": self.filename,
            "uploaded_at": self.uploaded_at,
            "is_active": self.is_active,
            "sheet_count": self.sheet_count,
            "total_rows": self.total_rows,
        }
        if self.path is not None:
            d["path"] = self.path
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "VersionSummary":
        return cls(
            version_id=d["version_id"],
            filename=d["filename"],
            uploaded_at=d["uploaded_at"],
            is_active=d.get("is_active", False),
            sheet_count=d.get("sheet_count", 0),
            total_rows=d.get("total_rows", 0),
            path=d.get("path"),
        )


# ---------------------------------------------------------------------------
# Storage constants (moved from base_repository.py in FASE DB.6.5)
# ---------------------------------------------------------------------------

VERSIONS_FILE = "versions.json"
