"""Smoke test: harness can run the engine on the canonical parity input."""
from tests.parity.tolerance import assert_close, expected_ingreso


def test_engine_runs_and_produces_pyg(run_engine, canonical_input):
    res = run_engine(canonical_input)
    assert len(res.pyg_por_mes) == 12
    m1 = res.pyg_por_mes[0]
    # Cadena A only: B and C must be zero
    assert m1.ingreso_bruto_b == 0.0
    assert m1.ingreso_bruto_c == 0.0
    assert m1.ingreso_bruto_a > 0.0


def test_formula_oracle_ingreso_a_uses_denominator_exacto(run_engine, canonical_input):
    """Bloque 1 WAVE 3: ingreso_a/costo_a = 1/factor_billing(margen_a, ...)
    (the ramp-up factor cancels in the per-month ratio, so this works on every mes).
    """
    from tests.parity.tolerance import factor_billing
    res = run_engine(canonical_input)
    p = canonical_input["panel_de_control"]
    expected_ratio = 1.0 / factor_billing(
        p["margen"], op_cont=p["op_cont"], com_cont=p["com_cont"],
        markup=p["markup"], descuento=p["descuento"],
    )
    # ingreso_a = costo_a / factor_billing × ramp-up. Recover the ratio dividing by ramp-up.
    for m in res.pyg_por_mes:
        c = m.payroll_a + m.no_payroll_a
        rampup = m.rampup or 1.0
        if c <= 0 or rampup <= 0:
            continue
        ratio = (m.ingreso_bruto_a / c) / rampup
        assert_close(ratio, expected_ratio, label=f"mes={m.mes} ingreso_a/costo_a/rampup")
        return
    raise AssertionError("No month with cost_a > 0")
