"""WAVE 10 — LineageQuery tests."""
from __future__ import annotations

import uuid

from nexa_engine.modules.lineage.domain.query import LineageQuery
from nexa_engine.modules.lineage.domain.models import (
    LineageGraph,
    LineageNode,
    LineageRef,
    SOURCE_TYPE_COMPUTED,
    SOURCE_TYPE_EXCEL,
    SOURCE_TYPE_REQUEST,
)


def _node(value_name: str, value, inputs=()) -> LineageNode:
    return LineageNode(
        trace_id=uuid.uuid4().hex,
        simulation_id="sim",
        stage="VISION_BUILD",
        calculator="TestCalc",
        value_name=value_name,
        value=value,
        formula="",
        inputs=tuple(inputs),
    )


def test_find_value_returns_last_writer():
    a = _node("x", 1)
    b = _node("x", 2)
    g = LineageGraph(simulation_id="sim", nodes=(a, b))
    q = LineageQuery(g)
    assert q.find_value("x") is b


def test_find_value_returns_none_for_missing():
    g = LineageGraph(simulation_id="sim", nodes=())
    assert LineageQuery(g).find_value("missing") is None


def test_trace_back_follows_computed_parents():
    leaf = _node(
        "leaf",
        0.21,
        inputs=[
            LineageRef(SOURCE_TYPE_REQUEST, "request.panel.margen", 0.21),
            LineageRef(SOURCE_TYPE_EXCEL, "Excel:Panel!C9", 0.21, sheet="Panel", cell="C9"),
        ],
    )
    mid = _node(
        "factor_billing",
        0.65,
        inputs=[
            LineageRef(SOURCE_TYPE_COMPUTED, f"computed:trace:{leaf.trace_id}", 0.21),
        ],
    )
    g = LineageGraph(simulation_id="sim", nodes=(leaf, mid))
    q = LineageQuery(g)
    refs = q.trace_back("factor_billing")
    # we should see: the direct computed ref + the two refs of leaf
    assert any(r.source_type == "excel" for r in refs)
    assert any(r.source_id == "request.panel.margen" for r in refs)


def test_explain_renders_human_readable_chain():
    leaf = _node(
        "vision_tarifas.tarifa[WhatsApp]",
        8421.33,
        inputs=[
            LineageRef(SOURCE_TYPE_REQUEST, "request.panel.margen", 0.21),
            LineageRef(SOURCE_TYPE_EXCEL, "Excel:Rot Ausent y Rentabilidad!G11", 0.1199,
                       sheet="Rot Ausent y Rentabilidad", cell="G11"),
        ],
    )
    g = LineageGraph(simulation_id="sim", nodes=(leaf,))
    text = LineageQuery(g).explain("vision_tarifas.tarifa[WhatsApp]")
    assert "vision_tarifas.tarifa[WhatsApp] = 8421.33" in text
    assert "Excel:Rot Ausent y Rentabilidad!G11" in text
    assert "request.panel.margen" in text


def test_explain_handles_missing_value():
    g = LineageGraph(simulation_id="sim", nodes=())
    text = LineageQuery(g).explain("does.not.exist")
    assert "not found" in text


def test_trace_back_handles_cycles_gracefully():
    # node_a parent is node_b ; node_b parent is node_a
    a_id = uuid.uuid4().hex
    b_id = uuid.uuid4().hex
    a = LineageNode(
        trace_id=a_id,
        simulation_id="sim",
        stage="X",
        calculator="C",
        value_name="a",
        value=1,
        inputs=(LineageRef(SOURCE_TYPE_COMPUTED, f"computed:trace:{b_id}", None),),
    )
    b = LineageNode(
        trace_id=b_id,
        simulation_id="sim",
        stage="X",
        calculator="C",
        value_name="b",
        value=2,
        inputs=(LineageRef(SOURCE_TYPE_COMPUTED, f"computed:trace:{a_id}", None),),
    )
    g = LineageGraph(simulation_id="sim", nodes=(a, b))
    refs = LineageQuery(g).trace_back("a")
    assert isinstance(refs, list)  # must not loop forever
