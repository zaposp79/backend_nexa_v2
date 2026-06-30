from __future__ import annotations

import copy
from dataclasses import dataclass

import pytest

from nexa_engine.db.exceptions import DbConcurrencyError, DbConnectionError, DbNotFoundError
from nexa_engine.db.models.atomic_write import AtomicWritePrecondition
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.providers.cosmos_document_store import CosmosDocumentStore


class FakeCosmosExceptions:
    class CosmosHttpResponseError(Exception):
        status_code = 500

    class CosmosResourceNotFoundError(CosmosHttpResponseError):
        status_code = 404

    class CosmosResourceExistsError(CosmosHttpResponseError):
        status_code = 409


@dataclass
class FakeBatchResponse:
    is_successful: bool
    operation_responses: list[object] | None = None


class FakeTransactionalBatch:
    def __init__(self, container: "FakeContainer", partition_key: str) -> None:
        self._container = container
        self._partition_key = partition_key
        self._items: list[dict] = []
        self._preconditions: list[tuple[str, str]] = []

    def upsert_item(
        self,
        item: dict,
        *,
        etag: str | None = None,
        match_condition: str | None = None,
    ) -> None:
        self._items.append(copy.deepcopy(item))
        if etag is not None:
            self._preconditions.append((item["id"], etag))

    def execute(self) -> FakeBatchResponse:
        if self._container.fail_next_batch:
            self._container.fail_next_batch = False
            return FakeBatchResponse(is_successful=False)
        for item_id, expected_etag in self._preconditions:
            current = self._container.items.get((self._partition_key, item_id))
            if current is None or current.get("_etag") != expected_etag:
                return FakeBatchResponse(
                    is_successful=False,
                    operation_responses=[type("Operation", (), {"status_code": 412})()],
                )
        for item in self._items:
            self._container.store_item(self._partition_key, item)
        return FakeBatchResponse(is_successful=True)


class FakeContainer:
    def __init__(self) -> None:
        self.items: dict[tuple[str | None, str], dict] = {}
        self.fail_next_batch = False
        self.batch_partition_keys: list[str] = []
        self._etag_counter = 0

    def upsert_item(self, item: dict) -> dict:
        partition_key = item.get("_pk") or item.get("domain")
        return self.store_item(partition_key, item)

    def store_item(self, partition_key: str | None, item: dict) -> dict:
        self._etag_counter += 1
        stored = copy.deepcopy(item)
        stored["_etag"] = f"etag-{self._etag_counter}"
        self.items[(partition_key, item["id"])] = stored
        return copy.deepcopy(stored)

    def read_item(self, item: str, partition_key: str | None) -> dict:
        try:
            return copy.deepcopy(self.items[(partition_key, item)])
        except KeyError as exc:
            raise FakeCosmosExceptions.CosmosResourceNotFoundError() from exc

    def delete_item(self, item: str, partition_key: str | None) -> None:
        try:
            del self.items[(partition_key, item)]
        except KeyError as exc:
            raise FakeCosmosExceptions.CosmosResourceNotFoundError() from exc

    def create_transactional_batch(self, partition_key: str) -> FakeTransactionalBatch:
        self.batch_partition_keys.append(partition_key)
        return FakeTransactionalBatch(self, partition_key)


class FakeExecuteItemBatchContainer(FakeContainer):
    def __init__(self) -> None:
        super().__init__()
        self.executed_batches: list[dict] = []

    def execute_item_batch(self, *, batch_operations, partition_key):  # type: ignore[no-untyped-def]
        self.executed_batches.append(
            {"batch_operations": copy.deepcopy(batch_operations), "partition_key": partition_key}
        )
        for operation_name, args, kwargs in batch_operations:
            assert operation_name == "upsert"
            item = args[0]
            if "if_match_etag" in kwargs:
                current = self.items.get((partition_key, item["id"]))
                if current is None or current.get("_etag") != kwargs["if_match_etag"]:
                    error = FakeCosmosExceptions.CosmosHttpResponseError()
                    error.status_code = 412
                    raise error
            self.store_item(partition_key, item)
        return [{"statusCode": 200} for _ in batch_operations]


COLLECTION = CollectionConfig(name="gn")


def _store(container: FakeContainer) -> CosmosDocumentStore:
    return CosmosDocumentStore(
        None,
        container_client=container,
        cosmos_exceptions=FakeCosmosExceptions,
    )


