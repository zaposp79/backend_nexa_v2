from __future__ import annotations

import collections
import json
import logging
import os
import time
from uuid import uuid4

from fastapi import FastAPI
from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from ..infrastructure.request_utils import (
    CORRELATION_ID_HEADER,
    SENSITIVE_HEADER_NAMES,
    SENSITIVE_QUERY_MARKERS,
    REDACTED,
)

logger = logging.getLogger("nexa")

# ---------------------------------------------------------------------------
# Rate-limiter configuration (env-configurable)
# Structured as {path_suffix: (limit, window_seconds)}.
# Upload endpoints: lower limit — Excel processing is CPU/memory-intensive.
# Calculate endpoint: moderate limit — 10-layer engine is computationally heavy.
# ---------------------------------------------------------------------------
_RATE_LIMIT_RULES: dict[str, tuple[int, int]] = {
    "/upload": (
        int(os.getenv("UPLOAD_RATE_LIMIT", "20")),
        int(os.getenv("UPLOAD_RATE_WINDOW", "60")),
    ),
    "/calculate": (
        int(os.getenv("CALC_RATE_LIMIT", "30")),
        int(os.getenv("CALC_RATE_WINDOW", "60")),
    ),
}


class RequestLoggingMiddleware:
    """Pure ASGI middleware for request logging and correlation ID injection.

    Unlike BaseHTTPMiddleware, this does NOT use call_next() so exceptions
    raised inside route handlers propagate naturally through Starlette's
    ExceptionMiddleware instead of being re-raised from call_next() and
    hitting ServerErrorMiddleware (500) before the typed handlers run.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        # Extract or generate correlation ID
        raw_cid = request.headers.get(CORRELATION_ID_HEADER, "").strip()
        correlation_id = raw_cid[:64] if raw_cid else str(uuid4())

        # Make correlation_id available to route handlers via request.state
        request.state.correlation_id = correlation_id

        started_at = time.monotonic()
        status_code_holder: list[int] = [500]

        _path = scope.get("path", "")
        _is_docs_path = _path in ("/docs", "/redoc") or _path.startswith("/static/swagger-ui/")

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                status_code_holder[0] = message["status"]
                headers = MutableHeaders(scope=message)
                headers.append(CORRELATION_ID_HEADER, correlation_id)
                # Defence-in-depth security headers (also enforced at nginx/CDN level)
                headers.append("X-Content-Type-Options", "nosniff")
                headers.append("X-Frame-Options", "DENY")
                headers.append("Referrer-Policy", "no-referrer")
                if _is_docs_path:
                    # Swagger UI requires scripts, styles and images from 'self' + inline scripts
                    headers.append(
                        "Content-Security-Policy",
                        "default-src 'self'; "
                        "script-src 'self' 'unsafe-inline'; "
                        "style-src 'self' 'unsafe-inline'; "
                        "img-src 'self' data:; "
                        "connect-src 'self'; "
                        "worker-src blob:;",
                    )
                else:
                    headers.append("Content-Security-Policy", "default-src 'none'")
                headers.append("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
                headers.append("Cache-Control", "no-store")
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = (time.monotonic() - started_at) * 1000
            status = status_code_holder[0]
            log_fn = logger.warning if status >= 400 else logger.info
            log_fn(
                "[NEXA] correlation_id=%s %s %s -> %d (%.1fms)",
                correlation_id,
                scope.get("method", ""),
                _safe_scope_path(scope),
                status,
                elapsed_ms,
            )


class EndpointRateLimitMiddleware:
    """Per-IP sliding-window rate limiter for specific POST endpoints.

    Applies rules from _RATE_LIMIT_RULES: {path_suffix → (limit, window_seconds)}.
    Each path suffix is tracked independently so a single IP cannot starve
    /calculate by consuming the /upload budget, or vice-versa.

    Limitations:
    - In-memory only — does not share state across multiple worker processes.
      For production multi-worker deployments, replace with a Redis-backed limiter.
    - X-Forwarded-For trust: the leftmost IP is used as the client identifier.
      This can be spoofed if the app is reached directly (not through a trusted
      reverse proxy). Ensure your proxy strips untrusted XFF headers before
      forwarding.
    """

    def __init__(self, app: ASGIApp, rules: dict[str, tuple[int, int]] = _RATE_LIMIT_RULES) -> None:
        self.app = app
        self.rules = rules
        # Per path-suffix, per IP → deque of request timestamps
        self._buckets: dict[str, dict[str, collections.deque]] = {p: {} for p in rules}

    def _client_ip(self, scope: Scope) -> str:
        headers = dict(scope.get("headers", []))
        xff = headers.get(b"x-forwarded-for", b"").decode("latin-1")
        if xff:
            return xff.split(",")[0].strip()
        client = scope.get("client")
        return client[0] if client else "unknown"

    def _match_rule(self, scope: Scope) -> tuple[str, int, int] | None:
        """Return (path_suffix, limit, window) if request matches a rule, else None."""
        if scope["type"] != "http" or scope.get("method", "").upper() != "POST":
            return None
        path = scope.get("path", "")
        for suffix, (limit, window) in self.rules.items():
            if path.endswith(suffix):
                return suffix, limit, window
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        matched = self._match_rule(scope)
        if matched is None:
            await self.app(scope, receive, send)
            return

        suffix, limit, window = matched
        ip = self._client_ip(scope)
        now = time.monotonic()

        bucket = self._buckets[suffix].setdefault(ip, collections.deque())
        while bucket and now - bucket[0] > window:
            bucket.popleft()

        if len(bucket) >= limit:
            logger.warning(
                "[NEXA] rate_limit_exceeded ip=%s path=%s limit=%d window=%ds",
                ip, scope.get("path", ""), limit, window,
            )
            body = json.dumps({
                "success": False,
                "data": None,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Demasiadas solicitudes. Límite: {limit} por {window} segundos.",
                    "field": None,
                    "details": None,
                },
                "meta": None,
            }).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"retry-after", str(window).encode()),
                ],
            })
            await send({"type": "http.response.body", "body": body, "more_body": False})
            return

        bucket.append(now)
        await self.app(scope, receive, send)


# Backward-compat alias
UploadRateLimitMiddleware = EndpointRateLimitMiddleware


def _safe_scope_path(scope: Scope) -> str:
    path = scope.get("path", "")
    raw_qs = scope.get("query_string", b"")
    if not raw_qs:
        return path
    pairs = []
    for part in raw_qs.decode("latin-1").split("&"):
        if "=" in part:
            name, _, value = part.partition("=")
            if any(m in name.lower() for m in SENSITIVE_QUERY_MARKERS):
                pairs.append(f"{name}={REDACTED}")
            else:
                pairs.append(f"{name}={value}")
        else:
            pairs.append(part)
    return f"{path}?{'&'.join(pairs)}"


def register_middlewares(app: FastAPI) -> None:
    # Registration order matters: last added = outermost layer.
    # Stack: RequestLoggingMiddleware → EndpointRateLimitMiddleware → CORSMiddleware → routes
    # 429 responses from the rate limiter are therefore captured and logged by
    # RequestLoggingMiddleware before being sent to the client.
    app.add_middleware(EndpointRateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
