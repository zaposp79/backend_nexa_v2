"""application.certification.models
====================================

Domain objects for the WAVE 15 Certified Mode.

* ``ExecutionCertificate``  — immutable record proving a simulation
  was executed against a fully-pinned engine + parametrization.
* ``CertificationFailure``  — structured failure reason returned to
  the API edge (mapped to HTTP 412 by the router).
* ``CertificationFailureError`` — exception carrying a
  ``CertificationFailure`` payload.

Design rules
------------
* Both dataclasses are ``frozen=True`` — instances are append-only
  audit artefacts.
* All fields are JSON-serialisable to keep persistence trivial.
* ``certificate_id`` is computed deterministically from the
  certificate fields (excluding ``issued_at`` and ``certificate_id``
  itself) so identical executions produce identical ids.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Dict, Optional


_FAILURE_CODES = {
    "HASH_MISMATCH",
    "EXPERIMENTAL_OVERRIDE",
    "PARITY_FAILURE",
    "BASELINE_NOT_FOUND",
}


# ---------------------------------------------------------------------------
# Failure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CertificationFailure:
    """Structured reason explaining why a certified run was rejected."""

    code: str
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:  # pragma: no cover — defensive
        if self.code not in _FAILURE_CODES:
            # Keep tolerant: unknown codes get a hint but are not blocked,
            # the API still maps them to HTTP 412.
            pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
            "details": dict(self.details),
        }


class CertificationFailureError(Exception):
    """Raised by ``CertifiedCalculationUseCase`` when validation fails.

    Carries a ``CertificationFailure`` so the router can serialise the
    structured payload as HTTP 412 detail.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        expected: Optional[str] = None,
        actual: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.failure = CertificationFailure(
            code=code,
            message=message,
            expected=expected,
            actual=actual,
            details=dict(details or {}),
        )
        super().__init__(message)

    # Pass-through convenience properties so callers don't dig into ``failure``.
    @property
    def code(self) -> str:
        return self.failure.code

    @property
    def message(self) -> str:
        return self.failure.message

    @property
    def expected(self) -> Optional[str]:
        return self.failure.expected

    @property
    def actual(self) -> Optional[str]:
        return self.failure.actual

    @property
    def details(self) -> Dict[str, Any]:
        return dict(self.failure.details)


# ---------------------------------------------------------------------------
# Certificate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionCertificate:
    """Immutable certificate of a certified-mode execution."""

    simulation_id: str
    certificate_id: str
    issued_at: str  # ISO-8601 timestamp (UTC)
    version_metadata: Dict[str, Any]
    request_hash: str
    result_hash: str
    lineage_hash: str
    baseline_matched: Optional[str] = None
    validation_results: Dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "certificate_id": self.certificate_id,
            "issued_at": self.issued_at,
            "version_metadata": dict(self.version_metadata),
            "request_hash": self.request_hash,
            "result_hash": self.result_hash,
            "lineage_hash": self.lineage_hash,
            "baseline_matched": self.baseline_matched,
            "validation_results": dict(self.validation_results),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionCertificate":
        return cls(
            simulation_id=str(data["simulation_id"]),
            certificate_id=str(data["certificate_id"]),
            issued_at=str(data["issued_at"]),
            version_metadata=dict(data.get("version_metadata", {})),
            request_hash=str(data["request_hash"]),
            result_hash=str(data["result_hash"]),
            lineage_hash=str(data["lineage_hash"]),
            baseline_matched=(
                str(data["baseline_matched"])
                if data.get("baseline_matched") is not None
                else None
            ),
            validation_results=dict(data.get("validation_results", {})),
        )

    # ------------------------------------------------------------------
    # Deterministic certificate id
    # ------------------------------------------------------------------
    @staticmethod
    def compute_certificate_id(
        *,
        simulation_id: str,
        version_metadata: Dict[str, Any],
        request_hash: str,
        result_hash: str,
        lineage_hash: str,
        baseline_matched: Optional[str],
        validation_results: Dict[str, str],
    ) -> str:
        """SHA-256 over the canonical (sorted-keys) form of the cert
        body. ``issued_at`` and ``certificate_id`` itself are excluded
        so identical executions produce identical certificate ids.
        """
        payload = {
            "simulation_id": simulation_id,
            "version_metadata": version_metadata,
            "request_hash": request_hash,
            "result_hash": result_hash,
            "lineage_hash": lineage_hash,
            "baseline_matched": baseline_matched,
            "validation_results": validation_results,
        }
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def with_overrides(self, **overrides: Any) -> "ExecutionCertificate":
        return replace(self, **overrides)


__all__ = [
    "CertificationFailure",
    "CertificationFailureError",
    "ExecutionCertificate",
]
