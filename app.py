"""
NEXA Simulator: punto de entrada ASGI.

Este módulo expone la factory FastAPI del backend. Importarlo es seguro:
no carga variables de entorno, no resuelve settings y no construye el
contenedor de persistencia hasta que create_app() es invocada y el lifespan
arranca.

Inicio del servidor:
    uvicorn backend_nexa.app:create_app --factory [--reload] [--host 0.0.0.0] [--port 8000]

Inicio con carga de backend_nexa/.env:
    python -m backend_nexa.app

Tests:
    from nexa_engine.app import create_app
    app = create_app(settings=AppSettings(...))
    client = TestClient(app)
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .modules.api_v1.router import router as v1_router
from .modules.shared.config.app_settings import AppSettings, load_app_settings
from .modules.shared.infrastructure.env_loader import load_env_file
from .modules.shared.infrastructure.exception_handlers import (
    register_exception_handlers,
)
from .modules.shared.infrastructure.lifespan import make_lifespan
from .modules.shared.middleware.middlewares import register_middlewares


def create_app(settings: AppSettings | None = None) -> FastAPI:
    resolved_settings = settings or load_app_settings()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    app = FastAPI(
        title=resolved_settings.app_title,
        description=resolved_settings.app_description,
        version=resolved_settings.app_version,
        lifespan=make_lifespan(resolved_settings),
        docs_url=resolved_settings.docs_url if resolved_settings.docs_enabled else None,
        redoc_url=(
            resolved_settings.redoc_url if resolved_settings.docs_enabled else None
        ),
        openapi_url=(
            resolved_settings.openapi_url if resolved_settings.docs_enabled else None
        ),
        openapi_tags=[
            {
                "name": "Health",
                "description": "Liveness and readiness probes for load balancers and orchestration.",
            },
            {
                "name": "Simulations",
                "description": "Input, execution, and status of pricing simulations. The primary workflow: configure panel and chains → POST /calculate → poll status → GET screen results.",
            },
            {
                "name": "Parametrization",
                "description": "Upload, version, and activate HR / GN / OP Excel parametrization files. Used to configure business rules before running simulations.",
            },
            {
                "name": "Vision Imprimible",
                "description": "Screen-ready contract for the canonical printable deal view (6 sections: header, summary cards, tables, charts, metadata).",
            },
            {
                "name": "Vision PYG",
                "description": "PyG by channel with monthly breakdown. Equivalent to Excel sheet 'P&G Resumen' filtered by scenario.",
            },
            {
                "name": "Vision Cost To Serve",
                "description": "Cost-to-Serve breakdown by chain, channel, and team structure. Equivalent to Excel sheet 'Vision CTS'.",
            },
            {
                "name": "Vision Tarifas",
                "description": "Fee structure by channel and product line including recalculable Modelo de Cobro preview.",
            },
        ],
    )
    app.state.settings = resolved_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_allowed_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_middlewares(app)
    register_exception_handlers(app)

    app.include_router(
        v1_router,
        prefix=f"/{resolved_settings.api_prefix}/{resolved_settings.api_version}",
    )

    @app.get(resolved_settings.health_path, tags=["Health"], operation_id="health", summary="Liveness probe")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": resolved_settings.service_name}

    @app.get(resolved_settings.health_path + "/ready", tags=["Health"], operation_id="healthReady", summary="Readiness probe")
    def health_ready(request: Request):
        try:
            store = request.app.state.container.store
            store.ping()
            return {"status": "ready"}
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "storage_unavailable"},
            )

    return app


if __name__ == "__main__":
    import uvicorn

    load_env_file()
    startup_settings = load_app_settings()
    uvicorn.run(
        "backend_nexa.app:create_app",
        factory=True,
        host=startup_settings.host,
        port=startup_settings.port,
        reload=startup_settings.reload,
    )
