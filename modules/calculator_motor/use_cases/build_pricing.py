"""
application.use_cases.build_pricing
===================================

BuildPricingUseCase — orchestrates pricing math (factor_billing, tarifas).
"""

from __future__ import annotations

from nexa_engine.modules.shared.ports.logger import ILogger, NullLogger
from nexa_engine.modules.shared.ports.trace_emitter import ITraceEmitter, NullTraceEmitter
from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator
from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator


class BuildPricingUseCase:
    """
    Orchestrator for canal-level pricing.

    Responsibilities:
      * Compute factor_billing per chain (margen_a/b/c)
      * Convert costo into ingreso bruto and tarifa unitaria
      * Emit structured `[PRICING_BUILD]` logs and lineage stages
    """

    def __init__(
        self,
        logger: ILogger | None = None,
        tracer: ITraceEmitter | None = None,
    ) -> None:
        self._logger = logger or NullLogger()
        self._tracer = tracer or NullTraceEmitter()

    def calcular_factor_billing(
        self,
        margen: float,
        op_cont: float,
        com_cont: float,
        markup: float,
        descuento: float,
        cadena: str = "A",
    ) -> float:
        """Compute the V2-7 billing denominator factor for one cadena."""
        result = ProfitabilityCalculator.calcular_factor_billing(
            margen, op_cont, com_cont, markup, descuento
        )
        self._logger.info(
            "[PRICING_BUILD] op=factor_billing",
            cadena=cadena,
            margen=margen,
            op_cont=op_cont,
            com_cont=com_cont,
            markup=markup,
            descuento=descuento,
            result=result,
        )
        self._tracer.emit(
            stage=f"pricing.factor_billing.{cadena}",
            inputs={
                "margen": margen,
                "op_cont": op_cont,
                "com_cont": com_cont,
                "markup": markup,
                "descuento": descuento,
            },
            outputs={"factor_billing": result},
            source="Panel-Deal",
        )
        return result

    def calcular_ingreso_bruto(self, costo: float, factor_billing: float) -> float:
        """ingreso_bruto = costo / factor_billing."""
        return PricingCalculator.calcular_ingreso_bruto(costo, factor_billing)


__all__ = ["BuildPricingUseCase"]
