"""modules.audit — public audit API, tracing and audit support services."""

from nexa_engine.modules.audit.trace import (
    AuditTracer,
    TraceEntry,
    clear_active_tracer,
    get_tracer,
    is_enabled,
    set_active_tracer,
    trace,
)
from nexa_engine.modules.audit.integration import audit_context, export_audit_trace
from nexa_engine.modules.audit.registry import FieldTraceabilityRegistry
from nexa_engine.modules.audit.writer import TraceabilityWriter

__all__ = [
    "AuditTracer",
    "TraceEntry",
    "clear_active_tracer",
    "get_tracer",
    "is_enabled",
    "set_active_tracer",
    "trace",
    "audit_context",
    "export_audit_trace",
    "FieldTraceabilityRegistry",
    "TraceabilityWriter",
]
