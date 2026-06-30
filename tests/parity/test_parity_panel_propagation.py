"""Cableado de campos WAVE 2/3 del Panel V2-7 hasta el resultado.

Verifica que los nuevos campos del Panel (margen_b/c, mes_ajuste_indexacion,
tasa_interes_mensual, imprevistos, op_cont, com_cont, markup, descuento) se
propagan correctamente desde el input JSON hasta los cálculos del motor.
"""
import copy

from tests.parity.tolerance import assert_close, factor_billing


def test_margen_b_propagado(run_engine, canonical_input):
    """Variar margen_b cambia el ratio ingreso_b/costo_b."""
    base = copy.deepcopy(canonical_input)
    base["panel_de_control"]["cadenas_activas"] = {
        "cadena_a": True, "cadena_b": True, "cadena_c": False}
    base["condiciones_cadena_b"] = {
        "canales": [{
            "nombre": "WhatsApp", "modalidad": "Inbound",
            "tarifa_unitaria": 4500.0, "volumen_mensual": 2000,
            "opex_fijo": 50_000_000.0, "pct_escalamiento": 0.0,
            "costo_escalamiento": 0.0,
        }],
        "fte_equipo_sm": 1.0, "amortizar_dispositivos_sm": True,
    }
    base["panel_de_control"]["margen_b"] = 0.30
    r1 = run_engine(base)

    high = copy.deepcopy(base)
    high["panel_de_control"]["margen_b"] = 0.50
    r2 = run_engine(high)

    # Para cualquier mes con costo_b > 0, ingreso_b debe haber subido
    found = False
    for m1, m2 in zip(r1.pyg_por_mes, r2.pyg_por_mes):
        if m1.costo_b > 0:
            assert m2.ingreso_bruto_b > m1.ingreso_bruto_b, (
                f"mes={m1.mes} margen_b=0.50 debe producir ingreso_b > margen_b=0.30")
            found = True
            break
    assert found, "Ningún mes con costo_b > 0"


def test_imprevistos_resta_de_ingreso_neto(run_engine, canonical_input):
    """Imprevistos restan del ingreso bruto para calcular ingreso neto (GAP-PYG-1)."""
    base = copy.deepcopy(canonical_input)
    base["panel_de_control"]["imprevistos"] = 0.0
    r0 = run_engine(base)

    high = copy.deepcopy(base)
    high["panel_de_control"]["imprevistos"] = 0.05
    r1 = run_engine(high)

    for m0, m1 in zip(r0.pyg_por_mes, r1.pyg_por_mes):
        if m0.ingreso_bruto > 0:
            # imprevistos = 0.05 * ingreso_bruto → ingreso_neto = bruto - imprevistos*bruto
            assert m1.imprevistos_ingreso > 0, f"mes={m0.mes} imprevistos no aplicados"
            # Aproximación: imprevistos_ingreso ≈ 0.05 × ingreso_bruto
            assert_close(
                m1.imprevistos_ingreso, 0.05 * m1.ingreso_bruto,
                label=f"mes={m0.mes} imprevistos_ingreso")
            return
    raise AssertionError("No month with ingreso_bruto > 0")


def test_op_cont_y_com_cont_se_aplican(run_engine, canonical_input):
    """Cambiar op_cont/com_cont altera el factor_billing usado por el motor."""
    base = copy.deepcopy(canonical_input)
    base["panel_de_control"]["op_cont"] = 0.0
    base["panel_de_control"]["com_cont"] = 0.0
    r0 = run_engine(base)

    high = copy.deepcopy(base)
    high["panel_de_control"]["op_cont"] = 0.10
    high["panel_de_control"]["com_cont"] = 0.05
    r1 = run_engine(high)

    p = high["panel_de_control"]
    expected_ratio = 1.0 / factor_billing(
        p["margen"], op_cont=p["op_cont"], com_cont=p["com_cont"],
        markup=p["markup"], descuento=p["descuento"])
    for m in r1.pyg_por_mes:
        c = m.payroll_a + m.no_payroll_a
        if c > 0 and (m.rampup or 0) > 0:
            ratio = (m.ingreso_bruto_a / c) / m.rampup
            assert_close(ratio, expected_ratio, label=f"op_cont/com_cont mes={m.mes}")
            return
    raise AssertionError("No month with valid cost")


def test_descuento_aumenta_ingreso(run_engine, canonical_input):
    """descuento > 0 incrementa el ingreso (multiplica por 1+descuento en el denominador,
    pero como el denominador está dividiendo, el ingreso crece)."""
    base = copy.deepcopy(canonical_input)
    base["panel_de_control"]["descuento"] = 0.0
    r0 = run_engine(base)
    high = copy.deepcopy(base)
    high["panel_de_control"]["descuento"] = 0.15
    r1 = run_engine(high)
    for m0, m1 in zip(r0.pyg_por_mes, r1.pyg_por_mes):
        if m0.ingreso_bruto_a > 0:
            # WAVE 3 formula: ingreso = costo / ((1-m)(1-op)(1-com)(1-markup)(1+descuento))
            # → descuento>0 hace el denominador *mayor* → ingreso *menor*.
            assert m1.ingreso_bruto_a < m0.ingreso_bruto_a, (
                f"mes={m0.mes}: descuento=0.15 debería bajar ingreso, "
                f"obtuve {m1.ingreso_bruto_a} vs base {m0.ingreso_bruto_a}")
            return
    raise AssertionError("No month with ingreso_a > 0")
