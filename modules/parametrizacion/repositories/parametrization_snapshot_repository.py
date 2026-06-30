"""ParametrizationSnapshotRepository — DB-backed certified parametrization snapshots.

Persiste snapshots inmutables de parametrización usando DocumentStore.put_immutable().
Cada snapshot representa los datos de parametrización de un módulo en el momento
de la certificación.

Colección::

    parametrization_snapshots

Formato de documento::

    {
      "id": "v2-7__business_rules",
      "version": "v2-7",
      "module": "business_rules",
      "schema_version": "parametrization_snapshot_v1",
      "hash": "<sha256 hex>",
      "payload": {...},
      "created_at": "<ISO 8601 UTC>"
    }

Formato de id (seguro para filesystem y Cosmos)::

    "{version}__{module}"  — doble guión bajo, sin barras ni caracteres especiales

Módulos válidos::

    business_rules, gn, hr, op

Garantías::
  - put_snapshot es create-only: lanza ParametrizationSnapshotConflictError si ya existe
  - get_snapshot retorna el snapshot o None (nunca lanza si no existe)
  - Los IDs nunca contienen '/' ni '\\' (validado antes de escritura)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Final

from nexa_engine.db.exceptions import DbConflictError
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.ports.document_store import DocumentStore

logger = logging.getLogger(__name__)

_COLLECTION: Final = CollectionConfig(name="parametrization_snapshots")
_SCHEMA_VERSION: Final = "parametrization_snapshot_v1"
_ALLOWED_MODULES: Final = frozenset({"business_rules", "gn", "hr", "op"})
_ID_SEPARATOR: Final = "__"


class ParametrizationSnapshotConflictError(Exception):
    """Raised when attempting to overwrite an existing immutable snapshot."""

    def __init__(self, version: str, module: str) -> None:
        self.version = version
        self.module = module
        super().__init__(
            f"Parametrization snapshot already exists: version={version!r} module={module!r}. "
            "Snapshots are immutable — create a new version to recertify."
        )


class ParametrizationSnapshotValidationError(ValueError):
    """Raised for invalid version or module arguments."""


class ParametrizationSnapshotRepository:
    """Repositorio de snapshots certificados de parametrización.

    Wraps DocumentStore.put_immutable() y get_snapshot() con validaciones
    de módulo, formato de id, y conversión de dominio.
    """

    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _build_id(version: str, module: str) -> str:
        """Construye id seguro: '{version}__{module}' sin barras."""
        return f"{version}{_ID_SEPARATOR}{module}"

    @staticmethod
    def _validate_module(module: str) -> None:
        if module not in _ALLOWED_MODULES:
            raise ParametrizationSnapshotValidationError(
                f"Invalid module {module!r}. Allowed: {sorted(_ALLOWED_MODULES)}"
            )

    @staticmethod
    def _validate_version(version: str) -> None:
        if not version or not isinstance(version, str):
            raise ParametrizationSnapshotValidationError("version must be a non-empty string")
        if "/" in version or "\\" in version:
            raise ParametrizationSnapshotValidationError(
                f"version {version!r} contains unsafe characters"
            )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def put_snapshot(
        self,
        version: str,
        module: str,
        payload: dict,
        *,
        content_hash: str = "",
    ) -> dict:
        """Persiste snapshot inmutable.

        Args:
            version: Versión de certificación (e.g. 'v2-7').
            module: Módulo de parametrización ('business_rules', 'gn', 'hr', 'op').
            payload: Datos de parametrización completos.
            content_hash: SHA-256 hex del payload canónico (opcional, para auditoría).

        Returns:
            El documento persistido como dict.

        Raises:
            ParametrizationSnapshotValidationError: versión o módulo inválido.
            ParametrizationSnapshotConflictError: snapshot ya existe.
        """
        self._validate_version(version)
        self._validate_module(module)

        doc_id = self._build_id(version, module)
        document: dict = {
            "version": version,
            "module": module,
            "schema_version": _SCHEMA_VERSION,
            "hash": content_hash,
            "payload": payload,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        record = StoredDocument(id=doc_id, payload=document)

        try:
            stored = self._store.put_immutable(_COLLECTION, record)
        except DbConflictError as exc:
            raise ParametrizationSnapshotConflictError(version, module) from exc

        logger.info(
            "[parametrization_snapshot] put version=%s module=%s id=%s",
            version,
            module,
            doc_id,
        )
        result = dict(stored.payload)  # type: ignore[arg-type]
        result["id"] = stored.id
        return result

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def get_snapshot(self, version: str, module: str) -> dict | None:
        """Retorna snapshot por versión y módulo, o None si no existe.

        Args:
            version: Versión de certificación (e.g. 'v2-7').
            module: Módulo de parametrización.

        Returns:
            Documento como dict (incluyendo 'id') o None.

        Raises:
            ParametrizationSnapshotValidationError: versión o módulo inválido.
        """
        self._validate_version(version)
        self._validate_module(module)

        doc_id = self._build_id(version, module)
        record = self._store.get_snapshot(_COLLECTION, doc_id)
        if record is None:
            return None

        result = dict(record.payload)  # type: ignore[arg-type]
        result["id"] = record.id
        return result


__all__ = [
    "ParametrizationSnapshotRepository",
    "ParametrizationSnapshotConflictError",
    "ParametrizationSnapshotValidationError",
]
