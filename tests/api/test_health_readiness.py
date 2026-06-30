"""
Focused tests for /health (liveness) and /health/ready (readiness).

Verifies:
1. /health returns 200 always (liveness).
2. /health/ready returns 200 when the configured store ping() succeeds.
3. /health/ready returns 503 with a safe response when ping() fails.
4. /health/ready response never exposes raw exception strings, class names,
   module names, tracebacks, secrets, or connection strings.
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from nexa_engine.app import create_app
from nexa_engine.modules.shared.config.app_settings import (
    APP_ENV_TEST,
    AppSettings,
    TEST_CORS_ORIGINS,
)


def _test_settings() -> AppSettings:
    return AppSettings(
        app_env=APP_ENV_TEST,
        cors_allowed_origins=TEST_CORS_ORIGINS,
        docs_enabled=True,
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


@contextmanager
def _client_ctx(ping_side_effect=None):
    """Context manager that yields a TestClient with a controlled store.ping()."""
    mock_store = MagicMock()
    if ping_side_effect is None:
        mock_store.ping.return_value = None
    else:
        mock_store.ping.side_effect = ping_side_effect

    mock_container = MagicMock()
    mock_container.store = mock_store

    # Keep patch active while the TestClient lifespan runs.
    with patch(
        "nexa_engine.modules.shared.infrastructure.lifespan.build_container",
        return_value=mock_container,
    ):
        app = create_app(settings=_test_settings())
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client


@pytest.fixture()
def client_with_healthy_store():
    """TestClient with a mock store whose ping() succeeds."""
    with _client_ctx() as client:
        yield client


@pytest.fixture()
def client_with_unhealthy_store():
    """TestClient with a mock store whose ping() raises."""
    with _client_ctx(
        ping_side_effect=Exception("cosmos://nexa-prod.documents.azure.com/SECRET_KEY_HERE timeout")
    ) as client:
        yield client


# ─────────────────────────────────────────────────────────────────────────────
# /health — liveness
# ─────────────────────────────────────────────────────────────────────────────

class TestLiveness:

    def test_health_returns_200(self, client_with_healthy_store):
        resp = client_with_healthy_store.get("/health")
        assert resp.status_code == 200

    def test_health_returns_ok_status(self, client_with_healthy_store):
        resp = client_with_healthy_store.get("/health")
        assert resp.json()["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# /health/ready — readiness
# ─────────────────────────────────────────────────────────────────────────────

class TestReadinessHealthy:

    def test_ready_returns_200_when_store_healthy(self, client_with_healthy_store):
        resp = client_with_healthy_store.get("/health/ready")
        assert resp.status_code == 200

    def test_ready_body_status_is_ready(self, client_with_healthy_store):
        resp = client_with_healthy_store.get("/health/ready")
        assert resp.json() == {"status": "ready"}


class TestReadinessUnhealthy:

    def test_ready_returns_503_when_store_fails(self, client_with_unhealthy_store):
        resp = client_with_unhealthy_store.get("/health/ready")
        assert resp.status_code == 503

    def test_ready_body_has_safe_status(self, client_with_unhealthy_store):
        body = client_with_unhealthy_store.get("/health/ready").json()
        assert body["status"] == "not_ready"
        assert body["reason"] == "storage_unavailable"

    def test_ready_does_not_expose_raw_exception(self, client_with_unhealthy_store):
        """Response must not leak raw exception strings."""
        body_text = client_with_unhealthy_store.get("/health/ready").text
        assert "cosmos://" not in body_text
        assert "SECRET_KEY_HERE" not in body_text
        assert "timeout" not in body_text

    def test_ready_does_not_expose_class_names(self, client_with_unhealthy_store):
        """Response must not expose internal class names or module paths."""
        body_text = client_with_unhealthy_store.get("/health/ready").text
        assert "CosmosDocumentStore" not in body_text
        assert "JsonDocumentStore" not in body_text
        assert "nexa_engine" not in body_text
        assert "traceback" not in body_text.lower()

    def test_ready_does_not_expose_traceback(self, client_with_unhealthy_store):
        """No traceback or stack trace in the response."""
        body_text = client_with_unhealthy_store.get("/health/ready").text
        assert "Traceback" not in body_text
        assert "File " not in body_text
        assert "line " not in body_text
