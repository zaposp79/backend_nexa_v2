"""Tests for GET /simulation/{id}/results/vision-tarifas/modelo-cobro.

Matches VISION_TARIFAS_MODELO_COBRO_GET_POST_SCREEN_CONTRACT.
"""
from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.vision_tarifas.api.router import get_vision_tarifas_modelo_cobro


@pytest.fixture
def persisted_pricing_result() -> dict:
    return {
        "simulation_id": "sim_endpoint_01",
        "panel": {
            "margen": 0.21,
            "margen_objetivo_cadena_a": 0.21,
        },
        "ficha_deal": {
            "cliente": "Banco de Bogotá",
            "linea_negocio": "Atención al cliente",
            "ciudad": "Bogotá",
        },
        "vision_tarifas": {
            "selected_scenario_id": "escenario_2",
            "canales": [
                {
                    "nombre_canal": "Voz 1",
                    "modalidad": "Inbound",
                    "producto": "Voz 1",
                    "fte": 10.0,
                    "vol_mensual": 5000.0,
                    "modelo_cobro": "Variable",
                    "pct_fijo": 0.0,
                    "pct_variable": 1.0,
                    "facturacion": 32000.0,
                    "tarifa_fijo_fte": 0.0,
                    "tarifa_variable": 7369.0,
                },
                {
                    "nombre_canal": "Voz 2",
                    "modalidad": "Backoffice",
                    "producto": "Voz 2",
                    "fte": 4.0,
                    "vol_mensual": 0.0,
                    "modelo_cobro": "Fijo FTE",
                    "pct_fijo": 1.0,
                    "pct_variable": 0.0,
                    "facturacion": 18000.0,
                    "tarifa_fijo_fte": 1500.0,
                    "tarifa_variable": 0.0,
                },
            ],
            "costo_total": 88888.0,
            "ingreso_mensual": 55555.0,
            "desglose_producto_opex": [
                {
                    "producto": "Voz 1",
                    "costo_directo": 5000.0,
                    "costo_financiacion": 0.0,
                    "polizas": 50.0,
                    "ingreso_producto": 7000.0,
                }
            ],
            "escenarios_detalle": [
                {
                    "meta": {
                        "escenario": 1,
                        "modalidad": "Inbound",
                        "canal": "Voz 1",
                        "modelo_cobro": "Variable",
                        "componente_fijo_label": "FTE",
                        "pct_fijo": 0.0,
                        "componente_variable_label": "Transacción",
                        "pct_variable": 1.0,
                        "facturacion_directo": 32000.0,
                        "tarifa_componente_fijo": 0.0,
                        "tarifa_componente_variable": 7369.0,
                    },
                    "reglas_business": {
                        "cont_operativa": 0.05,
                        "cont_comercial": 0.03,
                        "markup": 0.10,
                        "descuento_volumen": 0.02,
                        "margen_cadena_a": 0.15,
                        "margen_cadena_b": 0.10,
                        "margen_cadena_c": 0.08,
                    },
                    "cadena_a": {
                        "total_costo": 10000.0,
                        "payroll": 8000.0,
                        "no_payroll": 2000.0,
                        "ica": 300.0,
                        "gmf": 50.0,
                        "comision_administracion": 0.0,
                        "polizas": 100.0,
                        "costos_financiacion": 250.0,
                        "ingreso_bruto": 15000.0,
                    },
                    "cadena_b": {"total_costo": 2000.0, "componente_variable": 1200.0, "ingreso_bruto": 5000.0},
                    "cadena_c": {"total_costo": 1000.0, "componente_variable": 500.0, "ingreso_bruto": 2500.0},
                    "tarifas": {
                        "facturacion_total": 50000.0,
                        "ingreso_componente_fijo": 0.0,
                        "ingreso_componente_variable": 50000.0,
                        "tarifa_por_fte": 0.0,
                        "tarifa_hora_loggeada": 0.0,
                        "tarifa_hora_pagada": 0.0,
                        "tarifa_por_transaccion": 7369.0,
                        "volumen_minimo_transaccion": 33575.0,
                    },
                    "componente_fijo": {"habilitado": False},
                    "componente_variable": {"habilitado": True, "cant_asesores": 0, "meses_comisiones": [{"mes": 1, "comision": "#VALOR!", "ingreso_total": 1000.0}]},
                },
                {
                    "meta": {
                        "escenario": 2,
                        "modelo_cobro": "Fijo FTE",
                        "componente_fijo_label": "FTE",
                        "pct_fijo": 1.0,
                        "componente_variable_label": "",
                        "pct_variable": 0.0,
                        "facturacion_directo": 18000.0,
                        "tarifa_componente_fijo": 1500.0,
                        "tarifa_componente_variable": 0.0,
                    },
                    "reglas_business": {
                        "cont_operativa": 0.02,
                        "cont_comercial": 0.01,
                        "markup": 0.05,
                        "descuento_volumen": 0.01,
                        "margen_cadena_a": 0.12,
                        "margen_cadena_b": 0.09,
                        "margen_cadena_c": 0.06,
                    },
                    "cadena_a": {"total_costo": 0.0, "payroll": 0.0, "no_payroll": 0.0, "ingreso_bruto": 0.0},
                    "cadena_b": {"total_costo": 0.0, "componente_fijo": 0.0, "componente_variable": 0.0, "ingreso_bruto": 0.0},
                    "cadena_c": {"total_costo": 0.0, "componente_fijo": 0.0, "componente_variable": 0.0, "ingreso_bruto": 0.0},
                    "tarifas": {
                        "facturacion_total": 0.0,
                        "ingreso_componente_fijo": 0.0,
                        "ingreso_componente_variable": 0.0,
                        "tarifa_por_fte": 1500.0,
                        "tarifa_hora_loggeada": 0.0,
                        "tarifa_hora_pagada": 0.0,
                        "tarifa_por_transaccion": 0.0,
                        "volumen_minimo_transaccion": 0.0,
                        "volumetria_de_1_fte": 0.0,
                    },
                    "componente_fijo": {"habilitado": True},
                    "componente_variable": {"habilitado": False, "cant_asesores": 0},
                },
            ],
        },
    }


