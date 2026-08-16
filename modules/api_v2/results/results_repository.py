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

    def list_simulations(
        self,
        *,
        client_id: str | None = None,
        id_draft: str | None = None,
        limit: int = 50,
    ) -> list[Dict[str, Any]]:
        """Devuelve resúmenes de todas las simulaciones v2.

        Proyecta solo los campos de cabecera; no carga meses ni visiones.
        """
        filters: Dict[str, Any] = {"type": "results_v2"}
        if client_id:
            filters["client_id"] = client_id
        if id_draft:
            filters["id_draft"] = id_draft

        docs, _ = self._store.query(_COLLECTION, filters, limit=limit)

        _SUMMARY_FIELDS = (
            "id", "client_id", "type", "domain", "id_draft", "simulation_id",
            "version", "motor", "calculated_at", "created_at",
            "cliente", "servicio", "tipo_cliente", "antiguedad_cliente",
            "periodo_pago", "fecha_inicio", "duracion_meses", "ciudad", "sede",
        )
        return [
            {field: doc.get(field) for field in _SUMMARY_FIELDS}
            for doc in docs
        ]
