"""Unit tests for the period-centric vision_pyg screen mapper."""
from __future__ import annotations

from typing import Any

import pytest

from nexa_engine.modules.vision_pyg.helpers.screen_mapper import (
    build_vision_pyg_from_result,
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
def fake_persisted_result():
    return {
        "vision_pyg": {
            "resumen": {
                "cliente": "Test Client",
                "tipo_cliente": "GRANDE",
                "linea_negocio": "Outsourcing",
                "periodo_pago_dias": 30,
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
                            "excel_row": 10,
                            "formula": "=A1",
                        },
                        {
                            "key": "ingreso_neto",
                            "label": "Ingreso Neto",
                            "valores": [900.0, None],
                            "acumulado": 900.0,
                            "excel_row": 11,
                            "formula": "=B1",
                        },
                    ],
                },
                {
                    "key": "costos_op",
                    "filas": [
                        {
                            "key": "payroll_a",
                            "label": "Payroll A",
                            "valores": [200.0, 0.0],
                            "acumulado": 200.0,
                            "excel_row": 20,
                            "formula": "=C1",
                        },
                        {
                            "key": "costo_b",
                            "label": "Costo B",
                            "valores": [300.0, 330.0],
                            "acumulado": 630.0,
                            "excel_row": 21,
                            "formula": "=D1",
                        },
                        {
                            "key": "costo_c",
                            "label": "Costo C",
                            "valores": [400.0, 440.0],
                            "acumulado": 840.0,
                            "excel_row": 22,
                            "formula": "=E1",
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
                            "excel_row": 30,
                            "formula": "=F1",
                        }
                    ],
                },
                {
                    "key": "resultados",
                    "filas": [
                        {
                            "key": "utilidad_neta",
                            "label": "Utilidad Neta",
                            "valores": [50.0, 0.0],
                            "acumulado": 50.0,
                            "excel_row": 40,
                            "formula": "=G1",
                        }
                    ],
                },
            ],
        }
    }


class TestScreenMapperPeriodContract:
    def test_returns_required_root_fields(self, fake_persisted_result):
        contract = build_vision_pyg_from_result(fake_persisted_result, simulation_id="sim-123")

        assert contract["version"] == "v1"
        assert contract["simulation_id"] == "sim-123"
        assert contract["header"]["cliente"] == "Test Client"
        assert contract["metadata"]["source"] == "persisted_pricing_result"
        assert contract["metadata"]["omitted_empty_fields"] is True
        assert "periods" in contract
        assert "totales" in contract

    def test_maps_periods_to_period_centric_shape(self, fake_persisted_result):
        contract = build_vision_pyg_from_result(fake_persisted_result)
        first_period = contract["periods"][0]

        assert first_period["index"] == 1
        assert first_period["label"] == "2026-07-01"
        assert first_period["periodo"] == 1
        assert first_period["mes"] == 7
        assert first_period["anio"] == 2026
        assert first_period["ingresos"]["ingreso_cadena_a"] == 1000.0
        assert first_period["ingresos"]["ingreso_neto"] == 900.0
        assert first_period["costos"]["cadena_a"]["payroll"] == 200.0
        assert first_period["costos"]["cadena_b"]["total_cadena_b"] == 300.0
        assert first_period["costos"]["cadena_c"]["total_cadena_c"] == 400.0
        assert first_period["costos"]["componente_financiero"]["ica"] == 10.0
        assert first_period["utilidad"]["utilidad_neta"] == 50.0

    def test_maps_totales_from_acumulado(self, fake_persisted_result):
        contract = build_vision_pyg_from_result(fake_persisted_result)

        assert contract["totales"]["ingresos"]["ingreso_cadena_a"] == 2100.0
        assert contract["totales"]["ingresos"]["ingreso_neto"] == 900.0
        assert contract["totales"]["costos"]["cadena_a"]["payroll"] == 200.0
        assert contract["totales"]["costos"]["cadena_b"]["total_cadena_b"] == 630.0
        assert contract["totales"]["costos"]["cadena_c"]["total_cadena_c"] == 840.0
        assert contract["totales"]["costos"]["componente_financiero"]["ica"] == 10.0
        assert contract["totales"]["utilidad"]["utilidad_neta"] == 50.0

    def test_forbidden_raw_fields_are_absent_everywhere(self, fake_persisted_result):
        contract = build_vision_pyg_from_result(fake_persisted_result)

        assert "ingresos" not in contract
        assert "costos" not in contract
        assert "utilidad" not in contract
        assert "fechas_meses" not in contract
        assert "secciones" not in contract
        assert not _contains_key(contract, "excel_row")
        assert not _contains_key(contract, "formula")


class TestScreenMapperPruning:
    def test_null_fields_are_omitted_and_zero_values_are_preserved(self, fake_persisted_result):
        contract = build_vision_pyg_from_result(fake_persisted_result)
        first_period = contract["periods"][0]
        second_period = contract["periods"][1]

        assert first_period["costos"]["componente_financiero"]["ica"] == 10.0
        assert "componente_financiero" not in second_period["costos"]
        assert second_period["costos"]["cadena_a"]["payroll"] == 0.0
        assert second_period["utilidad"]["utilidad_neta"] == 0.0
        assert "ingreso_neto" not in second_period["ingresos"]

    def test_omits_empty_period_children(self):
        result = {
            "vision_pyg": {
                "resumen": {"cliente": "Test", "meses_contrato": 1, "periodo_pago_dias": 0},
                "fechas_meses": ["2026-01-01"],
                "secciones": [
                    {
                        "key": "ingresos",
                        "filas": [
                            {
                                "key": "ingreso_neto",
                                "valores": [None],
                                "acumulado": None,
                            }
                        ],
                    }
                ],
            }
        }

        contract = build_vision_pyg_from_result(result)

        assert contract["header"]["periodo_pago"] == 0
        assert contract["periods"][0]["label"] == "2026-01-01"
        assert "ingresos" not in contract["periods"][0]
        assert "totales" not in contract or "ingresos" not in contract.get("totales", {})


class TestScreenMapperCompatibility:
    def test_supports_flat_filas_shape_as_fallback(self):
        result = {
            "vision_pyg": {
                "resumen": {"cliente": "Flat"},
                "fechas_meses": ["2026-01-01"],
                "filas": [
                    {
                        "key": "ingreso_bruto",
                        "label": "Ingreso Bruto",
                        "seccion": "ingresos",
                        "valores": [0.0],
                        "acumulado": 0.0,
                        "excel_row": 10,
                        "formula": "=A1",
                    }
                ],
            }
        }

        contract = build_vision_pyg_from_result(result)

        assert contract["header"]["cliente"] == "Flat"
        assert contract["periods"][0]["ingresos"]["ingreso_bruto"] == 0.0
        assert contract["totales"]["ingresos"]["ingreso_bruto"] == 0.0
        assert not _contains_key(contract, "excel_row")
        assert not _contains_key(contract, "formula")

    def test_handles_none_and_missing_vision_pyg(self):
        assert build_vision_pyg_from_result(None)["version"] == "v1"
        assert build_vision_pyg_from_result({})["version"] == "v1"
        assert build_vision_pyg_from_result({"other_key": "value"})["version"] == "v1"


class TestScreenMapperNoRuntimeDependency:
    def test_no_provider_engine_or_excel_dependency(self, fake_persisted_result):
        contract = build_vision_pyg_from_result(fake_persisted_result)
        assert contract["metadata"]["source"] == "persisted_pricing_result"
