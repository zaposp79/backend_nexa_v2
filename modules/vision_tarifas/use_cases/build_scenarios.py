"""
application.use_cases.build_scenarios
=====================================

BuildScenariosUseCase — orchestrates scenario expansion (escenarios
comerciales, GAP-PCG-1).

WAVE 9 strangler: this is a thin façade. Actual scenario expansion lives
in `calculators.vision_tarifas` for now; this use case will own the
orchestration after WAVE 10 (lineage).
"""

from __future__ import annotations

from typing import Iterable, List

from nexa_engine.modules.shared.ports.logger import ILogger, NullLogger
from nexa_engine.modules.shared.ports.trace_emitter import ITraceEmitter, NullTraceEmitter


class BuildScenariosUseCase:
    """Reserved scenario-builder. Currently a passthrough façade."""

    def __init__(
        self,
        logger: ILogger | None = None,
        tracer: ITraceEmitter | None = None,
    ) -> None:
        self._logger = logger or NullLogger()
        self._tracer = tracer or NullTraceEmitter()

    def expandir(self, escenarios: Iterable) -> List:
        result = list(escenarios)
        self._logger.info(
            "[SCENARIO_BUILD] op=expandir", n_escenarios=len(result)
        )
        self._tracer.emit(
            stage="scenarios.expandir",
            inputs={"n_in": len(result)},
            outputs={"n_out": len(result)},
            source="Panel-Escenarios",
        )
        return result


__all__ = ["BuildScenariosUseCase"]
