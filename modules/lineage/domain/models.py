"""
application.lineage.models
==========================

Immutable data classes representing the financial-lineage graph.

A `LineageGraph` is the by-product of one simulation. It answers the
question *"where did this number come from?"* by linking every critical
financial value (visions, tarifas, márgenes, costs) back to:

  * the input request,
  * the active parametrization (HR/GN/OP), and
  * the Excel cell that originally produced it.

Design rules
------------
* **Frozen dataclasses** — graphs are immutable once built.
* **No IO** — these classes never read from disk. Persistence lives in
  `infrastructure/lineage/snapshot_repository.py`.
* **F9 placeholder** — `engine_version_placeholder` and
  `formula_set_placeholder` are string literals today; WAVE 14 will wire
  them to real SemVer/manifest hashes without breaking the schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Allowed source_type vocabulary
# ---------------------------------------------------------------------------
SOURCE_TYPE_REQUEST: str = "request"
SOURCE_TYPE_PARAMETRIZATION: str = "parametrization"
SOURCE_TYPE_EXCEL: str = "excel"
SOURCE_TYPE_COMPUTED: str = "computed"
SOURCE_TYPE_CONSTANT: str = "constant"

ALLOWED_SOURCE_TYPES: tuple[str, ...] = (
    SOURCE_TYPE_REQUEST,
    SOURCE_TYPE_PARAMETRIZATION,
    SOURCE_TYPE_EXCEL,
    SOURCE_TYPE_COMPUTED,
    SOURCE_TYPE_CONSTANT,
)


@dataclass(frozen=True)
class LineageRef:
    """
    Reference to an origin of data inside the lineage graph.

    Attributes:
        source_type: one of ALLOWED_SOURCE_TYPES.
        source_id:   stable string id, e.g.
                     ``"request.panel.margen_a"``,
                     ``"hr.nomina[Director].salario"``,
                     ``"Excel:Vision Tarifas!H42"``,
                     ``"computed:trace:<uuid>"``.
        value:       the actual value (number / string / dict / None).
        sheet:       Excel sheet name (only for source_type == "excel").
        cell:        Excel cell (only for source_type == "excel").
        formula:     Excel formula (only when known and source is excel).
    """

    source_type: str
    source_id: str
    value: Any
    sheet: Optional[str] = None
    cell: Optional[str] = None
    formula: Optional[str] = None

    def __post_init__(self) -> None:
        if self.source_type not in ALLOWED_SOURCE_TYPES:
            raise ValueError(
                f"LineageRef.source_type={self.source_type!r} not in "
                f"{ALLOWED_SOURCE_TYPES}"
            )

    def to_dict(self) -> dict:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "value": _coerce(self.value),
            "sheet": self.sheet,
            "cell": self.cell,
            "formula": self.formula,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LineageRef":
        return cls(
            source_type=data["source_type"],
            source_id=data["source_id"],
            value=data.get("value"),
            sheet=data.get("sheet"),
            cell=data.get("cell"),
            formula=data.get("formula"),
        )


@dataclass(frozen=True)
class LineageNode:
    """
    One node of the calculation graph — represents a single critical value
    produced by a calculator/use-case at a given pipeline stage.

    Attributes:
        trace_id:    uuid4 string, unique within the simulation.
        simulation_id: deal/cliente identifier.
        stage:       pipeline stage tag, e.g. "PAYROLL_BUILD".
        calculator:  qualified name of the producer.
        value_name:  canonical name of the produced value.
        value:       the produced value.
        formula:     human-readable formula description.
        inputs:      LineageRef list pointing to parent sources.
        outputs:     trace_ids of dependent nodes (filled lazily).
        engine_version: WAVE 14 — real engine SemVer (sourced from
                        VersionRegistry).  Backwards-compatible alias:
                        the legacy field name
                        ``engine_version_placeholder`` is still accepted
                        on deserialization.
        formula_set:    WAVE 14 — real formula-set tag.  Legacy alias
                        ``formula_set_placeholder`` accepted on read.
        timestamp_ms: optional benchmark timestamp (not used for hashing).
    """

    trace_id: str
    simulation_id: str
    stage: str
    calculator: str
    value_name: str
    value: Any
    formula: str = ""
    inputs: tuple[LineageRef, ...] = field(default_factory=tuple)
    outputs: tuple[str, ...] = field(default_factory=tuple)
    engine_version: str = "engine-v2"
    formula_set: str = "formula-set-v2-7"
    timestamp_ms: float = 0.0

    # ------------------------------------------------------------------
    # Backwards-compatible aliases (WAVE 14 — F9 renames)
    # ------------------------------------------------------------------
    @property
    def engine_version_placeholder(self) -> str:  # noqa: D401
        """Legacy alias kept for callers written before WAVE 14."""
        return self.engine_version

    @property
    def formula_set_placeholder(self) -> str:  # noqa: D401
        """Legacy alias kept for callers written before WAVE 14."""
        return self.formula_set

    def to_dict(self, *, include_timestamps: bool = False) -> dict:
        d = {
            "trace_id": self.trace_id,
            "simulation_id": self.simulation_id,
            "stage": self.stage,
            "calculator": self.calculator,
            "value_name": self.value_name,
            "value": _coerce(self.value),
            "formula": self.formula,
            "inputs": [r.to_dict() for r in self.inputs],
            "outputs": list(self.outputs),
            # WAVE 14 — real version stamps (keys renamed).
            "engine_version": self.engine_version,
            "formula_set": self.formula_set,
        }
        if include_timestamps:
            d["timestamp_ms"] = self.timestamp_ms
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "LineageNode":
        # WAVE 14: accept both the new field names AND the legacy
        # ``*_placeholder`` keys persisted by W10/W13 snapshots.
        engine_version = data.get("engine_version")
        if engine_version is None:
            engine_version = data.get("engine_version_placeholder", "engine-v2")
        formula_set = data.get("formula_set")
        if formula_set is None:
            formula_set = data.get("formula_set_placeholder", "formula-set-v2-7")
        return cls(
            trace_id=data["trace_id"],
            simulation_id=data["simulation_id"],
            stage=data["stage"],
            calculator=data["calculator"],
            value_name=data["value_name"],
            value=data.get("value"),
            formula=data.get("formula", ""),
            inputs=tuple(LineageRef.from_dict(r) for r in data.get("inputs", [])),
            outputs=tuple(data.get("outputs", [])),
            engine_version=str(engine_version),
            formula_set=str(formula_set),
            timestamp_ms=data.get("timestamp_ms", 0.0),
        )


@dataclass(frozen=True)
class LineageGraph:
    """
    Lineage graph for a complete simulation.

    Attributes:
        simulation_id: deal/cliente identifier.
        nodes:        list of LineageNode in emission order.
        roots:        trace_ids of "final output" nodes (visions, KPIs).
        parametrization_hashes: real SHA-256 of the active parametrization
                                JSONs (populated by WAVE 14 via
                                ``VersionRegistry``).
        version_metadata: optional dict snapshot of `VersionMetadata`
                          captured at simulation time (WAVE 14).
    """

    simulation_id: str
    nodes: tuple[LineageNode, ...] = field(default_factory=tuple)
    roots: tuple[str, ...] = field(default_factory=tuple)
    parametrization_hashes: dict[str, str] = field(default_factory=dict)
    version_metadata: Optional[dict] = None

    def to_dict(self, *, include_timestamps: bool = False) -> dict:
        d = {
            "simulation_id": self.simulation_id,
            "nodes": [n.to_dict(include_timestamps=include_timestamps) for n in self.nodes],
            "roots": list(self.roots),
            "parametrization_hashes": dict(self.parametrization_hashes),
        }
        if self.version_metadata is not None:
            d["version_metadata"] = dict(self.version_metadata)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "LineageGraph":
        version_metadata = data.get("version_metadata")
        return cls(
            simulation_id=data["simulation_id"],
            nodes=tuple(LineageNode.from_dict(n) for n in data.get("nodes", [])),
            roots=tuple(data.get("roots", [])),
            parametrization_hashes=dict(data.get("parametrization_hashes", {})),
            version_metadata=dict(version_metadata) if version_metadata else None,
        )

    # ------------------------------------------------------------------
    # Convenience accessors (read-only)
    # ------------------------------------------------------------------
    def by_trace_id(self, trace_id: str) -> Optional[LineageNode]:
        for n in self.nodes:
            if n.trace_id == trace_id:
                return n
        return None

    def by_value_name(self, value_name: str) -> Optional[LineageNode]:
        # last writer wins — emulates final value
        match: Optional[LineageNode] = None
        for n in self.nodes:
            if n.value_name == value_name:
                match = n
        return match


def _coerce(value: Any) -> Any:
    """Coerce values for deterministic JSON serialization."""
    if value is None:
        return None
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        # round only on serialize to avoid lossy storage
        return value
    if isinstance(value, dict):
        return {str(k): _coerce(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_coerce(v) for v in value]
    # fallback: stringify any complex object (Pydantic, dataclass, etc.)
    return repr(value)


__all__ = [
    "LineageRef",
    "LineageNode",
    "LineageGraph",
    "ALLOWED_SOURCE_TYPES",
    "SOURCE_TYPE_REQUEST",
    "SOURCE_TYPE_PARAMETRIZATION",
    "SOURCE_TYPE_EXCEL",
    "SOURCE_TYPE_COMPUTED",
    "SOURCE_TYPE_CONSTANT",
]
