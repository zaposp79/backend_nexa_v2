from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ...shared.exceptions import (
    DomainError,
    NotFoundError,
    ValidationError as DomainValidationError,
)
from ...shared.responses import ApiResponse, ErrorDetail
from .request_utils import CORRELATION_ID_HEADER, _safe_headers, _safe_path

logger = logging.getLogger("nexa")


async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    logger.error(
        "[NEXA] correlation_id=%s not found error method=%s path=%s details=%s",
        getattr(request.state, "correlation_id", str(uuid4())),
        request.method,
        _safe_path(request),
        str(exc),
    )
    return JSONResponse(
        status_code=404,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(code="NOT_FOUND", message="Recurso no encontrado."),
        ).model_dump(),
    )


async def handle_domain_validation_error(
    request: Request,
    exc: DomainValidationError,
) -> JSONResponse:
    logger.error(
        "[NEXA] correlation_id=%s validation error method=%s path=%s details=%s",
        getattr(request.state, "correlation_id", str(uuid4())),
        request.method,
        _safe_path(request),
        str(exc),
    )
    return JSONResponse(
        status_code=422,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(code="VALIDATION_ERROR", message="Validación de entrada inválida."),
        ).model_dump(),
    )


async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    logger.error(
        "[NEXA] correlation_id=%s domain error method=%s path=%s headers=%s error=%s",
        getattr(request.state, "correlation_id", str(uuid4())),
        request.method,
        _safe_path(request),
        _safe_headers(request),
        str(exc),
    )
    return JSONResponse(
        status_code=400,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(code="DOMAIN_ERROR", message="Error en la lógica de negocio."),
        ).model_dump(),
    )


async def handle_global_exception(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", str(uuid4()))
    logger.exception(
        "[NEXA] correlation_id=%s unhandled exception method=%s path=%s headers=%s",
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
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="Error inesperado en el servidor.",
            ),
            meta={"correlation_id": correlation_id},
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, handle_not_found)
    app.add_exception_handler(DomainValidationError, handle_domain_validation_error)
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(Exception, handle_global_exception)
