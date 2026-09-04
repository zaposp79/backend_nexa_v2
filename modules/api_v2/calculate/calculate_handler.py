"""
Handler del Motor de Reglas v2.

Pipeline:
  1. Ejecutar MotorDeReglas.calcular(request_data)
  2. Persistir resultado en container 'simulation' (mismo que v1, type='results_v2')
  3. Retornar respuesta simple: simulation_id, id_draft, client_id, timestamp
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

# Colombia no observa horario de verano — UTC-5 permanente
_TZ_CO = timezone(timedelta(hours=-5))

from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.calculator_v2.rubros_repository import RubrosRepository  # type: ignore[import]
from nexa_engine.modules.calculator_v2.engine import MotorDeReglas  # type: ignore[import]
from nexa_engine.modules.calculator_v2.models import SimulationResultV2  # type: ignore[import]
from nexa_engine.modules.api_v2.results.results_repository import V2SimulationResultsRepository  # type: ignore[import]

logger = logging.getLogger("nexa.motor_reglas.handler")


_MED_SEG_COST_KEYS = [
    "costo_examen_medico_inicial",
    "costo_examen_medico_rotacion",
    "costo_examen_medico_anual",
    "costo_estudio_prelim_inicial",
    "costo_estudio_prelim_rotacion",
    "costo_estudio_final_inicial",
    "costo_estudio_final_rotacion",
]


def _inject_med_seg_costs(request_data: Dict[str, Any], param_store: DocumentStore) -> None:
    """Enriquece datos_operativos con costos HR-Med-Seg ponderados por ciudad.

    Replica la fórmula Excel:
      NL!C329 = SUMPRODUCT(Rot!B67:F67 × Rot!B66:F66)
    donde Rot!B66:F66 = proporciones de ciudad desde PCG!B28:C31.

    Para cada ciudad en ciudades_recurso, obtiene los 7 costos de HR-Med-Seg
    y calcula el promedio ponderado: cost = Σ(costo_ciudad × proporcion).
    Fallback: si ciudades_recurso está vacío, usa datos_operativos.ciudad al 100%.
    Solo inyecta si el campo NO viene ya explícito en el request.
    """
    try:
        from nexa_engine.modules.parametrizacion.hr.repositories.hr_active_parametrization_repository import (
            HRActiveParametrizationRepository,
        )
        from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver
        from nexa_engine.modules.parametrizacion.repositories.infrastructure_parametrization_repository import (
            InfrastructureParametrizationRepository,
        )

        hr_repo = HRActiveParametrizationRepository(param_store)
        resolver = ParametrizationResolver(hr_repo=hr_repo)
        infra = InfrastructureParametrizationRepository(resolver)

        datos_op = request_data.setdefault("datos_operativos", {})

        # Leer tabla de ciudades con proporciones (PCG!B28:C31)
        ciudades_recurso = datos_op.get("ciudades_recurso") or []
        if not ciudades_recurso:
            ciudad = str(datos_op.get("ciudad") or "")
            if ciudad:
                ciudades_recurso = [{"ciudad": ciudad, "proporcion": 1.0}]

        if not ciudades_recurso:
            return

        # Normalizar proporciones (por si no suman exactamente 1.0)
        total_prop = sum(float(c.get("proporcion") or 0) for c in ciudades_recurso)
        if total_prop <= 0:
            logger.warning("[v2] ciudades_recurso tiene proporciones en 0, sin inyección Med-Seg")
            return

        # SUMPRODUCT: Σ(costo_ciudad × proporcion) para cada tipo de costo
        weighted: Dict[str, float] = {k: 0.0 for k in _MED_SEG_COST_KEYS}
        for entry in ciudades_recurso:
            ciudad = str(entry.get("ciudad") or "")
            prop = float(entry.get("proporcion") or 0.0)
            if prop <= 0 or not ciudad:
                continue
            city_costs = infra.get_all_med_seg_costs(ciudad)
            for key in _MED_SEG_COST_KEYS:
                weighted[key] += city_costs[key] * (prop / total_prop)

        # Inyectar solo si no vienen explícitos en el request
        for field, value in weighted.items():
            if datos_op.get(field) is None:
                datos_op[field] = round(value, 4)

        logger.info("[v2] Med-Seg costs (SUMPRODUCT ponderado) inyectados: %s", weighted)
    except Exception as exc:
        logger.warning("[v2] No se pudieron cargar costos HR-Med-Seg (%s), el motor usará defaults", exc)


def handle_calculate_v2(
    request_data: Dict[str, Any],
    param_store: DocumentStore,
    results_store: DocumentStore,
    id_draft: Optional[str] = None,
    client_id: Optional[str] = None,
) -> ApiResponse:
    """Ejecuta el motor v2, persiste en Cosmos y retorna respuesta simple."""

    _inject_med_seg_costs(request_data, param_store)

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
        "created_at": datetime.now(_TZ_CO).isoformat(),
        "cliente": result.cliente,
        "servicio": result.servicio,
        "tipo_cliente": result.tipo_cliente,
        "antiguedad_cliente": result.antiguedad_cliente,
        "periodo_pago": result.periodo_pago,
        "fecha_inicio": result.fecha_inicio,
        "duracion_meses": result.duracion_meses,
        "ciudad": result.ciudad,
        "sede": result.sede,
        "vision_pyg": result.vision_pyg.model_dump(),
        "vision_cts": result.vision_cts.model_dump() if result.vision_cts else None,
        "vision_imprimible": result.vision_imprimible,
        "vision_tarifas": result.vision_tarifas,
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
            "created_at": doc["created_at"],
        },
        meta={"version": "v2", "motor": "motor_de_reglas"},
    )
