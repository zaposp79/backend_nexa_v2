"""Tests for charts mapper — builds chart contracts from persisted result."""

from __future__ import annotations

import pytest

from nexa_engine.modules.vision_cost_to_serve.helpers.charts_mapper import (
    ChartsMapper,
    build_charts_from_result,
)


# ────────────────────────────────────────────────────────────────────────────
# Fixtures: Minimal persisted result dicts
# ────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def minimal_result_dict() -> dict:
    """Minimal result dict with cost_to_serve only."""
    return {
        "cost_to_serve": {
            "cts_cadena_a": 100.0,
            "cts_cadena_b": 50.0,
            "cts_cadena_c": 25.0,
            "cts_ponderado": 175.0,
            "participacion_a": 0.57,
            "participacion_b": 0.29,
            "participacion_c": 0.14,
            "fte_cadena_a": 10.0,
            "vol_cadena_b": 5000,
            "vol_cadena_c": 1000,
            "costo_total_acumulado": 175.0,
            "desglose_a": {
                "nomina": 75.0,
                "no_payroll": 25.0,
                "nomina_loaded": 60.0,
                "salario_fijo": 30.0,
                "salario_variable": 15.0,
                "capacitacion_inicial": 5.0,
                "capacitacion_rotacion": 5.0,
                "examenes": 2.5,
                "estudios_seguridad": 2.5,
                "crucero": 0.0,
                "opex_fijo": 15.0,
                "inversiones": 5.0,
                "costos_fijos_estacion": 5.0,
            },
            "desglose_b": {
                "componente_fijo": 30.0,
                "opex": 10.0,
                "inversiones": 5.0,
                "soporte_mantenimiento": 3.0,
                "componente_variable": 2.0,
                "tarifa": 0.0,
                "opex_variable": 0.0,
                "tasa_escalamiento": 0.0,
                "hitl": 0.0,
            },
            "canal_view_habilitado": True,
            "canales_detalle": [],
        }
    }


