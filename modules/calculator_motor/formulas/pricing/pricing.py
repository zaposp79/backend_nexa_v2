"""
Pure pricing math — stateless operations for ingreso/tarifa/factor/label derivation.

Source: Excel V2-7 denominator formula and canal-level billing conventions.
"""

from __future__ import annotations

from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator


class PricingCalculator:
    """
    Pure pricing math. Stateless. All methods are static.

    @excel_lineage:
      version: V2-8
      sheet: Visiones (and Vision Tarifas_Modelo_Cobro)
      cells: [UNCONFIRMED — ingreso_bruto = costo / factor_billing pattern observed in
              'Visiones' and 'Vision Tarifas_Modelo_Cobro' sheets; tarifa_unitaria =
              facturacion / divisor (FTE or volumen) pattern per canal]
      concept: ingreso_bruto_y_tarifa_por_canal
    @runtime_sources:
      - request/request.json → PanelDeControl (margen, op_cont, com_cont, markup, descuento)
      - request/request.json → PerfilCadenaA[].fte (FTE divisor for tarifa FTE)
      - request/request.json → volumen_mensual (volume divisor for tarifa transaccional)
    @confidence: MEDIUM
    @forbidden:
      - hardcoded_excel_values (factor_billing fully derived from Panel fields)
    """

    @staticmethod
    def calcular_ingreso_bruto(costo: float, factor_billing: float) -> float:
        """
        Convert a costo into ingreso bruto using the V2-7 denominator.

        Returns 0.0 if `factor_billing` is non-positive.
        """
        if factor_billing <= 0:
            return 0.0
        return costo / factor_billing

    @staticmethod
    def calcular_tarifa_unitaria(facturacion: float, divisor: float) -> float:
        """
        tarifa_unitaria = facturacion / divisor (FTE o volumen).

        Returns 0.0 if divisor is non-positive.
        """
        if divisor <= 0:
            return 0.0
        return facturacion / divisor

    @staticmethod
    def calcular_factor_billing(
        margen: float, op_cont: float, com_cont: float, markup: float, descuento: float
    ) -> float:
        """
        Proxy to ProfitabilityCalculator so pricing-domain callers don't
        import across domains.
        """
        return ProfitabilityCalculator.calcular_factor_billing(
            margen, op_cont, com_cont, markup, descuento
        )

    @staticmethod
    def derivar_componentes_label(modelo_cobro: str, pct_fijo: float) -> tuple[str, str]:
        """
        Convención Excel V2-4:
          "Fijo FTE"  -> ("FTE", "")
          "Variable"  -> ("",    "Transacción")
          "Híbrido"   -> ("FTE", "Transacción")
          fallback    -> derivar de pct_fijo
        """
        mc = modelo_cobro.lower()
        if "fijo" in mc and "fte" in mc:
            return "FTE", ""
        if "variable" in mc:
            return "", "Transacción"
        if "híbrido" in mc or "hibrido" in mc:
            return "FTE", "Transacción"
        comp_var = "" if pct_fijo >= 1.0 else "Transacción"
        comp_fijo = "FTE" if pct_fijo > 0 else ""
        return comp_fijo, comp_var


__all__ = ["PricingCalculator"]
