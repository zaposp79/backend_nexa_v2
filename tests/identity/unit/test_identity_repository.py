"""Tests unitarios de IdentityRepository con DocumentStore mockeado."""
import pytest
from unittest.mock import MagicMock, patch
from nexa_engine.modules.identity.repositories.identity_repository import IdentityRepository
from nexa_engine.modules.shared.exceptions import NotFoundError


def _make_doc(identity_id: str = "9b8c7f6e-5d4c-4b3a-8291-a0b1c2d3e4f5") -> dict:
    return {
        "id": identity_id,
        "identityId": identity_id,
        "alias": "Jaguar Azul 27",
        "authenticationType": "anonymous",
        "userId": None,
        "keycloakSubject": None,
        "confidenceScore": 100,
        "status": "active",
        "domain": "identities",
        "type": "identity",
        "createdAt": "2026-08-07T22:30:00Z",
        "lastSeenAt": "2026-08-07T22:30:00Z",
    }


@pytest.fixture
def store():
    return MagicMock()


@pytest.fixture
def repo(store) -> IdentityRepository:
    return IdentityRepository(store)


IDENTITY_ID = "9b8c7f6e-5d4c-4b3a-8291-a0b1c2d3e4f5"


class TestCreate:
    def test_create_calls_upsert(self, repo, store):
        doc = _make_doc()
        store.upsert.return_value = doc
        result = repo.create(doc)
        store.upsert.assert_called_once()
        assert result == doc

    def test_create_returns_stored_document(self, repo, store):
        doc = _make_doc()
        store.upsert.return_value = {**doc, "extra_cosmos_field": "x"}
        result = repo.create(doc)
        assert result["identityId"] == IDENTITY_ID


class TestGetByIdentityId:
    def test_get_returns_document_when_exists(self, repo, store):
        doc = _make_doc()
        store.get.return_value = doc
        result = repo.get_by_identity_id(IDENTITY_ID)
        assert result["identityId"] == IDENTITY_ID

    def test_get_raises_not_found_when_missing(self, repo, store):
        store.get.return_value = None
        with pytest.raises(NotFoundError):
            repo.get_by_identity_id(IDENTITY_ID)

    def test_get_calls_store_with_correct_partition(self, repo, store):
        store.get.return_value = _make_doc()
        repo.get_by_identity_id(IDENTITY_ID)
        call_kwargs = store.get.call_args
        assert call_kwargs.kwargs.get("partition_value") == "identities"


class TestExists:
    def test_exists_true_when_found(self, repo, store):
        store.get.return_value = _make_doc()
        assert repo.exists(IDENTITY_ID) is True

    def test_exists_false_when_not_found(self, repo, store):
        store.get.return_value = None
        assert repo.exists(IDENTITY_ID) is False


class TestUpdateLastSeen:
    def test_update_modifies_only_last_seen(self, repo, store):
        original = _make_doc()
        original["lastSeenAt"] = "2026-08-07T22:30:00Z"
        store.get.return_value = dict(original)
        store.upsert.return_value = {**original, "lastSeenAt": "2026-08-07T23:00:00Z"}

        result = repo.update_last_seen(IDENTITY_ID, "2026-08-07T23:00:00Z")

        assert result["lastSeenAt"] == "2026-08-07T23:00:00Z"
        # Verificar que el upsert recibió el timestamp actualizado
        upserted = store.upsert.call_args[0][1]
        assert upserted["lastSeenAt"] == "2026-08-07T23:00:00Z"

    def test_update_preserves_alias(self, repo, store):
        doc = _make_doc()
        store.get.return_value = dict(doc)
        store.upsert.return_value = dict(doc)
        repo.update_last_seen(IDENTITY_ID, "2026-08-07T23:00:00Z")
        upserted = store.upsert.call_args[0][1]
        assert upserted["alias"] == "Jaguar Azul 27"
