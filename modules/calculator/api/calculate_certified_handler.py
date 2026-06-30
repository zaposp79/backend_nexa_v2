"""Certified-mode handler for POST /api/v1/simulation/calculate (WAVE 15).

``mode=certified`` branch — strict hash + parity validation, emits an
ExecutionCertificate. Extracted verbatim from calculate_router.py
(FASE Y Batch 4b) — behaviour unchanged.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.serializers import (
    pricing_result_to_dict,
    validate_visions_complete,
)
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.shared.exceptions import DomainError, ParametrizationError
from nexa_engine.modules.shared.responses import ApiResponse, ErrorDetail
from nexa_engine.modules.calculator_motor.validation.contract_validator import ContractValidator

from nexa_engine.modules.calculator.api.calculate_dto import CalculationRequest
from nexa_engine.modules.calculator.api.calculate_dependencies import _results_repo, _lineage_repo

logger = logging.getLogger("nexa.calculate")


def _calculate_certified(body: CalculationRequest):
    """``mode=certified`` branch — strict hash + parity validation."""
    from nexa_engine.modules.shared.config.config import BASELINES_DIR
    from nexa_engine.modules.certification.models import (
        CertificationFailureError,
    )
    from nexa_engine.modules.calculator.use_cases.certified_calculation import (
        CertifiedCalculationUseCase,
    )
    from nexa_engine.modules.shared.versioning.version_registry import VersionRegistry
    from nexa_engine.modules.certification.certificate_repository import (
        CertificateRepository,
    )

    try:
        # WAVE 15 — experimental-override check runs BEFORE the loader so
        # that EXPERIMENTAL_OVERRIDE wins over CONTRACT_VIOLATION (which
        # the loader raises for unknown top-level keys).
        from nexa_engine.modules.calculator.use_cases.certified_calculation import (
            CertifiedCalculationUseCase,
        )
        from nexa_engine.modules.certification.models import (
            CertificationFailureError,
        )

        experimental_fields = list(CertifiedCalculationUseCase._find_experimental_keys(body.user_input))  # noqa: SLF001
        if experimental_fields:
            raise CertificationFailureError(
                code="EXPERIMENTAL_OVERRIDE",
                message=(
                    "certified mode forbids experimental overrides; "
                    f"found {len(experimental_fields)} field(s)"
                ),
                details={"fields": experimental_fields},
            )

        # Strip the metadata block (mode/expected hashes) before loading
        # — the loader treats unknown top-level keys as contract
        # violations. ``metadata`` is W15-only.
        clean_input = {
            k: v for k, v in body.user_input.items() if k != "metadata"
        }

        # Contract validation (entry_data) — same as normal path.
        if "datos_operativos" in clean_input:
            ContractValidator().raise_if_invalid(clean_input)

        loader = UserInputLoader()
        user_input = loader.cargar_desde_dict(clean_input)
        builder = SimulationContextBuilder()
        solicitud = builder.construir(user_input)

        registry = VersionRegistry()
        engine = NexaPricingEngine(version_registry=registry, lineage_repository=_lineage_repo)
        cert_repo = CertificateRepository()
        baseline_root = BASELINES_DIR
        use_case = CertifiedCalculationUseCase(
            engine=engine,
            version_registry=registry,
            baseline_root=baseline_root,
            cert_repo=cert_repo,
            lineage_repo=_lineage_repo,
        )

        # Optional client-supplied expected hashes (header-style override).
        expected_hashes = None
        meta = body.user_input.get("metadata") if isinstance(body.user_input, dict) else None
        if isinstance(meta, dict):
            ph = meta.get("expected_parametrization_hash")
            if isinstance(ph, dict):
                expected_hashes = ph

        result, certificate = use_case.execute(
            solicitud,
            raw_user_input=body.user_input,
            expected_parametrization_hash=expected_hashes,
        )

        # Persist the normal result so /simulation/{id}/results/* keep working.
        simulation_id = getattr(result, "simulation_id", None) or _results_repo.new_id()
        try:
            full_dict = pricing_result_to_dict(result, simulation_id)
            validate_visions_complete(result)
            _results_repo.save(full_dict)
        except Exception:  # pragma: no cover — visions failure shouldn't void certificate
            logger.exception("[calculate-certified] non-fatal: result persistence failed")

        payload = {
            "simulation_id": simulation_id,
            "certified": True,
            "certificate": certificate.to_dict(),
            "message": "Cálculos certificados guardados correctamente",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return ApiResponse.ok(payload)

    except CertificationFailureError as exc:
        logger.warning(
            "[calculate-certified] ✗ %s: %s expected=%r actual=%r",
            exc.code,
            exc.message,
            exc.expected,
            exc.actual,
        )
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={
                "code": exc.code,
                "message": exc.message,
                "expected": exc.expected,
                "actual": exc.actual,
                "details": exc.details,
            },
        )
    except HTTPException:
        raise
    except (DomainError, ParametrizationError) as exc:
        logger.exception("[calculate-certified] domain/parametrization error")
        return JSONResponse(
            status_code=422,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code="INPUT_ERROR",
                    message="Error en datos de entrada.",
                ),
            ).model_dump(),
        )
    except Exception as exc:
        logger.exception("[calculate-certified] unexpected error")
        return JSONResponse(
            status_code=500,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="Error inesperado en el servidor.",
                ),
            ).model_dump(),
        )


__all__ = ["_calculate_certified"]
