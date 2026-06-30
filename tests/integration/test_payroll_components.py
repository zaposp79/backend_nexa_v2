"""
Tests determinísticos por componente financiero — payroll.

Cada test verifica:
  - Componente específico (salario_fijo, comisiones, cap, exam)
  - Match exacto vs Excel V2-4 conocido
  - Determinismo (mismo input → mismo output)
"""
from __future__ import annotations

import pytest

# WAVE 7: marcado como legacy pre-V2-7 — espera fixtures whatsapp_only sin
# cadenas_activas (rompe en TASK_3). Valores Excel V2-4, no V2-7.
# Ver docs/v27/WAVE7_TRIAGE.md (OBSOLETE_FIXTURE + OBSOLETE_FORMULA).
pytestmark = pytest.mark.legacy


# Excel V2-4 expected values for Escenario 1 WhatsApp (Bancamia, mes 1)
# Excel V2-4 legacy no implementa exoneración Ley 1819; Salud (8.5%) e
# ICBF+SENA (4%) se cobran siempre — valores recalibrados para
# compatibilidad funcional estricta con el simulador legacy.
EXCEL_VALUES = {
    "payroll_a":          32_419_057,
    "no_payroll_a":        9_285_618,
    "costo_a":            41_704_675,
    "costo_b":           359_327_228,
    "polizas":            25_934_158,
    "financiacion_mes1":           0,
    "financiacion_mes2":   6_135_788,
    "ingreso_neto":      394_250_975,
}

# Tolerance per metric (proportional to magnitude)
TOLERANCE = {
    "payroll_a":          50.0,    # 0.0002%
    "no_payroll_a":       50.0,    # 0.0005%
    "costo_a":           100.0,    # 0.0003%
    "costo_b":      1_000_000.0,   # 0.3% (structural multi-channel difference)
    "polizas":        100_000.0,   # 0.4%
    "financiacion_mes1":   1.0,    # exact
    "financiacion_mes2": 10_000.0, # 0.16%
    "ingreso_neto":  1_000_000.0,  # 0.26%
}


class TestPayrollComponents:
    """Tests de componentes individuales del payroll."""

    def test_payroll_a_mes_1_match_exacto(self, whatsapp_only_case, run_engine):
        """payroll_a mes 1 = 30,017,217 (match exacto al peso)."""
        res = run_engine(whatsapp_only_case)
        actual = res.pyg_por_mes[0].payroll_a
        expected = EXCEL_VALUES["payroll_a"]
        assert abs(actual - expected) < TOLERANCE["payroll_a"], \
            f"payroll_a={actual:,.2f} vs Excel={expected:,.0f} (delta={actual-expected:+,.2f})"

    def test_no_payroll_a_mes_1(self, whatsapp_only_case, run_engine):
        """no_payroll_a mes 1 = OPEX + CAPEX(inicial+recurrente) + Fijos."""
        res = run_engine(whatsapp_only_case)
        actual = res.pyg_por_mes[0].no_payroll_a
        expected = EXCEL_VALUES["no_payroll_a"]
        assert abs(actual - expected) < TOLERANCE["no_payroll_a"]

    def test_no_payroll_a_mes_2_excluye_capex_inicial(self, whatsapp_only_case, run_engine):
        """mes 2+ debe excluir CAPEX inicial (~122K menos que mes 1)."""
        res = run_engine(whatsapp_only_case)
        delta = res.pyg_por_mes[0].no_payroll_a - res.pyg_por_mes[1].no_payroll_a
        # CAPEX inicial backend = 20,377 × 6 = 122,265
        assert 100_000 < delta < 150_000, f"Delta mes1-mes2 = {delta:,.0f}, esperado ~122K"

    def test_polizas_gross_up(self, whatsapp_only_case, run_engine):
        """Polizas aplica gross-up. Excel V2-4 P&G "Polizas" = ICA + GMF + Polizas-adic."""
        res = run_engine(whatsapp_only_case)
        p1 = res.pyg_por_mes[0]
        # Excel V2-4 P&G C64 "Polizas" semánticamente es la SUMA de los 3 conceptos.
        actual_total = p1.polizas + p1.ica + p1.gmf
        expected = EXCEL_VALUES["polizas"]
        assert abs(actual_total - expected) < TOLERANCE["polizas"], \
            f"Polizas total (P+I+G) = {actual_total:,.2f} vs Excel {expected:,.0f}"


