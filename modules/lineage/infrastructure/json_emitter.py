"""
infrastructure.lineage.json_lineage_emitter
===========================================

`JsonLineageEmitter` — accumulates `LineageNode`s while a simulation
runs, then exposes them as an immutable `LineageGraph`.

This is the real `ITraceEmitter` used when the caller passes
`with_lineage=True` to `NexaPricingEngine.calcular`.

Contract
--------
* `emit()` MUST be cheap (no IO) — engineering target: under 50µs per call.
* `emit()` accepts the WAVE 9 signature `(stage, inputs, outputs, source)`
  plus optional structured kwargs:
      lineage_refs    : list[LineageRef] of explicit parents
      calculator      : str   — override the calculator name
      value_name      : str   — explicit canonical value name
      formula         : str   — formula text for the explain output
* `get_graph()` returns an immutable `LineageGraph` snapshot.
* No mutability after `get_graph()` is called more than once; subsequent
  calls reflect any further `emit()` calls.

The emitter is single-threaded; one instance is created per simulation.
"""

from __future__ import annotations

import uuid
from typing import Any, Iterable, Mapping, Optional  # noqa: F401

from nexa_engine.modules.lineage.domain.models import (
    LineageGraph,
    LineageNode,
    LineageRef,
    SOURCE_TYPE_COMPUTED,
    SOURCE_TYPE_PARAMETRIZATION,
    SOURCE_TYPE_REQUEST,
)
from nexa_engine.modules.shared.versioning.version_registry import VersionMetadata


class JsonLineageEmitter:
    """
    Concrete `ITraceEmitter` implementation that buffers nodes.

    Args:
        simulation_id:    caller-provided deal id; used as graph anchor.
        version_metadata: WAVE 14 — real version stamps emitted into each
                          ``LineageNode`` and the final ``LineageGraph``.
                          If omitted a default `VersionMetadata` is used
                          (preserves W10 default-behavior tests).
        engine_version:   legacy override (W10 ergonomics).  When set, it
                          overrides ``version_metadata.engine_version``.
        formula_set:      legacy override.  When set, overrides
                          ``version_metadata.formula_set``.
    """

    def __init__(
        self,
        simulation_id: str,
        version_metadata: Optional[VersionMetadata] = None,
        engine_version: Optional[str] = None,
        formula_set: Optional[str] = None,
    ) -> None:
        self._simulation_id = str(simulation_id) if simulation_id else "unknown"
        meta = version_metadata or VersionMetadata()
        # honour legacy explicit overrides
        overrides = {}
        if engine_version is not None:
            overrides["engine_version"] = engine_version
        if formula_set is not None:
            overrides["formula_set"] = formula_set
        if overrides:
            meta = meta.with_overrides(**overrides)
        self._version_metadata: VersionMetadata = meta
        self._engine_version = meta.engine_version
        self._formula_set = meta.formula_set
        self._nodes: list[LineageNode] = []
        self._roots: list[str] = []

    # ------------------------------------------------------------------
    # ITraceEmitter
    # ------------------------------------------------------------------
    def emit(
        self,
        stage: str,
        inputs: Mapping[str, Any],
        outputs: Mapping[str, Any],
        source: str = "",
        **extras: Any,
    ) -> None:
        """
        Record one calculation step.

        The legacy positional signature stays intact; new lineage metadata
        is passed via `extras`:
            lineage_refs : Iterable[LineageRef]
            calculator   : str
            value_name   : str  (default: first key of outputs)
            formula      : str
            is_root      : bool (mark this node as a graph root)
            mark_roots   : bool (alias for is_root)
        """
        lineage_refs: Iterable[LineageRef] = extras.get("lineage_refs") or []
        calculator: str = extras.get("calculator") or source or "unknown"
        value_name: str = extras.get("value_name") or self._derive_value_name(stage, outputs)
        formula: str = extras.get("formula") or ""
        is_root: bool = bool(extras.get("is_root") or extras.get("mark_roots"))

        # Build refs from inputs mapping when no explicit refs were given.
        if not lineage_refs:
            lineage_refs = self._infer_refs_from_inputs(inputs, source)

        value = self._derive_value(outputs)

        trace_id = uuid.uuid4().hex
        node = LineageNode(
            trace_id=trace_id,
            simulation_id=self._simulation_id,
            stage=stage,
            calculator=calculator,
            value_name=value_name,
            value=value,
            formula=formula,
            inputs=tuple(lineage_refs),
            outputs=tuple(),
            engine_version=self._engine_version,
            formula_set=self._formula_set,
            timestamp_ms=0.0,
        )
        self._nodes.append(node)
        if is_root:
            self._roots.append(trace_id)

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------
    def get_graph(self) -> LineageGraph:
        """Return an immutable snapshot of all emitted nodes."""
        # if no explicit roots, take the last node per stage as a candidate
        roots: tuple[str, ...]
        if self._roots:
            roots = tuple(dict.fromkeys(self._roots))  # de-dup preserving order
        else:
            last_per_stage: dict[str, str] = {}
            for n in self._nodes:
                last_per_stage[n.stage] = n.trace_id
            roots = tuple(last_per_stage.values())

        return LineageGraph(
            simulation_id=self._simulation_id,
            nodes=tuple(self._nodes),
            roots=roots,
            parametrization_hashes=dict(self._version_metadata.parametrization_hashes),
            version_metadata=self._version_metadata.to_dict(),
        )

    @property
    def version_metadata(self) -> VersionMetadata:
        return self._version_metadata

    @property
    def simulation_id(self) -> str:
        return self._simulation_id

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _derive_value_name(stage: str, outputs: Mapping[str, Any]) -> str:
        if outputs:
            first_key = next(iter(outputs.keys()))
            return f"{stage}.{first_key}"
        return stage

    @staticmethod
    def _derive_value(outputs: Mapping[str, Any]) -> Any:
        if not outputs:
            return None
        if len(outputs) == 1:
            return next(iter(outputs.values()))
        return dict(outputs)

    @staticmethod
    def _infer_refs_from_inputs(
        inputs: Mapping[str, Any], source: str
    ) -> list[LineageRef]:
        """
        Heuristic: when the caller didn't pass explicit LineageRefs we
        synthesize one per input key. The source_type is derived from the
        ``source`` hint string (Panel / HR / Excel / etc.).
        """
        s = (source or "").lower()
        if "excel" in s:
            stype = "excel"
        elif "panel" in s or "request" in s:
            stype = SOURCE_TYPE_REQUEST
        elif "hr" in s or "gn" in s or "op" in s or "param" in s:
            stype = SOURCE_TYPE_PARAMETRIZATION
        else:
            stype = SOURCE_TYPE_COMPUTED
        refs: list[LineageRef] = []
        for key, value in inputs.items():
            refs.append(
                LineageRef(
                    source_type=stype,
                    source_id=f"{source}::{key}" if source else str(key),
                    value=value,
                )
            )
        return refs


__all__ = ["JsonLineageEmitter"]
