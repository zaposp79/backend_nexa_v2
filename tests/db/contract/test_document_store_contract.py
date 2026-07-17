"""Shared DocumentStore contract suite (FASE 13).

The same behavioural suite runs against every provider via the ``store``
fixture. JSON always runs. Cosmos is parametrized but ``pytest.skip``-ped when
credentials are absent, so a single suite covers both backends without
duplicating expectations.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from nexa_engine.db.config import CosmosSettings
from nexa_engine.db.constants.provider_constants import (
    ENV_COSMOS_CONTAINER_PARAMETRIZATION,
    ENV_COSMOS_DATABASE,
    ENV_COSMOS_ENDPOINT,
    ENV_COSMOS_KEY,
)
from nexa_engine.db.exceptions import DbNotFoundError, DbSerializationError
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.ports.document_store import DocumentStore

COLLECTION = CollectionConfig(name="contract_items", partition_key_field="group")


def _make_json_store(tmp_path: Path) -> DocumentStore:
    from nexa_engine.db.providers.json_document_store import JsonDocumentStore

    return JsonDocumentStore(tmp_path)


def _make_cosmos_store() -> DocumentStore:
    if not os.getenv(ENV_COSMOS_ENDPOINT) or not os.getenv(ENV_COSMOS_KEY):
        pytest.skip("Cosmos credentials not configured")
    settings = CosmosSettings(
        endpoint=os.environ[ENV_COSMOS_ENDPOINT],
        key=os.environ[ENV_COSMOS_KEY],
        database=os.environ.get(ENV_COSMOS_DATABASE, "nexa_pricing_db"),
        container=os.environ.get(ENV_COSMOS_CONTAINER_PARAMETRIZATION, "contract_items"),
    )
    from nexa_engine.db.providers.cosmos_document_store import CosmosDocumentStore

    return CosmosDocumentStore(settings)


@pytest.fixture(params=["json", "cosmos"])
def store(request, tmp_path) -> DocumentStore:
    if request.param == "json":
        return _make_json_store(tmp_path)
    return _make_cosmos_store()


def _doc(doc_id: str, group: str = "g1", **extra) -> dict:
    return {"id": doc_id, "group": group, **extra}


# --- get -------------------------------------------------------------------
def test_get_existing(store):
    store.upsert(COLLECTION, _doc("d1", value=1))
    got = store.get(COLLECTION, "d1", partition_value="g1")
    assert got["id"] == "d1"
    assert got["value"] == 1


def test_get_missing_returns_none(store):
    assert store.get(COLLECTION, "does-not-exist", partition_value="g1") is None


# --- list ------------------------------------------------------------------
def test_list(store):
    store.upsert(COLLECTION, _doc("d1"))
    store.upsert(COLLECTION, _doc("d2"))
    docs, token = store.list(COLLECTION)
    ids = {d["id"] for d in docs}
    assert {"d1", "d2"} <= ids


def test_list_paginated(store):
    for i in range(3):
        store.upsert(COLLECTION, _doc(f"d{i}"))
    page1, token1 = store.list(COLLECTION, limit=2)
    assert len(page1) == 2
    assert token1 is not None
    page2, token2 = store.list(COLLECTION, limit=2, continuation_token=token1)
    assert len(page2) == 1
    assert token2 is None


# --- query -----------------------------------------------------------------
def test_query_equality(store):
    store.upsert(COLLECTION, _doc("d1", group="g1", kind="a"))
    store.upsert(COLLECTION, _doc("d2", group="g1", kind="b"))
    docs, _ = store.query(COLLECTION, {"kind": "a"})
    assert [d["id"] for d in docs] == ["d1"]


def test_query_multiple_filters_and(store):
    store.upsert(COLLECTION, _doc("d1", group="g1", kind="a", tier=1))
    store.upsert(COLLECTION, _doc("d2", group="g1", kind="a", tier=2))
    store.upsert(COLLECTION, _doc("d3", group="g1", kind="b", tier=1))
    docs, _ = store.query(COLLECTION, {"kind": "a", "tier": 1})
    assert [d["id"] for d in docs] == ["d1"]


# --- upsert ----------------------------------------------------------------
def test_upsert_new(store):
    returned = store.upsert(COLLECTION, _doc("d1", value=1))
    assert returned["id"] == "d1"
    assert store.get(COLLECTION, "d1", partition_value="g1")["value"] == 1


def test_upsert_full_replace(store):
    store.upsert(COLLECTION, _doc("d1", a=1, b=2))
    store.upsert(COLLECTION, _doc("d1", a=99))  # b must disappear (full replace)
    got = store.get(COLLECTION, "d1", partition_value="g1")
    assert got["a"] == 99
    assert "b" not in got


# --- delete ----------------------------------------------------------------
def test_delete(store):
    store.upsert(COLLECTION, _doc("d1"))
    store.delete(COLLECTION, "d1", partition_value="g1")
    assert store.get(COLLECTION, "d1", partition_value="g1") is None


def test_delete_missing_raises(store):
    with pytest.raises(DbNotFoundError):
        store.delete(COLLECTION, "ghost", partition_value="g1")


# --- validation / exception translation ------------------------------------
def test_document_without_id_raises(store):
    with pytest.raises(DbSerializationError):
        store.upsert(COLLECTION, {"group": "g1", "value": 1})


def test_document_without_partition_key_raises(store):
    with pytest.raises(DbSerializationError):
        store.upsert(COLLECTION, {"id": "d1", "value": 1})
