"""Endpoints públicos del módulo de identidades anónimas.

POST   /api/v1/identity/anonymous          — crear identidad
GET    /api/v1/identity/{identity_id}      — obtener identidad
PATCH  /api/v1/identity/{identity_id}/last-seen — actualizar lastSeenAt

identityId NO es una credencial y no debe usarse para autorización.
La autenticación real llegará con Keycloak en una fase futura.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Path

from nexa_engine.modules.identity.api.schemas import IdentityResponse
from nexa_engine.modules.identity.services.identity_service import IdentityService
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.db.dependencies import get_identity_service

logger = logging.getLogger("nexa.identity.router")

router = APIRouter(prefix="/identity", tags=["Identity"])

_UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"


@router.post(
    "/anonymous",
    response_model=ApiResponse,
    status_code=201,
    summary="Crear identidad anónima",
    description=(
        "Genera un identityId (UUID v4) y un alias determinístico en backend. "
        "No acepta identityId desde el cliente. "
        "NOTA: identityId no es una credencial; no debe usarse para autorización."
    ),
    operation_id="createAnonymousIdentity",
)
def create_anonymous_identity(
    service: IdentityService = Depends(get_identity_service),
) -> ApiResponse:
    identity = service.create_anonymous()
    return ApiResponse.ok(IdentityResponse.from_identity(identity).model_dump())


@router.get(
    "/{identity_id}",
    response_model=ApiResponse,
    summary="Obtener identidad por ID",
    description="Retorna la identidad si existe. No crea una nueva si no se encuentra.",
    operation_id="getIdentity",
)
def get_identity(
    identity_id: str = Path(..., pattern=_UUID_PATTERN, description="UUID v4 de la identidad"),
    service: IdentityService = Depends(get_identity_service),
) -> ApiResponse:
    identity = service.get(identity_id)
    return ApiResponse.ok(IdentityResponse.from_identity(identity).model_dump())


@router.patch(
    "/{identity_id}/last-seen",
    response_model=ApiResponse,
    summary="Actualizar lastSeenAt",
    description=(
        "Actualiza lastSeenAt con timestamp UTC actual. "
        "No modifica: identityId, alias, createdAt, authenticationType, "
        "userId, keycloakSubject, confidenceScore."
    ),
    operation_id="touchIdentity",
)
def touch_identity(
    identity_id: str = Path(..., pattern=_UUID_PATTERN, description="UUID v4 de la identidad"),
    service: IdentityService = Depends(get_identity_service),
) -> ApiResponse:
    identity = service.touch(identity_id)
    return ApiResponse.ok(IdentityResponse.from_identity(identity).model_dump())
