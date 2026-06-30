"""Implementación JSON sobre filesystem de :class:`DocumentStore` (FASE 6).

Estructura::

    {JSON_STORAGE_PATH}/{collection.name}/{document_id}.json

Un archivo JSON por documento. Las escrituras son atómicas (archivo temporal +
``os.replace``). El provider es deliberadamente agnóstico al esquema: almacena
el ``dict`` recibido y solo exige que cada documento tenga un ``id`` (y la clave
de partición declarada por la colección, si aplica).

Política de logging: se registran ``provider``, ``collection`` y
``document_id``; nunca payloads completos ni secretos.
"""

from __future__ import annotations

import copy
import logging
import os
from pathlib import Path

from nexa_engine.db.constants.provider_constants import FIELD_ID, PROVIDER_JSON
from nexa_engine.db.exceptions import (
    DbConflictError,
    DbConnectionError,
    DbNotFoundError,
    DbSerializationError,
)
from nexa_engine.db.helpers.atomic_json_writer import read_json, write_json_atomic
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.ports.document_store import DocumentStore

logger = logging.getLogger(__name__)


class JsonDocumentStore(DocumentStore):
    """Almacén documental sobre filesystem con raíz en ``storage_path``."""

    def __init__(self, storage_path: Path) -> None:
        self._root = Path(storage_path)

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------
    def _collection_dir(self, collection: CollectionConfig) -> Path:
        return self._root / collection.name

    @staticmethod
    def _safe_document_id(document_id: str) -> str:
        if not document_id or not isinstance(document_id, str):
            raise DbSerializationError("document id must be a non-empty string")
        if "/" in document_id or "\\" in document_id or document_id in (".", ".."):
            raise DbSerializationError(f"unsafe document id: {document_id!r}")
        return document_id

    def _document_path(self, collection: CollectionConfig, document_id: str) -> Path:
        return self._collection_dir(collection) / f"{self._safe_document_id(document_id)}.json"

    @staticmethod
    def _validate_document(collection: CollectionConfig, document: dict) -> str:
        if not isinstance(document, dict):
            raise DbSerializationError("document must be a dict")
        doc_id = document.get(FIELD_ID)
        if not isinstance(doc_id, str) or not doc_id:
            raise DbSerializationError(
                f"document for collection {collection.name!r} is missing a string '{FIELD_ID}'"
            )
        if collection.partition_key_field:
            pk = document.get(collection.partition_key_field)
            if pk is None or pk == "":
                raise DbSerializationError(
                    f"document {doc_id!r} is missing required partition key "
                    f"'{collection.partition_key_field}'"
                )
        return doc_id

    def _iter_document_paths(self, collection: CollectionConfig) -> list[Path]:
        directory = self._collection_dir(collection)
        if not directory.is_dir():
            return []
        # Orden determinístico para paginación estable y tests reproducibles.
        return sorted(directory.glob("*.json"), key=lambda p: p.stem)

    @staticmethod
    def _decode_token(continuation_token: str | None) -> int:
        if continuation_token is None:
            return 0
        try:
            offset = int(continuation_token)
        except (TypeError, ValueError) as exc:
            raise DbSerializationError(
                f"invalid continuation_token: {continuation_token!r}"
            ) from exc
        if offset < 0:
            raise DbSerializationError(f"invalid continuation_token: {continuation_token!r}")
        return offset

    def _paginate(
        self,
        docs: list[dict],
        *,
        limit: int | None,
        continuation_token: str | None,
    ) -> tuple[list[dict], str | None]:
        offset = self._decode_token(continuation_token)
        window = docs[offset:]
        if limit is None:
            return window, None
        page = window[:limit]
        next_offset = offset + len(page)
        next_token = str(next_offset) if next_offset < len(docs) else None
        return page, next_token

    # ------------------------------------------------------------------
    # API DocumentStore
    # ------------------------------------------------------------------
    def get_record(
        self,
        collection: CollectionConfig,
        document_id: str,
        *,
        partition_value: str | None = None,
    ) -> StoredDocument | None:
        path = self._document_path(collection, document_id)
        logger.debug("[%s] get_record collection=%s id=%s", PROVIDER_JSON, collection.name, document_id)
        if not path.exists():
            return None
        payload = read_json(path)
        if not isinstance(payload, (dict, list)):
            raise DbSerializationError(
                f"record {document_id!r} in {collection.name!r} is not a JSON object or array"
            )
        return StoredDocument(
            id=document_id,
            payload=copy.deepcopy(payload),
            partition_value=partition_value,
        )

    def list_records(
        self,
        collection: CollectionConfig,
        *,
        limit: int | None = None,
        continuation_token: str | None = None,
    ) -> tuple[list[StoredDocument], str | None]:
        logger.debug("[%s] list_records collection=%s", PROVIDER_JSON, collection.name)
        records: list[StoredDocument] = []
        for path in self._iter_document_paths(collection):
            payload = read_json(path)
            if isinstance(payload, (dict, list)):
                records.append(StoredDocument(id=path.stem, payload=copy.deepcopy(payload)))
        return self._paginate(records, limit=limit, continuation_token=continuation_token)

    def query_records(
        self,
        collection: CollectionConfig,
        filters: dict[str, object],
        *,
        limit: int | None = None,
        continuation_token: str | None = None,
    ) -> tuple[list[StoredDocument], str | None]:
        logger.debug(
            "[%s] query_records collection=%s fields=%s",
            PROVIDER_JSON,
            collection.name,
            sorted(filters.keys()),
        )
        all_records, _ = self.list_records(collection)
        if filters:
            matched = [
                record
                for record in all_records
                if isinstance(record.payload, dict)
                and all(record.payload.get(field) == value for field, value in filters.items())
            ]
        else:
            matched = all_records
        return self._paginate(matched, limit=limit, continuation_token=continuation_token)

    def upsert_record(
        self,
        collection: CollectionConfig,
        record: StoredDocument,
    ) -> StoredDocument:
        document_id = self._safe_document_id(record.id)
        path = self._document_path(collection, document_id)
        payload = copy.deepcopy(record.payload)
        if not isinstance(payload, (dict, list)):
            raise DbSerializationError("record payload must be a JSON object or array")
        write_json_atomic(path, payload)
        logger.info("[%s] upsert_record collection=%s id=%s", PROVIDER_JSON, collection.name, document_id)
        return StoredDocument(
            id=document_id,
            payload=copy.deepcopy(payload),
            partition_value=record.partition_value,
        )

    def put_immutable(
        self,
        collection: CollectionConfig,
        record: StoredDocument,
    ) -> StoredDocument:
        document_id = self._safe_document_id(record.id)
        path = self._document_path(collection, document_id)
        if path.exists():
            raise DbConflictError(
                f"immutable document {document_id!r} already exists in {collection.name!r}"
            )
        payload = copy.deepcopy(record.payload)
        if not isinstance(payload, (dict, list)):
            raise DbSerializationError("record payload must be a JSON object or array")
        write_json_atomic(path, payload)
        logger.info("[%s] put_immutable collection=%s id=%s", PROVIDER_JSON, collection.name, document_id)
        return StoredDocument(
            id=document_id,
            payload=copy.deepcopy(payload),
            partition_value=record.partition_value,
        )

    def get_snapshot(
        self,
        collection: CollectionConfig,
        document_id: str,
        *,
        partition_value: str | None = None,
    ) -> StoredDocument | None:
        logger.debug("[%s] get_snapshot collection=%s id=%s", PROVIDER_JSON, collection.name, document_id)
        return self.get_record(collection, document_id, partition_value=partition_value)

    def get(
        self,
        collection: CollectionConfig,
        document_id: str,
        *,
        partition_value: str | None = None,
    ) -> dict | None:
        path = self._document_path(collection, document_id)
        logger.debug("[%s] get collection=%s id=%s", PROVIDER_JSON, collection.name, document_id)
        if not path.exists():
            return None
        doc = read_json(path)
        if not isinstance(doc, dict):
            raise DbSerializationError(
                f"document {document_id!r} in {collection.name!r} is not a JSON object"
            )
        return doc

    def list(
        self,
        collection: CollectionConfig,
        *,
        limit: int | None = None,
        continuation_token: str | None = None,
    ) -> tuple[list[dict], str | None]:
        logger.debug("[%s] list collection=%s", PROVIDER_JSON, collection.name)
        docs: list[dict] = []
        for path in self._iter_document_paths(collection):
            doc = read_json(path)
            if isinstance(doc, dict):
                docs.append(doc)
        return self._paginate(docs, limit=limit, continuation_token=continuation_token)

    def query(
        self,
        collection: CollectionConfig,
        filters: dict[str, object],
        *,
        limit: int | None = None,
        continuation_token: str | None = None,
    ) -> tuple[list[dict], str | None]:
        logger.debug(
            "[%s] query collection=%s fields=%s",
            PROVIDER_JSON,
            collection.name,
            sorted(filters.keys()),
        )
        all_docs, _ = self.list(collection)
        if filters:
            matched = [
                doc
                for doc in all_docs
                if all(doc.get(field) == value for field, value in filters.items())
            ]
        else:
            matched = all_docs
        return self._paginate(matched, limit=limit, continuation_token=continuation_token)

    def upsert(
        self,
        collection: CollectionConfig,
        document: dict,
    ) -> dict:
        doc_id = self._validate_document(collection, document)
        path = self._document_path(collection, doc_id)
        write_json_atomic(path, document)
        logger.info("[%s] upsert collection=%s id=%s", PROVIDER_JSON, collection.name, doc_id)
        return document

    def delete(
        self,
        collection: CollectionConfig,
        document_id: str,
        *,
        partition_value: str | None = None,
    ) -> None:
        path = self._document_path(collection, document_id)
        if not path.exists():
            raise DbNotFoundError(
                f"document {document_id!r} not found in collection {collection.name!r}"
            )
        path.unlink()
        logger.info("[%s] delete collection=%s id=%s", PROVIDER_JSON, collection.name, document_id)

    def ping(self) -> None:
        """Verify the storage root is accessible for readiness probes."""
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            if not os.access(self._root, os.R_OK | os.W_OK):
                raise DbConnectionError("JSON storage root is not readable/writable")
        except DbConnectionError:
            raise
        except Exception as exc:
            raise DbConnectionError("JSON storage not accessible") from exc


__all__ = ["JsonDocumentStore"]
