"""Vision P&G — HTTP endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from nexa_engine.db.dependencies import get_results_repository
from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.calculator.persistence.results_repository import ResultsRepository
from nexa_engine.modules.vision_pyg.api.response_models import VisionPygApiResponseV1
from nexa_engine.modules.vision_pyg.helpers.screen_mapper import (
    build_vision_pyg_from_result,
)

router = APIRouter(prefix="/simulation", tags=["Vision PYG"])

@router.get(
    "/{simulation_id}/results/vision-pyg",
    summary="Obtener visión de Pérdidas y Ganancias",
    description="Retorna el contrato screen-ready para frontend a partir del vision_pyg persistido.",
    operation_id="getVisionPyg",
    response_model=VisionPygApiResponseV1,
)
def get_vision_pyg(
    simulation_id: str,
    repo: ResultsRepository = Depends(get_results_repository),
):
    try:
        data = repo.get(simulation_id)
        payload = build_vision_pyg_from_result(data, simulation_id=simulation_id)
        return ApiResponse.ok(payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)
