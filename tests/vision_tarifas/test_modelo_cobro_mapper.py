"""Tests for the public Vision Tarifas modelo_cobro screen contract.

Matches VISION_TARIFAS_MODELO_COBRO_GET_POST_SCREEN_CONTRACT.
"""
from __future__ import annotations

import inspect

from nexa_engine.modules.vision_tarifas.helpers.modelo_cobro_mapper import (
    build_modelo_cobro_from_result,
)


def _base_result() -> dict:
    return {
        "simulation_id": "sim_tarifas_001",
        "panel": {
            "margen": 0.21,
            "margen_objetivo": 0.21,
        },
        "vision_tarifas": {
            "selected_scenario_id": "escenario_2",
            "canales": [
                {
                    "nombre_canal": "Voz 1",
                    "modalidad": "Inbound",
                    "producto": "Voz 1",
                    "fte": 12.0,
                    "vol_mensual": 25000.0,
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
            "costo_total": 99999.0,
            "ingreso_mensual": 55555.0,
            "desglose_producto_opex": [
                {
                    "producto": "Voz 1",
                    "costo_directo": 5000.0,
                    "costo_financiacion": 0.0,
                    "polizas": 0.0,
                    "ingreso_producto": 7000.0,
                },
                {
                    "producto": "Fantasma",
                    "costo_directo": None,
                    "costo_financiacion": None,
                    "polizas": None,
                    "ingreso_producto": None,
                },
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
                        "markup": 0.1,
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
                    "cadena_b": {
                        "total_costo": 2000.0,
                        "componente_fijo": 0.0,
                        "componente_variable": 1200.0,
                        "ica": 0.0,
                        "gmf": 0.0,
                        "comision_administracion": 0.0,
                        "polizas": 0.0,
                        "costos_financiacion": 0.0,
                        "ingreso_bruto": 5000.0,
                    },
                    "cadena_c": {
                        "total_costo": 1000.0,
                        "componente_fijo": 0.0,
                        "componente_variable": 500.0,
                        "ica": 0.0,
                        "gmf": 0.0,
                        "comision_administracion": 0.0,
                        "polizas": 0.0,
                        "costos_financiacion": 0.0,
                        "ingreso_bruto": 2500.0,
                    },
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
                    "componente_variable": {
                        "habilitado": True,
                        "cant_asesores": 0,
                        "meses_comisiones": [
                            {"mes": 1, "comision": "#DIV/0!", "ingreso_total": 1000.0, "per_capita": 0.0},
                            {"mes": 2, "comision": 0.0, "ingreso_total": 0.0, "per_capita": 0.0},
                        ],
                    },
                    "tarifas_venta": [
                        {"mes": 1, "tarifa_venta": 10.0, "minimo_ventas": 1.0},
                    ],
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
                    "cadena_a": {
                        "total_costo": 0.0,
                        "payroll": 0.0,
                        "no_payroll": 0.0,
                        "ica": 0.0,
                        "gmf": 0.0,
                        "comision_administracion": 0.0,
                        "polizas": 0.0,
                        "costos_financiacion": 0.0,
                        "ingreso_bruto": 0.0,
                    },
                    "cadena_b": {
                        "total_costo": 0.0,
                        "componente_fijo": 0.0,
                        "componente_variable": 0.0,
                        "ica": 0.0,
                        "gmf": 0.0,
                        "comision_administracion": 0.0,
                        "polizas": 0.0,
                        "costos_financiacion": 0.0,
                        "ingreso_bruto": 0.0,
                    },
                    "cadena_c": {
                        "total_costo": 0.0,
                        "componente_fijo": 0.0,
                        "componente_variable": 0.0,
                        "ica": 0.0,
                        "gmf": 0.0,
                        "comision_administracion": 0.0,
                        "polizas": 0.0,
                        "costos_financiacion": 0.0,
                        "ingreso_bruto": 0.0,
                    },
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
                    "tarifas_venta": [
                        {"mes": 1, "tarifa_venta": "#DIV/0!", "minimo_ventas": 0.0},
                    ],
                },
            ],
        },
    }


class TestModeloCobroMapper:
    def test_public_contract_shape_and_labels(self):
        payload = build_modelo_cobro_from_result(_base_result())

        assert "cliente" in payload
        assert "servicio" in payload
        assert "ciudad" in payload
        assert "selected_view_id" in payload
        assert "resumen_resultado_escenario" in payload
        assert "modelo_cobro" in payload
        assert "desglose_producto_opex" in payload

        assert "canales" not in payload
        assert "escenarios_detalle" not in payload
        assert "summary_matrix" not in payload
        assert "scenarios" not in payload
        assert "views" not in payload
        assert "shared_sections" not in payload

    def test_resumen_has_escenario_1_to_5_plus_total(self):
        payload = build_modelo_cobro_from_result(_base_result())
        rows = payload["resumen_resultado_escenario"]
        assert len(rows) == 6

        row_ids = [r["escenario"] for r in rows]
        assert row_ids == ["1", "2", "3", "4", "5", "Total"]

        for row in rows:
            assert "modalidad" in row
            assert "canal" in row
            assert "modelo_cobro" in row
            assert "componente_fijo" in row
            assert "proporcion_componente_fijo" in row
            assert "componente_variable" in row
            assert "proporcion_componente_variable" in row
            assert "facturacion" in row
            assert "tarifa_componente_fijo" in row
            assert "tarifa_componente_variable" in row

    def test_resumen_uses_canal_not_producto(self):
        payload = build_modelo_cobro_from_result(_base_result())
        rows = {r["escenario"]: r for r in payload["resumen_resultado_escenario"]}

        row_1 = rows["1"]
        assert row_1["canal"] == "Voz 1"
        assert "producto" not in row_1

    def test_unavailable_scenarios_have_null_placeholders(self):
        payload = build_modelo_cobro_from_result(_base_result())
        rows = {r["escenario"]: r for r in payload["resumen_resultado_escenario"]}

        row_3 = rows["3"]
        assert row_3["modalidad"] is None
        assert row_3["canal"] is None
        assert row_3["modelo_cobro"] is None
        assert row_3["proporcion_componente_fijo"] == 0
        assert row_3["proporcion_componente_variable"] == 0
        assert row_3["facturacion"] == 0

        row_4 = rows["4"]
        assert row_4["modalidad"] is None
        assert row_4["proporcion_componente_fijo"] == 0
        assert row_4["facturacion"] == 0

        row_5 = rows["5"]
        assert row_5["modalidad"] is None
        assert row_5["proporcion_componente_fijo"] == 0

    def test_total_row_has_correct_shape(self):
        payload = build_modelo_cobro_from_result(_base_result())
        rows = {r["escenario"]: r for r in payload["resumen_resultado_escenario"]}
        total = rows["Total"]

        assert total["modelo_cobro"] == "Fijo"
        assert total["componente_fijo"] == "FTE"
        assert total["proporcion_componente_fijo"] == 0
        assert total["componente_variable"] == "Transacción"
        assert total["proporcion_componente_variable"] == 1
        assert total["facturacion"] == 55555.0

    def test_selected_view_defaults_to_first_available(self):
        result = _base_result()
        del result["vision_tarifas"]["selected_scenario_id"]

        payload = build_modelo_cobro_from_result(result)
        assert payload["selected_view_id"] == "escenario_1"

    def test_modelo_cobro_is_list(self):
        payload = build_modelo_cobro_from_result(_base_result())
        assert isinstance(payload["modelo_cobro"], list)
        assert len(payload["modelo_cobro"]) == 6

    def test_modelo_cobro_contains_all_views(self):
        payload = build_modelo_cobro_from_result(_base_result())
        view_ids = [item["escenario"] for item in payload["modelo_cobro"]]
        assert view_ids == ["1", "2", "3", "4", "5", "Total"]

    def test_selected_view_id_does_not_filter_modelo_cobro(self):
        payload = build_modelo_cobro_from_result(_base_result())
        assert payload["selected_view_id"] == "escenario_2"
        assert len(payload["modelo_cobro"]) == 6

    def test_modelo_cobro_unavailable_scenarios_are_placeholders(self):
        payload = build_modelo_cobro_from_result(_base_result())
        views = {item["escenario"]: item for item in payload["modelo_cobro"]}

        view_4 = views["4"]
        assert view_4["modalidad"] is None
        assert view_4["canal"] is None
        assert view_4["modelo_cobro"] is None
        assert view_4["proporcion_componente_fijo"] == 0
        assert view_4["fte"] == 0

        view_5 = views["5"]
        assert view_5["modalidad"] is None
        assert view_5["fte"] == 0

    def test_modelo_cobro_total_is_last_item(self):
        payload = build_modelo_cobro_from_result(_base_result())
        assert payload["modelo_cobro"][-1]["escenario"] == "Total"

    def test_modelo_cobro_available_has_full_detail(self):
        payload = build_modelo_cobro_from_result(_base_result())
        views = {item["escenario"]: item for item in payload["modelo_cobro"]}
        view_1 = views["1"]

        assert "cadena_a" in view_1
        assert "cadena_b" in view_1
        assert "cadena_c" in view_1
        assert "totales" in view_1
        assert "reglas_negocio" in view_1
        assert "tarifa_componente_fijo" in view_1
        assert "tarifa_componente_variable" in view_1
        assert "fte" in view_1
        assert "producto" not in view_1

    def test_modelo_cobro_uses_canal_not_producto(self):
        payload = build_modelo_cobro_from_result(_base_result())
        views = {item["escenario"]: item for item in payload["modelo_cobro"]}
        view_1 = views["1"]
        assert view_1["canal"] == "Voz 1"
        assert "producto" not in view_1

    def test_modelo_cobro_cadenas_have_semantic_fields(self):
        payload = build_modelo_cobro_from_result(_base_result())
        views = {item["escenario"]: item for item in payload["modelo_cobro"]}
        view_1 = views["1"]

        ca = view_1["cadena_a"]
        assert "total" in ca
        assert "payroll" in ca
        assert "no_payroll" in ca
        assert "ica" in ca
        assert "gmf" in ca
        assert "comision_administracion" in ca
        assert "polizas" in ca
        assert "costos_financiacion" in ca
        assert "ingreso_mensual" in ca

        cb = view_1["cadena_b"]
        assert "componente_fijo" in cb
        assert "componente_variable" in cb

    def test_modelo_cobro_cadena_a_uses_exact_persisted_values(self):
        payload = build_modelo_cobro_from_result(_base_result())
        views = {item["escenario"]: item for item in payload["modelo_cobro"]}
        ca = views["1"]["cadena_a"]

        assert ca == {
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

    def test_modelo_cobro_reglas_negocio_has_correct_keys(self):
        payload = build_modelo_cobro_from_result(_base_result())
        views = {item["escenario"]: item for item in payload["modelo_cobro"]}
        view_1 = views["1"]
        rules = view_1["reglas_negocio"]

        assert "total_regla_negocio" in rules
        assert "descuento_volumen" in rules
        assert "cont_operativa" in rules
        assert "cont_comercial" in rules
        assert "margen_cadena_a" in rules
        assert "margen_cadena_b" in rules
        assert "margen_cadena_c" in rules
        assert "markup" in rules

        assert "pct_fijo" not in rules
        assert "pct_variable" not in rules
        assert "tarifa_fijo_fte" not in rules
        assert "reglas_necocios" not in rules

    def test_modelo_cobro_tarifa_fijo_no_formula_keys(self):
        payload = build_modelo_cobro_from_result(_base_result())
        views = {item["escenario"]: item for item in payload["modelo_cobro"]}
        view_1 = views["1"]
        tf = view_1["tarifa_componente_fijo"]

        assert "tarifa_principal_label" in tf
        assert "tarifa_secundaria_label" in tf
        assert "tarifa_por_fte" in tf
        assert "tarifa_por_minuto_loggeado" in tf
        assert "tarifa_por_minuto_pagado" in tf

        keys_str = str(list(tf.keys()))
        assert "=SI" not in keys_str
        assert "=CONCAT" not in keys_str

    def test_modelo_cobro_tarifa_fijo_label_fte_logic(self):
        payload = build_modelo_cobro_from_result(_base_result())
        views = {item["escenario"]: item for item in payload["modelo_cobro"]}
        # Escenario 2 has modelo_cobro="Fijo FTE", componente_fijo_label="FTE"
        view_2 = views["2"]
        tf = view_2["tarifa_componente_fijo"]
        assert tf["tarifa_principal_label"] == "Tarifa por FTE"

    def test_modelo_cobro_tarifa_variable_no_formula_keys(self):
        payload = build_modelo_cobro_from_result(_base_result())
        views = {item["escenario"]: item for item in payload["modelo_cobro"]}
        view_1 = views["1"]
        tv = view_1["tarifa_componente_variable"]

        assert "titulo" in tv
        assert "tarifa_principal_label" in tv
        assert "volumen_label" in tv
        assert "volumetria_label" in tv
        assert "tarifa_por_transaccion" in tv

        keys_str = str(list(tv.keys()))
        assert "=SI" not in keys_str
        assert "=CONCAT" not in keys_str

    def test_monetary_fields_do_not_fall_back_to_canales(self):
        result = _base_result()
        scenario = result["vision_tarifas"]["escenarios_detalle"][0]
        channel = result["vision_tarifas"]["canales"][0]

        scenario["meta"]["facturacion_directo"] = None
        scenario["meta"]["tarifa_componente_fijo"] = None
        scenario["meta"]["tarifa_componente_variable"] = None
        scenario["meta"]["fte"] = None
        scenario["meta"]["pct_fijo"] = None
        scenario["meta"]["pct_variable"] = None
        scenario["tarifas"]["ingreso_componente_fijo"] = None
        scenario["tarifas"]["ingreso_componente_variable"] = None
        scenario["tarifas"]["facturacion_total"] = None
        scenario["tarifas"]["tarifa_por_fte"] = None
        scenario["tarifas"]["tarifa_por_transaccion"] = None
        channel["facturacion"] = 999999.0
        channel["tarifa_fijo_fte"] = 8888.0
        channel["tarifa_variable"] = 7777.0
        channel["fte"] = 123.0
        channel["pct_fijo"] = 0.9
        channel["pct_variable"] = 0.1

        payload = build_modelo_cobro_from_result(result)
        summary_row = {row["escenario"]: row for row in payload["resumen_resultado_escenario"]}["1"]
        view_1 = {item["escenario"]: item for item in payload["modelo_cobro"]}["1"]

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

    def test_summary_labels_can_fallback_to_canales(self):
        result = _base_result()
        scenario = result["vision_tarifas"]["escenarios_detalle"][1]
        channel = result["vision_tarifas"]["canales"][1]

        scenario["meta"]["modalidad"] = None
        scenario["meta"]["canal"] = None
        scenario["meta"]["modelo_cobro"] = None
        channel["modalidad"] = "Backoffice"
        channel["producto"] = "Voz 2"
        channel["modelo_cobro"] = "Fijo FTE"

        payload = build_modelo_cobro_from_result(result)
        rows = {r["escenario"]: r for r in payload["resumen_resultado_escenario"]}
        row_2 = rows["2"]

        assert row_2["modalidad"] == "Backoffice"
        assert row_2["canal"] == "Voz 2"
        assert row_2["modelo_cobro"] == "Fijo FTE"

    def test_desglose_producto_opex_uses_producto(self):
        payload = build_modelo_cobro_from_result(_base_result())
        opex = payload["desglose_producto_opex"]

        assert len(opex) >= 1
        for item in opex:
            assert "producto" in item
            assert "costo_directo" in item
            assert "costo_financiacion" in item
            assert "polizas" in item
            assert "ingreso_por_producto" in item

        # Verify the Voz 1 product
        voz = next(item for item in opex if item["producto"] == "Voz 1")
        assert voz["costo_directo"] == 5000.0
        assert voz["ingreso_por_producto"] == 7000.0

    def test_invalid_placeholders_are_removed_and_zeroes_survive(self):
        payload = build_modelo_cobro_from_result(_base_result())

        assert "#DIV/0!" not in str(payload)
        assert "#VALOR!" not in str(payload)

        # Zero values are preserved
        rows = {r["escenario"]: r for r in payload["resumen_resultado_escenario"]}
        row_2 = rows["2"]
        assert row_2["proporcion_componente_variable"] == 0.0
        assert row_2["tarifa_componente_variable"] == 0.0

    def test_no_backend_recalculation_happens_in_mapper(self):
        payload = build_modelo_cobro_from_result(_base_result())
        views = {item["escenario"]: item for item in payload["modelo_cobro"]}
        view_1 = views["1"]
        totales = view_1["totales"]
        assert totales.get("costo_total_mensual") == 99999.0

    def test_header_fields_from_panel_fallback(self):
        payload = build_modelo_cobro_from_result(_base_result())
        assert payload["cliente"] is None  # No cliente in test data
        assert payload["servicio"] is None  # No servicio in test data
        assert payload["ciudad"] is None  # No ciudad in test data


class TestModeloCobroNoExternalDeps:
    def test_no_provider_engine_or_storage_imports(self):
        from nexa_engine.modules.vision_tarifas.helpers import modelo_cobro_mapper

        source = inspect.getsource(modelo_cobro_mapper)
        assert "ParametrizationProvider" not in source
        assert "NexaPricingEngine" not in source
        assert "SimulationContextBuilder" not in source
        assert "storage/" not in source

    def test_no_excel_runtime_usage(self):
        from nexa_engine.modules.vision_tarifas.helpers import modelo_cobro_mapper

        source = inspect.getsource(modelo_cobro_mapper)
        assert "openpyxl" not in source
