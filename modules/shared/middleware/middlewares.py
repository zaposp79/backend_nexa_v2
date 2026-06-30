from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from ..infrastructure.request_utils import (
    CORRELATION_ID_HEADER,
    _correlation_id,
    _safe_headers,
    _safe_path,
)

logger = logging.getLogger("nexa")


async def log_requests(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    correlation_id = _correlation_id(request)
    request.state.correlation_id = correlation_id
    request_started_at = time.monotonic()
    response = await call_next(request)
    elapsed_ms = (time.monotonic() - request_started_at) * 1000
    response.headers[CORRELATION_ID_HEADER] = correlation_id

    log_method = logger.warning if response.status_code >= 400 else logger.info
    log_method(
        "[NEXA] correlation_id=%s %s %s -> %d (%.1fms) headers=%s",
        correlation_id,
        request.method,
        _safe_path(request),
        response.status_code,
        elapsed_ms,
        _safe_headers(request),
    )
    return response


def register_middlewares(app: FastAPI) -> None:
    app.add_middleware(BaseHTTPMiddleware, dispatch=log_requests)
