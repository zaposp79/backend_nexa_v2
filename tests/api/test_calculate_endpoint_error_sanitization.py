"""
Focused security tests for API_HIGH_RISK_FIXES_01.

Validates that the calculate endpoint (normal and certified modes) does NOT:
  - expose str(exc) in HTTP response payloads
  - expose exception_type / exception_module in HTTP response payloads
  - return raw FastAPI {"detail": ...} envelope for errors in certified mode

All error responses must use the ApiResponse envelope.
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
# Normal handler — catch-all 500
# ────────────────────────────────────────────────────────────────────────────

class _BoomError(RuntimeError):
    """Unique sentinel so we can assert it never leaks to the client."""


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
    return SimpleNamespace(simulation_id="sim-test-sanitized")


@contextmanager
def _patch_normal_builder():
    with patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.SimulationContextBuilder.construir",
        return_value=_fake_request(),
    ):
        yield


@contextmanager
def _patch_certified_builder():
    with patch(
        "nexa_engine.modules.calculator.api.calculate_certified_handler.SimulationContextBuilder.construir",
        return_value=_fake_request(),
    ):
        yield


@contextmanager
def _patch_audit_integrity_pipeline():
    with ExitStack() as stack:
        stack.enter_context(_patch_normal_builder())
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
                return_value={"simulation_id": "sim-test-sanitized"},
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
        yield


def test_normal_catchall_500_does_not_expose_str_exc(client, canonical_body):
    """Catch-all 500 message must NOT contain the raw exception string."""
    sentinel = "BOOM_SENTINEL_XK9_LEAKCHECK"
    with _patch_normal_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.NexaPricingEngine.calcular",
        side_effect=_BoomError(sentinel),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    body_text = response.text
    assert sentinel not in body_text, (
        f"str(exc) leaked into 500 response: {body_text[:500]}"
    )


def test_normal_catchall_500_does_not_expose_exception_type(client, canonical_body):
    """Catch-all 500 response must NOT contain exception_type field."""
    with _patch_normal_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.NexaPricingEngine.calcular",
        side_effect=_BoomError("any"),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    data = response.json()
    error_details = (data.get("error") or {}).get("details") or {}
    assert "exception_type" not in error_details, (
        f"exception_type exposed in 500 details: {error_details}"
    )


def test_normal_catchall_500_does_not_expose_exception_module(client, canonical_body):
    """Catch-all 500 response must NOT contain exception_module field."""
    with _patch_normal_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.NexaPricingEngine.calcular",
        side_effect=_BoomError("any"),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    data = response.json()
    error_details = (data.get("error") or {}).get("details") or {}
    assert "exception_module" not in error_details, (
        f"exception_module exposed in 500 details: {error_details}"
    )


def test_normal_catchall_500_uses_api_response_envelope(client, canonical_body):
    """Catch-all 500 must return ApiResponse envelope (success/error keys)."""
    with _patch_normal_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler.NexaPricingEngine.calcular",
        side_effect=_BoomError("any"),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    data = response.json()
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "INTERNAL_ERROR"
    assert data["error"]["message"] == "Error inesperado en el servidor."


# ────────────────────────────────────────────────────────────────────────────
# Certified handler — error envelope
# ────────────────────────────────────────────────────────────────────────────

def test_certified_unexpected_error_uses_api_response_envelope(client, canonical_body):
    """Certified mode 500 must return ApiResponse envelope, not raw {"detail": ...}."""
    sentinel = "CERTIFIED_BOOM_SENTINEL_XK9"
    with _patch_certified_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_certified_handler.NexaPricingEngine.calcular",
        side_effect=RuntimeError(sentinel),
    ):
        response = client.post(
            "/api/v1/simulation/calculate?mode=certified", json=canonical_body
        )

    assert response.status_code == 500
    data = response.json()
    # Must NOT be raw FastAPI {"detail": ...}
    assert "detail" not in data, (
        f"Certified 500 returned raw FastAPI detail envelope: {data}"
    )
    assert "success" in data
    assert data["success"] is False
    assert "error" in data


def test_certified_unexpected_error_does_not_expose_str_exc(client, canonical_body):
    """Certified mode 500 must NOT expose raw exception string in response."""
    sentinel = "CERTIFIED_BOOM_SENTINEL_XK9_LEAK"
    with _patch_certified_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_certified_handler.NexaPricingEngine.calcular",
        side_effect=RuntimeError(sentinel),
    ):
        response = client.post(
            "/api/v1/simulation/calculate?mode=certified", json=canonical_body
        )

    assert response.status_code == 500
    assert sentinel not in response.text, (
        f"str(exc) leaked into certified 500 response: {response.text[:500]}"
    )


def test_certified_domain_error_uses_api_response_envelope(client, canonical_body):
    """Certified mode 422 (DomainError) must return ApiResponse envelope."""
    from nexa_engine.modules.shared.exceptions import DomainError

    with _patch_certified_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_certified_handler.NexaPricingEngine.calcular",
        side_effect=DomainError("domain rule violated"),
    ):
        response = client.post(
            "/api/v1/simulation/calculate?mode=certified", json=canonical_body
        )

    assert response.status_code == 422
    data = response.json()
    assert "detail" not in data, (
        f"Certified 422 returned raw FastAPI detail envelope: {data}"
    )
    assert "success" in data
    assert data["success"] is False
    assert "error" in data


def test_certified_domain_error_does_not_expose_str_exc(client, canonical_body):
    """Certified mode 422 must NOT expose raw DomainError string in response."""
    from nexa_engine.modules.shared.exceptions import DomainError

    sentinel = "DOMAIN_SECRET_FIELD_PATH_XK9"
    with _patch_certified_builder(), patch(
        "nexa_engine.modules.calculator.api.calculate_certified_handler.NexaPricingEngine.calcular",
        side_effect=DomainError(sentinel),
    ):
        response = client.post(
            "/api/v1/simulation/calculate?mode=certified", json=canonical_body
        )

    assert response.status_code == 422
    assert sentinel not in response.text, (
        f"DomainError str leaked into certified 422 response: {response.text[:500]}"
    )


# ────────────────────────────────────────────────────────────────────────────
# AuditIntegrityError — sanitized 500
# ────────────────────────────────────────────────────────────────────────────

_SNAP_FAILURE_SENTINEL = "SNAP_FAILURE_INTERNAL_OS_ERROR_XK9"


def test_audit_integrity_error_returns_500(client, canonical_body):
    """AuditIntegrityError from snapshot persistence must map to HTTP 500."""
    with _patch_audit_integrity_pipeline(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler._snapshot_repo.save",
        side_effect=RuntimeError(_SNAP_FAILURE_SENTINEL),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500


def test_audit_integrity_error_uses_api_response_envelope(client, canonical_body):
    """AuditIntegrityError must return ApiResponse envelope (success/error keys)."""
    with _patch_audit_integrity_pipeline(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler._snapshot_repo.save",
        side_effect=RuntimeError(_SNAP_FAILURE_SENTINEL),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    data = response.json()
    assert data.get("success") is False
    assert data.get("error", {}).get("code") == "AUDIT_INTEGRITY_ERROR"
    assert "detail" not in data, f"Raw FastAPI detail envelope leaked: {data}"


def test_audit_integrity_error_message_is_safe_generic(client, canonical_body):
    """AuditIntegrityError message must be the safe generic string."""
    with _patch_audit_integrity_pipeline(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler._snapshot_repo.save",
        side_effect=RuntimeError(_SNAP_FAILURE_SENTINEL),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    data = response.json()
    assert data["error"]["message"] == "Error de integridad de auditoría."


def test_audit_integrity_error_does_not_expose_str_exc(client, canonical_body):
    """AuditIntegrityError response must NOT contain the raw str(_snap_exc)."""
    with _patch_audit_integrity_pipeline(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler._snapshot_repo.save",
        side_effect=RuntimeError(_SNAP_FAILURE_SENTINEL),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    assert _SNAP_FAILURE_SENTINEL not in response.text, (
        f"str(_snap_exc) leaked into AuditIntegrityError response: {response.text[:500]}"
    )


def test_audit_integrity_error_does_not_expose_type_in_details(client, canonical_body):
    """AuditIntegrityError response must NOT contain Python class name in details."""
    with _patch_audit_integrity_pipeline(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler._snapshot_repo.save",
        side_effect=RuntimeError(_SNAP_FAILURE_SENTINEL),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    data = response.json()
    details = (data.get("error") or {}).get("details") or {}
    assert "type" not in details, f"Python class name exposed in AuditIntegrityError details: {details}"


def test_audit_integrity_error_does_not_expose_module_in_details(client, canonical_body):
    """AuditIntegrityError response must NOT contain Python module path in details."""
    with _patch_audit_integrity_pipeline(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler._snapshot_repo.save",
        side_effect=RuntimeError(_SNAP_FAILURE_SENTINEL),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    data = response.json()
    details = (data.get("error") or {}).get("details") or {}
    assert "module" not in details, f"Python module path exposed in AuditIntegrityError details: {details}"


def test_audit_integrity_error_does_not_expose_class_path(client, canonical_body):
    """AuditIntegrityError response body must not contain internal Python module paths."""
    sentinel_module = "nexa_engine.modules.shared.exceptions"
    with _patch_audit_integrity_pipeline(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler._snapshot_repo.save",
        side_effect=RuntimeError(_SNAP_FAILURE_SENTINEL),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    assert sentinel_module not in response.text, (
        f"Internal module path leaked in AuditIntegrityError response: {response.text[:300]}"
    )


def test_audit_integrity_error_does_not_expose_traceback(client, canonical_body):
    """AuditIntegrityError response must not contain Python traceback."""
    with _patch_audit_integrity_pipeline(), patch(
        "nexa_engine.modules.calculator.api.calculate_normal_handler._snapshot_repo.save",
        side_effect=RuntimeError(_SNAP_FAILURE_SENTINEL),
    ):
        response = client.post("/api/v1/simulation/calculate", json=canonical_body)

    assert response.status_code == 500
    body_text = response.text
    assert "Traceback" not in body_text
    assert "File " not in body_text
