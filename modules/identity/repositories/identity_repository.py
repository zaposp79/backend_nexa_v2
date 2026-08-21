"""Repositorio de identidades — abstrae CosmosDB del dominio.

Container: parameterization (COSMOS_CONTAINER_PARAMETRIZATION)
Partition key field: domain
Partition value: identities

id == identityId → point reads O(1) con store.get().
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from nexa_engine.db.ports.document_store import CollectionConfig, DocumentStore
from nexa_engine.modules.shared.exceptions import NotFoundError

logger = logging.getLogger("nexa.identity.repository")

_COLLECTION = CollectionConfig(name="identities", partition_key_field="domain")
_PARTITION = "identities"


class IdentityRepository:
    """CRUD de identidades sobre DocumentStore (CosmosDB o JSON local)."""

    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def create(self, doc: dict) -> dict:
        """Persiste una identidad nueva. Lanza DbConflictError si ya existe."""
        # _validate_document exige domain antes de que upsert lo inyecte → lo ponemos explícito
        stored = self._store.upsert(_COLLECTION, {**doc, "domain": _PARTITION})
        logger.info("[identity] created id=%s alias=%s", doc.get("id"), doc.get("alias"))
        return stored

    def update_last_seen(self, identity_id: str, last_seen_at: str) -> dict:
        """Actualiza lastSeenAt sin modificar ningún otro campo."""
        doc = self._get_raw(identity_id)
        doc["lastSeenAt"] = last_seen_at
        stored = self._store.upsert(_COLLECTION, {**doc, "domain": _PARTITION})
        logger.info("[identity] lastSeenAt updated id=%s ts=%s", identity_id, last_seen_at)
        return stored

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def get_by_identity_id(self, identity_id: str) -> dict:
        """Retorna el documento o lanza NotFoundError."""
        return self._get_raw(identity_id)

    def exists(self, identity_id: str) -> bool:
        """True si existe una identidad con ese id."""
        doc = self._store.get(_COLLECTION, identity_id, partition_value=_PARTITION)
        return doc is not None

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _get_raw(self, identity_id: str) -> dict:
        doc = self._store.get(_COLLECTION, identity_id, partition_value=_PARTITION)
        if doc is None:
            raise NotFoundError("Identity", identity_id)
        return doc
