"""Contrato HTTP para endpoints de parámetros Panel/Cadenas."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import backend_nexa  # noqa: F401 - registra el alias runtime nexa_engine
from nexa_engine.app import create_app
from nexa_engine.db.dependencies import (
    get_cadena_a_parameters_service,
    get_cadena_b_parameters_service,
    get_cadena_c_parameters_service,
    get_panel_service,
)
from nexa_engine.modules.shared.config.app_settings import AppSettings


PARAMETROS_ENDPOINTS = (
    (
        "/api/v1/simulation/input/panel/parametros",
        "ParametrosPanel",
        ("datos_operativos", "polizas", "reglas_negocio"),
        get_panel_service,
        "build_parametros",
    ),
    (
        "/api/v1/simulation/input/chain-a/parametros",
        "ParametrosCadenaA",
        ("ratios", "opex_fijo", "hardware_software"),
        get_cadena_a_parameters_service,
        "get_active_parameters",
    ),
    (
        "/api/v1/simulation/input/chain-b/parametros",
        "ParametrosCadenaB",
        ("dispositivos_requeridos", "equipo_hitl"),
        get_cadena_b_parameters_service,
        "get_active_parameters",
    ),
    (
        "/api/v1/simulation/input/chain-c/parametros",
        "ParametrosCadenaC",
        ("dispositivos_requeridos", "equipo_hitl"),
        get_cadena_c_parameters_service,
        "get_active_parameters",
    ),
)


def _test_settings() -> AppSettings:
    return AppSettings(
        app_env="test",
        cors_allowed_origins=("http://testserver",),
        docs_enabled=True,
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


@pytest.fixture()
def client() -> TestClient:
    with TestClient(create_app(settings=_test_settings())) as test_client:
        yield test_client


class FailingParametersService:
    def build_parametros(self):
        raise RuntimeError("forced parametrization failure")

    def get_active_parameters(self):
        raise RuntimeError("forced parametrization failure")


@pytest.mark.parametrize(
    ("path", "schema_name", "required_keys", "dependency", "method_name"),
    PARAMETROS_ENDPOINTS,
    ids=("panel", "chain-a", "chain-b", "chain-c"),
)
def test_parametros_success_payload_is_unwrapped(
    client: TestClient,
    path: str,
    schema_name: str,
    required_keys: tuple[str, ...],
    dependency,
    method_name: str,
) -> None:
    response = client.get(path)

    assert response.status_code == 200, response.text
    payload = response.json()
    for key in required_keys:
        assert key in payload
    assert "success" not in payload
    assert "error" not in payload


@pytest.mark.parametrize(
    ("path", "schema_name", "required_keys", "dependency", "method_name"),
    PARAMETROS_ENDPOINTS,
    ids=("panel", "chain-a", "chain-b", "chain-c"),
)
def test_parametros_error_uses_api_response_shape_without_response_validation_error(
    path: str,
    schema_name: str,
    required_keys: tuple[str, ...],
    dependency,
    method_name: str,
) -> None:
    app = create_app(settings=_test_settings())
    app.dependency_overrides[dependency] = lambda: FailingParametersService()

    with TestClient(app) as test_client:
        response = test_client.get(path)

    assert response.status_code == 500
    assert response.json() == {
        "success": False,
        "data": None,
        "error": {
            "code": "PARAMETRIZATION_ERROR",
            "message": "forced parametrization failure",
            "field": None,
            "details": None,
        },
        "meta": None,
    }


@pytest.mark.parametrize(
    ("path", "schema_name", "required_keys", "dependency", "method_name"),
    PARAMETROS_ENDPOINTS,
    ids=("panel", "chain-a", "chain-b", "chain-c"),
)
def test_parametros_openapi_keeps_success_model_and_documents_500(
    path: str,
    schema_name: str,
    required_keys: tuple[str, ...],
    dependency,
    method_name: str,
) -> None:
    app = create_app(settings=_test_settings())
    schema = app.openapi()
    responses = schema["paths"][path]["get"]["responses"]

    assert responses["200"]["content"]["application/json"]["schema"] == {
        "$ref": f"#/components/schemas/{schema_name}"
    }
    assert responses["500"]["description"] == "Parametrization error"
