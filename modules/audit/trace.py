"""
nexa_engine/audit/trace.py
===========================
Modo auditoría — trace estructurado por componente calculado.

Singleton AuditTracer que captura:
    - fórmula aplicada (string declarativo)
    - inputs (valores fuente)
    - source storage (qué master/celda generó el valor)
    - named rule (nombre legible de la regla, e.g. "LEY_1819_EXONERACION")
    - tipo laboral (EMPLEADO_ESTANDAR, APRENDIZ_SENA, ...)
    - rounding aplicado
    - cálculos intermedios
    - resultado final
"""
from __future__ import annotations

import json
import threading
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TraceEntry:
    """Un evento de trace: un cálculo intermedio o final."""
    component: str
    rule: str
    formula: str
    inputs: dict[str, Any]
    result: float
    intermediate: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    tipo_laboral: str = ""
    rol: str = ""
    canal: str = ""
    mes: int = 0
    rounding: str = "none"
    notes: str = ""
    formula_ids: list[str] = field(default_factory=list, repr=False)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds")


class AuditTracer:
    """Singleton tracer thread-safe."""

    _instance: "AuditTracer | None" = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, enabled: bool = False) -> None:
        if getattr(self, "_initialized", False):
            self.enabled = enabled
            return
        self._initialized = True
        self.enabled = enabled
        self.entries: list[TraceEntry] = []
        self.case: str = ""
        self.metadata: dict[str, Any] = {}

    def start(self, case: str = "", **metadata: Any) -> None:
        self.entries.clear()
        self.case = case
        self.metadata = metadata
        self.enabled = True

    def stop(self) -> None:
        self.enabled = False

    def reset(self) -> None:
        self.entries.clear()
        self.case = ""
        self.metadata.clear()

    def entry(
        self,
        component: str,
        rule: str,
        formula: str,
        inputs: dict[str, Any],
        result: float,
        intermediate: dict[str, Any] | None = None,
        source: str = "",
        tipo_laboral: str = "",
        rol: str = "",
        canal: str = "",
        mes: int = 0,
        rounding: str = "none",
        notes: str = "",
        formula_ids: list[str] | None = None,
    ) -> None:
        if not self.enabled:
            return
        self.entries.append(
            TraceEntry(
                component=component,
                rule=rule,
                formula=formula,
                inputs=dict(inputs),
                intermediate=dict(intermediate or {}),
                result=float(result),
                source=source,
                tipo_laboral=tipo_laboral,
                rol=rol,
                canal=canal,
                mes=mes,
                rounding=rounding,
                notes=notes,
                formula_ids=formula_ids or [],
            )
        )

    def to_dict(self) -> dict[str, Any]:
        by_rule: dict[str, int] = defaultdict(int)
        by_tipo: dict[str, int] = defaultdict(int)
        by_component: dict[str, int] = defaultdict(int)
        for entry in self.entries:
            by_rule[entry.rule] += 1
            by_tipo[entry.tipo_laboral or "_unspecified"] += 1
            by_component[entry.component] += 1

        entries_list = []
        for entry in self.entries:
            entry_dict = asdict(entry)
            entry_dict.pop("formula_ids", None)
            entries_list.append(entry_dict)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "case": self.case,
            "metadata": self.metadata,
            "entries": entries_list,
            "summary": {
                "total_entries": len(self.entries),
                "by_rule": dict(by_rule),
                "by_tipo_laboral": dict(by_tipo),
                "by_component": dict(by_component),
            },
        }

    def export(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2))
        return path

    def export_csv(self, path: str | Path) -> Path:
        import csv as _csv

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = _csv.writer(handle)
            writer.writerow([
                "timestamp", "component", "rule", "tipo_laboral", "rol", "canal",
                "mes", "formula", "inputs_json", "intermediate_json", "result",
                "source", "rounding", "notes",
            ])
            for entry in self.entries:
                writer.writerow([
                    entry.timestamp, entry.component, entry.rule, entry.tipo_laboral, entry.rol, entry.canal,
                    entry.mes, entry.formula,
                    json.dumps(entry.inputs, ensure_ascii=False),
                    json.dumps(entry.intermediate, ensure_ascii=False),
                    entry.result, entry.source, entry.rounding, entry.notes,
                ])
        return path


_thread_local = threading.local()
_global_disabled_tracer = AuditTracer(enabled=False)


def get_tracer() -> AuditTracer:
    return getattr(_thread_local, "active_tracer", _global_disabled_tracer)


def set_active_tracer(tracer: "AuditTracer") -> None:
    _thread_local.active_tracer = tracer


def clear_active_tracer() -> None:
    if hasattr(_thread_local, "active_tracer"):
        del _thread_local.active_tracer


def is_enabled() -> bool:
    return get_tracer().enabled


def trace(
    component: str,
    rule: str,
    formula: str,
    inputs: dict[str, Any],
    result: float,
    **kwargs: Any,
) -> None:
    active = get_tracer()
    if not active.enabled:
        return
    active.entry(component=component, rule=rule, formula=formula, inputs=inputs, result=result, **kwargs)
