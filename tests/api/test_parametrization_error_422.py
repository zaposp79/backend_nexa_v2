"""
HTTP integration tests for ENGINE_LOW_RISK_TESTS_01 — ParametrizationError handling.

Validates:
  - ParametrizationError during calculation is properly handled by HTTP layer
  - API returns appropriate error response (ideally 422 if applicable, else existing contract)
  - Error message is propagated to client
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from nexa_engine.app import create_app
from nexa_engine.modules.shared.exceptions import ParametrizationError


@pytest.fixture(scope="module")
def client():
    """TestClient over development app."""
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture(scope="module")
def canonical_request() -> dict:
    """Load the canonical V2-8 request.json for testing."""
    request_path = Path(__file__).resolve().parents[2] / "request" / "request.json"
    if not request_path.exists():
        pytest.skip(f"request.json not found at {request_path}")
    return json.loads(request_path.read_text(encoding="utf-8"))


def test_parametrization_error_in_engine_handling(client, canonical_request):
    """
    ParametrizationError during engine execution must be handled gracefully.

    When ParametrizationProvider fails (e.g., storage unavailable), the API should
    return a controlled error response instead of 500 Internal Server Error.
    """
    # Monkeypatch: Make ParametrizationProvider.get_v27_defaults() raise ParametrizationError
    # This simulates the scenario where OP storage is unavailable
    def _failing_get_v27_defaults():
        raise ParametrizationError(
            "OP parametrization provider failed in get_v27_defaults() — "
            "cannot resolve margen_b/margen_c/tasa_interes defaults",
            module="OP",
        )

    with patch(
        "nexa_engine.modules.parametrizacion.services.provider.ParametrizationProvider.get_v27_defaults",
        side_effect=_failing_get_v27_defaults,
    ):
        # POST to calculate endpoint with valid canonical request
        response = client.post(
            "/api/v1/simulation/calculate",
            json=canonical_request,
        )

        # Response should NOT be 500 (unhandled error)
        assert response.status_code != 500, (
            f"ParametrizationError should be handled gracefully, not as 500. Got {response.status_code}"
        )

        # Response should be a documented error (4xx range suggests client-provided context is part of issue)
        # 422 is typical for validation/precondition errors; 400 is also acceptable for bad state
        assert response.status_code in (400, 422), (
            f"Expected ParametrizationError to map to 400/422, got {response.status_code}. "
            f"Response: {response.json()}"
        )

        # Error response should follow ApiResponse contract
        body = response.json()
        assert "success" in body or "error" in body, (
            f"API error response missing success/error field. Got: {body}"
        )


def test_parametrization_error_provides_context_to_client(client, canonical_request):
    """
    When ParametrizationError occurs, the API response should include context about the failure.
    """
    def _failing_get_v27_defaults():
        raise ParametrizationError(
            "HR-rotacion_ausentismo sheet not found in uploaded Excel",
            module="HR",
        )

    with patch(
        "nexa_engine.modules.parametrizacion.services.provider.ParametrizationProvider.get_v27_defaults",
        side_effect=_failing_get_v27_defaults,
    ):
        response = client.post(
            "/api/v1/simulation/calculate",
            json=canonical_request,
        )

        # Response should map ParametrizationError to 422
        assert response.status_code == 422, (
            f"ParametrizationError should map to HTTP 422. Got {response.status_code}"
        )

        # Error response should follow API contract
        body = response.json()

        # Extract error message from response (could be in detail, error, message, etc.)
        error_info = str(body.get("detail") or body.get("error") or body.get("message") or json.dumps(body))

        # The error context should mention parametrization or failure context
        assert (
            "parametr" in error_info.lower()
            or "provider" in error_info.lower()
            or "failed" in error_info.lower()
        ), (
            f"Error response should include context about the failure. "
            f"Got: {error_info}"
        )


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
    return SimpleNamespace(simulation_id="sim-test-parametrization")


@contextmanager
def _patch_success_pipeline():
    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "nexa_engine.modules.calculator.api.calculate_normal_handler.SimulationContextBuilder.construir",
                return_value=_fake_request(),
            )
        )
        stack.enter_context(
            patch(
                "nexa_engine.modules.calculator.api.calculate_normal_handler.NexaPricingEngine.calcular",
                return_value=_fake_result(),
            )
        )
        stack.enter_context(
            patch(
                "nexa_engine.modules.calculator.api.calculate_normal_handler.validate_visions_complete",
                return_value=None,
            )
        )
        stack.enter_context(
            patch(
                "nexa_engine.modules.calculator.api.calculate_normal_handler.pricing_result_to_dict",
                return_value={"simulation_id": "sim-test-parametrization"},
            )
        )
        stack.enter_context(
            patch(
                "nexa_engine.modules.calculator.api.calculate_normal_handler._results_repo.save",
                return_value=None,
            )
        )
        stack.enter_context(
            patch(
                "nexa_engine.modules.calculator.api.calculate_normal_handler._trace_writer.write",
                return_value=None,
            )
        )
        stack.enter_context(
            patch(
                "nexa_engine.modules.calculator.api.calculate_normal_handler._snapshot_repo.save",
                return_value=None,
            )
        )
        yield


def test_valid_request_still_works(client, canonical_request):
    """
    Sanity check: normal requests still work after test setup.
    (ParametrizationError mocks should not persist between tests.)
    """
    with _patch_success_pipeline():
        response = client.post(
            "/api/v1/simulation/calculate",
            json=canonical_request,
        )

    # Should succeed (200) or at least not fail with 422 (unless request is malformed)
    assert response.status_code in (200, 201), (
        f"Normal request should succeed. Got {response.status_code}. "
        f"Response: {response.json() if response.text else '(no body)'}"
    )


__all__ = [
    "test_parametrization_error_in_engine_handling",
    "test_parametrization_error_provides_context_to_client",
    "test_valid_request_still_works",
]
