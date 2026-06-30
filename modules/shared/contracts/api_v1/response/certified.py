"""Certified-mode response DTOs (api-v1) — WAVE 15.

Frozen, extra='forbid' Pydantic models that wrap the certificate
emitted by ``CertifiedCalculationUseCase``.
"""
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExecutionCertificateV1(BaseModel):
    """Public DTO for an ``ExecutionCertificate``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    certificate_id: str
    simulation_id: str
    issued_at: str
    version_metadata: Dict[str, Any] = Field(default_factory=dict)
    request_hash: str
    result_hash: str
    lineage_hash: str
    baseline_matched: Optional[str] = None
    validation_results: Dict[str, str] = Field(default_factory=dict)


class CertifiedSimulationResponseV1(BaseModel):
    """Top-level envelope returned by ``/calculate?mode=certified``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    simulation_id: str
    certified: Literal[True] = True
    certificate: ExecutionCertificateV1
    message: str = "Cálculos certificados guardados correctamente"


class CertificateVerificationResultV1(BaseModel):
    """Result returned by ``POST /certification/verify/{certificate_id}``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    certificate_id: str
    simulation_id: str
    valid: bool
    drift: Dict[str, Dict[str, Optional[str]]] = Field(default_factory=dict)
    checked_modules: list[str] = Field(default_factory=list)


__all__ = [
    "CertificateVerificationResultV1",
    "CertifiedSimulationResponseV1",
    "ExecutionCertificateV1",
]
