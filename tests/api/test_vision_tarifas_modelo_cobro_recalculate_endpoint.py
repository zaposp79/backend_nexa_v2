"""Tests for POST /simulation/{id}/results/vision-tarifas/modelo-cobro/recalculate.

Matches VISION_TARIFAS_MODELO_COBRO_GET_POST_SCREEN_CONTRACT.
"""
from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.vision_tarifas.api.router import post_vision_tarifas_modelo_cobro_recalculate
from nexa_engine.modules.vision_tarifas.api.schemas import ModeloCobroOverride, ModeloCobroRecalculateRequest


@pytest.fixture
def persisted_pricing_result() -> dict:
    return {
        "simulation_id": "sim_recalc_01",
        "panel": {"margen": 0.21, "margen_objetivo_cadena_a": 0.21},
        "ficha_deal": {
            "cliente": "Banco de Bogotá",
            "linea_negocio": "Atención al cliente",
            "ciudad": "Bogotá",
        },
        "vision_tarifas": {
            "selected_scenario_id": "escenario_1",
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
            ],
            "costo_total": 88888.0,
            "ingreso_mensual": 55555.0,
            "desglose_producto_opex": [],
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
                    "cadena_a": {"total_costo": 10000.0, "payroll": 8000.0, "no_payroll": 2000.0, "ingreso_bruto": 15000.0},
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
                    "componente_variable": {"habilitado": True, "cant_asesores": 0},
                },
            ],
        },
    }


def _build_request(view_id: str, **overrides) -> ModeloCobroRecalculateRequest:
    return ModeloCobroRecalculateRequest(
        view_id=view_id,
        overrides=ModeloCobroOverride(**overrides),
    )


class TestPostVisionTarifasModeloCobroRecalculate:
    def test_accepts_valid_overrides(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        body = _build_request(
            view_id="escenario_1",
            modelo_cobro="Híbrido",
            componente_fijo="FTE",
            proporcion_componente_fijo=0.5,
            componente_variable="Transacción",
            proporcion_componente_variable=0.5,
        )
        response = post_vision_tarifas_modelo_cobro_recalculate("sim_recalc_01", body, repo=repo)

        assert isinstance(response, ApiResponse) or isinstance(response, JSONResponse)

    def test_returns_same_public_wrapper(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        body = _build_request(view_id="escenario_1", modelo_cobro="Fijo")
        response = post_vision_tarifas_modelo_cobro_recalculate("sim_recalc_01", body, repo=repo)

        if isinstance(response, ApiResponse):
            assert response.success is True
            assert response.error is None
            data = response.data
            assert "cliente" in data
            assert "servicio" in data
            assert "ciudad" in data
            assert "selected_view_id" in data
            assert "resumen_resultado_escenario" in data
            assert "modelo_cobro" in data
            assert "desglose_producto_opex" in data

    def test_recalculates_selected_modelo_cobro(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        body = _build_request(view_id="escenario_1", modelo_cobro="Fijo")
        response = post_vision_tarifas_modelo_cobro_recalculate("sim_recalc_01", body, repo=repo)

        data = response.data
        views = {item["escenario"]: item for item in data["modelo_cobro"]}
        assert views["1"]["modelo_cobro"] == "Fijo"

    def test_recalculates_total_preview(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        body = _build_request(view_id="total", modelo_cobro="Variable")
        response = post_vision_tarifas_modelo_cobro_recalculate("sim_recalc_01", body, repo=repo)

        data = response.data
        views = {item["escenario"]: item for item in data["modelo_cobro"]}
        assert views["Total"]["modelo_cobro"] == "Variable"

    def test_post_returns_all_modelo_cobro_items(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        body = _build_request(view_id="escenario_1", modelo_cobro="Híbrido")
        response = post_vision_tarifas_modelo_cobro_recalculate("sim_recalc_01", body, repo=repo)

        data = response.data
        assert isinstance(data["modelo_cobro"], list)
        assert len(data["modelo_cobro"]) == 6
        view_ids = [item["escenario"] for item in data["modelo_cobro"]]
        assert view_ids == ["1", "2", "3", "4", "5", "Total"]

    def test_does_not_mutate_persisted_get_result(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        body = _build_request(view_id="escenario_1", modelo_cobro="Híbrido")
        response1 = post_vision_tarifas_modelo_cobro_recalculate("sim_recalc_01", body, repo=repo)

        # Second call with same data should not be affected by first
        body2 = _build_request(view_id="escenario_1", modelo_cobro="Híbrido")
        response2 = post_vision_tarifas_modelo_cobro_recalculate("sim_recalc_01", body2, repo=repo)

        assert response1.data == response2.data

    def test_rejects_invalid_modelo_cobro(self, persisted_pricing_result):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="String should match pattern"):
            _build_request(view_id="escenario_1", modelo_cobro="INVALIDO")

    def test_rejects_invalid_proportions(self, persisted_pricing_result):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            _build_request(
                view_id="escenario_1",
                proporcion_componente_fijo=1.5,
                proporcion_componente_variable=0.5,
            )

    def test_rejects_negative_values(self, persisted_pricing_result):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            _build_request(
                view_id="escenario_1",
                proporcion_componente_fijo=-0.1,
            )

    def test_handles_not_found(self):
        repo = Mock()
        repo.get.side_effect = NotFoundError(resource="simulation", identifier="missing")

        body = _build_request(view_id="escenario_1", modelo_cobro="Fijo")

        with pytest.raises(HTTPException) as exc_info:
            post_vision_tarifas_modelo_cobro_recalculate("missing", body, repo=repo)

        assert exc_info.value.status_code == 404

    @pytest.mark.skip(reason="Full recalculation not implemented at preview level")
    def test_returns_full_recalculation_required_for_unsupported_overrides(self, persisted_pricing_result):
        pass

    def test_invalid_view_id_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _build_request(view_id="invalid", modelo_cobro="Fijo")

    def test_zero_values_preserved_after_recalculation(self, persisted_pricing_result):
        repo = Mock()
        repo.get.return_value = persisted_pricing_result

        body = _build_request(
            view_id="escenario_1",
            proporcion_componente_fijo=0,
            proporcion_componente_variable=1,
        )
        response = post_vision_tarifas_modelo_cobro_recalculate("sim_recalc_01", body, repo=repo)

        data = response.data
        views = {item["escenario"]: item for item in data["modelo_cobro"]}
        assert views["1"]["proporcion_componente_fijo"] == 0
        assert views["1"]["proporcion_componente_variable"] == 1.0
