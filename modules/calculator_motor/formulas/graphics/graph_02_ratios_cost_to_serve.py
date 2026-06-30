"""
calculator_motor/formulas/graphics/graph_02_ratios_cost_to_serve.py
--------------------------------------------------------------------
Graph 2 — Ratios Vision Cost To Serve.

Excel V2-8 · Graficos!P4:BH29.

Block A (P4:AF29) — absolute loaded payroll cost by role × scenario (Step 01).
Block B (AR4:BH29) — ratios: role_cost / column_denominator (Step 02).

Denominator rule (Excel: SUMIFS(col$5:col$29, $P$5:$P$29, "<>"&$AR$24)):
  denominator = sum(column_costs) EXCLUDING "Agente Básico 1"
  The excluded role's own ratio row is still computed normally.
  selected_ratio_column = "Total" per VCT!C125 = "Total" (static, V2-8).

Cargos Adicionales (P29 / Q29:AE29): deferred — backend source not confirmed.

Rules:
  - No Excel reads at runtime.
  - No storage reads.
  - No hardcoded payroll values.
  - Does not change NominaCalculator.calcular_para_mes.
"""
from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
    CostoRolEscenario,
    EscenarioCostoRoles,
    GraficoRatiosCTSResult,
)

if TYPE_CHECKING:
    from nexa_engine.modules.panel.models.panel import EscenarioComercial, PerfilCadenaA
    from nexa_engine.modules.calculator_motor.formulas.payroll.nomina import NominaCalculator


# ---------------------------------------------------------------------------
# Static role → category map
# Excel V2-8 · Graficos!AH5:AH28 (derived from FILTER($AN$5:$AN$28,...))
# This table is hardcoded in the Excel workbook and does not depend on
# parametrization, request inputs, or storage.
# ---------------------------------------------------------------------------
_ROL_CATEGORIA: Dict[str, str] = {
    "Director de cuentas": "Operaciones",
    "Director de Performance": "Operaciones",
    "Jefe Comercial Regional": "Operaciones",
    "Analista profesional AFAC": "Operaciones",
    "Lider de Entrenamiento": "Operaciones",
    "Lider de Experiencia de Cliente y Performance": "Operaciones",
    "Lider de Planeación Operativa": "Operaciones",
    "Jefe de Operación": "Operaciones",
    "Works force": "Operaciones",
    "Reporting": "Operaciones",
    "GTR": "Operaciones",
    "Analista Prof. De Selección (Inicial)": "Operaciones",
    "Analista 1 de Reclutamiento (Inicial)": "Operaciones",
    "Analista Prof. De Selección (Rotación)": "Operaciones",
    "Analista 1 de Reclutamiento (Rotación)": "Recursos humanos",
    "Analista 2 Service Desk": "Recursos humanos",
    "Formadores": "Recursos humanos",
    "Monitor de Calidad": "Recursos humanos",
    "Supervisor": "Recursos humanos",
    "Agente Básico 1": "Recursos humanos",
    "Validador": "Recursos humanos",
    "Aprendiz SENA": "Recursos humanos",
    "Inclusión": "Otros",
    "Especialista de Proyectos": "Otros",
}


# ---------------------------------------------------------------------------
# Approved scenario label mapping
# Driven by 'Condiciones Cadena A'!E8:S8 labels for V2-8.
# ---------------------------------------------------------------------------
_SCENARIO_LABEL_MAP: Dict[tuple, str] = {
    ("sac", "actual"): "Escenario SAC Actual",
    ("whatsapp", "actual"): "Escenario WhatsApp Actual",
    ("inhouse", ""): "Crecimiento inhouse",
    ("inhouse", "inhouse"): "Crecimiento inhouse",
    ("crecimiento inhouse", ""): "Crecimiento inhouse",
}


def _escenario_label(canal: str, modalidad: str) -> str:
    """
    Map (canal, modalidad) to the exact Excel scenario label.

    Excel V2-8 · 'Condiciones Cadena A'!E8:S8
    Approved mapping (from GRAPH_02_STEP_01):
      SAC + Actual       → "Escenario SAC Actual"
      WhatsApp + Actual  → "Escenario WhatsApp Actual"
      Inhouse + *        → "Crecimiento inhouse"
    Fallback: "Escenario {canal} {modalidad}".strip()
    """
    key = (canal.lower().strip(), modalidad.lower().strip())
    if key in _SCENARIO_LABEL_MAP:
        return _SCENARIO_LABEL_MAP[key]
    # Partial match on canal
    canal_key = canal.lower().strip()
    for (c, m), label in _SCENARIO_LABEL_MAP.items():
        if c == canal_key:
            return label
    return f"Escenario {canal} {modalidad}".strip()


# ---------------------------------------------------------------------------
# Denominator exclusion
# Excel V2-8 · Graficos!AS5: =Q5/SUMIFS(Q$5:Q$29,$P$5:$P$29,"<>"&$AR$24)
# $AR$24 = "Agente Básico 1" (the reference agent role, used as volume baseline)
# ---------------------------------------------------------------------------
_ROL_EXCLUIDO_DENOMINADOR = "Agente Básico 1"


