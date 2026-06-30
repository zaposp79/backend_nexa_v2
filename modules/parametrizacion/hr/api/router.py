"""Endpoints de parametrización HR."""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status

from nexa_engine.modules.parametrizacion.hr.services.hr_service import HRService
from nexa_engine.modules.shared.exceptions import DomainError, NotFoundError, UploadError, ValidationError
from nexa_engine.modules.shared.config.config import (
    ALLOWED_EXCEL_EXTENSIONS,
    MAX_EXCEL_UPLOAD_BYTES,
)
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.shared.versioning.registry_provider import _version_registry

router = APIRouter(prefix="/parametrization/hr", tags=["Parametrization"])
_service: HRService | None = None


def _get_service(request: Request) -> HRService:
    if _service is not None:
        return _service
    return request.app.state.container.hr_upload_service


def _check_extension(filename: str) -> None:
    from pathlib import Path
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXCEL_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido ('{ext}'). Solo se acepta .xlsx.",
        )


@router.post(
    "/upload",
    summary="Subir archivo Excel HR",
    description="Carga y procesa un archivo Excel de parametrización de Recursos Humanos.",
    operation_id="uploadHr",
)
async def upload_hr(file: UploadFile = File(...), service: HRService = Depends(_get_service)):
    _check_extension(file.filename or "")

    file_bytes = await file.read(MAX_EXCEL_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_EXCEL_UPLOAD_BYTES:
        return ApiResponse.fail(
            "EXCEL_LIMIT_EXCEEDED",
            "El archivo supera el tamaño máximo permitido.",
        )

    try:
        resp = service.process_upload(file.filename or "upload.xlsx", file_bytes)
        return ApiResponse.ok(resp.model_dump())
    except ValidationError as exc:
        return ApiResponse.fail("VALIDATION_ERROR", exc.message, details=exc.errors)
    except UploadError as exc:
        return ApiResponse.fail(exc.code, exc.message)
    except DomainError:
        return ApiResponse.fail("DOMAIN_ERROR", "Error procesando el archivo.")


@router.get(
    "/versions",
    summary="Listar versiones HR",
    description="Retorna el listado de versiones subidas de parametrización de Recursos Humanos.",
    operation_id="listHrVersions",
)
def list_hr_versions(service: HRService = Depends(_get_service)):
    versions = service.list_versions()
    return ApiResponse.ok([v.model_dump() for v in versions])


@router.get(
    "/active",
    summary="Obtener versión HR activa",
    description="Retorna la versión activa actual de parametrización de Recursos Humanos.",
    operation_id="getHrActiveVersion",
)
def get_hr_active(service: HRService = Depends(_get_service)):
    active = service.get_active()
    if active is None:
        return ApiResponse.fail("NOT_FOUND", "No hay versión HR activa.")
    return ApiResponse.ok(active)


@router.get(
    "/{version_id}/activate",
    summary="Activar versión HR",
    description="Activa una versión específica de parametrización de Recursos Humanos.",
    operation_id="activateHrVersion",
)
def activate_hr(version_id: str, service: HRService = Depends(_get_service)):
    try:
        summary = service.activate(version_id)
        _version_registry.invalidate_cache()
        return ApiResponse.ok(summary.model_dump())
    except NotFoundError:
        return ApiResponse.fail("NOT_FOUND", "Versión no encontrada.")


@router.delete(
    "/{version_id}",
    summary="Eliminar versión HR",
    description="Elimina una versión específica de parametrización de Recursos Humanos.",
    operation_id="deleteHrVersion",
)
def delete_hr(version_id: str, service: HRService = Depends(_get_service)):
    try:
        service.delete(version_id)
        return ApiResponse.ok(None)
    except NotFoundError:
        return ApiResponse.fail("NOT_FOUND", "Versión no encontrada.")
    except DomainError:
        return ApiResponse.fail("DOMAIN_ERROR", "Error procesando la operación.")
