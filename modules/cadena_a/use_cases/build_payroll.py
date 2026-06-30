"""
application.use_cases.build_payroll
====================================

BuildPayrollUseCase — orchestrates payroll computation by delegating math
to `domain.payroll.PayrollCalculator` and side effects (logging, trace
emission) to injected ports.

WAVE 9 strangler: the real V2-7 production path still flows through
`calculators.nomina.NominaCalculator` to preserve paridad. This use case
is the new orchestration surface for future cleanups and lineage (WAVE 10).
"""

from __future__ import annotations

from typing import Any

from nexa_engine.modules.shared.ports.logger import ILogger, NullLogger
from nexa_engine.modules.shared.ports.trace_emitter import ITraceEmitter, NullTraceEmitter
from nexa_engine.modules.calculator_motor.formulas.payroll import PayrollCalculator


class BuildPayrollUseCase:
    """
    Orchestrator for payroll cost build (Cadena A).

    Responsibilities:
      * Wrap calls to `PayrollCalculator` with structured logging.
      * Emit lineage stages via `ITraceEmitter` (WAVE 10 hook).
    """

    def __init__(
        self,
        logger: ILogger | None = None,
        tracer: ITraceEmitter | None = None,
    ) -> None:
        self._logger = logger or NullLogger()
        self._tracer = tracer or NullTraceEmitter()

    def calcular_factor_indexacion(
        self,
        factor_base: float,
        pct_aumento: float,
        mes_aplicacion: int,
        mes: int,
    ) -> float:
        """Compute combined wage-indexation factor for `mes`."""
        result = PayrollCalculator.calcular_factor_indexacion(
            factor_base, pct_aumento, mes_aplicacion, mes
        )
        self._logger.info(
            "[PAYROLL_BUILD] op=factor_indexacion",
            mes=mes,
            factor_base=factor_base,
            pct_aumento=pct_aumento,
            mes_aplicacion=mes_aplicacion,
            result=result,
        )
        self._tracer.emit(
            stage="payroll.factor_indexacion",
            inputs={
                "factor_base": factor_base,
                "pct_aumento": pct_aumento,
                "mes_aplicacion": mes_aplicacion,
                "mes": mes,
            },
            outputs={"factor": result},
            source="HR-Nomina",
        )
        return result


__all__ = ["BuildPayrollUseCase"]
