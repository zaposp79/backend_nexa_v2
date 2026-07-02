"""
GET /api/v1/audit/...
=====================

WAVE 13 — Audit endpoints.

Exposes the lineage of a previously executed simulation. Lineage is
produced only when `/calculate` is invoked with `with_lineage=True` (or
when the engine API call sets that flag). Without lineage, audit
endpoints return 404.

Endpoints
---------
* GET /audit/simulations
    List simulations that have a persisted lineage graph.

* GET /audit/simulation/{simulation_id}
    Full audit envelope: formulas, parameters used, lineage summary.

* GET /audit/simulation/{simulation_id}/explain?value_name=...
    Human-readable explanation of one specific value.

* GET /audit/simulation/{simulation_id}/baseline-diff?baseline_id=...
    Compare the simulation's kpis vs a certified baseline.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from nexa_engine.db.dependencies import get_audit_use_case
from nexa_engine.modules.shared.contracts.api_v1.response.audit import (
    AuditBaselineComparisonV1,
    AuditFormulaV1,
    AuditLineageSummaryV1,
    AuditParametersUsedV1,
    AuditResponseV1,
    AuditSimulationSummaryV1,
    AuditValueExplanationV1,
    LineageRefV1,
)
from nexa_engine.modules.lineage.domain.models import LineageRef
from nexa_engine.modules.audit.use_cases.audit_simulation import (
    AuditNotAvailableError,
    AuditResult,
    AuditSimulationUseCase,
    ValueExplanation,
    ValueNotFoundError,
)

logger = logging.getLogger("nexa.audit")

router = APIRouter(prefix="/audit", tags=["audit"])


def _ref_to_dto(ref: LineageRef) -> LineageRefV1:
    return LineageRefV1(
        source_type=ref.source_type,
        source_id=ref.source_id,
        value=ref.value,
        sheet=ref.sheet,
        cell=ref.cell,
        formula=ref.formula,
    )


def _audit_to_dto(audit: AuditResult) -> AuditResponseV1:
    return AuditResponseV1(
        simulation_id=audit.simulation_id,
        engine_version=audit.engine_version,
        formula_set=audit.formula_set,
        parametrization_hashes=audit.parametrization_hashes,
        lineage=AuditLineageSummaryV1(
            nodes_count=audit.lineage.nodes_count,
            roots=audit.lineage.roots,
            stages_summary=audit.lineage.stages_summary,
        ),
        formulas=[
            AuditFormulaV1(
                calculator=f.calculator,
                formula=f.formula,
                stage=f.stage,
                used_count=f.used_count,
            )
            for f in audit.formulas
        ],
        parameters_used=AuditParametersUsedV1(
            request=audit.parameters_used.request,
            parametrization=audit.parameters_used.parametrization,
            excel_refs=[_ref_to_dto(r) for r in audit.parameters_used.excel_refs],
        ),
        generated_at=audit.generated_at,
    )


def _explanation_to_dto(exp: ValueExplanation) -> AuditValueExplanationV1:
    return AuditValueExplanationV1(
        simulation_id=exp.simulation_id,
        value_name=exp.value_name,
        value=exp.value,
        calculator=exp.calculator,
        formula=exp.formula,
        stage=exp.stage,
        explanation=exp.explanation,
        refs_chain=[_ref_to_dto(r) for r in exp.refs_chain],
    )


def _validate_baseline_version(baseline_version: str) -> None:
    r"""Validate baseline_version to prevent path traversal attacks.

    Allowed format: alphanumeric, hyphens, underscores (e.g., 'v2-7-certified', 'v2_7')
    Rejects: .., /, \, ../, absolute paths, empty strings
    """
    if not baseline_version or not isinstance(baseline_version, str):
        raise HTTPException(
            status_code=400,
            detail="Invalid baseline_version: empty or non-string value."
        )

    if not re.match(r"^[a-zA-Z0-9_-]+$", baseline_version):
        raise HTTPException(
            status_code=400,
            detail="Invalid baseline_version: must contain only alphanumeric, hyphens, or underscores."
        )

    if ".." in baseline_version or "/" in baseline_version or "\\" in baseline_version:
        raise HTTPException(
            status_code=400,
            detail="Invalid baseline_version: path traversal characters not allowed."
        )


def _validate_baseline_id(baseline_id: str) -> None:
    """Validate baseline_id to prevent path traversal attacks.

    Allowed format: UUIDs and safe identifiers (alphanumeric, hyphens, underscores)
    """
    if not baseline_id or not isinstance(baseline_id, str):
        raise HTTPException(
            status_code=400,
            detail="Invalid baseline_id: empty or non-string value."
        )

    if not re.match(r"^[a-zA-Z0-9_.-]+$", baseline_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid baseline_id: must contain only alphanumeric, hyphens, underscores, or dots."
        )

    if ".." in baseline_id or "/" in baseline_id or "\\" in baseline_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid baseline_id: path traversal characters not allowed."
        )


def _safe_baseline_path(baseline_root: Path, baseline_id: str) -> Path:
    """Resolve and validate that the final path stays inside baseline_root.

    Prevents symlink-based traversal by resolving before comparing.
    """
    safe_root = baseline_root.resolve()
    target = (baseline_root / baseline_id).resolve()
    if not str(target).startswith(str(safe_root)):
        raise HTTPException(status_code=400, detail="Invalid baseline path.")
    return target


@router.get(
    "/simulations",
    response_model=list[AuditSimulationSummaryV1],
    summary="List simulations with persisted lineage.",
)
def list_audit_simulations(
    limit: int = Query(50, ge=1, le=500),
    use_case: AuditSimulationUseCase = Depends(get_audit_use_case),
) -> list[AuditSimulationSummaryV1]:
    """Return summaries of simulations that have a stored lineage graph."""
    items = use_case.list_simulations(limit=limit)
    return [
        AuditSimulationSummaryV1(
            simulation_id=s.simulation_id,
            nodes_count=s.nodes_count,
            roots_count=s.roots_count,
            stages=s.stages,
            generated_at=s.generated_at,
        )
        for s in items
    ]


@router.get(
    "/simulation/{simulation_id}",
    response_model=AuditResponseV1,
    summary="Full audit envelope for a simulation.",
)
def get_simulation_audit(
    simulation_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
    use_case: AuditSimulationUseCase = Depends(get_audit_use_case),
) -> AuditResponseV1:
    """Return the audit envelope for `simulation_id`.

    Returns 404 if the simulation was not run with `with_lineage=True`.
    """
    try:
        audit = use_case.execute(simulation_id)
    except AuditNotAvailableError as exc:
        logger.info("[audit] no lineage for sim_id=%s", simulation_id)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _audit_to_dto(audit)


@router.get(
    "/simulation/{simulation_id}/explain",
    response_model=AuditValueExplanationV1,
    summary="Lineage chain for a specific value in a simulation.",
)
def explain_value(
    simulation_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
    value_name: str = Query(..., min_length=1, max_length=256, description="Canonical value name in the lineage graph."),
    use_case: AuditSimulationUseCase = Depends(get_audit_use_case),
) -> AuditValueExplanationV1:
    """Return the trace_back chain + human explanation for `value_name`."""
    try:
        explanation = use_case.explain_value(simulation_id, value_name)
    except AuditNotAvailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _explanation_to_dto(explanation)


@router.get(
    "/simulation/{simulation_id}/baseline-diff",
    response_model=AuditBaselineComparisonV1,
    summary="Compare a simulation's kpis vs a certified baseline.",
)
def diff_vs_baseline(
    simulation_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
    baseline_id: str = Query(..., description="Certified baseline id."),
    baseline_version: str = Query(
        "v2-7-certified",
        description="Baseline collection version under storage/baselines/.",
    ),
    use_case: AuditSimulationUseCase = Depends(get_audit_use_case),
) -> AuditBaselineComparisonV1:
    """Compare KPIs from the persisted lineage vs the baseline's kpis.json."""
    _validate_baseline_version(baseline_version)
    _validate_baseline_id(baseline_id)

    baseline_root = Path.cwd() / "storage" / "baselines" / baseline_version / "cases"
    _safe_baseline_path(baseline_root, baseline_id)  # path-traversal guard via resolve()
    try:
        diff = use_case.diff_vs_baseline(simulation_id, baseline_id, baseline_root)
    except AuditNotAvailableError as exc:
        raise HTTPException(status_code=404, detail="Baseline comparison not available") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Baseline not found") from exc
    return AuditBaselineComparisonV1(
        baseline_id=diff["baseline_id"],
        matches_baseline=diff["matches_baseline"],
        diff=diff["diff"],
    )


__all__ = ["router", "_validate_baseline_id", "_validate_baseline_version"]
