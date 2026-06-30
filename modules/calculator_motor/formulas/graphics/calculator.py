"""
calculator_motor/formulas/graphics/calculator.py
-------------------------------------------------
Graph series calculator for the 'Bandas Visión Final' chart.

Excel V2-8 · Hoja 'Graficos' — Grafico 1 (Bandas Visión Final)

Formulas implemented:
  G6: =IFERROR(QUARTILE.INC(FILTER($C$5:$C$93,($A$5:$A$93=$G$4)*ISNUMBER($C$5:$C$93)),1),"")
  G7: same with quart=2 (median)
  G8: same with quart=3
  G9: same with quart=4 (max)
  I4: =IFS(G4="SAC",C3, G4="SACO",C30, ...) — category average lookup
  I5: =FILTER(C5:C93,(A5:A93=$G$4)*(B5:B93=$G$5))  — client historical margin
"""

from __future__ import annotations

from typing import List, Optional

from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
    GraficoBandasResult,
    GraficosResult,
    PortfolioClienteRow,
)


def _quartile_inc(values: List[float], quart: int) -> Optional[float]:
    """
    Python equivalent of Excel QUARTILE.INC.

    Excel V2-8 · Graficos!G6:G9
    quart=1 → 25th pct, quart=2 → median, quart=3 → 75th pct, quart=4 → max

    Uses inclusive linear interpolation identical to Excel's QUARTILE.INC.
    """
    if not values:
        return None
    n = len(values)
    sorted_v = sorted(values)
    if quart == 4:
        return sorted_v[-1]
    pct = quart / 4.0
    idx = pct * (n - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return sorted_v[lo]
    frac = idx - lo
    return sorted_v[lo] + frac * (sorted_v[hi] - sorted_v[lo])


class GraficoBandasCalculator:
    """
    Calculates the 'Bandas Visión Final' graph series.

    Receives already-computed deal margin (from PricingResult) and the
    static portfolio reference table (from OP parametrization / business rules).
    Does not read Excel or storage at runtime.
    """

    def calcular(
        self,
        *,
        categoria_servicio: str,
        cliente_nombre: str,
        deal_margin: float,
        portfolio: List[PortfolioClienteRow],
        promedios_por_categoria: dict,
    ) -> GraficoBandasResult:
        """
        Excel V2-8 · Graficos!F4:I9 — Grafico 1 (Bandas Visión Final)

        Args:
            categoria_servicio: service category (Panel de Control!C5)
            cliente_nombre:     client name (Panel de Control!C6)
            deal_margin:        current deal's pct_contribucion (from PricingResult)
            portfolio:          static client portfolio reference rows (Graficos!A5:C93)
            promedios_por_categoria: category averages (Graficos!C3/C30/C44/C62/C75/C82)

        Returns:
            GraficoBandasResult with quartile bands and deal overlay data.
        """
        # FILTER(C5:C93, A5:A93=categoria AND ISNUMBER(C5:C93))
        margins_in_category = [
            row.margen_bruto
            for row in portfolio
            if row.categoria == categoria_servicio
            and isinstance(row.margen_bruto, (int, float))
        ]

        q1 = _quartile_inc(margins_in_category, 1)
        q2 = _quartile_inc(margins_in_category, 2)
        q3 = _quartile_inc(margins_in_category, 3)
        q4 = _quartile_inc(margins_in_category, 4)

        promedio_cat = promedios_por_categoria.get(categoria_servicio)

        # FILTER(C5:C93, categoria=current AND cliente=current) — first match
        margen_historico: Optional[float] = None
        for row in portfolio:
            if row.categoria == categoria_servicio and row.cliente == cliente_nombre:
                margen_historico = row.margen_bruto
                break

        return GraficoBandasResult(
            categoria_servicio=categoria_servicio,
            cliente_nombre=cliente_nombre,
            quartil_1=q1,
            quartil_2=q2,
            quartil_3=q3,
            quartil_4=q4,
            promedio_categoria=promedio_cat,
            margen_historico_cliente=margen_historico,
            margen_deal_actual=deal_margin,
        )


def calculate_graph_series(
    *,
    categoria_servicio: str,
    cliente_nombre: str,
    deal_margin: float,
    portfolio: List[PortfolioClienteRow],
    promedios_por_categoria: dict,
) -> GraficosResult:
    """
    Entry point for the graph calculation layer.

    Calculates all graph series for the current deal.
    Currently implements Grafico 1 (Bandas Visión Final).

    Args:
        categoria_servicio: service category from request panel
        cliente_nombre:     client name from request panel
        deal_margin:        deal's profitability ratio from PricingResult
        portfolio:          static portfolio reference (from OP provider)
        promedios_por_categoria: category averages (from OP provider)

    Returns:
        GraficosResult containing all computed graph series.
    """
    bandas = GraficoBandasCalculator().calcular(
        categoria_servicio=categoria_servicio,
        cliente_nombre=cliente_nombre,
        deal_margin=deal_margin,
        portfolio=portfolio,
        promedios_por_categoria=promedios_por_categoria,
    )
    return GraficosResult(bandas_vision_final=bandas)
