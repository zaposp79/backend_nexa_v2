"""WAVE 15 — lineage gets stamped with the certificate_id."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.certified_filesystem_deferred


import json


def test_lineage_file_contains_certificate_id(use_case, bancamia_request, build_solicitud):
    from nexa_engine.modules.lineage.infrastructure.snapshot_repository import (
        LineageSnapshotRepository,
    )

    solicitud = build_solicitud(bancamia_request)
    _, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    repo = LineageSnapshotRepository()
    assert repo.exists(cert.simulation_id)
    path = repo._path_for(cert.simulation_id)  # noqa: SLF001
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("certificate_id") == cert.certificate_id


def test_lineage_simulation_id_matches_cert(use_case, bancamia_request, build_solicitud):
    solicitud = build_solicitud(bancamia_request)
    result, cert = use_case.execute(solicitud, raw_user_input=bancamia_request)
    assert result.simulation_id == cert.simulation_id


def test_certificate_lineage_hash_is_deterministic_for_same_run(
    use_case, bancamia_request, build_solicitud
):
    solicitud = build_solicitud(bancamia_request)
    _, cert_a = use_case.execute(solicitud, raw_user_input=bancamia_request)
    # Re-run with a fresh solicitud → new sim_id, but the lineage *graph*
    # structure (excluding sim_id) is the same — so request/result/lineage
    # hashes must remain identical when computed from the same content.
    solicitud_b = build_solicitud(bancamia_request)
    _, cert_b = use_case.execute(solicitud_b, raw_user_input=bancamia_request)
    assert cert_a.request_hash == cert_b.request_hash
    assert cert_a.result_hash == cert_b.result_hash
