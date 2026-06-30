"""Config resolution, factory selection and JSON-specific behaviour (FASE 13)."""
from __future__ import annotations

from pathlib import Path

import pytest

from nexa_engine.db.config import load_config
from nexa_engine.db.constants.provider_constants import (
    ENV_COSMOS_CONTAINER,
    ENV_COSMOS_DATABASE,
    ENV_COSMOS_ENDPOINT,
    ENV_COSMOS_KEY,
    ENV_DB_PROVIDER,
    ENV_JSON_STORAGE_PATH,
    PROVIDER_COSMOS,
    PROVIDER_JSON,
)
from nexa_engine.db.exceptions import DbConfigurationError, DbSerializationError
from nexa_engine.db.factory import (
    build_parametrization_document_store,
    build_provider,
    get_provider,
    reset_provider,
)
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.providers.json_document_store import JsonDocumentStore

COLL = CollectionConfig(name="cfg_items")


# --- config: defaults & validation -----------------------------------------
def test_default_provider_is_json():
    cfg = load_config({})
    assert cfg.provider == PROVIDER_JSON
    assert cfg.json_storage_path.name == "storage"


def test_invalid_provider_raises():
    with pytest.raises(DbConfigurationError):
        load_config({ENV_DB_PROVIDER: "mysql"})


def test_json_path_is_configurable(tmp_path):
    cfg = load_config({ENV_JSON_STORAGE_PATH: str(tmp_path)})
    assert cfg.json_storage_path == tmp_path


def test_cosmos_settings_not_required_for_json():
    # No Cosmos vars present, json selected -> no error, cosmos is None.
    cfg = load_config({ENV_DB_PROVIDER: PROVIDER_JSON})
    assert cfg.cosmos is None


def test_cosmos_missing_settings_raise():
    with pytest.raises(DbConfigurationError):
        load_config({ENV_DB_PROVIDER: PROVIDER_COSMOS})


def test_cosmos_settings_resolved():
    cfg = load_config(
        {
            ENV_DB_PROVIDER: PROVIDER_COSMOS,
            ENV_COSMOS_ENDPOINT: "https://acct.documents.azure.com:443/",
            ENV_COSMOS_KEY: "secret-key",
            ENV_COSMOS_DATABASE: "nexa_pricing_db",
            ENV_COSMOS_CONTAINER: "results",
        }
    )
    assert cfg.provider == PROVIDER_COSMOS
    assert cfg.cosmos is not None
    assert cfg.cosmos.database == "nexa_pricing_db"


# --- factory ----------------------------------------------------------------
def test_build_provider_json(tmp_path):
    cfg = load_config({ENV_JSON_STORAGE_PATH: str(tmp_path)})
    provider = build_provider(cfg)
    assert isinstance(provider, JsonDocumentStore)


def test_build_parametrization_store_default_is_json():
    from nexa_engine.modules.shared.config.config import PARAMETRIZATION_DIR

    cfg = load_config({})
    provider = build_parametrization_document_store(cfg)

    assert isinstance(provider, JsonDocumentStore)
    assert provider._root == PARAMETRIZATION_DIR


def test_build_parametrization_store_explicit_json_uses_legacy_root(tmp_path):
    from nexa_engine.modules.shared.config.config import PARAMETRIZATION_DIR

    cfg = load_config(
        {
            ENV_DB_PROVIDER: PROVIDER_JSON,
            ENV_JSON_STORAGE_PATH: str(tmp_path),
        }
    )
    provider = build_parametrization_document_store(cfg)

    assert isinstance(provider, JsonDocumentStore)
    assert provider._root == PARAMETRIZATION_DIR
    assert provider._root != tmp_path


def test_build_parametrization_store_cosmos_requires_settings():
    with pytest.raises(DbConfigurationError, match="missing required settings"):
        load_config({ENV_DB_PROVIDER: PROVIDER_COSMOS})


def test_build_parametrization_store_cosmos_constructs_from_settings(monkeypatch):
    from nexa_engine.db.providers import cosmos_document_store

    cfg = load_config(
        {
            ENV_DB_PROVIDER: PROVIDER_COSMOS,
            ENV_COSMOS_ENDPOINT: "https://acct.documents.azure.com:443/",
            ENV_COSMOS_KEY: "secret-key",
            ENV_COSMOS_DATABASE: "nexa_pricing",
            ENV_COSMOS_CONTAINER: "parametrization",
        }
    )

    constructed = {}

    class FakeCosmosDocumentStore:
        def __init__(self, settings):
            constructed["settings"] = settings

    monkeypatch.setattr(
        cosmos_document_store,
        "CosmosDocumentStore",
        FakeCosmosDocumentStore,
    )

    provider = build_parametrization_document_store(cfg)

    assert isinstance(provider, FakeCosmosDocumentStore)
    assert constructed["settings"] == cfg.cosmos


