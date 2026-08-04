"""
GET endpoints para resultados de simulación v2.

GET /api/v2/simulation/{simulation_id}/results/vision-pyg
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Path, Request

from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.shared.exceptions import NotFoundError
from .results_repository import V2SimulationResultsRepository

logger = logging.getLogger("nexa.v2.results_router")

router = APIRouter(prefix="/simulation", tags=["Simulation v2 Results"])


@router.get(
    "/{simulation_id}/results/vision-pyg",
    response_model=ApiResponse,
    summary="Visión P&G de una simulación v2",
    operation_id="getVisionPygV2",
)
async def get_vision_pyg_v2(
    request: Request,
    simulation_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
) -> ApiResponse:
    """Retorna la Visión P&G completa de una simulación v2 previamente calculada."""
    container = request.app.state.container
    repo = V2SimulationResultsRepository(container.configuration_store)

    try:
        doc = repo.get(simulation_id)
    except NotFoundError:
        return ApiResponse.fail(
            "SIM-00600",
            message=f"Simulación v2 no encontrada: {simulation_id}",
        )

    return ApiResponse.ok(
        data={
            "simulation_id": simulation_id,
            "cliente": doc.get("cliente"),
            "servicio": doc.get("servicio"),
            "duracion_meses": doc.get("duracion_meses"),
            "calculated_at": doc.get("calculated_at"),
            "vision_pyg": doc.get("vision_pyg", {}),
            "totales": doc.get("totales", {}),
        }
    )
