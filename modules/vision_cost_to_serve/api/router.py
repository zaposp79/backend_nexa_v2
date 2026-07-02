"""Cost To Serve — HTTP endpoint (public/read-only layer).

GET /simulation/{simulation_id}/results/cost-to-serve
Returns the screen-ready CTS contract from persisted calculation results.

Ownership:
  API:   vision_cost_to_serve · reads stored result via ResultsRepository.
  Charts: helpers/charts_mapper.py — pure composition from persisted data.
  Formulas: calculator_motor · CostToServeCalculator in formulas/cts/calculator.py.

No formula logic here — only wire protocol.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path

from nexa_engine.db.dependencies import get_results_repository
from nexa_engine.modules.calculator.persistence.results_repository import ResultsRepository
from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.vision_cost_to_serve.api.response_models import VisionCostToServeApiResponseV1
from nexa_engine.modules.vision_cost_to_serve.helpers.screen_mapper import (
    build_vision_cts_from_result,
)

router = APIRouter(prefix="/simulation", tags=["Vision Cost To Serve"])

CHARTS_VERSION = "1.0"



@router.get(
    "/{simulation_id}/results/cost-to-serve",
    summary="Obtener visión de Cost-to-Serve",
    description="CTS por cadena con desgloses, canales y estructura del equipo. Equivale a la hoja 'Vision CTS' del Excel V2-7.",
    operation_id="getVisionCostToServe",
    response_model=VisionCostToServeApiResponseV1,
)
def get_cost_to_serve(
    simulation_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
    repo: ResultsRepository = Depends(get_results_repository),
) -> ApiResponse:
    """Return Cost To Serve data with charts.

    Returns:
        ApiResponse with the screen-ready frontend contract:
          - header
          - summary_cards
          - sections
          - charts
          - metadata

    Raises:
        HTTPException(404): if simulation_id not found
    """
    try:
        resultado_simulacion = repo.get(simulation_id)
        payload = build_vision_cts_from_result(resultado_simulacion)
        return ApiResponse.ok(payload, meta={"charts_version": CHARTS_VERSION})
    except NotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=exc.message,
        )
