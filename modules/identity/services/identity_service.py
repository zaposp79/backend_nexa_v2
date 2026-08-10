"""Servicio de identidades anónimas — coordinador entre Repository y AliasService.

No contiene lógica de acceso directo a CosmosDB.
Diseñado para evolucionar: cuando se agregue Keycloak, se añadirá un
KeycloakIdentityProvider sin reescribir este servicio.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from nexa_engine.modules.identity.models.identity import Identity
from nexa_engine.modules.identity.repositories.identity_repository import IdentityRepository
from nexa_engine.modules.identity.services.alias_service import AliasService
from nexa_engine.modules.shared.exceptions import NotFoundError, ValidationError

logger = logging.getLogger("nexa.identity.service")


def _utc_now() -> str:
    """Timestamp UTC en formato ISO-8601 (2026-08-07T22:30:00Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class IdentityService:
    """Lógica de negocio para identidades anónimas.

    Coordina IdentityRepository y AliasService.
    No interactúa directamente con CosmosDB ni el SDK de Azure.

    Preparado para evolución:
      - Fase actual: authenticationType='anonymous', userId/keycloakSubject=null
      - Fase futura: agregar KeycloakIdentityProvider que actualice userId y
        keycloakSubject sin reescribir este servicio.
    """

    def __init__(
        self,
        repository: IdentityRepository,
        alias_service: AliasService,
    ) -> None:
        self._repo = repository
        self._alias = alias_service

    # ------------------------------------------------------------------
    # Crear
    # ------------------------------------------------------------------

    def create_anonymous(self) -> Identity:
        """Genera una nueva identidad anónima con UUID v4 y alias determinístico.

        El identityId siempre se genera en backend (nunca se acepta del cliente).
        """
        identity_id = str(uuid.uuid4())
        alias = self._alias.generate(identity_id)
        now = _utc_now()

        doc = {
            "id": identity_id,
            "identityId": identity_id,
            "alias": alias,
            "authenticationType": "anonymous",
            "userId": None,
            "keycloakSubject": None,
            "confidenceScore": 100,
            "status": "active",
            "createdAt": now,
            "lastSeenAt": now,
        }

        stored = self._repo.create(doc)
        logger.info("[identity] new anonymous identity id=%s alias=%s", identity_id, alias)
        return Identity.model_validate(stored)

    # ------------------------------------------------------------------
    # Leer
    # ------------------------------------------------------------------

    def get(self, identity_id: str) -> Identity:
        """Obtiene una identidad por id. Lanza NotFoundError si no existe."""
        _validate_uuid(identity_id)
        doc = self._repo.get_by_identity_id(identity_id)
        return Identity.model_validate(doc)

    def exists(self, identity_id: str) -> bool:
        """True si la identidad existe en CosmosDB."""
        _validate_uuid(identity_id)
        return self._repo.exists(identity_id)

    # ------------------------------------------------------------------
    # Actualizar
    # ------------------------------------------------------------------

    def touch(self, identity_id: str) -> Identity:
        """Actualiza lastSeenAt. No modifica ningún otro campo."""
        _validate_uuid(identity_id)
        now = _utc_now()
        stored = self._repo.update_last_seen(identity_id, now)
        return Identity.model_validate(stored)


# ------------------------------------------------------------------
# Helpers de validación
# ------------------------------------------------------------------

def _validate_uuid(value: str) -> None:
    """Lanza ValidationError si el valor no es UUID v4 válido."""
    try:
        parsed = uuid.UUID(value, version=4)
        # UUID() acepta versiones distintas sin error; verificar explícitamente
        if str(parsed) != value.lower():
            raise ValueError("formato no coincide")
    except (ValueError, AttributeError):
        raise ValidationError(
            f"identityId inválido: '{value}' no es un UUID v4 válido.",
            field="identityId",
            sim_code="SIM-00502",
        )
