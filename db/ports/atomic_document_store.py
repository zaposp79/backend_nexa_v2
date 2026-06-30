"""Puerto opcional para providers con batch transaccional por partición."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from nexa_engine.db.models.atomic_write import AtomicWritePrecondition, AtomicWriteResult
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument


@runtime_checkable
class AtomicDocumentStore(Protocol):
    """Capacidad adicional de batch atómico sin ampliar el contrato base."""

    def upsert_records_atomic(
        self,
        collection: CollectionConfig,
        records: list[StoredDocument],
        *,
        partition_value: str | None = None,
        precondition: AtomicWritePrecondition | None = None,
    ) -> AtomicWriteResult:
        """Crea o reemplaza registros de una colección en una sola partición."""


__all__ = ["AtomicDocumentStore"]
