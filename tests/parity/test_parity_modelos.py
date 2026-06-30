"""Parity tests by modelo de cobro (Fijo FTE, Variable, Híbrido)."""
import pytest
from tests.parity.tolerance import assert_close, factor_billing


MODELOS = [
    ("Fijo FTE", 1.0),    # 100% fijo
    ("Variable", 0.0),    # 0% fijo = 100% variable
    ("Híbrido", 0.5),     # 50/50
]


@pytest.mark.parametrize("modelo,pct_fijo", MODELOS)
def test_modelo_cobro_formula_paridad(run_engine, canonical_input, modelo, pct_fijo):
    canonical_input["condiciones_cadena_a"]["perfiles"][0]["modelo_cobro"] = modelo
    canonical_input["condiciones_cadena_a"]["perfiles"][0]["pct_fijo"] = pct_fijo
    res = run_engine(canonical_input)
    p = canonical_input["panel_de_control"]
    expected_ratio = 1.0 / factor_billing(
        p["margen"], op_cont=p["op_cont"], com_cont=p["com_cont"],
        markup=p["markup"], descuento=p["descuento"])
    for m in res.pyg_por_mes:
        c = m.payroll_a + m.no_payroll_a
        if c > 0 and (m.rampup or 0) > 0:
            ratio = (m.ingreso_bruto_a / c) / m.rampup
            assert_close(ratio, expected_ratio, label=f"{modelo} mes={m.mes}")
            return
    raise AssertionError(f"{modelo}: no month with valid cost/ramp-up")
