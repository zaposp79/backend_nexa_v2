"""Tests de API para los endpoints de identidad."""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from fastapi.responses import JSONResponse

from nexa_engine.modules.identity.api.router import router as identity_router
from nexa_engine.modules.identity.services.identity_service import IdentityService
from nexa_engine.modules.identity.models.identity import Identity
from nexa_engine.modules.shared.exceptions import NotFoundError, ValidationError
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.db.dependencies import get_identity_service


IDENTITY_ID = "9b8c7f6e-5d4c-4b3a-8291-a0b1c2d3e4f5"
INVALID_UUID = "not-a-uuid"


def _make_identity(identity_id: str = IDENTITY_ID) -> Identity:
    return Identity(
        id=identity_id,
        identityId=identity_id,
        alias="Jaguar Azul 27",
        authenticationType="anonymous",
        userId=None,
        keycloakSubject=None,
        confidenceScore=100,
        status="active",
        domain="identities",
        type="identity",
        createdAt="2026-08-07T22:30:00Z",
        lastSeenAt="2026-08-07T22:30:00Z",
    )


@pytest.fixture
def mock_svc():
    return MagicMock(spec=IdentityService)


@pytest.fixture
def client(mock_svc) -> TestClient:
    app = FastAPI()
    app.include_router(identity_router, prefix="/api/v1")
    app.dependency_overrides[get_identity_service] = lambda: mock_svc

    @app.exception_handler(NotFoundError)
    async def _not_found(request, exc):
        return JSONResponse(
            status_code=404,
            content=ApiResponse.fail(
                getattr(exc, "sim_code", None) or "SIM-00600",
                message=str(exc),
            ).model_dump(),
        )

    @app.exception_handler(ValidationError)
    async def _validation(request, exc):
        return JSONResponse(
            status_code=422,
            content=ApiResponse.fail(
                getattr(exc, "sim_code", None) or "SIM-00400",
                message=str(exc),
            ).model_dump(),
        )

    return TestClient(app, raise_server_exceptions=False)


class TestPostAnonymous:
    def test_creates_identity_returns_201(self, client, mock_svc):
        mock_svc.create_anonymous.return_value = _make_identity()
        response = client.post("/api/v1/identity/anonymous")
        assert response.status_code == 201

    def test_response_contains_identity_id(self, client, mock_svc):
        mock_svc.create_anonymous.return_value = _make_identity()
        data = client.post("/api/v1/identity/anonymous").json()
        assert data["success"] is True
        assert data["data"]["identityId"] == IDENTITY_ID

    def test_response_contains_alias(self, client, mock_svc):
        mock_svc.create_anonymous.return_value = _make_identity()
        data = client.post("/api/v1/identity/anonymous").json()
        assert data["data"]["alias"] == "Jaguar Azul 27"

    def test_response_does_not_expose_domain(self, client, mock_svc):
        mock_svc.create_anonymous.return_value = _make_identity()
        data = client.post("/api/v1/identity/anonymous").json()
        assert "domain" not in data["data"]

    def test_response_does_not_expose_type(self, client, mock_svc):
        mock_svc.create_anonymous.return_value = _make_identity()
        data = client.post("/api/v1/identity/anonymous").json()
        assert "type" not in data["data"]

    def test_authentication_type_is_anonymous(self, client, mock_svc):
        mock_svc.create_anonymous.return_value = _make_identity()
        data = client.post("/api/v1/identity/anonymous").json()
        assert data["data"]["authenticationType"] == "anonymous"


class TestGetIdentity:
    def test_returns_200_when_found(self, client, mock_svc):
        mock_svc.get.return_value = _make_identity()
        response = client.get(f"/api/v1/identity/{IDENTITY_ID}")
        assert response.status_code == 200

    def test_returns_identity_data(self, client, mock_svc):
        mock_svc.get.return_value = _make_identity()
        data = client.get(f"/api/v1/identity/{IDENTITY_ID}").json()
        assert data["data"]["identityId"] == IDENTITY_ID

    def test_returns_422_for_invalid_uuid(self, client, mock_svc):
        response = client.get(f"/api/v1/identity/{INVALID_UUID}")
        assert response.status_code == 422

    def test_returns_404_when_not_found(self, client, mock_svc):
        mock_svc.get.side_effect = NotFoundError("Identity", IDENTITY_ID)
        response = client.get(f"/api/v1/identity/{IDENTITY_ID}")
        assert response.status_code == 404

    def test_does_not_create_identity_on_404(self, client, mock_svc):
        mock_svc.get.side_effect = NotFoundError("Identity", IDENTITY_ID)
        client.get(f"/api/v1/identity/{IDENTITY_ID}")
        mock_svc.create_anonymous.assert_not_called()


class TestPatchLastSeen:
    def test_returns_200_on_success(self, client, mock_svc):
        updated = _make_identity()
        mock_svc.touch.return_value = updated
        response = client.patch(f"/api/v1/identity/{IDENTITY_ID}/last-seen")
        assert response.status_code == 200

    def test_returns_updated_identity(self, client, mock_svc):
        updated = _make_identity()
        mock_svc.touch.return_value = updated
        data = client.patch(f"/api/v1/identity/{IDENTITY_ID}/last-seen").json()
        assert data["data"]["identityId"] == IDENTITY_ID

    def test_returns_422_for_invalid_uuid(self, client, mock_svc):
        response = client.patch(f"/api/v1/identity/{INVALID_UUID}/last-seen")
        assert response.status_code == 422

    def test_returns_404_when_not_found(self, client, mock_svc):
        mock_svc.touch.side_effect = NotFoundError("Identity", IDENTITY_ID)
        response = client.patch(f"/api/v1/identity/{IDENTITY_ID}/last-seen")
        assert response.status_code == 404

    def test_does_not_modify_alias_in_response(self, client, mock_svc):
        identity = _make_identity()
        mock_svc.touch.return_value = identity
        data = client.patch(f"/api/v1/identity/{IDENTITY_ID}/last-seen").json()
        assert data["data"]["alias"] == "Jaguar Azul 27"
