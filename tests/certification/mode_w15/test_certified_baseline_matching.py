"""WAVE 15 — baseline matching + parity tolerance."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.certified_filesystem_deferred



def test_bancamia_matches_known_baseline(use_case, bancamia_request, build_solicitud):
    solicitud = build_solicitud(bancamia_request)
    _, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    assert cert.baseline_matched == "bancamia_sac_inbound_fte"


def test_parity_check_runs_when_baseline_matched(
    use_case, bancamia_request, build_solicitud
):
    solicitud = build_solicitud(bancamia_request)
    _, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    assert cert.validation_results["parity"] == "passed"


def test_no_match_when_baseline_dimensions_disagree(
    use_case, build_solicitud, bancamia_request, monkeypatch
):
    """When matching scores < 2 we return no baseline and skip parity."""
    # Force the matcher to find nothing by mocking _find_matching_baseline.
    monkeypatch.setattr(use_case, "_find_matching_baseline", lambda req: None)
    solicitud = build_solicitud(bancamia_request)
    _, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    assert cert.baseline_matched is None
    assert cert.validation_results["parity"] == "skipped"


def test_deterministic_certificate_id_for_same_request(
    use_case, bancamia_request, build_solicitud
):
    """Two cert id computations from the same hashes must agree."""
    from nexa_engine.modules.certification.models import ExecutionCertificate

    solicitud = build_solicitud(bancamia_request)
    _, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    recomputed = ExecutionCertificate.compute_certificate_id(
        simulation_id=cert.simulation_id,
        version_metadata=cert.version_metadata,
        request_hash=cert.request_hash,
        result_hash=cert.result_hash,
        lineage_hash=cert.lineage_hash,
        baseline_matched=cert.baseline_matched,
        validation_results=cert.validation_results,
    )
    assert recomputed == cert.certificate_id
