"""WAVE 14 — simulation_id must be consistent between /calculate and /audit."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine


class _FakePanel:
    def __init__(self, cliente="Cliente", sim_id=None):
        self.cliente = cliente
        if sim_id is not None:
            self.simulation_id = sim_id


def _make_request(sim_id=None, cliente="Cliente"):
    req = SimpleNamespace()
    req.panel = _FakePanel(cliente=cliente, sim_id=sim_id)
    return req


def test_generate_simulation_id_default_is_uuid_like():
    req = _make_request()
    sid = NexaPricingEngine._generate_simulation_id(req)
    assert isinstance(sid, str)
    assert len(sid) >= 16


def test_generate_simulation_id_honors_panel_field():
    req = _make_request(sim_id="explicit-sim-123")
    sid = NexaPricingEngine._generate_simulation_id(req)
    assert sid == "explicit-sim-123"


def test_generate_simulation_id_honors_metadata_object():
    req = _make_request()
    req.metadata = SimpleNamespace(simulation_id="metadata-sim")
    sid = NexaPricingEngine._generate_simulation_id(req)
    assert sid == "metadata-sim"


def test_generate_simulation_id_honors_metadata_dict():
    req = _make_request()
    req.metadata = {"simulation_id": "from-dict"}
    sid = NexaPricingEngine._generate_simulation_id(req)
    assert sid == "from-dict"


def test_generate_simulation_id_distinct_calls_are_unique():
    req = _make_request()
    a = NexaPricingEngine._generate_simulation_id(req)
    b = NexaPricingEngine._generate_simulation_id(req)
    assert a != b


def test_audit_finds_lineage_by_simulation_id(tmp_path: Path):
    """Persist via a simulation_id and retrieve via the same id end-to-end."""
    from nexa_engine.modules.lineage.domain.models import LineageGraph, LineageNode
    from nexa_engine.modules.shared.versioning.version_registry import VersionMetadata
    from nexa_engine.modules.lineage.infrastructure.json_emitter import JsonLineageEmitter
    from nexa_engine.modules.lineage.infrastructure.snapshot_repository import (
        LineageSnapshotRepository,
    )
    from nexa_engine.modules.audit.use_cases.audit_simulation import (
        AuditSimulationUseCase,
    )

    sim_id = "test-sim-mapping-001"
    emitter = JsonLineageEmitter(sim_id, version_metadata=VersionMetadata())
    emitter.emit(stage="X", inputs={}, outputs={"v": 1}, source="t")
    graph = emitter.get_graph()

    base = tmp_path / "storage" / "lineage"
    repo = LineageSnapshotRepository(base_dir=base)
    repo.save(graph)

    # The persisted graph carries the same id.
    assert repo.exists(sim_id)
    audit = AuditSimulationUseCase(lineage_repo=repo).execute(sim_id)
    assert audit.simulation_id == sim_id
