"""Endpoints de parametrización OP."""

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, UploadFile, File
from fastapi.responses import JSONResponse

from nexa_engine.modules.parametrizacion.op.services.op_service import OPService
from nexa_engine.modules.parametrizacion.shared.helpers.upload_guards import (
    check_filename_prefix,
    check_file_extension,
    check_file_size,
    sanitize_user_id,
)
from nexa_engine.modules.shared.config.config import MAX_EXCEL_UPLOAD_BYTES
from nexa_engine.modules.shared.exceptions import NotFoundError, ValidationError
from nexa_engine.modules.shared.responses import ApiResponse, ErrorDetail
from nexa_engine.modules.shared.error_catalog import make_detail as _make_detail
from nexa_engine.modules.shared.versioning.registry_provider import _version_registry

router = APIRouter(prefix="/parametrization/op", tags=["parametrization-op"])
_service: OPService | None = None


def _get_service(request: Request) -> OPService:
    if _service is not None:
        return _service
    return request.app.state.container.op_upload_service


@router.post(
    "/upload",
    summary="Subir archivo Excel OP",
    description="Carga y procesa un archivo Excel de parametrización de Gastos de Operación.",
    operation_id="uploadOp",
    status_code=201,
)
async def upload_op(
    file: UploadFile | None = File(None),
    user_id: str = Query(default="anonymous"),
    service: OPService = Depends(_get_service),
):
    if file is None or not file.filename:
        return JSONResponse(
            status_code=400,
            content=ApiResponse(success=False, error=_make_detail("SIM-00501")).model_dump(),
        )
    filename = file.filename or ""
    check_filename_prefix(filename, "OP")
    check_file_extension(filename)
    file_bytes = await file.read(MAX_EXCEL_UPLOAD_BYTES + 1)
    check_file_size(file_bytes)
    user_id = sanitize_user_id(user_id)
    resp = service.process_upload(filename or "upload.xlsx", file_bytes, user_id=user_id)
    return ApiResponse.ok(resp.model_dump())


@router.get(
    "/versions",
    summary="Listar versiones OP",
    description="Retorna el listado de versiones subidas de parametrización de Gastos de Operación.",
    operation_id="listOpVersions",
)
def list_op_versions(service: OPService = Depends(_get_service)):
    return ApiResponse.ok([v.model_dump() for v in service.list_versions()])



@router.get(
    "/{id}",
    summary="Obtener versión OP por ID",
    description="Retorna el documento completo de una versión OP desde Cosmos, filtrando por domain='op' y el UUID4 indicado.",
    operation_id="getOpVersionById",
    responses={
        200: {"description": "Documento encontrado"},
        404: {"description": "Versión no encontrada"},
        422: {"description": "UUID inválido o no es versión 4"},
    },
)
def get_op_by_id(
    id: UUID = Path(..., description="UUID4 del documento OP a consultar"),
    service: OPService = Depends(_get_service),
):
    if id.version != 4:
        return JSONResponse(
            status_code=422,
            content=ApiResponse(success=False, error=_make_detail("SIM-00502")).model_dump(),
        )
    try:
        doc = service.get_by_id(str(id))
    except NotFoundError as e:
        return JSONResponse(
            status_code=404,
            content=ApiResponse(success=False, error=_make_detail("SIM-00600", message=str(e))).model_dump(),
        )
    return ApiResponse.ok(doc)


@router.patch(
    "/{id}/activate",
    summary="Activar versión OP",
    description="Activa una versión OP por UUID4 en Cosmos, desactivando las demás del mismo domain.",
    operation_id="activateOpVersion",
    responses={
        200: {"description": "Versión activada correctamente"},
        404: {"description": "Versión no encontrada"},
        422: {"description": "UUID inválido o no es versión 4"},
    },
)
def activate_op(
    id: UUID = Path(..., description="UUID4 del documento OP a activar"),
    service: OPService = Depends(_get_service),
):
    if id.version != 4:
        return JSONResponse(
            status_code=422,
            content=ApiResponse(success=False, error=_make_detail("SIM-00502")).model_dump(),
        )
    try:
        summary = service.activate(str(id))
    except ValidationError as e:
        return JSONResponse(
            status_code=422,
            content=ApiResponse(
                success=False,
                error=_make_detail(getattr(e, "sim_code", "SIM-00506"), message=str(e.message), details=e.errors if e.errors else None),
            ).model_dump(),
        )
    except NotFoundError as e:
        return JSONResponse(
            status_code=404,
            content=ApiResponse(success=False, error=_make_detail("SIM-00600", message=str(e))).model_dump(),
        )
    _version_registry.invalidate_cache()
    return ApiResponse.ok(summary.model_dump())


@router.delete(
    "/{id}",
    summary="Eliminar versión OP",
    description="Elimina una versión específica de parametrización de Gastos de Operación por su UUID4.",
    operation_id="deleteOpVersion",
    status_code=200,
)
def delete_op(
    id: UUID = Path(..., description="UUID4 del documento OP a eliminar"),
    service: OPService = Depends(_get_service),
):
    if id.version != 4:
        return JSONResponse(
            status_code=422,
            content=ApiResponse(success=False, error=_make_detail("SIM-00502")).model_dump(),
        )
    try:
        service.delete(str(id))
    except NotFoundError as e:
        return JSONResponse(
            status_code=404,
            content=ApiResponse(success=False, error=_make_detail("SIM-00600", message=str(e))).model_dump(),
        )
    return ApiResponse.ok(None)
