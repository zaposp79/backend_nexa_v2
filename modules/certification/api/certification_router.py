"""
GET/POST /api/v1/certification/...
====================================

WAVE 15 — Certified Mode introspection endpoints.

Endpoints
---------
* GET  /certification/certificates                     — list recent
* GET  /certification/certificate/{certificate_id}      — load one
* POST /certification/verify/{certificate_id}           — re-validate
  the certificate against the live parametrization hashes.

Canonical location: modules/certification/api/ (moved from shared/certification/ in Fase shared-cleanup).
"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from nexa_engine.db.dependencies import get_certificate_repository
from nexa_engine.modules.shared.contracts.api_v1.response.certified import (
    CertificateVerificationResultV1,
    ExecutionCertificateV1,
)
from nexa_engine.modules.certification.models import ExecutionCertificate
from nexa_engine.modules.certification.certificate_repository import CertificateRepository
from nexa_engine.modules.shared.versioning.version_registry import VersionRegistry


logger = logging.getLogger("nexa.certification")

router = APIRouter(prefix="/certification", tags=["certification"])


def _to_dto(cert: ExecutionCertificate) -> ExecutionCertificateV1:
    return ExecutionCertificateV1(
        certificate_id=cert.certificate_id,
        simulation_id=cert.simulation_id,
        issued_at=cert.issued_at,
        version_metadata=dict(cert.version_metadata),
        request_hash=cert.request_hash,
        result_hash=cert.result_hash,
        lineage_hash=cert.lineage_hash,
        baseline_matched=cert.baseline_matched,
        validation_results=dict(cert.validation_results),
    )


@router.get("/certificates", response_model=List[ExecutionCertificateV1])
def list_certificates(
    limit: int = 50,
    repo: CertificateRepository = Depends(get_certificate_repository),
):
    """List most recent certificates (descending by mtime)."""
    return [_to_dto(c) for c in repo.list_recent(limit=limit)]


@router.get(
    "/certificate/{certificate_id}",
    response_model=ExecutionCertificateV1,
)
def get_certificate(
    certificate_id: str,
    repo: CertificateRepository = Depends(get_certificate_repository),
):
    try:
        cert = repo.load(certificate_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"certificate_id={certificate_id!r} not found",
        )
    return _to_dto(cert)


@router.post(
    "/verify/{certificate_id}",
    response_model=CertificateVerificationResultV1,
    responses={404: {"description": "Certificate not found"}},
)
def verify_certificate(
    certificate_id: str,
    repo: CertificateRepository = Depends(get_certificate_repository),
):
    """Re-validate ``certificate_id`` against the live parametrization hashes."""
    try:
        cert = repo.load(certificate_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"certificate_id={certificate_id!r} not found",
        )

    # Lazy import to avoid circular dependency at module load time.
    from nexa_engine.modules.calculator.use_cases.certified_calculation import (
        CertifiedCalculationUseCase,
    )
    from nexa_engine.modules.shared.config.config import BASELINES_DIR
    from nexa_engine.db.dependencies import _lineage_repo

    registry = VersionRegistry()
    helper = CertifiedCalculationUseCase(
        engine=None,
        version_registry=registry,
        baseline_root=BASELINES_DIR,
        cert_repo=repo,
        lineage_repo=_lineage_repo,
    )
    live = helper._compute_canonical_param_hashes()  # noqa: SLF001
    expected = (cert.version_metadata or {}).get("parametrization_hashes", {})

    drift: dict = {}
    for module, exp_v in expected.items():
        actual = live.get(module)
        if actual != exp_v:
            drift[module] = {"expected": exp_v, "actual": actual}

    return {
        "certificate_id": cert.certificate_id,
        "simulation_id": cert.simulation_id,
        "valid": len(drift) == 0,
        "drift": drift,
        "checked_modules": sorted(expected.keys()),
    }


__all__ = ["router"]
