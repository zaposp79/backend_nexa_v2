"""WAVE 10 — Integration tests: end-to-end lineage with Bancamia fixture.

We reuse the canonical Bancamia v2_7 fixture from `tests/parity/fixtures/`
to run the engine with `with_lineage=True` and validate the structure of
the resulting `LineageGraph`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexa_engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.lineage.domain.models import LineageGraph
from nexa_engine.modules.lineage.domain.query import LineageQuery
from nexa_engine.modules.lineage.domain.models import (
    SOURCE_TYPE_EXCEL,
    SOURCE_TYPE_REQUEST,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BANCAMIA_FIXTURE = PROJECT_ROOT / "tests" / "parity" / "fixtures" / "bancamia_v2_7.json"


@pytest.fixture(scope="module")
def bancamia_input() -> dict:
    return json.loads(BANCAMIA_FIXTURE.read_text())["inputs"]


@pytest.fixture(scope="module")
def engine() -> NexaPricingEngine:
    return NexaPricingEngine()


@pytest.fixture(scope="module")
def loader() -> UserInputLoader:
    return UserInputLoader()


@pytest.fixture(scope="module")
def builder() -> SimulationContextBuilder:
    return SimulationContextBuilder()


@pytest.fixture(scope="module")
def request_obj(bancamia_input, loader, builder, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("lineage_bancamia")
    p = tmp / "bancamia.json"
    p.write_text(json.dumps(bancamia_input, default=str))
    ui = loader.cargar(p)
    return builder.construir(ui)


@pytest.fixture(scope="module")
def lineage_run(engine, request_obj):
    """Run the engine once with lineage; share across tests."""
    return engine.calcular(request_obj, with_lineage=True)


def test_with_lineage_returns_tuple(lineage_run):
    assert isinstance(lineage_run, tuple)
    assert len(lineage_run) == 2
    result, graph = lineage_run
    assert result is not None
    assert isinstance(graph, LineageGraph)


def test_default_call_still_returns_only_result(engine, request_obj):
    """Default behaviour pre-WAVE-10 must be unchanged."""
    result = engine.calcular(request_obj)
    assert not isinstance(result, tuple)
    assert hasattr(result, "pyg_por_mes")


def test_graph_has_meaningful_node_count(lineage_run):
    _, graph = lineage_run
    # 50-100 critical nodes target; allow ≥ 20 lower bound in case of partial canales
    assert len(graph.nodes) >= 20, f"too few lineage nodes: {len(graph.nodes)}"


def test_graph_has_roots(lineage_run):
    _, graph = lineage_run
    assert len(graph.roots) >= 1


def test_panel_margen_traced_from_request_to_excel(lineage_run):
    _, graph = lineage_run
    node = LineageQuery(graph).find_value("request.panel.margen")
    assert node is not None
    # both request ref and excel ref should be present
    types = {r.source_type for r in node.inputs}
    assert SOURCE_TYPE_REQUEST in types
    assert SOURCE_TYPE_EXCEL in types


def test_vision_tarifas_canales_have_lineage(lineage_run):
    result, graph = lineage_run
    if result.vision_tarifas is None or not result.vision_tarifas.canales:
        pytest.skip("Bancamia run without vision_tarifas canales — fixture-dependent")
    sample_canal = result.vision_tarifas.canales[0]
    key = f"vision_tarifas.tarifa[canal={sample_canal.nombre_canal}]"
    node = LineageQuery(graph).find_value(key)
    assert node is not None, f"missing lineage node for {key}"
    # check that the formula text mentions factor_billing
    assert "factor_billing" in node.formula or "tarifa" in node.formula


def test_kpis_utilidad_neta_is_root(lineage_run):
    _, graph = lineage_run
    node = LineageQuery(graph).find_value("kpis.utilidad_neta_total")
    if node is None:
        pytest.skip("kpis not present in this run")
    assert node.trace_id in graph.roots


def test_explain_renders_panel_margen_chain(lineage_run):
    _, graph = lineage_run
    text = LineageQuery(graph).explain("request.panel.margen")
    assert "request.panel.margen" in text
    assert "Excel" in text or "Panel-Deal" in text


def test_lineage_persisted_to_disk(lineage_run, tmp_path_factory):
    """The engine persists by default under storage/lineage/<sim_id>/."""
    from nexa_engine.modules.lineage.infrastructure.snapshot_repository import LineageSnapshotRepository

    _, graph = lineage_run
    repo = LineageSnapshotRepository()
    assert repo.exists(graph.simulation_id), (
        f"expected storage/lineage/{graph.simulation_id}/lineage.json to exist"
    )
    loaded = repo.load(graph.simulation_id)
    assert loaded.simulation_id == graph.simulation_id
    assert len(loaded.nodes) == len(graph.nodes)


def test_lineage_graph_serializes_deterministically(lineage_run):
    _, graph = lineage_run
    a = json.dumps(graph.to_dict(), sort_keys=True, default=str)
    b = json.dumps(graph.to_dict(), sort_keys=True, default=str)
    assert a == b


def test_at_least_five_critical_values_traced(lineage_run):
    """Plan target: ≥5 critical values fully traceable."""
    _, graph = lineage_run
    q = LineageQuery(graph)
    expected_some_of = [
        "request.panel.margen",
        "request.panel.op_cont",
        "request.panel.com_cont",
        "request.panel.markup",
        "request.panel.descuento",
        "kpis.ingreso_bruto_total",
        "kpis.costo_total_contrato",
        "kpis.contribucion_total",
        "cost_to_serve.costo_total",
    ]
    hits = [n for n in expected_some_of if q.find_value(n) is not None]
    assert len(hits) >= 5, f"only {len(hits)} critical values traced: {hits}"
