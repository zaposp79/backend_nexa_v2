"""Endpoints de parametrización HR."""

from fastapi import APIRouter, Depends, Path, Query, Request, UploadFile, File
from fastapi.responses import JSONResponse

from nexa_engine.modules.parametrizacion.hr.services.hr_service import HRService
from nexa_engine.modules.parametrizacion.shared.helpers.upload_guards import (
    check_filename_prefix,
    check_file_extension,
    check_file_size,
    sanitize_user_id,
)
from nexa_engine.modules.shared.config.config import MAX_EXCEL_UPLOAD_BYTES
from nexa_engine.modules.shared.responses import ApiResponse, ErrorDetail
from nexa_engine.modules.shared.versioning.registry_provider import _version_registry

router = APIRouter(prefix="/parametrization/hr", tags=["Parametrization"])
_service: HRService | None = None


def _get_service(request: Request) -> HRService:
    if _service is not None:
        return _service
    return request.app.state.container.hr_upload_service


@router.post(
    "/upload",
    summary="Subir archivo Excel HR",
    description="Carga y procesa un archivo Excel de parametrización de Recursos Humanos.",
    operation_id="uploadHr",
    status_code=201,
)
async def upload_hr(
    file: UploadFile = File(...),
    user_id: str = Query(default="anonymous"),
    service: HRService = Depends(_get_service),
):
    filename = file.filename or ""
    check_filename_prefix(filename, "HR")
    check_file_extension(filename)
    file_bytes = await file.read(MAX_EXCEL_UPLOAD_BYTES + 1)
    check_file_size(file_bytes)
    user_id = sanitize_user_id(user_id)
    resp = service.process_upload(filename or "upload.xlsx", file_bytes, user_id=user_id)
    return ApiResponse.ok(resp.model_dump())


@router.get(
    "/versions",
    summary="Listar versiones HR",
    description="Retorna el listado de versiones subidas de parametrización de Recursos Humanos.",
    operation_id="listHrVersions",
)
def list_hr_versions(service: HRService = Depends(_get_service)):
    return ApiResponse.ok([v.model_dump() for v in service.list_versions()])


@router.get(
    "/active",
    summary="Obtener versión HR activa",
    description="Retorna la versión activa actual de parametrización de Recursos Humanos.",
    operation_id="getHrActiveVersion",
)
def get_hr_active(service: HRService = Depends(_get_service)):
    active = service.get_active()
    if active is None:
        return JSONResponse(
            status_code=404,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="NOT_FOUND", message="No hay versión HR activa."),
            ).model_dump(),
        )
    return ApiResponse.ok(active)


@router.get(
    "/{version_id}/activate",
    summary="Activar versión HR",
    description="Activa una versión específica de parametrización de Recursos Humanos.",
    operation_id="activateHrVersion",
)
def activate_hr(
    version_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
    service: HRService = Depends(_get_service),
):
    summary = service.activate(version_id)
    _version_registry.invalidate_cache()
    return ApiResponse.ok(summary.model_dump())


@router.delete(
    "/{version_id}",
    summary="Eliminar versión HR",
    description="Elimina una versión específica de parametrización de Recursos Humanos.",
    operation_id="deleteHrVersion",
    status_code=200,
)
def delete_hr(
    version_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
    service: HRService = Depends(_get_service),
):
    service.delete(version_id)
    return ApiResponse.ok(None)
