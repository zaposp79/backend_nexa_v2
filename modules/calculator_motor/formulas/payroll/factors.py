"""
modules.calculator.formulas.payroll.calculators
================================================

Pure payroll formulas. Stateless, zero IO, zero logging.

Public API:
  PayrollCalculator.calcular_factor_aumento(mes, pct_aumento, mes_aplicacion) -> float
  PayrollCalculator.calcular_factor_indexacion(factor_base, pct_aumento, mes_aplicacion, mes) -> float
  PayrollCalculator.calcular_examenes_fraccion(meses_contrato, pct_rotacion_mensual, pct_examen_anual) -> float
"""

from __future__ import annotations


class PayrollCalculator:
    """
    Pure payroll math. Stateless. Class methods only.

    @excel_lineage:
      version: V2-8
      sheet: Tasas, TRM, Polizas
      cells: [B8:G9 (SMLV/IPC cumulative factor tables), I8:O11 (per-year increment rates)]
      concept: factor_indexacion_salarial
    @runtime_sources:
      - storage/parametrization/hr → ParametrosNomina.pct_aumento_salarial
        (maps to 'Tasas, TRM, Polizas' yearly increment row for the chosen indexation mode)
      - storage/parametrization/hr → ParametrosNomina.mes_aplicacion_aumento
        (maps to 'Panel de Control General'!L10 — Mes de Ajuste)
    @confidence: HIGH
    @forbidden:
      - hardcoded_excel_values (pct_aumento and mes_aplicacion come from HR parametrization)
    """

    @staticmethod
    def calcular_factor_aumento(mes: int, pct_aumento: float, mes_aplicacion: int) -> float:
        """
        Compound wage-increase multiplier for the given mes.

        Increase applies once every 12 months starting at `mes_aplicacion`.
        Months before the first adjustment return 1.0.

        Example with mes_aplicacion=13 and pct_aumento=0.10:
          mes 1..12  -> 1.0
          mes 13..24 -> 1.10
          mes 25..36 -> 1.21
        """
        if mes < mes_aplicacion:
            return 1.0
        anos_completos = (mes - mes_aplicacion) // 12 + 1
        return (1.0 + pct_aumento) ** anos_completos

    @staticmethod
    def calcular_factor_indexacion(
        factor_base: float,
        pct_aumento: float,
        mes_aplicacion: int,
        mes: int,
    ) -> float:
        """
        Combined wage-indexation factor:
          factor_indexacion(mes) = factor_base × factor_aumento(mes, pct, mes_aplicacion)
        """
        return factor_base * PayrollCalculator.calcular_factor_aumento(
            mes, pct_aumento, mes_aplicacion
        )

    @staticmethod
    def calcular_examenes_fraccion(
        meses_contrato: int,
        pct_rotacion_mensual: float,
        pct_examen_anual: float,
    ) -> float:
        """
        Medical exam fractional component (see nomina.py for context).

        fraccion_total = 1/meses + pct_rotacion + pct_anual/12

        Returns 0.0 if meses_contrato <= 0.
        """
        if meses_contrato <= 0:
            return 0.0
        return (1.0 / meses_contrato) + pct_rotacion_mensual + (pct_examen_anual / 12.0)


__all__ = ["PayrollCalculator"]
