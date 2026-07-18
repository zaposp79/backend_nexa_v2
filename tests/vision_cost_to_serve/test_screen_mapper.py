"""Tests for the Vision Cost To Serve screen mapper."""

from __future__ import annotations

from typing import Any

from nexa_engine.modules.vision_cost_to_serve.helpers.screen_mapper import (
    build_vision_cts_from_result,
)


def _contains_key(obj: Any, forbidden_key: str) -> bool:
    if isinstance(obj, dict):
        if forbidden_key in obj:
            return True
        return any(_contains_key(value, forbidden_key) for value in obj.values())
    if isinstance(obj, list):
        return any(_contains_key(value, forbidden_key) for value in obj)
    return False


def _persisted_result() -> dict:
    return {
        "simulation_id": "sim-cts-1",
        "ficha_deal": {
            "cliente": "Cliente Demo",
            "linea_negocio": "SAC",
            "ciudad": "Bogota",
            "fecha_inicio": "2026-07-01",
            "fecha_fin": "2027-06-30",
            "tipo_cliente": "Grupo Aval",
            "meses_contrato": 12,
        },
        "panel": {
            "modelo_cobro": "Fijo FTE",
            "ejecutivo": "Ana Perez",
            "tipo_cliente": "Grupo Aval",
        },
        "kpis": {
            "ingreso_mensual": 500000.0,
            "costo_mensual_promedio": 200000.0,
            "valor_total_deal": 6000000.0,
            "pct_utilidad_neta_total": 0.25,
        },
        "vision_por_servicio": [
            {"servicio": "SAC", "ingreso_mensual": 500000.0, "cts_ponderado": 175.0, "margen": 0.25}
        ],
        "vision_por_canal": [
            {"canal": "Chat", "modalidad": "Inbound", "modelo_cobro": "Fijo FTE", "estado": "Activo", "fte": 5.0}
        ],
        "detalle_por_canal": [
            {"canal": "Chat", "cadenas": {"cadena_a": {"items": [{"concepto": "Cost To Serve", "inbound": 1.0, "outbound": 0.0}]}}}
        ],
        "estructura_equipo": {
            "roles": [
                {"rol": "Agente", "fte": 5.0, "es_soporte": False, "costo_mensual": 10000.0}
            ],
            "por_cargo": [
                {"cargo_tipo": "Agente", "fte": 5.0, "costo_mensual": 10000.0}
            ],
            "fte_total": 5.0,
            "fte_agentes": 5.0,
            "fte_soporte": 0.0,
            "costo_total_mensual": 10000.0,
        },
        "cost_to_serve": {
            "cts_cadena_a": 100.0,
            "cts_cadena_b": 50.0,
            "cts_cadena_c": 25.0,
            "cts_ponderado": 175.0,
            "canal_view_habilitado": True,
        },
        "reglas_negocio": {
            "alerta": {"activa": True, "mensaje": "Alerta"},
            "costo_total": 200000.0,
            "valor_total_deal": 6000000.0,
            "reglas": [
                {
                    "nombre": "margen_objetivo_cadena_a",
                    "label": "Margen objetivo",
                    "aplicado": 0.25,
                    "min_valor": 0.2,
                    "max_valor": 0.3,
                    "status": "dentro_rango",
                }
            ],
        },
        "evaluacion_riesgo": {
            "score_cliente": 1.5,
            "score_operativo": 2.0,
            "score_total": 1.75,
            "clasificacion_total": "Medio",
            "requiere_aprobacion": True,
            "criterios": [
                {
                    "id": 1,
                    "factor": "Factor 1",
                    "categoria": "Cliente",
                    "valor_evaluado": "x",
                    "calificacion": "Medio",
                    "puntaje": 2,
                    "peso": 0.2,
                }
            ],
        },
    }


def test_mapper_builds_complete_screen_contract():
    contract = build_vision_cts_from_result(_persisted_result())

    assert contract["version"] == "v1"
    assert contract["simulation_id"] == "sim-cts-1"
    assert contract["header"]["cliente"] == "Cliente Demo"
    assert contract["summary_cards"][0]["key"] == "ingreso"
    assert contract["summary_cards"][3]["key"] == "cts"
    assert contract["summary_cards"][4]["key"] == "riesgo"
    assert [section["key"] for section in contract["sections"]] == [
        "servicio",
        "canal",
        "detalle_canal",
        "equipo",
        "reglas",
        "riesgo",
    ]
    assert "risk_heatmap" not in contract["charts"]["data_status"]["missing_upstream_data"]
    assert contract["metadata"]["source"] == "persisted_pricing_result"


def test_mapper_does_not_expose_raw_root_sources():
    contract = build_vision_cts_from_result(_persisted_result())

    assert "cost_to_serve" not in contract
    assert "vision_por_servicio" not in contract
    assert "vision_por_canal" not in contract
    assert "detalle_por_canal" not in contract
    assert "estructura_equipo" not in contract


def test_mapper_preserves_zero_values_and_prunes_empty_fields():
    payload = build_vision_cts_from_result(
        {
            "simulation_id": "sim-zero",
            "kpis": {
                "ingreso_mensual": 0.0,
                "costo_mensual_promedio": 0.0,
                "pct_utilidad_neta_total": 0.0,
            },
            "cost_to_serve": {
                "cts_cadena_a": 0.0,
                "cts_cadena_b": 0.0,
                "cts_cadena_c": 0.0,
                "cts_ponderado": 0.0,
                "canal_view_habilitado": False,
            },
            "vision_por_servicio": [],
            "vision_por_canal": [],
            "detalle_por_canal": [],
            "estructura_equipo": {},
            "reglas_negocio": {},
        }
    )

    assert "header" not in payload
    assert payload["summary_cards"][0]["value"] == 0.0
    assert payload["summary_cards"][3]["value"] == 0.0
    assert payload["sections"][0]["key"] == "equipo" or payload["sections"][0]["key"] in {"reglas", "servicio", "canal", "detalle_canal"}
    assert payload["metadata"]["missing_fields"] == ["evaluacion_riesgo"]
    assert not _contains_key(payload, "cost_to_serve")


def test_mapper_adds_missing_risk_metadata_when_absent():
    result = _persisted_result()
    result.pop("evaluacion_riesgo")

    contract = build_vision_cts_from_result(result)

    assert "riesgo" not in [section["key"] for section in contract["sections"]]
    assert contract["metadata"]["missing_fields"] == ["evaluacion_riesgo"]
    assert "risk_heatmap" in contract["charts"]["data_status"]["missing_upstream_data"]
