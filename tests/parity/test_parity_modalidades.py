"""Parity tests by modalidad (Inbound, Outbound, Blended)."""
import pytest
from tests.parity.tolerance import assert_close, factor_billing


MODALIDADES = ["Inbound", "Outbound", "Blended"]


@pytest.mark.parametrize("modalidad", MODALIDADES)
def test_modalidad_formula_paridad(run_engine, canonical_input, modalidad):
    canonical_input["condiciones_cadena_a"]["perfiles"][0]["modalidad"] = modalidad
    res = run_engine(canonical_input)
    p = canonical_input["panel_de_control"]
    expected_ratio = 1.0 / factor_billing(
        p["margen"], op_cont=p["op_cont"], com_cont=p["com_cont"],
        markup=p["markup"], descuento=p["descuento"])
    for m in res.pyg_por_mes:
        c = m.payroll_a + m.no_payroll_a
        if c > 0 and (m.rampup or 0) > 0:
            ratio = (m.ingreso_bruto_a / c) / m.rampup
            assert_close(ratio, expected_ratio, label=f"{modalidad} mes={m.mes}")
            return
    raise AssertionError(f"{modalidad}: no month with valid cost/ramp-up")
