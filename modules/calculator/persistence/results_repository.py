"""Repositorio de resultados de cálculo de precios.

Persiste y recupera resultados en el container 'simulation' de CosmosDB
(COSMOS_CONTAINER_SIMULATION), con partition key /client_id.

En JSON local la collection mapea a storage/simulation/{id}.json.

El campo ``id`` (== simulation_id) y ``client_id`` se añaden internamente
al documento; se eliminan al leer para preservar el esquema HTTP.

Las visiones recuperan por simulation_id mediante query cross-partition
(no necesitan conocer client_id).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.shared.exceptions import NotFoundError

_COLLECTION = CollectionConfig(name="simulation", partition_key_field="client_id")

# Campos de infraestructura que no forman parte del contrato HTTP.
_INTERNAL_FIELDS = {"id", "client_id"}


class ResultsRepository:
    """Almacena y recupera resultados de cálculo de precios."""

    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())

    def save(self, data: Dict[str, Any]) -> str:
        """Persiste el resultado usando data['simulation_id'] como id.

        Requiere data['client_id'] para la partition key de Cosmos.

        Returns:
            El simulation_id del registro guardado.
        """
        simulation_id = data["simulation_id"]
        client_id = data.get("client_id", "")
        document = {"id": simulation_id, "client_id": client_id, **data}
        self._store.upsert(_COLLECTION, document)
        return simulation_id

    def get(self, result_id: str) -> Dict[str, Any]:
        """Retorna el resultado o lanza NotFoundError.

        Usa query cross-partition por simulation_id: las visiones solo conocen
        el simulation_id, no el client_id (partition key).
        """
        docs, _ = self._store.query(_COLLECTION, {"simulation_id": result_id})
        if not docs:
            raise NotFoundError("PricingResult", result_id)
        doc = docs[0]
        return {k: v for k, v in doc.items() if k not in _INTERNAL_FIELDS}

    def exists(self, result_id: str) -> bool:
        docs, _ = self._store.query(_COLLECTION, {"simulation_id": result_id})
        return bool(docs)
