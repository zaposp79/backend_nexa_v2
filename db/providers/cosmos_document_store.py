"""Implementación Cosmos DB de :class:`DocumentStore` (FASE DB.7).

ESTADO: PREPARADO, NO ACTIVO. Este provider solo se construye desde la factory
cuando ``DB_PROVIDER=cosmos`` y toda la configuración de Cosmos está presente.
El import de ``azure.cosmos`` se difiere hasta la construcción para que un
despliegue puramente JSON no requiera instalar ``azure-cosmos``.

La topología container/partition-key por colección lógica NO se inventa aquí.
El ``partition_key_field`` de una colección nombra el campo del documento usado
como valor de la partition key de Cosmos; el container viene de configuración.
Toda colección cuya topología Cosmos no esté documentada queda POSTERGADA; ver
``docs`` / reporte de FASE DB. NO se realiza dual-write estilo
``get_active_version``.

El soporte de query sigue el contrato del puerto: igualdad sobre campos de
primer nivel, combinada solo con AND.
"""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING

from nexa_engine.db.config import CosmosSettings
from nexa_engine.db.constants.provider_constants import FIELD_ID, PROVIDER_COSMOS
from nexa_engine.db.exceptions import (
    DbConcurrencyError,
    DbConflictError,
    DbConnectionError,
    DbNotFoundError,
    DbSerializationError,
)
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.atomic_write import AtomicWritePrecondition, AtomicWriteResult
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.ports.atomic_document_store import AtomicDocumentStore
from nexa_engine.db.ports.document_store import DocumentStore

if TYPE_CHECKING:  # pragma: no cover - solo tipado
    pass

logger = logging.getLogger(__name__)


class _InjectedCosmosExceptions:
    """Excepciones mínimas para tests con cliente fake sin azure-cosmos."""

    class CosmosHttpResponseError(Exception):
        status_code = 500

    class CosmosResourceNotFoundError(CosmosHttpResponseError):
        status_code = 404

    class CosmosResourceExistsError(CosmosHttpResponseError):
        status_code = 409


