"""DB-backed certification Step 1 — immutable snapshot contract.

Validates put_immutable / get_snapshot semantics on every provider.
JSON always runs; Cosmos is skipped when credentials are absent.

Guarantees under test:
  1. put_immutable creates a document.
  2. get_snapshot returns it by id.
  3. A second put_immutable with the same id raises DbConflictError.
  4. upsert_record behavior is unchanged (can overwrite).
  5. put_immutable and upsert_record coexist in the same collection.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nexa_engine.db.exceptions import DbConflictError
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.ports.document_store import DocumentStore

_SNAPSHOTS = CollectionConfig(name="parametrization_snapshots")


def _make_json_store(tmp_path: Path) -> DocumentStore:
    from nexa_engine.db.providers.json_document_store import JsonDocumentStore

    return JsonDocumentStore(tmp_path)


def _make_cosmos_store() -> DocumentStore:
    from nexa_engine.db.config import CosmosSettings
    from nexa_engine.db.constants.provider_constants import (
        ENV_COSMOS_CONTAINER_PARAMETRIZATION,
        ENV_COSMOS_DATABASE,
        ENV_COSMOS_ENDPOINT,
        ENV_COSMOS_KEY,
    )

    if not os.getenv(ENV_COSMOS_ENDPOINT) or not os.getenv(ENV_COSMOS_KEY):
        pytest.skip("Cosmos credentials not configured")
    settings = CosmosSettings(
        endpoint=os.environ[ENV_COSMOS_ENDPOINT],
        key=os.environ[ENV_COSMOS_KEY],
        database=os.environ.get(ENV_COSMOS_DATABASE, "nexa_pricing_db"),
        container=os.environ.get(ENV_COSMOS_CONTAINER_PARAMETRIZATION, "parametrization_snapshots"),
    )
    from nexa_engine.db.providers.cosmos_document_store import CosmosDocumentStore

    return CosmosDocumentStore(settings)


@pytest.fixture(params=["json", "cosmos"])
def store(request, tmp_path: Path) -> DocumentStore:
    if request.param == "json":
        return _make_json_store(tmp_path)
    return _make_cosmos_store()


def _record(doc_id: str, data: dict | None = None) -> StoredDocument:
    return StoredDocument(id=doc_id, payload=data or {"version": "v2-7-certified", "module": doc_id})


class TestPutImmutableCreates:
    def test_put_immutable_creates_document(self, store: DocumentStore) -> None:
        record = _record("business_rules")
        result = store.put_immutable(_SNAPSHOTS, record)
        assert result.id == "business_rules"
        assert result.payload == record.payload

    def test_get_snapshot_returns_created_document(self, store: DocumentStore) -> None:
        record = _record("hr_snapshot")
        store.put_immutable(_SNAPSHOTS, record)
        retrieved = store.get_snapshot(_SNAPSHOTS, "hr_snapshot")
        assert retrieved is not None
        assert retrieved.id == "hr_snapshot"
        assert retrieved.payload == record.payload

    def test_get_snapshot_returns_none_when_not_found(self, store: DocumentStore) -> None:
        result = store.get_snapshot(_SNAPSHOTS, "nonexistent_snapshot")
        assert result is None


class TestPutImmutableConflict:
    def test_second_put_immutable_raises_conflict(self, store: DocumentStore) -> None:
        record = _record("op_snapshot")
        store.put_immutable(_SNAPSHOTS, record)
        with pytest.raises(DbConflictError):
            store.put_immutable(_SNAPSHOTS, record)

    def test_conflict_on_different_payload_same_id(self, store: DocumentStore) -> None:
        """Even with different payload content, same id must be rejected."""
        store.put_immutable(_SNAPSHOTS, _record("gn_snapshot", {"data": "original"}))
        with pytest.raises(DbConflictError):
            store.put_immutable(_SNAPSHOTS, _record("gn_snapshot", {"data": "tampered"}))

    def test_original_payload_preserved_after_conflict(self, store: DocumentStore) -> None:
        """A failed put_immutable must not overwrite the original document."""
        original = _record("business_rules_v2", {"hash": "abc123"})
        store.put_immutable(_SNAPSHOTS, original)
        try:
            store.put_immutable(_SNAPSHOTS, _record("business_rules_v2", {"hash": "xyz999"}))
        except DbConflictError:
            pass
        retrieved = store.get_snapshot(_SNAPSHOTS, "business_rules_v2")
        assert retrieved is not None
        assert retrieved.payload["hash"] == "abc123"


class TestUpsertUnchanged:
    def test_upsert_record_can_overwrite(self, store: DocumentStore) -> None:
        """upsert_record behavior must be unchanged — overwrites are allowed."""
        record_v1 = StoredDocument(id="mutable_doc", payload={"version": 1})
        record_v2 = StoredDocument(id="mutable_doc", payload={"version": 2})
        store.upsert_record(_SNAPSHOTS, record_v1)
        store.upsert_record(_SNAPSHOTS, record_v2)
        retrieved = store.get_record(_SNAPSHOTS, "mutable_doc")
        assert retrieved is not None
        assert retrieved.payload["version"] == 2

    def test_put_immutable_and_upsert_coexist(self, store: DocumentStore) -> None:
        """put_immutable and upsert_record can coexist in the same collection."""
        immutable = _record("certified_snapshot")
        mutable = StoredDocument(id="active_params", payload={"active": True})
        store.put_immutable(_SNAPSHOTS, immutable)
        store.upsert_record(_SNAPSHOTS, mutable)
        assert store.get_snapshot(_SNAPSHOTS, "certified_snapshot") is not None
        assert store.get_record(_SNAPSHOTS, "active_params") is not None

    def test_upsert_does_not_affect_immutable_ids(self, store: DocumentStore) -> None:
        """upsert_record on a different id does not affect immutable snapshots."""
        store.put_immutable(_SNAPSHOTS, _record("frozen_snapshot"))
        store.upsert_record(_SNAPSHOTS, StoredDocument(id="other_doc", payload={"x": 1}))
        frozen = store.get_snapshot(_SNAPSHOTS, "frozen_snapshot")
        assert frozen is not None
        assert frozen.payload["module"] == "frozen_snapshot"


__all__ = [
    "TestPutImmutableCreates",
    "TestPutImmutableConflict",
    "TestUpsertUnchanged",
]
