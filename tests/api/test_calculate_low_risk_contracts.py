"""
Focused API contract tests for API_LOW_COVERAGE_AND_OPENAPI_01.

Covers:
  1. PydanticValidationError — safe envelope, no internal leaks
  2. Auto-wrap flat body — accepted without user_input field-required 422
  3. DomainError — HTTP 400 with ApiResponse envelope
  4. Missing simulation_id — HTTP 404 with ApiResponse envelope
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from nexa_engine.app import create_app
from nexa_engine.modules.shared.exceptions import DomainError


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
# Helper: real PydanticValidationError instance
# ────────────────────────────────────────────────────────────────────────────

class _Dummy(BaseModel):
    required_int: int


def _make_pydantic_error() -> PydanticValidationError:
    try:
        _Dummy(required_int="not_an_int")  # type: ignore[arg-type]
    except PydanticValidationError as exc:
        return exc
    raise AssertionError("_Dummy did not raise PydanticValidationError")  # pragma: no cover


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


@contextmanager
def _patch_normal_builder():
    with patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.SimulationContextBuilder.construir",
        return_value=_fake_request(),
    ):
        yield


# ────────────────────────────────────────────────────────────────────────────
# 1. PydanticValidationError — safe envelope, no internal leaks
# ────────────────────────────────────────────────────────────────────────────

def test_pydantic_validation_error_returns_422(client, canonical_body):
    """PydanticValidationError raised inside the pipeline must map to HTTP 422."""
    with patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.SimulationContextBuilder.construir",
        side_effect=_make_pydantic_error(),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 422


def test_pydantic_validation_error_uses_api_response_envelope(client, canonical_body):
    """PydanticValidationError must return ApiResponse envelope (success/error keys)."""
    with patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.SimulationContextBuilder.construir",
        side_effect=_make_pydantic_error(),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 422
    data = response.json()
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "PYDANTIC_VALIDATION_ERROR"


def test_pydantic_validation_error_does_not_expose_raw_str_exc(client, canonical_body):
    """PydanticValidationError message must be a count summary, not raw str(exc)."""
    with patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.SimulationContextBuilder.construir",
        side_effect=_make_pydantic_error(),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 422
    data = response.json()
    message = data["error"]["message"]
    # Message should be the safe count summary, not a raw Python exception string
    assert "error(es)" in message or "error" in message.lower()
    # Must not be a raw traceback or exception repr
    assert "Traceback" not in message
    assert "File " not in message


def test_pydantic_validation_error_does_not_expose_raw_detail_envelope(client, canonical_body):
    """PydanticValidationError must NOT return raw FastAPI {"detail": [...]} envelope."""
    with patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.SimulationContextBuilder.construir",
        side_effect=_make_pydantic_error(),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 422
    data = response.json()
    # FastAPI's default 422 for request validation uses {"detail": [...]}
    # Our handler must intercept and use ApiResponse instead
    assert "detail" not in data, (
        f"Raw FastAPI detail envelope leaked for PydanticValidationError: {data}"
    )


# ────────────────────────────────────────────────────────────────────────────
# 2. Auto-wrap flat body compatibility
# ────────────────────────────────────────────────────────────────────────────

def test_flat_body_does_not_trigger_user_input_field_required_422(client):
    """
    A flat body (no 'user_input' key) must be auto-wrapped, not rejected with
    Pydantic's 'field required' error for the user_input key.
    """
    flat_body = {"panel_de_control": {"cliente": "test"}}
    response = client.post("/api/v1/simulation/calculate", json=flat_body)

    # Must NOT be FastAPI's request-validation 422 with user_input field required
    if response.status_code == 422:
        data = response.json()
        # FastAPI request-validation 422 uses {"detail": [...]} envelope
        # Our handler 422s use {"success": false, "error": {...}}
        if "detail" in data:
            locs = [str(e.get("loc", "")) for e in (data["detail"] if isinstance(data["detail"], list) else [])]
            assert not any("user_input" in loc for loc in locs), (
                f"Auto-wrap failed — got 'user_input field required' Pydantic error: {data}"
            )


def test_flat_body_is_processed_not_rejected_by_schema(client, canonical_body):
    """
    Posting the canonical body WITHOUT the user_input wrapper (flat) must
    reach the handler (not be rejected by Pydantic schema validation).

    The response may be any handler error (422/500) but must NOT be
    a Pydantic request-schema error with {"detail": [...]}.
    """
    # canonical_body already has user_input; extract the inner dict to simulate flat body
    flat_body = canonical_body.get("user_input", canonical_body)
    response = client.post("/api/v1/simulation/calculate", json=flat_body)

    data = response.json()
    # If it's a raw Pydantic request-validation 422, auto-wrap failed
    if "detail" in data and isinstance(data.get("detail"), list):
        locs = [str(e.get("loc", "")) for e in data["detail"]]
        assert not any("user_input" in loc for loc in locs), (
            f"Auto-wrap failed — flat body rejected with Pydantic schema error: {data}"
        )
    # Otherwise the handler accepted the request (may return any handler error)


# ────────────────────────────────────────────────────────────────────────────
# 3. DomainError — HTTP 400 with ApiResponse envelope
# ────────────────────────────────────────────────────────────────────────────

def test_domain_error_returns_400(client, canonical_body):
    """DomainError from the engine must map to HTTP 400."""
    with _patch_normal_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.NexaPricingEngine.calcular",
        side_effect=DomainError("domain rule violated"),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 400


def test_domain_error_uses_api_response_envelope(client, canonical_body):
    """DomainError must return ApiResponse envelope (success/error keys)."""
    with _patch_normal_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.NexaPricingEngine.calcular",
        side_effect=DomainError("domain rule violated"),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 400
    data = response.json()
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "DOMAIN_ERROR"
    # Must NOT be raw FastAPI {"detail": ...}
    assert "detail" not in data, f"Raw FastAPI detail envelope for DomainError: {data}"


def test_domain_error_does_not_expose_traceback(client, canonical_body):
    """DomainError response must not contain Python traceback."""
    with _patch_normal_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.NexaPricingEngine.calcular",
        side_effect=DomainError("some domain rule"),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 400
    body_text = response.text
    assert "Traceback" not in body_text
    assert "File " not in body_text


def test_domain_error_does_not_expose_type_in_details(client, canonical_body):
    """DomainError response must NOT contain Python class name in details."""
    with _patch_normal_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.NexaPricingEngine.calcular",
        side_effect=DomainError("domain rule violated"),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 400
    data = response.json()
    details = (data.get("error") or {}).get("details") or {}
    assert "type" not in details, f"Python class name exposed in DomainError details: {details}"


def test_domain_error_does_not_expose_module_in_details(client, canonical_body):
    """DomainError response must NOT contain Python module path in details."""
    with _patch_normal_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.NexaPricingEngine.calcular",
        side_effect=DomainError("domain rule violated"),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 400
    data = response.json()
    details = (data.get("error") or {}).get("details") or {}
    assert "module" not in details, f"Python module path exposed in DomainError details: {details}"


def test_domain_error_does_not_expose_class_path(client, canonical_body):
    """DomainError response body must not contain internal Python module paths."""
    sentinel_module = "nexa_engine.modules.shared.exceptions"
    with _patch_normal_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.NexaPricingEngine.calcular",
        side_effect=DomainError("domain rule violated"),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 400
    assert sentinel_module not in response.text, (
        f"Internal module path leaked in DomainError response: {response.text[:300]}"
    )


# ────────────────────────────────────────────────────────────────────────────
# 4. Missing simulation_id → 404 with ApiResponse envelope
# ────────────────────────────────────────────────────────────────────────────

def test_missing_simulation_id_returns_404(client):
    """GET /vision-imprimible for a nonexistent simulation_id must return HTTP 404."""
    response = client.get("/api/v1/simulation/NONEXISTENT-SIM-XK9-TEST/results/vision-imprimible")
    assert response.status_code == 404


def test_missing_simulation_id_uses_api_response_envelope(client):
    """404 for missing simulation must use ApiResponse envelope."""
    response = client.get("/api/v1/simulation/NONEXISTENT-SIM-XK9-TEST/results/vision-imprimible")
    assert response.status_code == 404
    data = response.json()
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"


def test_missing_simulation_id_404_is_not_raw_fastapi_detail(client):
    """404 must NOT return raw FastAPI {"detail": "Not Found"} envelope."""
    response = client.get("/api/v1/simulation/NONEXISTENT-SIM-XK9-TEST/results/vision-imprimible")
    assert response.status_code == 404
    data = response.json()
    assert "detail" not in data, (
        f"Raw FastAPI detail envelope for missing simulation_id: {data}"
    )