class CosmosDocumentStore(DocumentStore, AtomicDocumentStore):
    """Almacén documental sobre Cosmos. Se construye solo si Cosmos está seleccionado."""

    _RECORD_COLLECTION_FIELD = "_collection"
    _RECORD_LOGICAL_ID_FIELD = "_logical_id"
    _RECORD_KIND_FIELD = "_kind"
    _RECORD_PARTITION_FIELD = "_pk"
    _RECORD_KIND_VALUE = "stored_document"
    _ETAG_FIELD = "_etag"
    _PRECONDITION_FAILED_STATUS = 412

    def __init__(
        self,
        settings: CosmosSettings | None,
        *,
        container_client: object | None = None,
        cosmos_exceptions: object | None = None,
    ) -> None:
        if container_client is not None:
            self._container = container_client
            self._cosmos_exceptions = cosmos_exceptions or _InjectedCosmosExceptions
            logger.info("[%s] initialized with injected container client", PROVIDER_COSMOS)
            return

        if settings is None:
            raise DbConnectionError("Cosmos settings are required when no container client is injected")

        # Import diferido: azure.cosmos solo es requerido cuando Cosmos está activo.
        try:
            from azure.cosmos import CosmosClient  # type: ignore[import-not-found]
            from azure.cosmos import exceptions as cosmos_exceptions  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - ejercido solo con cosmos seleccionado
            raise DbConnectionError(
                "azure-cosmos is not installed but DB_PROVIDER=cosmos. "
                "Install it with: pip install azure-cosmos"
            ) from exc

        self._cosmos_exceptions = cosmos_exceptions
        try:
            self._client = CosmosClient(settings.endpoint, credential=settings.key)
            database = self._client.get_database_client(settings.database)
            self._container = database.get_container_client(settings.container)
        except cosmos_exceptions.CosmosHttpResponseError as exc:  # pragma: no cover
            raise DbConnectionError(f"Cosmos connection failed: {exc.status_code}") from exc
        logger.info(
            "[%s] connected database=%s container=%s",
            PROVIDER_COSMOS,
            settings.database,
            settings.container,
        )

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_document_id(document_id: str) -> str:
        if not document_id or not isinstance(document_id, str):
            raise DbSerializationError("document id must be a non-empty string")
        return document_id

    @staticmethod
    def _validate_document(collection: CollectionConfig, document: dict) -> tuple[str, object]:
        if not isinstance(document, dict):
            raise DbSerializationError("document must be a dict")
        doc_id = document.get(FIELD_ID)
        if not isinstance(doc_id, str) or not doc_id:
            raise DbSerializationError(
                f"document for collection {collection.name!r} is missing a string '{FIELD_ID}'"
            )
        partition_value: object = None
        if collection.partition_key_field:
            partition_value = document.get(collection.partition_key_field)
            if partition_value is None or partition_value == "":
                raise DbSerializationError(
                    f"document {doc_id!r} is missing required partition key "
                    f"'{collection.partition_key_field}'"
                )
        return doc_id, partition_value

    @classmethod
    def _record_item_id(cls, collection: CollectionConfig, document_id: str) -> str:
        return f"{collection.name}:{cls._safe_document_id(document_id)}"

    @classmethod
    def _record_partition_value(
        cls,
        collection: CollectionConfig,
        record: StoredDocument,
        *,
        explicit_partition_value: str | None = None,
    ) -> str:
        if explicit_partition_value:
            return explicit_partition_value
        if record.partition_value:
            return record.partition_value
        if collection.partition_key_field:
            raise DbSerializationError(
                f"record {record.id!r} is missing partition_value for "
                f"collection {collection.name!r}"
            )
        return collection.name

    # ------------------------------------------------------------------
    # API DocumentStore
    # ------------------------------------------------------------------
    def _record_to_item(
        self,
        collection: CollectionConfig,
        record: StoredDocument,
        *,
        explicit_partition_value: str | None = None,
    ) -> dict:
        if not isinstance(record.payload, (dict, list)):
            raise DbSerializationError("record payload must be a JSON object or array")
        partition_value = self._record_partition_value(
            collection,
            record,
            explicit_partition_value=explicit_partition_value,
        )
        item = {
            FIELD_ID: self._record_item_id(collection, record.id),
            self._RECORD_COLLECTION_FIELD: collection.name,
            self._RECORD_LOGICAL_ID_FIELD: record.id,
            self._RECORD_KIND_FIELD: self._RECORD_KIND_VALUE,
            self._RECORD_PARTITION_FIELD: partition_value,
            "payload": copy.deepcopy(record.payload),
        }
        if collection.partition_key_field:
            item[collection.partition_key_field] = partition_value
        return item

    def _item_to_record(
        self,
        collection: CollectionConfig,
        item: dict,
    ) -> StoredDocument:
        doc_id = item.get(self._RECORD_LOGICAL_ID_FIELD) or item.get(FIELD_ID)
        if not isinstance(doc_id, str) or not doc_id:
            raise DbSerializationError(f"Cosmos item in {collection.name!r} is missing '{FIELD_ID}'")
        payload = item.get("payload")
        if not isinstance(payload, (dict, list)):
            raise DbSerializationError(f"Cosmos item {doc_id!r} is missing logical payload")
        partition_value = None
        raw_partition = item.get(self._RECORD_PARTITION_FIELD)
        if raw_partition is None and collection.partition_key_field:
            raw_partition = item.get(collection.partition_key_field)
        partition_value = None if raw_partition is None else str(raw_partition)
        return StoredDocument(
            id=doc_id,
            payload=copy.deepcopy(payload),
            partition_value=partition_value,
            etag=item.get(self._ETAG_FIELD),
        )

    def get_record(
        self,
        collection: CollectionConfig,
        document_id: str,
        *,
        partition_value: str | None = None,
    ) -> StoredDocument | None:
        logger.debug("[%s] get_record collection=%s id=%s", PROVIDER_COSMOS, collection.name, document_id)
        item_id = self._record_item_id(collection, document_id)
        resolved_partition = partition_value or collection.name
        try:
            item = dict(
                self._container.read_item(
                    item=item_id, partition_key=resolved_partition
                )
            )
        except self._cosmos_exceptions.CosmosResourceNotFoundError:
            return None
        except self._cosmos_exceptions.CosmosHttpResponseError as exc:
            raise DbConnectionError(f"Cosmos get_record failed: {exc.status_code}") from exc
        return self._item_to_record(collection, item)

    def list_records(
        self,
        collection: CollectionConfig,
        *,
        limit: int | None = None,
        continuation_token: str | None = None,
    ) -> tuple[list[StoredDocument], str | None]:
        return self.query_records(
            collection, {}, limit=limit, continuation_token=continuation_token
        )

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
            PROVIDER_COSMOS,
            collection.name,
            sorted(filters.keys()),
        )
        base_filters = [
            f"c.{self._RECORD_KIND_FIELD} = @kind",
            f"c.{self._RECORD_COLLECTION_FIELD} = @collection",
        ]
        payload_filters = [
            f"c.payload.{field} = @p{i}" for i, field in enumerate(filters)
        ]
        where = " AND ".join(base_filters + payload_filters)
        sql = f"SELECT * FROM c WHERE {where}"
        parameters = [
            {"name": "@kind", "value": self._RECORD_KIND_VALUE},
            {"name": "@collection", "value": collection.name},
            *[
            {"name": f"@p{i}", "value": value}
            for i, value in enumerate(filters.values())
            ],
        ]
        kwargs: dict = {"query": sql, "parameters": parameters}
        if limit is not None:
            kwargs["max_item_count"] = limit
        try:
            iterator = self._container.query_items(
                enable_cross_partition_query=True, **kwargs
            )
            pager = iterator.by_page(continuation_token)
            page = next(pager)
            records = [
                self._item_to_record(collection, dict(item))
                for item in page
            ]
            next_token = pager.continuation_token
            return records, next_token
        except StopIteration:
            return [], None
        except self._cosmos_exceptions.CosmosHttpResponseError as exc:
            raise DbConnectionError(f"Cosmos query_records failed: {exc.status_code}") from exc

    def upsert_record(
        self,
        collection: CollectionConfig,
        record: StoredDocument,
    ) -> StoredDocument:
        item = self._record_to_item(collection, record)
        try:
            stored = self._container.upsert_item(item)
        except self._cosmos_exceptions.CosmosResourceExistsError as exc:
            raise DbConflictError(f"conflict upserting {record.id!r}") from exc
        except self._cosmos_exceptions.CosmosHttpResponseError as exc:
            raise DbConnectionError(f"Cosmos upsert_record failed: {exc.status_code}") from exc
        logger.info("[%s] upsert_record collection=%s id=%s", PROVIDER_COSMOS, collection.name, record.id)
        return self._item_to_record(collection, dict(stored))

    def put_immutable(
        self,
        collection: CollectionConfig,
        record: StoredDocument,
    ) -> StoredDocument:
        item = self._record_to_item(collection, record)
        try:
            stored = self._container.create_item(item)
        except self._cosmos_exceptions.CosmosResourceExistsError as exc:
            raise DbConflictError(
                f"immutable document {record.id!r} already exists in {collection.name!r}"
            ) from exc
        except self._cosmos_exceptions.CosmosHttpResponseError as exc:
            raise DbConnectionError(f"Cosmos put_immutable failed: {exc.status_code}") from exc
        logger.info("[%s] put_immutable collection=%s id=%s", PROVIDER_COSMOS, collection.name, record.id)
        return self._item_to_record(collection, dict(stored))

    def get_snapshot(
        self,
        collection: CollectionConfig,
        document_id: str,
        *,
        partition_value: str | None = None,
    ) -> StoredDocument | None:
        logger.debug("[%s] get_snapshot collection=%s id=%s", PROVIDER_COSMOS, collection.name, document_id)
        return self.get_record(collection, document_id, partition_value=partition_value)

    def upsert_records_atomic(
        self,
        collection: CollectionConfig,
        records: list[StoredDocument],
        *,
        partition_value: str | None = None,
        precondition: AtomicWritePrecondition | None = None,
    ) -> AtomicWriteResult:
        """Ejecuta upsert de varios registros en un transactional batch Cosmos."""
        if not records:
            return AtomicWriteResult(records=())

        resolved_partition = self._record_partition_value(
            collection,
            records[0],
            explicit_partition_value=partition_value,
        )
        items = []
        for record in records:
            item = self._record_to_item(
                collection,
                record,
                explicit_partition_value=resolved_partition,
            )
            item_partition = str(item[self._RECORD_PARTITION_FIELD])
            if item_partition != resolved_partition:
                raise DbSerializationError("all records in an atomic batch must share partition")
            items.append(item)

        response = self._execute_atomic_upsert_batch(
            items=items,
            partition_key=resolved_partition,
            precondition=precondition,
        )

        if not self._batch_response_is_successful(response):
            if self._batch_response_has_precondition_failure(response):
                raise DbConcurrencyError("Cosmos transactional batch precondition failed")
            raise DbConnectionError("Cosmos transactional batch failed")

        logger.info(
            "[%s] upsert_records_atomic collection=%s count=%d",
            PROVIDER_COSMOS,
            collection.name,
            len(records),
        )
        return AtomicWriteResult(
            records=tuple(self._item_to_record(collection, item) for item in items)
        )

    def _execute_atomic_upsert_batch(
        self,
        *,
        items: list[dict],
        partition_key: str,
        precondition: AtomicWritePrecondition | None,
    ) -> object:
        if hasattr(self._container, "execute_item_batch"):
            return self._execute_item_batch(
                items=items,
                partition_key=partition_key,
                precondition=precondition,
            )
        return self._execute_transactional_batch_builder(
            items=items,
            partition_key=partition_key,
            precondition=precondition,
        )

    def _execute_item_batch(
        self,
        *,
        items: list[dict],
        partition_key: str,
        precondition: AtomicWritePrecondition | None,
    ) -> object:
        operations = []
        for item in items:
            logical_id = item[self._RECORD_LOGICAL_ID_FIELD]
            kwargs = {}
            if precondition is not None and logical_id == precondition.logical_id:
                kwargs["if_match_etag"] = precondition.expected_etag
            operations.append(("upsert", (item,), kwargs))
        try:
            return self._container.execute_item_batch(
                batch_operations=operations,
                partition_key=partition_key,
            )
        except self._batch_exception_types() as exc:
            if self._exception_has_precondition_failure(exc):
                raise DbConcurrencyError("Cosmos transactional batch precondition failed") from exc
            raise DbConnectionError(
                f"Cosmos transactional batch failed: {getattr(exc, 'status_code', 'unknown')}"
            ) from exc

    def _execute_transactional_batch_builder(
        self,
        *,
        items: list[dict],
        partition_key: str,
        precondition: AtomicWritePrecondition | None,
    ) -> object:
        try:
            batch = self._container.create_transactional_batch(partition_key=partition_key)
            for item in items:
                logical_id = item[self._RECORD_LOGICAL_ID_FIELD]
                if precondition is not None and logical_id == precondition.logical_id:
                    batch.upsert_item(
                        item,
                        etag=precondition.expected_etag,
                        match_condition="IfNotModified",
                    )
                else:
                    batch.upsert_item(item)
            return batch.execute()
        except self._batch_exception_types() as exc:
            if self._exception_has_precondition_failure(exc):
                raise DbConcurrencyError("Cosmos transactional batch precondition failed") from exc
            raise DbConnectionError(
                f"Cosmos transactional batch failed: {getattr(exc, 'status_code', 'unknown')}"
            ) from exc

    def _batch_exception_types(self) -> tuple[type[BaseException], ...]:
        types: list[type[BaseException]] = [self._cosmos_exceptions.CosmosHttpResponseError]
        batch_error = getattr(self._cosmos_exceptions, "CosmosBatchOperationError", None)
        if batch_error is not None:
            types.append(batch_error)
        return tuple(types)

    def _exception_has_precondition_failure(self, exc: BaseException) -> bool:
        if getattr(exc, "status_code", None) == self._PRECONDITION_FAILED_STATUS:
            return True
        operation_responses = getattr(exc, "operation_responses", None)
        if operation_responses is None:
            return False
        return any(
            (
                response.get("statusCode")
                if isinstance(response, dict)
                else getattr(response, "status_code", None)
            )
            == self._PRECONDITION_FAILED_STATUS
            for response in operation_responses
        )

    def _batch_response_has_precondition_failure(self, response: object) -> bool:
        if isinstance(response, list):
            return any(
                operation_response.get("statusCode") == self._PRECONDITION_FAILED_STATUS
                for operation_response in response
                if isinstance(operation_response, dict)
            )
        operation_responses = getattr(response, "operation_responses", None)
        if operation_responses is None:
            return False
        return any(
            getattr(operation_response, "status_code", None) == self._PRECONDITION_FAILED_STATUS
            for operation_response in operation_responses
        )

    def _batch_response_is_successful(self, response: object) -> bool:
        if isinstance(response, list):
            return not self._batch_response_has_precondition_failure(response)
        return bool(getattr(response, "is_successful", False))

    def get(
        self,
        collection: CollectionConfig,
        document_id: str,
        *,
        partition_value: str | None = None,
    ) -> dict | None:
        logger.debug("[%s] get collection=%s id=%s", PROVIDER_COSMOS, collection.name, document_id)
        try:
            return dict(
                self._container.read_item(
                    item=document_id, partition_key=partition_value
                )
            )
        except self._cosmos_exceptions.CosmosResourceNotFoundError:
            return None
        except self._cosmos_exceptions.CosmosHttpResponseError as exc:
            raise DbConnectionError(f"Cosmos get failed: {exc.status_code}") from exc

    def list(
        self,
        collection: CollectionConfig,
        *,
        limit: int | None = None,
        continuation_token: str | None = None,
    ) -> tuple[list[dict], str | None]:
        return self.query(
            collection, {}, limit=limit, continuation_token=continuation_token
        )

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
            PROVIDER_COSMOS,
            collection.name,
            sorted(filters.keys()),
        )
        where = " AND ".join(f"c.{field} = @p{i}" for i, field in enumerate(filters))
        sql = "SELECT * FROM c" + (f" WHERE {where}" if where else "")
        parameters = [
            {"name": f"@p{i}", "value": value}
            for i, value in enumerate(filters.values())
        ]
        kwargs: dict = {"query": sql, "parameters": parameters}
        if limit is not None:
            kwargs["max_item_count"] = limit
        try:
            iterator = self._container.query_items(
                enable_cross_partition_query=True, **kwargs
            )
            pager = iterator.by_page(continuation_token)
            page = next(pager)
            docs = [dict(item) for item in page]
            next_token = pager.continuation_token
            return docs, next_token
        except StopIteration:
            return [], None
        except self._cosmos_exceptions.CosmosHttpResponseError as exc:
            raise DbConnectionError(f"Cosmos query failed: {exc.status_code}") from exc

    def upsert(
        self,
        collection: CollectionConfig,
        document: dict,
    ) -> dict:
        doc_id, _ = self._validate_document(collection, document)
        try:
            stored = self._container.upsert_item(document)
        except self._cosmos_exceptions.CosmosResourceExistsError as exc:
            raise DbConflictError(f"conflict upserting {doc_id!r}") from exc
        except self._cosmos_exceptions.CosmosHttpResponseError as exc:
            raise DbConnectionError(f"Cosmos upsert failed: {exc.status_code}") from exc
        logger.info("[%s] upsert collection=%s id=%s", PROVIDER_COSMOS, collection.name, doc_id)
        return dict(stored)

    def delete(
        self,
        collection: CollectionConfig,
        document_id: str,
        *,
        partition_value: str | None = None,
    ) -> None:
        record_item_id = self._record_item_id(collection, document_id)
        record_partition = partition_value or collection.name
        try:
            self._container.delete_item(item=record_item_id, partition_key=record_partition)
        except self._cosmos_exceptions.CosmosResourceNotFoundError as exc:
            try:
                self._container.delete_item(item=document_id, partition_key=partition_value)
            except self._cosmos_exceptions.CosmosResourceNotFoundError as legacy_exc:
                raise DbNotFoundError(
                    f"document {document_id!r} not found in collection {collection.name!r}"
                ) from legacy_exc
            except self._cosmos_exceptions.CosmosHttpResponseError as legacy_exc:
                raise DbConnectionError(f"Cosmos delete failed: {legacy_exc.status_code}") from legacy_exc
        except self._cosmos_exceptions.CosmosHttpResponseError as exc:
            raise DbConnectionError(f"Cosmos delete failed: {exc.status_code}") from exc
        logger.info("[%s] delete collection=%s id=%s", PROVIDER_COSMOS, collection.name, document_id)

    def ping(self) -> None:
        """Lightweight Cosmos connectivity check for readiness probes.

        Performs a SELECT TOP 1 * on the simulation_results collection.
        Returns None when Cosmos is reachable; raises DbConnectionError otherwise.
        """
        from nexa_engine.db.models.collection_config import CollectionConfig as _CC
        _sentinel = _CC(name="simulation_results")
        try:
            self.list(_sentinel, limit=1)
        except DbConnectionError:
            raise
        except Exception as exc:
            raise DbConnectionError("Cosmos not accessible") from exc


__all__ = ["CosmosDocumentStore"]
