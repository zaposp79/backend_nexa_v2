from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from nexa_engine.modules.shared.exceptions import (
    DomainError,
    NotFoundError,
    StorageError,
    UploadError,
    ValidationError as DomainValidationError,
)
from ...shared.responses import ApiResponse, ErrorDetail
from ...shared.error_catalog import make_detail as _make_detail
from .request_utils import CORRELATION_ID_HEADER, _safe_headers, _safe_path

logger = logging.getLogger("nexa")

# HTTP status code per UploadError.code
_UPLOAD_STATUS: dict[str, int] = {
    "INVALID_FILENAME_PREFIX": 422,
    "INVALID_FILE_EXTENSION":  422,
    "EXCEL_LIMIT_EXCEEDED":    413,
    "INVALID_EXCEL_FILE":      422,
    "ENCRYPTED_EXCEL_FILE":    422,
    "UNSAFE_EXCEL_CONTENT":    422,
    "VIRUS_DETECTED":          422,
    "UPLOAD_ERROR":            400,
}


async def handle_upload_error(request: Request, exc: UploadError) -> JSONResponse:
    status = _UPLOAD_STATUS.get(exc.code, 422)
    logger.warning(
        "[NEXA] upload rejected code=%s status=%s method=%s path=%s",
        exc.code,
        status,
        request.method,
        _safe_path(request),
    )
    return JSONResponse(
        status_code=status,
        content=ApiResponse(
            success=False,
            error=_make_detail(getattr(exc, "sim_code", "SIM-00700"), message=exc.message),
        ).model_dump(),
    )


async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    logger.warning(
        "[NEXA] not found method=%s path=%s details=%s",
        request.method,
        _safe_path(request),
        str(exc),
    )
    return JSONResponse(
        status_code=404,
        content=ApiResponse(
            success=False,
            error=_make_detail(getattr(exc, "sim_code", "SIM-00600"), message=str(exc)),
        ).model_dump(),
    )


async def handle_domain_validation_error(
    request: Request,
    exc: DomainValidationError,
) -> JSONResponse:
    logger.warning(
        "[NEXA] validation error method=%s path=%s message=%s",
        request.method,
        _safe_path(request),
        exc.message,
    )
    return JSONResponse(
        status_code=422,
        content=ApiResponse(
            success=False,
            error=_make_detail(getattr(exc, "sim_code", "SIM-00506"), message=exc.message, details=exc.errors if exc.errors else None),
        ).model_dump(),
    )


async def handle_storage_error(request: Request, exc: StorageError) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", str(uuid4()))
    logger.error(
        "[NEXA] storage error correlation_id=%s method=%s path=%s error=%s",
        correlation_id,
        request.method,
        _safe_path(request),
        exc.message,
    )
    return JSONResponse(
        status_code=500,
        headers={CORRELATION_ID_HEADER: correlation_id},
        content=ApiResponse(
            success=False,
            error=_make_detail("SIM-00900", message="Error de almacenamiento interno. Intenta de nuevo."),
            meta={"correlation_id": correlation_id},
        ).model_dump(),
    )


async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    logger.error(
        "[NEXA] domain error method=%s path=%s headers=%s error=%s",
        request.method,
        _safe_path(request),
        _safe_headers(request),
        str(exc),
    )
    return JSONResponse(
        status_code=400,
        content=ApiResponse(
            success=False,
            error=_make_detail(getattr(exc, "sim_code", "SIM-00700"), message=str(exc)),
        ).model_dump(),
    )


async def handle_global_exception(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", str(uuid4()))
    logger.exception(
        "[NEXA] unhandled exception correlation_id=%s method=%s path=%s headers=%s",
        correlation_id,
        request.method,
        _safe_path(request),
        _safe_headers(request),
    )
    return JSONResponse(
        status_code=500,
        headers={CORRELATION_ID_HEADER: correlation_id},
        content=ApiResponse(
            success=False,
            error=_make_detail("SIM-00900"),
            meta={"correlation_id": correlation_id},
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    # Specific subclasses must be registered so their MRO is checked first.
    app.add_exception_handler(UploadError, handle_upload_error)
    app.add_exception_handler(StorageError, handle_storage_error)
    app.add_exception_handler(NotFoundError, handle_not_found)
    app.add_exception_handler(DomainValidationError, handle_domain_validation_error)
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(Exception, handle_global_exception)
