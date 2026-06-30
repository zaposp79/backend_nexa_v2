"""
domain.profitability.calculators
================================

Pure profitability calculators. NO IO, NO logging.

This module is the canonical home for the WAVE 3 V2-7 fórmula del
denominador exacto de billing.

Public API
----------

  ProfitabilityCalculator.calcular_factor_billing(margen, op_cont, com_cont, markup, descuento) -> float
  ProfitabilityCalculator.calcular_ingreso_desde_costo(costo, factor_billing, factor_rampup) -> float
  ProfitabilityCalculator.calcular_factor_margenes(panel_like) -> float
      (compatibilidad con calculators.utils.calcular_factor_margenes — usa atributos)
"""

from __future__ import annotations

from typing import Any


class ProfitabilityCalculator:
    """
    Pure profitability math. Stateless. Use class methods.

    Formula V2-7 (Excel-anchored):
        factor_billing = (1-m)(1-op)(1-com)(1-mk)(1+d)
        ingreso        = costo / factor_billing * factor_rampup

    @excel_lineage:
      version: V2-8
      sheet: Panel de Control General (and Visiones)
      cells: [UNCONFIRMED — denominator factor_billing composed from:
              Panel!margen (margen objetivo cadena), Panel!op_cont, Panel!com_cont,
              Panel!markup, Panel!descuento — exact cell addresses UNCONFIRMED in V2-8]
      concept: factor_billing_denominador_v27
    @runtime_sources:
      - request/request.json → PanelDeControl (margen, margen_b, margen_c,
        op_cont, com_cont, markup, descuento)
    @confidence: HIGH (formula pattern well-established; exact cell addresses unconfirmed)
    @forbidden:
      - hardcoded_excel_values (all margin/contingency values come from Panel)
    """

    @staticmethod
    def calcular_factor_billing(
        margen: float,
        op_cont: float,
        com_cont: float,
        markup: float,
        descuento: float,
    ) -> float:
        """
        Compute the exact V2-7 billing denominator factor.

        Args:
            margen:    Margen objetivo de la cadena (Cadena A: panel.margen;
                       B: panel.margen_b; C: panel.margen_c).
            op_cont:   Contingencia operativa.
            com_cont:  Contingencia comercial.
            markup:    Markup aplicado.
            descuento: Descuento volumen (suma con signo +).

        Returns:
            factor_billing = (1-m)(1-op)(1-com)(1-mk)(1+d)
        """
        return (
            (1.0 - margen)
            * (1.0 - op_cont)
            * (1.0 - com_cont)
            * (1.0 - markup)
            * (1.0 + descuento)
        )

    @staticmethod
    def calcular_ingreso_desde_costo(
        costo: float,
        factor_billing: float,
        factor_rampup: float,
    ) -> float:
        """
        Derive ingreso from costo via the exact V2-7 denominator.

        Returns 0.0 if factor_billing is non-positive (deal mal configurado).
        """
        if factor_billing <= 0:
            return 0.0
        return (costo / factor_billing) * factor_rampup

    # ──────────────────────────────────────────────────────────────
    # Backward-compatible alias for calculators.utils.calcular_factor_margenes
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def calcular_factor_margenes(panel: Any) -> float:
        """
        Equivalent to legacy `calcular_factor_margenes(panel)` — receives any
        object with attributes `margen`, `op_cont`, `com_cont`, `markup`,
        `descuento`.

        Kept here so calculators/utils.py shim can delegate.
        """
        return ProfitabilityCalculator.calcular_factor_billing(
            margen=panel.margen,
            op_cont=panel.op_cont,
            com_cont=panel.com_cont,
            markup=panel.markup,
            descuento=panel.descuento,
        )


__all__ = ["ProfitabilityCalculator"]
