"""
application.lineage.lineage_builder
===================================

Helpers used by `engine.calcular(..., with_lineage=True)` to seed the
emitter with the ~50-100 critical lineage nodes per simulation:

1. **`seed_lineage_from_request`** — emits one node per critical input
   (panel knobs, indexación, márgenes por cadena, polizas usuario).
2. **`seed_lineage_from_result`** — emits one node per critical output
   (cost_to_serve, vision_tarifas canales, kpis, primer / último mes
   del PyG).

These functions are intentionally read-only against the engine result;
no math is performed here — we only *describe* the values produced.

References to Excel sheets/cells come from `docs/v27/MAPEO_EXCEL_BACKEND.md`
and `docs/v27/INVENTARIO_EXCEL.md`. They are stored as `LineageRef` with
`source_type="excel"` so the `LineageQuery.explain()` output can quote
the Excel coordinates directly.
"""

from __future__ import annotations

from typing import Any, Optional

from nexa_engine.modules.lineage.domain.models import (
    LineageRef,
    SOURCE_TYPE_COMPUTED,
    SOURCE_TYPE_EXCEL,
    SOURCE_TYPE_PARAMETRIZATION,
    SOURCE_TYPE_REQUEST,
)


# Static map of panel knobs → Excel cell (best-effort; W14 will refine)
_PANEL_EXCEL_MAP: dict[str, tuple[str, str]] = {
    "margen":   ("Panel-Deal", "C9"),
    "op_cont":  ("Panel-Deal", "C12"),
    "com_cont": ("Panel-Deal", "C13"),
    "markup":   ("Panel-Deal", "C14"),
    "descuento": ("Panel-Deal", "C15"),
    "tasa_ica": ("Panel-Deal", "C20"),
    "tasa_gmf": ("Panel-Deal", "C21"),
    "imprevistos": ("Panel-Deal", "C73"),
    "tasa_comision_administracion": ("Panel-Deal", "G45"),
    "margen_b": ("Panel-Deal", "D63"),
    "margen_c": ("Panel-Deal", "E63"),
}


# ---------------------------------------------------------------------------
# Public seeders
# ---------------------------------------------------------------------------
def seed_lineage_from_request(emitter, solicitud) -> None:
    """Emit lineage nodes for the critical knobs in the request."""
    panel = getattr(solicitud, "panel", None)
    if panel is None:
        return

    _emit_panel_knobs(emitter, panel)
    _emit_indexacion(emitter, panel)

    # Cadenas activas
    cadenas = getattr(solicitud, "cadenas_activas", None)
    if cadenas is not None:
        emitter.emit(
            stage="REQUEST_BUILD",
            inputs={"cadena_a": cadenas.cadena_a, "cadena_b": cadenas.cadena_b, "cadena_c": cadenas.cadena_c},
            outputs={"cadenas_activas": f"A={cadenas.cadena_a}/B={cadenas.cadena_b}/C={cadenas.cadena_c}"},
            source="Panel-Deal",
            calculator="ContextBuilder",
            value_name="request.cadenas_activas",
            formula="A|B|C flags from request payload",
            lineage_refs=[
                LineageRef(SOURCE_TYPE_REQUEST, "request.cadenas_activas.cadena_a", cadenas.cadena_a),
                LineageRef(SOURCE_TYPE_REQUEST, "request.cadenas_activas.cadena_b", cadenas.cadena_b),
                LineageRef(SOURCE_TYPE_REQUEST, "request.cadenas_activas.cadena_c", cadenas.cadena_c),
            ],
        )

    # Pólizas del usuario (opcional, FASE D)
    polizas_usuario = getattr(solicitud, "polizas_usuario", None)
    if polizas_usuario:
        emitter.emit(
            stage="REQUEST_BUILD",
            inputs={"polizas_count": len(polizas_usuario) if hasattr(polizas_usuario, "__len__") else 1},
            outputs={"polizas_usuario": "<present>"},
            source="Panel-Deal",
            calculator="ContextBuilder",
            value_name="request.polizas_usuario",
            formula="user-supplied polizas override",
        )


