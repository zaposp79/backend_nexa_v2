"""Smoke tests for CosmosDocumentStore with real parametrization data.

These tests are SKIPPED automatically when Cosmos credentials are not configured.
They are intended to run in CI/CD with real Cosmos credentials, or manually
during the pre-activation validation phase.

To run:
    export COSMOS_ENDPOINT=https://<account>.documents.azure.com:443/
    export COSMOS_KEY=<your-key>
    export COSMOS_DATABASE=nexa_pricing_smoke_test   # use an isolated database!
    export COSMOS_CONTAINER_PARAMETRIZATION=parametrization_smoke
    pytest tests/db/smoke/ -v

IMPORTANT:
- Use an ISOLATED Cosmos database (not production).
- These tests CREATE and DELETE documents.
- Do not run against production containers.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Skip logic — credentials required
# ---------------------------------------------------------------------------

_COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "")
_COSMOS_KEY = os.getenv("COSMOS_KEY", "")
_SKIP_REASON = "Cosmos credentials not configured (COSMOS_ENDPOINT, COSMOS_KEY)"

pytestmark = [
    pytest.mark.cosmos_integration,
    pytest.mark.skipif(
        not (_COSMOS_ENDPOINT and _COSMOS_KEY),
        reason=_SKIP_REASON,
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _payload_hash(payload) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _make_smoke_collection():
    """Create a CollectionConfig for the smoke test container."""
    from nexa_engine.db.models.collection_config import CollectionConfig
    return CollectionConfig(name="smoke_parametrization")


def _build_cosmos_store():
    """Build CosmosDocumentStore from environment variables."""
    from nexa_engine.db.config import load_config
    from nexa_engine.db.constants.provider_constants import (
        ENV_COSMOS_DATABASE,
        ENV_COSMOS_CONTAINER_PARAMETRIZATION,
        ENV_COSMOS_ENDPOINT,
        ENV_COSMOS_KEY,
        PROVIDER_COSMOS,
        ENV_DB_PROVIDER,
    )
    from nexa_engine.db.factory import build_parametrization_document_store

    # Use smoke-specific database/container if configured
    smoke_db = os.getenv("COSMOS_DATABASE", "nexa_pricing_smoke")
    smoke_container = os.getenv("COSMOS_CONTAINER_PARAMETRIZATION", "parametrization_smoke")

    config = load_config({
        ENV_DB_PROVIDER: PROVIDER_COSMOS,
        ENV_COSMOS_ENDPOINT: _COSMOS_ENDPOINT,
        ENV_COSMOS_KEY: _COSMOS_KEY,
        ENV_COSMOS_DATABASE: smoke_db,
        ENV_COSMOS_CONTAINER_PARAMETRIZATION: smoke_container,
    })
    return build_parametrization_document_store(config)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def cosmos_store():
    """Module-scoped CosmosDocumentStore for smoke tests."""
    store = _build_cosmos_store()
    yield store


@pytest.fixture
def smoke_collection():
    return _make_smoke_collection()


@pytest.fixture
def unique_doc_id():
    """A unique document ID for each test to avoid conflicts."""
    return f"smoke-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

class TestCosmosSmoke:
    """Smoke tests: verify CosmosDocumentStore works with parametrization payloads."""

    def test_cosmos_connection_established(self, cosmos_store):
        """Store can be instantiated without error."""
        from nexa_engine.db.ports.document_store import DocumentStore
        assert isinstance(cosmos_store, DocumentStore)

    def test_upsert_and_get_record_round_trip(self, cosmos_store, smoke_collection, unique_doc_id):
        """upsert_record → get_record preserves payload exactly (hash-verified)."""
        from nexa_engine.db.models.stored_document import StoredDocument

        payload = {
            "version_id": unique_doc_id,
            "sheets": [{"name": "GN-LV", "key": "lv", "catalogs": {
                "ciudad": [{"name": "Bogotá"}],
                "servicio": [{"name": "Cobranzas"}],
            }}],
        }
        original_hash = _payload_hash(payload)

        record = StoredDocument(id=unique_doc_id, payload=payload)
        cosmos_store.upsert_record(smoke_collection, record)

        retrieved = cosmos_store.get_record(smoke_collection, unique_doc_id)
        assert retrieved is not None, "Document not found after upsert"
        assert retrieved.id == unique_doc_id
        assert _payload_hash(retrieved.payload) == original_hash, (
            "Payload hash mismatch — metadata may have leaked into payload"
        )
        # Verify id is NOT inside the payload
        assert "id" not in retrieved.payload, (
            "Technical 'id' field must not appear inside the logical payload"
        )

        # Cleanup
        cosmos_store.delete(smoke_collection, unique_doc_id)

    def test_payload_does_not_gain_technical_fields(self, cosmos_store, smoke_collection, unique_doc_id):
        """Cosmos envelope must not inject _pk, _etag, id into payload on read-back."""
        from nexa_engine.db.models.stored_document import StoredDocument

        payload = {"version_id": unique_doc_id, "data": {"rate": 0.17, "name": "Cobranzas"}}
        cosmos_store.upsert_record(smoke_collection, StoredDocument(id=unique_doc_id, payload=payload))

        retrieved = cosmos_store.get_record(smoke_collection, unique_doc_id)
        assert retrieved is not None

        forbidden_keys = {"id", "_pk", "_etag", "partition_value", "_ts"}
        leaked = forbidden_keys & set(retrieved.payload.keys())
        assert not leaked, f"Technical fields leaked into payload: {leaked}"

        # Cleanup
        cosmos_store.delete(smoke_collection, unique_doc_id)

    def test_get_nonexistent_returns_none(self, cosmos_store, smoke_collection):
        """get_record for nonexistent document returns None, not an exception."""
        result = cosmos_store.get_record(smoke_collection, f"nonexistent-{uuid.uuid4().hex}")
        assert result is None

    def test_list_records_returns_previously_written(self, cosmos_store, smoke_collection, unique_doc_id):
        """list_records includes a document just written."""
        from nexa_engine.db.models.stored_document import StoredDocument

        payload = {"version_id": unique_doc_id, "test": True}
        cosmos_store.upsert_record(smoke_collection, StoredDocument(id=unique_doc_id, payload=payload))

        records, _ = cosmos_store.list_records(smoke_collection)
        ids = {r.id for r in records}
        assert unique_doc_id in ids, "Document written but not found in list_records"

        # Cleanup
        cosmos_store.delete(smoke_collection, unique_doc_id)

    def test_delete_removes_document(self, cosmos_store, smoke_collection, unique_doc_id):
        """delete removes a document so get_record returns None afterward."""
        from nexa_engine.db.models.stored_document import StoredDocument
        from nexa_engine.db.exceptions import DbNotFoundError

        payload = {"version_id": unique_doc_id}
        cosmos_store.upsert_record(smoke_collection, StoredDocument(id=unique_doc_id, payload=payload))
        assert cosmos_store.get_record(smoke_collection, unique_doc_id) is not None

        cosmos_store.delete(smoke_collection, unique_doc_id)
        assert cosmos_store.get_record(smoke_collection, unique_doc_id) is None

    def test_delete_nonexistent_raises_db_not_found(self, cosmos_store, smoke_collection):
        """Deleting a nonexistent document raises DbNotFoundError."""
        from nexa_engine.db.exceptions import DbNotFoundError
        with pytest.raises(DbNotFoundError):
            cosmos_store.delete(smoke_collection, f"ghost-{uuid.uuid4().hex}")

    def test_parametrization_payload_with_nested_catalogs(self, cosmos_store, smoke_collection, unique_doc_id):
        """Complex parametrization payload (HR-LV style) survives round-trip."""
        from nexa_engine.db.models.stored_document import StoredDocument

        payload = {
            "version_id": unique_doc_id,
            "niveles": {
                "catalogs": {
                    "tipo": [{"name": "Empleado"}, {"name": "Equipo de HITL"}],
                    "rol": [{"name": "Agente"}, {"name": "Supervisor"}, {"name": "Director"}],
                    "ssparafiscales": [{"name": "Salud"}, {"name": "Fondo de pensión"}, {"name": "ARL"}],
                }
            },
            "salarios": [
                {"servicio": "Salario Mínimo", "valor": 1750905.0},
                {"servicio": "%Cumplimiento Variable", "valor": 0.7},
            ],
            "rentabilidad": [
                {"categoriaservicio": "Cobranzas", "minimo": 0.17, "margenobjetivo": 0.18},
            ],
        }
        original_hash = _payload_hash(payload)

        cosmos_store.upsert_record(smoke_collection, StoredDocument(id=unique_doc_id, payload=payload))
        retrieved = cosmos_store.get_record(smoke_collection, unique_doc_id)

        assert retrieved is not None
        assert _payload_hash(retrieved.payload) == original_hash, (
            f"Complex payload hash changed. Original={original_hash[:12]}, "
            f"Retrieved={_payload_hash(retrieved.payload)[:12]}"
        )

        # Cleanup
        cosmos_store.delete(smoke_collection, unique_doc_id)


class TestCosmosTransactionalBatch:
    """Real Cosmos validation for transactional batch + optimistic concurrency."""

    @pytest.mark.parametrize(
        "domain",
        ["gn", "hr", "op", "business_rules"],
    )
    def test_domain_partition_round_trip_without_payload_metadata(
        self,
        cosmos_store,
        domain,
    ):
        from nexa_engine.db.models.collection_config import CollectionConfig
        from nexa_engine.db.models.stored_document import StoredDocument

        collection = CollectionConfig(name=domain)
        document_id = f"{domain}-{uuid.uuid4().hex[:8]}"
        payload = {"version_id": document_id, "domain": domain, "value": 1}

        cosmos_store.upsert_record(
            collection,
            StoredDocument(id=document_id, payload=payload, partition_value=domain),
        )
        retrieved = cosmos_store.get_record(
            collection,
            document_id,
            partition_value=domain,
        )

        assert retrieved is not None
        assert retrieved.partition_value == domain
        assert retrieved.payload == payload
        assert not ({"id", "_pk", "_etag"} & set(retrieved.payload))

        cosmos_store.delete(collection, document_id, partition_value=domain)

    def test_transactional_batch_writes_payload_and_versions_in_one_partition(
        self,
        cosmos_store,
    ):
        from nexa_engine.db.models.collection_config import CollectionConfig
        from nexa_engine.db.models.stored_document import StoredDocument

        collection = CollectionConfig(name="gn")
        version_id = f"gn-{uuid.uuid4().hex[:8]}"
        payload = {"version_id": version_id, "lv": {}, "sheets": []}
        versions = [
            {
                "version_id": version_id,
                "filename": "GN.xlsx",
                "uploaded_at": "2026-06-05T00:00:00Z",
                "is_active": True,
                "sheet_count": 1,
                "total_rows": 1,
            }
        ]

        cosmos_store.upsert_records_atomic(
            collection,
            [
                StoredDocument(id=version_id, payload=payload, partition_value="gn"),
                StoredDocument(id="versions", payload=versions, partition_value="gn"),
            ],
        )

        stored_payload = cosmos_store.get_record(collection, version_id, partition_value="gn")
        stored_versions = cosmos_store.get_record(collection, "versions", partition_value="gn")

        assert stored_payload is not None
        assert stored_versions is not None
        assert stored_payload.payload == payload
        assert stored_versions.payload == versions
        assert stored_payload.partition_value == "gn"
        assert stored_versions.partition_value == "gn"
        assert not ({"id", "_pk", "_etag"} & set(stored_payload.payload))
        assert "_etag" not in stored_versions.payload[0]

        cosmos_store.delete(collection, version_id, partition_value="gn")
        cosmos_store.delete(collection, "versions", partition_value="gn")

    def test_transactional_batch_rejects_stale_versions_etag(
        self,
        cosmos_store,
    ):
        from nexa_engine.db.exceptions import DbConcurrencyError
        from nexa_engine.db.models.atomic_write import AtomicWritePrecondition
        from nexa_engine.db.models.collection_config import CollectionConfig
        from nexa_engine.db.models.stored_document import StoredDocument

        collection = CollectionConfig(name="hr")
        first_version = f"hr-{uuid.uuid4().hex[:8]}"
        second_version = f"hr-{uuid.uuid4().hex[:8]}"

        cosmos_store.upsert_records_atomic(
            collection,
            [
                StoredDocument(id=first_version, payload={"version_id": first_version}, partition_value="hr"),
                StoredDocument(
                    id="versions",
                    payload=[{"version_id": first_version, "is_active": True}],
                    partition_value="hr",
                ),
            ],
        )
        stale_versions = cosmos_store.get_record(collection, "versions", partition_value="hr")
        assert stale_versions is not None
        assert stale_versions.etag

        cosmos_store.upsert_records_atomic(
            collection,
            [
                StoredDocument(id=second_version, payload={"version_id": second_version}, partition_value="hr"),
                StoredDocument(
                    id="versions",
                    payload=[
                        {"version_id": first_version, "is_active": False},
                        {"version_id": second_version, "is_active": True},
                    ],
                    partition_value="hr",
                ),
            ],
            precondition=AtomicWritePrecondition(
                logical_id="versions",
                expected_etag=stale_versions.etag,
            ),
        )

        with pytest.raises(DbConcurrencyError):
            cosmos_store.upsert_records_atomic(
                collection,
                [
                    StoredDocument(id=f"hr-{uuid.uuid4().hex[:8]}", payload={"version_id": "stale"}, partition_value="hr"),
                    StoredDocument(
                        id="versions",
                        payload=[{"version_id": "stale", "is_active": True}],
                        partition_value="hr",
                    ),
                ],
                precondition=AtomicWritePrecondition(
                    logical_id="versions",
                    expected_etag=stale_versions.etag,
                ),
            )

        cosmos_store.delete(collection, first_version, partition_value="hr")
        cosmos_store.delete(collection, second_version, partition_value="hr")
        cosmos_store.delete(collection, "versions", partition_value="hr")
