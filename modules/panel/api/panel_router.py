"""Panel de Control General — HTTP transport layer."""

import logging
from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from nexa_engine.db.dependencies import get_panel_service
from nexa_engine.modules.shared.responses import ApiResponse
from nexa_engine.modules.panel.dto.panel_dto import ParametrosPanel
from nexa_engine.modules.panel.services.panel_service import PanelService

router = APIRouter(prefix="/simulation/input/panel", tags=["Simulations"])
logger = logging.getLogger("nexa.panel")
PARAMETRIZATION_ERROR_RESPONSE = {
    500: {"description": "Parametrization error"},
}


@router.get(
    "/parametros",
    response_model=ParametrosPanel,
    responses=PARAMETRIZATION_ERROR_RESPONSE,
    summary="Obtener parámetros del Panel de Control General",
    operation_id="getPanelParametros",
)
def get_parametros(
    panel_service: PanelService = Depends(get_panel_service),
) -> ParametrosPanel | JSONResponse:
    try:
        return panel_service.build_parametros()
    except Exception as exc:
        logger.exception("Error building panel parametros", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(
                ApiResponse.fail("SIM-00701", message=str(exc))
            ),
        )
