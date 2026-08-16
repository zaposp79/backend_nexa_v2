"""Vision Imprimible — HTTP endpoint.

GET /simulation/{simulation_id}/results/vision-imprimible
Returns the screen-ready contract for the canonical printable deal view.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse

from nexa_engine.db.dependencies import get_results_repository
from nexa_engine.modules.calculator.persistence.results_repository import ResultsRepository
from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.shared.responses import ApiResponse, ErrorDetail
from nexa_engine.modules.shared.error_catalog import make_detail as _make_detail
from nexa_engine.modules.vision_imprimible.api.public_mapper import build_public_vision_imprimible

router = APIRouter(prefix="/simulation", tags=["Vision Imprimible"])


def _not_found(simulation_id: str, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ApiResponse(
            success=False,
            error=_make_detail(getattr(exc, "sim_code", "SIM-00600"), message=exc.message),
        ).model_dump(),
    )


def _build_v2_response(simulation_id: str, doc: dict) -> ApiResponse:
    """Retorna la visión imprimible pre-construida de un resultado del motor v2."""
    vision_imprimible = doc.get("vision_imprimible")
    if not vision_imprimible:
        return ApiResponse.fail(
            "SIM-00604",
            message="Esta simulación no contiene Visión Imprimible. Recalcule con la versión actual del motor.",
        )
    return ApiResponse.ok(data={
        "version": "v2",
        "simulation_id": simulation_id,
        "header": {
            "cliente":            doc.get("cliente"),
            "servicio":           doc.get("servicio"),
            "tipo_cliente":       doc.get("tipo_cliente"),
            "antiguedad_cliente": doc.get("antiguedad_cliente"),
            "periodo_pago":       doc.get("periodo_pago"),
            "fecha_inicio":       doc.get("fecha_inicio"),
            "duracion_meses":     doc.get("duracion_meses"),
            "ciudad":             doc.get("ciudad"),
            "sede":               doc.get("sede"),
        },
        "calculated_at": doc.get("calculated_at"),
        "created_at":    doc.get("created_at"),
        "vision_imprimible": vision_imprimible,
    })


@router.get(
    "/{simulation_id}/results/vision-imprimible",
    response_model=ApiResponse,
    summary="Obtener visión imprimible del deal",
    description=(
        "Contrato screen-ready de la Visión Imprimible. "
        "Para simulaciones del motor v2 retorna las secciones pre-construidas; "
        "para v1 retorna el contrato screen-ready clásico."
    ),
    operation_id="getVisionImprimible",
)
def get_vision_imprimible(
    simulation_id: str = Path(..., pattern=r"^[a-zA-Z0-9_\-]{1,128}$"),
    repo: ResultsRepository = Depends(get_results_repository),
):
    try:
        data = repo.get(simulation_id)
    except NotFoundError as exc:
        return _not_found(simulation_id, exc)

    if data.get("version") == "v2":
        return _build_v2_response(simulation_id, data)

    return ApiResponse.ok(build_public_vision_imprimible(data))
