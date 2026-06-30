"""
tests/golden/test_cost_to_serve_golden_v27.py
==============================================
Phase 1 — Golden tests for CostToServe before any refactor.

PURPOSE:
  Capture the current (pre-refactor) numerical output of CostToServeCalculator.
  Any refactor that moves per-canal cost computation out of CostToServeCalculator
  and into calculators/aggregations/ must produce identical values.

WHAT IS PROTECTED:
  - cts_cadena_a (avg_costo_a / fte_cadena_a or vol_inbound)
  - cts_cadena_b (avg_costo_b / vol_cadena_b)
  - cts_ponderado (weighted average)
  - fte_cadena_a, vol_cadena_b denominators
  - participacion_a, participacion_b, participacion_c
  - desglose_a sub-fields (nomina_loaded, costos_fijos_estacion, opex_fijo, inversiones)
    — these are produced by NominaCalculator + NoPayrollCalculator recalculation
  - canal_view canales_detalle per-canal CTS (Inbound Voz, Inbound WhatsApp)
    — per-canal breakdown requires re-slicing by canal

CASES:
  Case A: cobranzas_outbound_fte — single canal, cts_cadena_a non-zero
  Case B: excel_v2_7_real_request — two canales with canal_view per-canal detail

TOLERANCE: rel=1e-5 (10 ppm — golden lock)

REFACTORING RULE:
  If any of these values change after a refactor, investigate before merging.
  Legitimate causes: parametrization update (regenerate fixtures).
  Illegitimate causes: formula moved incorrectly (must fix).
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

REL = 1e-5  # 10 ppm


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def golden_cobranzas() -> dict:
    with open(GOLDEN_FIXTURES / "cts_cobranzas_outbound_fte.json", encoding="utf-8") as f:
        return json.load(f)["data"]


@pytest.fixture(scope="module")
def golden_v27() -> dict:
    with open(GOLDEN_FIXTURES / "cts_v27_real_request.json", encoding="utf-8") as f:
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
# Case A — cobranzas_outbound_fte (non-zero cts_cadena_a)
# ─────────────────────────────────────────────────────────────────────────────

class TestCostToServeGoldenCobranzas:
    """
    Golden lock: CostToServe for a single Outbound FTE canal.
    cts_cadena_a is non-zero here (K50 = FTE_outbound = 10).

    desglose_a values are produced by NominaCalculator + NoPayrollCalculator
    averaged over all months and divided by fte_cadena_a. These are the
    internal recalculations targeted for refactoring in Phase 4+.
    """

    def test_cts_cadena_a(self, resultado_cobranzas, golden_cobranzas):
        """Protected: avg(costo_a_promedio) / fte_cadena_a."""
        live = resultado_cobranzas.cost_to_serve.cts_cadena_a
        golden = golden_cobranzas["cts_cadena_a"]
        assert live == pytest.approx(golden, rel=REL), (
            f"cts_cadena_a regression: live={live}, golden={golden}"
        )

    def test_cts_ponderado(self, resultado_cobranzas, golden_cobranzas):
        live = resultado_cobranzas.cost_to_serve.cts_ponderado
        golden = golden_cobranzas["cts_ponderado"]
        assert live == pytest.approx(golden, rel=REL)

    def test_fte_cadena_a(self, resultado_cobranzas, golden_cobranzas):
        assert resultado_cobranzas.cost_to_serve.fte_cadena_a == pytest.approx(
            golden_cobranzas["fte_cadena_a"], rel=REL
        )

    def test_participacion_a(self, resultado_cobranzas, golden_cobranzas):
        assert resultado_cobranzas.cost_to_serve.participacion_a == pytest.approx(
            golden_cobranzas["participacion_a"], rel=REL
        )

    def test_desglose_a_nomina_loaded(self, resultado_cobranzas, golden_cobranzas):
        """Protected: produced by NominaCalculator avg / K50."""
        live = resultado_cobranzas.cost_to_serve.desglose_a.nomina_loaded
        golden = golden_cobranzas["desglose_a"]["nomina_loaded"]
        assert live == pytest.approx(golden, rel=REL), (
            f"desglose_a.nomina_loaded regression (NominaCalculator/K50): live={live}, golden={golden}"
        )

    def test_desglose_a_costos_fijos_estacion(self, resultado_cobranzas, golden_cobranzas):
        """Protected: produced by NoPayrollCalculator avg / K50."""
        live = resultado_cobranzas.cost_to_serve.desglose_a.costos_fijos_estacion
        golden = golden_cobranzas["desglose_a"]["costos_fijos_estacion"]
        assert live == pytest.approx(golden, rel=REL), (
            f"desglose_a.costos_fijos_estacion regression (NoPayrollCalculator/K50): live={live}"
        )

    def test_desglose_a_salario_fijo(self, resultado_cobranzas, golden_cobranzas):
        live = resultado_cobranzas.cost_to_serve.desglose_a.salario_fijo
        golden = golden_cobranzas["desglose_a"]["salario_fijo"]
        assert live == pytest.approx(golden, rel=REL)

    def test_costo_total_acumulado(self, resultado_cobranzas, golden_cobranzas):
        live = resultado_cobranzas.cost_to_serve.costo_total_acumulado
        golden = golden_cobranzas["costo_total_acumulado"]
        assert live == pytest.approx(golden, rel=REL)

    def test_costo_total_acumulado_consistent_with_pyg(self, resultado_cobranzas):
        """Cross-check: sum(pyg.costo_total) == costo_total_acumulado."""
        pyg = resultado_cobranzas.pyg_por_mes
        expected = sum(m.costo_total for m in pyg)
        assert resultado_cobranzas.cost_to_serve.costo_total_acumulado == pytest.approx(
            expected, rel=1e-9
        )


# ─────────────────────────────────────────────────────────────────────────────
# Case B — excel_v2_7_real_request (two canales with per-canal CTS detail)
# ─────────────────────────────────────────────────────────────────────────────

class TestCostToServeGoldenV27Aggregate:
    """Golden lock for CostToServe aggregate values with 2-channel input."""

    def test_cts_cadena_a(self, resultado_v27, golden_v27):
        live = resultado_v27.cost_to_serve.cts_cadena_a
        golden = golden_v27["cts_cadena_a"]
        assert live == pytest.approx(golden, rel=REL)

    def test_cts_cadena_b(self, resultado_v27, golden_v27):
        live = resultado_v27.cost_to_serve.cts_cadena_b
        golden = golden_v27["cts_cadena_b"]
        assert live == pytest.approx(golden, rel=REL, abs=1e-6)

    def test_cts_ponderado(self, resultado_v27, golden_v27):
        live = resultado_v27.cost_to_serve.cts_ponderado
        golden = golden_v27["cts_ponderado"]
        assert live == pytest.approx(golden, rel=REL)

    def test_fte_cadena_a(self, resultado_v27, golden_v27):
        live = resultado_v27.cost_to_serve.fte_cadena_a
        golden = golden_v27["fte_cadena_a"]
        assert live == pytest.approx(golden, rel=REL)

    def test_participaciones(self, resultado_v27, golden_v27):
        cts = resultado_v27.cost_to_serve
        assert cts.participacion_a == pytest.approx(golden_v27["participacion_a"], rel=REL)
        assert cts.participacion_b == pytest.approx(golden_v27["participacion_b"], rel=REL)
        assert cts.participacion_c == pytest.approx(golden_v27["participacion_c"], rel=REL)

    def test_desglose_a_nomina_loaded(self, resultado_v27, golden_v27):
        """Protected: produced by NominaCalculator avg / K50 across all profiles."""
        live = resultado_v27.cost_to_serve.desglose_a.nomina_loaded
        golden = golden_v27["desglose_a"]["nomina_loaded"]
        assert live == pytest.approx(golden, rel=REL)

    def test_desglose_a_costos_fijos_estacion(self, resultado_v27, golden_v27):
        live = resultado_v27.cost_to_serve.desglose_a.costos_fijos_estacion
        golden = golden_v27["desglose_a"]["costos_fijos_estacion"]
        assert live == pytest.approx(golden, rel=REL)

    def test_desglose_a_opex_fijo(self, resultado_v27, golden_v27):
        live = resultado_v27.cost_to_serve.desglose_a.opex_fijo
        golden = golden_v27["desglose_a"]["opex_fijo"]
        assert live == pytest.approx(golden, rel=REL)


class TestCostToServeGoldenV27PerCanal:
    """
    Golden lock for per-canal CTS detail (canales_detalle).

    Protected fields produced by the internal per-canal recalculation in
    CostToServeCalculator (filters NominaCalculator + NoPayrollCalculator per canal).
    This is the second main target for Phase 4+ refactoring.
    """

    def test_canal_detalle_count(self, resultado_v27, golden_v27):
        """Two canales should produce two canal entries in canales_detalle."""
        live = resultado_v27.cost_to_serve.canales_detalle
        golden = golden_v27.get("canales_detalle", [])
        assert len(live) == len(golden) == 2

    @pytest.mark.parametrize("canal_name", ["Voz", "WhatsApp"])
    def test_per_canal_cts(self, resultado_v27, golden_v27, canal_name):
        """CTS per canal (cost / vol or cost / FTE for that canal)."""
        golden_canal = next(c for c in golden_v27["canales_detalle"] if c["canal"] == canal_name)
        live_canal = next(c for c in resultado_v27.cost_to_serve.canales_detalle if c.canal == canal_name)
        assert live_canal.cts == pytest.approx(golden_canal["cts"], rel=REL), (
            f"canal {canal_name}.cts regression: live={live_canal.cts}, golden={golden_canal['cts']}"
        )

    @pytest.mark.parametrize("canal_name,field", [
        ("Voz",      "payroll"),
        ("Voz",      "nomina_loaded"),
        ("Voz",      "no_payroll"),
        ("Voz",      "salario_fijo"),
        ("Voz",      "costos_fijos"),
        ("WhatsApp", "payroll"),
        ("WhatsApp", "nomina_loaded"),
        ("WhatsApp", "no_payroll"),
        ("WhatsApp", "salario_fijo"),
        ("WhatsApp", "costos_fijos"),
    ])
    def test_per_canal_payroll_breakdown(self, resultado_v27, golden_v27, canal_name, field):
        """
        Per-canal payroll/no-payroll breakdown fields.
        Protected: these come from NominaCalculator + NoPayrollCalculator
        filtered per canal — the core recalculation targeted for refactoring.
        """
        golden_canal = next(c for c in golden_v27["canales_detalle"] if c["canal"] == canal_name)
        live_canal = next(c for c in resultado_v27.cost_to_serve.canales_detalle if c.canal == canal_name)
        live_val = getattr(live_canal, field)
        golden_val = golden_canal[field]
        assert live_val == pytest.approx(golden_val, rel=REL, abs=1.0), (
            f"canal {canal_name}.{field}: live={live_val}, golden={golden_val}"
        )
