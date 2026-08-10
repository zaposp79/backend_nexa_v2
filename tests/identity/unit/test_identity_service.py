"""Tests unitarios de IdentityService con Repository y AliasService mockeados."""
import pytest
from unittest.mock import MagicMock, patch
from nexa_engine.modules.identity.services.identity_service import IdentityService
from nexa_engine.modules.identity.services.alias_service import AliasService
from nexa_engine.modules.identity.models.identity import Identity
from nexa_engine.modules.shared.exceptions import NotFoundError, ValidationError


IDENTITY_ID = "9b8c7f6e-5d4c-4b3a-8291-a0b1c2d3e4f5"
INVALID_UUID = "not-a-uuid"


def _make_doc(identity_id: str = IDENTITY_ID) -> dict:
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
def repo():
    return MagicMock()


@pytest.fixture
def alias_svc():
    svc = MagicMock(spec=AliasService)
    svc.generate.return_value = "Jaguar Azul 27"
    return svc


@pytest.fixture
def svc(repo, alias_svc) -> IdentityService:
    return IdentityService(repository=repo, alias_service=alias_svc)


class TestCreateAnonymous:
    def test_creates_identity_with_generated_uuid(self, svc, repo):
        doc = _make_doc()
        repo.create.return_value = doc
        identity = svc.create_anonymous()
        assert identity.authenticationType == "anonymous"
        assert identity.status == "active"
        assert identity.confidenceScore == 100

    def test_identity_id_is_not_null(self, svc, repo):
        doc = _make_doc()
        repo.create.return_value = doc
        identity = svc.create_anonymous()
        assert identity.identityId is not None
        assert len(identity.identityId) > 0

    def test_alias_is_set(self, svc, repo, alias_svc):
        doc = _make_doc()
        repo.create.return_value = doc
        identity = svc.create_anonymous()
        assert identity.alias == "Jaguar Azul 27"
        alias_svc.generate.assert_called_once()

    def test_user_id_is_null(self, svc, repo):
        doc = _make_doc()
        repo.create.return_value = doc
        identity = svc.create_anonymous()
        assert identity.userId is None

    def test_keycloak_subject_is_null(self, svc, repo):
        doc = _make_doc()
        repo.create.return_value = doc
        identity = svc.create_anonymous()
        assert identity.keycloakSubject is None

    def test_created_at_equals_last_seen_at_on_creation(self, svc, repo):
        doc = _make_doc()
        repo.create.return_value = doc
        identity = svc.create_anonymous()
        # En creación son iguales (mismo timestamp)
        assert identity.createdAt == identity.lastSeenAt


class TestGet:
    def test_returns_identity_when_exists(self, svc, repo):
        repo.get_by_identity_id.return_value = _make_doc()
        identity = svc.get(IDENTITY_ID)
        assert identity.identityId == IDENTITY_ID

    def test_raises_not_found_when_missing(self, svc, repo):
        repo.get_by_identity_id.side_effect = NotFoundError("Identity", IDENTITY_ID)
        with pytest.raises(NotFoundError):
            svc.get(IDENTITY_ID)

    def test_raises_validation_error_for_invalid_uuid(self, svc, repo):
        with pytest.raises(ValidationError):
            svc.get(INVALID_UUID)

    def test_does_not_create_if_not_found(self, svc, repo):
        repo.get_by_identity_id.side_effect = NotFoundError("Identity", IDENTITY_ID)
        with pytest.raises(NotFoundError):
            svc.get(IDENTITY_ID)
        repo.create.assert_not_called()


class TestTouch:
    def test_updates_last_seen(self, svc, repo):
        updated_doc = {**_make_doc(), "lastSeenAt": "2026-08-07T23:00:00Z"}
        repo.update_last_seen.return_value = updated_doc
        identity = svc.touch(IDENTITY_ID)
        assert identity.lastSeenAt == "2026-08-07T23:00:00Z"

    def test_does_not_modify_created_at(self, svc, repo):
        original = _make_doc()
        repo.update_last_seen.return_value = original
        identity = svc.touch(IDENTITY_ID)
        assert identity.createdAt == "2026-08-07T22:30:00Z"

    def test_does_not_modify_alias(self, svc, repo):
        doc = _make_doc()
        repo.update_last_seen.return_value = doc
        identity = svc.touch(IDENTITY_ID)
        assert identity.alias == "Jaguar Azul 27"

    def test_does_not_modify_authentication_type(self, svc, repo):
        doc = _make_doc()
        repo.update_last_seen.return_value = doc
        identity = svc.touch(IDENTITY_ID)
        assert identity.authenticationType == "anonymous"

    def test_raises_validation_error_for_invalid_uuid(self, svc, repo):
        with pytest.raises(ValidationError):
            svc.touch(INVALID_UUID)

    def test_calls_repo_update_not_create(self, svc, repo):
        doc = _make_doc()
        repo.update_last_seen.return_value = doc
        svc.touch(IDENTITY_ID)
        repo.update_last_seen.assert_called_once()
        repo.create.assert_not_called()
