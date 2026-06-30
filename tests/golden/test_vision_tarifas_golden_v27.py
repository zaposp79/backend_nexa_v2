"""
tests/golden/test_vision_tarifas_golden_v27.py
===============================================
Phase 1 — Golden tests for VisionTarifas before any refactor.

PURPOSE:
  Capture the current (pre-refactor) numerical output of VisionTarifasCalculator.
  If any refactor causes these values to change, these tests will fail and alert
  the engineer before merging.

WHAT IS PROTECTED:
  - tarifa_fijo_fte per canal (derived from NominaCalculator + NoPayrollCalculator
    internal recalculation filtered by canal)
  - tarifa_variable per canal (derived from vol_mensual and ingreso_variable)
  - ingreso_bruto per canal (costo_atribuible / factor_billing)
  - costo_atribuible per canal (costo_a_ch + financieros + cadena_b_atribuible)
  - payroll_ch per canal (result of NominaCalculator for filtered perfiles)
  - no_payroll_ch per canal (result of NoPayrollCalculator for filtered perfiles)
  - ingreso_mensual total (sum of channel ingresos / composed total)
  - costo_total (sum cadena_a + cadena_b + cadena_c)

CASES:
  Case A: cobranzas_outbound_fte — single canal, outbound FTE model
  Case B: excel_v2_7_real_request — two canales (Inbound Voz + Inbound WhatsApp)

TOLERANCE: rel=1e-5 (10 ppm — tighter than parity tests, appropriate for golden lock)

REFACTORING RULE:
  After any refactor, the golden output MUST be identical within tolerance.
  If these tests fail, either:
    (a) The refactor introduced a numerical regression — must fix.
    (b) A parametrization change legitimately altered costs — must regenerate fixtures
        by running: venv/bin/python scripts/golden/regenerate_golden.py (TBD Fase 2+)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_FIXTURES = Path(__file__).resolve().parent / "fixtures"
CASES_ROOT = BACKEND_ROOT / "storage" / "baselines" / "v2-7-certified" / "cases"
PARITY_FIXTURES = BACKEND_ROOT / "tests" / "parity" / "fixtures"

if str(BACKEND_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT.parent))

import backend_nexa  # noqa: F401

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine

REL = 1e-5  # 10 ppm — golden lock tolerance


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def golden_cobranzas() -> dict:
    with open(GOLDEN_FIXTURES / "vt_cobranzas_outbound_fte.json", encoding="utf-8") as f:
        return json.load(f)["data"]


@pytest.fixture(scope="module")
def golden_v27() -> dict:
    with open(GOLDEN_FIXTURES / "vt_v27_real_request.json", encoding="utf-8") as f:
        return json.load(f)["data"]


@pytest.fixture(scope="module")
def resultado_cobranzas():
    req = CASES_ROOT / "cobranzas_outbound_fte" / "request.json"
    ui = UserInputLoader().cargar(req)
    ctx = SimulationContextBuilder().construir(ui)
    return NexaPricingEngine().calcular(ctx)


@pytest.fixture(scope="module")
def resultado_v27():
    req = PARITY_FIXTURES / "excel_v2_7_real_request.json"
    ui = UserInputLoader().cargar(req)
    ctx = SimulationContextBuilder().construir(ui)
    return NexaPricingEngine().calcular(ctx)


# ─────────────────────────────────────────────────────────────────────────────
# Case A — cobranzas_outbound_fte (single canal, pure FTE model)
# ─────────────────────────────────────────────────────────────────────────────

class TestVisionTarifasGoldenCobranzas:
    """
    Golden lock for VisionTarifas with a single Outbound FTE canal.

    Protected values are produced by:
      - NominaCalculator.calcular(perfiles_filtrados_por_canal, mes)
      - NoPayrollCalculator.calcular(perfiles_filtrados_por_canal, mes)
    These are the recalculations that will be moved to calculators/aggregations/
    in a later phase. These tests ensure the move produces identical numbers.
    """

    def test_canal_count(self, resultado_cobranzas):
        assert len(resultado_cobranzas.vision_tarifas.canales) == 1

    def test_tarifa_fijo_fte(self, resultado_cobranzas, golden_cobranzas):
        golden_canal = golden_cobranzas["canales"][0]
        live_canal = resultado_cobranzas.vision_tarifas.canales[0]
        assert live_canal.tarifa_fijo_fte == pytest.approx(
            golden_canal["tarifa_fijo_fte"], rel=REL
        ), f"tarifa_fijo_fte regression: live={live_canal.tarifa_fijo_fte}, golden={golden_canal['tarifa_fijo_fte']}"

    def test_tarifa_variable(self, resultado_cobranzas, golden_cobranzas):
        golden_canal = golden_cobranzas["canales"][0]
        live_canal = resultado_cobranzas.vision_tarifas.canales[0]
        assert live_canal.tarifa_variable == pytest.approx(
            golden_canal["tarifa_variable"], rel=REL, abs=1.0
        )

    def test_ingreso_bruto(self, resultado_cobranzas, golden_cobranzas):
        golden_canal = golden_cobranzas["canales"][0]
        live_canal = resultado_cobranzas.vision_tarifas.canales[0]
        assert live_canal.ingreso_bruto == pytest.approx(
            golden_canal["ingreso_bruto"], rel=REL
        ), f"ingreso_bruto regression: {live_canal.ingreso_bruto}"

    def test_costo_atribuible(self, resultado_cobranzas, golden_cobranzas):
        golden_canal = golden_cobranzas["canales"][0]
        live_canal = resultado_cobranzas.vision_tarifas.canales[0]
        assert live_canal.costo_atribuible == pytest.approx(
            golden_canal["costo_atribuible"], rel=REL
        )

    def test_payroll_ch(self, resultado_cobranzas, golden_cobranzas):
        """Protected: produced by NominaCalculator filtered per canal."""
        golden_canal = golden_cobranzas["canales"][0]
        live_canal = resultado_cobranzas.vision_tarifas.canales[0]
        assert live_canal.payroll_ch == pytest.approx(
            golden_canal["payroll_ch"], rel=REL
        ), f"payroll_ch regression (NominaCalculator per canal): {live_canal.payroll_ch}"

    def test_no_payroll_ch(self, resultado_cobranzas, golden_cobranzas):
        """Protected: produced by NoPayrollCalculator filtered per canal."""
        golden_canal = golden_cobranzas["canales"][0]
        live_canal = resultado_cobranzas.vision_tarifas.canales[0]
        assert live_canal.no_payroll_ch == pytest.approx(
            golden_canal["no_payroll_ch"], rel=REL
        ), f"no_payroll_ch regression (NoPayrollCalculator per canal): {live_canal.no_payroll_ch}"

    def test_nomina_agente_basico(self, resultado_cobranzas, golden_cobranzas):
        golden_canal = golden_cobranzas["canales"][0]
        live_canal = resultado_cobranzas.vision_tarifas.canales[0]
        assert live_canal.nomina_agente_basico == pytest.approx(
            golden_canal["nomina_agente_basico"], rel=REL
        )

    def test_ingreso_mensual_total(self, resultado_cobranzas, golden_cobranzas):
        assert resultado_cobranzas.vision_tarifas.ingreso_mensual == pytest.approx(
            golden_cobranzas["ingreso_mensual"], rel=REL
        )

    def test_costo_cadena_a_total(self, resultado_cobranzas, golden_cobranzas):
        assert resultado_cobranzas.vision_tarifas.costo_cadena_a_total == pytest.approx(
            golden_cobranzas["costo_cadena_a_total"], rel=REL
        )

    def test_costo_total(self, resultado_cobranzas, golden_cobranzas):
        assert resultado_cobranzas.vision_tarifas.costo_total == pytest.approx(
            golden_cobranzas["costo_total"], rel=REL
        )

    def test_payroll_plus_no_payroll_equals_costo_a_ch(self, resultado_cobranzas):
        """Internal consistency: costo_a = payroll + no_payroll."""
        c = resultado_cobranzas.vision_tarifas.canales[0]
        assert c.costo_cadena_a_ch == pytest.approx(c.payroll_ch + c.no_payroll_ch, rel=1e-9)


# ─────────────────────────────────────────────────────────────────────────────
# Case B — excel_v2_7_real_request (two canales: Inbound Voz + Inbound WhatsApp)
# ─────────────────────────────────────────────────────────────────────────────

class TestVisionTarifasGoldenV27TwoChannels:
    """
    Golden lock for VisionTarifas with two inbound canales.

    This case is critical because VisionTarifas recalculates Nomina + NoPayroll
    independently for EACH canal by filtering PerfilCadenaA by canal name.
    If the filtering logic changes, both per-canal values must stay identical.
    """

    def test_canal_count(self, resultado_v27):
        assert len(resultado_v27.vision_tarifas.canales) == 2

    def test_canal_names_present(self, resultado_v27):
        names = {c.nombre_canal for c in resultado_v27.vision_tarifas.canales}
        assert "Inbound 25" in names
        assert "inboun Whatsapp" in names

    @pytest.mark.parametrize("canal_name,field", [
        ("Inbound 25",     "tarifa_fijo_fte"),
        ("Inbound 25",     "ingreso_bruto"),
        ("Inbound 25",     "costo_atribuible"),
        ("Inbound 25",     "payroll_ch"),
        ("Inbound 25",     "no_payroll_ch"),
        ("inboun Whatsapp", "tarifa_fijo_fte"),
        ("inboun Whatsapp", "ingreso_bruto"),
        ("inboun Whatsapp", "costo_atribuible"),
        ("inboun Whatsapp", "payroll_ch"),
        ("inboun Whatsapp", "no_payroll_ch"),
    ])
    def test_per_canal_field(self, resultado_v27, golden_v27, canal_name, field):
        """Per-canal golden value lock — protected from refactor regressions."""
        golden_canal = next(
            c for c in golden_v27["canales"] if c["nombre_canal"] == canal_name
        )
        live_canal = next(
            c for c in resultado_v27.vision_tarifas.canales if c.nombre_canal == canal_name
        )
        live_val = getattr(live_canal, field)
        golden_val = golden_canal[field]
        assert live_val == pytest.approx(golden_val, rel=REL, abs=1.0), (
            f"{canal_name}.{field}: live={live_val}, golden={golden_val}"
        )

    def test_ingreso_mensual_total(self, resultado_v27, golden_v27):
        assert resultado_v27.vision_tarifas.ingreso_mensual == pytest.approx(
            golden_v27["ingreso_mensual"], rel=REL
        )

    def test_costo_cadena_a_total(self, resultado_v27, golden_v27):
        assert resultado_v27.vision_tarifas.costo_cadena_a_total == pytest.approx(
            golden_v27["costo_cadena_a_total"], rel=REL
        )

    def test_payroll_plus_no_payroll_per_canal(self, resultado_v27):
        """Internal consistency for each canal: costo_a_ch = payroll_ch + no_payroll_ch."""
        for c in resultado_v27.vision_tarifas.canales:
            assert c.costo_cadena_a_ch == pytest.approx(
                c.payroll_ch + c.no_payroll_ch, rel=1e-9
            ), f"{c.nombre_canal}: costo_a_ch != payroll + no_payroll"

    def test_costo_atribuible_decomposition(self, resultado_v27):
        """costo_atribuible = costo_a_ch + financieros + cadena_b_atribuible."""
        for c in resultado_v27.vision_tarifas.canales:
            expected = c.costo_cadena_a_ch + c.financieros_atribuible + c.cadena_b_atribuible
            assert c.costo_atribuible == pytest.approx(expected, rel=1e-9), (
                f"{c.nombre_canal}: costo_atribuible decomposition mismatch"
            )
