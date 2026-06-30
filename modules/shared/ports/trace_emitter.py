"""
application.ports.trace_emitter
===============================

Trace emitter port — preparado para WAVE 10 (lineage / trazabilidad
financiera).

The `emit()` method records one calculation stage:

    tracer.emit(
        stage   = "pricing.factor_billing",
        inputs  = {"margen": 0.20, "op_cont": 0.06, "com_cont": 0.05},
        outputs = {"factor_billing": 0.6588},
        source  = "Panel-Deal + ProfitabilityCalculator",
    )

WAVE 9 ships a `NullTraceEmitter` (no-op). WAVE 10 will provide a real
implementation that buffers stages and emits a lineage graph alongside
the SimulationResult.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class ITraceEmitter(Protocol):
    """
    Emit a single calculation stage. Implementations decide retention,
    serialization, and whether to short-circuit when disabled.
    """

    def emit(
        self,
        stage: str,
        inputs: Mapping[str, Any],
        outputs: Mapping[str, Any],
        source: str = "",
    ) -> None: ...


class NullTraceEmitter:
    """No-op trace emitter. Default until WAVE 10."""

    def emit(
        self,
        stage: str,
        inputs: Mapping[str, Any],
        outputs: Mapping[str, Any],
        source: str = "",
    ) -> None:
        return None


__all__ = ["ITraceEmitter", "NullTraceEmitter"]
