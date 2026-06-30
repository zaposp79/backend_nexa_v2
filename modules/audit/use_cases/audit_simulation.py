"""application.use_cases.audit_simulation
=========================================

WAVE 13 — Audit use case.

Builds an `AuditResult` (internal dataclass) from a persisted
`LineageGraph`. The API router translates the dataclass into the
`AuditResponseV1` DTO defined in `contracts/api_v1/response/audit.py`.

Pure application layer: no FastAPI / HTTP dependencies.
"""
from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from nexa_engine.modules.lineage.domain.models import (
    LineageGraph,
    LineageNode,
    LineageRef,
    SOURCE_TYPE_EXCEL,
    SOURCE_TYPE_PARAMETRIZATION,
    SOURCE_TYPE_REQUEST,
)
from nexa_engine.modules.lineage.domain.query import LineageQuery
from nexa_engine.modules.shared.versioning.version_registry import VersionMetadata, VersionRegistry
from nexa_engine.modules.lineage.infrastructure.snapshot_repository import (
    LineageSnapshotRepository,
)

_logger_audit = __import__("logging").getLogger("nexa.audit.versioning")


# ---------------------------------------------------------------------------
# Internal DTOs (dataclasses — translated to pydantic DTOs at the API edge)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FormulaSummary:
    calculator: str
    formula: str
    stage: str
    used_count: int


@dataclass(frozen=True)
class ParametersUsed:
    request: Dict[str, Any] = field(default_factory=dict)
    parametrization: Dict[str, Any] = field(default_factory=dict)
    excel_refs: List[LineageRef] = field(default_factory=list)


@dataclass(frozen=True)
class LineageSummary:
    nodes_count: int
    roots: List[str]
    stages_summary: Dict[str, int]


@dataclass(frozen=True)
class AuditResult:
    simulation_id: str
    lineage: LineageSummary
    formulas: List[FormulaSummary]
    parameters_used: ParametersUsed
    parametrization_hashes: Dict[str, str]
    engine_version: str
    formula_set: str
    generated_at: datetime


@dataclass(frozen=True)
class ValueExplanation:
    simulation_id: str
    value_name: str
    value: Any
    calculator: str
    formula: str
    stage: str
    explanation: str
    refs_chain: List[LineageRef]


@dataclass(frozen=True)
class SimulationSummary:
    simulation_id: str
    nodes_count: int
    roots_count: int
    stages: List[str]
    generated_at: Optional[datetime]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AuditNotAvailableError(Exception):
    """Raised when no lineage snapshot exists for the requested simulation."""


class ValueNotFoundError(Exception):
    """Raised when `value_name` is not present in the lineage graph."""


# ---------------------------------------------------------------------------
# Use case
# ---------------------------------------------------------------------------


