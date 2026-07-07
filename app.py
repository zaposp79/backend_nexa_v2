"""
NEXA Simulator: punto de entrada ASGI.

Application factory — no existe instancia global a nivel de módulo.
Importar este módulo NO ejecuta load_app_settings() ni construye la app.

Inicio del servidor:
    # Factory mode (recomendado — soporta hot reload y múltiples workers):
    #   Ejecutar desde el directorio PADRE de backend_nexa_v2/
    uvicorn backend_nexa_v2.app:create_app --factory [--reload] [--host 0.0.0.0] [--port 8000]

    # NOTA: 'nexa_engine' es un alias runtime registrado por backend_nexa_v2/__init__.py.
    # El módulo canónico es 'backend_nexa_v2.app'. Uvicorn no puede resolver
    # 'nexa_engine.app' si backend_nexa_v2/__init__.py no se importó previamente.

    # Via __main__ del módulo real (equivalente, lee APP_ENV/APP_HOST/APP_PORT de os.environ):
    #   Ejecutar desde el directorio padre de backend_nexa_v2/
    python -m backend_nexa_v2.app
    #
    # El bloque __main__ usa internamente:
    #   uvicorn.run("backend_nexa_v2.app:create_app", factory=True, ...)
    # lo que garantiza que los subprocesses de reload usen el módulo canónico real.

Tests:
    from nexa_engine.app import create_app
    app = create_app(settings=AppSettings(...))
    client = TestClient(app)
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
import logging
import os
import time
from pathlib import Path
from uuid import uuid4


def _load_env_file() -> None:
    """Carga backend_nexa_v2/.env en os.environ (override=False).

    La app lee la configuración (DB_PROVIDER, COSMOS_*) desde os.environ en
    tiempo de arranque (load_config / load_app_settings). Sin esta carga, un
    .env presente en el repo no tendría efecto al lanzar el servidor.

    IMPORTANTE: se invoca SOLO desde el entrypoint __main__ (python -m
    backend_nexa_v2.app), NO al importar el módulo. Así los tests que importan
    create_app permanecen herméticos (no heredan el .env del desarrollador) y
    el subproceso de reload de uvicorn hereda las variables vía os.environ.
    No sobrescribe variables ya definidas en el entorno real.
    """
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv  # type: ignore[import]
        load_dotenv(env_path)
        return
    except ImportError:
        pass
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .modules.api_v1.router import router as v1_router
from .db.container import build_container
# IMPORTANTE: importar por 'nexa_engine.*' (no '.modules.*'). El alias nexa_engine
# carga estos módulos como objetos distintos de backend_nexa_v2.*, por lo que las
# clases de excepción difieren. El código interno LANZA las de nexa_engine; los
# exception handlers deben registrarse con ESAS mismas clases o no se capturan
# (caería en 500 en vez del 4xx correcto).
from nexa_engine.modules.shared.exceptions import (
    DomainError,
    NotFoundError,
    ValidationError as DomainValidationError,
)
from .modules.shared.config.app_settings import AppSettings, load_app_settings
from .modules.shared.config.config import ensure_storage_dirs
from .modules.shared.responses import ApiResponse, ErrorDetail

logger = logging.getLogger("nexa")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

CORRELATION_ID_HEADER = "X-Correlation-ID"
SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "api-key",
    "apikey",
    "x-auth-token",
}
SENSITIVE_QUERY_MARKERS = (
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "key",
)
REDACTED = "[REDACTED]"


def _correlation_id(request: Request) -> str:
    provided = request.headers.get(CORRELATION_ID_HEADER)
    return provided.strip() if provided and provided.strip() else str(uuid4())


def _safe_headers(request: Request) -> dict[str, str]:
    safe: dict[str, str] = {}
    for name, value in request.headers.items():
        if name.lower() in SENSITIVE_HEADER_NAMES:
            safe[name] = REDACTED
        else:
            safe[name] = value
    return safe


def _safe_path(request: Request) -> str:
    if not request.query_params:
        return request.url.path
    redacted = []
    for name, value in request.query_params.multi_items():
        if any(marker in name.lower() for marker in SENSITIVE_QUERY_MARKERS):
            redacted.append(f"{name}={REDACTED}")
        else:
            redacted.append(f"{name}={value}")
    return f"{request.url.path}?{'&'.join(redacted)}"


def _make_lifespan(
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


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Application factory.

    Llama a load_app_settings() en el momento de la invocación,
    NO durante la importación del módulo.

    Args:
        settings: Settings pre-construidos (para tests). Si None, lee
                  os.environ en este momento mediante load_app_settings().

    Returns:
        Instancia FastAPI completamente configurada, lista para servir.
    """
    resolved = settings or load_app_settings()

    # /docs se sirve mediante una ruta propia (más abajo) para forzar el orden
    # de métodos POST → GET → PATCH → DELETE en Swagger UI.
    redoc_url = "/redoc" if resolved.docs_enabled else None
    openapi_url = "/openapi.json" if resolved.docs_enabled else None

    fastapi_app = FastAPI(
        title="NEXA Simulator API",
        description="Motor de pricing + API de parametrización y simulación",
        version="1.0.0",
        lifespan=_make_lifespan(resolved),
        docs_url=None,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    fastapi_app.state.settings = resolved

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_allowed_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @fastapi_app.middleware("http")
    async def log_requests(request: Request, call_next):
        correlation_id = _correlation_id(request)
        request.state.correlation_id = correlation_id
        t0 = time.monotonic()
        response = await call_next(request)
        ms = (time.monotonic() - t0) * 1000
        response.headers[CORRELATION_ID_HEADER] = correlation_id

        log_method = logger.warning if response.status_code >= 400 else logger.info
        log_method(
            "[NEXA] correlation_id=%s %s %s -> %d (%.1fms) headers=%s",
            correlation_id,
            request.method,
            _safe_path(request),
            response.status_code,
            ms,
            _safe_headers(request),
        )
        return response

    @fastapi_app.exception_handler(NotFoundError)
    async def not_found_handler(request, exc):
        return JSONResponse(
            status_code=404,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="NOT_FOUND", message=str(exc)),
            ).model_dump(),
        )

    @fastapi_app.exception_handler(DomainValidationError)
    async def validation_error_handler(request, exc):
        return JSONResponse(
            status_code=422,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="VALIDATION_ERROR", message=str(exc)),
            ).model_dump(),
        )

    @fastapi_app.exception_handler(DomainError)
    async def domain_error_handler(request, exc):
        logger.error(
            "[NEXA] correlation_id=%s domain error method=%s path=%s headers=%s",
            getattr(request.state, "correlation_id", str(uuid4())),
            request.method,
            _safe_path(request),
            _safe_headers(request),
        )
        return JSONResponse(
            status_code=400,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="DOMAIN_ERROR", message=str(exc)),
            ).model_dump(),
        )

    @fastapi_app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        correlation_id = getattr(request.state, "correlation_id", str(uuid4()))
        logger.exception(
            "[NEXA] correlation_id=%s unhandled exception method=%s path=%s headers=%s",
            correlation_id,
            request.method,
            _safe_path(request),
            _safe_headers(request),
        )
        return JSONResponse(
            status_code=500,
            headers={CORRELATION_ID_HEADER: correlation_id},
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code="INTERNAL_SERVER_ERROR",
                    message="Error inesperado en el servidor.",
                ),
                meta={"correlation_id": correlation_id},
            ).model_dump(),
        )

    @fastapi_app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Normaliza errores HTTP (404 ruta inexistente, 405 método inválido,
        400 de validaciones manuales, etc.) al formato ApiResponse.

        Cubre el caso de una URI mal escrita (p. ej. `.../uplo` en vez de
        `.../upload`): Starlette levanta un 404 que de otro modo devolvería el
        cuerpo por defecto `{"detail": "Not Found"}`, fuera del contrato.
        """
        status_to_code = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            415: "UNSUPPORTED_MEDIA_TYPE",
        }
        code = status_to_code.get(exc.status_code, "HTTP_ERROR")
        if exc.status_code == 404:
            message = (
                f"Ruta no encontrada: '{request.method} {request.url.path}'. "
                "Revisa la URL del endpoint (método y segmentos de la ruta)."
            )
        elif exc.status_code == 405:
            message = (
                f"Método '{request.method}' no permitido para "
                f"'{request.url.path}'."
            )
        else:
            message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResponse.fail(code, message).model_dump(),
            headers=getattr(exc, "headers", None),
        )

    @fastapi_app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        """422 cuando los parámetros, query o cuerpo de la solicitud no cumplen
        el esquema esperado (formato ApiResponse, con el detalle por campo)."""
        return JSONResponse(
            status_code=422,
            content=ApiResponse.fail(
                "VALIDATION_ERROR",
                "Parámetros o cuerpo de la solicitud inválidos.",
                details=jsonable_encoder(exc.errors()),
            ).model_dump(),
        )

    fastapi_app.include_router(v1_router, prefix="/api/v1")

    if resolved.docs_enabled:
        # operationsSorter JS: ordena cada tag por método POST → GET → PATCH →
        # DELETE; ante el mismo método, alfabético por path. Se inyecta como
        # función (no JSON-serializable) reemplazando un marcador en el HTML.
        _ops_sorter = (
            "(a, b) => {"
            "  const order = {post: 0, get: 1, patch: 2, delete: 3};"
            "  const ra = order[a.get('method')]; const rb = order[b.get('method')];"
            "  const xa = (ra === undefined ? 99 : ra), xb = (rb === undefined ? 99 : rb);"
            "  return xa !== xb ? xa - xb : a.get('path').localeCompare(b.get('path'));"
            "}"
        )

        @fastapi_app.get("/docs", include_in_schema=False)
        def custom_swagger_ui_html():
            html = get_swagger_ui_html(
                openapi_url=openapi_url,
                title="NEXA Simulator API - Swagger UI",
                swagger_ui_parameters={"operationsSorter": "__NEXA_OPS_SORTER__"},
            ).body.decode("utf-8")
            html = html.replace('"__NEXA_OPS_SORTER__"', _ops_sorter)
            return HTMLResponse(html)

    @fastapi_app.get("/health")
    def health():
        return {"status": "ok", "service": "nexa-simulator-api"}

    return fastapi_app


# ---------------------------------------------------------------------------
# __main__ — inicio directo (python -m backend_nexa_v2.app)
#
# MÓDULO CANÓNICO: backend_nexa_v2.app  (real en disco)
# NO usar: nexa_engine.app — es un alias runtime, no existe como directorio.
#   Los subprocesses de reload parten con sys.modules vacío; si uvicorn
#   intenta importar 'nexa_engine.app' en un proceso nuevo, falla con
#   ModuleNotFoundError o cae al fallback buscando el atributo 'app' global.
#
# CADENA DE RESOLUCIÓN con backend_nexa_v2.app:create_app:
#   1. Python importa 'backend_nexa_v2' → __init__.py → sys.modules["nexa_engine"]=backend_nexa_v2
#   2. Python importa 'backend_nexa_v2.app'
#   3. Todos los 'from nexa_engine.modules.xxx import ...' internos funcionan
#      porque el alias ya está registrado en el paso 1.
#   4. uvicorn llama create_app() → factory real, sin instancia global.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    # Carga .env SOLO al lanzar el servidor (no en tests). El subproceso de
    # reload de uvicorn hereda estas variables vía os.environ.
    _load_env_file()
    _s = load_app_settings()
    uvicorn.run(
        "backend_nexa_v2.app:create_app",
        factory=True,
        host=_s.host,
        port=_s.port,
        reload=_s.reload,
    )
