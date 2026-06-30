"""ParametrizationSnapshotRepository contract tests.

Validates put_snapshot / get_snapshot semantics using JsonDocumentStore.
Cosmos is skipped without credentials.

Guarantees under test:
  1. put_snapshot creates a snapshot document.
  2. get_snapshot returns it by (version, module).
  3. Duplicate put_snapshot raises ParametrizationSnapshotConflictError.
  4. Invalid module is rejected before touching the store.
  5. Document id never contains '/' or '\\'.
  6. Original payload is preserved after a failed duplicate attempt.
  7. get_snapshot returns None for nonexistent snapshot.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.modules.parametrizacion.repositories.parametrization_snapshot_repository import (
    ParametrizationSnapshotConflictError,
    ParametrizationSnapshotRepository,
    ParametrizationSnapshotValidationError,
)

_VERSION = "v2-7"
_BUSINESS_RULES_PAYLOAD = {
    "smmlv": 1300000,
    "gmf_rate": 0.004,
    "ica_rate": 0.00966,
}


def _make_json_repo(tmp_path: Path) -> ParametrizationSnapshotRepository:
    from nexa_engine.db.providers.json_document_store import JsonDocumentStore

    return ParametrizationSnapshotRepository(JsonDocumentStore(tmp_path))


def _make_cosmos_repo() -> ParametrizationSnapshotRepository:
    from nexa_engine.db.config import CosmosSettings
    from nexa_engine.db.constants.provider_constants import (
        ENV_COSMOS_CONTAINER,
        ENV_COSMOS_DATABASE,
        ENV_COSMOS_ENDPOINT,
        ENV_COSMOS_KEY,
    )
    from nexa_engine.db.providers.cosmos_document_store import CosmosDocumentStore

    if not os.getenv(ENV_COSMOS_ENDPOINT) or not os.getenv(ENV_COSMOS_KEY):
        pytest.skip("Cosmos credentials not configured")
    settings = CosmosSettings(
        endpoint=os.environ[ENV_COSMOS_ENDPOINT],
        key=os.environ[ENV_COSMOS_KEY],
        database=os.environ.get(ENV_COSMOS_DATABASE, "nexa_pricing_db"),
        container=os.environ.get(ENV_COSMOS_CONTAINER, "parametrization_snapshots"),
    )
    return ParametrizationSnapshotRepository(CosmosDocumentStore(settings))


@pytest.fixture(params=["json", "cosmos"])
def repo(request, tmp_path: Path) -> ParametrizationSnapshotRepository:
    if request.param == "json":
        return _make_json_repo(tmp_path)
    return _make_cosmos_repo()


class TestPutSnapshotCreates:
    def test_put_snapshot_creates_document(self, repo: ParametrizationSnapshotRepository) -> None:
        doc = repo.put_snapshot(_VERSION, "business_rules", _BUSINESS_RULES_PAYLOAD)
        assert doc["version"] == _VERSION
        assert doc["module"] == "business_rules"
        assert doc["schema_version"] == "parametrization_snapshot_v1"
        assert doc["payload"] == _BUSINESS_RULES_PAYLOAD

    def test_put_snapshot_includes_id(self, repo: ParametrizationSnapshotRepository) -> None:
        doc = repo.put_snapshot(_VERSION, "hr", {"smmlv": 1300000})
        assert doc["id"] == "v2-7__hr"

    def test_put_snapshot_created_at_present(self, repo: ParametrizationSnapshotRepository) -> None:
        doc = repo.put_snapshot(_VERSION, "gn", {"gn_key": "value"})
        assert "created_at" in doc
        assert doc["created_at"]

    def test_put_snapshot_with_hash(self, repo: ParametrizationSnapshotRepository) -> None:
        doc = repo.put_snapshot(
            _VERSION, "op", {"op_key": "val"}, content_hash="abc123deadbeef"
        )
        assert doc["hash"] == "abc123deadbeef"

    def test_get_snapshot_returns_created(self, repo: ParametrizationSnapshotRepository) -> None:
        repo.put_snapshot(_VERSION, "business_rules", _BUSINESS_RULES_PAYLOAD)
        result = repo.get_snapshot(_VERSION, "business_rules")
        assert result is not None
        assert result["payload"] == _BUSINESS_RULES_PAYLOAD
        assert result["module"] == "business_rules"

    def test_get_snapshot_returns_none_when_absent(
        self, repo: ParametrizationSnapshotRepository
    ) -> None:
        result = repo.get_snapshot(_VERSION, "gn")
        assert result is None


class TestPutSnapshotConflict:
    def test_duplicate_put_raises_conflict(self, repo: ParametrizationSnapshotRepository) -> None:
        repo.put_snapshot(_VERSION, "business_rules", _BUSINESS_RULES_PAYLOAD)
        with pytest.raises(ParametrizationSnapshotConflictError) as exc_info:
            repo.put_snapshot(_VERSION, "business_rules", {"different": "data"})
        err = exc_info.value
        assert err.version == _VERSION
        assert err.module == "business_rules"

    def test_original_payload_preserved_after_conflict(
        self, repo: ParametrizationSnapshotRepository
    ) -> None:
        original = {"smmlv": 1300000, "source": "certified"}
        repo.put_snapshot(_VERSION, "hr", original)
        try:
            repo.put_snapshot(_VERSION, "hr", {"smmlv": 999, "source": "tampered"})
        except ParametrizationSnapshotConflictError:
            pass
        retrieved = repo.get_snapshot(_VERSION, "hr")
        assert retrieved is not None
        assert retrieved["payload"]["source"] == "certified"
        assert retrieved["payload"]["smmlv"] == 1300000


class TestSafeIdFormat:
    def test_id_does_not_contain_slash(self, repo: ParametrizationSnapshotRepository) -> None:
        doc = repo.put_snapshot(_VERSION, "gn", {"key": "val"})
        assert "/" not in doc["id"]
        assert "\\" not in doc["id"]

    def test_id_uses_double_underscore_separator(
        self, repo: ParametrizationSnapshotRepository
    ) -> None:
        doc = repo.put_snapshot("v2-8", "op", {"key": "val"})
        assert doc["id"] == "v2-8__op"

    def test_all_modules_produce_safe_ids(self, repo: ParametrizationSnapshotRepository) -> None:
        for module in ["business_rules", "gn", "hr", "op"]:
            doc = repo.put_snapshot(_VERSION, module, {"module": module})
            assert doc["id"] == f"{_VERSION}__{module}"
            assert "/" not in doc["id"]


class TestModuleValidation:
    def test_invalid_module_raises_before_write(
        self, repo: ParametrizationSnapshotRepository
    ) -> None:
        with pytest.raises(ParametrizationSnapshotValidationError):
            repo.put_snapshot(_VERSION, "cadena_b", {"key": "val"})

    def test_empty_module_raises(self, repo: ParametrizationSnapshotRepository) -> None:
        with pytest.raises(ParametrizationSnapshotValidationError):
            repo.put_snapshot(_VERSION, "", {"key": "val"})

    def test_invalid_module_get_raises(self, repo: ParametrizationSnapshotRepository) -> None:
        with pytest.raises(ParametrizationSnapshotValidationError):
            repo.get_snapshot(_VERSION, "unknown_module")

    def test_unsafe_version_raises(self, repo: ParametrizationSnapshotRepository) -> None:
        with pytest.raises(ParametrizationSnapshotValidationError):
            repo.put_snapshot("v2-7/hack", "hr", {"key": "val"})


__all__ = [
    "TestPutSnapshotCreates",
    "TestPutSnapshotConflict",
    "TestSafeIdFormat",
    "TestModuleValidation",
]
