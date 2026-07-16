"""Repositorio de borradores de simulación.

Persiste documentos en la colección "configuration" de CosmosDB con
partition key /client_id.

Para operaciones de punto (get/delete) se necesita el client_id exacto.
Para búsquedas por id sin conocer el client_id se usa list() cross-partition
+ filtro en Python — la misma estrategia que funciona en GET /all.
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
        """Crea o reemplaza un borrador. El doc debe tener 'id' y 'client_id'."""
        return self._store.upsert(_COLLECTION, document)

    def find_by_id(self, draft_id: str) -> dict:
        """Busca un borrador por id sin conocer su client_id (partición).

        Hace un scan cross-partition (igual que list_all) y filtra en Python.
        Esto funciona porque CosmosDB soporta enable_cross_partition_query=True.
        """
        docs, _ = self._store.list(_COLLECTION)
        for doc in docs:
            if doc.get("id") == draft_id:
                return doc
        raise NotFoundError("SimulationDraft", draft_id)

    def list_all(self) -> list[dict]:
        """Retorna todos los borradores del container."""
        docs, _ = self._store.list(_COLLECTION)
        return docs

    def find_by_status(self, status: str) -> list[dict]:
        """Retorna todos los borradores con el status indicado (cross-partition)."""
        docs, _ = self._store.query(_COLLECTION, {"status": status})
        return docs

    def relocate(self, old_client_id: str, document: dict) -> dict:
        """Elimina el doc de la partición antigua y lo guarda en la nueva.

        Necesario cuando client_id cambia: en CosmosDB la partition key es
        inmutable, se debe borrar + re-insertar en la nueva partición.
        """
        try:
            self._store.delete(_COLLECTION, document["id"], partition_value=old_client_id)
        except DbNotFoundError:
            pass
        return self._store.upsert(_COLLECTION, document)

    def delete_by_partition(self, draft_id: str, client_id: str) -> None:
        """Elimina el borrador pasando el client_id (partition key) explícito."""
        try:
            self._store.delete(_COLLECTION, draft_id, partition_value=client_id)
        except DbNotFoundError as exc:
            raise NotFoundError("SimulationDraft", draft_id) from exc


__all__ = ["SimulationDraftRepository"]
