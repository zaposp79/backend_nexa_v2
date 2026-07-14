"""Configuración para la capa de persistencia transversal."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

_logger = logging.getLogger("nexa.db.config")

from nexa_engine.db.constants.provider_constants import (
    DEFAULT_PROVIDER,
    ENV_COSMOS_CONTAINER,
    ENV_COSMOS_CONTAINER_CONFIGURATION,
    ENV_COSMOS_DATABASE,
    ENV_COSMOS_ENDPOINT,
    ENV_COSMOS_KEY,
    ENV_DB_PROVIDER,
    ENV_JSON_STORAGE_PATH,
    PROVIDER_COSMOS,
    VALID_PROVIDERS,
)
from nexa_engine.db.exceptions import DbConfigurationError

# Raíz del proyecto: db/config.py -> backend_nexa/. Usado como raíz por defecto
# para el backend JSON de forma que aterrice en el directorio top-level ``storage/``.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_JSON_STORAGE_PATH = _PROJECT_ROOT / "storage"


@dataclass(frozen=True)
class CosmosSettings:
    """Configuración de Cosmos resuelta."""

    endpoint: str
    key: str
    database: str
    container: str
    # Container separado para la colección "configuration" (simulation drafts).
    # Si está vacío, el factory usa `container` como fallback.
    container_configuration: str = ""


@dataclass(frozen=True)
class DbConfig:
    """Configuración de persistencia resuelta."""

    provider: str
    json_storage_path: Path
    cosmos: CosmosSettings | None = None


def _resolve_provider(env: dict[str, str]) -> str:
    explicit = env.get(ENV_DB_PROVIDER)
    if explicit is None:
        _logger.warning(
            "[NEXA] %s not set — defaulting to %r. "
            "Set %s=cosmos in production Cosmos deployments.",
            ENV_DB_PROVIDER, DEFAULT_PROVIDER, ENV_DB_PROVIDER,
        )
    raw = (explicit or DEFAULT_PROVIDER).strip().lower()
    if raw not in VALID_PROVIDERS:
        raise DbConfigurationError(
            f"{ENV_DB_PROVIDER}={raw!r} es inválido; se esperaba uno de {VALID_PROVIDERS}"
        )
    return raw


def _resolve_json_path(env: dict[str, str], provider: str) -> Path:
    """Resolver la ruta de almacenamiento JSON."""
    raw = env.get(ENV_JSON_STORAGE_PATH, "").strip()
    if not raw:
        # Detectar contextos similares a producción: si APP_ENV=production está establecido
        # pero JSON_STORAGE_PATH falta, lanzar en lugar de exponer la ruta del sistema.
        app_env = env.get("APP_ENV", "").strip().lower()
        if app_env == "production" and provider != PROVIDER_COSMOS:
            raise DbConfigurationError(
                f"{ENV_JSON_STORAGE_PATH} es obligatorio cuando APP_ENV=production "
                f"y DB_PROVIDER=json para evitar exponer la ruta absoluta del servidor."
            )
        return _DEFAULT_JSON_STORAGE_PATH
    path = Path(raw)
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    return path


def _resolve_cosmos(env: dict[str, str]) -> CosmosSettings:
    endpoint = env.get(ENV_COSMOS_ENDPOINT, "").strip()
    key = env.get(ENV_COSMOS_KEY, "").strip()
    database = env.get(ENV_COSMOS_DATABASE, "").strip()
    container = env.get(ENV_COSMOS_CONTAINER, "").strip()
    # Opcional: container separado para "configuration". Vacío = usa `container`.
    container_configuration = env.get(ENV_COSMOS_CONTAINER_CONFIGURATION, "").strip()
    missing = [
        name
        for name, value in (
            (ENV_COSMOS_ENDPOINT, endpoint),
            (ENV_COSMOS_KEY, key),
            (ENV_COSMOS_DATABASE, database),
            (ENV_COSMOS_CONTAINER, container),
        )
        if not value
    ]
    if missing:
        # Nunca exponer los valores — solo los nombres de variables faltantes.
        raise DbConfigurationError(
            "Cosmos backend selected but missing required settings: "
            + ", ".join(missing)
        )
    return CosmosSettings(
        endpoint=endpoint,
        key=key,
        database=database,
        container=container,
        container_configuration=container_configuration,
    )


def load_config(env: dict[str, str] | None = None) -> DbConfig:
    """Resolver DbConfig desde env (por defecto os.environ)."""
    source = dict(os.environ if env is None else env)
    provider = _resolve_provider(source)
    json_path = _resolve_json_path(source, provider)
    cosmos = _resolve_cosmos(source) if provider == PROVIDER_COSMOS else None
    return DbConfig(provider=provider, json_storage_path=json_path, cosmos=cosmos)


__all__ = ["DbConfig", "CosmosSettings", "load_config"]
