"""Audit response DTOs (api-v1).

WAVE 13 — exposes the lineage of a simulation as the audit contract.

These DTOs are part of the frozen api-v1 contract: changes are additive
only. F9 placeholders (`engine_version`, `formula_set`,
`parametrization_hashes`) hold literal strings/empty dicts today; WAVE 14
will wire them to real SemVer / manifest hashes without breaking the
schema.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


class LineageRefV1(BaseModel):
    """One reference inside a lineage chain (audit-facing view)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: str
    source_id: str
    value: Any = None
    sheet: Optional[str] = None
    cell: Optional[str] = None
    formula: Optional[str] = None


class AuditFormulaV1(BaseModel):
    """One unique formula recorded by a calculator during the simulation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    calculator: str
    formula: str
    stage: str
    used_count: int = Field(default=1, ge=1)


class AuditParametersUsedV1(BaseModel):
    """Split of inputs consumed by the simulation: request vs parametrization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request: Dict[str, Any] = Field(default_factory=dict)
    parametrization: Dict[str, Any] = Field(default_factory=dict)
    excel_refs: List[LineageRefV1] = Field(default_factory=list)


class AuditLineageSummaryV1(BaseModel):
    """Compact summary of the lineage graph."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    nodes_count: int = Field(default=0, ge=0)
    roots: List[str] = Field(default_factory=list)
    stages_summary: Dict[str, int] = Field(default_factory=dict)


class AuditBaselineComparisonV1(BaseModel):
    """Comparison vs a certified baseline (optional)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline_id: str
    matches_baseline: bool
    diff: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Top-level audit response
# ---------------------------------------------------------------------------


class AuditResponseV1(BaseModel):
    """Audit envelope for one simulation.

    All fields are populated by the audit use case from live VersionMetadata
    and lineage graph at simulation time.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    simulation_id: str
    api_version: Literal["api-v1"] = "api-v1"
    engine_version: str
    formula_set: str
    parametrization_hashes: Dict[str, str] = Field(default_factory=dict)
    lineage: AuditLineageSummaryV1
    formulas: List[AuditFormulaV1] = Field(default_factory=list)
    parameters_used: AuditParametersUsedV1 = Field(default_factory=AuditParametersUsedV1)
    baseline_comparison: Optional[AuditBaselineComparisonV1] = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Explain endpoint
# ---------------------------------------------------------------------------


class AuditValueExplanationV1(BaseModel):
    """Cadena de lineage humanamente legible para un valor concreto."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    simulation_id: str
    value_name: str
    value: Any = None
    calculator: str = ""
    formula: str = ""
    stage: str = ""
    explanation: str = ""
    refs_chain: List[LineageRefV1] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# List endpoint
# ---------------------------------------------------------------------------


class AuditSimulationSummaryV1(BaseModel):
    """Compact summary for the listing endpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    simulation_id: str
    nodes_count: int = Field(default=0, ge=0)
    roots_count: int = Field(default=0, ge=0)
    stages: List[str] = Field(default_factory=list)
    generated_at: Optional[datetime] = None


__all__ = [
    "LineageRefV1",
    "AuditFormulaV1",
    "AuditParametersUsedV1",
    "AuditLineageSummaryV1",
    "AuditBaselineComparisonV1",
    "AuditResponseV1",
    "AuditValueExplanationV1",
    "AuditSimulationSummaryV1",
]
