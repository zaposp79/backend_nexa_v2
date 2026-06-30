"""Tests for GET /simulation/{id}/results/cost-to-serve endpoint."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.vision_cost_to_serve.api.router import get_cost_to_serve
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


@pytest.fixture
def persisted_result() -> dict:
    return {
        "simulation_id": "sim-123",
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
            {
                "servicio": "SAC",
                "ingreso_mensual": 500000.0,
                "cts_ponderado": 175.0,
                "margen": 0.25,
            }
        ],
        "vision_por_canal": [
            {
                "canal": "Chat",
                "modalidad": "Inbound",
                "modelo_cobro": "Fijo FTE",
                "estado": "Activo",
                "fte": 5.0,
                "volumen_mensual": 3000,
            }
        ],
        "detalle_por_canal": [
            {
                "canal": "Chat",
                "cadenas": {
                    "cadena_a": {"items": [{"concepto": "Cost To Serve", "inbound": 1.0, "outbound": 0.0}]},
                    "cadena_b": {"items": []},
                    "cadena_c": {"items": []},
                },
            }
        ],
        "estructura_equipo": {
            "roles": [
                {
                    "rol": "Agente",
                    "cargo_tipo": "Agente",
                    "canal": "Chat",
                    "modalidad": "Inbound",
                    "fte": 5.0,
                    "es_soporte": False,
                    "salario_cargado_unitario": 2000.0,
                    "costo_mensual": 10000.0,
                }
            ],
            "por_cargo": [
                {
                    "cargo_tipo": "Agente",
                    "fte": 5.0,
                    "costo_mensual": 10000.0,
                }
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
            "participacion_a": 0.57,
            "participacion_b": 0.29,
            "participacion_c": 0.14,
            "fte_cadena_a": 10.0,
            "vol_cadena_b": 5000,
            "vol_cadena_c": 1000,
            "costo_total_acumulado": 175.0,
            "canal_view_habilitado": True,
            "canales_detalle": [],
        },
        "reglas_negocio": {
            "alerta": {
                "activa": True,
                "mensaje": "El contrato requiere aprobacion por parte de Alta Dirección",
            },
            "costo_total": 200000.0,
            "valor_total_deal": 6000000.0,
            "reglas": [
                {
                    "nombre": "margen_objetivo",
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


class TestGetCostToServeHandler:
    def test_returns_screen_contract(self, persisted_result):
        mock_repo = Mock()
        mock_repo.get.return_value = persisted_result

        response = get_cost_to_serve("sim-123", repo=mock_repo)
        expected = build_vision_cts_from_result(persisted_result)

        assert isinstance(response, ApiResponse)
        assert response.success is True
        assert response.data == expected
        assert response.meta == {"charts_version": "1.0"}

    def test_handles_not_found_error(self):
        mock_repo = Mock()
        mock_repo.get.side_effect = NotFoundError(
            resource="simulation",
            identifier="missing-id",
        )

        with pytest.raises(HTTPException) as exc_info:
            get_cost_to_serve("missing-id", repo=mock_repo)

        assert exc_info.value.status_code == 404


class TestGetCostToServePublicShape:
    def test_public_root_is_screen_contract(self, persisted_result):
        mock_repo = Mock()
        mock_repo.get.return_value = persisted_result

        response = get_cost_to_serve("sim-123", repo=mock_repo)
        data = response.data

        assert data["version"] == "v1"
        assert data["simulation_id"] == "sim-123"
        assert "header" in data
        assert "summary_cards" in data
        assert "sections" in data
        assert "charts" in data
        assert "metadata" in data

    def test_public_root_hides_raw_sources(self, persisted_result):
        mock_repo = Mock()
        mock_repo.get.return_value = persisted_result

        data = get_cost_to_serve("sim-123", repo=mock_repo).data

        assert "cost_to_serve" not in data
        assert "vision_por_servicio" not in data
        assert "vision_por_canal" not in data
        assert "detalle_por_canal" not in data
        assert "estructura_equipo" not in data

    def test_sections_hold_screen_data(self, persisted_result):
        mock_repo = Mock()
        mock_repo.get.return_value = persisted_result

        data = get_cost_to_serve("sim-123", repo=mock_repo).data
        section_keys = [section["key"] for section in data["sections"]]

        assert section_keys == ["servicio", "canal", "detalle_canal", "equipo", "reglas", "riesgo"]
        assert data["sections"][0]["items"][0]["servicio"] == "SAC"
        assert data["sections"][5]["items"][0]["clasificacion_total"] == "Medio"

    def test_risk_gap_removed_when_risk_exists(self, persisted_result):
        mock_repo = Mock()
        mock_repo.get.return_value = persisted_result

        data = get_cost_to_serve("sim-123", repo=mock_repo).data

        assert "risk_heatmap" not in data["charts"]["data_status"]["missing_upstream_data"]
        assert data["metadata"]["missing_fields"] == []

    def test_risk_section_omitted_when_missing(self, persisted_result):
        mock_repo = Mock()
        without_risk = dict(persisted_result)
        without_risk.pop("evaluacion_riesgo")
        mock_repo.get.return_value = without_risk

        data = get_cost_to_serve("sim-123", repo=mock_repo).data

        assert "riesgo" not in [section["key"] for section in data["sections"]]
        assert data["metadata"]["missing_fields"] == ["evaluacion_riesgo"]
        assert "risk_heatmap" in data["charts"]["data_status"]["missing_upstream_data"]

    def test_empty_values_pruned_but_zero_and_false_preserved(self):
        mock_repo = Mock()
        mock_repo.get.return_value = {
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

        data = get_cost_to_serve("sim-zero", repo=mock_repo).data

        assert "header" not in data
        assert data["summary_cards"][0]["value"] == 0.0
        assert data["summary_cards"][3]["value"] == 0.0
        assert data["metadata"]["missing_fields"] == ["evaluacion_riesgo"]
        assert not _contains_key(data, "cost_to_serve")
