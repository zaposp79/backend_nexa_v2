"""Repositorio de lectura GN: lee la parametrización GN activa vía DocumentStore.

Busca en Cosmos el documento con domain="gn" y status="active".
No usa VersionIndexRepository ni lee del filesystem local.
"""

from __future__ import annotations

from typing import Any, Dict

from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.parametrizacion.gn.repositories.collections import (
    GN_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.shared.exceptions import ParametrizationNotFoundError


class GNActiveParametrizationRepository:
    """Lee la data de parametrización GN activa desde Cosmos."""

    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    def get_active_data(self) -> Dict[str, Any]:
        docs, _ = self._store.query(
            GN_PARAMETRIZATION_COLLECTION,
            {"domain": "gn", "status": "active"},
        )
        if docs:
            doc = docs[0]
            payload = doc.get("payload")
            if isinstance(payload, dict) and payload:
                if "version_id" not in payload:
                    payload = {**payload, "version_id": doc.get("id", "unknown")}
                return payload
        raise ParametrizationNotFoundError("gn", None)

    def get_data_by_id(self, document_id: str) -> Dict[str, Any]:
        """Lee una versión específica por su ID de documento."""
        record = self._store.get_record(GN_PARAMETRIZATION_COLLECTION, document_id)
        if record is None:
            raise ParametrizationNotFoundError("gn", document_id)
        payload = record.payload if hasattr(record, "payload") else record.get("payload")
        if not isinstance(payload, dict) or not payload:
            raise ParametrizationNotFoundError("gn", document_id)
        return payload


__all__ = ["GNActiveParametrizationRepository"]