class AuditSimulationUseCase:
    """Builds audit artefacts from persisted lineage graphs."""

    def __init__(
        self,
        lineage_repo: Optional[LineageSnapshotRepository] = None,
        version_registry: Optional[VersionRegistry] = None,
    ) -> None:
        self._repo = lineage_repo or LineageSnapshotRepository()
        self._version_registry = version_registry or VersionRegistry()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def execute(self, simulation_id: str) -> AuditResult:
        graph = self._load_graph(simulation_id)
        return self._build_audit(graph)

    def explain_value(
        self, simulation_id: str, value_name: str
    ) -> ValueExplanation:
        graph = self._load_graph(simulation_id)
        query = LineageQuery(graph)
        node = query.find_value(value_name)
        if node is None:
            raise ValueNotFoundError(
                f"value_name={value_name!r} not present in lineage for "
                f"simulation_id={simulation_id!r}"
            )
        chain = query.trace_back(value_name)
        return ValueExplanation(
            simulation_id=graph.simulation_id,
            value_name=value_name,
            value=node.value,
            calculator=node.calculator,
            formula=node.formula,
            stage=node.stage,
            explanation=query.explain(value_name),
            refs_chain=list(chain),
        )

    def list_simulations(self, limit: int = 50) -> List[SimulationSummary]:
        """Return summaries of simulations that have a persisted lineage graph.

        Delegates enumeration to the repository so both DocumentStore-backed
        (Cosmos, JSON provider) and filesystem-only (store=None) repos are
        supported.  Filesystem mtime is used only in filesystem mode.
        """
        try:
            graphs = self._repo.list_graphs(limit=limit)
        except Exception as exc:
            _logger_audit.error(
                "[audit] list_simulations: repository enumeration failed: %s", exc
            )
            raise

        items: List[SimulationSummary] = []
        for graph in graphs:
            stages = sorted({n.stage for n in graph.nodes})
            # mtime only available in filesystem mode; use None for store-backed repos
            mtime: Optional[datetime] = None
            path = self._repo.base_dir / graph.simulation_id / "lineage.json"
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            items.append(
                SimulationSummary(
                    simulation_id=graph.simulation_id,
                    nodes_count=len(graph.nodes),
                    roots_count=len(graph.roots),
                    stages=stages,
                    generated_at=mtime,
                )
            )
        items.sort(
            key=lambda s: s.generated_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return items

    def diff_vs_baseline(
        self,
        simulation_id: str,
        baseline_id: str,
        baseline_root,  # type: ignore[no-untyped-def]
    ) -> Dict[str, Any]:
        """
        Compare a simulation's outputs vs a certified baseline.

        `baseline_root` is the path to the certified baselines directory
        (e.g. `storage/baselines/v2-7-certified/cases/`). We compare the
        persisted lineage's root outputs against the baseline's
        outputs/kpis.json. This is a placeholder comparator — WAVE 15
        will harden it for the Certified Mode.
        """
        import json
        from pathlib import Path

        graph = self._load_graph(simulation_id)
        baseline_dir = Path(baseline_root) / baseline_id
        if not baseline_dir.exists():
            raise FileNotFoundError(
                f"baseline_id={baseline_id!r} not found at {baseline_dir}"
            )
        kpis_path = baseline_dir / "outputs" / "kpis.json"
        baseline_kpis: Dict[str, Any] = {}
        if kpis_path.exists():
            baseline_kpis = json.loads(kpis_path.read_text(encoding="utf-8"))

        # collect simulation kpis from lineage nodes
        sim_kpis: Dict[str, Any] = {}
        for n in graph.nodes:
            if n.value_name.startswith("kpis."):
                sim_kpis[n.value_name.removeprefix("kpis.")] = n.value

        diff: Dict[str, Any] = {}
        # only compare keys present in both
        for k, baseline_v in baseline_kpis.items():
            if k in sim_kpis:
                sim_v = sim_kpis[k]
                if isinstance(baseline_v, (int, float)) and isinstance(
                    sim_v, (int, float)
                ):
                    if abs(float(baseline_v) - float(sim_v)) > 1e-2:
                        diff[k] = {"baseline": baseline_v, "simulation": sim_v}
                elif baseline_v != sim_v:
                    diff[k] = {"baseline": baseline_v, "simulation": sim_v}

        return {
            "baseline_id": baseline_id,
            "matches_baseline": len(diff) == 0,
            "diff": diff,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load_graph(self, simulation_id: str) -> LineageGraph:
        if not self._repo.exists(simulation_id):
            raise AuditNotAvailableError(
                f"No lineage snapshot for simulation_id={simulation_id!r}. "
                f"Re-run /calculate with with_lineage=True to enable audit."
            )
        return self._repo.load(simulation_id)

    def _build_audit(self, graph: LineageGraph) -> AuditResult:
        # ── Formulas (unique by calculator+formula+stage) ────────────────
        formula_counter: Counter = Counter()
        for n in graph.nodes:
            if n.formula:
                formula_counter[(n.calculator, n.formula, n.stage)] += 1
        formulas = [
            FormulaSummary(calculator=c, formula=f, stage=s, used_count=cnt)
            for (c, f, s), cnt in formula_counter.most_common()
        ]

        # ── Parameters used (split by source_type) ───────────────────────
        request_params: "OrderedDict[str, Any]" = OrderedDict()
        param_params: "OrderedDict[str, Any]" = OrderedDict()
        excel_refs: List[LineageRef] = []
        seen_excel: set = set()
        for n in graph.nodes:
            for ref in n.inputs:
                if ref.source_type == SOURCE_TYPE_REQUEST:
                    request_params.setdefault(ref.source_id, ref.value)
                elif ref.source_type == SOURCE_TYPE_PARAMETRIZATION:
                    param_params.setdefault(ref.source_id, ref.value)
                elif ref.source_type == SOURCE_TYPE_EXCEL:
                    key = (ref.source_id, ref.sheet, ref.cell)
                    if key not in seen_excel:
                        seen_excel.add(key)
                        excel_refs.append(ref)

        parameters_used = ParametersUsed(
            request=dict(request_params),
            parametrization=dict(param_params),
            excel_refs=excel_refs,
        )

        # ── Lineage summary ──────────────────────────────────────────────
        stages_summary: Dict[str, int] = {}
        for n in graph.nodes:
            stages_summary[n.stage] = stages_summary.get(n.stage, 0) + 1

        summary = LineageSummary(
            nodes_count=len(graph.nodes),
            roots=list(graph.roots),
            stages_summary=stages_summary,
        )

        # ── WAVE 14 — real version metadata ──────────────────────────────
        engine_version, formula_set, hashes = self._resolve_versions(graph)

        return AuditResult(
            simulation_id=graph.simulation_id,
            lineage=summary,
            formulas=formulas,
            parameters_used=parameters_used,
            parametrization_hashes=hashes,
            engine_version=engine_version,
            formula_set=formula_set,
            generated_at=datetime.now(timezone.utc),
        )

    def _resolve_versions(
        self, graph: LineageGraph
    ) -> tuple[str, str, Dict[str, str]]:
        """
        Resolve `engine_version`, `formula_set`, `parametrization_hashes`
        for the audit envelope. Prefers values persisted on the graph
        (WAVE 14). Falls back to `VersionRegistry.get_current()` with a
        warning when the snapshot is legacy (pre-W14).
        """
        # 1. Best source: explicit `version_metadata` recorded by WAVE 14.
        vm = getattr(graph, "version_metadata", None)
        if vm:
            meta = VersionMetadata.from_dict(vm)
            hashes = dict(meta.parametrization_hashes) or dict(
                graph.parametrization_hashes
            )
            return meta.engine_version, meta.formula_set, hashes

        # 2. Older WAVE 13 graphs: read from the first node + hashes dict.
        engine_version = "engine-v2"
        formula_set = "formula-set-v2-7"
        if graph.nodes:
            engine_version = graph.nodes[0].engine_version
            formula_set = graph.nodes[0].formula_set
        hashes = dict(graph.parametrization_hashes)

        # 3. If hashes still empty (legacy snapshot), fill from registry.
        if not hashes:
            _logger_audit.warning(
                "[audit] legacy lineage (no version_metadata) for sim=%s — "
                "filling parametrization_hashes from VersionRegistry",
                graph.simulation_id,
            )
            try:
                live = self._version_registry.get_current()
                hashes = dict(live.parametrization_hashes)
                if engine_version == "engine-v2":
                    engine_version = live.engine_version
                if formula_set == "formula-set-v2-7":
                    formula_set = live.formula_set
            except Exception as exc:  # pragma: no cover - defensive
                _logger_audit.warning(
                    "[audit] VersionRegistry fallback failed: %s", exc
                )
        return engine_version, formula_set, hashes


__all__ = [
    "AuditSimulationUseCase",
    "AuditResult",
    "ValueExplanation",
    "SimulationSummary",
    "FormulaSummary",
    "ParametersUsed",
    "LineageSummary",
    "AuditNotAvailableError",
    "ValueNotFoundError",
]
