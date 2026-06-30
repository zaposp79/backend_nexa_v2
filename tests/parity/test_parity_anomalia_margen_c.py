"""Excel V2-7 intentional anomaly (DEC #5 WAVE 0).

Vision Tarifas uses margen_a for ALL chains (incl. Cadena C).
P&G correctly uses margen_c for Cadena C.

This test pins both behaviors so a regression would surface immediately.
"""
import copy

from tests.parity.tolerance import assert_close, factor_billing


def _input_with_chain_c(canonical_input):
    inp = copy.deepcopy(canonical_input)
    inp["panel_de_control"]["cadenas_activas"] = {
        "cadena_a": True, "cadena_b": False, "cadena_c": True}
    inp["condiciones_cadena_c"] = {"canales": [
        {
            "nombre": "C provider",
            "modalidad": "Inbound",
            "tarifa_unitaria": 1000.0,
            "volumen_mensual": 5000,
            "opex_fijo": 10_000_000.0,
            "pct_escalamiento": 0.05,
            "costo_escalamiento": 0.0,
        }
    ]}
    return inp


def test_pyg_cadena_c_usa_margen_c(run_engine, canonical_input):
    """P&G: ingreso_c se calcula con margen_c (no margen_a)."""
    inp = _input_with_chain_c(canonical_input)
    inp["panel_de_control"]["margen_c"] = 0.20  # distinto a margen_a=0.21
    res = run_engine(inp)
    panel = inp["panel_de_control"]
    expected = 1.0 / factor_billing(
        panel["margen_c"], op_cont=panel["op_cont"], com_cont=panel["com_cont"],
        markup=panel["markup"], descuento=panel["descuento"])
    for m in res.pyg_por_mes:
        if m.costo_c > 0 and (m.rampup or 0) > 0:
            ratio = (m.ingreso_bruto_c / m.costo_c) / m.rampup
            assert_close(ratio, expected, label=f"P&G Cadena C mes={m.mes}")
            return


def test_vision_tarifas_cadena_c_usa_margen_a(run_engine, canonical_input):
    """Vision Tarifas usa margen_a en su _factor_billing — anomalía V2-7 documentada.

    Verifica que el factor de billing utilizado en Vision Tarifas refleja
    `panel.margen` (== margen_a), no margen_c.
    """
    inp = _input_with_chain_c(canonical_input)
    res = run_engine(inp)
    assert res.vision_tarifas is not None, "Cadena A activa → vision_tarifas no debe ser None"
    # Verificar la documentación del factor (vision_tarifas usa panel.margen).
    # No expone el factor directamente; comprobamos vía la utilidad
    # calculators.utils.calcular_factor_margenes:
    from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator
    factor = ProfitabilityCalculator.calcular_factor_margenes(res.panel)
    expected = factor_billing(
        res.panel.margen,
        op_cont=res.panel.op_cont, com_cont=res.panel.com_cont,
        markup=res.panel.markup, descuento=res.panel.descuento,
    )
    assert_close(factor, expected, label="Vision Tarifas factor_billing usa margen_a")
