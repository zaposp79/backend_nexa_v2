"""WAVE 15 — /certification HTTP endpoints."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.certified_filesystem_deferred


import json

from nexa_engine.modules.certification.models import ExecutionCertificate
from nexa_engine.modules.certification.certificate_repository import (
    CertificateRepository,
)


def _override_cert_repo(client, monkeypatch, tmp_path) -> CertificateRepository:
    """Override the certificate repository in the app's container."""
    repo = CertificateRepository(root=tmp_path)
    # Monkeypatch the container's cert repository (used by all requests via this client)
    monkeypatch.setattr(client.app.state.container, "certificate_repository", repo)
    return repo


def _persist_sample_cert(client, monkeypatch, tmp_path, cid="endpointcert"):
    """Reroute the certificate repository at the container level to tmp_path."""
    repo = _override_cert_repo(client, monkeypatch, tmp_path)
    from pathlib import Path

    from nexa_engine.modules.calculator.use_cases.certified_calculation import (
        CertifiedCalculationUseCase,
    )
    from nexa_engine.modules.shared.versioning.version_registry import VersionRegistry

    helper = CertifiedCalculationUseCase(
        engine=None,
        version_registry=VersionRegistry(),
        baseline_root=Path("storage") / "baselines" / "v2-7-certified",
        cert_repo=repo,
    )
    live = helper._compute_canonical_param_hashes()  # noqa: SLF001
    cert = ExecutionCertificate(
        simulation_id="sim-endpoint",
        certificate_id=cid,
        issued_at="2026-05-28T00:00:00Z",
        version_metadata={
            "engine_version": "engine-v2",
            "parametrization_hashes": dict(live),
            "baseline_version": "v2-7-certified",
        },
        request_hash="r" * 64,
        result_hash="s" * 64,
        lineage_hash="l" * 64,
        baseline_matched="bancamia_sac_inbound_fte",
        validation_results={"parity": "passed"},
    )
    repo.save(cert)
    return cert


def test_get_certificate_returns_200(client, monkeypatch, tmp_path):
    cert = _persist_sample_cert(client, monkeypatch, tmp_path)
    resp = client.get(f"/api/v1/certification/certificate/{cert.certificate_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["certificate_id"] == cert.certificate_id
    assert data["simulation_id"] == cert.simulation_id


def test_get_unknown_certificate_returns_404(client, monkeypatch, tmp_path):
    _persist_sample_cert(client, monkeypatch, tmp_path)
    resp = client.get("/api/v1/certification/certificate/does-not-exist")
    assert resp.status_code == 404


def test_list_certificates_returns_array(client, monkeypatch, tmp_path):
    _persist_sample_cert(client, monkeypatch, tmp_path, cid="alpha")
    _persist_sample_cert(client, monkeypatch, tmp_path, cid="beta")
    resp = client.get("/api/v1/certification/certificates?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = {c["certificate_id"] for c in data}
    assert {"alpha", "beta"}.issubset(ids)


def test_verify_certificate_reports_validity(client, monkeypatch, tmp_path):
    cert = _persist_sample_cert(client, monkeypatch, tmp_path, cid="verifycert")
    resp = client.post(f"/api/v1/certification/verify/{cert.certificate_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) == {
        "certificate_id",
        "simulation_id",
        "valid",
        "drift",
        "checked_modules",
    }
    assert data["certificate_id"] == cert.certificate_id
    assert data["simulation_id"] == cert.simulation_id
    assert data["valid"] is True
    assert data["drift"] == {}
    assert isinstance(data["certificate_id"], str)
    assert isinstance(data["simulation_id"], str)
    assert isinstance(data["valid"], bool)
    assert isinstance(data["drift"], dict)
    assert isinstance(data["checked_modules"], list)
    assert set(data["checked_modules"]) >= {"hr", "gn", "op", "business_rules"}


def test_verify_certificate_reports_drift(client, monkeypatch, tmp_path):
    cert = _persist_sample_cert(client, monkeypatch, tmp_path, cid="driftcert")
    hashes = dict(cert.version_metadata["parametrization_hashes"])
    hashes["hr"] = "0" * 64
    metadata = dict(cert.version_metadata)
    metadata["parametrization_hashes"] = hashes

    repo = CertificateRepository(root=tmp_path)
    repo.save(cert.with_overrides(version_metadata=metadata))

    resp = client.post(f"/api/v1/certification/verify/{cert.certificate_id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["valid"] is False
    assert data["drift"]["hr"]["expected"] == "0" * 64
    assert isinstance(data["drift"]["hr"]["actual"], str)


def test_verify_unknown_certificate_returns_404(client, monkeypatch, tmp_path):
    _persist_sample_cert(client, monkeypatch, tmp_path)
    resp = client.post("/api/v1/certification/verify/does-not-exist")
    assert resp.status_code == 404


def test_verify_certificate_openapi_documents_success_schema_and_404(client):
    schema = client.app.openapi()
    operation = schema["paths"]["/api/v1/certification/verify/{certificate_id}"]["post"]

    assert "404" in operation["responses"]
    assert operation["responses"]["404"]["description"] == "Certificate not found"

    success_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert success_schema == {
        "$ref": "#/components/schemas/CertificateVerificationResultV1"
    }

    component = schema["components"]["schemas"]["CertificateVerificationResultV1"]
    assert set(component["properties"]) == {
        "certificate_id",
        "simulation_id",
        "valid",
        "drift",
        "checked_modules",
    }
    assert set(component["required"]) == {
        "certificate_id",
        "simulation_id",
        "valid",
    }
