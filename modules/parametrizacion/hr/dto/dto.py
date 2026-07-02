"""HR Pydantic DTOs for API input/output."""

from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel


class HRUploadSummary(BaseModel):
    """Summary metadata returned after a successful HR upload."""
    version_id: str
    filename: str
    uploaded_at: str
    is_active: bool
    sheet_count: int
    total_rows: int
    user_id: str
    id: str
    sheets_found: List[str]
    sheets_missing: List[str]
    row_counts: Dict[str, int]
    warnings: List[str]


class HRUploadResult(BaseModel):
    """Full response for POST /parametrization/hr/upload."""
    summary: HRUploadSummary
    payload: Dict[str, Any]


class HRVersionSummary(BaseModel):
    """Compact version metadata for list/activate endpoints."""
    version_id: str
    filename: str
    uploaded_at: str
    is_active: bool
    sheet_count: int
    total_rows: int
