"""Funciones de dependencias FastAPI."""

from __future__ import annotations

from fastapi import Depends, Request

from nexa_engine.db.container import ApplicationContainer
from nexa_engine.db.factory import get_provider
from nexa_engine.modules.calculator.persistence.results_repository import ResultsRepository
from nexa_engine.modules.certification.certificate_repository import CertificateRepository
from nexa_engine.modules.lineage.infrastructure.snapshot_repository import (
    LineageSnapshotRepository,
)
from nexa_engine.modules.calculator.persistence.snapshots_repository import SnapshotRepository

# Module-level singleton — shared composition root for all consumers that
# cannot use FastAPI Depends() (handlers, certification router lazy imports).
# Single store instance per process; matches the pattern in calculate_dependencies.
_lineage_repo = LineageSnapshotRepository(store=get_provider())
from nexa_engine.modules.cadena_a.services.parameters_query_service import (
    CadenaAParametersQueryService,
)
from nexa_engine.modules.cadena_b.services.parameters_query_service import (
    CadenaBParametersQueryService,
)
from nexa_engine.modules.cadena_c.services.parameters_query_service import (
    CadenaCParametersQueryService,
)
from nexa_engine.modules.panel.services.panel_service import PanelService
from nexa_engine.modules.parametrizacion.hr.services.hr_service import HRService
from nexa_engine.modules.parametrizacion.gn.services.gn_service import GNService
from nexa_engine.modules.parametrizacion.op.services.op_service import OPService
from nexa_engine.modules.audit.use_cases.audit_simulation import AuditSimulationUseCase
from nexa_engine.modules.shared.versioning.registry_provider import _version_registry
from nexa_engine.modules.simulation_draft.services.draft_service import SimulationDraftService


def get_container(request: Request) -> ApplicationContainer:
    return request.app.state.container


def get_results_repository(
    container: ApplicationContainer = Depends(get_container),
) -> ResultsRepository:
    return container.results_repository


def get_snapshots_repository(
    container: ApplicationContainer = Depends(get_container),
) -> SnapshotRepository:
    return container.snapshots_repository


def get_certificate_repository(
    container: ApplicationContainer = Depends(get_container),
) -> CertificateRepository:
    return container.certificate_repository


def get_lineage_repository(
    container: ApplicationContainer = Depends(get_container),
) -> LineageSnapshotRepository:
    return container.lineage_repository


def get_cadena_a_parameters_service(
    container: ApplicationContainer = Depends(get_container),
) -> CadenaAParametersQueryService:
    return container.cadena_a_parameters_service


def get_cadena_b_parameters_service(
    container: ApplicationContainer = Depends(get_container),
) -> CadenaBParametersQueryService:
    return container.cadena_b_parameters_service


def get_cadena_c_parameters_service(
    container: ApplicationContainer = Depends(get_container),
) -> CadenaCParametersQueryService:
    return container.cadena_c_parameters_service


def get_panel_service(
    container: ApplicationContainer = Depends(get_container),
) -> PanelService:
    return container.panel_service


def get_gn_upload_service(
    container: ApplicationContainer = Depends(get_container),
) -> GNService:
    return container.gn_upload_service


def get_hr_upload_service(
    container: ApplicationContainer = Depends(get_container),
) -> HRService:
    return container.hr_upload_service


def get_op_upload_service(
    container: ApplicationContainer = Depends(get_container),
) -> OPService:
    return container.op_upload_service


def get_draft_service(
    container: ApplicationContainer = Depends(get_container),
) -> SimulationDraftService:
    return container.draft_service


def get_audit_use_case(
    lineage_repo: LineageSnapshotRepository = Depends(get_lineage_repository),
) -> AuditSimulationUseCase:
    return AuditSimulationUseCase(lineage_repo=lineage_repo, version_registry=_version_registry)


__all__ = [
    "get_container",
    "get_results_repository",
    "get_snapshots_repository",
    "get_certificate_repository",
    "get_lineage_repository",
    "get_cadena_a_parameters_service",
    "get_cadena_b_parameters_service",
    "get_cadena_c_parameters_service",
    "get_panel_service",
    "get_gn_upload_service",
    "get_hr_upload_service",
    "get_op_upload_service",
    "get_audit_use_case",
    "get_draft_service",
    "_lineage_repo",
]
