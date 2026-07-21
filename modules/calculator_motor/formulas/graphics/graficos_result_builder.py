"""Graph result orchestration for calculator_motor."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from nexa_engine.modules.calculator_motor.formulas.graphics.calculator import (
    calculate_graph_series,
)
from nexa_engine.modules.calculator_motor.formulas.graphics.graph_02_ratios_cost_to_serve import (
    build_ratios_cost_to_serve,
)
from nexa_engine.modules.calculator_motor.formulas.graphics.graph_03_ingresos_mensuales import (
    build_ingresos_mensuales,
)
from nexa_engine.modules.calculator_motor.formulas.graphics.graph_04_waterfall_table import (
    build_waterfall_table,
)
from nexa_engine.modules.calculator_motor.formulas.graphics.graph_05_cts_bargaining_zone import (
    build_cts_bargaining_zone,
)
from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
    GraficosResult,
    PortfolioClienteRow,
)
from nexa_engine.modules.calculator_motor.formulas.payroll import NominaCalculator
from nexa_engine.modules.shared.models import PricingRequest, PricingResult

if TYPE_CHECKING:
    from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider

logger = logging.getLogger("nexa.graficos_result_builder")


def build_graficos_result(
    resultado: PricingResult,
    solicitud: PricingRequest,
    parametrizacion: "Optional[IParametrizationProvider]" = None,
) -> Optional[GraficosResult]:
    """Build the full graph result object using calculator_motor-owned formulas."""
    try:
        if parametrizacion is None:
            logger.debug("[graficos_result_builder] graficos skipped: no parametrizacion provider")
            return None

        portfolio_raw = parametrizacion.get_portfolio_clientes()
        if portfolio_raw is None:
            portfolio = []
            promedios = {}
        else:
            portfolio = [
                PortfolioClienteRow(
                    categoria=row["categoria"],
                    cliente=row["cliente"],
                    margen_bruto=float(row["margen_bruto"]),
                )
                for row in portfolio_raw.get("clientes", [])
            ]
            promedios = portfolio_raw.get("promedios_por_categoria", {})

        panel = solicitud.panel
        categoria_servicio = getattr(panel, "linea_negocio", None) or ""
        cliente_nombre = getattr(panel, "cliente", None) or ""

        pyg_meses = resultado.pyg_por_mes or []
        margins = [m.pct_contribucion for m in pyg_meses if m.ingreso_neto > 0]
        deal_margin = sum(margins) / len(margins) if margins else 0.0

        graficos = calculate_graph_series(
            categoria_servicio=categoria_servicio,
            cliente_nombre=cliente_nombre,
            deal_margin=deal_margin,
            portfolio=portfolio,
            promedios_por_categoria=promedios,
        )

        ratios_cts = None
        escenarios = solicitud.escenarios or []
        perfiles = solicitud.perfiles_cadena_a or []
        if escenarios and perfiles:
            calc_nomina = NominaCalculator(
                solicitud.parametros_nomina,
                solicitud.parametros_calculo,
            )
            ratios_cts = build_ratios_cost_to_serve(
                perfiles=perfiles,
                escenarios=escenarios,
                calc_nomina=calc_nomina,
                mes=1,
            )

        graficos.ratios_cost_to_serve = ratios_cts
        graficos.ingresos_mensuales = build_ingresos_mensuales(
            pyg_por_mes=resultado.pyg_por_mes or [],
        )

        pyg_meses_list = resultado.pyg_por_mes or []
        if pyg_meses_list:
            graficos.waterfall_table = build_waterfall_table(
                pyg_por_mes=pyg_meses_list,
                pct_utilidad_neta_total=resultado.kpis.pct_utilidad_neta_total,
            )

        kpis = resultado.kpis
        graficos.cts_bargaining_zone = build_cts_bargaining_zone(
            costo_mensual_promedio=getattr(kpis, "costo_mensual_promedio", None),
            ingreso_neto_total=getattr(kpis, "ingreso_neto_total", None),
            meses_contrato=len(pyg_meses_list),
            margen_objetivo=getattr(panel, "margen", None),
        )

        return graficos

    except Exception as exc:
        logger.warning("[graficos_result_builder] graficos build failed (non-fatal): %s", exc)
        return None
