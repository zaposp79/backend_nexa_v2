"""Configuración de aplicación para despliegue y seguridad base."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from nexa_engine.db.exceptions import DbConfigurationError

logger = logging.getLogger("nexa")

ENV_APP_ENV = "APP_ENV"
ENV_CORS_ALLOWED_ORIGINS = "CORS_ALLOWED_ORIGINS"
ENV_APP_HOST = "APP_HOST"
ENV_APP_PORT = "APP_PORT"
ENV_APP_RELOAD = "APP_RELOAD"
ENV_APP_TITLE = "APP_TITLE"
ENV_APP_DESCRIPTION = "APP_DESCRIPTION"
ENV_APP_VERSION = "APP_VERSION"
ENV_API_PREFIX = "API_PREFIX"
ENV_API_VERSION = "API_VERSION"
ENV_DOCS_URL = "DOCS_URL"
ENV_REDOC_URL = "REDOC_URL"
ENV_OPENAPI_URL = "OPENAPI_URL"
ENV_HEALTH_PATH = "HEALTH_PATH"
ENV_SERVICE_NAME = "SERVICE_NAME"

# Persistence signals used only in cross-validation (no persistence import)
_ENV_DB_PROVIDER = "DB_PROVIDER"
_ENV_COSMOS_ENDPOINT = "COSMOS_ENDPOINT"
_PROVIDER_COSMOS = "cosmos"

# Opt-in explícito para correr Cosmos FUERA de production (desarrollo local con
# Swagger y reload). NO tiene efecto en production: con APP_ENV=production los
# docs SIEMPRE quedan desactivados, así que un App Service productivo no puede
# exponer /docs por accidente aunque esta variable esté presente.
ENV_ALLOW_COSMOS_NON_PRODUCTION = "ALLOW_COSMOS_NON_PRODUCTION"

APP_ENV_DEVELOPMENT = "development"
APP_ENV_TEST = "test"
APP_ENV_PRODUCTION = "production"
VALID_APP_ENVS = {APP_ENV_DEVELOPMENT, APP_ENV_TEST, APP_ENV_PRODUCTION}

DEVELOPMENT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
)
TEST_CORS_ORIGINS = (
    "http://testserver",
    "http://localhost",
)


@dataclass(frozen=True)
class AppSettings:
    app_env: str
    cors_allowed_origins: tuple[str, ...]
    docs_enabled: bool
    host: str
    port: int
    reload: bool
    app_title: str = "NEXA Simulator API"
    app_description: str = "Motor de pricing + API de parametrización y simulación"
    app_version: str = "1.0.0"
    api_prefix: str = "api"
    api_version: str = "v1"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    health_path: str = "/health"
    service_name: str = "nexa-simulator-api"

    @property
    def is_production(self) -> bool:
        return self.app_env == APP_ENV_PRODUCTION


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _env_name(env: dict[str, str]) -> str:
    raw = env.get(ENV_APP_ENV)
    if raw is None:
        logger.warning(
            "[NEXA] %s not set — defaulting to %r. "
            "Set %s=production in production deployments to disable Swagger and hot-reload.",
            ENV_APP_ENV, APP_ENV_DEVELOPMENT, ENV_APP_ENV,
        )
    app_env = (raw or APP_ENV_DEVELOPMENT).strip().lower()
    if app_env not in VALID_APP_ENVS:
        raise DbConfigurationError(
            f"{ENV_APP_ENV}={app_env!r} es inválido; esperado: {sorted(VALID_APP_ENVS)}"
        )
    return app_env


def _cors_origins(env: dict[str, str], app_env: str) -> tuple[str, ...]:
    raw = env.get(ENV_CORS_ALLOWED_ORIGINS, "").strip()
    if raw:
        origins = _split_csv(raw)
    elif app_env == APP_ENV_DEVELOPMENT:
        origins = DEVELOPMENT_CORS_ORIGINS
    elif app_env == APP_ENV_TEST:
        origins = TEST_CORS_ORIGINS
    else:
        origins = ()

    if app_env == APP_ENV_PRODUCTION:
        if not origins:
            raise DbConfigurationError(
                f"{ENV_CORS_ALLOWED_ORIGINS} es obligatorio cuando {ENV_APP_ENV}=production"
            )
        if any(origin == "*" for origin in origins):
            raise DbConfigurationError("CORS wildcard no está permitido en production")
    return origins


def _bool_env(env: dict[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _port(env: dict[str, str]) -> int:
    raw = env.get(ENV_APP_PORT, "8000").strip()
    try:
        port = int(raw)
    except ValueError as exc:
        raise DbConfigurationError(f"{ENV_APP_PORT} debe ser entero") from exc
    if port <= 0 or port > 65535:
        raise DbConfigurationError(f"{ENV_APP_PORT} fuera de rango")
    return port


def _path_segment(env: dict[str, str], name: str, default: str) -> str:
    value = env.get(name, default).strip().strip("/")
    return value or default


def _route_path(env: dict[str, str], name: str, default: str) -> str:
    value = env.get(name, default).strip()
    if not value:
        return default
    return value if value.startswith("/") else f"/{value}"


def _validate_production_infra_consistency(
    env: dict[str, str], app_env: str
) -> None:
    """Fail-fast: si hay infra de producción activa, APP_ENV debe ser 'production'.

    Si ``DB_PROVIDER=cosmos`` o ``COSMOS_ENDPOINT`` está definido, la aplicación
    está configurada para infraestructura de producción. Iniciar en modo
    development (docs habilitados, reload permitido) con esa configuración es
    un riesgo de seguridad, por lo que se rechaza explícitamente.

    Esto previene el escenario: "configuro Cosmos pero olvido establecer
    APP_ENV=production, y mis /docs quedan expuestos en producción."

    Escape hatch para desarrollo local: establecer
    ``ALLOW_COSMOS_NON_PRODUCTION=true`` permite, de forma deliberada, usar
    Cosmos con APP_ENV=development/test (Swagger + reload activos). Es un opt-in
    explícito, no un default, por lo que no reintroduce el riesgo accidental.
    """
    if app_env == APP_ENV_PRODUCTION:
        return  # ya está en producción, no hay inconsistencia

    db_provider = env.get(_ENV_DB_PROVIDER, "json").strip().lower()
    cosmos_endpoint = env.get(_ENV_COSMOS_ENDPOINT, "").strip()

    if db_provider == _PROVIDER_COSMOS or cosmos_endpoint:
        if _bool_env(env, ENV_ALLOW_COSMOS_NON_PRODUCTION, default=False):
            logger.warning(
                "[NEXA] %s=true: usando Cosmos en %s=%r (Swagger/docs ACTIVOS). "
                "Solo para desarrollo local; NO usar en despliegues expuestos.",
                ENV_ALLOW_COSMOS_NON_PRODUCTION, ENV_APP_ENV, app_env,
            )
            return
        raise DbConfigurationError(
            f"Infraestructura de producción detectada ({_ENV_DB_PROVIDER}={db_provider!r}"
            + (f", {_ENV_COSMOS_ENDPOINT} configurado" if cosmos_endpoint else "")
            + f") pero {ENV_APP_ENV} no es 'production'. "
            f"Establece {ENV_APP_ENV}=production para un despliegue productivo, o "
            f"{ENV_ALLOW_COSMOS_NON_PRODUCTION}=true para usar Cosmos en desarrollo local con Swagger."
        )


def load_app_settings(env: dict[str, str] | None = None) -> AppSettings:
    source = dict(os.environ if env is None else env)
    app_env = _env_name(source)

    # Cross-validate: production infra requires explicit APP_ENV=production.
    _validate_production_infra_consistency(source, app_env)

    reload_enabled = _bool_env(
        source,
        ENV_APP_RELOAD,
        default=(app_env == APP_ENV_DEVELOPMENT),
    )
    if app_env == APP_ENV_PRODUCTION and reload_enabled:
        raise DbConfigurationError("APP_RELOAD no puede estar activo en production")

    return AppSettings(
        app_env=app_env,
        cors_allowed_origins=_cors_origins(source, app_env),
        docs_enabled=app_env != APP_ENV_PRODUCTION,
        host=source.get(ENV_APP_HOST, "0.0.0.0").strip() or "0.0.0.0",
        port=_port(source),
        reload=reload_enabled,
        app_title=source.get(ENV_APP_TITLE, "NEXA Simulator API").strip()
        or "NEXA Simulator API",
        app_description=source.get(
            ENV_APP_DESCRIPTION,
            "Motor de pricing + API de parametrización y simulación",
        ).strip()
        or "Motor de pricing + API de parametrización y simulación",
        app_version=source.get(ENV_APP_VERSION, "1.0.0").strip() or "1.0.0",
        api_prefix=_path_segment(source, ENV_API_PREFIX, "api"),
        api_version=_path_segment(source, ENV_API_VERSION, "v1"),
        docs_url=_route_path(source, ENV_DOCS_URL, "/docs"),
        redoc_url=_route_path(source, ENV_REDOC_URL, "/redoc"),
        openapi_url=_route_path(source, ENV_OPENAPI_URL, "/openapi.json"),
        health_path=_route_path(source, ENV_HEALTH_PATH, "/health"),
        service_name=source.get(ENV_SERVICE_NAME, "nexa-simulator-api").strip()
        or "nexa-simulator-api",
    )


__all__ = [
    "APP_ENV_DEVELOPMENT",
    "APP_ENV_PRODUCTION",
    "APP_ENV_TEST",
    "AppSettings",
    "ENV_APP_ENV",
    "ENV_APP_HOST",
    "ENV_APP_PORT",
    "ENV_APP_RELOAD",
    "ENV_APP_TITLE",
    "ENV_APP_DESCRIPTION",
    "ENV_APP_VERSION",
    "ENV_API_PREFIX",
    "ENV_API_VERSION",
    "ENV_CORS_ALLOWED_ORIGINS",
    "ENV_DOCS_URL",
    "ENV_REDOC_URL",
    "ENV_OPENAPI_URL",
    "ENV_HEALTH_PATH",
    "ENV_SERVICE_NAME",
    "load_app_settings",
]
