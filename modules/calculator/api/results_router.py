"""
GET /api/v1/simulation/{simulation_id}/results/...
===================================================
Endpoints de consulta de resultados de cálculo y trazabilidad contractual.

Expone el documento persistido completo y la clasificación ligera de
traceability derivada del resultado almacenado.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from nexa_engine.db.dependencies import get_results_repository
from nexa_engine.modules.calculator.persistence.results_repository import ResultsRepository
from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.shared.responses import ApiResponse, ErrorDetail
from nexa_engine.modules.audit.registry import FieldTraceabilityRegistry
from nexa_engine.modules.vision_imprimible.api.public_mapper import build_public_vision_imprimible
from nexa_engine.modules.vision_imprimible.api.response_models import VisionImprimibleApiResponseV1

router = APIRouter(prefix="/simulation", tags=["Simulations"])


def _not_found_response(simulation_id: str, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(code="NOT_FOUND", message=exc.message),
        ).model_dump(),
    )


@router.get("/{simulation_id}/results", response_model=VisionImprimibleApiResponseV1)
def get_results(
    simulation_id: str,
    repo: ResultsRepository = Depends(get_results_repository),
):
    """
    Respuesta pública de una ejecución, limitada a la hoja Visión Imprimible.

    El documento técnico completo permanece persistido para auditoría y para
    las rutas especializadas, pero no se expone en este endpoint.
    """
    try:
        data = repo.get(simulation_id)
        return ApiResponse.ok(build_public_vision_imprimible(data))
    except NotFoundError as exc:
        return _not_found_response(simulation_id, exc)


@router.get("/{simulation_id}/traceability")
def get_traceability(
    simulation_id: str,
    repo: ResultsRepository = Depends(get_results_repository),
):
    """Trazabilidad contractual persistida para una simulación."""
    try:
        data = repo.get(simulation_id)
        return ApiResponse.ok(FieldTraceabilityRegistry().build(data))
    except NotFoundError as exc:
        return _not_found_response(simulation_id, exc)
