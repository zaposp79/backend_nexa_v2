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
        logger.info("[NEXA] Storage directories initialised")
        app.state.container = build_container()
        logger.info(
            "[NEXA] Persistence container ready (provider=%s)",
            app.state.container.store.__class__.__name__,
        )
        logger.info(
            "[NEXA] Starting in %r mode (docs=%s, reload=%s)",
            resolved_settings.app_env,
            resolved_settings.docs_enabled,
            resolved_settings.reload,
        )
        yield
        app.state.container.close()

    return lifespan
