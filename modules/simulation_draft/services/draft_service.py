"""Lógica de negocio para borradores de simulación."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.simulation_draft.api.draft_dto import (
    SimulationDraftRequest,
    SimulationDraftResponse,
    SimulationDraftUpdateRequest,
)
from nexa_engine.modules.simulation_draft.persistence.draft_repository import (
    SimulationDraftRepository,
)

# Campos de sistema que CosmosDB agrega a los documentos al leerlos.
# Deben eliminarse antes de hacer upsert para evitar errores al reubicar particiones.
_COSMOS_SYSTEM_FIELDS = {"_rid", "_self", "_etag", "_attachments", "_ts", "domain"}


def _clean(doc: dict) -> dict:
    """Retorna el documento sin campos de sistema de CosmosDB."""
    return {k: v for k, v in doc.items() if k not in _COSMOS_SYSTEM_FIELDS}


class SimulationDraftService:
    def __init__(self, repository: SimulationDraftRepository) -> None:
        self._repo = repository

    def _get_by_id(self, draft_id: str) -> dict:
        """Busca un borrador usando list_all() + filtro Python.
        Mismo path que GET /all — garantizado que funciona si el doc existe.
        """
        all_docs = self._repo.list_all()
        for doc in all_docs:
            if doc.get("id") == draft_id:
                return doc
        raise NotFoundError("SimulationDraft", draft_id)

    def create(self, request: SimulationDraftRequest) -> SimulationDraftResponse:
        now = datetime.now(timezone.utc).isoformat()

        # Desactivar todos los borradores activos antes de crear el nuevo
        for active_doc in self._repo.find_by_status("active"):
            clean_active = _clean(active_doc)
            clean_active["status"] = "inactive"
            clean_active["updated_at"] = now
            self._repo.save(clean_active)

        document = {
            "id": str(uuid.uuid4()),
            "user_id": request.user_id,
            "client_id": request.client_id,
            "id_hr": request.id_hr,
            "id_gn": request.id_gn,
            "id_op": request.id_op,
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
        existing_raw = self._get_by_id(draft_id)
        existing = _clean(existing_raw)  # elimina campos de sistema antes de operar
        old_client_id = existing["client_id"]
        now = datetime.now(timezone.utc).isoformat()

        document = {
            **existing,
            "updated_at": now,
            "version": existing.get("version", 1) + 1,
        }
        if request.user_id is not None:
            document["user_id"] = request.user_id
        if request.client_id is not None:
            document["client_id"] = request.client_id
        if request.id_hr is not None:
            document["id_hr"] = request.id_hr
        if request.id_gn is not None:
            document["id_gn"] = request.id_gn
        if request.id_op is not None:
            document["id_op"] = request.id_op
        if request.panel_de_control is not None:
            document["panel_de_control"] = request.panel_de_control.model_dump(exclude_none=True)
        if request.condiciones_cadena_a is not None:
            document["condiciones_cadena_a"] = request.condiciones_cadena_a.model_dump(exclude_none=True)
        if request.condiciones_cadena_b is not None:
            document["condiciones_cadena_b"] = request.condiciones_cadena_b.model_dump(exclude_none=True)
        if request.condiciones_cadena_c is not None:
            document["condiciones_cadena_c"] = request.condiciones_cadena_c.model_dump(exclude_none=True)

        # client_id se sincroniza con panel_de_control.cliente (máxima prioridad)
        panel = document.get("panel_de_control") or {}
        cliente = panel.get("cliente")
        if cliente:
            document["client_id"] = cliente

        new_client_id = document["client_id"]
        if new_client_id != old_client_id:
            saved = self._repo.relocate(old_client_id, document)
        else:
            saved = self._repo.save(document)

        return _to_response(saved)

    def get(self, draft_id: str) -> SimulationDraftResponse:
        doc = self._get_by_id(draft_id)
        return _to_response(_clean(doc))

    def list_all(self) -> list[SimulationDraftResponse]:
        docs = self._repo.list_all()
        return [_to_response(doc) for doc in docs]

    def delete(self, draft_id: str) -> None:
        doc = self._get_by_id(draft_id)
        client_id = doc["client_id"]
        self._repo.delete_by_partition(draft_id, client_id)


def _to_response(doc: dict) -> SimulationDraftResponse:
    return SimulationDraftResponse.model_validate({
        "id": doc["id"],
        "user_id": doc.get("user_id", "anonymous"),
        "client_id": doc.get("client_id", ""),
        "id_hr": doc.get("id_hr"),
        "id_gn": doc.get("id_gn"),
        "id_op": doc.get("id_op"),
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
