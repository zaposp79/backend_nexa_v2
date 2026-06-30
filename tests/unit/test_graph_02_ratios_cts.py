"""
Unit tests for Graph 2 — Ratios Vision Cost To Serve (Steps 01 + 02).

Covers:
  - NominaCalculator.calcular_desglose_por_rol
  - Scenario label mapping
  - GraficoRatiosCTSResult construction (Block A: P4:AF29)
  - Block B ratios (AR4:BH29): denominator, per-scenario, total, ratio_actual
  - calcular_para_mes behavior preserved (non-regression)
  - Cargos Adicionales deferred

Excel V2-8 · Graficos!P4:AF29
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from nexa_engine.modules.calculator_motor.formulas.graphics.graph_02_ratios_cost_to_serve import (
    _compute_denominador,
    _compute_ratios_por_escenario,
    _compute_ratios_total,
    _escenario_label,
    _filter_perfiles_por_escenario,
    _safe_ratio,
    build_ratios_cost_to_serve,
)
from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
    GraficoRatiosCTSResult,
    GraficosResult,
)
from nexa_engine.modules.calculator_motor.formulas.payroll.nomina import NominaCalculator
from nexa_engine.modules.panel.models.panel import EscenarioComercial, PerfilCadenaA
from nexa_engine.modules.shared.models import ParametrosCalculo, ParametrosNomina


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_nomina(**overrides) -> ParametrosNomina:
    defaults = dict(
        mes_inicio=1,
        mes_fin=12,
        pct_aumento_salarial=0.10,
        mes_aplicacion_aumento=13,
        tarifa_dia_cap=100_000,
        costo_examen_medico=80_000,
        costo_estudio_seg=50_000,
        meses_contrato=12,
        factor_indexacion_base=1.0,
    )
    defaults.update(overrides)
    return ParametrosNomina(**defaults)


def _make_calculo(**overrides) -> ParametrosCalculo:
    defaults = dict(
        pct_rotacion=0.03,
        pct_examen_anual=0.1,
        pct_cumplimiento_variable=0.8,
    )
    defaults.update(overrides)
    return ParametrosCalculo(**defaults)


def _make_perfil(**overrides) -> PerfilCadenaA:
    defaults = dict(
        nombre="Supervisor",
        modalidad="Actual",
        canal="SAC",
        fte=5.0,
        salario_base=2_000_000,
        salario_cargado=3_200_000,
        comision_pct=0.0,
        dias_cap_inicial=0,
        dias_cap_rotacion=0,
        incluye_examenes=False,
        incluye_seguridad=False,
        fte_examenes=0.0,
        es_soporte=False,
    )
    defaults.update(overrides)
    return PerfilCadenaA(**defaults)


def _make_calc() -> NominaCalculator:
    return NominaCalculator(_make_nomina(), _make_calculo())


def _make_escenario(**overrides) -> EscenarioComercial:
    defaults = dict(escenario=1, modalidad="Actual", canal="SAC", modelo_cobro="Fijo")
    defaults.update(overrides)
    return EscenarioComercial(**defaults)


# ---------------------------------------------------------------------------
# Phase 2: calcular_desglose_por_rol
# ---------------------------------------------------------------------------

class TestCalcularDesglosePorRol:
    def test_returns_dict_keyed_by_nombre(self):
        calc = _make_calc()
        perfil = _make_perfil(nombre="Supervisor", fte=5.0, salario_cargado=3_200_000)
        result = calc.calcular_desglose_por_rol([perfil], mes=1)
        assert isinstance(result, dict)
        assert "Supervisor" in result

    def test_cost_matches_calcular_perfil(self):
        calc = _make_calc()
        perfil = _make_perfil(nombre="Agente Básico 1", fte=10.0, salario_cargado=2_500_000)
        desglose = calc.calcular_desglose_por_rol([perfil], mes=1)
        # Must equal _calcular_perfil.total
        expected = calc._calcular_perfil(perfil, mes=1).total
        assert desglose["Agente Básico 1"] == pytest.approx(expected, rel=1e-9)

    def test_multiple_profiles_each_keyed(self):
        calc = _make_calc()
        p1 = _make_perfil(nombre="Supervisor", fte=5.0)
        p2 = _make_perfil(nombre="Formadores", fte=2.0, salario_cargado=2_800_000)
        result = calc.calcular_desglose_por_rol([p1, p2], mes=1)
        assert "Supervisor" in result
        assert "Formadores" in result
        assert len(result) == 2

    def test_duplicate_nombres_are_summed(self):
        """Excel SUMIFS aggregates by role name — duplicates must sum."""
        calc = _make_calc()
        p1 = _make_perfil(nombre="Supervisor", fte=3.0, salario_cargado=3_000_000)
        p2 = _make_perfil(nombre="Supervisor", fte=2.0, salario_cargado=3_000_000, canal="WhatsApp")
        result = calc.calcular_desglose_por_rol([p1, p2], mes=1)
        expected_p1 = calc._calcular_perfil(p1, mes=1).total
        expected_p2 = calc._calcular_perfil(p2, mes=1).total
        assert result["Supervisor"] == pytest.approx(expected_p1 + expected_p2, rel=1e-9)

    def test_empty_perfiles_returns_empty_dict(self):
        calc = _make_calc()
        result = calc.calcular_desglose_por_rol([], mes=1)
        assert result == {}

    def test_does_not_change_calcular_para_mes(self):
        """calcular_para_mes must return the same result before and after desglose call."""
        calc = _make_calc()
        perfiles = [
            _make_perfil(nombre="Supervisor", fte=5.0),
            _make_perfil(nombre="Formadores", fte=2.0, salario_cargado=2_800_000),
        ]
        original = calc.calcular_para_mes(perfiles, mes=1)
        _ = calc.calcular_desglose_por_rol(perfiles, mes=1)
        after = calc.calcular_para_mes(perfiles, mes=1)
        assert original.total == pytest.approx(after.total, rel=1e-12)

    def test_total_matches_calcular_para_mes(self):
        """Sum of desglose values must equal calcular_para_mes.total."""
        calc = _make_calc()
        perfiles = [
            _make_perfil(nombre="Supervisor", fte=5.0),
            _make_perfil(nombre="Formadores", fte=2.0, salario_cargado=2_800_000),
        ]
        desglose = calc.calcular_desglose_por_rol(perfiles, mes=1)
        aggregate = calc.calcular_para_mes(perfiles, mes=1)
        assert sum(desglose.values()) == pytest.approx(aggregate.total, rel=1e-9)


# ---------------------------------------------------------------------------
# Scenario label mapping
# ---------------------------------------------------------------------------

class TestEscenarioLabel:
    def test_sac_actual(self):
        assert _escenario_label("SAC", "Actual") == "Escenario SAC Actual"

    def test_sac_actual_lowercase(self):
        assert _escenario_label("sac", "actual") == "Escenario SAC Actual"

    def test_whatsapp_actual(self):
        assert _escenario_label("WhatsApp", "Actual") == "Escenario WhatsApp Actual"

    def test_whatsapp_actual_lowercase(self):
        assert _escenario_label("whatsapp", "actual") == "Escenario WhatsApp Actual"

    def test_inhouse(self):
        assert _escenario_label("Inhouse", "") == "Crecimiento inhouse"

    def test_inhouse_lowercase(self):
        assert _escenario_label("inhouse", "") == "Crecimiento inhouse"

    def test_unknown_fallback(self):
        label = _escenario_label("NuevoCanal", "Inbound")
        assert "NuevoCanal" in label


# ---------------------------------------------------------------------------
# _filter_perfiles_por_escenario
# ---------------------------------------------------------------------------

class TestFilterPerfilesPorEscenario:
    def test_filters_by_canal_and_modalidad(self):
        p_sac = _make_perfil(canal="SAC", modalidad="Actual")
        p_wa = _make_perfil(canal="WhatsApp", modalidad="Actual")
        esc = _make_escenario(canal="SAC", modalidad="Actual")
        result = _filter_perfiles_por_escenario([p_sac, p_wa], esc)
        assert p_sac in result
        assert p_wa not in result

    def test_includes_soporte_profiles(self):
        p_agent = _make_perfil(canal="SAC", modalidad="Actual", es_soporte=False)
        p_soporte = _make_perfil(canal="SAC", modalidad="Inbound", es_soporte=True)
        esc = _make_escenario(canal="SAC", modalidad="Actual")
        result = _filter_perfiles_por_escenario([p_agent, p_soporte], esc)
        assert p_agent in result
        assert p_soporte in result

    def test_case_insensitive_match(self):
        p = _make_perfil(canal="sac", modalidad="actual")
        esc = _make_escenario(canal="SAC", modalidad="Actual")
        result = _filter_perfiles_por_escenario([p], esc)
        assert p in result


# ---------------------------------------------------------------------------
# build_ratios_cost_to_serve — Block A
# ---------------------------------------------------------------------------

class TestBuildRatiosCostToServe:
    def _two_scenario_setup(self):
        calc = _make_calc()
        p_sac_sup = _make_perfil(nombre="Supervisor", canal="SAC", modalidad="Actual", fte=5.0)
        p_sac_agent = _make_perfil(nombre="Agente Básico 1", canal="SAC", modalidad="Actual", fte=50.0)
        p_wa_sup = _make_perfil(nombre="Supervisor", canal="WhatsApp", modalidad="Actual", fte=2.0)
        p_wa_agent = _make_perfil(nombre="Agente Básico 1", canal="WhatsApp", modalidad="Actual", fte=20.0)
        perfiles = [p_sac_sup, p_sac_agent, p_wa_sup, p_wa_agent]
        escenarios = [
            _make_escenario(escenario=1, canal="SAC", modalidad="Actual"),
            _make_escenario(escenario=2, canal="WhatsApp", modalidad="Actual"),
        ]
        return calc, perfiles, escenarios

    def test_returns_grafico_ratios_cts_result(self):
        calc, perfiles, escenarios = self._two_scenario_setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        assert isinstance(result, GraficoRatiosCTSResult)

    def test_escenario_count(self):
        calc, perfiles, escenarios = self._two_scenario_setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        assert len(result.escenarios) == 2

    def test_escenario_labels_exact(self):
        calc, perfiles, escenarios = self._two_scenario_setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        labels = [e.escenario_label for e in result.escenarios]
        assert "Escenario SAC Actual" in labels
        assert "Escenario WhatsApp Actual" in labels

    def test_costos_por_rol_populated(self):
        calc, perfiles, escenarios = self._two_scenario_setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        sac = next(e for e in result.escenarios if e.escenario_label == "Escenario SAC Actual")
        nombres = [r.rol_nombre for r in sac.costos_por_rol]
        assert "Supervisor" in nombres
        assert "Agente Básico 1" in nombres

    def test_total_por_rol_sums_across_scenarios(self):
        calc, perfiles, escenarios = self._two_scenario_setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        # total_por_rol["Supervisor"] = SAC supervisor cost + WhatsApp supervisor cost
        sac = next(e for e in result.escenarios if "SAC" in e.escenario_label)
        wa = next(e for e in result.escenarios if "WhatsApp" in e.escenario_label)
        sac_sup = next(r for r in sac.costos_por_rol if r.rol_nombre == "Supervisor")
        wa_sup = next(r for r in wa.costos_por_rol if r.rol_nombre == "Supervisor")
        expected = sac_sup.costo_total + wa_sup.costo_total
        assert result.total_por_rol["Supervisor"] == pytest.approx(expected, rel=1e-9)

    def test_selected_ratio_column_is_total(self):
        calc, perfiles, escenarios = self._two_scenario_setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        assert result.selected_ratio_column == "Total"

    def test_excel_trace(self):
        calc, perfiles, escenarios = self._two_scenario_setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        assert result.excel_trace == "Graficos!P4:BH29"

    def test_ratios_populated_after_step02(self):
        calc, perfiles, escenarios = self._two_scenario_setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        assert result.ratios_por_escenario != {}
        assert result.ratio_actual != {}

    def test_cargos_adicionales_is_deferred(self):
        calc, perfiles, escenarios = self._two_scenario_setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        cargos_deferred = any("Cargos Adicionales" in item for item in result.deferred_items)
        assert cargos_deferred, f"Expected Cargos Adicionales in deferred_items, got: {result.deferred_items}"

    def test_ratios_ar4_bh29_not_deferred(self):
        """Block B ratios are implemented in Step 02 — must NOT appear in deferred_items."""
        calc, perfiles, escenarios = self._two_scenario_setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        ratios_still_deferred = any("AR4:BH29" in item for item in result.deferred_items)
        assert not ratios_still_deferred

    def test_no_escenarios_returns_empty_result(self):
        calc = _make_calc()
        result = build_ratios_cost_to_serve([], [], calc)
        assert result.escenarios == []
        assert result.total_por_rol == {}

    def test_escenario_with_no_matching_profiles_is_skipped(self):
        calc = _make_calc()
        p = _make_perfil(canal="SAC", modalidad="Actual")
        esc_wa = _make_escenario(canal="WhatsApp", modalidad="Actual")
        result = build_ratios_cost_to_serve([p], [esc_wa], calc)
        assert result.escenarios == []

    def test_inhouse_label(self):
        calc = _make_calc()
        p = _make_perfil(canal="Inhouse", modalidad="Actual")
        esc = _make_escenario(canal="Inhouse", modalidad="Actual")
        result = build_ratios_cost_to_serve([p], [esc], calc)
        if result.escenarios:
            assert result.escenarios[0].escenario_label == "Crecimiento inhouse"


# ---------------------------------------------------------------------------
# GraficosResult backward compat
# ---------------------------------------------------------------------------

class TestGraficosResultExtended:
    def test_graficos_result_has_ratios_field(self):
        gr = GraficosResult()
        assert hasattr(gr, "ratios_cost_to_serve")
        assert gr.ratios_cost_to_serve is None

    def test_graficos_result_as_dict_includes_ratios(self):
        gr = GraficosResult()
        d = gr.as_dict()
        assert "ratios_cost_to_serve" in d
        assert d["ratios_cost_to_serve"] is None

    def test_graficos_result_bandas_still_works(self):
        gr = GraficosResult()
        assert gr.bandas_vision_final is None
        d = gr.as_dict()
        assert "bandas_vision_final" in d


# ---------------------------------------------------------------------------
# Step 02 — ratio helpers (unit tests)
# ---------------------------------------------------------------------------

class TestSafeRatio:
    def test_normal_division(self):
        assert _safe_ratio(10.0, 100.0) == pytest.approx(0.1)

    def test_zero_denominator_returns_zero(self):
        assert _safe_ratio(50.0, 0.0) == 0.0

    def test_zero_numerator(self):
        assert _safe_ratio(0.0, 100.0) == 0.0


class TestComputeDenominador:
    def test_excludes_agente_basico_1(self):
        costos = {"Supervisor": 100.0, "Agente Básico 1": 900.0, "Formadores": 50.0}
        denom = _compute_denominador(costos)
        assert denom == pytest.approx(150.0)

    def test_no_agente_basico_sums_all(self):
        costos = {"Supervisor": 100.0, "Formadores": 50.0}
        assert _compute_denominador(costos) == pytest.approx(150.0)

    def test_empty_returns_zero(self):
        assert _compute_denominador({}) == 0.0

    def test_only_agente_basico_returns_zero(self):
        costos = {"Agente Básico 1": 500.0}
        assert _compute_denominador(costos) == 0.0


class TestComputeRatiosPorEscenario:
    def _make_escenario_costos(self, label, costos_dict):
        from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
            CostoRolEscenario, EscenarioCostoRoles,
        )
        costos = [CostoRolEscenario(rol_nombre=k, costo_total=v) for k, v in costos_dict.items()]
        return EscenarioCostoRoles(escenario_label=label, canal="SAC", modalidad="Actual", costos_por_rol=costos)

    def test_ratio_values_are_correct(self):
        # Supervisor=100, Agente Básico 1=900, Formadores=50
        # denom = 100+50 = 150 (excludes Agente Básico 1)
        esc = self._make_escenario_costos(
            "Escenario SAC Actual",
            {"Supervisor": 100.0, "Agente Básico 1": 900.0, "Formadores": 50.0},
        )
        ratios = _compute_ratios_por_escenario([esc])
        sac = ratios["Escenario SAC Actual"]
        assert sac["Supervisor"] == pytest.approx(100.0 / 150.0)
        assert sac["Formadores"] == pytest.approx(50.0 / 150.0)

    def test_agente_basico_ratio_still_computed(self):
        """Agente Básico 1 is excluded from denominator but its ratio row IS computed."""
        esc = self._make_escenario_costos(
            "Escenario SAC Actual",
            {"Supervisor": 100.0, "Agente Básico 1": 900.0},
        )
        ratios = _compute_ratios_por_escenario([esc])
        sac = ratios["Escenario SAC Actual"]
        assert "Agente Básico 1" in sac
        # ratio = 900 / 100 (denom = only Supervisor)
        assert sac["Agente Básico 1"] == pytest.approx(900.0 / 100.0)

    def test_zero_denominator_returns_zero(self):
        esc = self._make_escenario_costos(
            "Test", {"Agente Básico 1": 500.0},
        )
        ratios = _compute_ratios_por_escenario([esc])
        assert ratios["Test"]["Agente Básico 1"] == 0.0

    def test_multiple_scenarios_independent(self):
        esc1 = self._make_escenario_costos("SAC", {"Supervisor": 100.0, "Agente Básico 1": 200.0})
        esc2 = self._make_escenario_costos("WA", {"Supervisor": 50.0, "Agente Básico 1": 100.0})
        ratios = _compute_ratios_por_escenario([esc1, esc2])
        assert ratios["SAC"]["Supervisor"] == pytest.approx(1.0)  # 100/100
        assert ratios["WA"]["Supervisor"] == pytest.approx(1.0)   # 50/50


class TestComputeRatiosTotal:
    def test_bh_column_formula(self):
        # total_por_rol: Supervisor=200, Agente Básico 1=800, Formadores=100
        # denom = 200+100 = 300
        total = {"Supervisor": 200.0, "Agente Básico 1": 800.0, "Formadores": 100.0}
        ratios = _compute_ratios_total(total)
        assert ratios["Supervisor"] == pytest.approx(200.0 / 300.0)
        assert ratios["Formadores"] == pytest.approx(100.0 / 300.0)
        assert ratios["Agente Básico 1"] == pytest.approx(800.0 / 300.0)

    def test_empty_returns_empty(self):
        assert _compute_ratios_total({}) == {}


# ---------------------------------------------------------------------------
# Step 02 — integration through build_ratios_cost_to_serve
# ---------------------------------------------------------------------------

class TestBuildRatiosStep02:
    """Integration tests for Block B (AR4:BH29) within build_ratios_cost_to_serve."""

    def _setup(self):
        """
        Three profiles: Supervisor + Agente Básico 1 + Formadores in SAC scenario.
        Makes denominator = Supervisor + Formadores costs (excl. Agente Básico 1).
        """
        calc = _make_calc()
        # Use distinct salario_cargado so costs are predictable per-role
        p_sup = _make_perfil(nombre="Supervisor", canal="SAC", modalidad="Actual",
                             fte=2.0, salario_cargado=3_000_000)
        p_agent = _make_perfil(nombre="Agente Básico 1", canal="SAC", modalidad="Actual",
                               fte=50.0, salario_cargado=2_500_000)
        p_form = _make_perfil(nombre="Formadores", canal="SAC", modalidad="Actual",
                              fte=1.0, salario_cargado=2_800_000)
        perfiles = [p_sup, p_agent, p_form]
        escenarios = [_make_escenario(escenario=1, canal="SAC", modalidad="Actual")]
        return calc, perfiles, escenarios

    def test_ratios_por_escenario_is_populated(self):
        calc, perfiles, escenarios = self._setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        assert "Escenario SAC Actual" in result.ratios_por_escenario

    def test_ratio_actual_is_populated(self):
        calc, perfiles, escenarios = self._setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        assert len(result.ratio_actual) > 0

    def test_denominator_excludes_agente_basico_1(self):
        """
        Verify: ratio_Supervisor = costo_Supervisor / (costo_Supervisor + costo_Formadores)
        denominator must NOT include costo_Agente Básico 1.
        """
        calc, perfiles, escenarios = self._setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        sac_ratios = result.ratios_por_escenario["Escenario SAC Actual"]

        # Reconstruct expected ratio independently
        sac_esc = result.escenarios[0]
        costo_sup = sac_esc.total_por_rol["Supervisor"]
        costo_form = sac_esc.total_por_rol["Formadores"]
        denom = costo_sup + costo_form          # Agente Básico 1 excluded
        expected = costo_sup / denom
        assert sac_ratios["Supervisor"] == pytest.approx(expected, rel=1e-9)

    def test_agente_basico_1_ratio_is_calculated(self):
        """Agente Básico 1 has its own ratio row (it IS in the numerator)."""
        calc, perfiles, escenarios = self._setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        sac_ratios = result.ratios_por_escenario["Escenario SAC Actual"]
        assert "Agente Básico 1" in sac_ratios
        assert sac_ratios["Agente Básico 1"] > 0.0

    def test_ratio_actual_equals_total_ratios(self):
        """ratio_actual = BH column = ratios computed on total_por_rol."""
        calc, perfiles, escenarios = self._setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        expected_total_ratios = _compute_ratios_total(result.total_por_rol)
        for rol, ratio in expected_total_ratios.items():
            assert result.ratio_actual[rol] == pytest.approx(ratio, rel=1e-12)

    def test_selected_ratio_column_is_total(self):
        calc, perfiles, escenarios = self._setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        assert result.selected_ratio_column == "Total"

    def test_excel_trace_covers_full_range(self):
        calc, perfiles, escenarios = self._setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        assert "BH29" in result.excel_trace

    def test_step01_absolute_costs_preserved(self):
        """Block A (escenarios, costos_por_rol) must still be populated."""
        calc, perfiles, escenarios = self._setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        assert len(result.escenarios) == 1
        sac = result.escenarios[0]
        assert len(sac.costos_por_rol) == 3
        assert result.total_por_rol != {}

    def test_cargos_adicionales_still_deferred(self):
        calc, perfiles, escenarios = self._setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        assert any("Cargos Adicionales" in item for item in result.deferred_items)

    def test_ratios_sum_check_single_scenario(self):
        """
        Ratios of non-excluded roles should sum to 1 + Agente Básico 1 ratio.
        More precisely: sum(all ratios) = sum(all costs) / denom.
        """
        calc, perfiles, escenarios = self._setup()
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)
        sac = result.escenarios[0]
        denom = _compute_denominador(sac.total_por_rol)
        total_cost = sum(sac.total_por_rol.values())
        expected_ratio_sum = _safe_ratio(total_cost, denom)
        actual_ratio_sum = sum(
            result.ratios_por_escenario["Escenario SAC Actual"].values()
        )
        assert actual_ratio_sum == pytest.approx(expected_ratio_sum, rel=1e-9)

    def test_two_scenarios_ratios_independent(self):
        """Each scenario has its own denominator, independent of other scenarios."""
        calc = _make_calc()
        p_sac_sup = _make_perfil(nombre="Supervisor", canal="SAC", modalidad="Actual",
                                 fte=5.0, salario_cargado=3_000_000)
        p_sac_agent = _make_perfil(nombre="Agente Básico 1", canal="SAC", modalidad="Actual",
                                   fte=50.0, salario_cargado=2_500_000)
        p_wa_sup = _make_perfil(nombre="Supervisor", canal="WhatsApp", modalidad="Actual",
                                fte=2.0, salario_cargado=3_000_000)
        p_wa_agent = _make_perfil(nombre="Agente Básico 1", canal="WhatsApp", modalidad="Actual",
                                  fte=20.0, salario_cargado=2_500_000)
        perfiles = [p_sac_sup, p_sac_agent, p_wa_sup, p_wa_agent]
        escenarios = [
            _make_escenario(escenario=1, canal="SAC", modalidad="Actual"),
            _make_escenario(escenario=2, canal="WhatsApp", modalidad="Actual"),
        ]
        result = build_ratios_cost_to_serve(perfiles, escenarios, calc)

        # SAC: denom=Supervisor_SAC_cost; ratio_Supervisor_SAC = 1.0
        # WA:  denom=Supervisor_WA_cost;  ratio_Supervisor_WA  = 1.0
        sac_ratios = result.ratios_por_escenario["Escenario SAC Actual"]
        wa_ratios = result.ratios_por_escenario["Escenario WhatsApp Actual"]
        assert sac_ratios["Supervisor"] == pytest.approx(1.0)
        assert wa_ratios["Supervisor"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Step 03 — VisionDatasetsBuilder wiring tests
# ---------------------------------------------------------------------------

class TestVisionDatasetsBuilderGraph02Wiring:
    """Verify that VisionDatasetsBuilder reads precomputed graph data."""

    def test_builder_reads_precomputed_graphs(self):
        from nexa_engine.modules.calculator_motor.formulas.graphics.models import (
            GraficosResult,
        )
        from nexa_engine.modules.vision_imprimible.builders.vision_datasets_builder import (
            VisionDatasetsBuilder,
        )
        from nexa_engine.modules.vision_imprimible.models.vision_datasets import (
            DatasetsVision,
        )

        graficos = GraficosResult(
            bandas_vision_final=SimpleNamespace(as_dict=lambda: {"graph": 1}),
            ratios_cost_to_serve=SimpleNamespace(as_dict=lambda: {"graph": 2}),
            ingresos_mensuales=SimpleNamespace(as_dict=lambda: {"graph": 3}),
            waterfall_table=SimpleNamespace(as_dict=lambda: {"graph": 4}),
            cts_bargaining_zone=SimpleNamespace(as_dict=lambda: {"graph": 5}),
        )
        resultado = SimpleNamespace(
            datasets_vision=DatasetsVision(graficos=graficos),
        )

        builder = VisionDatasetsBuilder(parametrizacion=object())
        datasets = builder.construir(SimpleNamespace(), resultado)

        assert datasets.graficos is graficos
        assert datasets.graficos.ratios_cost_to_serve.as_dict() == {"graph": 2}
        assert datasets.as_dict()["graficos"]["bandas_vision_final"] == {"graph": 1}
