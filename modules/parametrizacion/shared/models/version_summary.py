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
        display_version_id: Optional[str] = None,
        sheets_found: Optional[list] = None,
    ):
        self.version_id = version_id        # Internal UUID — used as document key
        self.filename = filename
        self.uploaded_at = uploaded_at
        self.is_active = is_active
        self.sheet_count = sheet_count
        self.total_rows = total_rows
        self.path = path
        self.display_version_id = display_version_id  # Human-readable "2026-07-02 07:44:53"
        self.sheets_found: list = sheets_found or []

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
        if self.display_version_id is not None:
            d["display_version_id"] = self.display_version_id
        if self.sheets_found:
            d["sheets_found"] = self.sheets_found
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
            display_version_id=d.get("display_version_id"),
            sheets_found=d.get("sheets_found", []),
        )


# ---------------------------------------------------------------------------
# Storage constants (moved from base_repository.py in FASE DB.6.5)
# ---------------------------------------------------------------------------

VERSIONS_FILE = "versions.json"
