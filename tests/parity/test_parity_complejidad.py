"""Parity tests by complejidad (Baja, Media, Alta) ↔ markup.

Excel V2-7 traduce complejidad a markup vía:
  Baja = 0.0, Media = 0.04, Alta = 0.08 (aprox; consulta `business_rules.json`).
"""
import pytest
from tests.parity.tolerance import assert_close, factor_billing


COMPLEJIDADES = [
    ("Baja", 0.0),
    ("Media", 0.04),
    ("Alta", 0.08),
]


@pytest.mark.parametrize("nombre,markup", COMPLEJIDADES)
def test_complejidad_markup_paridad(run_engine, canonical_input, patch_input, nombre, markup):
    inp = patch_input(canonical_input, panel={"markup": markup})
    res = run_engine(inp)
    p = inp["panel_de_control"]
    expected_ratio = 1.0 / factor_billing(
        p["margen"], op_cont=p["op_cont"], com_cont=p["com_cont"],
        markup=markup, descuento=p["descuento"])
    for m in res.pyg_por_mes:
        c = m.payroll_a + m.no_payroll_a
        if c > 0 and (m.rampup or 0) > 0:
            ratio = (m.ingreso_bruto_a / c) / m.rampup
            assert_close(ratio, expected_ratio, label=f"{nombre}(markup={markup}) mes={m.mes}")
            return
    raise AssertionError(f"{nombre}: no month with valid cost/ramp-up")
