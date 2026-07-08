"""GN Pydantic DTOs."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class GNUploadResponse(BaseModel):
    id: str
    domain: str
    pk: str
    version_id: str
    type: str
    status: str
    created_at: str
    file_name: str
    sheet_count: int
    total_rows: int
    user_id: Optional[str]
    sheets_found: List[str]
    payload: Dict[str, Any]
    warnings: List[str]


class GNVersionSummary(BaseModel):
    id: str
    version_id: str
    filename: str
    uploaded_at: str
    is_active: bool
    sheet_count: int
    total_rows: int
    sheets_found: List[str]


class GNSheetPreview(BaseModel):
    name: str
    row_count: int
    columns: List[str]
    sample_rows: List[Dict[str, Any]]
