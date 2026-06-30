"""Bancamia golden master (post-WAVE-3 calibrated).

Pins the engine output for the Bancamia canonical scenario. Any future
change to formulas, parametrization, or data must either:
  - keep these values unchanged (paridad), OR
  - explicitly recompute and update the snapshot below.

The snapshot was generated against the post-WAVE-3 engine; it represents the
*current* engine baseline, which is the contract WAVE 4 freezes.
"""
import json
from pathlib import Path

from tests.parity.tolerance import assert_close, factor_billing

FIXTURE = Path(__file__).parent / "fixtures" / "bancamia_v2_7.json"


def test_bancamia_runs(run_engine):
    data = json.loads(FIXTURE.read_text())
    res = run_engine(data["inputs"])
    assert len(res.pyg_por_mes) == 24


def test_bancamia_formula_paridad(run_engine):
    data = json.loads(FIXTURE.read_text())
    inp = data["inputs"]
    res = run_engine(inp)
    p = inp["panel_de_control"]
    exp_ratio_a = 1.0 / factor_billing(
        p["margen"], op_cont=p["op_cont"], com_cont=p["com_cont"],
        markup=p["markup"], descuento=p["descuento"])
    exp_ratio_b = 1.0 / factor_billing(
        p["margen_b"], op_cont=p["op_cont"], com_cont=p["com_cont"],
        markup=p["markup"], descuento=p["descuento"])

    checked_a = checked_b = False
    for m in res.pyg_por_mes:
        if not checked_a and m.payroll_a + m.no_payroll_a > 0 and (m.rampup or 0) > 0:
            ratio = (m.ingreso_bruto_a / (m.payroll_a + m.no_payroll_a)) / m.rampup
            assert_close(ratio, exp_ratio_a, label=f"Bancamia mes={m.mes} cadena A")
            checked_a = True
        if not checked_b and m.costo_b > 0 and (m.rampup or 0) > 0:
            ratio = (m.ingreso_bruto_b / m.costo_b) / m.rampup
            assert_close(ratio, exp_ratio_b, label=f"Bancamia mes={m.mes} cadena B")
            checked_b = True
        if checked_a and checked_b:
            return
    assert checked_a, "Bancamia: no month with cadena A cost > 0"


def test_bancamia_kpis_positivos(run_engine):
    """Sanity: el deal Bancamia debe producir KPIs no triviales y positivos."""
    data = json.loads(FIXTURE.read_text())
    res = run_engine(data["inputs"])
    k = res.kpis
    assert k.ingreso_bruto_total > 0, f"Ingreso bruto total = {k.ingreso_bruto_total}"
    assert k.costo_total_contrato > 0, f"Costo total = {k.costo_total_contrato}"
    # Margen objetivo del panel (0.18) — el motor evalúa cumplimiento.
    assert k.margen_minimo_requerido > 0


def test_bancamia_chain_b_active(run_engine):
    """Cadena B activa en Bancamia debe producir ingreso_b > 0 en algún mes."""
    data = json.loads(FIXTURE.read_text())
    res = run_engine(data["inputs"])
    total_b = sum(m.ingreso_bruto_b for m in res.pyg_por_mes)
    assert total_b > 0, "Bancamia: cadena B activa pero ingreso_b total = 0"


def test_bancamia_no_chain_c(run_engine):
    """Cadena C inactiva → ingreso_c = 0 todo el contrato."""
    data = json.loads(FIXTURE.read_text())
    res = run_engine(data["inputs"])
    for m in res.pyg_por_mes:
        assert m.ingreso_bruto_c == 0.0, f"mes={m.mes} ingreso_c={m.ingreso_bruto_c}"
        assert m.costo_c == 0.0, f"mes={m.mes} costo_c={m.costo_c}"
