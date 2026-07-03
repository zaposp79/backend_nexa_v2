"""Endpoints de parametrización GN."""

from fastapi import APIRouter, Depends, Path, Query, Request, UploadFile, File
from fastapi.responses import JSONResponse

from nexa_engine.modules.parametrizacion.gn.services.gn_service import GNService
from nexa_engine.modules.parametrizacion.shared.helpers.upload_guards import (
    check_filename_prefix,
    check_file_extension,
    check_file_size,
    sanitize_user_id,
)
from nexa_engine.modules.shared.config.config import MAX_EXCEL_UPLOAD_BYTES
from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.shared.responses import ApiResponse, ErrorDetail
from nexa_engine.modules.shared.versioning.registry_provider import _version_registry

router = APIRouter(prefix="/parametrization/gn", tags=["parametrization-gn"])
_service: GNService | None = None


def _get_service(request: Request) -> GNService:
    if _service is not None:
        return _service
    return request.app.state.container.gn_upload_service


@router.post(
    "/upload",
    summary="Subir archivo Excel GN",
    description="Carga y procesa un archivo Excel de parametrización de Gastos de Negociación.",
    operation_id="uploadGn",
    status_code=201,
)
async def upload_gn(
    file: UploadFile = File(...),
    user_id: str = Query(default="anonymous"),
    service: GNService = Depends(_get_service),
):
    filename = file.filename or ""
    check_filename_prefix(filename, "GN")
    check_file_extension(filename)
    file_bytes = await file.read(MAX_EXCEL_UPLOAD_BYTES + 1)
    check_file_size(file_bytes)
    user_id = sanitize_user_id(user_id)
    resp = service.process_upload(filename or "upload.xlsx", file_bytes, user_id=user_id)
    return ApiResponse.ok(resp.model_dump())


@router.get(
    "/versions",
    summary="Listar versiones GN",
    description="Retorna el listado de versiones subidas de parametrización de Gastos de Negociación.",
    operation_id="listGnVersions",
)
def list_gn_versions(service: GNService = Depends(_get_service)):
    return ApiResponse.ok([v.model_dump() for v in service.list_versions()])


@router.get(
    "/active",
    summary="Obtener versión GN activa",
    description="Retorna la versión activa actual de parametrización de Gastos de Negociación.",
    operation_id="getGnActiveVersion",
)
def get_gn_active(service: GNService = Depends(_get_service)):
    active = service.get_active()
    if active is None:
        return JSONResponse(
            status_code=404,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="NOT_FOUND", message="No hay versión GN activa."),
            ).model_dump(),
        )
    return ApiResponse.ok(active)


@router.get(
    "/{version_id}/activate",
    summary="Activar versión GN",
    description="Activa una versión específica de parametrización de Gastos de Negociación.",
    operation_id="activateGnVersion",
)
def activate_gn(
    version_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
    service: GNService = Depends(_get_service),
):
    summary = service.activate(version_id)
    _version_registry.invalidate_cache()
    return ApiResponse.ok(summary.model_dump())


@router.delete(
    "/{version_id}",
    summary="Eliminar versión GN",
    description="Elimina una versión específica de parametrización de Gastos de Negociación.",
    operation_id="deleteGnVersion",
    status_code=200,
)
def delete_gn(
    version_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
    service: GNService = Depends(_get_service),
):
    try:
        service.delete(version_id)
    except NotFoundError as e:
        return JSONResponse(
            status_code=404,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="NOT_FOUND", message=str(e)),
            ).model_dump(),
        )
    return ApiResponse.ok(None)
