"""
POST /api/v1/simulation/calculate
===================================
Endpoint de ejecución del motor de precios NEXA.

Flujo completo:
  1. Recibe user_input (inputs del deal)
  2. Ejecuta el motor de precios (10 capas de cálculo)
  3. Valida que todas las visiones fueron construidas
  4. Persiste el resultado en storage/simulation_results/{simulation_id}.json
  5. Devuelve el simulation_id para consultar las visiones via GET

Visiones consultables tras el cálculo:
  GET /simulation/{simulation_id}/results/vision-imprimible  → 6 secciones imprimibles
  GET /simulation/{simulation_id}/results/vision-pyg         → Vision P&G estructurado
  GET /simulation/{simulation_id}/results/vision-tarifas     → Tarifas por canal
  GET /simulation/{simulation_id}/results/cost-to-serve      → Cost To Serve

Flujo de datos garantizado:
  entry_data → dominio → calculadoras → visiones oficiales → persistencia → simulation_id

Estructura (FASE Y Batch 4b — partición):
  calculate_router.py            → router + endpoint /calculate (este archivo)
  calculate_dto.py               → CalculationRequest
  calculate_dependencies.py      → singletons (results/trace/snapshot repos)
  calculate_normal_handler.py    → _calculate_normal
  calculate_certified_handler.py → _calculate_certified (WAVE 15)
  calculate_validate.py          → validate_input (diagnóstico)
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from nexa_engine.modules.calculator.api.calculate_dto import CalculationRequest
from nexa_engine.modules.calculator.api.calculate_normal_handler import _calculate_normal
from nexa_engine.modules.calculator.api.calculate_certified_handler import _calculate_certified

router = APIRouter(prefix="/simulation", tags=["Simulations"])


@router.post(
    "/calculate",
    status_code=201,
    response_model=None,
    summary="Ejecutar simulación de pricing",
    description="Recibe inputs del deal (panel + 3 cadenas), ejecuta el motor de 10 capas, persiste el resultado y devuelve simulation_id.",
    operation_id="createSimulation",
)
def calculate(
    body: CalculationRequest,
    mode: Literal["normal", "certified"] = Query(
        "normal",
        description="Execution mode. Use 'certified' to enforce baseline hashes and emit an ExecutionCertificate.",
    ),
):
    # WAVE 15 — body-level override: ``metadata.mode = "certified"``.
    body_mode = (body.user_input.get("metadata") or {}).get("mode") if isinstance(body.user_input, dict) else None
    effective_mode = mode
    if body_mode == "certified":
        effective_mode = "certified"

    if effective_mode == "certified":
        return _calculate_certified(body)
    return _calculate_normal(body)
