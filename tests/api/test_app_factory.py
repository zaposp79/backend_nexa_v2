"""Tests: application factory correctness.

Verifica los criterios de aceptación del patrón factory:
  1. Importar backend_nexa_v2.app no ejecuta load_app_settings().
  2. Importar backend_nexa_v2.app no construye una instancia FastAPI.
  3. create_app(settings=...) usa exactamente los settings inyectados.
  4. create_app() sin args lee os.environ en el momento de la llamada.
  5. monkeypatch antes de create_app() tiene efecto.
  6. Dos instancias del mismo proceso pueden usar configs distintas.
  7. CORS corresponde a los settings usados para construir cada instancia.
  8. El lifespan construye el contenedor al arrancar, no al importar.
  9. DB_PROVIDER=json funciona sin credenciales Cosmos.
 10. DB_PROVIDER=cosmos falla claramente si faltan credenciales.
 11. Ningún secreto aparece en mensajes de error o logs.
 12. Rutas, contratos HTTP y respuestas existentes no se alteran.
"""
from __future__ import annotations

import dataclasses
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from nexa_engine.db.exceptions import DbConfigurationError
from nexa_engine.db.factory import reset_provider
from nexa_engine.modules.shared.config.app_settings import (
    APP_ENV_DEVELOPMENT,
    APP_ENV_PRODUCTION,
    AppSettings,
    load_app_settings,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEV_BASE = AppSettings(
    app_env=APP_ENV_DEVELOPMENT,
    cors_allowed_origins=("http://localhost:3000",),
    docs_enabled=True,
    host="127.0.0.1",
    port=8000,
    reload=False,
)

_PROD_BASE = AppSettings(
    app_env=APP_ENV_PRODUCTION,
    cors_allowed_origins=("https://app.nexa.io",),
    docs_enabled=False,
    host="0.0.0.0",
    port=8000,
    reload=False,
)


def _dev(**overrides) -> AppSettings:
    return dataclasses.replace(_DEV_BASE, **overrides)


def _prod(**overrides) -> AppSettings:
    return dataclasses.replace(_PROD_BASE, **overrides)


# ---------------------------------------------------------------------------
# 1 + 2. Importar app.py no ejecuta load_app_settings() ni construye FastAPI
# ---------------------------------------------------------------------------

def test_importing_app_module_does_not_call_load_app_settings():
    """Importing backend_nexa_v2.app must NOT call load_app_settings() at module level.

    Uses the canonical module path (backend_nexa_v2.app), not the runtime alias,
    because reload subprocesses start with an empty sys.modules and must be
    able to import the module without prior alias registration.
    """
    import nexa_engine.modules.shared.config.app_settings as _settings_mod
    orig = _settings_mod.load_app_settings
    calls = []

    def spy(*a, **kw):
        calls.append(1)
        return orig(*a, **kw)

    _settings_mod.load_app_settings = spy
    try:
        # Remove the canonical module to force a fresh import
        for key in list(sys.modules):
            if key in ("backend_nexa_v2.app", "nexa_engine.app"):
                del sys.modules[key]

        import backend_nexa_v2.app as _  # noqa: F401 — canonical import
    finally:
        _settings_mod.load_app_settings = orig

    assert len(calls) == 0, (
        f"load_app_settings() was called {len(calls)} time(s) during import of "
        "backend_nexa_v2.app — module-level side effects detected."
    )


def test_importing_app_module_does_not_expose_global_app_instance():
    """backend_nexa_v2.app must not have a module-level 'app' variable."""
    import backend_nexa_v2.app as app_mod

    assert not hasattr(app_mod, "app"), (
        "backend_nexa_v2.app exposes a module-level 'app' instance. "
        "Importing should be side-effect free — call create_app() explicitly."
    )


# ---------------------------------------------------------------------------
# 3. create_app(settings=...) usa exactamente los settings inyectados
# ---------------------------------------------------------------------------

def test_create_app_uses_injected_settings():
    from nexa_engine.app import create_app

    s = _dev()
    fastapi_app = create_app(settings=s)

    assert fastapi_app.state.settings is s
    assert fastapi_app.state.settings.app_env == APP_ENV_DEVELOPMENT


def test_create_app_uses_injected_http_surface_settings():
    from nexa_engine.app import create_app

    fastapi_app = create_app(settings=_dev(
        app_title="Injected NEXA",
        api_prefix="custom",
        api_version="v9",
        health_path="/ready",
        service_name="custom-service",
    ))

    assert fastapi_app.title == "Injected NEXA"
    assert any(route.path.startswith("/custom/v9") for route in fastapi_app.routes)

    client = TestClient(fastapi_app)
    assert client.get("/ready").json() == {
        "status": "ok",
        "service": "custom-service",
    }


def test_create_app_injected_production_settings_disables_docs():
    from nexa_engine.app import create_app

    fastapi_app = create_app(settings=_prod())

    assert fastapi_app.docs_url is None
    assert fastapi_app.redoc_url is None
    assert fastapi_app.openapi_url is None


# ---------------------------------------------------------------------------
# 4 + 5. create_app() sin args lee os.environ; monkeypatch tiene efecto
# ---------------------------------------------------------------------------

def test_create_app_without_args_reads_env_at_call_time(monkeypatch):
    """create_app() with no args should read os.environ at the time of the call."""
    monkeypatch.setenv("APP_ENV", "test")
    from nexa_engine.app import create_app

    fastapi_app = create_app()
    assert fastapi_app.state.settings.app_env == "test"


def test_monkeypatch_before_create_app_has_effect(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("APP_PORT", "9876")
    from nexa_engine.app import create_app

    fastapi_app = create_app()
    assert fastapi_app.state.settings.port == 9876


# ---------------------------------------------------------------------------
# 6. Dos instancias con configs distintas en el mismo proceso
# ---------------------------------------------------------------------------

def test_two_instances_with_different_configs_in_same_process():
    from nexa_engine.app import create_app

    dev = create_app(settings=_dev())
    prod = create_app(settings=_prod())

    assert dev.state.settings.app_env == APP_ENV_DEVELOPMENT
    assert prod.state.settings.app_env == APP_ENV_PRODUCTION
    assert dev.state.settings is not prod.state.settings
    assert dev is not prod


# ---------------------------------------------------------------------------
# 7. CORS corresponde a los settings de cada instancia
# ---------------------------------------------------------------------------

def test_cors_uses_settings_from_each_instance():
    from nexa_engine.app import create_app

    dev_app = create_app(settings=_dev(cors_allowed_origins=("http://dev.nexa.io",)))
    prod_app = create_app(settings=_prod(cors_allowed_origins=("https://prod.nexa.io",)))

    dev_client = TestClient(dev_app)
    prod_client = TestClient(prod_app)

    dev_resp = dev_client.get("/health", headers={"Origin": "http://dev.nexa.io"})
    prod_resp = prod_client.get("/health", headers={"Origin": "https://prod.nexa.io"})

    assert dev_resp.headers.get("access-control-allow-origin") == "http://dev.nexa.io"
    assert prod_resp.headers.get("access-control-allow-origin") == "https://prod.nexa.io"


def test_cors_from_instance_a_does_not_bleed_into_instance_b():
    from nexa_engine.app import create_app

    app_a = create_app(settings=_dev(cors_allowed_origins=("http://a.example",)))
    app_b = create_app(settings=_dev(cors_allowed_origins=("http://b.example",)))

    client_a = TestClient(app_a)
    client_b = TestClient(app_b)

    resp = client_a.get("/health", headers={"Origin": "http://b.example"})
    assert resp.headers.get("access-control-allow-origin") != "http://b.example", (
        "Origin from app_b leaked into app_a CORS"
    )


# ---------------------------------------------------------------------------
# 8. Lifespan construye el contenedor al arrancar, no al importar
# ---------------------------------------------------------------------------

def test_lifespan_builds_container_on_startup_not_on_import():
    """The DB container must only exist after lifespan startup."""
    from nexa_engine.app import create_app

    fastapi_app = create_app(settings=_dev())

    # Before starting the client (before lifespan), state.container must not exist.
    assert not hasattr(fastapi_app.state, "container"), (
        "container is set before lifespan startup — build_container() is being "
        "called at import time or in create_app() body instead of in lifespan."
    )

    # After starting the TestClient (triggers lifespan), container must be available.
    with TestClient(fastapi_app) as client:
        assert hasattr(fastapi_app.state, "container")
        assert fastapi_app.state.container is not None


# ---------------------------------------------------------------------------
# 9. DB_PROVIDER=json sin credenciales Cosmos
# ---------------------------------------------------------------------------

def test_json_backend_starts_without_cosmos(monkeypatch):
    monkeypatch.setenv("DB_PROVIDER", "json")
    monkeypatch.delenv("COSMOS_ENDPOINT", raising=False)
    monkeypatch.delenv("COSMOS_KEY", raising=False)
    from nexa_engine.app import create_app

    fastapi_app = create_app(settings=_dev())
    with TestClient(fastapi_app) as client:
        assert client.get("/health").status_code == 200


# ---------------------------------------------------------------------------
# 10. DB_PROVIDER=cosmos falla si faltan credenciales
# ---------------------------------------------------------------------------

def test_cosmos_without_credentials_fails_at_container_build(monkeypatch):
    monkeypatch.setenv("DB_PROVIDER", "cosmos")
    monkeypatch.delenv("COSMOS_ENDPOINT", raising=False)
    monkeypatch.delenv("COSMOS_KEY", raising=False)
    # Reset provider cache so get_provider() reads DB_PROVIDER from env again
    reset_provider()
    from nexa_engine.app import create_app

    # create_app itself succeeds (settings-only); the failure happens in lifespan
    # when build_container() calls get_provider() → load_config(DB_PROVIDER=cosmos)
    # which requires COSMOS_ENDPOINT and COSMOS_KEY.
    fastapi_app = create_app(settings=_dev())
    with pytest.raises(DbConfigurationError):
        with TestClient(fastapi_app, raise_server_exceptions=True):
            pass
    # Always restore JSON backend after this test to avoid polluting the cache.
    reset_provider()


# ---------------------------------------------------------------------------
# 11. Secretos no aparecen en mensajes de error o logs
# ---------------------------------------------------------------------------

def test_missing_cosmos_key_error_does_not_expose_secret_values(monkeypatch):
    monkeypatch.setenv("DB_PROVIDER", "cosmos")
    monkeypatch.setenv("COSMOS_ENDPOINT", "https://secret-account.documents.azure.com")
    monkeypatch.delenv("COSMOS_KEY", raising=False)

    from nexa_engine.db.config import load_config
    with pytest.raises(DbConfigurationError) as exc_info:
        load_config({
            "DB_PROVIDER": "cosmos",
            "COSMOS_ENDPOINT": "https://secret-account.documents.azure.com",
        })
    msg = str(exc_info.value)
    assert "COSMOS_KEY" in msg              # variable name — OK to show
    assert "secret-account" not in msg     # endpoint value — must NOT appear


# ---------------------------------------------------------------------------
# 12. Rutas y contratos no se alteran
# ---------------------------------------------------------------------------

def test_health_endpoint_contract_unchanged():
    from nexa_engine.app import create_app

    with TestClient(create_app(settings=_dev())) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "nexa-simulator-api"


def test_api_v1_prefix_is_registered():
    from nexa_engine.app import create_app

    fastapi_app = create_app(settings=_dev())
    routes = [r.path for r in fastapi_app.routes]
    assert any(r.startswith("/api/v1") for r in routes)
