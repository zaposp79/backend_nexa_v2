"""Fábrica de proveedores y punto de entrada de composición."""

from __future__ import annotations

import logging

from nexa_engine.db.config import DbConfig, load_config
from nexa_engine.db.constants.provider_constants import PROVIDER_COSMOS, PROVIDER_JSON
from nexa_engine.db.exceptions import DbConfigurationError
from nexa_engine.db.ports.document_store import DocumentStore

logger = logging.getLogger(__name__)

# Module-level cache: one instance per process lifetime.
# Safe in production (single process, stable config).
# Risk under pytest: hot-reload can reuse a stale instance across tests.
# Mitigation: call reset_provider() in test teardown / conftest fixtures.
_cached_provider: DocumentStore | None = None
_cached_parametrization_provider: DocumentStore | None = None


def build_provider(config: DbConfig) -> DocumentStore:
    """Construir el DocumentStore para snapshots, lineage y certificados (siempre JSON local).

    Los resultados de simulación van a COSMOS_CONTAINER_SIMULATION via
    build_configuration_document_store(). Los borradores draft también usan ese store.
    La parametrización usa COSMOS_CONTAINER_PARAMETRIZATION via build_parametrization_document_store().
    """
    from nexa_engine.db.providers.json_document_store import JsonDocumentStore

    logger.info("[db.factory] main store=json path=%s", config.json_storage_path)
    return JsonDocumentStore(config.json_storage_path)


def build_parametrization_document_store(settings: DbConfig) -> DocumentStore:
    """Construir el DocumentStore de parametrización (HR/GN/OP).

    En Cosmos usa exclusivamente COSMOS_CONTAINER_PARAMETRIZATION.
    """
    if settings.provider == PROVIDER_JSON:
        from nexa_engine.db.providers.json_document_store import JsonDocumentStore
        from nexa_engine.modules.shared.config.config import PARAMETRIZATION_DIR

        logger.info("[db.factory] parametrization_store=json path=%s", PARAMETRIZATION_DIR)
        return JsonDocumentStore(PARAMETRIZATION_DIR)

    if settings.provider == PROVIDER_COSMOS:
        if settings.cosmos is None:  # pragma: no cover - load_config guarantees this
            raise DbConfigurationError(
                "Cosmos parametrization store selected but settings are unresolved"
            )
        from nexa_engine.db.providers.cosmos_document_store import CosmosDocumentStore
        from nexa_engine.db.config import CosmosSettings

        container_name = settings.cosmos.container_parametrization
        if not container_name:
            raise DbConfigurationError(
                "COSMOS_CONTAINER_PARAMETRIZATION es obligatorio cuando DB_PROVIDER=cosmos"
            )
        cfg = CosmosSettings(
            endpoint=settings.cosmos.endpoint,
            key=settings.cosmos.key,
            database=settings.cosmos.database,
            container=container_name,
        )
        logger.info("[db.factory] parametrization_store=cosmos container=%s", container_name)
        return CosmosDocumentStore(cfg)

    raise DbConfigurationError(f"unknown parametrization provider: {settings.provider!r}")


def build_configuration_document_store(config: DbConfig) -> DocumentStore:
    """Construir el DocumentStore para la colección 'configuration' (simulation drafts).

    En Cosmos usa exclusivamente COSMOS_CONTAINER_SIMULATION.
    """
    if config.provider == PROVIDER_JSON:
        from nexa_engine.db.providers.json_document_store import JsonDocumentStore

        logger.info("[db.factory] configuration_store=json path=%s", config.json_storage_path)
        return JsonDocumentStore(config.json_storage_path)

    if config.provider == PROVIDER_COSMOS:
        if config.cosmos is None:  # pragma: no cover - load_config guarantees this
            raise DbConfigurationError(
                "Cosmos configuration store selected but settings are unresolved"
            )
        from nexa_engine.db.providers.cosmos_document_store import CosmosDocumentStore
        from nexa_engine.db.config import CosmosSettings

        container_name = config.cosmos.container_simulation
        if not container_name:
            raise DbConfigurationError(
                "COSMOS_CONTAINER_SIMULATION es obligatorio cuando DB_PROVIDER=cosmos"
            )
        cfg = CosmosSettings(
            endpoint=config.cosmos.endpoint,
            key=config.cosmos.key,
            database=config.cosmos.database,
            container=container_name,
        )
        logger.info(
            "[db.factory] configuration_store=cosmos container=%s", container_name
        )
        return CosmosDocumentStore(cfg)

    raise DbConfigurationError(f"unknown provider for configuration store: {config.provider!r}")


def get_provider() -> DocumentStore:
    """Obtener el DocumentStore a nivel de proceso."""
    global _cached_provider
    if _cached_provider is None:
        _cached_provider = build_provider(load_config())
    return _cached_provider


def reset_provider() -> None:
    """Descartar el proveedor en caché para que se resuelva nuevamente."""
    global _cached_provider, _cached_parametrization_provider
    _cached_provider = None
    _cached_parametrization_provider = None


def get_parametrization_store() -> DocumentStore:
    """Obtener el DocumentStore de parametrización a nivel de proceso."""
    global _cached_parametrization_provider
    if _cached_parametrization_provider is None:
        _cached_parametrization_provider = build_parametrization_document_store(load_config())
    return _cached_parametrization_provider


__all__ = [
    "build_provider",
    "build_parametrization_document_store",
    "build_configuration_document_store",
    "get_provider",
    "get_parametrization_store",
    "reset_provider",
]
