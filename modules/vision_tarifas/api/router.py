"""Vision Tarifas — HTTP endpoint."""
from __future__ import annotations
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from fastapi.responses import JSONResponse
from nexa_engine.db.dependencies import get_results_repository
from nexa_engine.modules.calculator.persistence.results_repository import ResultsRepository
from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.shared.responses import ApiResponse, ErrorDetail
from nexa_engine.modules.shared.error_catalog import make_detail as _make_detail
from nexa_engine.modules.vision_tarifas.api.schemas import (
    ModeloCobroApiResponseV1,
    ModeloCobroRecalculateRequest,
)
from nexa_engine.modules.vision_tarifas.helpers.modelo_cobro_mapper import (
    build_modelo_cobro_from_result,
)
from nexa_engine.modules.vision_tarifas.services.modelo_cobro_recalculation_service import (
    OverrideValidationError,
    recalculate_preview,
)

router = APIRouter(prefix="/simulation", tags=["Vision Tarifas"])


@router.get(
    "/{simulation_id}/results/vision-tarifas/modelo-cobro",
    summary="Obtener visión Modelo de Cobro",
    description="Retorna el contrato público modelo_cobro (sin recalcular).",
    operation_id="getVisionTarifasModeloCobro",
    response_model=ModeloCobroApiResponseV1,
    responses={
        200: {
            "description": "Contrato público screen-ready.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "cliente": "Banco de Bogotá",
                            "servicio": "Atención al cliente",
                            "ciudad": "Bogotá",
                            "selected_view_id": "escenario_1",
                            "resumen_resultado_escenario": [],
                            "modelo_cobro": [],
                            "desglose_producto_opex": [],
                        },
                        "error": None,
                        "meta": None,
                    }
                }
            },
        }
    },
)
def get_vision_tarifas_modelo_cobro(
    simulation_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
    repo: ResultsRepository = Depends(get_results_repository),
):
    """
    Get Vision Tarifas Modelo de Cobro screen contract from persisted result.

    Returns the simplified public contract without runtime calculations.

    Args:
        simulation_id: UUID of the simulation

    Returns:
        ApiResponse with modelo_cobro screen contract

    Raises:
        HTTPException 404 if simulation not found
    """
    try:
        data = repo.get(simulation_id)
        payload = build_modelo_cobro_from_result(data)
        return ApiResponse.ok(payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)


@router.post(
    "/{simulation_id}/results/vision-tarifas/modelo-cobro/recalculate",
    summary="Previsualizar recálculo de Modelo de Cobro",
    description="Aplica overrides del usuario y retorna un preview sin persistir.",
    operation_id="recalculateVisionTarifasModeloCobro",
    response_model=ModeloCobroApiResponseV1,
)
def post_vision_tarifas_modelo_cobro_recalculate(
    simulation_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
    body: ModeloCobroRecalculateRequest = Body(...),
    repo: ResultsRepository = Depends(get_results_repository),
):
    """
    Stateless preview: apply user overrides and return recalculated modelo_cobro.

    Does NOT mutate the persisted result. Returns FULL_RECALCULATION_REQUIRED
    if the override cannot be handled at preview level.

    Args:
        simulation_id: UUID of the simulation
        body: Override request with view_id and overrides

    Returns:
        ApiResponse with updated modelo_cobro preview

    Raises:
        HTTPException 404 if simulation not found
    """
    try:
        data = repo.get(simulation_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message)

    try:
        payload = recalculate_preview(data, body.view_id, body.overrides.model_dump(exclude_none=True))
        return ApiResponse.ok(payload)
    except OverrideValidationError as exc:
        if "full calculator recalculation" in str(exc.message).lower():
            return JSONResponse(
                status_code=400,
                content=ApiResponse(
                    success=False,
                    error=_make_detail("SIM-00700", message=exc.message),
                ).model_dump(),
            )
        return JSONResponse(
            status_code=422,
            content=ApiResponse(
                success=False,
                error=_make_detail("SIM-00506", message="Invalid modelo_cobro override", details=exc.details if exc.details else None),
            ).model_dump(),
        )
