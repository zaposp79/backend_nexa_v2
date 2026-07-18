"""Focused tests for the screen-ready vision_imprimible mapper."""
from __future__ import annotations

from typing import Any

from nexa_engine.modules.vision_imprimible.api.public_mapper import (
    build_public_vision_imprimible,
)


def _contains_key(obj: Any, forbidden_key: str) -> bool:
    if isinstance(obj, dict):
        if forbidden_key in obj:
            return True
        return any(_contains_key(value, forbidden_key) for value in obj.values())
    if isinstance(obj, list):
        return any(_contains_key(value, forbidden_key) for value in obj)
    return False


def _fake_persisted_result(include_approval_actors: bool = False) -> dict:
    payload = {
        "simulation_id": "sim-vi-1",
        "vision_imprimible": {
            "ficha_deal": {
                "cliente": "Cliente Demo",
                "linea_negocio": "SAC",
                "ciudad": "Bogota",
                "sede": "Toberin",
                "tipo_cliente": "Grupo Aval",
                "antiguedad_cliente": "Cliente Antiguo",
                "fecha_inicio": "2026-07-01",
                "meses_contrato": 12,
                "periodo_pago_dias": 45,
                "ajuste_precio_tipo": "IPC",
                "ajuste_precio_tecnologico": "SMMLV",
                "ajuste_precio_frecuencia": "Anual",
                "divisa": "COP",
            },
            "kpis": {
                "ingreso_mensual": 120000.0,
                "costo_mensual_promedio": 90000.0,
                "valor_total_deal": 1440000.0,
                "margen_minimo_requerido": 0.17,
                "cumple_margen_minimo": True,
                "facturacion_mensual_proyectada": 130000.0,
            },
            "configuracion_comercial": {
                "modelo_cobro_principal": "Variable",
                "pct_fijo_global": 0.2,
                "pct_variable_global": 0.8,
                "tarifa_fija": 0.0,
                "tarifa_variable": 15.0,
                "descuento": 0.0,
                "margen_objetivo_cadena_a": 0.22,
                "volumen_base_mensual": 5000.0,
                "ingreso_mensual": 120000.0,
                "costo_mensual_total": 90000.0,
                "valor_total_deal": 1440000.0,
            },
            "waterfall_promedio": {
                "ingreso_neto": 120000.0,
                "contribucion": 30000.0,
            },
            "pyg_por_mes": [
                {"mes": 1, "ingreso_neto": 115000.0},
                {"mes": 2, "ingreso_neto": 120000.0},
            ],
            "reglas_negocio": {
                "reglas": [
                    {"nombre": "contingencia_operativa", "aplicado": 0.05, "min_valor": 0.05, "max_valor": 0.08, "status": "dentro_rango"},
                    {"nombre": "contingencia_comercial", "aplicado": 0.01, "min_valor": 0.01, "max_valor": 0.03, "status": "dentro_rango"},
                    {"nombre": "markup", "aplicado": 0.02, "min_valor": 0.02, "max_valor": 0.08, "status": "dentro_rango"},
                    {"nombre": "descuento", "aplicado": 0.0, "min_valor": 0.0, "max_valor": 0.08, "status": "dentro_rango"},
                    {"nombre": "imprevistos", "aplicado": 0.03, "min_valor": 0.0, "max_valor": 0.06, "status": "dentro_rango"},
                ]
            },
            "evaluacion_riesgo": {
                "score_cliente": 1.5,
                "score_operativo": 2.0,
                "score_total": 1.75,
                "clasificacion_total": "Medio",
                "requiere_aprobacion": True,
                "criterios": [
                    {"id": 1, "factor": "Factor 1", "categoria": "Cliente", "puntaje": 2, "valor_evaluado": "x"},
                    {"id": 4, "factor": "Antiguedad", "categoria": "Cliente", "puntaje": 1, "valor_evaluado": "Cliente Antiguo"},
                ],
            },
            "comparativo_escenarios": [
                {"escenario": "Escenario 1", "modalidad_canal": "Inbound - Voz", "modelo_cobro": "Variable", "canales": "Voz"},
            ],
        },
        "vision_tarifas": {
            "canales": [
                {
                    "componente_fijo": "FTE",
                    "pct_fijo": 0.2,
                    "componente_variable": "Transaccion",
                    "pct_variable": 0.8,
                    "tarifa_fijo_fte": 0.0,
                    "tarifa_variable": 15.0,
                }
            ]
        },
    }
    if include_approval_actors:
        payload["vision_imprimible"]["aprobaciones"] = {
            "elaborador_pricing": {"nombre": "Ana Pricing", "estado": "pendiente"},
            "aprobador_director_pricing": {"nombre": "Carlos Director", "estado": "aprobado"},
        }
    return payload


