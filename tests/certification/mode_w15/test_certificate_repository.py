"""WAVE 15 — CertificateRepository unit coverage."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.certified_filesystem_deferred


import json

from nexa_engine.modules.certification.models import ExecutionCertificate
from nexa_engine.modules.certification.certificate_repository import (
    CertificateRepository,
)


def _sample_cert(cid: str = "abc123", sim: str = "sim001") -> ExecutionCertificate:
    return ExecutionCertificate(
        simulation_id=sim,
        certificate_id=cid,
        issued_at="2026-05-28T00:00:00Z",
        version_metadata={"engine_version": "engine-v2"},
        request_hash="r" * 64,
        result_hash="s" * 64,
        lineage_hash="l" * 64,
        baseline_matched=None,
        validation_results={"ok": "yes"},
    )


def test_save_and_load_roundtrip(tmp_path):
    repo = CertificateRepository(root=tmp_path)
    cert = _sample_cert()
    repo.save(cert)
    loaded = repo.load(cert.certificate_id)
    assert loaded == cert


def test_exists_returns_true_after_save(tmp_path):
    repo = CertificateRepository(root=tmp_path)
    cert = _sample_cert()
    assert not repo.exists(cert.certificate_id)
    repo.save(cert)
    assert repo.exists(cert.certificate_id)


def test_list_recent_orders_descending(tmp_path):
    import time
    repo = CertificateRepository(root=tmp_path)
    for i in range(3):
        repo.save(_sample_cert(cid=f"cert_{i:03d}", sim=f"sim_{i:03d}"))
        time.sleep(0.01)
    items = repo.list_recent(limit=10)
    assert len(items) == 3
    # most recently saved comes first
    assert items[0].certificate_id == "cert_002"


def test_find_by_simulation_id_uses_index(tmp_path):
    repo = CertificateRepository(root=tmp_path)
    cert = _sample_cert(cid="xyz", sim="my-sim")
    repo.save(cert)
    found = repo.find_by_simulation_id("my-sim")
    assert found is not None
    assert found.certificate_id == "xyz"


def test_save_is_deterministic_byte_layout(tmp_path):
    repo = CertificateRepository(root=tmp_path)
    cert = _sample_cert()
    path1 = repo.save(cert)
    bytes_a = path1.read_bytes()
    # Re-save with the same content → same bytes.
    repo.save(cert)
    bytes_b = path1.read_bytes()
    assert bytes_a == bytes_b
    # File parses as JSON and has all expected keys.
    data = json.loads(bytes_a)
    assert set(data.keys()) >= {
        "simulation_id",
        "certificate_id",
        "issued_at",
        "version_metadata",
        "request_hash",
        "result_hash",
        "lineage_hash",
        "baseline_matched",
        "validation_results",
    }
