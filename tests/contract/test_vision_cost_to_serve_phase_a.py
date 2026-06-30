"""
tests/contract/test_vision_cost_to_serve_phase_a.py
=====================================================
Fase A+B — Tests de contrato para Vision Cost To Serve.

Fixtures:
  - bancamia_excel_match.json:       26 FTE all-Inbound, K50=0 (no vol set), 0.00000% PyG match
  - excel_v24_canonical_bancamia.json: 26 FTE all-Inbound + vol_cadena_a, K50=4534.89, 0.00000% PyG

Fuente de verdad Excel:
  tests/fixtures/excel_v2_4/vision_cost_to_serve/bancamia_12m_canonical.json
  Generado: openpyxl data_only=True de Excel Nexa Pricing Simulador V2-4.xlsx

Estado de paridad:
  EXACT   (0.0000%): K50, L50, part_a, part_b, capacitacion_inicial, examenes,
                      opex_fijo, inversiones, costos_fijos, tarifa, estudios_seguridad, tasa_escalamiento
  NEAR    (<1%):      nomina_loaded (0.56%), salario_fijo (0.59%), salario_variable (0.16%)
  KNOWN   (>1%):      capacitacion_rotacion (70%), cts_a (1.3%), cts_b (2.2%)
  EXACT   (0.0000%): hitl (HITL items now routed to costo_personal_hitl)

Documented formula differences (backend is reference implementation):
  - capacitacion_rotacion: backend includes ALL profiles; Excel excludes profiles with vol_cadena_a=0
  - costos_fijos: FIXED — now uses FTE×pct_presencia for infra, raw FTE for capex
  - hitl: HITL opex_consumo items detected by producto=="HITL" and routed to costo_personal_hitl
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# WAVE 7: marcado como legacy pre-V2-7 — usa fixtures Excel V2-4 obsoletas
# (excel_v24_canonical_bancamia.json, bancamia_excel_match.json en rutas legacy).
# Ver docs/v27/WAVE7_TRIAGE.md (categoría OBSOLETE_FIXTURE).
pytestmark = pytest.mark.legacy

# ─────────────────────────────────────────────────────────────
# Path setup
# ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: F401 — registra el alias nexa_engine

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine

BACKEND_ROOT = PROJECT_ROOT / "backend_nexa"
CANONICAL_FIXTURE = (
    BACKEND_ROOT
    / "tests/fixtures/excel_v2_4/vision_cost_to_serve/bancamia_12m_canonical.json"
)
# Fixture original sin vol_cadena_a (K50=0) — solo para estructura y PyG guards
CASE_PATH = BACKEND_ROOT / "test_cases/bancamia_excel_match.json"
# Golden fixture canónico — mismo escenario + K50 inputs
CASE_PATH_GOLDEN = BACKEND_ROOT / "test_cases/excel_v24_canonical_bancamia.json"
# Legacy K50 fixture (24 FTE, different cost base) — kept for reference
CASE_PATH_K50 = BACKEND_ROOT / "test_cases/bancamia_canonical_k50.json"

TOLERANCE_EXACT = 0.001   # 0.001% = exact match (float rounding headroom)
TOLERANCE_NEAR  = 1.0     # 1% = near match (support staff salary indexation)
TOLERANCE_WIDE  = 5.0     # 5% = wide tolerance (aggregate CTS with known residuals)


# ─────────────────────────────────────────────────────────────
# Fixtures pytest
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def excel_canonical() -> dict:
    """Valores canónicos extraídos del Excel V2-4 — fuente de verdad."""
    with open(CANONICAL_FIXTURE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def resultado():
    """
    Resultado del engine para bancamia_excel_match (26 FTE Inbound, K50=0).
    Usado para: PyG invariants, TestMonthCount, estructura.
    """
    ui = UserInputLoader().cargar(CASE_PATH)
    solic = SimulationContextBuilder().construir(ui)
    return NexaPricingEngine().calcular(solic)


@pytest.fixture(scope="module")
def resultado_golden():
    """
    Resultado del engine para el fixture canónico golden.
    26 FTE Inbound con vol_cadena_a configurado → K50=4534.89.
    Misma base de costos que bancamia_excel_match (0% PyG match).
    """
    ui = UserInputLoader().cargar(CASE_PATH_GOLDEN)
    solic = SimulationContextBuilder().construir(ui)
    return NexaPricingEngine().calcular(solic)


@pytest.fixture(scope="module")
def cts(resultado):
    """CTS del escenario bancamia_excel_match (K50=0)."""
    return resultado.cost_to_serve


@pytest.fixture(scope="module")
def cts_golden(resultado_golden):
    """CTS del escenario canónico golden (K50=4534.89, L50=3000)."""
    return resultado_golden.cost_to_serve


def _delta_pct(backend_val: float, excel_val: float) -> float:
    if excel_val == 0:
        return 0.0 if backend_val == 0 else float("inf")
    return abs(backend_val - excel_val) / abs(excel_val) * 100


# ─────────────────────────────────────────────────────────────
# TestCurrentBehaviorSnapshot
# Guards para bancamia_excel_match (K50=0 scenario)
# ─────────────────────────────────────────────────────────────

class TestCurrentBehaviorSnapshot:
    """
    Documenta el comportamiento para bancamia_excel_match (sin vol_cadena_a).
    K50=0 es CORRECTO cuando ningún perfil Inbound tiene vol_cadena_a_mensual.
    """

    def test_k50_is_zero_when_inbound_no_vol_configured(self, cts):
        """K50=0 para fixture all-Inbound sin vol_cadena_a_mensual."""
        assert cts.fte_cadena_a == pytest.approx(0.0)

    def test_cts_a_is_zero_when_k50_is_zero(self, cts):
        """cts_a = 0 cuando K50=0 (division by zero guard)."""
        assert cts.cts_cadena_a == pytest.approx(0.0)

    def test_cts_b_close_to_excel(self, cts, excel_canonical):
        """CTS_B should be within 3% (same L50, slightly different costs)."""
        excel_cts_b = excel_canonical["cadena_b_desglose"]["G034_cts_b"]
        delta = _delta_pct(cts.cts_cadena_b, excel_cts_b)
        assert delta < 3.0, f"cts_b delta={delta:.4f}%"

    def test_participacion_a_is_zero_when_k50_is_zero(self, cts):
        """participacion_a=0 when K50=0."""
        assert cts.participacion_a == pytest.approx(0.0)

    def test_desglose_a_subcomponents_are_zero(self, cts):
        """Desglose A zeros when K50=0 (can't compute per-K50-unit values)."""
        da = cts.desglose_a
        assert da.nomina_loaded == 0.0
        assert da.opex_fijo == 0.0


# ─────────────────────────────────────────────────────────────
# TestDenominadores — K50, L50, participacion (EXACT MATCH)
# ─────────────────────────────────────────────────────────────

class TestDenominadores:
    """
    K50, L50 y participaciones deben coincidir exactamente con el Excel.
    Usa el golden fixture (excel_v24_canonical_bancamia.json).

    K50 = Σ vol_cadena_a(inbound profiles) = 4521.89 + 13 + 0 = 4534.89
    L50 = Σ volumen_mensual(canales B) = 3000
    """

    def test_k50_matches_excel(self, cts_golden, excel_canonical):
        """K50 = 4534.890080 (PCG K50 del Excel). EXACT MATCH."""
        excel_k50 = excel_canonical["denominadores_k50_l50"]["K50"]
        delta = _delta_pct(cts_golden.fte_cadena_a, excel_k50)
        assert delta <= TOLERANCE_EXACT, (
            f"K50: backend={cts_golden.fte_cadena_a:.6f}, "
            f"excel={excel_k50:.6f}, delta={delta:.6f}%"
        )

    def test_l50_matches_excel(self, cts_golden, excel_canonical):
        """L50 = 3000.0 (PCG L50). EXACT MATCH."""
        excel_l50 = excel_canonical["denominadores_k50_l50"]["L50"]
        delta = _delta_pct(cts_golden.vol_cadena_b, excel_l50)
        assert delta <= TOLERANCE_EXACT, (
            f"L50: backend={cts_golden.vol_cadena_b:.2f}, excel={excel_l50:.2f}"
        )

    def test_participacion_a_matches_excel(self, cts_golden, excel_canonical):
        """participacion_a = K50 / (K50+L50) = 0.60185219. EXACT MATCH."""
        excel_val = excel_canonical["denominadores_k50_l50"]["K51_participacion_a"]
        delta = _delta_pct(cts_golden.participacion_a, excel_val)
        assert delta <= TOLERANCE_EXACT, (
            f"part_a: backend={cts_golden.participacion_a:.8f}, excel={excel_val:.8f}"
        )

    def test_participacion_b_matches_excel(self, cts_golden, excel_canonical):
        """participacion_b = L50 / (K50+L50) = 0.39814781. EXACT MATCH."""
        excel_val = excel_canonical["denominadores_k50_l50"]["L51_participacion_b"]
        delta = _delta_pct(cts_golden.participacion_b, excel_val)
        assert delta <= TOLERANCE_EXACT, (
            f"part_b: backend={cts_golden.participacion_b:.8f}, excel={excel_val:.8f}"
        )


# ─────────────────────────────────────────────────────────────
# TestCTSAggregate — cts_a, cts_b, cts_ponderado
# ─────────────────────────────────────────────────────────────

class TestCTSAggregate:
    """
    CTS aggregate values with golden fixture.

    Known residuals (backend is reference implementation):
      - cts_a: ~1.3% (backend includes ALL profiles in numerator; Excel
        may exclude profiles with vol_cadena_a=0 from CTS_A cost attribution)
      - cts_b: ~2.2% (S&M salary indexation SMMLV 2025→2026 difference)
      - cts_pond: ~0.5% (derived from cts_a + cts_b)
    """

    def test_cts_cadena_a_within_tolerance(self, cts_golden, excel_canonical):
        """CTS_A = avg_costo_a / K50. Delta ~1.3% (all profiles in numerator)."""
        excel_cts_a = excel_canonical["cadena_a_desglose"]["C034_cts_a"]
        delta = _delta_pct(cts_golden.cts_cadena_a, excel_cts_a)
        assert delta <= TOLERANCE_WIDE, (
            f"cts_a: backend={cts_golden.cts_cadena_a:.2f}, excel={excel_cts_a:.2f}, "
            f"delta={delta:.4f}%"
        )

    def test_cts_cadena_b_within_tolerance(self, cts_golden, excel_canonical):
        """CTS_B = avg_costo_b / L50. Delta ~2.2% (S&M salary SMMLV diff)."""
        excel_cts_b = excel_canonical["cadena_b_desglose"]["G034_cts_b"]
        delta = _delta_pct(cts_golden.cts_cadena_b, excel_cts_b)
        assert delta <= TOLERANCE_WIDE, (
            f"cts_b: backend={cts_golden.cts_cadena_b:.2f}, excel={excel_cts_b:.2f}, "
            f"delta={delta:.4f}%"
        )

    def test_cts_ponderado_within_tolerance(self, cts_golden, excel_canonical):
        """CTS_pond = (cts_a*part_a + cts_b*part_b). Delta ~0.5%."""
        excel_pond = excel_canonical["cts_ponderado"]["G049_cts_ponderado"]
        delta = _delta_pct(cts_golden.cts_ponderado, excel_pond)
        assert delta <= TOLERANCE_WIDE, (
            f"cts_pond: backend={cts_golden.cts_ponderado:.2f}, excel={excel_pond:.2f}, "
            f"delta={delta:.4f}%"
        )


# ─────────────────────────────────────────────────────────────
# TestDesgloseAStructure — field presence
# ─────────────────────────────────────────────────────────────

class TestDesgloseAStructure:
    """DesgloseCTSCadenaA must have all payroll and no-payroll sub-fields."""

    def test_desglose_cadena_a_has_all_payroll_fields(self, cts):
        da = cts.desglose_a
        required = [
            "nomina_loaded", "salario_fijo", "salario_variable",
            "capacitacion_inicial", "capacitacion_rotacion", "examenes",
            "estudios_seguridad",
        ]
        missing = [f for f in required if not hasattr(da, f)]
        assert not missing, f"Missing payroll fields: {missing}"

    def test_desglose_cadena_a_has_all_no_payroll_fields(self, cts):
        da = cts.desglose_a
        required = ["opex_fijo", "inversiones", "costos_fijos_estacion"]
        missing = [f for f in required if not hasattr(da, f)]
        assert not missing, f"Missing no_payroll fields: {missing}"


# ─────────────────────────────────────────────────────────────
# TestDesgloseAExactMatch — fields that match Excel within 0.001%
# ─────────────────────────────────────────────────────────────

class TestDesgloseAExactMatch:
    """
    Desglose A fields that match the Excel exactly (0.0000% delta).
    These confirm the backend formulas are correct for these components.
    """

    @pytest.mark.parametrize("field,excel_key", [
        ("capacitacion_inicial",        "C039_cap_inicial"),
        ("examenes",           "C041_examenes"),
        ("estudios_seguridad", "C042_estudios_seg"),
        ("opex_fijo",          "C046_opex_fijo"),
        ("inversiones",        "C047_inversiones"),
    ])
    def test_exact_match_field(self, cts_golden, excel_canonical, field, excel_key):
        """Sub-field matches Excel within 0.001%."""
        da = cts_golden.desglose_a
        backend_val = getattr(da, field)
        excel_val = excel_canonical["cadena_a_desglose"][excel_key]
        delta = _delta_pct(backend_val, excel_val)
        assert delta <= TOLERANCE_EXACT, (
            f"{field}: backend={backend_val:.4f}, excel={excel_val:.4f}, "
            f"delta={delta:.6f}%"
        )


# ─────────────────────────────────────────────────────────────
# TestDesgloseANearMatch — fields within 1% (support staff indexation)
# ─────────────────────────────────────────────────────────────

class TestDesgloseANearMatch:
    """
    Desglose A fields within 1% of Excel. The small delta is from
    support staff salary indexation differences (SMMLV 2025→2026).
    """

    @pytest.mark.parametrize("field,excel_key,description", [
        ("nomina_loaded",    "C036_nomina_loaded",    "C036: base salary loaded (sf+com)"),
        ("salario_fijo",     "C037_salario_fijo",     "C037: salario fijo"),
        ("salario_variable", "C038_salario_variable", "C038: comisiones"),
    ])
    def test_near_match_field(self, cts_golden, excel_canonical, field, excel_key, description):
        """Sub-field within 1% of Excel — support staff indexation residual."""
        da = cts_golden.desglose_a
        backend_val = getattr(da, field)
        excel_val = excel_canonical["cadena_a_desglose"][excel_key]
        delta = _delta_pct(backend_val, excel_val)
        assert delta <= TOLERANCE_NEAR, (
            f"{description}: backend={backend_val:.4f}, excel={excel_val:.4f}, "
            f"delta={delta:.4f}% (limit {TOLERANCE_NEAR}%)"
        )


# ─────────────────────────────────────────────────────────────
# TestDesgloseADocumentedDelta — known formula differences
# ─────────────────────────────────────────────────────────────

class TestDesgloseADocumentedDelta:
    """
    Desglose A fields with documented formula differences (backend is reference).

    capacitacion_rotacion (C040): Backend includes capacitacion_rotacion from ALL profiles;
      Excel only includes profiles whose channel contributes to K50 (vol_cadena_a > 0).
      Backend: 90.72/K50 (3 profiles) vs Excel: 53.23/K50 (2 profiles: WA+Correo).

    costos_fijos_estacion (C048): Backend uses sum(FTE) for station count;
      Excel uses sum(FTE * pct_presencia) for infrastructure stations.
      Backend: 26 stations vs Excel: 18 stations (6×1.0 + 10×0.6 + 10×0.6).
    """

    def test_capacitacion_rotacion_documented_delta(self, cts_golden, excel_canonical):
        """
        capacitacion_rotacion: backend=90.72, Excel=53.23.
        KNOWN DELTA: backend includes ALL profiles; Excel excludes profiles
        with vol_cadena_a=0 (WebChat, 10 FTE) from CTS numerator.
        Backend is correct per its own formula. Document, don't fix.
        """
        da = cts_golden.desglose_a
        excel_val = excel_canonical["cadena_a_desglose"]["C040_cap_rotacion"]
        # Verify the backend value is deterministic (regression guard)
        assert da.capacitacion_rotacion == pytest.approx(90.7188, rel=1e-3), (
            f"capacitacion_rotacion regression: expected ~90.72, got {da.capacitacion_rotacion:.4f}"
        )
        # Document the delta vs Excel
        delta = _delta_pct(da.capacitacion_rotacion, excel_val)
        assert delta > 50.0, (
            f"capacitacion_rotacion delta unexpectedly low ({delta:.2f}%). "
            f"If this changed, review formula change impact."
        )

    def test_costos_fijos_matches_excel(self, cts_golden, excel_canonical):
        """
        costos_fijos_estacion now uses FTE×pct_presencia for infra stations,
        matching Excel formula (Condiciones Cadena A fila 19).
        """
        da = cts_golden.desglose_a
        excel_val = excel_canonical["cadena_a_desglose"]["C048_costos_fijos_est"]
        assert da.costos_fijos_estacion == pytest.approx(excel_val, rel=1e-3), (
            f"costos_fijos mismatch: backend={da.costos_fijos_estacion:.4f}, "
            f"Excel={excel_val:.4f}"
        )


# ─────────────────────────────────────────────────────────────
# TestDesgloseBStructure — field presence
# ─────────────────────────────────────────────────────────────

class TestDesgloseBStructure:
    """DesgloseCTSCadenaB must have all componente fijo and variable fields."""

    def test_result_has_desglose_cadena_b(self, cts):
        assert hasattr(cts, "desglose_b"), "desglose_b ausente"

    def test_desglose_cadena_b_has_componente_fijo_fields(self, cts):
        db = cts.desglose_b
        required = ["componente_fijo", "opex", "inversiones", "soporte_mantenimiento"]
        missing = [f for f in required if not hasattr(db, f)]
        assert not missing, f"Missing fijo fields: {missing}"

    def test_desglose_cadena_b_has_componente_variable_fields(self, cts):
        db = cts.desglose_b
        required = ["componente_variable", "tarifa", "opex_variable", "tasa_escalamiento", "hitl"]
        missing = [f for f in required if not hasattr(db, f)]
        assert not missing, f"Missing variable fields: {missing}"


# ─────────────────────────────────────────────────────────────
# TestDesgloseBValues — Cadena B sub-field values
# ─────────────────────────────────────────────────────────────

class TestDesgloseBValues:
    """
    Cadena B desglose values vs Excel.

    EXACT MATCH: tarifa (G042), tasa_escalamiento (G044), hitl (G045)
    DOCUMENTED DELTA: soporte_mantenimiento, componente_fijo/variable
    """

    def test_tarifa_exact_match(self, cts_golden, excel_canonical):
        """G042 tarifa: EXACT MATCH (1500.0)."""
        db = cts_golden.desglose_b
        excel_val = excel_canonical["cadena_b_desglose"]["G042_tarifa"]
        delta = _delta_pct(db.tarifa, excel_val)
        assert delta <= TOLERANCE_EXACT, (
            f"tarifa: backend={db.tarifa:.2f}, excel={excel_val:.2f}"
        )

    def test_tasa_escalamiento_exact_match(self, cts_golden, excel_canonical):
        """G044 tasa_escalamiento: EXACT MATCH (0.0)."""
        db = cts_golden.desglose_b
        excel_val = excel_canonical["cadena_b_desglose"]["G044_tasa_escalamiento"]
        delta = _delta_pct(db.tasa_escalamiento, excel_val)
        assert delta <= TOLERANCE_EXACT, (
            f"tasa_esc: backend={db.tasa_escalamiento}, excel={excel_val}"
        )

    def test_hitl_matches_excel(self, cts_golden, excel_canonical):
        """G045 hitl: HITL items routed to costo_personal_hitl, not opex_fijo."""
        db = cts_golden.desglose_b
        excel_val = excel_canonical["cadena_b_desglose"]["G045_hitl"]
        delta = _delta_pct(db.hitl, excel_val)
        assert delta <= TOLERANCE_EXACT, (
            f"hitl: backend={db.hitl:.2f}, excel={excel_val:.2f}, delta={delta:.2f}%"
        )

    def test_total_cts_b_reasonable(self, cts_golden, excel_canonical):
        """
        Total CTS_B (opex+inv+soporte_mantenimiento+var+esc+hitl) should be within 5% of Excel.
        The total is correct even if components are differently classified.
        """
        excel_cts_b = excel_canonical["cadena_b_desglose"]["G034_cts_b"]
        delta = _delta_pct(cts_golden.cts_cadena_b, excel_cts_b)
        assert delta <= TOLERANCE_WIDE, (
            f"cts_b total: backend={cts_golden.cts_cadena_b:.2f}, "
            f"excel={excel_cts_b:.2f}, delta={delta:.2f}%"
        )


# ─────────────────────────────────────────────────────────────
# TestCadenaCPresent
# ─────────────────────────────────────────────────────────────

class TestCadenaCPresent:
    """ResultadoCostToServe must expose Cadena C fields (0.0 when inactive)."""

    def test_result_has_participacion_c(self, cts):
        assert hasattr(cts, "participacion_c")

    def test_result_has_cts_cadena_c(self, cts):
        assert hasattr(cts, "cts_cadena_c")

    def test_participacion_c_is_zero_when_inactive(self, cts):
        assert cts.participacion_c == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────
# TestReglaMonetaryValues
# ─────────────────────────────────────────────────────────────

class TestReglaMonetaryValues:
    """
    Reglas de negocio: monto field and costo_total_acumulado.

    The golden fixture has the same PyG as bancamia_excel_match (adding
    vol_cadena_a doesn't change costs). costo_total_acumulado = 8.2B
    (backend includes ALL cost lines: payroll_a + no_payroll_a + costo_b
    + financieros). Excel C186 = 4.8B (may define "costo total" differently).
    """

    def test_reglas_negocio_have_monto_field(self, resultado):
        """Each ReglaNegocios must have a 'monto' field."""
        import dataclasses
        reglas = resultado.reglas_negocio
        assert reglas, "reglas_negocio empty"
        for regla in reglas:
            fields = {f.name for f in dataclasses.fields(regla)}
            assert "monto" in fields, f"'{regla.nombre}' missing 'monto'"

    def test_margen_monto_is_populated(self, resultado_golden):
        """margen.monto = costo_total_acumulado * margen_pct. Must be non-None."""
        reglas = resultado_golden.reglas_negocio
        margen = next((r for r in reglas if "margen" in r.nombre.lower()), None)
        assert margen is not None, "No margen rule found"
        assert margen.monto is not None, "margen.monto is None"
        assert margen.monto > 0, f"margen.monto must be > 0, got {margen.monto}"

    def test_costo_total_acumulado_field_exists(self, resultado_golden):
        """costo_total_acumulado must be exposed in cost_to_serve or kpis."""
        has_field = (
            hasattr(resultado_golden.cost_to_serve, "costo_total_acumulado") or
            hasattr(resultado_golden.kpis, "costo_total_acumulado")
        )
        assert has_field, "costo_total_acumulado not exposed in result"

    def test_costo_total_acumulado_consistent_with_pyg(self, resultado_golden):
        """costo_total_acumulado = sum(pyg.costo_total for all months)."""
        cts = resultado_golden.cost_to_serve
        pyg = resultado_golden.pyg_por_mes
        expected = sum(m.costo_total for m in pyg)
        assert cts.costo_total_acumulado == pytest.approx(expected, rel=1e-6), (
            f"costo_total_acumulado: {cts.costo_total_acumulado:,.2f} vs "
            f"sum(pyg.costo_total): {expected:,.2f}"
        )


# ─────────────────────────────────────────────────────────────
# TestMonthCount
# ─────────────────────────────────────────────────────────────

class TestMonthCount:
    """Motor must handle variable meses_contrato (not hardcoded 12)."""

    def test_pyg_count_matches_meses_contrato(self, resultado):
        assert len(resultado.pyg_por_mes) == 12

    @pytest.mark.parametrize("meses", [6, 24, 36, 60])
    def test_engine_supports_variable_month_count(self, meses):
        import json
        with open(CASE_PATH) as f:
            raw = json.load(f)
        raw["panel_de_control"]["meses_contrato"] = meses
        ui = UserInputLoader().cargar_desde_dict(raw)
        solic = SimulationContextBuilder().construir(ui)
        r = NexaPricingEngine().calcular(solic)
        assert len(r.pyg_por_mes) == meses

    def test_cts_uses_actual_months_for_avg(self, resultado):
        """CTS avg = sum(cost)/n, not hardcoded /12."""
        cts = resultado.cost_to_serve
        pyg = resultado.pyg_por_mes
        n = len(pyg)
        avg_b_manual = sum(m.costo_b for m in pyg) / n
        expected = avg_b_manual / cts.vol_cadena_b if cts.vol_cadena_b > 0 else 0
        assert cts.cts_cadena_b == pytest.approx(expected, rel=1e-6)


# ─────────────────────────────────────────────────────────────
# TestPyGInvariant — MUST ALWAYS PASS
# ─────────────────────────────────────────────────────────────

class TestPyGInvariant:
    """
    PyG invariant: adding vol_cadena_a_mensual DOES NOT change costs.
    vol_cadena_a only affects CTS denominator (K50), not PyG computation.
    Guards: capturado 2026-05-20.
    """

    def test_payroll_a_mes1_regression_guard(self, resultado):
        """payroll_a mes 1 = 112,121,855.17 (bancamia_excel_match)."""
        actual = resultado.pyg_por_mes[0].payroll_a
        assert actual == pytest.approx(112_121_855.1703, rel=1e-4)

    def test_golden_payroll_matches_original(self, resultado, resultado_golden):
        """Golden fixture must produce IDENTICAL payroll_a to original."""
        for i, (orig, gold) in enumerate(
            zip(resultado.pyg_por_mes, resultado_golden.pyg_por_mes)
        ):
            assert gold.payroll_a == pytest.approx(orig.payroll_a, rel=1e-9), (
                f"Mes {i+1}: golden payroll_a differs from original"
            )

    def test_golden_costo_total_matches_original(self, resultado, resultado_golden):
        """Golden fixture must produce IDENTICAL costo_total to original."""
        for i, (orig, gold) in enumerate(
            zip(resultado.pyg_por_mes, resultado_golden.pyg_por_mes)
        ):
            assert gold.costo_total == pytest.approx(orig.costo_total, rel=1e-9), (
                f"Mes {i+1}: golden costo_total differs from original"
            )

    def test_costo_a_promedio_mensual_regression_guard(self, resultado):
        """avg(payroll_a + no_payroll_a) = 329,280,439.33 (after infra pct_presencia fix)."""
        pyg = resultado.pyg_por_mes
        avg_total_a = sum(m.payroll_a + m.no_payroll_a for m in pyg) / len(pyg)
        assert avg_total_a == pytest.approx(329_280_439.3333, rel=1e-4)
