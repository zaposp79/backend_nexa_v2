"""WAVE 14 — legacy lineage snapshots (pre-W14) must still load."""
from __future__ import annotations

import json
from pathlib import Path

from nexa_engine.modules.lineage.domain.models import LineageGraph
from nexa_engine.modules.audit.use_cases.audit_simulation import AuditSimulationUseCase
from nexa_engine.modules.shared.versioning.version_registry import VersionRegistry
from nexa_engine.modules.lineage.infrastructure.snapshot_repository import (
    LineageSnapshotRepository,
)


_LEGACY_GRAPH = {
    "simulation_id": "legacy-sim",
    "nodes": [
        {
            "trace_id": "abc",
            "simulation_id": "legacy-sim",
            "stage": "REQUEST_BUILD",
            "calculator": "ContextBuilder",
            "value_name": "request.panel.margen",
            "value": 0.18,
            "formula": "Panel knob margen",
            "inputs": [],
            "outputs": [],
            # legacy placeholder keys — these used to be the only fields.
            "engine_version_placeholder": "engine-v2",
            "formula_set_placeholder": "formula-set-v2-7",
        }
    ],
    "roots": ["abc"],
    "parametrization_hashes": {},
}


def test_legacy_lineage_deserialization_tolerates_placeholders():
    graph = LineageGraph.from_dict(_LEGACY_GRAPH)
    assert graph.simulation_id == "legacy-sim"
    node = graph.nodes[0]
    # New canonical attribute populated from legacy key.
    assert node.engine_version == "engine-v2"
    assert node.formula_set == "formula-set-v2-7"
    # Legacy alias accessor still works.
    assert node.engine_version_placeholder == node.engine_version


def test_legacy_lineage_round_trip_writes_new_keys(tmp_path: Path):
    # Persist a legacy file directly, then load via repo and re-emit.
    base = tmp_path / "storage" / "lineage"
    (base / "legacy-sim").mkdir(parents=True)
    (base / "legacy-sim" / "lineage.json").write_text(
        json.dumps(_LEGACY_GRAPH, indent=2), encoding="utf-8"
    )
    repo = LineageSnapshotRepository(base_dir=base)
    graph = repo.load("legacy-sim")
    assert graph.nodes[0].engine_version == "engine-v2"
    # Re-emitting must use the new canonical key.
    out = graph.to_dict()
    assert "engine_version" in out["nodes"][0]
    assert "engine_version_placeholder" not in out["nodes"][0]


def test_audit_fallback_to_registry_for_legacy_graph(tmp_path: Path, fake_storage):
    base = tmp_path / "storage" / "lineage"
    (base / "legacy-sim").mkdir(parents=True)
    (base / "legacy-sim" / "lineage.json").write_text(
        json.dumps(_LEGACY_GRAPH, indent=2), encoding="utf-8"
    )
    use_case = AuditSimulationUseCase(
        lineage_repo=LineageSnapshotRepository(base_dir=base),
        version_registry=VersionRegistry(storage_root=fake_storage),
    )
    audit = use_case.execute("legacy-sim")
    # Legacy graph had empty hashes → registry fallback should fill them.
    assert audit.parametrization_hashes  # non-empty
    assert audit.engine_version == "engine-v2"
    assert audit.formula_set == "formula-set-v2-7"
