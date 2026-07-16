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
    """Crea un nuevo borrador de simulación con `status=active`.

    **Regla de unicidad:** antes de guardar el nuevo borrador, todos los borradores
    con `status=active` existentes en el container se actualizan automáticamente
    a `status=inactive`. Solo el borrador recién creado queda activo.

    Campos obligatorios: `client_id` (clave de partición en CosmosDB).
    Campos opcionales: `user_id`, `id_hr`, `id_gn`, `id_op`, `panel_de_control`,
    `condiciones_cadena_a`, `condiciones_cadena_b`, `condiciones_cadena_c`.

    Retorna el documento con `id` UUID4 autogenerado, `version=1`, `status=active`
    y timestamps `created_at` / `updated_at`.
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

    Solo las secciones enviadas con valor distinto de `null` reemplazan las
    almacenadas. Las secciones ausentes o `null` se conservan sin cambios.
    Incrementa `version` en cada llamada exitosa.

    **Sincronización automática de `client_id`:** si `panel_de_control.cliente`
    está presente en el documento resultante (del request o del doc almacenado),
    el campo `client_id` se actualiza automáticamente con ese valor. Si el
    `client_id` cambia respecto al anterior, el documento se reubica en la nueva
    partición de CosmosDB (delete + insert transparente).

    **Importante:** después de un PUT donde `panel_de_control.cliente` cambió,
    usar el nuevo `client_id` del response en todas las llamadas siguientes
    a GET, PUT y DELETE.
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
