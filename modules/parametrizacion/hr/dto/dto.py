"""HR Pydantic DTOs for API input/output."""

from __future__ import annotations
from typing import Dict, List
from pydantic import BaseModel


class HRUploadResponse(BaseModel):
    version_id: str
    filename: str
    uploaded_at: str
    sheets_found: List[str]
    sheets_missing: List[str]
    row_counts: Dict[str, int]
    warnings: List[str]


class HRVersionSummary(BaseModel):
    version_id: str
    filename: str
    uploaded_at: str
    is_active: bool
    sheet_count: int
    total_rows: int
