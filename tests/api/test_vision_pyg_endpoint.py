"""Tests for GET /simulation/{id}/results/vision-pyg frontend contract."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.vision_pyg.api.vision_router import get_vision_pyg


def _contains_key(obj: Any, forbidden_key: str) -> bool:
    if isinstance(obj, dict):
        if forbidden_key in obj:
            return True
        return any(_contains_key(value, forbidden_key) for value in obj.values())
    if isinstance(obj, list):
        return any(_contains_key(value, forbidden_key) for value in obj)
    return False


@pytest.fixture
def minimal_pricing_result():
    return {
        "vision_pyg": {
            "resumen": {
                "cliente": "Test Client",
                "tipo_cliente": "GRANDE",
                "linea_negocio": "Outsourcing",
                "periodo_pago_dias": 0,
                "duracion_contrato": "01/07/2026 a 30/06/2028",
                "meses_contrato": 2,
                "divisa": "COP",
            },
            "fechas_meses": ["2026-07-01", "2026-08-01"],
            "secciones": [
                {
                    "key": "ingresos",
                    "filas": [
                        {
                            "key": "ingreso_bruto_a",
                            "label": "Ingreso Cadena A",
                            "valores": [1000.0, 1100.0],
                            "acumulado": 2100.0,
                            "promedio": 1050.0,
                            "excel_row": 18,
                            "formula": "=SUM(A1:A2)",
                            "detalle": [],
                            "tipo": "subtotal",
                            "signo": "=",
                        }
                    ],
                },
                {
                    "key": "costos_op",
                    "filas": [
                        {
                            "key": "payroll_a",
                            "label": "Payroll A",
                            "valores": [500.0, 0.0],
                            "acumulado": 500.0,
                            "excel_row": 19,
                            "formula": "=SUM(B1:B2)",
                        },
                        {
                            "key": "costo_b",
                            "label": "Costo B",
                            "valores": [300.0, 330.0],
                            "acumulado": 630.0,
                            "excel_row": 20,
                            "formula": "=SUM(C1:C2)",
                        },
                        {
                            "key": "costo_c",
                            "label": "Costo C",
                            "valores": [200.0, 220.0],
                            "acumulado": 420.0,
                            "excel_row": 21,
                            "formula": "=SUM(D1:D2)",
                        },
                    ],
                },
                {
                    "key": "costos_fin",
                    "filas": [
                        {
                            "key": "ica",
                            "label": "ICA",
                            "valores": [10.0, None],
                            "acumulado": 10.0,
                            "excel_row": 22,
                            "formula": "=E1",
                        }
                    ],
                },
                {
                    "key": "resultados",
                    "filas": [
                        {
                            "key": "utilidad_neta",
                            "label": "Utilidad Neta",
                            "valores": [0.0, 0.0],
                            "acumulado": 0.0,
                            "excel_row": 23,
                            "formula": "=F1",
                        }
                    ],
                },
            ],
        }
    }


@pytest.fixture
def mock_repo():
    return Mock()


class TestVisionPyGFrontendEndpoint:
    def test_public_endpoint_returns_period_centric_contract(self, minimal_pricing_result, mock_repo):
        mock_repo.get.return_value = minimal_pricing_result

        response = get_vision_pyg("sim-123", repo=mock_repo)
        data = response.data if hasattr(response, "data") else response

        assert data["version"] == "v1"
        assert data["simulation_id"] == "sim-123"
        assert "header" in data
        assert "periods" in data
        assert "totales" in data
        assert "metadata" in data

    def test_public_endpoint_uses_repo_simulation_id(self, minimal_pricing_result, mock_repo):
        mock_repo.get.return_value = minimal_pricing_result

        get_vision_pyg("sim-frontend", repo=mock_repo)
        mock_repo.get.assert_called_once_with("sim-frontend")

    def test_public_endpoint_raises_404_on_missing_result(self, mock_repo):
        mock_repo.get.side_effect = NotFoundError(
            resource="simulation",
            identifier="missing-id",
        )

        with pytest.raises(HTTPException) as exc_info:
            get_vision_pyg("missing-id", repo=mock_repo)

        assert exc_info.value.status_code == 404


class TestVisionPyGFrontendShape:
    def test_public_response_returns_period_children(self, minimal_pricing_result, mock_repo):
        mock_repo.get.return_value = minimal_pricing_result

        data = get_vision_pyg("sim-123", repo=mock_repo).data
        first_period = data["periods"][0]

        assert first_period["ingresos"]["ingreso_cadena_a"] == 1000.0
        assert first_period["costos"]["cadena_a"]["payroll"] == 500.0
        assert first_period["costos"]["cadena_b"]["total_cadena_b"] == 300.0
        assert first_period["costos"]["cadena_c"]["total_cadena_c"] == 200.0
        assert first_period["costos"]["componente_financiero"]["ica"] == 10.0
        assert first_period["utilidad"]["utilidad_neta"] == 0.0

    def test_public_response_returns_totales(self, minimal_pricing_result, mock_repo):
        mock_repo.get.return_value = minimal_pricing_result

        data = get_vision_pyg("sim-123", repo=mock_repo).data

        assert data["totales"]["ingresos"]["ingreso_cadena_a"] == 2100.0
        assert data["totales"]["costos"]["cadena_a"]["payroll"] == 500.0
        assert data["totales"]["costos"]["cadena_b"]["total_cadena_b"] == 630.0
        assert data["totales"]["costos"]["cadena_c"]["total_cadena_c"] == 420.0
        assert data["totales"]["costos"]["componente_financiero"]["ica"] == 10.0
        assert data["totales"]["utilidad"]["utilidad_neta"] == 0.0

    def test_public_response_does_not_expose_old_root_arrays(self, minimal_pricing_result, mock_repo):
        mock_repo.get.return_value = minimal_pricing_result

        data = get_vision_pyg("sim-123", repo=mock_repo).data

        assert "ingresos" not in data
        assert "costos" not in data
        assert "utilidad" not in data

    def test_public_response_does_not_expose_internal_row_fields(self, minimal_pricing_result, mock_repo):
        mock_repo.get.return_value = minimal_pricing_result

        data = get_vision_pyg("sim-123", repo=mock_repo).data

        assert not _contains_key(data, "excel_row")
        assert not _contains_key(data, "formula")
        assert not _contains_key(data, "seccion")
        assert not _contains_key(data, "signo")
        assert not _contains_key(data, "tipo")
        assert not _contains_key(data, "detalle")

    def test_null_fields_are_omitted_and_zero_values_are_preserved(self, minimal_pricing_result, mock_repo):
        mock_repo.get.return_value = minimal_pricing_result

        data = get_vision_pyg("sim-123", repo=mock_repo).data
        first_period = data["periods"][0]
        second_period = data["periods"][1]

        assert first_period["costos"]["componente_financiero"]["ica"] == 10.0
        assert "componente_financiero" not in second_period["costos"]
        assert second_period["costos"]["cadena_a"]["payroll"] == 0.0
        assert second_period["utilidad"]["utilidad_neta"] == 0.0

    def test_missing_vision_pyg_returns_empty_screen_contract(self, mock_repo):
        mock_repo.get.return_value = {}

        data = get_vision_pyg("sim-empty", repo=mock_repo).data

        assert data["version"] == "v1"
        assert data["simulation_id"] == "sim-empty"
        assert data["metadata"]["source"] == "persisted_pricing_result"


class TestVisionPyGFrontendDependencyGuardrail:
    def test_endpoint_has_no_excel_or_engine_runtime_dependency(self, minimal_pricing_result, mock_repo):
        mock_repo.get.return_value = minimal_pricing_result

        data = get_vision_pyg("sim-123", repo=mock_repo).data
        assert data["metadata"]["source"] == "persisted_pricing_result"
