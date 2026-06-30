"""
calculator_motor/formulas/graphics/graph_05_cts_bargaining_zone.py
-------------------------------------------------------------------
Graph 5 — CTS Deal Bargaining Zone.

Excel V2-8 · Graficos!P84:Q93

Q84 = costo_mensual_promedio
Q85 = ingreso_neto_total / meses_contrato
Q86 = margen_objetivo  (panel.margen)
Q87 = Q84 / (1 - Q86)
Q88 = MAX(Q85, Q87) * 1.05
Q90 = Q84
Q91 = Q88 - Q84
Q92 = Q88 - Q87
Q93 = Q85
"""

from __future__ import annotations

from typing import Optional

from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
    GraficoCtsBargainingZoneResult,
)


def build_cts_bargaining_zone(
    *,
    costo_mensual_promedio: Optional[float],
    ingreso_neto_total: Optional[float],
    meses_contrato: int,
    margen_objetivo: Optional[float],
) -> Optional[GraficoCtsBargainingZoneResult]:
    """
    Pure arithmetic for the CTS Deal Bargaining Zone chart.

    Returns None when any required input is missing or guard conditions are met.
    """
    if costo_mensual_promedio is None:
        return None
    if ingreso_neto_total is None:
        return None
    if margen_objetivo is None:
        return None
    if meses_contrato <= 0:
        return None
    if margen_objetivo >= 1.0:
        return None

    cts_deal = costo_mensual_promedio                               # Q84
    ingreso_deal = ingreso_neto_total / meses_contrato              # Q85
    meta_ingreso = cts_deal / (1.0 - margen_objetivo)              # Q87
    eje_max = max(ingreso_deal, meta_ingreso) * 1.05               # Q88

    pierde_plata = cts_deal                                         # Q90
    no_cumple_meta = eje_max - cts_deal                            # Q91
    zona_segura = eje_max - meta_ingreso                           # Q92
    marcador = ingreso_deal                                         # Q93

    return GraficoCtsBargainingZoneResult(
        cts_deal=cts_deal,
        ingreso_deal=ingreso_deal,
        margen_objetivo=margen_objetivo,
        meta_ingreso=meta_ingreso,
        eje_max=eje_max,
        pierde_plata=pierde_plata,
        no_cumple_meta=no_cumple_meta,
        zona_segura=zona_segura,
        marcador=marcador,
    )
