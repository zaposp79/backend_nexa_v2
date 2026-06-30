from __future__ import annotations

import importlib
import inspect
from unittest.mock import create_autospec

import pytest

from nexa_engine.db.config import CosmosSettings
from nexa_engine.db.exceptions import DbConcurrencyError
from nexa_engine.db.models.atomic_write import AtomicWritePrecondition
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.providers.cosmos_document_store import CosmosDocumentStore


def _cosmos_modules():
    try:
        container_module = importlib.import_module("azure.cosmos.container")
        exceptions_module = importlib.import_module("azure.cosmos.exceptions")
        cosmos_module = importlib.import_module("azure.cosmos")
    except ModuleNotFoundError:
        pytest.skip("azure-cosmos is not installed in this environment")
    return cosmos_module, container_module, exceptions_module


def test_supported_azure_cosmos_sdk_contract_is_documented():
    cosmos_module, _, _ = _cosmos_modules()

    version = getattr(cosmos_module, "__version__", "")
    assert version
    major = int(version.split(".", 1)[0])
    assert major == 4


def test_container_execute_item_batch_signature_is_compatible():
    _, container_module, _ = _cosmos_modules()

    signature = inspect.signature(container_module.ContainerProxy.execute_item_batch)

    assert "batch_operations" in signature.parameters
    assert "partition_key" in signature.parameters


def test_cosmos_document_store_calls_execute_item_batch_with_sdk_autospec():
    _, container_module, exceptions_module = _cosmos_modules()
    container = create_autospec(container_module.ContainerProxy, instance=True)
    container.execute_item_batch.return_value = [{"statusCode": 200}, {"statusCode": 200}]
    store = CosmosDocumentStore(
        CosmosSettings(
            endpoint="https://example.documents.azure.com:443/",
            key="fake",
            database="nexa",
            container="parametrization",
        ),
        container_client=container,
        cosmos_exceptions=exceptions_module,
    )

    store.upsert_records_atomic(
        CollectionConfig(name="gn"),
        [
            StoredDocument(id="gn-v1", payload={"version_id": "gn-v1"}),
            StoredDocument(id="versions", payload=[{"version_id": "gn-v1"}]),
        ],
        precondition=AtomicWritePrecondition(
            logical_id="versions",
            expected_etag="etag-actual",
        ),
    )

    container.execute_item_batch.assert_called_once()
    _, kwargs = container.execute_item_batch.call_args
    assert kwargs["partition_key"] == "gn"
    operations = kwargs["batch_operations"]
    assert [operation[0] for operation in operations] == ["upsert", "upsert"]
    assert operations[0][2] == {}
    assert operations[1][2] == {"if_match_etag": "etag-actual"}


def test_cosmos_precondition_status_maps_to_concurrency_error_with_sdk_exception():
    _, container_module, exceptions_module = _cosmos_modules()
    container = create_autospec(container_module.ContainerProxy, instance=True)
    error = exceptions_module.CosmosHttpResponseError(status_code=412, message="precondition failed")
    container.execute_item_batch.side_effect = error
    store = CosmosDocumentStore(
        CosmosSettings(
            endpoint="https://example.documents.azure.com:443/",
            key="fake",
            database="nexa",
            container="parametrization",
        ),
        container_client=container,
        cosmos_exceptions=exceptions_module,
    )

    with pytest.raises(DbConcurrencyError):
        store.upsert_records_atomic(
            CollectionConfig(name="gn"),
            [
                StoredDocument(id="gn-v1", payload={"version_id": "gn-v1"}),
                StoredDocument(id="versions", payload=[{"version_id": "gn-v1"}]),
            ],
            precondition=AtomicWritePrecondition(
                logical_id="versions",
                expected_etag="etag-obsoleto",
            ),
        )


def test_cosmos_batch_operation_error_maps_to_concurrency_error():
    _, container_module, exceptions_module = _cosmos_modules()
    container = create_autospec(container_module.ContainerProxy, instance=True)
    error = exceptions_module.CosmosBatchOperationError(
        error_index=1,
        headers={},
        status_code=412,
        message="precondition failed",
        operation_responses=[{"statusCode": 200}, {"statusCode": 412}],
    )
    container.execute_item_batch.side_effect = error
    store = CosmosDocumentStore(
        CosmosSettings(
            endpoint="https://example.documents.azure.com:443/",
            key="fake",
            database="nexa",
            container="parametrization",
        ),
        container_client=container,
        cosmos_exceptions=exceptions_module,
    )

    with pytest.raises(DbConcurrencyError):
        store.upsert_records_atomic(
            CollectionConfig(name="gn"),
            [
                StoredDocument(id="gn-v1", payload={"version_id": "gn-v1"}),
                StoredDocument(id="versions", payload=[{"version_id": "gn-v1"}]),
            ],
            precondition=AtomicWritePrecondition(
                logical_id="versions",
                expected_etag="etag-obsoleto",
            ),
        )
