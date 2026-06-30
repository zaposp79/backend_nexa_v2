"""
domain.financial.calculators
============================

Pure financial calculators. NO IO, NO logging.

Public API
----------

  FinancialCalculator.calcular_ica(base_ica, tasa_ica, factor_margenes) -> float
  FinancialCalculator.calcular_gmf(base_gmf, tasa_gmf) -> float
  FinancialCalculator.calcular_financiacion(costo_base, tasa_mensual, factor_periodo) -> float
  FinancialCalculator.calcular_polizas(base, tasa_polizas) -> float

WAVE9-DEFERRED: the full `CostosFinancierosCalculator.calcular()` orchestrates
ICA gross-up, polizas dependency, and user-provided polizas logic in a way
that's tightly coupled to PanelDeControl. We extract the four atomic
formulas here so future use cases can compose them while keeping the legacy
calculator class untouched for paridad.
"""

from __future__ import annotations


class FinancialCalculator:
    """
    Pure financial math. Stateless. Class methods.

    @excel_lineage:
      version: V2-8
      sheet: Pólizas - Costo Financiacion
      cells: [UNCONFIRMED — financing formula cells not individually verified;
              financing = costo_base × tasa_mensual × factor_periodo pattern observed
              in 'Panel de Control General'!L11 (tasa interés mensual = 0.0153)]
      concept: costos_financieros_atomicos (financiacion, polizas, ica, gmf)
    @runtime_sources:
      - request/request.json → PanelDeControl.tasa_mensual_financ ('Panel de Control General'!L11)
      - storage/parametrization/op → IParametrizationProvider.get_factor_periodo()
      - request/request.json → PanelDeControl.tasa_ica
      - request/request.json → PanelDeControl.tasa_gmf
    @confidence: MEDIUM
    @forbidden:
      - hardcoded_excel_values (tasa_mensual comes from Panel!L11, not hardcoded)
    """

    @staticmethod
    def calcular_financiacion(
        costo_base: float, tasa_mensual: float, factor_periodo: int
    ) -> float:
        """
        financiacion = costo_base × tasa_mensual × factor_periodo

        Returns 0.0 if any factor is non-positive.
        """
        if costo_base <= 0 or tasa_mensual <= 0 or factor_periodo <= 0:
            return 0.0
        return costo_base * tasa_mensual * factor_periodo

    @staticmethod
    def calcular_polizas(base: float, tasa_polizas: float) -> float:
        """
        polizas = base × tasa_polizas_efectiva
        """
        if base <= 0 or tasa_polizas <= 0:
            return 0.0
        return base * tasa_polizas

    @staticmethod
    def calcular_ica(
        costo: float,
        polizas: float,
        financiacion: float,
        tasa_ica: float,
        factor_margenes: float,
    ) -> float:
        """
        ICA con gross-up:
          base = costo/factor_margenes + polizas + financiacion
          ica  = base × tasa_ica

        Returns 0.0 if factor_margenes <= 0 (deal mal configurado).
        """
        if factor_margenes <= 0 or tasa_ica <= 0:
            return 0.0
        base = (costo / factor_margenes) + polizas + financiacion
        return base * tasa_ica

    @staticmethod
    def calcular_gmf(
        costo: float,
        polizas: float,
        financiacion: float,
        tasa_gmf: float,
    ) -> float:
        """
        GMF sin gross-up:
          gmf = (costo + polizas + financiacion) × tasa_gmf
        """
        if tasa_gmf <= 0:
            return 0.0
        return (costo + polizas + financiacion) * tasa_gmf


__all__ = ["FinancialCalculator"]