def seed_lineage_from_result(emitter, solicitud, result) -> None:
    """Emit lineage nodes for the critical outputs of a simulation."""
    if result is None:
        return

    _emit_kpis(emitter, result)
    _emit_pyg_summary(emitter, result)
    _emit_cost_to_serve(emitter, result)
    _emit_vision_tarifas(emitter, result)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _emit_panel_knobs(emitter, panel) -> None:
    cliente = getattr(panel, "cliente", "?")
    for knob, (sheet, cell) in _PANEL_EXCEL_MAP.items():
        if not hasattr(panel, knob):
            continue
        value = getattr(panel, knob)
        excel_ref = LineageRef(
            source_type=SOURCE_TYPE_EXCEL,
            source_id=f"Excel:{sheet}!{cell}",
            value=value,
            sheet=sheet,
            cell=cell,
            formula=None,
        )
        req_ref = LineageRef(
            source_type=SOURCE_TYPE_REQUEST,
            source_id=f"request.panel.{knob}",
            value=value,
        )
        emitter.emit(
            stage="REQUEST_BUILD",
            inputs={knob: value},
            outputs={knob: value},
            source="Panel-Deal",
            calculator="ContextBuilder",
            value_name=f"request.panel.{knob}",
            formula=f"Panel knob {knob} (deal={cliente})",
            lineage_refs=[req_ref, excel_ref],
        )


def _emit_indexacion(emitter, panel) -> None:
    idx = getattr(panel, "indexacion", None)
    if idx is None:
        return
    refs = [
        LineageRef(SOURCE_TYPE_REQUEST, "request.panel.indexacion.componente_humano", idx.componente_humano),
        LineageRef(SOURCE_TYPE_REQUEST, "request.panel.indexacion.componente_tecnologico", idx.componente_tecnologico),
        LineageRef(SOURCE_TYPE_REQUEST, "request.panel.indexacion.mes_aplicacion", idx.mes_aplicacion),
        LineageRef(SOURCE_TYPE_EXCEL, "Excel:Panel-Deal!L9", idx.mes_aplicacion, sheet="Panel-Deal", cell="L9"),
    ]
    emitter.emit(
        stage="REQUEST_BUILD",
        inputs={
            "componente_humano": idx.componente_humano,
            "componente_tecnologico": idx.componente_tecnologico,
            "mes_aplicacion": idx.mes_aplicacion,
        },
        outputs={"indexacion": "configured"},
        source="Panel-Deal",
        calculator="ContextBuilder",
        value_name="request.panel.indexacion",
        formula="Indexación anual configurada (mes_aplicacion controla fecha)",
        lineage_refs=refs,
    )


def _emit_kpis(emitter, result) -> None:
    kpis = getattr(result, "kpis", None)
    if kpis is None:
        return
    fields = [
        "ingreso_bruto_total",
        "ingreso_neto_total",
        "costo_total_contrato",
        "contribucion_total",
        "utilidad_neta_total",
        "pct_utilidad_neta_total",
        "valor_total_deal",
        "margen_minimo_requerido",
        "cumple_margen_minimo",
    ]
    for f in fields:
        if not hasattr(kpis, f):
            continue
        v = getattr(kpis, f)
        emitter.emit(
            stage="VISION_BUILD",
            inputs={},
            outputs={f: v},
            source="KPIsCalculator",
            calculator="KPIsCalculator",
            value_name=f"kpis.{f}",
            formula=f"KPI agregado {f} sobre P&G mensual completo",
            is_root=(f in ("utilidad_neta_total", "valor_total_deal", "pct_utilidad_neta_total")),
            lineage_refs=[
                LineageRef(
                    SOURCE_TYPE_COMPUTED,
                    "computed:pyg_por_mes",
                    None,
                ),
            ],
        )


def _emit_pyg_summary(emitter, result) -> None:
    pyg_list = getattr(result, "pyg_por_mes", None) or []
    if not pyg_list:
        return
    # Emit first and last month — and a synthetic aggregate
    first = pyg_list[0]
    last = pyg_list[-1]
    for tag, mes in (("first", first), ("last", last)):
        emitter.emit(
            stage="PYG_BUILD",
            inputs={
                "mes": mes.mes,
                "rampup": mes.rampup,
            },
            outputs={
                "ingreso_bruto": mes.ingreso_bruto,
                "costo_total": mes.costo_total,
                "contribucion": mes.contribucion,
            },
            source="PyGCalculator",
            calculator="PyGCalculator.calcular_mes",
            value_name=f"pyg.mes[{mes.mes}].contribucion",
            formula="contribucion = ingreso_neto - costo_total",
            lineage_refs=[
                LineageRef(SOURCE_TYPE_COMPUTED, "computed:ingreso_bruto", mes.ingreso_bruto),
                LineageRef(SOURCE_TYPE_COMPUTED, "computed:costo_total", mes.costo_total),
                LineageRef(SOURCE_TYPE_PARAMETRIZATION, "HR-Campana.rampup", mes.rampup),
            ],
        )


