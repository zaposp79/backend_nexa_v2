"""WAVE 14 — lineage graphs must carry real version metadata."""
from __future__ import annotations

from nexa_engine.modules.lineage.domain.models import LineageGraph, LineageNode
from nexa_engine.modules.shared.versioning.version_registry import VersionMetadata
from nexa_engine.modules.lineage.infrastructure.json_emitter import JsonLineageEmitter


def _meta() -> VersionMetadata:
    return VersionMetadata(
        excel_version="V2-7",
        parametrization_version="v2-7",
        engine_version="engine-v2",
        api_version="api-v1",
        formula_set="formula-set-v2-7",
        parametrization_hashes={"hr": "h" * 64, "gn": "g" * 64},
    )


def test_emitter_nodes_carry_real_engine_version():
    emitter = JsonLineageEmitter("sim-1", version_metadata=_meta())
    emitter.emit(stage="X", inputs={}, outputs={"v": 1}, source="t")
    graph = emitter.get_graph()
    node = graph.nodes[0]
    assert node.engine_version == "engine-v2"
    assert node.formula_set == "formula-set-v2-7"


def test_emitter_graph_carries_parametrization_hashes():
    emitter = JsonLineageEmitter("sim-2", version_metadata=_meta())
    emitter.emit(stage="X", inputs={}, outputs={"v": 1}, source="t")
    graph = emitter.get_graph()
    assert graph.parametrization_hashes == {"hr": "h" * 64, "gn": "g" * 64}
    assert graph.version_metadata is not None
    assert graph.version_metadata["parametrization_version"] == "v2-7"


def test_emitter_serialization_uses_new_keys():
    emitter = JsonLineageEmitter("sim-3", version_metadata=_meta())
    emitter.emit(stage="X", inputs={}, outputs={"v": 1}, source="t")
    graph = emitter.get_graph()
    d = graph.to_dict()
    assert "version_metadata" in d
    node_d = d["nodes"][0]
    assert "engine_version" in node_d
    assert "formula_set" in node_d
    # legacy placeholder keys must NOT be emitted any more
    assert "engine_version_placeholder" not in node_d


def test_emitter_default_metadata_when_omitted():
    emitter = JsonLineageEmitter("sim-4")
    emitter.emit(stage="X", inputs={}, outputs={"v": 1}, source="t")
    graph = emitter.get_graph()
    # No metadata supplied → defaults to engine-v2 / formula-set-v2-7.
    assert graph.nodes[0].engine_version == "engine-v2"
    assert graph.nodes[0].formula_set == "formula-set-v2-7"


def test_explicit_overrides_propagated():
    emitter = JsonLineageEmitter(
        "sim-5",
        version_metadata=_meta(),
        engine_version="engine-v9",
        formula_set="formula-set-experimental",
    )
    emitter.emit(stage="X", inputs={}, outputs={"v": 1}, source="t")
    graph = emitter.get_graph()
    assert graph.nodes[0].engine_version == "engine-v9"
    assert graph.nodes[0].formula_set == "formula-set-experimental"
    assert graph.version_metadata["engine_version"] == "engine-v9"
