"""Endpoints para borradores de simulación (Panel de Control + Cadenas A/B/C).

POST   /simulation/draft          → crea borrador, devuelve id UUID4
GET    /simulation/draft/all      → lista todos los borradores del container
PUT    /simulation/draft/{id}     → actualiza secciones del borrador (merge parcial)
GET    /simulation/draft/{id}     → recupera borrador por id + client_id
DELETE /simulation/draft/{id}     → elimina borrador por id + client_id
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends

from nexa_engine.db.dependencies import get_draft_service
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.simulation_draft.api.draft_dto import (
    SimulationDraftRequest,
    SimulationDraftResponse,
    SimulationDraftUpdateRequest,
)
from nexa_engine.modules.simulation_draft.services.draft_service import SimulationDraftService

router = APIRouter(prefix="/simulation/draft", tags=["Simulation Draft"])


@router.post(
    "",
    response_model=ApiResponse[SimulationDraftResponse],
    status_code=201,
    operation_id="createSimulationDraft",
    summary="Crear borrador de simulación",
)
def create_draft(
    body: SimulationDraftRequest,
    service: SimulationDraftService = Depends(get_draft_service),
) -> ApiResponse[SimulationDraftResponse]:
    """Crea un nuevo borrador con id UUID4 automático.

    Incluye panel de control y/o condiciones de cadenas A, B, C (todos opcionales).
    Retorna el documento completo con id, version=1, status=active y timestamps.
    """
    draft = service.create(body)
    return ApiResponse.ok(draft)


@router.get(
    "/all",
    response_model=ApiResponse[List[SimulationDraftResponse]],
    operation_id="listAllSimulationDrafts",
    summary="Listar todos los borradores de simulación",
)
def list_all_drafts(
    service: SimulationDraftService = Depends(get_draft_service),
) -> ApiResponse[List[SimulationDraftResponse]]:
    """Retorna todos los borradores almacenados en el container 'configuration'.

    No requiere filtros. Realiza un scan completo del container en CosmosDB.
    """
    drafts = service.list_all()
    return ApiResponse.ok(drafts)


@router.put(
    "/{draft_id}",
    response_model=ApiResponse[SimulationDraftResponse],
    operation_id="updateSimulationDraft",
    summary="Actualizar borrador de simulación",
)
def update_draft(
    draft_id: str,
    body: SimulationDraftUpdateRequest,
    service: SimulationDraftService = Depends(get_draft_service),
) -> ApiResponse[SimulationDraftResponse]:
    """Actualiza un borrador existente (merge parcial por sección).

    Solo las secciones enviadas en el body reemplazan las almacenadas.
    Las secciones ausentes o null se conservan sin cambios.
    Incrementa `version` en cada llamada exitosa.
    """
    draft = service.update(draft_id, body)
    return ApiResponse.ok(draft)


@router.get(
    "/{draft_id}",
    response_model=ApiResponse[SimulationDraftResponse],
    operation_id="getSimulationDraft",
    summary="Recuperar borrador de simulación",
)
def get_draft(
    draft_id: str,
    client_id: str,
    service: SimulationDraftService = Depends(get_draft_service),
) -> ApiResponse[SimulationDraftResponse]:
    """Recupera un borrador por su id.

    `client_id` es requerido como query param (clave de partición en CosmosDB).
    """
    draft = service.get(draft_id, client_id)
    return ApiResponse.ok(draft)


@router.delete(
    "/{draft_id}",
    response_model=ApiResponse[dict],
    status_code=200,
    operation_id="deleteSimulationDraft",
    summary="Eliminar borrador de simulación",
)
def delete_draft(
    draft_id: str,
    client_id: str,
    service: SimulationDraftService = Depends(get_draft_service),
) -> ApiResponse[dict]:
    """Elimina un borrador del container 'configuration' en CosmosDB.

    `client_id` es requerido como query param (clave de partición en CosmosDB).
    Retorna 404 si el borrador no existe.
    """
    service.delete(draft_id, client_id)
    return ApiResponse.ok({"deleted": True, "id": draft_id})


__all__ = ["router"]
