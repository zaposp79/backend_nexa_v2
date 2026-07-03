"""OP Pydantic DTOs."""

from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel


class OPUploadResponse(BaseModel):
    version_id: str
    filename: str
    uploaded_at: str
    sheets_found: List[str]
    total_rows: int
    warnings: List[str]


class OPVersionSummary(BaseModel):
    id: str
    version_id: str
    filename: str
    uploaded_at: str
    is_active: bool
    sheet_count: int
    total_rows: int
    sheets_found: List[str]


class OPSheetPreview(BaseModel):
    name: str
    row_count: int
    columns: List[str]
    sample_rows: List[Dict[str, Any]]
