from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
import logging

from fastapi import FastAPI

from ....db.container import build_container
from ..config.app_settings import AppSettings
from ..config.config import ensure_storage_dirs

logger = logging.getLogger("nexa")


def make_lifespan(
    resolved_settings: AppSettings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Crea el lifespan de la aplicación con los settings ya resueltos.

    El contenedor de persistencia se construye una sola vez al arrancar
    el servidor (en el lifespan), no durante la importación del módulo.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        ensure_storage_dirs()
        app.state.container = build_container()

        _on  = "ON "
        _off = "OFF"
        logger.info("=" * 60)
        logger.info("[NEXA] %s v%s — arrancando", resolved_settings.app_title, resolved_settings.app_version)
        logger.info("[NEXA]   APP_ENV    : %s", resolved_settings.app_env.upper())
        logger.info("[NEXA]   Swagger    : %s  (/docs)", _on if resolved_settings.docs_enabled else _off)
        logger.info("[NEXA]   ReDoc      : %s  (/redoc)", _on if resolved_settings.docs_enabled else _off)
        logger.info("[NEXA]   Hot reload : %s", _on if resolved_settings.reload else _off)
        logger.info("[NEXA]   DB backend : %s", app.state.container.store.__class__.__name__)
        logger.info("=" * 60)

        yield
        app.state.container.close()

    return lifespan