@pytest.fixture
def full_result_dict() -> dict:
    """Full result dict with vision_imprimible sections."""
    return {
        "cost_to_serve": {
            "cts_cadena_a": 100.0,
            "cts_cadena_b": 50.0,
            "cts_cadena_c": 25.0,
            "cts_ponderado": 175.0,
            "participacion_a": 0.57,
            "participacion_b": 0.29,
            "participacion_c": 0.14,
            "fte_cadena_a": 10.0,
            "vol_cadena_b": 5000,
            "vol_cadena_c": 1000,
            "costo_total_acumulado": 175.0,
            "desglose_a": {
                "nomina": 75.0,
                "no_payroll": 25.0,
                "nomina_loaded": 60.0,
                "salario_fijo": 30.0,
                "salario_variable": 15.0,
                "capacitacion_inicial": 5.0,
                "capacitacion_rotacion": 5.0,
                "examenes": 2.5,
                "estudios_seguridad": 2.5,
                "crucero": 0.0,
                "opex_fijo": 15.0,
                "inversiones": 5.0,
                "costos_fijos_estacion": 5.0,
            },
            "desglose_b": {
                "componente_fijo": 30.0,
                "opex": 10.0,
                "inversiones": 5.0,
                "soporte_mantenimiento": 3.0,
                "componente_variable": 2.0,
                "tarifa": 0.0,
                "opex_variable": 0.0,
                "tasa_escalamiento": 0.0,
                "hitl": 0.0,
            },
            "canal_view_habilitado": True,
            "canales_detalle": [],
        },
        "vision_imprimible": {
            "vision_por_servicio": [
                {
                    "servicio": "SAC",
                    "ingreso_mensual": 500000.0,
                    "cts_ponderado": 175.0,
                    "costo_mensual": 200.0,
                    "margen": 299800.0,
                    "contribucion_total": 300000.0,
                    "fte_total": 15.0,
                    "volumen_mensual": 10000,
                    "meses_contrato": 12,
                    "cadenas_activas": ["A", "B", "C"],
                },
                {
                    "servicio": "Soporte Técnico",
                    "ingreso_mensual": 300000.0,
                    "cts_ponderado": 100.0,
                    "costo_mensual": 150.0,
                    "margen": 299850.0,
                    "contribucion_total": 250000.0,
                    "fte_total": 8.0,
                    "volumen_mensual": 5000,
                    "meses_contrato": 12,
                    "cadenas_activas": ["A", "B"],
                },
            ],
            "vision_por_canal": [
                {
                    "canal": "Chat",
                    "modalidad": "Inbound",
                    "modelo_cobro": "Por transacción",
                    "estado": "Activo",
                    "fte": 5.0,
                    "participacion_cadena_a": 0.3,
                    "volumen_mensual": 3000,
                    "facturacion": 150000.0,
                    "ingreso_bruto": 150000.0,
                    "costo_atribuible": 50.0,
                    "pct_fijo": 60.0,
                    "pct_variable": 40.0,
                    "inbound": {"fte": 5.0, "payroll": 40.0, "no_payroll": 10.0, "costo_total": 50.0},
                    "outbound": None,
                },
                {
                    "canal": "Voz",
                    "modalidad": "Outbound",
                    "modelo_cobro": "Mensual",
                    "estado": "Activo",
                    "fte": 8.0,
                    "participacion_cadena_a": 0.5,
                    "volumen_mensual": 5000,
                    "facturacion": 250000.0,
                    "ingreso_bruto": 250000.0,
                    "costo_atribuible": 80.0,
                    "pct_fijo": 50.0,
                    "pct_variable": 50.0,
                    "inbound": None,
                    "outbound": {"fte": 8.0, "payroll": 60.0, "no_payroll": 20.0, "costo_total": 80.0},
                },
                {
                    "canal": "Email",
                    "modalidad": "Inbound",
                    "modelo_cobro": "Híbrido",
                    "estado": "Inactivo",
                    "fte": 0.0,
                    "participacion_cadena_a": 0.0,
                    "volumen_mensual": 0,
                    "facturacion": 0.0,
                    "ingreso_bruto": 0.0,
                    "costo_atribuible": 0.0,
                    "pct_fijo": 0.0,
                    "pct_variable": 0.0,
                    "inbound": None,
                    "outbound": None,
                },
            ],
            "estructura_equipo": {
                "roles": [
                    {
                        "rol": "Agente de Chat",
                        "cargo_tipo": "Agente",
                        "canal": "Chat",
                        "modalidad": "Inbound",
                        "fte": 5.0,
                        "es_soporte": False,
                        "salario_cargado_unitario": 2000.0,
                        "costo_mensual": 10000.0,
                    },
                    {
                        "rol": "Supervisor",
                        "cargo_tipo": "Supervisor",
                        "canal": "Chat",
                        "modalidad": "Inbound",
                        "fte": 1.0,
                        "es_soporte": True,
                        "salario_cargado_unitario": 3000.0,
                        "costo_mensual": 3000.0,
                    },
                    {
                        "rol": "Agente Voz",
                        "cargo_tipo": "Agente",
                        "canal": "Voz",
                        "modalidad": "Outbound",
                        "fte": 8.0,
                        "es_soporte": False,
                        "salario_cargado_unitario": 2000.0,
                        "costo_mensual": 16000.0,
                    },
                    {
                        "rol": "QA",
                        "cargo_tipo": "QA",
                        "canal": "Voz",
                        "modalidad": "Outbound",
                        "fte": 1.0,
                        "es_soporte": True,
                        "salario_cargado_unitario": 2500.0,
                        "costo_mensual": 2500.0,
                    },
                ],
                "por_cargo": [
                    {
                        "cargo_tipo": "Agente",
                        "fte": 13.0,
                        "costo_mensual": 26000.0,
                    },
                    {
                        "cargo_tipo": "Supervisor",
                        "fte": 1.0,
                        "costo_mensual": 3000.0,
                    },
                    {
                        "cargo_tipo": "QA",
                        "fte": 1.0,
                        "costo_mensual": 2500.0,
                    },
                ],
                "fte_total": 15.0,
                "fte_agentes": 13.0,
                "fte_soporte": 2.0,
                "costo_total_mensual": 31500.0,
            },
        },
    }


# ────────────────────────────────────────────────────────────────────────────
# Tests: Chart emission
# ────────────────────────────────────────────────────────────────────────────


