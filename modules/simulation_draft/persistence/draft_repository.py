"""Repositorio de borradores de simulación.

Persiste documentos en la colección "configuration" de CosmosDB,
particionados por client_id. Compatible también con el provider JSON local.
"""

from __future__ import annotations

from nexa_engine.db.exceptions import DbNotFoundError
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.shared.exceptions import NotFoundError

_COLLECTION = CollectionConfig(name="configuration", partition_key_field="client_id")


class SimulationDraftRepository:
    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    def save(self, document: dict) -> dict:
        """Crea o reemplaza un borrador. El documento debe tener 'id' y 'client_id'."""
        return self._store.upsert(_COLLECTION, document)

    def get(self, draft_id: str, client_id: str) -> dict:
        """Retorna el borrador o lanza NotFoundError."""
        try:
            doc = self._store.get(_COLLECTION, draft_id, partition_value=client_id)
        except DbNotFoundError as exc:
            raise NotFoundError("SimulationDraft", draft_id) from exc
        if doc is None:
            raise NotFoundError("SimulationDraft", draft_id)
        return doc

    def list_all(self) -> list[dict]:
        """Retorna todos los borradores del container (sin filtro de partición)."""
        docs, _ = self._store.list(_COLLECTION)
        return docs

    def delete(self, draft_id: str, client_id: str) -> None:
        """Elimina el borrador. Lanza NotFoundError si no existe."""
        try:
            self._store.delete(_COLLECTION, draft_id, partition_value=client_id)
        except DbNotFoundError as exc:
            raise NotFoundError("SimulationDraft", draft_id) from exc

    def exists(self, draft_id: str, client_id: str) -> bool:
        try:
            return self._store.get(_COLLECTION, draft_id, partition_value=client_id) is not None
        except DbNotFoundError:
            return False


__all__ = ["SimulationDraftRepository"]
