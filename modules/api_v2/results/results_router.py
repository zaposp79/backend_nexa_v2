"""
Endpoints para resultados de simulación v2.

GET    /api/v2/simulation/results                                    — lista de todas las simulaciones
GET    /api/v2/simulation/{id_draft}/results?client_id=...           — simulaciones por id_draft
DELETE /api/v2/simulation/results/{id}                               — eliminar simulación por id
GET    /api/v2/simulation/{simulation_id}/results/vision-pyg
GET    /api/v2/simulation/{simulation_id}/results/vision-cost-to-serve
GET    /api/v2/simulation/{simulation_id}/results/vision/modelo-cobro
GET    /api/v2/simulation/{simulation_id}/results/vision-imprimible
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Path, Query, Request

from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.shared.exceptions import NotFoundError
from .results_repository import V2SimulationResultsRepository
from nexa_engine.modules.calculator_v2.vision_pyg_periods_builder import build_vision_pyg_periods

logger = logging.getLogger("nexa.v2.results_router")

router = APIRouter(prefix="/simulation", tags=["Simulation v2 Results"])


@router.get(
    "/results",
    response_model=ApiResponse,
    summary="Listado de simulaciones v2 calculadas",
    operation_id="listSimulationsV2",
)
async def list_simulations_v2(
    request: Request,
    client_id: Optional[str] = Query(None, description="Filtrar por client_id"),
    limit: int = Query(50, ge=1, le=200, description="Máximo de resultados"),
) -> ApiResponse:
    """Devuelve un resumen de todas las simulaciones v2 persistidas.

    Cada item incluye solo los campos de cabecera; no retorna meses ni visiones.
    """
    container = request.app.state.container
    repo = V2SimulationResultsRepository(container.configuration_store)

    simulations = repo.list_simulations(client_id=client_id, limit=limit)
    return ApiResponse.ok(
        data={"simulations": simulations, "total": len(simulations)},
        meta={"version": "v2", "limit": limit},
    )


@router.delete(
    "/results/{id}",
    response_model=ApiResponse,
    summary="Eliminar simulación v2 por ID",
    operation_id="deleteSimulationV2",
)
async def delete_simulation_v2(
    request: Request,
    id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$", description="ID de la simulación a eliminar"),
) -> ApiResponse:
    """Elimina una simulación v2 previamente calculada.

    Solo elimina documentos de tipo `results_v2`. Si el ID corresponde a un
    documento v1 o no existe, retorna error sin modificar nada.
    """
    container = request.app.state.container
    repo = V2SimulationResultsRepository(container.configuration_store)

    try:
        deleted = repo.delete_simulation(id)
    except NotFoundError:
        return ApiResponse.fail(
            "SIM-00800",
            message=f"Simulación no encontrada: {id}",
        )
    except ValueError as exc:
        return ApiResponse.fail(
            "SIM-00801",
            message=str(exc),
        )

    return ApiResponse.ok({"deleted": True, "id": id})


@router.get(
    "/{id_draft}/results",
    response_model=ApiResponse,
    summary="Simulaciones v2 por id_draft",
    operation_id="listSimulationsByDraftV2",
)
async def list_simulations_by_draft_v2(
    request: Request,
    id_draft: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
    client_id: Optional[str] = Query(None, description="Filtrar adicionalmente por client_id"),
    limit: int = Query(50, ge=1, le=200, description="Máximo de resultados"),
) -> ApiResponse:
    """Devuelve las simulaciones v2 asociadas a un id_draft específico."""
    container = request.app.state.container
    repo = V2SimulationResultsRepository(container.configuration_store)

    simulations = repo.list_simulations(client_id=client_id, id_draft=id_draft, limit=limit)
    return ApiResponse.ok(
        data={"simulations": simulations, "total": len(simulations)},
        meta={"version": "v2", "id_draft": id_draft, "limit": limit},
    )


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

    periods_data = build_vision_pyg_periods(doc)
    return ApiResponse.ok(
        data={
            "version": doc.get("version", "v2"),
            "simulation_id": simulation_id,
            "header": {
                "cliente": doc.get("cliente"),
                "servicio": doc.get("servicio"),
                "duracion_meses": doc.get("duracion_meses"),
                "fecha_inicio": doc.get("fecha_inicio"),
            },
            **periods_data,
            "metadata": {
                "source": "motor_de_reglas_v2",
                "calculated_at": doc.get("calculated_at"),
                "omitted_empty_fields": False,
            },
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
            "header": {
                "cliente":            doc.get("cliente"),
                "servicio":           doc.get("servicio"),
                "tipo_cliente":       doc.get("tipo_cliente"),
                "antiguedad_cliente": doc.get("antiguedad_cliente"),
                "periodo_pago":       doc.get("periodo_pago"),
                "fecha_inicio":       doc.get("fecha_inicio"),
                "duracion_meses":     doc.get("duracion_meses"),
                "ciudad":             doc.get("ciudad"),
                "sede":               doc.get("sede"),
            },
            "calculated_at": doc.get("calculated_at"),
            "vision_imprimible": vision_imprimible,
        }
    )
