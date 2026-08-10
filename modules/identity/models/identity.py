"""Modelo de dominio para identidad anónima de Simulator Pricing."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class Identity(BaseModel):
    """Documento de identidad persistido en CosmosDB.

    id == identityId: UUID v4. Cosmos requiere 'id'; el modelo de dominio
    requiere 'identityId'. Ambos campos apuntan al mismo valor para evitar
    redundancia de identificadores y permitir point reads eficientes.

    Almacenado en container 'parameterization', partición domain='identities'.
    """

    model_config = {"extra": "allow"}

    id: str
    identityId: str
    alias: str
    authenticationType: str = "anonymous"
    userId: Optional[str] = None
    keycloakSubject: Optional[str] = None
    confidenceScore: int = 100
    status: str = "active"
    createdAt: str
    lastSeenAt: str

    # Campos internos de Cosmos — no se exponen en respuestas públicas
    domain: str = "identities"
    type: str = "identity"
