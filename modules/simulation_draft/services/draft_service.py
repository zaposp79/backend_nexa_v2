"""Lógica de negocio para borradores de simulación."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.simulation_draft.api.draft_dto import (
    SimulationDraftListItem,
    SimulationDraftRequest,
    SimulationDraftResponse,
    SimulationDraftUpdateRequest,
)
from nexa_engine.modules.simulation_draft.persistence.draft_repository import (
    SimulationDraftRepository,
)

# Campos de sistema que CosmosDB agrega a los documentos al leerlos.
_COSMOS_SYSTEM_FIELDS = {"_rid", "_self", "_etag", "_attachments", "_ts", "domain"}


def _clean(doc: dict) -> dict:
    """Retorna el documento sin campos de sistema de CosmosDB."""
    return {k: v for k, v in doc.items() if k not in _COSMOS_SYSTEM_FIELDS}


def _dump(model) -> dict | None:
    """Serializa un modelo Pydantic a dict excluyendo None, o retorna None."""
    if model is None:
        return None
    return model.model_dump(exclude_none=True)


class SimulationDraftService:
    def __init__(self, repository: SimulationDraftRepository) -> None:
        self._repo = repository

    def _get_by_id(self, draft_id: str) -> dict:
        all_docs = self._repo.list_all()
        for doc in all_docs:
            if doc.get("id") == draft_id and doc.get("type") == "draft":
                return doc
        raise NotFoundError("SimulationDraft", draft_id)

    def create(self, request: SimulationDraftRequest) -> SimulationDraftResponse:
        now = datetime.now(timezone.utc).isoformat()

        # Desactivar todos los borradores activos antes de crear el nuevo
        for active_doc in self._repo.find_by_status("active"):
            clean_active = _clean(active_doc)
            clean_active["status"] = "inactive"
            clean_active["updated_at"] = now
            clean_active["client_id"] = clean_active.get("client_id") or "anonymous"
            self._repo.save(clean_active)

        client_id = request.client_id or "anonymous"

        document = {
            "id": str(uuid.uuid4()),
            "client_id": client_id,
            "id_hr": request.id_hr,
            "id_gn": request.id_gn,
            "id_op": request.id_op,
            "type": "draft",
            "status": "active",
            "user_id": request.user_id,
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "datos_operativos": _dump(request.datos_operativos),
            "polizas": (
                [_dump(p) for p in request.polizas]
                if request.polizas is not None else None
            ),
            "reglas_negocio": _dump(request.reglas_negocio),
            "volumetria": _dump(request.volumetria),
            "escenarios_comerciales": (
                [_dump(e) for e in request.escenarios_comerciales]
                if request.escenarios_comerciales is not None else None
            ),
            "condiciones_cadena_a": _dump(request.condiciones_cadena_a),
            "condiciones_cadena_b": _dump(request.condiciones_cadena_b),
            "condiciones_cadena_c": _dump(request.condiciones_cadena_c),
        }
        saved = self._repo.save(document)
        return _to_response(saved)

    def update(self, draft_id: str, request: SimulationDraftUpdateRequest) -> SimulationDraftResponse:
        existing_raw = self._get_by_id(draft_id)
        existing = _clean(existing_raw)
        old_client_id = existing.get("client_id", "")
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
        if request.datos_operativos is not None:
            document["datos_operativos"] = _dump(request.datos_operativos)
        if request.polizas is not None:
            document["polizas"] = [_dump(p) for p in request.polizas]
        if request.reglas_negocio is not None:
            document["reglas_negocio"] = _dump(request.reglas_negocio)
        if request.volumetria is not None:
            document["volumetria"] = _dump(request.volumetria)
        if request.escenarios_comerciales is not None:
            document["escenarios_comerciales"] = [_dump(e) for e in request.escenarios_comerciales]
        if request.condiciones_cadena_a is not None:
            document["condiciones_cadena_a"] = _dump(request.condiciones_cadena_a)
        if request.condiciones_cadena_b is not None:
            document["condiciones_cadena_b"] = _dump(request.condiciones_cadena_b)
        if request.condiciones_cadena_c is not None:
            document["condiciones_cadena_c"] = _dump(request.condiciones_cadena_c)

        # client_id se sincroniza con datos_operativos.cliente si está presente
        datos_op = document.get("datos_operativos") or {}
        cliente = datos_op.get("cliente")
        if cliente:
            document["client_id"] = cliente

        new_client_id = document.get("client_id", "")
        if new_client_id != old_client_id:
            saved = self._repo.relocate(old_client_id, document)
        else:
            saved = self._repo.save(document)

        return _to_response(saved)

    def get(self, draft_id: str, client_id: str | None = None) -> SimulationDraftResponse:
        doc = self._repo.find_by_id(draft_id, client_id=client_id)
        return _to_response(_clean(doc))

    def list_all(self) -> list[SimulationDraftListItem]:
        docs = self._repo.list_all()
        return [_to_list_item(doc) for doc in docs]

    def delete(self, draft_id: str) -> None:
        doc = self._get_by_id(draft_id)
        client_id = doc.get("client_id", "")
        self._repo.delete_by_partition(draft_id, client_id)


def _to_list_item(doc: dict) -> SimulationDraftListItem:
    """Mapeo plano para el listado: raíz + campos clave de datos_operativos."""
    datos = doc.get("datos_operativos") or {}
    return SimulationDraftListItem(
        id=doc["id"],
        client_id=doc.get("client_id"),
        id_hr=doc.get("id_hr"),
        id_gn=doc.get("id_gn"),
        id_op=doc.get("id_op"),
        status=doc.get("status", "active"),
        user_id=doc.get("user_id", "anonymous"),
        version=doc.get("version", 1),
        updated_at=doc.get("updated_at", ""),
        servicio=datos.get("servicio"),
        cliente=datos.get("cliente"),
        periodo_pago=datos.get("periodo_pago"),
        fecha_inicio=datos.get("fecha_inicio"),
        duracion_meses=datos.get("duracion_meses"),
        ciudad=datos.get("ciudad"),
        sede=datos.get("sede"),
    )


def _to_response(doc: dict) -> SimulationDraftResponse:
    return SimulationDraftResponse.model_validate({
        "id": doc["id"],
        "client_id": doc.get("client_id"),
        "id_hr": doc.get("id_hr"),
        "id_gn": doc.get("id_gn"),
        "id_op": doc.get("id_op"),
        "status": doc.get("status", "active"),
        "user_id": doc.get("user_id", "anonymous"),
        "version": doc.get("version", 1),
        "created_at": doc.get("created_at", ""),
        "updated_at": doc.get("updated_at", ""),
        "datos_operativos": doc.get("datos_operativos"),
        "polizas": doc.get("polizas"),
        "reglas_negocio": doc.get("reglas_negocio"),
        "volumetria": doc.get("volumetria"),
        "escenarios_comerciales": doc.get("escenarios_comerciales"),
        "condiciones_cadena_a": doc.get("condiciones_cadena_a"),
        "condiciones_cadena_b": doc.get("condiciones_cadena_b"),
        "condiciones_cadena_c": doc.get("condiciones_cadena_c"),
    })


__all__ = ["SimulationDraftService"]