def _emit_cost_to_serve(emitter, result) -> None:
    cts = getattr(result, "cost_to_serve", None)
    if cts is None:
        return
    candidate_fields = [
        "costo_total",
        "costo_cadena_a",
        "costo_cadena_b",
        "costo_cadena_c",
        "ingreso_mensual",
    ]
    for f in candidate_fields:
        if not hasattr(cts, f):
            continue
        v = getattr(cts, f)
        emitter.emit(
            stage="COST_TO_SERVE_BUILD",
            inputs={},
            outputs={f: v},
            source="CostToServeCalculator",
            calculator="CostToServeCalculator",
            value_name=f"cost_to_serve.{f}",
            formula=f"CTS aggregate {f} = sum(payroll + no_payroll + cadena_b + cadena_c)",
            lineage_refs=[
                LineageRef(SOURCE_TYPE_COMPUTED, "computed:nomina.total", None),
                LineageRef(SOURCE_TYPE_COMPUTED, "computed:no_payroll.total", None),
                LineageRef(SOURCE_TYPE_COMPUTED, "computed:cadena_b.total", None),
                LineageRef(SOURCE_TYPE_COMPUTED, "computed:cadena_c.total", None),
            ],
        )


def _emit_vision_tarifas(emitter, result) -> None:
    vt = getattr(result, "vision_tarifas", None)
    if vt is None:
        return
    canales = getattr(vt, "canales", []) or []
    for canal in canales:
        nombre = getattr(canal, "nombre_canal", "?")
        emitter.emit(
            stage="VISION_BUILD",
            inputs={
                "fte": getattr(canal, "fte", 0.0),
                "vol_mensual": getattr(canal, "vol_mensual", 0.0),
                "modelo_cobro": getattr(canal, "modelo_cobro", ""),
                "costo_atribuible": getattr(canal, "costo_atribuible", 0.0),
            },
            outputs={
                "tarifa_fijo_fte": getattr(canal, "tarifa_fijo_fte", 0.0),
                "tarifa_variable": getattr(canal, "tarifa_variable", 0.0),
                "ingreso_bruto": getattr(canal, "ingreso_bruto", 0.0),
                "facturacion": getattr(canal, "facturacion", 0.0),
            },
            source="VisionTarifasCalculator",
            calculator="VisionTarifasCalculator.calcular",
            value_name=f"vision_tarifas.tarifa[canal={nombre}]",
            formula="tarifa = costo_atribuible / factor_billing(margen, op, com, mk, desc)",
            is_root=True,
            lineage_refs=[
                LineageRef(SOURCE_TYPE_COMPUTED, "computed:factor_billing", None),
                LineageRef(SOURCE_TYPE_COMPUTED, "computed:payroll_ch", getattr(canal, "payroll_ch", 0.0)),
                LineageRef(SOURCE_TYPE_COMPUTED, "computed:no_payroll_ch", getattr(canal, "no_payroll_ch", 0.0)),
                LineageRef(SOURCE_TYPE_PARAMETRIZATION, "HR-Campana.rotacion_ausentismo", None,
                          sheet="Rot Ausent y Rentabilidad", cell="G11"),
                LineageRef(SOURCE_TYPE_REQUEST, "request.panel.margen_a", getattr(result.panel, "margen", 0.0) if hasattr(result, "panel") else 0.0),
            ],
        )

    # aggregate
    for f in ("costo_total", "ingreso_mensual", "costo_cadena_a_total", "costo_cadena_b_total"):
        if not hasattr(vt, f):
            continue
        emitter.emit(
            stage="VISION_BUILD",
            inputs={},
            outputs={f: getattr(vt, f)},
            source="VisionTarifasCalculator",
            calculator="VisionTarifasCalculator",
            value_name=f"vision_tarifas.{f}",
            formula=f"Agregado {f}",
            is_root=True,
        )


__all__ = ["seed_lineage_from_request", "seed_lineage_from_result"]