class TestChartsEmission:
    """Test that expected charts are emitted with proper structure."""

    def test_returns_dict_with_charts_and_gaps(self, full_result_dict):
        """build_charts returns dict with 'charts' and 'gaps' keys."""
        mapper = ChartsMapper(full_result_dict)
        result = mapper.build_charts()

        assert isinstance(result, dict)
        assert "charts" in result
        assert "gaps" in result
        assert isinstance(result["charts"], list)
        assert isinstance(result["gaps"], list)

    def test_cts_por_cadena_stacked_emitted(self, minimal_result_dict):
        """cts_por_cadena_stacked chart is emitted."""
        mapper = ChartsMapper(minimal_result_dict)
        charts = mapper.build_charts()["charts"]

        cts_charts = [c for c in charts if c["id"] == "cts_por_cadena_stacked"]
        assert len(cts_charts) == 1

        chart = cts_charts[0]
        assert chart["type"] == "bar_stacked"
        assert chart["title"] == "CTS Ponderado por Cadena"
        assert len(chart["data"]) == 3  # A, B, C
        assert chart["data"][0]["cadena"] == "A"
        assert chart["data"][0]["cts_cadena_a"] == 100.0

    def test_vision_por_canal_fte_emitted(self, full_result_dict):
        """vision_por_canal_fte chart is emitted."""
        mapper = ChartsMapper(full_result_dict)
        charts = mapper.build_charts()["charts"]

        fte_charts = [c for c in charts if c["id"] == "vision_por_canal_fte"]
        assert len(fte_charts) == 1

        chart = fte_charts[0]
        assert chart["type"] == "bar_horizontal"
        assert chart["x_axis"]["format"] == "number"
        assert chart["y_axis"]["format"] == "string"
        # Should only include active channels
        assert len(chart["data"]) == 2  # Chat, Voz (Email is Inactivo)
        assert chart["data"][0]["canal"] == "Chat"
        assert chart["data"][0]["fte"] == 5.0

    def test_vision_por_servicio_economics_emitted(self, full_result_dict):
        """vision_por_servicio_economics chart is emitted."""
        mapper = ChartsMapper(full_result_dict)
        charts = mapper.build_charts()["charts"]

        econ_charts = [c for c in charts if c["id"] == "vision_por_servicio_economics"]
        assert len(econ_charts) == 1

        chart = econ_charts[0]
        assert chart["type"] == "bar_grouped"
        assert len(chart["data"]) == 2  # SAC, Soporte Técnico
        assert chart["data"][0]["servicio"] == "SAC"
        assert chart["data"][0]["ingreso_mensual"] == 500000.0
        assert chart["data"][0]["cts_ponderado"] == 175.0

    def test_fte_estructura_pie_emitted(self, full_result_dict):
        """fte_estructura_pie chart is emitted."""
        mapper = ChartsMapper(full_result_dict)
        charts = mapper.build_charts()["charts"]

        pie_charts = [c for c in charts if c["id"] == "fte_estructura_pie"]
        assert len(pie_charts) == 1

        chart = pie_charts[0]
        assert chart["type"] == "pie"
        assert len(chart["data"]) == 2  # Agentes, Soporte
        assert chart["data"][0]["label"] == "Agentes"
        assert chart["data"][0]["value"] == 13.0
        assert chart["data"][1]["label"] == "Soporte"
        assert chart["data"][1]["value"] == 2.0
        # Check percentages
        assert abs(chart["data"][0]["percentage"] - (13.0 / 15.0 * 100)) < 0.01
        assert abs(chart["data"][1]["percentage"] - (2.0 / 15.0 * 100)) < 0.01

    def test_nomina_por_cargo_emitted(self, full_result_dict):
        """nomina_por_cargo chart is emitted."""
        mapper = ChartsMapper(full_result_dict)
        charts = mapper.build_charts()["charts"]

        cargo_charts = [c for c in charts if c["id"] == "nomina_por_cargo"]
        assert len(cargo_charts) == 1

        chart = cargo_charts[0]
        assert chart["type"] == "bar_horizontal"
        assert len(chart["data"]) == 3  # Agente, Supervisor, QA
        # Check first cargo (Agente)
        agente = chart["data"][0]
        assert agente["cargo_tipo"] == "Agente"
        assert agente["costo_mensual"] == 26000.0
        # pct_participacion = 26000 / 31500 * 100
        expected_pct = 26000.0 / 31500.0 * 100
        assert abs(agente["pct_participacion"] - expected_pct) < 0.01

    def test_desglose_b_por_componente_emitted(self, minimal_result_dict):
        """desglose_b_por_componente chart is emitted."""
        mapper = ChartsMapper(minimal_result_dict)
        charts = mapper.build_charts()["charts"]

        desglose_charts = [c for c in charts if c["id"] == "desglose_b_por_componente"]
        assert len(desglose_charts) == 1

        chart = desglose_charts[0]
        assert chart["type"] == "bar_horizontal"
        assert len(chart["data"]) == 5  # Fijo, Variable, OpEx, Inversiones, Soporte/Mantenimiento
        assert chart["data"][0]["componente"] == "Fijo"
        assert chart["data"][0]["monto"] == 30.0


