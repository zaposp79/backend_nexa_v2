"""
infrastructure.lineage.null_emitter
===================================

`NullLineageEmitter` — concrete no-op implementation of `ITraceEmitter`.

This is functionally identical to `application.ports.trace_emitter.NullTraceEmitter`.
It exists in infrastructure to mirror `JsonLineageEmitter` and so the
engine wiring can swap implementations symmetrically.

The original `NullTraceEmitter` remains the canonical no-op (re-exported
here) to avoid breaking the WAVE 9 imports.
"""

from __future__ import annotations

from typing import Any, Mapping

from nexa_engine.modules.shared.ports.trace_emitter import NullTraceEmitter


class NullLineageEmitter(NullTraceEmitter):
    """Alias subclass — `with_lineage=False` uses this."""

    def emit(  # type: ignore[override]
        self,
        stage: str,
        inputs: Mapping[str, Any],
        outputs: Mapping[str, Any],
        source: str = "",
        **extras: Any,
    ) -> None:
        return None


__all__ = ["NullLineageEmitter"]
