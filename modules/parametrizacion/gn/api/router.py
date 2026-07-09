"""Endpoints de parametrización GN."""

from uuid import UUID

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
from nexa_engine.modules.shared.exceptions import NotFoundError, ValidationError
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
    file: UploadFile | None = File(None),
    user_id: str = Query(default="anonymous"),
    service: GNService = Depends(_get_service),
):
    if file is None or not file.filename:
        return JSONResponse(
            status_code=400,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="VALIDATION_ERROR", message="No se cargó ningún archivo, es necesario."),
            ).model_dump(),
        )
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
    "/{id}",
    summary="Obtener versión GN por ID",
    description="Retorna el documento completo de una versión GN desde Cosmos, filtrando por domain='gn' y el UUID4 indicado.",
    operation_id="getGnVersionById",
    responses={
        200: {"description": "Documento encontrado"},
        404: {"description": "Versión no encontrada"},
        422: {"description": "UUID inválido o no es versión 4"},
    },
)
def get_gn_by_id(
    id: UUID = Path(..., description="UUID4 del documento GN a consultar"),
    service: GNService = Depends(_get_service),
):
    if id.version != 4:
        return JSONResponse(
            status_code=422,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="VALIDATION_ERROR", message="El parámetro 'id' debe ser un UUID versión 4 válido."),
            ).model_dump(),
        )
    try:
        doc = service.get_by_id(str(id))
    except NotFoundError as e:
        return JSONResponse(
            status_code=404,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="NOT_FOUND", message=str(e)),
            ).model_dump(),
        )
    return ApiResponse.ok(doc)


@router.patch(
    "/{id}/activate",
    summary="Activar versión GN",
    description="Activa una versión GN por UUID4 en Cosmos, desactivando las demás del mismo domain.",
    operation_id="activateGnVersion",
    responses={
        200: {"description": "Versión activada correctamente"},
        404: {"description": "Versión no encontrada"},
        422: {"description": "UUID inválido o no es versión 4"},
    },
)
def activate_gn(
    id: UUID = Path(..., description="UUID4 del documento GN a activar"),
    service: GNService = Depends(_get_service),
):
    if id.version != 4:
        return JSONResponse(
            status_code=422,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="VALIDATION_ERROR", message="El parámetro 'id' debe ser un UUID versión 4 válido."),
            ).model_dump(),
        )
    try:
        summary = service.activate(str(id))
    except ValidationError as e:
        return JSONResponse(
            status_code=422,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=str(e.message),
                    details=e.errors if e.errors else None,
                ),
            ).model_dump(),
        )
    except NotFoundError as e:
        return JSONResponse(
            status_code=404,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="NOT_FOUND", message=str(e)),
            ).model_dump(),
        )
    _version_registry.invalidate_cache()
    return ApiResponse.ok(summary.model_dump())


@router.delete(
    "/{id}",
    summary="Eliminar versión GN",
    description="Elimina una versión específica de parametrización de Gastos de Negociación por su UUID4.",
    operation_id="deleteGnVersion",
    status_code=200,
)
def delete_gn(
    id: UUID = Path(..., description="UUID4 del documento GN a eliminar"),
    service: GNService = Depends(_get_service),
):
    if id.version != 4:
        return JSONResponse(
            status_code=422,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="VALIDATION_ERROR", message="El parámetro 'id' debe ser un UUID versión 4 válido."),
            ).model_dump(),
        )
    try:
        service.delete(str(id))
    except NotFoundError as e:
        return JSONResponse(
            status_code=404,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code="NOT_FOUND", message=str(e)),
            ).model_dump(),
        )
    return ApiResponse.ok(None)
