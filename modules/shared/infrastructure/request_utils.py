from __future__ import annotations

from uuid import uuid4

from fastapi import Request

CORRELATION_ID_HEADER = "X-Correlation-ID"
SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "api-key",
    "apikey",
    "x-auth-token",
}
SENSITIVE_QUERY_MARKERS = (
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "key",
)
REDACTED = "[REDACTED]"


def _correlation_id(request: Request) -> str:
    incoming_correlation_id = request.headers.get(CORRELATION_ID_HEADER)
    return (
        incoming_correlation_id.strip()[:64]
        if incoming_correlation_id and incoming_correlation_id.strip()
        else str(uuid4())
    )


def _safe_headers(request: Request) -> dict[str, str]:
    sanitized_headers: dict[str, str] = {}
    for name, value in request.headers.items():
        if name.lower() in SENSITIVE_HEADER_NAMES:
            sanitized_headers[name] = REDACTED
        else:
            sanitized_headers[name] = value
    return sanitized_headers


def _safe_path(request: Request) -> str:
    if not request.query_params:
        return request.url.path
    sanitized_params = []
    for name, value in request.query_params.multi_items():
        if any(marker in name.lower() for marker in SENSITIVE_QUERY_MARKERS):
            sanitized_params.append(f"{name}={REDACTED}")
        else:
            sanitized_params.append(f"{name}={value}")
    return f"{request.url.path}?{'&'.join(sanitized_params)}"