def test_cosmos_record_upsert_read_and_delete_without_payload_metadata():
    container = FakeContainer()
    store = _store(container)
    payload = {"version_id": "gn-v1", "sheets": []}

    stored = store.upsert_record(
        COLLECTION,
        StoredDocument(id="gn-v1", payload=payload),
    )

    assert stored == StoredDocument(id="gn-v1", payload=payload, partition_value="gn", etag="etag-1")
    assert ("gn", "gn:gn-v1") in container.items
    assert container.items[("gn", "gn:gn-v1")]["payload"] == payload
    assert "id" not in container.items[("gn", "gn:gn-v1")]["payload"]

    read = store.get_record(COLLECTION, "gn-v1")
    assert read == StoredDocument(id="gn-v1", payload=payload, partition_value="gn", etag="etag-1")

    store.delete(COLLECTION, "gn-v1")
    assert store.get_record(COLLECTION, "gn-v1") is None


def test_cosmos_delete_missing_record_raises_not_found():
    store = _store(FakeContainer())

    with pytest.raises(DbNotFoundError):
        store.delete(COLLECTION, "missing")


def test_cosmos_transactional_batch_upserts_payload_and_legacy_index_in_same_partition():
    container = FakeContainer()
    store = _store(container)
    payload = StoredDocument(
        id="gn-v1",
        payload={"version_id": "gn-v1", "lv": {}, "sheets": []},
    )
    versions = StoredDocument(
        id="versions",
        payload=[
            {
                "version_id": "gn-v1",
                "filename": "GN.xlsx",
                "uploaded_at": "2026-06-04T00:00:00Z",
                "is_active": True,
                "sheet_count": 1,
                "total_rows": 1,
            }
        ],
    )

    result = store.upsert_records_atomic(COLLECTION, [payload, versions])

    assert result.records == (
        StoredDocument(id="gn-v1", payload=payload.payload, partition_value="gn"),
        StoredDocument(id="versions", payload=versions.payload, partition_value="gn"),
    )
    assert container.batch_partition_keys == ["gn"]
    assert store.get_record(COLLECTION, "gn-v1").payload == payload.payload
    assert store.get_record(COLLECTION, "versions").payload == versions.payload


def test_cosmos_transactional_batch_preserves_duplicate_version_contract():
    container = FakeContainer()
    store = _store(container)
    first_payload = StoredDocument(
        id="gn-v1",
        payload={"version_id": "gn-v1", "lv": {"name": "primero"}, "sheets": []},
    )
    first_versions = StoredDocument(
        id="versions",
        payload=[{"version_id": "gn-v1", "filename": "GN_first.xlsx", "is_active": True}],
    )
    second_payload = StoredDocument(
        id="gn-v1",
        payload={"version_id": "gn-v1", "lv": {"name": "segundo"}, "sheets": []},
    )
    second_versions = StoredDocument(
        id="versions",
        payload=[
            {"version_id": "gn-v1", "filename": "GN_first.xlsx", "is_active": False},
            {"version_id": "gn-v1", "filename": "GN_second.xlsx", "is_active": True},
        ],
    )

    store.upsert_records_atomic(COLLECTION, [first_payload, first_versions])
    store.upsert_records_atomic(COLLECTION, [second_payload, second_versions])

    assert store.get_record(COLLECTION, "gn-v1").payload == second_payload.payload
    versions = store.get_record(COLLECTION, "versions").payload
    assert [entry["version_id"] for entry in versions] == ["gn-v1", "gn-v1"]
    assert [entry["is_active"] for entry in versions] == [False, True]


def test_cosmos_transactional_batch_rolls_back_all_items_when_batch_fails():
    container = FakeContainer()
    store = _store(container)
    container.fail_next_batch = True

    with pytest.raises(DbConnectionError):
        store.upsert_records_atomic(
            COLLECTION,
            [
                StoredDocument(id="gn-v1", payload={"version_id": "gn-v1"}),
                StoredDocument(id="versions", payload=[{"version_id": "gn-v1"}]),
            ],
        )

    assert store.get_record(COLLECTION, "gn-v1") is None
    assert store.get_record(COLLECTION, "versions") is None


