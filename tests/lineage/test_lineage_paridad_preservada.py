"""WAVE 10 — Paridad inmutable: con/sin lineage los outputs son idénticos."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexa_engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BANCAMIA_FIXTURE = PROJECT_ROOT / "tests" / "parity" / "fixtures" / "bancamia_v2_7.json"


@pytest.fixture(scope="module")
def request_obj(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("lineage_par")
    inputs = json.loads(BANCAMIA_FIXTURE.read_text())["inputs"]
    p = tmp / "bancamia.json"
    p.write_text(json.dumps(inputs, default=str))
    ui = UserInputLoader().cargar(p)
    return SimulationContextBuilder().construir(ui)


@pytest.fixture(scope="module")
def engine() -> NexaPricingEngine:
    return NexaPricingEngine()


def test_pyg_values_identical_with_and_without_lineage(engine, request_obj):
    r_no = engine.calcular(request_obj)
    r_yes, _graph = engine.calcular(request_obj, with_lineage=True)

    assert len(r_no.pyg_por_mes) == len(r_yes.pyg_por_mes)
    for a, b in zip(r_no.pyg_por_mes, r_yes.pyg_por_mes):
        assert a.mes == b.mes
        assert a.ingreso_bruto == pytest.approx(b.ingreso_bruto, rel=1e-12, abs=1e-9)
        assert a.costo_total == pytest.approx(b.costo_total, rel=1e-12, abs=1e-9)
        assert a.contribucion == pytest.approx(b.contribucion, rel=1e-12, abs=1e-9)


def test_kpis_identical_with_and_without_lineage(engine, request_obj):
    r_no = engine.calcular(request_obj)
    r_yes, _ = engine.calcular(request_obj, with_lineage=True)
    k1, k2 = r_no.kpis, r_yes.kpis
    assert k1.ingreso_bruto_total == pytest.approx(k2.ingreso_bruto_total, rel=1e-12)
    assert k1.costo_total_contrato == pytest.approx(k2.costo_total_contrato, rel=1e-12)
    assert k1.utilidad_neta_total == pytest.approx(k2.utilidad_neta_total, rel=1e-12)
    assert k1.valor_total_deal == pytest.approx(k2.valor_total_deal, rel=1e-12)