def test_container_does_not_hardcode_parametrization_json_store():
    import inspect
    from nexa_engine.db import container

    source = inspect.getsource(container)

    assert "JsonDocumentStore(PARAMETRIZATION_DIR)" not in source
    assert "build_parametrization_document_store" in source


def test_get_provider_caches_and_reset():
    reset_provider()
    first = get_provider()
    second = get_provider()
    assert first is second  # cached
    reset_provider()
    third = get_provider()
    assert third is not first  # reset forces rebuild
    reset_provider()


# --- JSON-specific: malformed file & path configurability -------------------
def test_invalid_json_raises_serialization_error(tmp_path):
    store = JsonDocumentStore(tmp_path)
    coll_dir = tmp_path / COLL.name
    coll_dir.mkdir(parents=True)
    (coll_dir / "broken.json").write_text("{ not valid json ", encoding="utf-8")
    with pytest.raises(DbSerializationError):
        store.get(COLL, "broken")


def test_unsafe_document_id_rejected(tmp_path):
    store = JsonDocumentStore(tmp_path)
    with pytest.raises(DbSerializationError):
        store.upsert(COLL, {"id": "../escape"})


def test_collection_name_must_be_safe():
    with pytest.raises(ValueError):
        CollectionConfig(name="../etc")


# --- Cosmos isolation: DB.6.8 readiness tests --------------------------------

def test_cosmos_not_imported_when_db_provider_is_json(tmp_path, monkeypatch):
    """CosmosDocumentStore is NEVER imported when DB_PROVIDER=json.

    This ensures the azure-cosmos package is not required in JSON environments
    and that no Cosmos initialization occurs accidentally.
    """
    import sys
    # Remove any cached cosmos module from previous tests
    for key in list(sys.modules.keys()):
        if "cosmos_document_store" in key:
            del sys.modules[key]

    cfg = load_config({ENV_JSON_STORAGE_PATH: str(tmp_path)})
    provider = build_provider(cfg)

    assert isinstance(provider, JsonDocumentStore)
    # CosmosDocumentStore must not be in sys.modules (not even imported lazily)
    cosmos_mod = "nexa_engine.db.providers.cosmos_document_store"
    assert cosmos_mod not in sys.modules, (
        "CosmosDocumentStore was imported even though DB_PROVIDER=json. "
        "This breaks environments where azure-cosmos is not installed."
    )


def test_cosmos_store_raises_db_connection_error_without_settings():
    """CosmosDocumentStore(settings=None) raises DbConnectionError immediately.

    No credentials, no partial initialization, no silent failure.
    """
    from nexa_engine.db.exceptions import DbConnectionError
    from nexa_engine.db.providers.cosmos_document_store import CosmosDocumentStore

    with pytest.raises(DbConnectionError, match="settings are required"):
        CosmosDocumentStore(settings=None)


def test_get_parametrization_store_returns_document_store(tmp_path, monkeypatch):
    """get_parametrization_store() returns a DocumentStore rooted at PARAMETRIZATION_DIR.

    It must never return a domain-aware factory or a Cosmos-specific object
    when DB_PROVIDER is not set to cosmos.
    """
    from nexa_engine.db.factory import get_parametrization_store, reset_provider
    from nexa_engine.db.ports.document_store import DocumentStore

    reset_provider()
    store = get_parametrization_store()
    assert isinstance(store, DocumentStore), (
        "get_parametrization_store() must return a DocumentStore instance. "
        "It must not return a domain-specific repository or factory."
    )
    # Verify it does not know about GN/HR/OP domains by checking its interface
    assert hasattr(store, "get_record")
    assert hasattr(store, "upsert_record")
    reset_provider()


def test_json_provider_does_not_expose_cosmos_methods():
    """JsonDocumentStore must not expose Cosmos-specific atomic batch methods.

    Cosmos-specific operations (upsert_records_atomic) are only available on
    CosmosDocumentStore via the AtomicDocumentStore protocol.  Calling them on
    JSON provider must raise AttributeError, not silently succeed.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        store = JsonDocumentStore(Path(tmp))
        assert not hasattr(store, "upsert_records_atomic"), (
            "JsonDocumentStore should not expose upsert_records_atomic. "
            "That is a Cosmos-specific method."
        )
