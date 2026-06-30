"""
Focused security tests for API_MEDIUM_RISK_FIXES_01.

Validates that the calculate endpoint (normal mode) does NOT expose:
  - panel_context or datos_operativos in ParametrizationError responses
  - str(exc), type, or module in ValueError responses
  - str(exc) or pipeline step names in VisionIncompleteError responses

All responses must use the ApiResponse envelope and contain only safe metadata.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from nexa_engine.app import create_app
from nexa_engine.modules.shared.exceptions import ParametrizationError
from nexa_engine.modules.calculator_motor.serializers import VisionIncompleteError


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture(scope="module")
def canonical_body() -> dict:
    request_path = Path(__file__).resolve().parents[2] / "request" / "request.json"
    if not request_path.exists():
        pytest.skip(f"request.json not found at {request_path}")
    return json.loads(request_path.read_text(encoding="utf-8"))


# ────────────────────────────────────────────────────────────────────────────
# Fix 1 — ParametrizationError
# ────────────────────────────────────────────────────────────────────────────

def _make_parametrization_error():
    raise ParametrizationError(
        "OP storage unavailable — cannot resolve defaults",
        module="OP",
    )


def test_parametrization_error_uses_api_response_envelope(client, canonical_body):
    with patch(
        "nexa_engine.modules.parametrizacion.services.provider.ParametrizationProvider.get_v27_defaults",
        side_effect=_make_parametrization_error,
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 422
    data = response.json()
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "PARAMETRIZATION_ERROR"


def test_parametrization_error_does_not_expose_panel_context(client, canonical_body):
    with patch(
        "nexa_engine.modules.parametrizacion.services.provider.ParametrizationProvider.get_v27_defaults",
        side_effect=_make_parametrization_error,
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 422
    body_text = response.text
    assert "panel_context" not in body_text, (
        f"panel_context leaked in ParametrizationError response: {body_text[:500]}"
    )


def test_parametrization_error_does_not_expose_datos_operativos(client, canonical_body):
    with patch(
        "nexa_engine.modules.parametrizacion.services.provider.ParametrizationProvider.get_v27_defaults",
        side_effect=_make_parametrization_error,
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 422
    body_text = response.text
    assert "datos_operativos" not in body_text, (
        f"datos_operativos leaked in ParametrizationError response: {body_text[:500]}"
    )


def test_parametrization_error_does_not_expose_user_input(client, canonical_body):
    with patch(
        "nexa_engine.modules.parametrizacion.services.provider.ParametrizationProvider.get_v27_defaults",
        side_effect=_make_parametrization_error,
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 422
    data = response.json()
    details = (data.get("error") or {}).get("details") or {}
    forbidden = {"panel_context", "datos_operativos", "user_input", "request", "body"}
    leaked = forbidden & set(details.keys())
    assert not leaked, f"User input fields leaked in ParametrizationError details: {leaked}"


# ────────────────────────────────────────────────────────────────────────────
# Fix 2 — ValueError
# ────────────────────────────────────────────────────────────────────────────

_VALUE_ERROR_SENTINEL = "SECRET_INTERNAL_FIELD_PATH_XK9"


def test_value_error_uses_api_response_envelope(client, canonical_body):
    with patch(
        "nexa_engine.modules.calculator_motor.adapters.user_input_loader.UserInputLoader.cargar_desde_dict",
        side_effect=ValueError(_VALUE_ERROR_SENTINEL),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 422
    data = response.json()
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "INPUT_ERROR"


def test_value_error_does_not_expose_str_exc(client, canonical_body):
    with patch(
        "nexa_engine.modules.calculator_motor.adapters.user_input_loader.UserInputLoader.cargar_desde_dict",
        side_effect=ValueError(_VALUE_ERROR_SENTINEL),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 422
    assert _VALUE_ERROR_SENTINEL not in response.text, (
        f"ValueError str(exc) leaked into response: {response.text[:500]}"
    )


def test_value_error_does_not_expose_type_or_module(client, canonical_body):
    with patch(
        "nexa_engine.modules.calculator_motor.adapters.user_input_loader.UserInputLoader.cargar_desde_dict",
        side_effect=ValueError("any"),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 422
    data = response.json()
    details = (data.get("error") or {}).get("details") or {}
    assert "type" not in details, f"'type' exposed in ValueError details: {details}"
    assert "module" not in details, f"'module' exposed in ValueError details: {details}"
    assert "panel_context" not in details, f"'panel_context' exposed in ValueError details: {details}"


def test_value_error_uses_safe_generic_message(client, canonical_body):
    with patch(
        "nexa_engine.modules.calculator_motor.adapters.user_input_loader.UserInputLoader.cargar_desde_dict",
        side_effect=ValueError("any internal detail"),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["message"] == "Error en datos de entrada."


# ────────────────────────────────────────────────────────────────────────────
# Fix 3 — VisionIncompleteError
# ────────────────────────────────────────────────────────────────────────────

_PIPELINE_STEP_NAME = "pyg_por_mes vacío — PyGCalculator no ejecutó"


def _fake_request():
    panel = SimpleNamespace(
        cliente="Test Client",
        tipo_cliente="BPO",
        linea_negocio="SAC",
        ciudad="Bogota",
        fecha_inicio="2026-01-01",
        meses_contrato=12,
        margen=0.2,
    )
    return SimpleNamespace(
        panel=panel,
        perfiles_cadena_a=[],
        polizas_usuario=None,
    )


def _fake_result():
    return SimpleNamespace(simulation_id="sim-test-medium-risk")


@contextmanager
def _patch_vision_incomplete_pipeline():
    with patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.SimulationContextBuilder.construir",
        return_value=_fake_request(),
    ), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.NexaPricingEngine.calcular",
        return_value=_fake_result(),
    ):
        yield


def test_vision_incomplete_uses_api_response_envelope(client, canonical_body):
    with _patch_vision_incomplete_pipeline(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.validate_visions_complete",
        side_effect=VisionIncompleteError(_PIPELINE_STEP_NAME),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    data = response.json()
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "VISION_INCOMPLETE"


def test_vision_incomplete_does_not_expose_str_exc(client, canonical_body):
    with _patch_vision_incomplete_pipeline(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.validate_visions_complete",
        side_effect=VisionIncompleteError(_PIPELINE_STEP_NAME),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    assert _PIPELINE_STEP_NAME not in response.text, (
        f"VisionIncompleteError str(exc) leaked: {response.text[:500]}"
    )


def test_vision_incomplete_does_not_expose_pipeline_step_names(client, canonical_body):
    step_names = ["PyGCalculator", "KPIsCalculator", "NominaCalculator", "no ejecutó"]
    with _patch_vision_incomplete_pipeline(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.validate_visions_complete",
        side_effect=VisionIncompleteError("KPIsCalculator no ejecutó — vision vacía"),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    body_text = response.text
    for name in step_names:
        assert name not in body_text, (
            f"Pipeline step name '{name}' leaked in VisionIncompleteError response"
        )


def test_vision_incomplete_uses_safe_generic_message(client, canonical_body):
    with _patch_vision_incomplete_pipeline(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.validate_visions_complete",
        side_effect=VisionIncompleteError(_PIPELINE_STEP_NAME),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    data = response.json()
    assert data["error"]["message"] == "Error interno: resultado de cálculo incompleto."
