"""Cadena B — HTTP transport layer.

URL activa: GET /simulation/input/chain-b/parametros
"""
from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from nexa_engine.db.dependencies import get_cadena_b_parameters_service
from nexa_engine.modules.cadena_b.dto.cadena_b_dto import ParametrosCadenaB
from nexa_engine.modules.cadena_b.services.parameters_query_service import (
    CadenaBParametersQueryService,
)
from nexa_engine.modules.shared.responses import ApiResponse

router = APIRouter(prefix="/simulation/input/chain-b", tags=["Simulations"])
PARAMETRIZATION_ERROR_RESPONSE = {
    500: {"description": "Parametrization error"},
}


@router.get(
    "/parametros",
    response_model=ParametrosCadenaB,
    responses=PARAMETRIZATION_ERROR_RESPONSE,
    summary="Obtener parámetros de Cadena B (Digital)",
    operation_id="getChainBParametros",
)
def get_parametros(
    service: CadenaBParametersQueryService = Depends(get_cadena_b_parameters_service),
) -> ParametrosCadenaB | JSONResponse:
    try:
        return service.get_active_parameters()
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(
                ApiResponse.fail("SIM-00701", message=str(exc))
            ),
        )
