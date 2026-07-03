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
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .modules.api_v1.router import router as v1_router
from .modules.shared.config.app_settings import AppSettings, load_app_settings
from .modules.shared.infrastructure.env_loader import load_env_file
from .modules.shared.infrastructure.exception_handlers import (
    register_exception_handlers,
)
from .modules.shared.infrastructure.lifespan import make_lifespan
from .modules.shared.middleware.middlewares import register_middlewares

_CDN_BASE = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5"
_CDN_JS = f"{_CDN_BASE}/swagger-ui-bundle.js"
_CDN_CSS = f"{_CDN_BASE}/swagger-ui.css"
_CDN_FAVICON = f"{_CDN_BASE}/favicon-32x32.png"

# Directorio local con los archivos de Swagger UI v5 descargados del CDN.
# Generado por `python -m backend_nexa_v2.scripts.download_swagger_ui` o al inicio.
_LOCAL_SWAGGER_DIR = os.path.join(os.path.dirname(__file__), "static", "swagger-ui")
_LOCAL_BUNDLE_FILE = os.path.join(_LOCAL_SWAGGER_DIR, "swagger-ui-bundle.js")


def _local_swagger_available() -> bool:
    return os.path.isfile(_LOCAL_BUNDLE_FILE)


def _download_swagger_ui_if_needed() -> bool:
    """Descarga swagger-ui-dist@5 del CDN al directorio local si no existe.

    Retorna True si los archivos locales están disponibles al finalizar.
    Requisito: swagger-ui v5 para compatibilidad con OpenAPI 3.1.0.
    """
    if _local_swagger_available():
        return True

    logger = logging.getLogger("nexa")
    files = [
        "swagger-ui-bundle.js",
        "swagger-ui-standalone-preset.js",
        "swagger-ui.css",
        "favicon-32x32.png",
        "favicon-16x16.png",
        "oauth2-redirect.html",
    ]
    try:
        import urllib.request
        os.makedirs(_LOCAL_SWAGGER_DIR, exist_ok=True)
        for fname in files:
            url = f"{_CDN_BASE}/{fname}"
            dest = os.path.join(_LOCAL_SWAGGER_DIR, fname)
            urllib.request.urlretrieve(url, dest)
        logger.info("[NEXA] swagger-ui-dist@5 descargado y guardado en static/swagger-ui/")
        return True
    except Exception as exc:
        logger.warning("[NEXA] No se pudo descargar swagger-ui del CDN: %s. Usando CDN en tiempo de ejecucion.", exc)
        return False


def create_app(settings: AppSettings | None = None) -> FastAPI:
    # Cargar .env antes de leer los settings, pero SOLO cuando no se pasan
    # settings explícitos (los tests siempre pasan AppSettings → permanecen herméticos).
    # Esto hace que `uvicorn backend_nexa_v2.app:create_app --factory` cargue el
    # .env igual que `python -m backend_nexa_v2.app`. En Azure App Service las
    # variables se inyectan por el portal (Application Settings) y tienen prioridad
    # sobre el .env porque load_env_file usa override=False / setdefault.
    if settings is None:
        load_env_file()
    resolved_settings = settings or load_app_settings()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Disable built-in docs routes; we register them manually below to allow
    # local static file serving instead of CDN (blocked in corporate networks).
    app = FastAPI(
        title=resolved_settings.app_title,
        description=resolved_settings.app_description,
        version=resolved_settings.app_version,
        lifespan=make_lifespan(resolved_settings),
        docs_url=None,
        redoc_url=None,
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
                "name": "parametrization-active",
                "description": "Consolidated active parametrization: merged HR + GN + OP payload in a single response.",
            },
            {
                "name": "parametrization-hr",
                "description": "Upload, version, and activate HR (Human Resources) Excel parametrization files.",
            },
            {
                "name": "parametrization-gn",
                "description": "Upload, version, and activate GN (Gastos de Negociación) Excel parametrization files.",
            },
            {
                "name": "parametrization-op",
                "description": "Upload, version, and activate OP (Gastos de Operación) Excel parametrization files.",
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

    # Exception handlers MUST be registered before any add_middleware() call.
    # Starlette rebuilds middleware_stack on each add_middleware() using the
    # current exception_handlers dict. Registering handlers after would leave
    # the already-built ExceptionMiddleware without the typed handlers.
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_allowed_origins),
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Correlation-ID"],
        expose_headers=["X-Correlation-ID"],
    )

    register_middlewares(app)

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

    if resolved_settings.docs_enabled:
        _log = logging.getLogger("nexa")
        _use_local = _download_swagger_ui_if_needed()

        if _use_local:
            app.mount(
                "/static/swagger-ui",
                StaticFiles(directory=_LOCAL_SWAGGER_DIR),
                name="swagger-ui-static",
            )
            _js_url = "/static/swagger-ui/swagger-ui-bundle.js"
            _css_url = "/static/swagger-ui/swagger-ui.css"
            _favicon_url = "/static/swagger-ui/favicon-32x32.png"
            _log.info("[NEXA] Swagger UI v5 sirviendo desde archivos locales (static/swagger-ui/)")
        else:
            _js_url = _CDN_JS
            _css_url = _CDN_CSS
            _favicon_url = _CDN_FAVICON
            _log.warning("[NEXA] Swagger UI cargando desde CDN (archivos locales no disponibles)")

        @app.get(resolved_settings.docs_url, include_in_schema=False)
        async def swagger_ui_html():
            return get_swagger_ui_html(
                openapi_url=resolved_settings.openapi_url,
                title=f"{resolved_settings.app_title} - Swagger UI",
                swagger_js_url=_js_url,
                swagger_css_url=_css_url,
                swagger_favicon_url=_favicon_url,
            )

        @app.get(resolved_settings.docs_url + "/oauth2-redirect", include_in_schema=False)
        async def swagger_ui_redirect():
            from fastapi.openapi.docs import get_swagger_ui_oauth2_redirect_html
            return get_swagger_ui_oauth2_redirect_html()

        @app.get(resolved_settings.redoc_url, include_in_schema=False)
        async def redoc_html():
            return get_redoc_html(
                openapi_url=resolved_settings.openapi_url,
                title=f"{resolved_settings.app_title} - ReDoc",
            )

    return app


if __name__ == "__main__":
    import uvicorn

    load_env_file()
    startup_settings = load_app_settings()
    # Use __spec__.parent to avoid hardcoding the package name (works as backend_nexa or backend_nexa_v2)
    _pkg = __spec__.parent if __spec__ else "backend_nexa"
    uvicorn.run(
        f"{_pkg}.app:create_app",
        factory=True,
        host=startup_settings.host,
        port=startup_settings.port,
        reload=startup_settings.reload,
    )
