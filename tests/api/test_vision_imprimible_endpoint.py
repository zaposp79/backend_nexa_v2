"""Tests for GET /simulation/{id}/results/vision-imprimible screen contract."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.vision_imprimible.api.router import get_vision_imprimible


@pytest.fixture
def persisted_result() -> dict:
    return {
        "simulation_id": "sim-vi-api",
        "vision_imprimible": {
            "ficha_deal": {
                "cliente": "Cliente API",
                "linea_negocio": "SAC",
                "ciudad": "Bogota",
                "sede": "Toberin",
                "tipo_cliente": "Grupo Aval",
                "antiguedad_cliente": "Cliente Antiguo",
                "fecha_inicio": "2026-07-01",
                "meses_contrato": 12,
                "periodo_pago_dias": 30,
                "ajuste_precio_tipo": "IPC",
                "ajuste_precio_tecnologico": "SMMLV",
                "ajuste_precio_frecuencia": "Anual",
                "divisa": "COP",
            },
            "kpis": {
                "ingreso_mensual": 100000.0,
                "costo_mensual_promedio": 75000.0,
                "valor_total_deal": 1200000.0,
                "margen_minimo_requerido": 0.17,
                "cumple_margen_minimo": True,
                "facturacion_mensual_proyectada": 110000.0,
            },
            "configuracion_comercial": {
                "modelo_cobro_principal": "Variable",
                "pct_fijo_global": 0.0,
                "pct_variable_global": 1.0,
                "tarifa_fija": 0.0,
                "tarifa_variable": 10.0,
                "descuento": 0.0,
                "margen_objetivo_cadena_a": 0.21,
                "volumen_base_mensual": 1000.0,
                "ingreso_mensual": 100000.0,
                "costo_mensual_total": 75000.0,
                "valor_total_deal": 1200000.0,
            },
            "waterfall_promedio": {"ingreso_neto": 100000.0},
            "pyg_por_mes": [{"mes": 1, "ingreso_neto": 100000.0}],
            "reglas_negocio": {
                "reglas": [
                    {"nombre": "contingencia_operativa", "aplicado": 0.05, "min_valor": 0.05, "max_valor": 0.08, "status": "dentro_rango"},
                    {"nombre": "contingencia_comercial", "aplicado": 0.01, "min_valor": 0.01, "max_valor": 0.03, "status": "dentro_rango"},
                    {"nombre": "markup", "aplicado": 0.02, "min_valor": 0.02, "max_valor": 0.08, "status": "dentro_rango"},
                    {"nombre": "descuento", "aplicado": 0.0, "min_valor": 0.0, "max_valor": 0.08, "status": "dentro_rango"},
                    {"nombre": "imprevistos", "aplicado": 0.0, "min_valor": 0.0, "max_valor": 0.05, "status": "dentro_rango"},
                ]
            },
            "evaluacion_riesgo": {
                "score_cliente": 1.6,
                "score_operativo": 2.1,
                "score_total": 1.9,
                "clasificacion_total": "Medio",
                "requiere_aprobacion": True,
                "criterios": [{"id": 1, "factor": "Factor 1", "categoria": "Cliente", "puntaje": 2}],
            },
            "comparativo_escenarios": [
                {"escenario": "Escenario 1", "modalidad_canal": "Inbound - Voz", "modelo_cobro": "Variable", "canales": "Voz"}
            ],
        },
        "vision_tarifas": {
            "canales": [
                {
                    "componente_fijo": "",
                    "pct_fijo": 0.0,
                    "componente_variable": "Transaccion",
                    "pct_variable": 1.0,
                    "tarifa_fijo_fte": 0.0,
                    "tarifa_variable": 10.0,
                }
            ]
        },
    }


def test_public_endpoint_returns_complete_screen_contract(persisted_result):
    repo = Mock()
    repo.get.return_value = persisted_result

    response = get_vision_imprimible("sim-vi-api", repo=repo)
    data = response.data.model_dump(mode="json") if hasattr(response.data, "model_dump") else response.data

    assert data["version"] == "v1"
    assert data["simulation_id"] == "sim-vi-api"
    assert "header" in data
    assert "summary_cards" in data
    assert "sections" in data
    assert "charts" in data
    assert "metadata" in data


def test_public_endpoint_contains_required_sections(persisted_result):
    repo = Mock()
    repo.get.return_value = persisted_result

    response = get_vision_imprimible("sim-vi-api", repo=repo)
    data = response.data.model_dump(mode="json") if hasattr(response.data, "model_dump") else response.data
    section_ids = {section["id"] for section in data["sections"]}

    assert {
        "ficha_deal",
        "economics",
        "configuracion_comercial",
        "analisis_grafico",
        "comparativo_escenarios",
        "control_aprobacion",
        "contingencias_ajustes",
    }.issubset(section_ids)


def test_public_endpoint_404s_when_result_missing():
    repo = Mock()
    repo.get.side_effect = NotFoundError(resource="simulation", identifier="missing")

    response = get_vision_imprimible("missing", repo=repo)

    assert response.status_code == 404
