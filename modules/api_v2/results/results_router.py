"""
GET endpoints para resultados de simulación v2.

GET /api/v2/simulation/{simulation_id}/results/vision-pyg
GET /api/v2/simulation/{simulation_id}/results/vision-cost-to-serve
GET /api/v2/simulation/{simulation_id}/results/vision/modelo-cobro
GET /api/v2/simulation/{simulation_id}/results/vision-imprimible
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


@router.get(
    "/{simulation_id}/results/vision-cost-to-serve",
    response_model=ApiResponse,
    summary="Visión Cost-to-Serve de una simulación v2",
    operation_id="getVisionCostToServeV2",
)
async def get_vision_cost_to_serve_v2(
    request: Request,
    simulation_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
) -> ApiResponse:
    """Retorna la Visión Cost-to-Serve de una simulación v2 previamente calculada."""
    container = request.app.state.container
    repo = V2SimulationResultsRepository(container.configuration_store)

    try:
        doc = repo.get(simulation_id)
    except NotFoundError:
        return ApiResponse.fail(
            "SIM-00601",
            message=f"Simulación v2 no encontrada: {simulation_id}",
        )

    vision_cts = doc.get("vision_cts")
    if not vision_cts:
        return ApiResponse.fail(
            "SIM-00602",
            message="Esta simulación no contiene Visión Cost-to-Serve. Recalcule con la versión actual del motor.",
        )

    return ApiResponse.ok(
        data={
            "simulation_id": simulation_id,
            "cliente": doc.get("cliente"),
            "servicio": doc.get("servicio"),
            "duracion_meses": doc.get("duracion_meses"),
            "calculated_at": doc.get("calculated_at"),
            "vision_cts": vision_cts,
        }
    )


@router.get(
    "/{simulation_id}/results/vision/modelo-cobro",
    response_model=ApiResponse,
    summary="Visión Tarifas / Modelo de Cobro de una simulación v2",
    operation_id="getVisionModeloCobroV2",
)
async def get_vision_modelo_cobro_v2(
    request: Request,
    simulation_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
) -> ApiResponse:
    """Retorna la Visión Tarifas (modelo de cobro por escenario) de una simulación v2."""
    container = request.app.state.container
    repo = V2SimulationResultsRepository(container.configuration_store)

    try:
        doc = repo.get(simulation_id)
    except NotFoundError:
        return ApiResponse.fail(
            "SIM-00605",
            message=f"Simulación v2 no encontrada: {simulation_id}",
        )

    vision_tarifas = doc.get("vision_tarifas")
    if not vision_tarifas:
        return ApiResponse.fail(
            "SIM-00606",
            message="Esta simulación no contiene Visión Tarifas. Recalcule con la versión actual del motor.",
        )

    return ApiResponse.ok(
        data={
            "simulation_id": simulation_id,
            "cliente": doc.get("cliente"),
            "servicio": doc.get("servicio"),
            "duracion_meses": doc.get("duracion_meses"),
            "calculated_at": doc.get("calculated_at"),
            "vision_tarifas": vision_tarifas,
        }
    )


@router.get(
    "/{simulation_id}/results/vision-imprimible",
    response_model=ApiResponse,
    summary="Visión Imprimible de una simulación v2",
    operation_id="getVisionImprimibleV2",
)
async def get_vision_imprimible_v2(
    request: Request,
    simulation_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
) -> ApiResponse:
    """Retorna la Visión Imprimible (7 secciones) de una simulación v2 previamente calculada."""
    container = request.app.state.container
    repo = V2SimulationResultsRepository(container.configuration_store)

    try:
        doc = repo.get(simulation_id)
    except NotFoundError:
        return ApiResponse.fail(
            "SIM-00603",
            message=f"Simulación v2 no encontrada: {simulation_id}",
        )

    vision_imprimible = doc.get("vision_imprimible")
    if not vision_imprimible:
        return ApiResponse.fail(
            "SIM-00604",
            message="Esta simulación no contiene Visión Imprimible. Recalcule con la versión actual del motor.",
        )

    return ApiResponse.ok(
        data={
            "simulation_id": simulation_id,
            "cliente": doc.get("cliente"),
            "servicio": doc.get("servicio"),
            "duracion_meses": doc.get("duracion_meses"),
            "calculated_at": doc.get("calculated_at"),
            "vision_imprimible": vision_imprimible,
        }
    )
