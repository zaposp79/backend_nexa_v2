"""WAVE 15 — basic happy-path coverage for certified mode."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.certified_filesystem_deferred



def test_certified_run_returns_certificate(use_case, bancamia_request, build_solicitud):
    solicitud = build_solicitud(bancamia_request)
    result, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    assert cert.certificate_id
    assert cert.simulation_id == result.simulation_id
    assert cert.request_hash
    assert cert.result_hash
    assert cert.lineage_hash


def test_certificate_includes_all_hashes(use_case, bancamia_request, build_solicitud):
    solicitud = build_solicitud(bancamia_request)
    _, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    # All hashes are non-empty hex strings of length 64.
    for h in (cert.request_hash, cert.result_hash, cert.lineage_hash, cert.certificate_id):
        assert isinstance(h, str)
        assert len(h) == 64
        int(h, 16)  # valid hex


def test_certificate_baseline_matched_for_bancamia(use_case, bancamia_request, build_solicitud):
    solicitud = build_solicitud(bancamia_request)
    _, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    assert cert.baseline_matched == "bancamia_sac_inbound_fte"
    assert cert.validation_results["parity"] == "passed"


def test_simulation_id_consistent_with_audit(use_case, bancamia_request, build_solicitud):
    """The certificate's simulation_id must point at a persisted lineage."""
    from nexa_engine.modules.lineage.infrastructure.snapshot_repository import (
        LineageSnapshotRepository,
    )
    solicitud = build_solicitud(bancamia_request)
    result, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    assert LineageSnapshotRepository().exists(cert.simulation_id)
    assert result.simulation_id == cert.simulation_id


def test_certificate_persisted(use_case, tmp_cert_repo, bancamia_request, build_solicitud):
    solicitud = build_solicitud(bancamia_request)
    _, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    loaded = tmp_cert_repo.load(cert.certificate_id)
    assert loaded.certificate_id == cert.certificate_id
    assert loaded.simulation_id == cert.simulation_id
    assert loaded.request_hash == cert.request_hash


def test_version_metadata_includes_baseline_version(use_case, bancamia_request, build_solicitud):
    solicitud = build_solicitud(bancamia_request)
    _, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    assert cert.version_metadata.get("baseline_version") == "v2-7-certified"
    assert cert.version_metadata.get("engine_version")
    assert cert.version_metadata.get("formula_set")
    assert set(cert.version_metadata.get("parametrization_hashes", {}).keys()) >= {
        "hr",
        "gn",
        "op",
        "business_rules",
    }
