"""Lógica de negocio para borradores de simulación."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from nexa_engine.modules.simulation_draft.api.draft_dto import (
    SimulationDraftRequest,
    SimulationDraftResponse,
    SimulationDraftUpdateRequest,
)
from nexa_engine.modules.simulation_draft.persistence.draft_repository import (
    SimulationDraftRepository,
)


class SimulationDraftService:
    def __init__(self, repository: SimulationDraftRepository) -> None:
        self._repo = repository

    def create(self, request: SimulationDraftRequest) -> SimulationDraftResponse:
        now = datetime.now(timezone.utc).isoformat()
        document = {
            "id": str(uuid.uuid4()),
            "dataset_id": request.dataset_id,
            "user_id": request.user_id,
            "client_id": request.client_id,
            "version": 1,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "panel_de_control": (
                request.panel_de_control.model_dump(exclude_none=True)
                if request.panel_de_control else None
            ),
            "condiciones_cadena_a": (
                request.condiciones_cadena_a.model_dump(exclude_none=True)
                if request.condiciones_cadena_a else None
            ),
            "condiciones_cadena_b": (
                request.condiciones_cadena_b.model_dump(exclude_none=True)
                if request.condiciones_cadena_b else None
            ),
            "condiciones_cadena_c": (
                request.condiciones_cadena_c.model_dump(exclude_none=True)
                if request.condiciones_cadena_c else None
            ),
        }
        saved = self._repo.save(document)
        return _to_response(saved)

    def update(self, draft_id: str, request: SimulationDraftUpdateRequest) -> SimulationDraftResponse:
        existing = self._repo.get(draft_id, request.client_id)
        now = datetime.now(timezone.utc).isoformat()

        # Preserva todos los campos existentes y sobreescribe solo los enviados
        document = {
            **existing,
            "updated_at": now,
            "version": existing.get("version", 1) + 1,
        }
        if request.dataset_id is not None:
            document["dataset_id"] = request.dataset_id
        if request.user_id is not None:
            document["user_id"] = request.user_id
        if request.panel_de_control is not None:
            document["panel_de_control"] = request.panel_de_control.model_dump(exclude_none=True)
        if request.condiciones_cadena_a is not None:
            document["condiciones_cadena_a"] = request.condiciones_cadena_a.model_dump(exclude_none=True)
        if request.condiciones_cadena_b is not None:
            document["condiciones_cadena_b"] = request.condiciones_cadena_b.model_dump(exclude_none=True)
        if request.condiciones_cadena_c is not None:
            document["condiciones_cadena_c"] = request.condiciones_cadena_c.model_dump(exclude_none=True)

        saved = self._repo.save(document)
        return _to_response(saved)

    def get(self, draft_id: str, client_id: str) -> SimulationDraftResponse:
        doc = self._repo.get(draft_id, client_id)
        return _to_response(doc)


def _to_response(doc: dict) -> SimulationDraftResponse:
    return SimulationDraftResponse.model_validate({
        "id": doc["id"],
        "dataset_id": doc.get("dataset_id"),
        "user_id": doc.get("user_id", "anonymous"),
        "client_id": doc["client_id"],
        "version": doc.get("version", 1),
        "status": doc.get("status", "active"),
        "created_at": doc.get("created_at", ""),
        "updated_at": doc.get("updated_at", ""),
        "panel_de_control": doc.get("panel_de_control"),
        "condiciones_cadena_a": doc.get("condiciones_cadena_a"),
        "condiciones_cadena_b": doc.get("condiciones_cadena_b"),
        "condiciones_cadena_c": doc.get("condiciones_cadena_c"),
    })


__all__ = ["SimulationDraftService"]
