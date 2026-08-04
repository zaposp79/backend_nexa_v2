"""
Handler del Motor de Reglas v2.

Pipeline:
  1. Ejecutar MotorDeReglas.calcular(request_data)
  2. Persistir resultado en container 'simulation' (mismo que v1, type='results_v2')
  3. Retornar respuesta simple: simulation_id, id_draft, client_id, timestamp
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.calculator_v2.rubros_repository import RubrosRepository  # type: ignore[import]
from nexa_engine.modules.calculator_v2.engine import MotorDeReglas  # type: ignore[import]
from nexa_engine.modules.calculator_v2.models import SimulationResultV2  # type: ignore[import]
from nexa_engine.modules.api_v2.results.results_repository import V2SimulationResultsRepository  # type: ignore[import]

logger = logging.getLogger("nexa.motor_reglas.handler")


def handle_calculate_v2(
    request_data: Dict[str, Any],
    param_store: DocumentStore,
    results_store: DocumentStore,
    id_draft: Optional[str] = None,
    client_id: Optional[str] = None,
) -> ApiResponse:
    """Ejecuta el motor v2, persiste en Cosmos y retorna respuesta simple."""

    rubros_repo = RubrosRepository(param_store)
    engine = MotorDeReglas(rubros_repo)

    try:
        result: SimulationResultV2 = engine.calcular(request_data)
    except Exception as exc:
        logger.exception("[v2] Error ejecutando motor de cálculo: %s", exc)
        return ApiResponse.fail("SIM-00700", message=f"Error en Motor de Reglas: {exc}")

    # client_id: explícito en el request, o fallback a datos_operativos.cliente
    effective_client_id = client_id or (
        request_data.get("datos_operativos", {}).get("cliente") or ""
    )

    doc = {
        "id": result.simulation_id,
        "client_id": effective_client_id,
        "type": "results_v2",
        "domain": "simulation",
        "id_draft": id_draft,
        "simulation_id": result.simulation_id,
        "version": "v2",
        "motor": "motor_de_reglas",
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "cliente": result.cliente,
        "servicio": result.servicio,
        "duracion_meses": result.duracion_meses,
        "vision_pyg": result.vision_pyg.model_dump(),
        "meses": [m.model_dump() for m in result.meses],
        "totales": result.totales,
    }

    repo = V2SimulationResultsRepository(results_store)
    try:
        repo.save(doc)
    except Exception as exc:
        logger.warning("[v2] No se pudo persistir resultado (sim=%s): %s", result.simulation_id, exc)

    return ApiResponse.ok(
        data={
            "id": result.simulation_id,
            "id_draft": id_draft,
            "client_id": effective_client_id,
            "message": "Cálculo guardado correctamente",
            "timestamp": doc["calculated_at"],
        },
        meta={"version": "v2", "motor": "motor_de_reglas"},
    )
