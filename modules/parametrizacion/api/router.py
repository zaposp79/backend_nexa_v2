"""Aggregated router for the parametrizacion capability.

Registra únicamente los routers de los dominios GN, HR y OP.
Los servicios de cadena_a/b/c son módulos independientes con sus propios
routers registrados en api/v1/router.py.
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from nexa_engine.modules.parametrizacion.gn.api.router import router as gn_router
from nexa_engine.modules.parametrizacion.hr.api.router import router as hr_router
from nexa_engine.modules.parametrizacion.op.api.router import router as op_router
from nexa_engine.modules.shared.responses import ApiResponse, ErrorDetail
from nexa_engine.modules.shared.error_catalog import make_detail as _make_detail

parametrizacion_router = APIRouter()
parametrizacion_router.include_router(hr_router)
parametrizacion_router.include_router(gn_router)
parametrizacion_router.include_router(op_router)


@parametrizacion_router.get(
    "/parametrization/versions/all",
    summary="Listar todas las versiones (HR + GN + OP)",
    description=(
        "Retorna el listado unificado de versiones subidas de HR, GN y OP, "
        "ordenadas por fecha de carga descendente. "
        "Cada entrada incluye el campo 'domain' para identificar a qué módulo pertenece."
    ),
    operation_id="listAllParametrizationVersions",
    tags=["parametrization-active"],
)
def list_all_versions(request: Request):
    container = request.app.state.container
    entries = []
    for domain, service in (
        ("hr", container.hr_upload_service),
        ("gn", container.gn_upload_service),
        ("op", container.op_upload_service),
    ):
        for v in service.list_versions():
            d = v.model_dump()
            d["domain"] = domain
            entries.append(d)
    entries.sort(key=lambda e: e.get("uploaded_at") or "", reverse=True)
    entries.sort(key=lambda e: e["domain"])
    return ApiResponse.ok(entries)


@parametrizacion_router.get(
    "/parametrization/active",
    summary="Obtener parametrización activa consolidada",
    description=(
        "Retorna la parametrización activa de HR, GN y OP consolidada en un solo objeto. "
        "Fusiona los catálogos lv.catalogs de los 3 archivos y agrupa todas las hojas en payload."
    ),
    operation_id="getAllActiveParametrization",
    tags=["parametrization-active"],
)
def get_all_active_parametrization(request: Request):
    service = request.app.state.container.active_parametrization_service
    data = service.get_all_active()
    if data is None:
        return JSONResponse(
            status_code=404,
            content=ApiResponse(success=False, error=_make_detail("SIM-00601")).model_dump(),
        )
    return ApiResponse.ok(data)


__all__ = ["parametrizacion_router"]
