"""WAVE 14 — audit response must surface real versions and hashes."""
from __future__ import annotations

from pathlib import Path

from nexa_engine.modules.lineage.domain.models import LineageGraph, LineageNode
from nexa_engine.modules.audit.use_cases.audit_simulation import AuditSimulationUseCase
from nexa_engine.modules.shared.versioning.version_registry import VersionMetadata, VersionRegistry
from nexa_engine.modules.lineage.infrastructure.json_emitter import JsonLineageEmitter
from nexa_engine.modules.lineage.infrastructure.snapshot_repository import (
    LineageSnapshotRepository,
)


def _persist_graph_with_versions(base: Path, sim_id: str, meta: VersionMetadata):
    emitter = JsonLineageEmitter(sim_id, version_metadata=meta)
    emitter.emit(stage="X", inputs={}, outputs={"v": 1}, source="t")
    graph = emitter.get_graph()
    repo = LineageSnapshotRepository(base_dir=base)
    repo.save(graph)
    return repo


def test_audit_response_uses_real_engine_version(tmp_path: Path):
    meta = VersionMetadata(
        engine_version="engine-v2",
        formula_set="formula-set-v2-7",
        parametrization_version="v2-7",
        parametrization_hashes={"hr": "a" * 64, "gn": "b" * 64},
    )
    base = tmp_path / "storage" / "lineage"
    repo = _persist_graph_with_versions(base, "sim-A", meta)
    use_case = AuditSimulationUseCase(lineage_repo=repo)
    audit = use_case.execute("sim-A")
    assert audit.engine_version == "engine-v2"
    assert audit.formula_set == "formula-set-v2-7"


def test_audit_response_includes_real_hashes(tmp_path: Path):
    meta = VersionMetadata(
        parametrization_hashes={"hr": "h" * 64, "gn": "g" * 64, "op": "o" * 64},
    )
    base = tmp_path / "storage" / "lineage"
    repo = _persist_graph_with_versions(base, "sim-B", meta)
    use_case = AuditSimulationUseCase(lineage_repo=repo)
    audit = use_case.execute("sim-B")
    assert audit.parametrization_hashes == {
        "hr": "h" * 64,
        "gn": "g" * 64,
        "op": "o" * 64,
    }


def test_audit_hashes_match_registry_for_live_storage(fake_storage: Path, tmp_path: Path):
    reg = VersionRegistry(storage_root=fake_storage)
    meta = reg.get_current()
    base = tmp_path / "storage" / "lineage"
    repo = _persist_graph_with_versions(base, "sim-C", meta)
    use_case = AuditSimulationUseCase(lineage_repo=repo, version_registry=reg)
    audit = use_case.execute("sim-C")
    assert audit.parametrization_hashes == reg.compute_parametrization_hashes()


def test_audit_response_placeholders_no_longer_literal(tmp_path: Path, fake_storage: Path):
    """When live storage is present, hashes are non-empty real SHA-256."""
    reg = VersionRegistry(storage_root=fake_storage)
    base = tmp_path / "storage" / "lineage"
    repo = _persist_graph_with_versions(base, "sim-D", reg.get_current())
    use_case = AuditSimulationUseCase(lineage_repo=repo, version_registry=reg)
    audit = use_case.execute("sim-D")
    assert audit.parametrization_hashes  # non-empty
    for h in audit.parametrization_hashes.values():
        assert len(h) == 64
        int(h, 16)
