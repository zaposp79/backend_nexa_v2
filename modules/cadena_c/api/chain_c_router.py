"""Cadena C — HTTP transport layer.

URL activa: GET /simulation/input/chain-c/parametros
"""
from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from nexa_engine.db.dependencies import get_cadena_c_parameters_service
from nexa_engine.modules.cadena_c.dto.cadena_c_dto import ParametrosCadenaC
from nexa_engine.modules.cadena_c.services.parameters_query_service import (
    CadenaCParametersQueryService,
)
from nexa_engine.modules.shared.responses import ApiResponse

router = APIRouter(prefix="/simulation/input/chain-c", tags=["Simulations"])
PARAMETRIZATION_ERROR_RESPONSE = {
    500: {"description": "Parametrization error"},
}


@router.get(
    "/parametros",
    response_model=ParametrosCadenaC,
    responses=PARAMETRIZATION_ERROR_RESPONSE,
    summary="Obtener parámetros de Cadena C (IA)",
    operation_id="getChainCParametros",
)
def get_parametros(
    service: CadenaCParametersQueryService = Depends(get_cadena_c_parameters_service),
) -> ParametrosCadenaC | JSONResponse:
    try:
        return service.get_active_parameters()
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(
                ApiResponse.fail("PARAMETRIZATION_ERROR", str(exc))
            ),
        )
