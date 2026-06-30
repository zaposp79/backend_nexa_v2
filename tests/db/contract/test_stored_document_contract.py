from __future__ import annotations

import copy
import json

import pytest

from nexa_engine.db.exceptions import DbConfigurationError, DbSerializationError
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.providers.json_document_store import JsonDocumentStore


COLLECTION = CollectionConfig(name="stored_records", partition_key_field="domain")


def test_json_upsert_record_uses_id_for_location_and_writes_only_payload(tmp_path):
    store = JsonDocumentStore(tmp_path)
    payload = {"version_id": "v2-7", "sheets": []}
    original = copy.deepcopy(payload)

    record = StoredDocument(id="v2-7", payload=payload, partition_value="hr")
    returned = store.upsert_record(COLLECTION, record)

    assert payload == original
    assert returned == record
    path = tmp_path / "stored_records" / "v2-7.json"
    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == original


def test_json_get_record_round_trips_payload_without_metadata(tmp_path):
    store = JsonDocumentStore(tmp_path)
    store.upsert_record(
        COLLECTION,
        StoredDocument(id="v2-7", payload={"version_id": "v2-7", "sheets": []}, partition_value="hr"),
    )

    record = store.get_record(COLLECTION, "v2-7", partition_value="hr")

    assert record == StoredDocument(
        id="v2-7",
        payload={"version_id": "v2-7", "sheets": []},
        partition_value="hr",
    )
    assert "id" not in record.payload
    assert "domain" not in record.payload


def test_json_list_and_query_records_filter_logical_payload(tmp_path):
    store = JsonDocumentStore(tmp_path)
    store.upsert_record(COLLECTION, StoredDocument(id="hr-v1", payload={"version_id": "hr-v1", "domain": "hr"}))
    store.upsert_record(COLLECTION, StoredDocument(id="gn-v1", payload={"version_id": "gn-v1", "domain": "gn"}))

    records, token = store.list_records(COLLECTION)
    assert token is None
    assert [record.id for record in records] == ["gn-v1", "hr-v1"]

    filtered, token = store.query_records(COLLECTION, {"domain": "hr"})
    assert token is None
    assert filtered == [StoredDocument(id="hr-v1", payload={"version_id": "hr-v1", "domain": "hr"})]


def test_json_upsert_record_rejects_non_json_payload(tmp_path):
    store = JsonDocumentStore(tmp_path)

    with pytest.raises(DbSerializationError):
        store.upsert_record(COLLECTION, StoredDocument(id="bad", payload="not-json"))  # type: ignore[arg-type]


def test_json_get_record_invalid_json_shape_raises(tmp_path):
    store = JsonDocumentStore(tmp_path)
    path = tmp_path / "stored_records"
    path.mkdir()
    (path / "bad.json").write_text('"not-object-or-list"', encoding="utf-8")

    with pytest.raises(DbSerializationError):
        store.get_record(COLLECTION, "bad")


def test_cosmos_provider_not_initialized_for_json_factory(monkeypatch, tmp_path):
    from nexa_engine.db.config import ENV_DB_PROVIDER, ENV_JSON_STORAGE_PATH
    from nexa_engine.db.constants.provider_constants import PROVIDER_JSON
    from nexa_engine.db.factory import build_provider
    from nexa_engine.db.providers.json_document_store import JsonDocumentStore
    from nexa_engine.db.config import load_config

    config = load_config({
        ENV_DB_PROVIDER: PROVIDER_JSON,
        ENV_JSON_STORAGE_PATH: str(tmp_path),
    })

    assert isinstance(build_provider(config), JsonDocumentStore)


def test_cosmos_missing_configuration_still_fails_before_provider_creation():
    from nexa_engine.db.config import ENV_DB_PROVIDER, load_config

    with pytest.raises(DbConfigurationError):
        load_config({ENV_DB_PROVIDER: "cosmos"})
