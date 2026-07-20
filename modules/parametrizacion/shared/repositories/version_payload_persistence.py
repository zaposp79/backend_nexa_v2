"""Persistencia del payload de versión en el DocumentStore."""

from __future__ import annotations

from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.ports.document_store import DocumentStore


def save_version_payload_and_index(
    *,
    store: DocumentStore,
    collection: CollectionConfig,
    payload_record: StoredDocument,
    **_kwargs,
) -> None:
    """Guarda el payload de versión en el DocumentStore.

    Escribe únicamente el documento de datos (sin índice 'versions').
    La versión activa se identifica directamente por domain + status='active'.
    """
    store.upsert_record(collection, payload_record)


__all__ = ["save_version_payload_and_index"]