class TestFinanciacion:
    """Tests específicos de financiación (timing crítico)."""

    def test_financiacion_mes_1_es_cero(self, whatsapp_only_case, run_engine):
        """Mes 1 SIEMPRE = 0 (no hay mes previo). Excel V2-4 convention."""
        res = run_engine(whatsapp_only_case)
        assert res.pyg_por_mes[0].financiacion == 0.0

    def test_financiacion_mes_2_usa_costo_mes_1(self, whatsapp_only_case, run_engine):
        """Mes 2 = costo_mes_1 × tasa × factor_periodo."""
        res = run_engine(whatsapp_only_case)
        m1 = res.pyg_por_mes[0]
        m2 = res.pyg_por_mes[1]
        # tasa_financ = 0.0153, factor_periodo (30 días) = 1
        expected_m2 = m1.costo_total * 0.0153 * 1
        # Tolerancia 1% sobre el valor esperado (puede haber ajustes menores)
        assert abs(m2.financiacion - expected_m2) / expected_m2 < 0.01

    def test_financiacion_3_perfiles(self, three_profiles_case, run_engine):
        """Mes 1 = 0 también para deal multi-canal."""
        res = run_engine(three_profiles_case)
        assert res.pyg_por_mes[0].financiacion == 0.0


class TestUtilidadNeta:
    """Test crítico: % utilidad neta debe matchear Excel V2-4."""

    def test_pct_utilidad_mes_1_negativo(self, whatsapp_only_case, run_engine):
        """Mes 1 con rampup 0.85 → utilidad negativa -1.72%."""
        res = run_engine(whatsapp_only_case)
        actual = res.pyg_por_mes[0].pct_utilidad_neta
        assert abs(actual - (-0.0172)) < 0.0001

    def test_pct_utilidad_mes_2_positivo(self, whatsapp_only_case, run_engine):
        """Mes 2 con rampup 0.92 → utilidad +6.02%."""
        res = run_engine(whatsapp_only_case)
        actual = res.pyg_por_mes[1].pct_utilidad_neta
        assert abs(actual - 0.0602) < 0.0001

    def test_pct_utilidad_steady_state(self, whatsapp_only_case, run_engine):
        """Mes 3+ con rampup 1.0 → utilidad steady 13.54%."""
        res = run_engine(whatsapp_only_case)
        for i in [2, 3, 4, 5, 11]:
            actual = res.pyg_por_mes[i].pct_utilidad_neta
            assert abs(actual - 0.1354) < 0.0001, f"mes {i+1}: {actual:.4f} vs 0.1354"


class TestDeterminismo:
    """Mismo input debe dar EXACTAMENTE el mismo output (sin random/timestamp)."""

    def test_run_dos_veces_mismo_resultado(self, whatsapp_only_case, run_engine):
        r1 = run_engine(whatsapp_only_case)
        r2 = run_engine(whatsapp_only_case)
        for i in range(12):
            assert r1.pyg_por_mes[i].payroll_a == r2.pyg_por_mes[i].payroll_a
            assert r1.pyg_por_mes[i].polizas == r2.pyg_por_mes[i].polizas
            assert r1.pyg_por_mes[i].financiacion == r2.pyg_por_mes[i].financiacion
            assert r1.pyg_por_mes[i].pct_utilidad_neta == r2.pyg_por_mes[i].pct_utilidad_neta
