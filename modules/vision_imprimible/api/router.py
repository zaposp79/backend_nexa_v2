"""Vision Imprimible — HTTP endpoint.

GET /simulation/{simulation_id}/results/vision-imprimible
Returns the screen-ready contract for the canonical printable deal view.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from nexa_engine.db.dependencies import get_results_repository
from nexa_engine.modules.calculator.persistence.results_repository import ResultsRepository
from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.shared.responses import ApiResponse, ErrorDetail
from nexa_engine.modules.vision_imprimible.api.public_mapper import build_public_vision_imprimible
from nexa_engine.modules.vision_imprimible.api.response_models import VisionImprimibleApiResponseV1

router = APIRouter(prefix="/simulation", tags=["Vision Imprimible"])



def _not_found(simulation_id: str, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(code="NOT_FOUND", message=exc.message),
        ).model_dump(),
    )


@router.get(
    "/{simulation_id}/results/vision-imprimible",
    response_model=VisionImprimibleApiResponseV1,
    summary="Obtener visión imprimible del deal",
    description=(
        "Contrato screen-ready de la Visión Imprimible: header, summary cards, "
        "sections, charts y metadata basados solo en el resultado persistido."
    ),
    operation_id="getVisionImprimible",
)
def get_vision_imprimible(
    simulation_id: str,
    repo: ResultsRepository = Depends(get_results_repository),
):
    try:
        data = repo.get(simulation_id)
        return ApiResponse.ok(build_public_vision_imprimible(data))
    except NotFoundError as exc:
        return _not_found(simulation_id, exc)