def test_cosmos_transactional_batch_keeps_previous_items_when_replacement_fails():
    container = FakeContainer()
    store = _store(container)
    previous_payload = StoredDocument(
        id="gn-v1",
        payload={"version_id": "gn-v1", "lv": {"name": "previo"}, "sheets": []},
    )
    previous_versions = StoredDocument(
        id="versions",
        payload=[{"version_id": "gn-v1", "filename": "GN_old.xlsx", "is_active": True}],
    )
    store.upsert_records_atomic(COLLECTION, [previous_payload, previous_versions])
    container.fail_next_batch = True

    with pytest.raises(DbConnectionError):
        store.upsert_records_atomic(
            COLLECTION,
            [
                StoredDocument(
                    id="gn-v1",
                    payload={"version_id": "gn-v1", "lv": {"name": "nuevo"}, "sheets": []},
                ),
                StoredDocument(
                    id="versions",
                    payload=[{"version_id": "gn-v1", "filename": "GN_new.xlsx", "is_active": True}],
                ),
            ],
        )

    assert store.get_record(COLLECTION, "gn-v1").payload == previous_payload.payload
    assert store.get_record(COLLECTION, "versions").payload == previous_versions.payload


def test_cosmos_transactional_batch_succeeds_with_current_index_etag():
    container = FakeContainer()
    store = _store(container)
    store.upsert_records_atomic(
        COLLECTION,
        [
            StoredDocument(id="gn-v1", payload={"version_id": "gn-v1"}),
            StoredDocument(id="versions", payload=[{"version_id": "gn-v1"}]),
        ],
    )
    current_versions = store.get_record(COLLECTION, "versions")

    store.upsert_records_atomic(
        COLLECTION,
        [
            StoredDocument(id="gn-v2", payload={"version_id": "gn-v2"}),
            StoredDocument(
                id="versions",
                payload=[
                    {"version_id": "gn-v1", "is_active": False},
                    {"version_id": "gn-v2", "is_active": True},
                ],
            ),
        ],
        precondition=AtomicWritePrecondition(
            logical_id="versions",
            expected_etag=current_versions.etag,
        ),
    )

    versions = store.get_record(COLLECTION, "versions")
    assert [entry["version_id"] for entry in versions.payload] == ["gn-v1", "gn-v2"]


def test_cosmos_execute_item_batch_uses_upsert_operations_and_if_match_etag():
    container = FakeExecuteItemBatchContainer()
    store = _store(container)
    store.upsert_records_atomic(
        COLLECTION,
        [
            StoredDocument(id="gn-v1", payload={"version_id": "gn-v1"}),
            StoredDocument(id="versions", payload=[{"version_id": "gn-v1"}]),
        ],
    )
    current_versions = store.get_record(COLLECTION, "versions")

    store.upsert_records_atomic(
        COLLECTION,
        [
            StoredDocument(id="gn-v2", payload={"version_id": "gn-v2"}),
            StoredDocument(id="versions", payload=[{"version_id": "gn-v1"}, {"version_id": "gn-v2"}]),
        ],
        precondition=AtomicWritePrecondition(
            logical_id="versions",
            expected_etag=current_versions.etag,
        ),
    )

    second_batch = container.executed_batches[1]
    assert second_batch["partition_key"] == "gn"
    operations = second_batch["batch_operations"]
    assert [operation[0] for operation in operations] == ["upsert", "upsert"]
    assert operations[0][2] == {}
    assert operations[1][2] == {"if_match_etag": current_versions.etag}


def test_cosmos_transactional_batch_rejects_stale_index_etag_without_partial_changes():
    container = FakeContainer()
    store = _store(container)
    store.upsert_records_atomic(
        COLLECTION,
        [
            StoredDocument(id="gn-v1", payload={"version_id": "gn-v1"}),
            StoredDocument(id="versions", payload=[{"version_id": "gn-v1"}]),
        ],
    )
    stale_versions = store.get_record(COLLECTION, "versions")
    store.upsert_records_atomic(
        COLLECTION,
        [
            StoredDocument(id="gn-v2", payload={"version_id": "gn-v2"}),
            StoredDocument(id="versions", payload=[{"version_id": "gn-v1"}, {"version_id": "gn-v2"}]),
        ],
        precondition=AtomicWritePrecondition(
            logical_id="versions",
            expected_etag=stale_versions.etag,
        ),
    )

    with pytest.raises(DbConcurrencyError):
        store.upsert_records_atomic(
            COLLECTION,
            [
                StoredDocument(id="gn-v3", payload={"version_id": "gn-v3"}),
                StoredDocument(id="versions", payload=[{"version_id": "gn-v1"}, {"version_id": "gn-v3"}]),
            ],
            precondition=AtomicWritePrecondition(
                logical_id="versions",
                expected_etag=stale_versions.etag,
            ),
        )

    assert store.get_record(COLLECTION, "gn-v3") is None
    versions = store.get_record(COLLECTION, "versions")
    assert [entry["version_id"] for entry in versions.payload] == ["gn-v1", "gn-v2"]
    assert "_etag" not in versions.payload[0]
