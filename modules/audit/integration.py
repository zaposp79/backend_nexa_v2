"""
Context manager para activar/desactivar el AuditTracer alrededor
del pipeline completo de cálculo.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator

from nexa_engine.modules.audit.trace import (
    AuditTracer,
    clear_active_tracer,
    set_active_tracer,
)

logger = logging.getLogger("nexa.audit.integration")


@contextmanager
def audit_context(
    enabled: bool = True,
    simulation_id: str = "",
    case_name: str = "",
) -> Generator[AuditTracer, None, None]:
    tracer = AuditTracer.__new__(AuditTracer)
    tracer._initialized = False
    tracer.__init__(enabled=enabled)
    tracer.start(case=case_name or simulation_id or "simulation")
    set_active_tracer(tracer)

    try:
        yield tracer
    finally:
        clear_active_tracer()
        if enabled:
            logger.info(
                "[audit] Capturadas %d entradas para simulation_id=%s",
                len(tracer.entries),
                simulation_id,
            )


def export_audit_trace(tracer: AuditTracer) -> Dict[str, Any]:
    if not tracer or not tracer.enabled:
        return {"entries": [], "summary": {}, "enabled": False}

    try:
        return tracer.to_dict()
    except Exception as exc:
        logger.warning("[audit] Error exportando audit trace: %s", exc)
        return {"entries": [], "summary": {}, "error": str(exc)}
