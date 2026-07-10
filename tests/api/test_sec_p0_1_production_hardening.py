from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from nexa_engine.app import create_app
from nexa_engine.db.exceptions import DbConfigurationError
from nexa_engine.modules.shared.config.app_settings import (
    APP_ENV_PRODUCTION,
    AppSettings,
    ENV_APP_ENV,
    ENV_APP_RELOAD,
    ENV_CORS_ALLOWED_ORIGINS,
    load_app_settings,
)
from nexa_engine.modules.shared.infrastructure.request_utils import CORRELATION_ID_HEADER


def _production_settings(origin: str = "https://app.nexa.example") -> AppSettings:
    return AppSettings(
        app_env=APP_ENV_PRODUCTION,
        cors_allowed_origins=(origin,),
        docs_enabled=False,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


def test_production_cors_allows_configured_origin_and_rejects_unknown_origin():
    client = TestClient(create_app(_production_settings()))

    allowed = client.get("/health", headers={"Origin": "https://app.nexa.example"})
    rejected = client.get("/health", headers={"Origin": "https://evil.example"})

    assert allowed.headers["access-control-allow-origin"] == "https://app.nexa.example"
    assert "access-control-allow-origin" not in rejected.headers


def test_production_rejects_missing_or_open_cors_configuration():
    with pytest.raises(DbConfigurationError):
        load_app_settings({ENV_APP_ENV: APP_ENV_PRODUCTION})

    with pytest.raises(DbConfigurationError):
        load_app_settings({
            ENV_APP_ENV: APP_ENV_PRODUCTION,
            ENV_CORS_ALLOWED_ORIGINS: "*",
        })


def test_production_rejects_reload():
    with pytest.raises(DbConfigurationError):
        load_app_settings({
            ENV_APP_ENV: APP_ENV_PRODUCTION,
            ENV_CORS_ALLOWED_ORIGINS: "https://app.nexa.example",
            ENV_APP_RELOAD: "true",
        })


def test_docs_redoc_and_openapi_are_disabled_in_production():
    client = TestClient(create_app(_production_settings()))

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_500_response_does_not_expose_internal_details():
    app = create_app(_production_settings())

    @app.get("/boom")
    def boom():
        raise RuntimeError("internal-secret-path /tmp/nexa")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")
    body = response.json()

    assert response.status_code == 500
    assert body["error"]["code"] == "SIM-00900"
    assert body["error"]["type"] == "INTERNAL_SERVER_ERROR"
    assert body["error"]["message"] == "Se produjo un error inesperado en el servidor que no pudo ser manejado."
    rendered = str(body)
    assert "internal-secret-path" not in rendered
    assert "RuntimeError" not in rendered
    assert "/tmp/nexa" not in rendered
    assert response.headers[CORRELATION_ID_HEADER]


def test_logs_redact_sensitive_headers_and_query_params(caplog):
    app = create_app(_production_settings())

    @app.get("/boom")
    def boom():
        raise RuntimeError("detalle permitido solo en logs")

    client = TestClient(app, raise_server_exceptions=False)
    caplog.set_level(logging.ERROR, logger="nexa")

    client.get(
        "/boom?token=query-secret&visible=ok",
        headers={
            "Authorization": "Bearer header-secret",
            "Cookie": "session=cookie-secret",
            "X-Api-Key": "api-key-secret",
            CORRELATION_ID_HEADER: "cid-test",
        },
    )

    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "header-secret" not in logs
    assert "cookie-secret" not in logs
    assert "api-key-secret" not in logs
    assert "query-secret" not in logs
    assert "token=[REDACTED]" in logs
    assert "cid-test" in logs


def test_each_request_has_correlation_id_and_health_remains_available():
    client = TestClient(create_app(_production_settings()))

    generated = client.get("/health")
    provided = client.get("/health", headers={CORRELATION_ID_HEADER: "external-cid"})

    assert generated.status_code == 200
    assert generated.json() == {"status": "ok", "service": "nexa-simulator-api"}
    assert generated.headers[CORRELATION_ID_HEADER]
    assert provided.headers[CORRELATION_ID_HEADER] == "external-cid"
