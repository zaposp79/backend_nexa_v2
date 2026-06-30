"""Parity tests by cadena: solo A, solo B, solo C, A+B, A+C, A+B+C.

Esta suite verifica:
1. La activación de cadenas se respeta (`cadenas_activas`).
2. La fórmula WAVE 3 (denominador exacto) se aplica con el margen específico
   por cadena (margen_b=0.30, margen_c=0.20 por default).
"""
import copy

import pytest
from tests.parity.tolerance import assert_close, factor_billing


def _set_chains(inp, a=False, b=False, c=False):
    inp = copy.deepcopy(inp)
    inp["panel_de_control"]["cadenas_activas"] = {
        "cadena_a": a, "cadena_b": b, "cadena_c": c}
    if b and not inp.get("condiciones_cadena_b", {}).get("canales"):
        inp["condiciones_cadena_b"] = {
            "canales": [{
                "nombre": "WhatsApp Inbound",
                "modalidad": "Inbound",
                "tarifa_unitaria": 4500.0,
                "volumen_mensual": 1000,
                "opex_fijo": 50_000_000.0,
                "pct_escalamiento": 0.03,
                "costo_escalamiento": 0.0,
            }],
            "fte_equipo_sm": 1.0,
            "amortizar_dispositivos_sm": True,
        }
    if c:
        inp.setdefault("condiciones_cadena_c", {"canales": []})
    return inp


def _check_ratio(m, panel, cadena: str, margen_cad: float):
    """Assert ingreso_cad/costo_cad/rampup ≈ 1/factor_billing(margen_cad)."""
    if cadena == "a":
        c = m.payroll_a + m.no_payroll_a
        ing = m.ingreso_bruto_a
    elif cadena == "b":
        c = m.costo_b
        ing = m.ingreso_bruto_b
    else:
        c = m.costo_c
        ing = m.ingreso_bruto_c
    if c <= 0 or (m.rampup or 0) <= 0:
        return False
    expected = 1.0 / factor_billing(
        margen_cad, op_cont=panel["op_cont"], com_cont=panel["com_cont"],
        markup=panel["markup"], descuento=panel["descuento"])
    ratio = (ing / c) / m.rampup
    assert_close(ratio, expected, label=f"cadena={cadena} mes={m.mes}")
    return True


def test_solo_a(run_engine, canonical_input):
    inp = _set_chains(canonical_input, a=True)
    res = run_engine(inp)
    panel = inp["panel_de_control"]
    for m in res.pyg_por_mes:
        assert m.ingreso_bruto_b == 0
        assert m.ingreso_bruto_c == 0
        if _check_ratio(m, panel, "a", panel["margen"]):
            return
    raise AssertionError("A: no month with cost_a > 0")


def test_solo_b(run_engine, canonical_input):
    inp = _set_chains(canonical_input, b=True)
    res = run_engine(inp)
    panel = inp["panel_de_control"]
    for m in res.pyg_por_mes:
        assert m.ingreso_bruto_a == 0, f"A debe ser 0 cuando cadena_a=False mes={m.mes}"
        if _check_ratio(m, panel, "b", panel["margen_b"]):
            return
    raise AssertionError("B: no month with cost_b > 0")


def test_a_plus_b(run_engine, canonical_input):
    inp = _set_chains(canonical_input, a=True, b=True)
    res = run_engine(inp)
    panel = inp["panel_de_control"]
    a_checked = b_checked = False
    for m in res.pyg_por_mes:
        if not a_checked and _check_ratio(m, panel, "a", panel["margen"]):
            a_checked = True
        if not b_checked and _check_ratio(m, panel, "b", panel["margen_b"]):
            b_checked = True
        if a_checked and b_checked:
            return
    raise AssertionError(f"A+B: a_checked={a_checked} b_checked={b_checked}")


def test_chain_independence(run_engine, canonical_input):
    """Cambiar margen_b no afecta ingreso_a y viceversa."""
    inp1 = _set_chains(canonical_input, a=True, b=True)
    res1 = run_engine(inp1)
    inp2 = copy.deepcopy(inp1)
    inp2["panel_de_control"]["margen_b"] = 0.45  # mover solo margen_b
    res2 = run_engine(inp2)
    for m1, m2 in zip(res1.pyg_por_mes, res2.pyg_por_mes):
        # Cadena A invariante
        assert abs(m1.ingreso_bruto_a - m2.ingreso_bruto_a) < 1e-4, (
            f"mes={m1.mes} ingreso_a debería ser invariante: {m1.ingreso_bruto_a} vs {m2.ingreso_bruto_a}")
        # Cadena B distinto si hay ingreso
        if m1.costo_b > 0:
            assert abs(m1.ingreso_bruto_b - m2.ingreso_bruto_b) > 1e-2, (
                f"mes={m1.mes} ingreso_b debe haber cambiado al cambiar margen_b")
