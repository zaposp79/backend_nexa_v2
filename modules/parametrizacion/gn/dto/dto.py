"""GN Pydantic DTOs."""

from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel


class GNUploadResponse(BaseModel):
    version_id: str
    filename: str
    uploaded_at: str
    sheets_found: List[str]
    total_rows: int
    warnings: List[str]


class GNVersionSummary(BaseModel):
    version_id: str
    filename: str
    uploaded_at: str
    is_active: bool
    sheet_count: int
    total_rows: int


class GNSheetPreview(BaseModel):
    name: str
    row_count: int
    columns: List[str]
    sample_rows: List[Dict[str, Any]]
