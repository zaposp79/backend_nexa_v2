"""Cadena A — HTTP transport layer.

URL activa: GET /simulation/input/chain-a/parametros
"""
from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from nexa_engine.db.dependencies import get_cadena_a_parameters_service
from nexa_engine.modules.cadena_a.dto.cadena_a_dto import ParametrosCadenaA
from nexa_engine.modules.cadena_a.services.parameters_query_service import (
    CadenaAParametersQueryService,
)
from nexa_engine.modules.shared.responses import ApiResponse

router = APIRouter(prefix="/simulation/input/chain-a", tags=["Simulations"])
PARAMETRIZATION_ERROR_RESPONSE = {
    500: {"description": "Parametrization error"},
}


@router.get(
    "/parametros",
    response_model=ParametrosCadenaA,
    responses=PARAMETRIZATION_ERROR_RESPONSE,
    summary="Obtener parámetros de Cadena A (Backoffice)",
    operation_id="getChainAParametros",
)
def get_parametros(
    service: CadenaAParametersQueryService = Depends(get_cadena_a_parameters_service),
) -> ParametrosCadenaA | JSONResponse:
    try:
        return service.get_active_parameters()
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(
                ApiResponse.fail("PARAMETRIZATION_ERROR", str(exc))
            ),
        )