# ────────────────────────────────────────────────────────────────────────────
# Tests: Gaps reporting
# ────────────────────────────────────────────────────────────────────────────


class TestGapsReporting:
    """Test that gaps are correctly reported for missing data."""

    def test_nomina_por_grupo_gap_reported(self, full_result_dict):
        """nomina_por_grupo gap is reported."""
        mapper = ChartsMapper(full_result_dict)
        gaps = mapper.build_charts()["gaps"]

        nomina_gaps = [g for g in gaps if g["chart_id"] == "nomina_por_grupo"]
        assert len(nomina_gaps) == 1
        assert nomina_gaps[0]["reason"] == "missing_semantic_group_mapping"

    def test_waterfall_gap_reported(self, full_result_dict):
        """detalle_canal_waterfall gap is reported."""
        mapper = ChartsMapper(full_result_dict)
        gaps = mapper.build_charts()["gaps"]

        waterfall_gaps = [g for g in gaps if g["chart_id"] == "detalle_canal_waterfall"]
        assert len(waterfall_gaps) == 1
        assert waterfall_gaps[0]["reason"] == "missing_waterfall_fact"

    def test_risk_gap_reported(self, full_result_dict):
        """risk_heatmap gap is reported."""
        mapper = ChartsMapper(full_result_dict)
        gaps = mapper.build_charts()["gaps"]

        risk_gaps = [g for g in gaps if g["chart_id"] == "risk_heatmap"]
        assert len(risk_gaps) == 1
        assert risk_gaps[0]["reason"] == "risk_contract_not_defined_for_cts"

    def test_comparativo_gap_reported(self, full_result_dict):
        """comparativo_escenarios gap is reported."""
        mapper = ChartsMapper(full_result_dict)
        gaps = mapper.build_charts()["gaps"]

        comp_gaps = [g for g in gaps if g["chart_id"] == "comparativo_escenarios"]
        assert len(comp_gaps) == 1
        assert comp_gaps[0]["reason"] == "scenario_variants_not_persisted_for_cts"


# ────────────────────────────────────────────────────────────────────────────
# Tests: Robustness with missing sections
# ────────────────────────────────────────────────────────────────────────────


class TestMissingData:
    """Test that mapper handles missing or empty sections gracefully."""

    def test_no_crash_with_empty_result(self):
        """Mapper doesn't crash with empty dict."""
        mapper = ChartsMapper({})
        result = mapper.build_charts()

        assert result["charts"] == []
        assert len(result["gaps"]) == 4  # Still report gaps

    def test_no_crash_with_none_result(self):
        """Mapper handles None result dict."""
        mapper = ChartsMapper(None)
        result = mapper.build_charts()

        assert result["charts"] == []
        assert len(result["gaps"]) == 4

    def test_backward_compat_root_level_keys(self):
        """Mapper supports vision_por_servicio at root level."""
        result = {
            "vision_por_servicio": [
                {
                    "servicio": "SAC",
                    "ingreso_mensual": 500000.0,
                    "cts_ponderado": 175.0,
                    "margen": 299800.0,
                }
            ]
        }
        mapper = ChartsMapper(result)
        charts = mapper.build_charts()["charts"]

        econ_charts = [c for c in charts if c["id"] == "vision_por_servicio_economics"]
        assert len(econ_charts) == 1
        assert econ_charts[0]["data"][0]["servicio"] == "SAC"

    def test_empty_vision_por_canal_returns_no_chart(self):
        """Empty vision_por_canal returns no FTE chart."""
        result = {"vision_imprimible": {"vision_por_canal": []}}
        mapper = ChartsMapper(result)
        charts = mapper.build_charts()["charts"]

        fte_charts = [c for c in charts if c["id"] == "vision_por_canal_fte"]
        assert len(fte_charts) == 0


# ────────────────────────────────────────────────────────────────────────────
# Tests: Helper function
# ────────────────────────────────────────────────────────────────────────────


class TestConvenienceFunction:
    """Test the build_charts_from_result convenience function."""

    def test_convenience_function_works(self, full_result_dict):
        """build_charts_from_result produces same output as mapper."""
        charts = build_charts_from_result(full_result_dict)

        assert "charts" in charts
        assert "gaps" in charts
        assert len(charts["charts"]) > 0
