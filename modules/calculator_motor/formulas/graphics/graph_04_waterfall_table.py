"""
calculator_motor/formulas/graphics/graph_04_waterfall_table.py
--------------------------------------------------------------
Graph 4 — Waterfall Precio Total (table slice).

Excel V2-8 · Graficos!P65:S81
Columns: Concepto | Total | Promedio | % sobre Ingreso Neto

Source rows (all SUM over contrato months, 'Visión P&G'!C*:BJ*):
  Q68 → row 18 → Ingreso Bruto      = sum(pyg.ingreso_bruto)
  Q73 → row 27 → Ingreso Neto       = sum(pyg.ingreso_neto)
  Q74 → row 31 → Costos Cadena A    = sum(pyg.costo_a)
  Q75 → row 45 → Costos Cadena B    = sum(pyg.costo_b)
  Q76 → row 55 → Costos Cadena C    = sum(pyg.costo_c)
  Q77 → row 30 → Costo Total        = sum(pyg.costo_total)
  Q78 → row 74 → Contribución       = sum(pyg.contribucion)
  Q79 → row 78 → Costo Fijo         = NOT IN BACKEND (deferred)
  Q80 → row 79 → Utilidad Neta      = sum(pyg.utilidad_neta)
  Q81 → BK80   → % Utilidad Neta    = kpis.pct_utilidad_neta_total

Deferred: Graficos!P53:AA57 (ArrayFormulas waterfall chart segments).
"""

from __future__ import annotations

from typing import List

from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
    GraficoWaterfallTableResult,
    WaterfallItem,
)
from nexa_engine.modules.calculator_motor.models.results import PyGMensual


def build_waterfall_table(
    *,
    pyg_por_mes: List[PyGMensual],
    pct_utilidad_neta_total: float,
) -> GraficoWaterfallTableResult:
    """
    Build the waterfall table from already-computed PyG monthly facts.

    Excel V2-8 · Graficos!P65:S81
    Formula pattern: Total = SUM('Visión P&G'!C<row>:BJ<row>)
                     Promedio = Total / meses_contrato
                     % = Total / ingreso_neto_total
    """
    meses = len(pyg_por_mes)

    # SUM aggregates — mirror of Excel SUM('Visión P&G'!C*:BJ*) across all months
    ingreso_bruto_total = sum(m.ingreso_bruto for m in pyg_por_mes)   # Q68 row 18
    ingreso_neto_total  = sum(m.ingreso_neto  for m in pyg_por_mes)   # Q73 row 27
    costos_a_total      = sum(m.costo_a       for m in pyg_por_mes)   # Q74 row 31
    costos_b_total      = sum(m.costo_b       for m in pyg_por_mes)   # Q75 row 45
    costos_c_total      = sum(m.costo_c       for m in pyg_por_mes)   # Q76 row 55
    costo_total         = sum(m.costo_total   for m in pyg_por_mes)   # Q77 row 30
    contribucion_total  = sum(m.contribucion  for m in pyg_por_mes)   # Q78 row 74
    utilidad_neta_total = sum(m.utilidad_neta for m in pyg_por_mes)   # Q80 row 79

    def _pct(v: float) -> float:
        return v / ingreso_neto_total if ingreso_neto_total else 0.0

    def _avg(v: float) -> float:
        return v / meses if meses else 0.0

    items: List[WaterfallItem] = [
        WaterfallItem(
            concepto="Ingreso Bruto",
            total=ingreso_bruto_total,
            promedio=_avg(ingreso_bruto_total),
            pct_ingreso_neto=_pct(ingreso_bruto_total),
            tipo="ingreso",
            orden=1,
        ),
        WaterfallItem(
            concepto="Ingreso Neto",
            total=ingreso_neto_total,
            promedio=_avg(ingreso_neto_total),
            pct_ingreso_neto=_pct(ingreso_neto_total),
            tipo="subtotal",
            orden=2,
        ),
        WaterfallItem(
            concepto="Costos Cadena A",
            total=costos_a_total,
            promedio=_avg(costos_a_total),
            pct_ingreso_neto=_pct(costos_a_total),
            tipo="costo",
            orden=3,
        ),
        WaterfallItem(
            concepto="Costos Cadena B",
            total=costos_b_total,
            promedio=_avg(costos_b_total),
            pct_ingreso_neto=_pct(costos_b_total),
            tipo="costo",
            orden=4,
        ),
        WaterfallItem(
            concepto="Costos Cadena C",
            total=costos_c_total,
            promedio=_avg(costos_c_total),
            pct_ingreso_neto=_pct(costos_c_total),
            tipo="costo",
            orden=5,
        ),
        WaterfallItem(
            concepto="Costo Total",
            total=costo_total,
            promedio=_avg(costo_total),
            pct_ingreso_neto=_pct(costo_total),
            tipo="subtotal",
            orden=6,
        ),
        WaterfallItem(
            concepto="Contribución",
            total=contribucion_total,
            promedio=_avg(contribucion_total),
            pct_ingreso_neto=_pct(contribucion_total),
            tipo="subtotal",
            orden=7,
        ),
        WaterfallItem(
            concepto="Utilidad Neta",
            total=utilidad_neta_total,
            promedio=_avg(utilidad_neta_total),
            pct_ingreso_neto=pct_utilidad_neta_total,  # Q81 = kpis.BK80
            tipo="utilidad",
            orden=8,
        ),
    ]

    return GraficoWaterfallTableResult(
        items=items,
        meses_contrato=meses,
        excel_trace="Graficos!P65:S81",
    )