class TestGetVisionTarifasModeloCobro:
    def test_returns_api_response(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)

        assert isinstance(response, ApiResponse)
        assert response.success is True

    def test_returns_success_data_error_meta_wrapper(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        assert response.success is True
        assert response.data is not None
        assert response.error is None
        assert response.meta is None

    def test_data_includes_cliente_servicio_ciudad(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data = response.data

        assert data["cliente"] == "Banco de Bogotá"
        assert data["servicio"] == "Atención al cliente"
        assert data["ciudad"] == "Bogotá"

    def test_data_includes_resumen_resultado_escenario(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data = response.data

        rows = data["resumen_resultado_escenario"]
        assert len(rows) == 6
        row_ids = [r["escenario"] for r in rows]
        assert row_ids == ["1", "2", "3", "4", "5", "Total"]

    def test_uses_canal_not_producto_for_scenarios(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data = response.data

        rows = {r["escenario"]: r for r in data["resumen_resultado_escenario"]}
        for row in rows.values():
            if row["escenario"] in ("1", "2"):
                assert "producto" not in row

    def test_modelo_cobro_is_list(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data = response.data

        assert isinstance(data["modelo_cobro"], list)
        assert len(data["modelo_cobro"]) == 6

    def test_modelo_cobro_contains_all_views(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data = response.data
        view_ids = [item["escenario"] for item in data["modelo_cobro"]]
        assert view_ids == ["1", "2", "3", "4", "5", "Total"]

    def test_selected_view_id_does_not_filter_modelo_cobro(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data = response.data
        assert data["selected_view_id"] == "escenario_2"
        assert len(data["modelo_cobro"]) == 6
        assert data["modelo_cobro"][0]["escenario"] == "1"  # All views still present

    def test_modelo_cobro_unavailable_are_placeholders(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data = response.data
        views = {item["escenario"]: item for item in data["modelo_cobro"]}

        assert views["4"]["modalidad"] is None
        assert views["4"]["fte"] == 0
        assert views["5"]["modalidad"] is None
        assert views["5"]["fte"] == 0

    def test_modelo_cobro_contains_detail_for_available(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data = response.data
        views = {item["escenario"]: item for item in data["modelo_cobro"]}

        view_2 = views["2"]
        assert view_2["modelo_cobro"] == "Fijo FTE"
        assert "cadena_a" in view_2
        assert "cadena_b" in view_2
        assert "cadena_c" in view_2
        assert "reglas_negocio" in view_2
        assert "tarifa_componente_fijo" in view_2
        assert "tarifa_componente_variable" in view_2

    def test_cadena_a_uses_exact_persisted_values(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data = response.data
        view_1 = next(item for item in data["modelo_cobro"] if item["escenario"] == "1")

        assert view_1["cadena_a"] == {
            "total": 10000.0,
            "payroll": 8000.0,
            "no_payroll": 2000.0,
            "ica": 300.0,
            "gmf": 50.0,
            "comision_administracion": 0.0,
            "polizas": 100.0,
            "costos_financiacion": 250.0,
            "ingreso_mensual": 15000.0,
        }

    def test_does_not_expose_raw_canales_or_escenarios_detalle(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data_str = str(response.data)

        assert "canales" not in data_str
        assert "escenarios_detalle" not in data_str
        assert "summary_matrix" not in data_str
        assert "shared_sections" not in data_str

    def test_does_not_expose_formula_strings(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data_str = str(response.data)

        assert "=SI" not in data_str
        assert "=CONCAT" not in data_str
        assert "#VALOR!" not in data_str

    def test_invalid_placeholders_are_hidden(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data_str = str(response.data)

        assert "#VALOR!" not in data_str
        assert "#DIV/0!" not in data_str
        assert "NaN" not in data_str

    def test_zero_values_are_preserved(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data = response.data

        rows = {r["escenario"]: r for r in data["resumen_resultado_escenario"]}
        row_2 = rows["2"]
        assert row_2["proporcion_componente_variable"] == 0.0
        assert row_2["tarifa_componente_variable"] == 0.0

    def test_monetary_fields_do_not_fall_back_to_canales(self, persisted_pricing_result):
        persisted_pricing_result["vision_tarifas"]["escenarios_detalle"][0]["meta"]["facturacion_directo"] = None
        persisted_pricing_result["vision_tarifas"]["escenarios_detalle"][0]["meta"]["tarifa_componente_fijo"] = None
        persisted_pricing_result["vision_tarifas"]["escenarios_detalle"][0]["meta"]["tarifa_componente_variable"] = None
        persisted_pricing_result["vision_tarifas"]["escenarios_detalle"][0]["meta"]["fte"] = None
        persisted_pricing_result["vision_tarifas"]["escenarios_detalle"][0]["meta"]["pct_fijo"] = None
        persisted_pricing_result["vision_tarifas"]["escenarios_detalle"][0]["meta"]["pct_variable"] = None
        persisted_pricing_result["vision_tarifas"]["escenarios_detalle"][0]["tarifas"]["ingreso_componente_fijo"] = None
        persisted_pricing_result["vision_tarifas"]["escenarios_detalle"][0]["tarifas"]["ingreso_componente_variable"] = None
        persisted_pricing_result["vision_tarifas"]["escenarios_detalle"][0]["tarifas"]["facturacion_total"] = None
        persisted_pricing_result["vision_tarifas"]["escenarios_detalle"][0]["tarifas"]["tarifa_por_fte"] = None
        persisted_pricing_result["vision_tarifas"]["escenarios_detalle"][0]["tarifas"]["tarifa_por_transaccion"] = None
        persisted_pricing_result["vision_tarifas"]["canales"][0]["facturacion"] = 999999.0
        persisted_pricing_result["vision_tarifas"]["canales"][0]["tarifa_fijo_fte"] = 8888.0
        persisted_pricing_result["vision_tarifas"]["canales"][0]["tarifa_variable"] = 7777.0
        persisted_pricing_result["vision_tarifas"]["canales"][0]["fte"] = 123.0
        persisted_pricing_result["vision_tarifas"]["canales"][0]["pct_fijo"] = 0.9
        persisted_pricing_result["vision_tarifas"]["canales"][0]["pct_variable"] = 0.1

        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data = response.data
        summary_row = next(item for item in data["resumen_resultado_escenario"] if item["escenario"] == "1")
        view_1 = next(item for item in data["modelo_cobro"] if item["escenario"] == "1")

        assert summary_row["facturacion"] is None
        assert summary_row["tarifa_componente_fijo"] is None
        assert summary_row["tarifa_componente_variable"] is None
        assert view_1["tarifa_componente_fijo"]["ingreso_componente_fijo"] is None
        assert view_1["tarifa_componente_fijo"]["tarifa_principal"] is None
        assert view_1["tarifa_componente_variable"]["ingreso_componente_variable"] is None
        assert view_1["tarifa_componente_variable"]["tarifa_principal"] is None
        assert view_1["fte"] is None
        assert view_1["proporcion_componente_fijo"] is None
        assert view_1["proporcion_componente_variable"] is None

    def test_handles_not_found(self):
        repo = Mock()
        repo.get.side_effect = NotFoundError(resource="simulation", identifier="missing")

        with pytest.raises(HTTPException) as exc_info:
            get_vision_tarifas_modelo_cobro("missing", repo=repo)

        assert exc_info.value.status_code == 404

    def test_desglose_producto_opex_uses_producto(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        response = get_vision_tarifas_modelo_cobro("sim_endpoint_01", repo=repo)
        data = response.data

        opex = data["desglose_producto_opex"]
        assert len(opex) >= 1
        for item in opex:
            assert "producto" in item
            assert "costo_directo" in item
            assert "costo_financiacion" in item
            assert "polizas" in item
            assert "ingreso_por_producto" in item
