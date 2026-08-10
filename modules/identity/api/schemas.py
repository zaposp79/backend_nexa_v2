"""DTOs públicos del módulo de identidades.

Los campos internos (domain, type) no se exponen en respuestas de API.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class IdentityResponse(BaseModel):
    """Contrato público de una identidad — respuesta de todos los endpoints."""

    model_config = {"extra": "ignore"}

    identityId: str
    alias: str
    authenticationType: str
    confidenceScore: int
    status: str
    createdAt: str
    lastSeenAt: str

    @classmethod
    def from_identity(cls, identity) -> "IdentityResponse":
        return cls(
            identityId=identity.identityId,
            alias=identity.alias,
            authenticationType=identity.authenticationType,
            confidenceScore=identity.confidenceScore,
            status=identity.status,
            createdAt=identity.createdAt,
            lastSeenAt=identity.lastSeenAt,
        )
