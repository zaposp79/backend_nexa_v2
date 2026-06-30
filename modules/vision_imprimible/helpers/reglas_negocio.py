"""Reglas de Negocio / Alerta — Visión Imprimible sección 07.

Fórmula propia de VI sección 07:
  alerta_activa = requiere_aprobacion OR existe regla fuera de rango
  alerta_mensaje: prioridad aprobación > reglas fuera de rango > vacío

Mensaje de aprobación: "Alta Dirección" (Excel V2-7 nomenclature, BP-01).

Regla Superior: Excel V2-7 es canónico.
  - No leer business_rules en runtime.
  - No reintroducir smmlv.
  - No cambiar estructura de alerta.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from nexa_engine.modules.shared.models import PricingResult, ReglaNegocios


def reglas_negocio_to_dict(
    reglas: List[ReglaNegocios],
    resultado: PricingResult,
) -> Dict[str, Any]:
    """Serializa reglas de negocio como bloque completo con alerta — VI sección 07.

    Estructura de salida:
      alerta.activa   — OR(requiere_aprobacion, reglas_fuera_rango)
      alerta.mensaje  — prioridad: aprobación > fuera_de_rango > ""
      costo_total     — kpis.costo_total_contrato
      valor_total_deal — kpis.valor_total_deal
      reglas          — lista completa serializada
    """
    ev = resultado.evaluacion_riesgo
    reglas_fuera_rango = [r for r in reglas if r.status != "dentro_rango"]
    requiere_aprobacion = ev.requiere_aprobacion if ev else False

    alerta_activa = requiere_aprobacion or len(reglas_fuera_rango) > 0

    if requiere_aprobacion:
        alerta_mensaje = (
            "El contrato requiere aprobacion por parte de Alta Dirección "
            "debido al valor del contrato"
        )
    elif reglas_fuera_rango:
        nombres = ", ".join(r.label for r in reglas_fuera_rango)
        alerta_mensaje = f"Reglas fuera de rango: {nombres}"
    else:
        alerta_mensaje = ""

    kpis = resultado.kpis
    return {
        "alerta": {
            "activa":  alerta_activa,
            "mensaje": alerta_mensaje,
        },
        "costo_total":      kpis.costo_total_contrato,
        "valor_total_deal": kpis.valor_total_deal,
        "reglas":           [asdict(r) for r in reglas],
    }
