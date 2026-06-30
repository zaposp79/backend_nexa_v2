"""Repositorio de resultados de cálculo de precios.

Persiste y recupera resultados como documentos JSON via el DocumentStore
transversal (FASE DB.2). El backend activo (JSON / Cosmos) se resuelve
fuera de este repositorio — se recibe por constructor desde el composition
root (db.container.build_container).

Layout con el provider JSON:
    storage/simulation_results/{simulation_id}.json

El campo ``id`` se añade internamente al documento para cumplir el contrato
de DocumentStore y se elimina al leer, preservando el esquema de respuesta
HTTP sin cambios.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

from nexa_engine.db.exceptions import DbNotFoundError
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.shared.exceptions import NotFoundError

_COLLECTION = CollectionConfig(name="simulation_results")


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

        Returns:
            El simulation_id del registro guardado.
        """
        simulation_id = data["simulation_id"]
        document = {"id": simulation_id, **data}
        self._store.upsert(_COLLECTION, document)
        return simulation_id

    def get(self, result_id: str) -> Dict[str, Any]:
        """Retorna el resultado o lanza NotFoundError."""
        try:
            doc = self._store.get(_COLLECTION, result_id)
        except DbNotFoundError as exc:
            raise NotFoundError("PricingResult", result_id) from exc
        if doc is None:
            raise NotFoundError("PricingResult", result_id)
        # Strip the ``id`` added for DocumentStore; it is not part of the
        # result contract exposed via HTTP.
        return {k: v for k, v in doc.items() if k != "id"}

    def exists(self, result_id: str) -> bool:
        return self._store.get(_COLLECTION, result_id) is not None
