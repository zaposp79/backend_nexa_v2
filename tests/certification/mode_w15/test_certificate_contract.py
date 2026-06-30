"""WAVE 15 — Pydantic DTO contract checks."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.certified_filesystem_deferred

from pydantic import ValidationError

from nexa_engine.modules.shared.contracts.api_v1.response.certified import (
    CertifiedSimulationResponseV1,
    ExecutionCertificateV1,
)


def _valid_cert_payload():
    return {
        "certificate_id": "a" * 64,
        "simulation_id": "sim123",
        "issued_at": "2026-05-28T00:00:00Z",
        "version_metadata": {"engine_version": "engine-v2"},
        "request_hash": "b" * 64,
        "result_hash": "c" * 64,
        "lineage_hash": "d" * 64,
        "baseline_matched": "bancamia_sac_inbound_fte",
        "validation_results": {"parity": "passed"},
    }


def test_execution_certificate_v1_accepts_valid_payload():
    cert = ExecutionCertificateV1(**_valid_cert_payload())
    assert cert.certificate_id.startswith("a")
    assert cert.baseline_matched == "bancamia_sac_inbound_fte"


def test_execution_certificate_v1_forbids_extra_fields():
    payload = _valid_cert_payload()
    payload["unexpected"] = "boom"
    with pytest.raises(ValidationError):
        ExecutionCertificateV1(**payload)


def test_execution_certificate_v1_is_frozen():
    cert = ExecutionCertificateV1(**_valid_cert_payload())
    with pytest.raises(ValidationError):
        cert.certificate_id = "mutated"


def test_certified_simulation_response_v1_envelope():
    inner = _valid_cert_payload()
    env = CertifiedSimulationResponseV1(
        simulation_id="sim123",
        certificate=ExecutionCertificateV1(**inner),
    )
    assert env.certified is True
    assert env.certificate.certificate_id == inner["certificate_id"]
