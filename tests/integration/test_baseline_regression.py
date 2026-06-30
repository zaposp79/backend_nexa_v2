"""
Test de regresión contra baseline oficial.

Cualquier cambio que afecte outputs debe regenerar el baseline conscientemente:
    python scripts/generate_baseline.py
"""
from __future__ import annotations

import pytest

# WAVE 7: marcado como legacy pre-V2-7 — baseline antiguo (storage/baseline.json).
# Reemplazado por tests/baselines/test_v2_7_regression.py (12 casos certificados V2-7).
# Ver docs/v27/WAVE7_TRIAGE.md (OBSOLETE_FIXTURE).
pytestmark = pytest.mark.legacy


class TestBaselineRegression:
    """Verifica que el output actual matchea el baseline congelado."""

    def test_whatsapp_only_pyg_por_mes_match_baseline(
        self, whatsapp_only_case, run_engine, baseline_data
    ):
        scenario = baseline_data["scenarios"].get("bancamia_whatsapp_only")
        if scenario is None:
            pytest.skip("bancamia_whatsapp_only no está en baseline.")

        res = run_engine(whatsapp_only_case)
        baseline_pyg = scenario["pyg_por_mes"]
        for i, (actual, expected) in enumerate(zip(res.pyg_por_mes, baseline_pyg)):
            assert abs(actual.payroll_a - expected["payroll_a"]) < 1.0, \
                f"mes {i+1} payroll_a drift: {actual.payroll_a} vs baseline {expected['payroll_a']}"
            assert abs(actual.no_payroll_a - expected["no_payroll_a"]) < 1.0
            assert abs(actual.polizas - expected["polizas"]) < 1.0
            assert abs(actual.financiacion - expected["financiacion"]) < 1.0
            assert abs(actual.pct_utilidad_neta - expected["pct_utilidad_neta"]) < 1e-6

    def test_whatsapp_only_kpis_match_baseline(
        self, whatsapp_only_case, run_engine, baseline_data
    ):
        scenario = baseline_data["scenarios"].get("bancamia_whatsapp_only")
        if scenario is None:
            pytest.skip("baseline missing scenario")
        res = run_engine(whatsapp_only_case)
        bkpis = scenario["kpis"]
        assert abs(res.kpis.ingreso_mensual - bkpis["ingreso_mensual"]) < 1.0
        assert abs(res.kpis.utilidad_neta_total - bkpis["utilidad_neta_total"]) < 1.0
        assert res.kpis.cumple_margen_minimo == bkpis["cumple_margen_minimo"]
        assert abs(res.kpis.pct_utilidad_neta_total - bkpis["pct_utilidad_neta_total"]) < 1e-6

    def test_three_profiles_baseline_present(self, baseline_data):
        """Baseline debe incluir el escenario 3 perfiles para deteccion de regresión."""
        assert "bancamia_excel_match" in baseline_data["scenarios"]

    def test_three_profiles_pyg_match_baseline(
        self, three_profiles_case, run_engine, baseline_data
    ):
        scenario = baseline_data["scenarios"]["bancamia_excel_match"]
        res = run_engine(three_profiles_case)
        baseline_pyg = scenario["pyg_por_mes"]
        for i, (actual, expected) in enumerate(zip(res.pyg_por_mes, baseline_pyg)):
            # 3 perfiles tiene más complejidad - tolerancia mayor
            assert abs(actual.payroll_a - expected["payroll_a"]) < 100.0, \
                f"mes {i+1} 3perfiles payroll_a drift"
