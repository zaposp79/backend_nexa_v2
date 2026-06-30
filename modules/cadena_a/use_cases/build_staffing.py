"""
application.use_cases.build_staffing
====================================

BuildStaffingUseCase — orchestrates staffing math (FTE, ramp-up).
"""

from __future__ import annotations

from nexa_engine.modules.shared.ports.logger import ILogger, NullLogger
from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider
from nexa_engine.modules.shared.ports.trace_emitter import ITraceEmitter, NullTraceEmitter
from nexa_engine.modules.cadena_a.staffing.calculators import StaffingCalculator


class BuildStaffingUseCase:
    """
    Orchestrator for staffing FTE math.

    The ramp-up table lookup uses `IParametrizationProvider.get_rampup()`;
    the pure scaling is done by `StaffingCalculator`.
    """

    def __init__(
        self,
        provider: IParametrizationProvider,
        logger: ILogger | None = None,
        tracer: ITraceEmitter | None = None,
    ) -> None:
        self._provider = provider
        self._logger = logger or NullLogger()
        self._tracer = tracer or NullTraceEmitter()

    def aplicar_rampup_para_mes(
        self, linea_negocio: str, mes: int, fte_target: float
    ) -> float:
        """fte_efectivo = fte_target × ramp-up(linea, mes)."""
        factor = self._provider.get_rampup(linea_negocio, mes)
        result = StaffingCalculator.aplicar_rampup(fte_target, factor)
        self._logger.info(
            "[STAFFING_BUILD] op=aplicar_rampup",
            linea=linea_negocio,
            mes=mes,
            fte_target=fte_target,
            factor=factor,
            result=result,
        )
        self._tracer.emit(
            stage="staffing.rampup",
            inputs={"linea": linea_negocio, "mes": mes, "fte_target": fte_target},
            outputs={"factor": factor, "fte_efectivo": result},
            source="HR-Campana",
        )
        return result


__all__ = ["BuildStaffingUseCase"]
