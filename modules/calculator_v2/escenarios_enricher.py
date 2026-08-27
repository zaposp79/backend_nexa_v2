"""
Enriquece los perfiles de Cadena A con la configuración de modelo de cobro
definida en los Escenarios Comerciales del Panel de Control General.

El campo del request es 'escenarios_comerciales' (hasta 5 ítems). Cada ítem
se mapea a un perfil de condiciones_cadena_a por (canal, modalidad) e inyecta
modelo_cobro, componentes y proporciones antes de que los calculadores los lean.

Estructura esperada de cada escenario comercial:
  {
    "escenario": 1,                          # número 1-5
    "modalidad": "Inbound",
    "canal": "Voz 1",
    "modelo_cobro": "Fijo",                  # "Fijo" | "Híbrido" | "Variable"
    "componente_fijo": "FTE",                # "FTE" | "Tiempo" | "Precio Fijo" | ""
    "proporcion_componente_fijo": 1,         # float 0-1
    "componente_variable": "",               # "Transacción" | "Resultados" | "Honorarios" | ""
    "proporcion_componente_variable": 0      # float 0-1
  }
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("nexa.motor_reglas.escenarios")


def _clave(canal: Any, modalidad: Any) -> Tuple[str, str]:
    return (str(canal or "").strip().lower(), str(modalidad or "").strip().lower())


def get_escenarios_activos_keys(
    request_data: Dict[str, Any],
) -> Optional[Set[Tuple[str, str]]]:
    """Retorna el conjunto de claves (canal, modalidad) con escenario configurado.

    Retorna None si no hay 'escenarios_comerciales' en el request (sin filtro → backward compat).
    Retorna un set (posiblemente vacío) si 'escenarios_comerciales' existe pero todos están vacíos.
    """
    escenarios: Any = request_data.get("escenarios_comerciales")
    if escenarios is None:
        return None  # campo ausente → no filtrar
    return {
        _clave(e.get("canal"), e.get("modalidad"))
        for e in (escenarios or [])
        if str(e.get("canal") or "").strip()
    }


def enrich_perfiles_with_escenarios(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Inyecta modelo de cobro de escenarios_comerciales en cada perfil de Cadena A.

    Matching: (canal.lower(), modalidad.lower()) del escenario con el perfil.
    Escenarios sin canal (vacíos) se ignoran.
    Perfiles sin match conservan sus campos originales (backward compatible).

    Campos inyectados en el perfil desde el escenario coincidente:
      - modelo_cobro        ("Fijo" | "Híbrido" | "Variable")
      - componente_fijo     ("FTE" | "Tiempo" | "Precio Fijo" | None)
      - pct_variable        float 0-1  (de proporcion_componente_variable)
      - componente_variable ("Transacción" | "Resultados" | "Honorarios" | None)
      - escenario_nombre    "Escenario N" (basado en el número de escenario)
    """
    escenarios: List[Dict] = request_data.get("escenarios_comerciales") or []
    if not escenarios:
        return request_data

    # Índice (canal, modalidad) → config del escenario — excluye escenarios vacíos
    esc_index: Dict[Tuple[str, str], Dict] = {}
    for esc in escenarios:
        canal = str(esc.get("canal") or "").strip()
        if not canal:
            continue  # escenario sin canal configurado (vacío o Escenario 5 no usado)
        key = _clave(canal, esc.get("modalidad"))
        esc_index[key] = esc

    if not esc_index:
        return request_data

    cadena_a: Dict = request_data.get("condiciones_cadena_a") or {}
    perfiles: List[Dict] = cadena_a.get("perfiles") or []
    if not perfiles:
        return request_data

    enriched: List[Dict] = []
    for perfil in perfiles:
        key = _clave(perfil.get("canal"), perfil.get("modalidad"))
        esc = esc_index.get(key)
        if not esc:
            enriched.append(perfil)
            continue

        prop_var = float(esc.get("proporcion_componente_variable") or 0.0)
        comp_fijo = str(esc.get("componente_fijo") or "").strip() or None
        comp_var = str(esc.get("componente_variable") or "").strip() or None
        num_esc = esc.get("escenario", "")

        # comp_fijo debe ser None si el modelo es Variable puro (prop_var == 1)
        if prop_var >= 1.0:
            comp_fijo = None

        merged: Dict[str, Any] = {
            **perfil,
            "modelo_cobro": esc.get("modelo_cobro") or perfil.get("modelo_cobro", "Fijo"),
            "componente_fijo": comp_fijo,
            "pct_variable": prop_var,
            "componente_variable": comp_var if prop_var > 0 else None,
            "escenario_nombre": f"Escenario {num_esc}" if num_esc else perfil.get("nombre"),
        }

        logger.debug(
            "[escenarios] perfil '%s' ← 'Escenario %s': modelo=%s fijo=%s(%.0f%%) var=%s(%.0f%%)",
            perfil.get("nombre"),
            num_esc,
            merged["modelo_cobro"],
            comp_fijo,
            (1.0 - prop_var) * 100,
            comp_var,
            prop_var * 100,
        )
        enriched.append(merged)

    return {
        **request_data,
        "condiciones_cadena_a": {
            **cadena_a,
            "perfiles": enriched,
        },
    }
