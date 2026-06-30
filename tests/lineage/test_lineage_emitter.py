"""WAVE 10 — JsonLineageEmitter + LineageSnapshotRepository tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexa_engine.modules.lineage.domain.models import (
    LineageGraph,
    LineageRef,
    SOURCE_TYPE_REQUEST,
)
from nexa_engine.modules.shared.ports.trace_emitter import ITraceEmitter
from nexa_engine.modules.lineage.infrastructure.json_emitter import JsonLineageEmitter
from nexa_engine.modules.lineage.infrastructure.snapshot_repository import LineageSnapshotRepository
from nexa_engine.modules.lineage.infrastructure.null_emitter import NullLineageEmitter


def test_emitter_implements_itraceemitter_protocol():
    e = JsonLineageEmitter("sim-1")
    assert isinstance(e, ITraceEmitter)


def test_emit_appends_node_and_graph_is_immutable():
    e = JsonLineageEmitter("sim-1")
    e.emit(stage="A", inputs={"x": 1}, outputs={"y": 2}, source="Panel")
    assert e.node_count == 1
    g = e.get_graph()
    assert isinstance(g, LineageGraph)
    assert len(g.nodes) == 1
    assert g.simulation_id == "sim-1"
    # immutability: cannot mutate dataclass fields
    with pytest.raises(Exception):
        g.nodes[0].value = 999  # type: ignore[misc]


def test_emit_with_explicit_lineage_refs_preserved():
    e = JsonLineageEmitter("sim-1")
    refs = [
        LineageRef(SOURCE_TYPE_REQUEST, "request.panel.margen", 0.21),
        LineageRef("excel", "Excel:Panel!C9", 0.21, sheet="Panel", cell="C9"),
    ]
    e.emit(
        stage="REQUEST_BUILD",
        inputs={"margen": 0.21},
        outputs={"factor_billing": 0.6588},
        source="Panel",
        lineage_refs=refs,
        value_name="pricing.factor_billing",
        formula="costo / ((1-m)*(1-op)*(1-com))",
    )
    g = e.get_graph()
    assert g.nodes[0].value_name == "pricing.factor_billing"
    assert g.nodes[0].inputs == tuple(refs)
    assert g.nodes[0].formula.startswith("costo / ")


def test_emit_marks_roots_and_get_graph_returns_them():
    e = JsonLineageEmitter("sim-2")
    e.emit(stage="X", inputs={"a": 1}, outputs={"b": 2}, source="Panel")
    e.emit(stage="Y", inputs={}, outputs={"c": 9}, source="VisionTarifasCalculator", is_root=True)
    g = e.get_graph()
    assert len(g.roots) == 1
    assert g.by_trace_id(g.roots[0]).stage == "Y"


def test_null_lineage_emitter_is_noop():
    e = NullLineageEmitter()
    e.emit(stage="X", inputs={"a": 1}, outputs={"b": 2}, source="Panel")
    # no public state to inspect, no error raised


def test_snapshot_repository_save_and_load_idempotent(tmp_path: Path):
    repo = LineageSnapshotRepository(base_dir=tmp_path)
    e = JsonLineageEmitter("sim-rt")
    e.emit(stage="A", inputs={"x": 1}, outputs={"y": 2}, source="Panel", value_name="t.y")
    graph = e.get_graph()
    p1 = repo.save(graph)
    p2 = repo.save(graph)
    assert p1 == p2
    assert p1.exists()
    txt1 = p1.read_text()
    repo.save(graph)
    txt2 = p1.read_text()
    assert txt1 == txt2  # deterministic
    loaded = repo.load("sim-rt")
    assert loaded.simulation_id == "sim-rt"
    assert len(loaded.nodes) == 1
    assert loaded.nodes[0].value_name == "t.y"


def test_snapshot_repository_handles_unsafe_ids(tmp_path: Path):
    repo = LineageSnapshotRepository(base_dir=tmp_path)
    g = LineageGraph(simulation_id="cliente/with*weird:chars")
    p = repo.save(g)
    assert p.exists()
    assert "/" not in p.parent.name
    assert "*" not in p.parent.name


def test_lineage_ref_rejects_unknown_source_type():
    with pytest.raises(ValueError):
        LineageRef(source_type="bogus", source_id="x", value=1)


def test_lineage_graph_by_value_name_returns_last_writer():
    e = JsonLineageEmitter("sim-3")
    e.emit(stage="A", inputs={}, outputs={"x": 1}, source="Panel", value_name="t.x")
    e.emit(stage="B", inputs={}, outputs={"x": 2}, source="Panel", value_name="t.x")
    g = e.get_graph()
    n = g.by_value_name("t.x")
    assert n.value == 2
    assert n.stage == "B"


def test_emitter_signature_compatible_with_legacy_callsites():
    """The WAVE 9 callsite signature must keep working unchanged."""
    e = JsonLineageEmitter("sim-4")
    # WAVE 9 callsite — no kwargs beyond the 4 required
    e.emit("pricing.factor_billing", {"margen": 0.2}, {"factor_billing": 0.66}, "Panel-Deal")
    g = e.get_graph()
    assert len(g.nodes) == 1
    assert g.nodes[0].stage == "pricing.factor_billing"


def test_graph_to_dict_and_from_dict_roundtrip():
    e = JsonLineageEmitter("sim-rt2")
    e.emit(
        stage="A",
        inputs={"m": 0.2},
        outputs={"fb": 0.65},
        source="Panel",
        value_name="t.fb",
        formula="f = g(m)",
        lineage_refs=[LineageRef(SOURCE_TYPE_REQUEST, "request.panel.m", 0.2)],
    )
    g = e.get_graph()
    d = g.to_dict()
    s = json.dumps(d, sort_keys=True)
    d2 = json.loads(s)
    g2 = LineageGraph.from_dict(d2)
    assert g2.simulation_id == g.simulation_id
    assert len(g2.nodes) == len(g.nodes)
    assert g2.nodes[0].value_name == "t.fb"
    assert g2.nodes[0].inputs[0].source_id == "request.panel.m"
