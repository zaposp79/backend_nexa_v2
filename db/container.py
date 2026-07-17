"""Contenedor de la aplicación: raíz de inyección de dependencias."""

from __future__ import annotations

from dataclasses import dataclass

from nexa_engine.db.config import load_config
from nexa_engine.db.factory import (
    build_configuration_document_store,
    build_parametrization_document_store,
    build_provider,
)
from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.calculator.persistence.results_repository import (
    ResultsRepository,
)
from nexa_engine.modules.certification.certificate_repository import (
    CertificateRepository,
)
from nexa_engine.modules.lineage.infrastructure.snapshot_repository import (
    LineageSnapshotRepository,
)
from nexa_engine.modules.calculator.persistence.snapshots_repository import (
    SnapshotRepository,
)
from nexa_engine.modules.parametrizacion.hr.repositories.hr_active_parametrization_repository import (
    HRActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.hr.mappers.hr_version_document_codec import (
    HRVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.hr.repositories.collections import (
    HR_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.hr.repositories.hr_repository import HRRepository
from nexa_engine.modules.parametrizacion.hr.services.hr_service import HRService
from nexa_engine.modules.parametrizacion.gn.repositories.gn_active_parametrization_repository import (
    GNActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.gn.mappers.gn_version_document_codec import (
    GNVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.gn.repositories.gn_repository import GNRepository
from nexa_engine.modules.parametrizacion.gn.repositories.collections import (
    GN_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.gn.services.gn_service import GNService
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)
from nexa_engine.modules.parametrizacion.op.repositories.op_active_parametrization_repository import (
    OPActiveParametrizationRepository,
)
from nexa_engine.modules.parametrizacion.op.mappers.op_version_document_codec import (
    OPVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.op.repositories.collections import (
    OP_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.op.repositories.op_repository import OPRepository
from nexa_engine.modules.parametrizacion.op.services.op_service import OPService
from nexa_engine.modules.parametrizacion.services.resolver import (
    ParametrizationResolver,
)
from nexa_engine.modules.parametrizacion.services.provider import (
    ParametrizationProvider,
)
from nexa_engine.modules.parametrizacion.services.active_parametrization_service import (
    ActiveParametrizationService,
)
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
from nexa_engine.modules.simulation_draft.persistence.draft_repository import (
    SimulationDraftRepository,
)
from nexa_engine.modules.simulation_draft.services.draft_service import (
    SimulationDraftService,
)


@dataclass
class ApplicationContainer:
    """Contenedor de la aplicación: raíz de inyección de dependencias."""

    store: DocumentStore
    parametrization_store: DocumentStore
    results_repository: ResultsRepository
    snapshots_repository: SnapshotRepository
    certificate_repository: CertificateRepository
    lineage_repository: LineageSnapshotRepository
    hr_repository: HRActiveParametrizationRepository
    hr_upload_repository: HRRepository
    gn_repository: GNActiveParametrizationRepository
    gn_upload_repository: GNRepository
    op_repository: OPActiveParametrizationRepository
    op_upload_repository: OPRepository
    hr_upload_service: HRService
    parametrization_resolver: ParametrizationResolver
    parametrization_provider: ParametrizationProvider
    gn_upload_service: GNService
    op_upload_service: OPService
    cadena_a_parameters_service: CadenaAParametersQueryService
    cadena_b_parameters_service: CadenaBParametersQueryService
    cadena_c_parameters_service: CadenaCParametersQueryService
    panel_service: PanelService
    active_parametrization_service: ActiveParametrizationService
    configuration_store: DocumentStore
    draft_repository: SimulationDraftRepository
    draft_service: SimulationDraftService

    def close(self) -> None:
        """Cerrar recursos (sin efecto para el backend JSON)."""


def _build_parametrization_repos(db_config) -> dict:
    """Crear repositorios de parametrización para cualquier backend (JSON o Cosmos).

    build_parametrization_document_store() ya maneja la distinción de proveedor
    internamente; no es necesario ramificar aquí por tipo de backend.
    """
    param_store = build_parametrization_document_store(db_config)
    hr_version_index = VersionIndexRepository(store=param_store, collection=HR_PARAMETRIZATION_COLLECTION)
    gn_version_index = VersionIndexRepository(store=param_store, collection=GN_PARAMETRIZATION_COLLECTION)
    op_version_index = VersionIndexRepository(store=param_store, collection=OP_PARAMETRIZATION_COLLECTION)
    return {
        "param_store": param_store,
        "hr_repo": HRActiveParametrizationRepository(param_store, hr_version_index),
        "hr_upload_repo": HRRepository(
            store=param_store,
            version_index_repository=hr_version_index,
            codec=HRVersionDocumentCodec(),
        ),
        "gn_repo": GNActiveParametrizationRepository(param_store, gn_version_index),
        "gn_upload_repo": GNRepository(
            store=param_store,
            version_index_repository=gn_version_index,
            codec=GNVersionDocumentCodec(),
        ),
        "op_repo": OPActiveParametrizationRepository(param_store, op_version_index),
        "op_upload_repo": OPRepository(
            store=param_store,
            version_index_repository=op_version_index,
            codec=OPVersionDocumentCodec(),
        ),
    }


def build_container() -> ApplicationContainer:
    """Crea el contenedor de la aplicación a partir de la configuración del entorno."""
    db_config = load_config()
    store = build_provider(db_config)
    configuration_store = build_configuration_document_store(db_config)
    param_repos = _build_parametrization_repos(db_config)

    param_store = param_repos["param_store"]
    hr_repo = param_repos["hr_repo"]
    hr_upload_repo = param_repos["hr_upload_repo"]
    gn_repo = param_repos["gn_repo"]
    gn_upload_repo = param_repos["gn_upload_repo"]
    op_repo = param_repos["op_repo"]
    op_upload_repo = param_repos["op_upload_repo"]
    hr_upload_service = HRService(repository=hr_upload_repo)
    gn_upload_service = GNService(repository=gn_upload_repo)
    op_upload_service = OPService(repository=op_upload_repo)

    resolver = ParametrizationResolver(
        hr_repo=hr_repo, gn_repo=gn_repo, op_repo=op_repo
    )
    provider = ParametrizationProvider.build(resolver=resolver)

    return ApplicationContainer(
        store=store,
        parametrization_store=param_store,
        results_repository=ResultsRepository(configuration_store),
        snapshots_repository=SnapshotRepository(store=store),
        certificate_repository=CertificateRepository(store=store),
        lineage_repository=LineageSnapshotRepository(store=store),
        hr_repository=hr_repo,
        hr_upload_repository=hr_upload_repo,
        gn_repository=gn_repo,
        gn_upload_repository=gn_upload_repo,
        op_repository=op_repo,
        op_upload_repository=op_upload_repo,
        hr_upload_service=hr_upload_service,
        parametrization_resolver=resolver,
        parametrization_provider=provider,
        gn_upload_service=gn_upload_service,
        op_upload_service=op_upload_service,
        cadena_a_parameters_service=CadenaAParametersQueryService(
            hr_repo=hr_repo, op_repo=op_repo, gn_repo=gn_repo
        ),
        cadena_b_parameters_service=CadenaBParametersQueryService(
            hr_repo=hr_repo, op_repo=op_repo
        ),
        cadena_c_parameters_service=CadenaCParametersQueryService(
            hr_repo=hr_repo, op_repo=op_repo
        ),
        panel_service=PanelService(
            op_repo=op_repo, gn_repo=gn_repo
        ),
        active_parametrization_service=ActiveParametrizationService(
            hr_service=hr_upload_service,
            gn_service=gn_upload_service,
            op_service=op_upload_service,
        ),
        configuration_store=configuration_store,
        draft_repository=SimulationDraftRepository(configuration_store),
        draft_service=SimulationDraftService(SimulationDraftRepository(configuration_store)),
    )


__all__ = ["ApplicationContainer", "build_container"]