def _safe_ratio(numerator: float, denominator: float) -> float:
    """Return numerator/denominator; 0.0 when denominator is zero."""
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def _compute_denominador(costos: "Dict[str, float]") -> float:
    """
    Column denominator: sum of all role costs excluding Agente Básico 1.

    Excel V2-8 · Graficos!AS5 denominator:
      SUMIFS(Q$5:Q$29, $P$5:$P$29, "<>"&$AR$24)
    """
    return sum(v for k, v in costos.items() if k != _ROL_EXCLUIDO_DENOMINADOR)


def _compute_ratios_por_escenario(
    escenarios: "List[EscenarioCostoRoles]",
) -> "Dict[str, Dict[str, float]]":
    """
    Compute per-scenario ratios (Block B columns AS:BG).

    Excel V2-8 · Graficos!AS5:BG29
    Formula: =Q5/SUMIFS(Q$5:Q$29,$P$5:$P$29,"<>"&$AR$24)
    """
    result: "Dict[str, Dict[str, float]]" = {}
    for esc in escenarios:
        costos = esc.total_por_rol
        denom = _compute_denominador(costos)
        result[esc.escenario_label] = {
            rol: _safe_ratio(costo, denom) for rol, costo in costos.items()
        }
    return result


def _compute_ratios_total(
    total_por_rol: "Dict[str, float]",
) -> "Dict[str, float]":
    """
    Compute total column ratios (Block B column BH).

    Excel V2-8 · Graficos!BH5:BH29
    Formula: =AF5/SUMIFS(AF$5:AF$29,$P$5:$P$29,"<>"&$AR$24)
    """
    denom = _compute_denominador(total_por_rol)
    return {rol: _safe_ratio(cost, denom) for rol, cost in total_por_rol.items()}


def _filter_perfiles_por_escenario(
    perfiles: "List[PerfilCadenaA]",
    escenario: "EscenarioComercial",
) -> "List[PerfilCadenaA]":
    """
    Filter profiles matching one escenario's canal + modalidad.
    Mirrors the engine's EscenarioCanalFacts build logic (engine.py line ~264).
    Support profiles (es_soporte=True) are included as in the engine.
    """
    canal_lower = escenario.canal.lower()
    modalidad_lower = escenario.modalidad.lower()
    return [
        p for p in perfiles
        if p.canal.lower() == canal_lower
        and (p.modalidad.lower() == modalidad_lower or p.es_soporte)
    ]


def build_ratios_cost_to_serve(
    perfiles: "List[PerfilCadenaA]",
    escenarios: "List[EscenarioComercial]",
    calc_nomina: "NominaCalculator",
    mes: int = 1,
) -> GraficoRatiosCTSResult:
    """
    Build Graph 2: absolute role costs (Block A) and ratios (Block B).

    Block A — Excel V2-8 · Graficos!P4:AF29
    Formula Q5:AE28:
      =SUMIFS('Nomina Loaded'!col$43:col$66, $B$43:$B$66, role_name)
       + SUMIFS('Nomina Loaded'!col$155:col$178, $B$155:$B$178, role_name)

    Block B — Excel V2-8 · Graficos!AR4:BH29
    Formula AS5:BG29: =Q5/SUMIFS(Q$5:Q$29,$P$5:$P$29,"<>"&$AR$24)
    Formula BH5:BH29: =AF5/SUMIFS(AF$5:AF$29,$P$5:$P$29,"<>"&$AR$24)
    Denominator excludes "Agente Básico 1" (=$AR$24).
    selected_ratio_column = "Total" → ratio_actual = BH column ratios.

    Args:
        perfiles:    All PerfilCadenaA profiles for the deal.
        escenarios:  Active EscenarioComercial entries (canal + modalidad).
        calc_nomina: Configured NominaCalculator instance.
        mes:         Reference month (default 1, matches Nomina Loaded section 1).

    Returns:
        GraficoRatiosCTSResult with Block A costs and Block B ratios populated.
    """
    escenarios_resultado: List[EscenarioCostoRoles] = []
    total_acum: Dict[str, float] = {}

    for esc in escenarios:
        perfiles_esc = _filter_perfiles_por_escenario(perfiles, esc)
        if not perfiles_esc:
            continue

        desglose = calc_nomina.calcular_desglose_por_rol(perfiles_esc, mes)

        costos = [
            CostoRolEscenario(
                rol_nombre=nombre,
                costo_total=costo,
                categoria=_ROL_CATEGORIA.get(nombre, ""),
            )
            for nombre, costo in desglose.items()
        ]

        for nombre, costo in desglose.items():
            total_acum[nombre] = total_acum.get(nombre, 0.0) + costo

        escenarios_resultado.append(EscenarioCostoRoles(
            escenario_label=_escenario_label(esc.canal, esc.modalidad),
            canal=esc.canal,
            modalidad=esc.modalidad,
            costos_por_rol=costos,
        ))

    # Block B — ratios
    ratios_por_escenario = _compute_ratios_por_escenario(escenarios_resultado)
    ratios_total = _compute_ratios_total(total_acum)

    return GraficoRatiosCTSResult(
        escenarios=escenarios_resultado,
        total_por_rol=total_acum,
        ratios_por_escenario=ratios_por_escenario,
        ratio_actual=ratios_total,          # VCT!C125="Total" → always BH column
        selected_ratio_column="Total",
        excel_trace="Graficos!P4:BH29",
        deferred_items=[
            "Cargos Adicionales (P29/Q29:AE29) — backend source not confirmed",
        ],
    )