def _section_by_id(result: dict[str, Any], section_id: str) -> dict[str, Any]:
    return next(section for section in result["sections"] if section["id"] == section_id)


def test_mapper_returns_screen_contract_root_shape():
    result = build_public_vision_imprimible(_fake_persisted_result()).model_dump(mode="json")

    assert result["version"] == "v1"
    assert result["simulation_id"] == "sim-vi-1"
    assert "header" in result
    assert "summary_cards" in result
    assert "sections" in result
    assert "charts" in result
    assert "metadata" in result


def test_mapper_includes_required_sections_and_charts():
    result = build_public_vision_imprimible(_fake_persisted_result()).model_dump(mode="json")
    section_ids = {section["id"] for section in result["sections"]}

    assert {
        "ficha_deal",
        "economics",
        "configuracion_comercial",
        "analisis_grafico",
        "comparativo_escenarios",
        "control_aprobacion",
        "contingencias_ajustes",
    }.issubset(section_ids)
    assert "waterfall" in result["charts"]
    assert "evolucion_ingreso_neto" in result["charts"]


def test_mapper_aligns_persisted_data_from_canonical_sections():
    result = build_public_vision_imprimible(_fake_persisted_result()).model_dump(mode="json")
    ficha = _section_by_id(result, "ficha_deal")
    economics = _section_by_id(result, "economics")
    control = _section_by_id(result, "control_aprobacion")

    ficha_items = {item["key"]: item["value"] for item in ficha["items"]}
    economics_items = {item["key"]: item["value"] for item in economics["items"]}
    control_item = control["items"][0]

    assert ficha_items["periodo_pago_dias"] == 45
    assert ficha_items["volumen_base_mensual"] == 5000.0
    assert ficha_items["antiguedad_cliente"] == "Cliente Antiguo"
    assert economics_items["ingreso_mensual"] == 120000.0
    assert economics_items["costo_mensual"] == 90000.0
    assert economics_items["valor_total_contrato"] == 1440000.0
    assert control_item["nivel_riesgo"]["score_cliente"] == 1.5
    assert control_item["nivel_riesgo"]["score_operativo"] == 2.0
    assert control_item["nivel_riesgo"]["score_deal"] == 1.75


def test_mapper_adds_aprobaciones_section_when_actor_data_exists():
    result = build_public_vision_imprimible(_fake_persisted_result(include_approval_actors=True)).model_dump(mode="json")
    section_ids = {section["id"] for section in result["sections"]}

    assert "aprobaciones" in section_ids


def test_mapper_omits_empty_aprobaciones_and_tracks_missing_fields():
    result = build_public_vision_imprimible(_fake_persisted_result(include_approval_actors=False)).model_dump(mode="json")
    section_ids = {section["id"] for section in result["sections"]}

    assert "aprobaciones" not in section_ids
    assert "aprobaciones.elaborador_pricing" in result["metadata"]["missing_fields"]
    assert "aprobaciones.aprobador_gerente_general" in result["metadata"]["missing_fields"]


def test_mapper_prunes_nulls_and_preserves_zeroes():
    payload = _fake_persisted_result()
    payload["vision_imprimible"]["configuracion_comercial"]["tarifa_fija"] = 0.0
    payload["vision_imprimible"]["configuracion_comercial"]["tarifa_variable"] = None

    result = build_public_vision_imprimible(payload).model_dump(mode="json")
    configuracion = _section_by_id(result, "configuracion_comercial")
    items = {item["key"]: item["value"] for item in configuracion["items"] if "value" in item}

    assert items["tarifa_fija"] == 0.0
    assert "tarifa_variable" not in items


def test_mapper_hides_internal_formula_excel_fields():
    result = build_public_vision_imprimible(_fake_persisted_result()).model_dump(mode="json")

    assert not _contains_key(result, "formula")
    assert not _contains_key(result, "excel_row")
