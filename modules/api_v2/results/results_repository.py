"""Repositorio de resultados de simulación v2 en CosmosDB.

Container: simulation (mismo que v1, COSMOS_CONTAINER_CONFIGURATION)
Partition key: client_id
Distinguidor de v1: type="results_v2"
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from nexa_engine.db.ports.document_store import CollectionConfig, DocumentStore
from nexa_engine.modules.shared.exceptions import NotFoundError

logger = logging.getLogger("nexa.v2.results_repo")

_COLLECTION = CollectionConfig(
    name="simulation",
    partition_key_field="client_id",
)


class V2SimulationResultsRepository:
    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    def save(self, doc: Dict[str, Any]) -> None:
        self._store.upsert(_COLLECTION, doc)
        logger.info("[v2] Resultado persistido: id=%s client_id=%s", doc.get("id"), doc.get("client_id"))

    def get(self, simulation_id: str) -> Dict[str, Any]:
        docs, _ = self._store.query(
            _COLLECTION, {"type": "results_v2", "id": simulation_id}
        )
        if not docs:
            raise NotFoundError("SimulationV2", simulation_id)
        return docs[0]
