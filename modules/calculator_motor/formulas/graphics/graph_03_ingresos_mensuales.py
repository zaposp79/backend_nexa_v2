"""
calculator_motor/formulas/graphics/graph_03_ingresos_mensuales.py
-----------------------------------------------------------------
Graph 3 — Ingresos Netos por Mes.

Excel V2-8 · Graficos!P42:BW47.

Structure:
  Row 43: x-axis label / periodos metadata       (P43=Graficos!E6 = meses_contrato)
  Row 44: y-axis max                             (R44=MAX('Visión P&G'!C27:BJ27))
  Row 46: month indices 1..N                     (P46=1, Q46=IF(P46+1<=N,P46+1,NA()))
  Row 47: ingreso_neto per month (positive only) (P47=IF(PYG!C27>=0,PYG!C27,NA()))

Rules:
  - Source: PricingResult.pyg_por_mes[i].ingreso_neto (already computed by engine).
  - No Excel reads at runtime.
  - No storage reads.
  - Months where ingreso_neto < 0 map to None (Excel NA()).
"""
from __future__ import annotations

from typing import List, TYPE_CHECKING

from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
    GraficoIngresosMensualesResult,
    MesIngresoNeto,
)

if TYPE_CHECKING:
    from nexa_engine.modules.calculator_motor.models.results import PygMes


def build_ingresos_mensuales(
    pyg_por_mes: "List[PygMes]",
) -> GraficoIngresosMensualesResult:
    """
    Build Graph 3: monthly net income series from the computed P&G.

    Excel V2-8 · Graficos!P46:BW47
    Row 47 formula: =IF('Visión P&G'!$C$27>=0,'Visión P&G'!C$27,NA())

    Args:
        pyg_por_mes: Ordered list of monthly P&G results (index 0 = month 1).

    Returns:
        GraficoIngresosMensualesResult ready for GraficosResult.ingresos_mensuales.
    """
    if not pyg_por_mes:
        return GraficoIngresosMensualesResult()

    meses: List[MesIngresoNeto] = []
    max_value = 0.0

    for i, mes_pyg in enumerate(pyg_por_mes):
        valor = mes_pyg.ingreso_neto
        # Excel: =IF(...>=0, value, NA()) — negative months excluded from chart
        punto = MesIngresoNeto(
            mes=i + 1,
            ingreso_neto=valor if valor >= 0 else None,
        )
        meses.append(punto)
        if valor > max_value:
            max_value = valor

    return GraficoIngresosMensualesResult(
        meses=meses,
        periodos=len(pyg_por_mes),
        ingreso_neto_max=max_value,
        excel_trace="Graficos!P42:BW47",
    )
