"""OP Pydantic DTOs."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class OPUploadSummary(BaseModel):
    id: str
    domain: str
    pk: str
    version_id: str
    uploaded_at: str
    filename: str
    sheet_count: int
    total_rows: int
    user_id: Optional[str]
    is_active: bool
    sheets_found: List[str]
    warnings: List[str]


class OPUploadResponse(BaseModel):
    summary: OPUploadSummary
    payload: Dict[str, Any]


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
