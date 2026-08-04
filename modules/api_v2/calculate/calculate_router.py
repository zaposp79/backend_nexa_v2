"""
Endpoints del motor de cálculo v2.

POST /api/v2/simulation/calculate  — ejecutar simulación con motor rubros_maestro
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from nexa_engine.modules.shared.responses import ApiResponse
from .calculate_dto import CalculationRequestV2
from .calculate_handler import handle_calculate_v2

logger = logging.getLogger("nexa.v2.router")

router = APIRouter(prefix="/simulation", tags=["Simulation v2"])


@router.post("/calculate", response_model=ApiResponse)
async def calculate_v2(body: CalculationRequestV2, request: Request) -> ApiResponse:
    """Motor de cálculo v2 basado en rubros_maestro de Cosmos DB.

    Ejecuta el pipeline de 10 capas, persiste en el container 'simulation'
    (type='results_v2') y retorna un resumen con el simulation_id.
    """
    container = request.app.state.container

    return handle_calculate_v2(
        request_data=body.user_input,
        param_store=container.parametrization_store,
        results_store=container.configuration_store,
        id_draft=body.id_draft,
        client_id=body.client_id,
    )
