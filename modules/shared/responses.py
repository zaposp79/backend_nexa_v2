"""Standard API response wrapper for the NEXA simulator."""

from typing import Any, Dict, Generic, Optional, TypeVar, Union
from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str           # SIM-XXXXX
    type: str           # VALIDATION_ERROR, DOMAIN_ERROR, etc.
    message: str
    field: Optional[str] = None
    details: Optional[Union[Dict[str, Any], list]] = None


class ApiResponse(BaseModel, Generic[T]):
    """Generic wrapper returned by all API endpoints."""

    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None
    meta: Optional[dict] = None

    @classmethod
    def ok(cls, data: T, meta: Optional[dict] = None) -> "ApiResponse[T]":
        return cls(success=True, data=data, meta=meta)

    @classmethod
    def fail(
        cls,
        sim_code: str,
        message: str | None = None,
        field: Optional[str] = None,
        details: Optional[list] = None,
    ) -> "ApiResponse":
        from nexa_engine.modules.shared.error_catalog import make_detail
        return cls(success=False, error=make_detail(sim_code, message=message, field=field, details=details))
