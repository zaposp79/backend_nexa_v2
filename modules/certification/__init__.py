"""modules/certification — bounded context for certified-mode execution.

Canonical home for ExecutionCertificate, CertificateRepository and the
certification API router. Moved from shared/certification/ in Fase shared-cleanup (2026-06-10).
"""
from nexa_engine.modules.certification.models import (
    CertificationFailure,
    CertificationFailureError,
    ExecutionCertificate,
)
from nexa_engine.modules.certification.certificate_repository import (
    CertificateRepository,
    now_iso,
)

__all__ = [
    "CertificationFailure",
    "CertificationFailureError",
    "ExecutionCertificate",
    "CertificateRepository",
    "now_iso",
]
