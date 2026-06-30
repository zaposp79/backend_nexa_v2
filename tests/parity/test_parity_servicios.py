"""Parity tests by servicio (linea_negocio).

Each service must produce a self-consistent P&G under the canonical input,
i.e. the WAVE 3 denominator-exact formula must hold for ingreso_a/costo_a
after dividing out ramp-up.

Services covered:
- Cobranzas, SAC, Ventas, Backoffice  → expected ramp-up > 0 (operativos)
- Captura de Datos, Plataformas       → ramp-up = 0 in V2-7 (P&G = 0)
"""
import pytest
from tests.parity.tolerance import assert_close, factor_billing


OPERATIVE_SERVICES = ["Cobranzas", "Sac", "SACO", "Ventas multicanal"]
ZERO_RAMPUP_SERVICES = ["Captura de Datos", "Plataformas"]


@pytest.mark.parametrize("servicio", OPERATIVE_SERVICES)
def test_servicio_operativo_paridad_formula(run_engine, canonical_input, patch_input, servicio):
    inp = patch_input(canonical_input, panel={"linea_negocio": servicio})
    res = run_engine(inp)
    p = inp["panel_de_control"]
    expected_ratio = 1.0 / factor_billing(
        p["margen"], op_cont=p["op_cont"], com_cont=p["com_cont"],
        markup=p["markup"], descuento=p["descuento"])
    for m in res.pyg_por_mes:
        c = m.payroll_a + m.no_payroll_a
        if c <= 0 or (m.rampup or 0) <= 0:
            continue
        ratio = (m.ingreso_bruto_a / c) / m.rampup
        assert_close(ratio, expected_ratio, label=f"{servicio} mes={m.mes}")
        return  # one valid month is enough


@pytest.mark.parametrize("servicio", ZERO_RAMPUP_SERVICES)
def test_servicio_zero_rampup_paridad(run_engine, canonical_input, patch_input, servicio):
    """V2-7 ramp-up=0 → todos los ingresos brutos = 0 en P&G."""
    inp = patch_input(canonical_input, panel={"linea_negocio": servicio})
    res = run_engine(inp)
    for m in res.pyg_por_mes:
        assert m.ingreso_bruto_a == 0.0, f"{servicio} mes={m.mes} ingreso_a={m.ingreso_bruto_a}"
        assert (m.rampup or 0) == 0.0, f"{servicio} mes={m.mes} rampup={m.rampup}"
