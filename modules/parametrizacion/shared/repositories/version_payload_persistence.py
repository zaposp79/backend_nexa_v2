"""Persistencia coordinada de payload de versión e índice."""

from __future__ import annotations

from nexa_engine.db.exceptions import DbNotFoundError
from nexa_engine.db.models.atomic_write import AtomicWritePrecondition
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.ports.atomic_document_store import AtomicDocumentStore
from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)
from nexa_engine.modules.parametrizacion.shared.models.version_summary import VersionSummary


def save_version_payload_and_index(
    *,
    store: DocumentStore,
    collection: CollectionConfig,
    version_index_repository: VersionIndexRepository,
    payload_record: StoredDocument,
    summary: VersionSummary,
) -> None:
    """Guarda payload e índice usando batch atómico si el store lo soporta."""
    index_record = version_index_repository.build_append_record(summary)

    if isinstance(store, AtomicDocumentStore):
        precondition = (
            AtomicWritePrecondition(
                logical_id=index_record.id,
                expected_etag=index_record.etag,
            )
            if index_record.etag is not None
            else None
        )
        store.upsert_records_atomic(
            collection,
            [payload_record, index_record],
            precondition=precondition,
        )
        return

    previous_record = store.get_record(collection, payload_record.id)
    store.upsert_record(collection, payload_record)
    try:
        version_index_repository.save_record(index_record)
    except Exception:
        if previous_record is None:
            _delete_record_if_present(store, collection, payload_record.id)
        else:
            store.upsert_record(collection, previous_record)
        raise


def _delete_record_if_present(
    store: DocumentStore,
    collection: CollectionConfig,
    version_id: str,
) -> None:
    try:
        store.delete(collection, version_id)
    except DbNotFoundError:
        return


__all__ = ["save_version_payload_and_index"]
