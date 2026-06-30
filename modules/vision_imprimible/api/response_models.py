"""Typed public contract for the screen-ready vision_imprimible response."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from nexa_engine.modules.shared.responses import ApiResponse


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VisionImprimibleDataV1(StrictModel):
    version: str
    simulation_id: str | None = None
    header: dict[str, Any]
    summary_cards: list[dict[str, Any]]
    sections: list[dict[str, Any]]
    charts: dict[str, Any]
    metadata: dict[str, Any]


class VisionImprimibleApiResponseV1(ApiResponse[VisionImprimibleDataV1]):
    """Success envelope for the screen-ready vision_imprimible contract."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "data": {
                        "version": "v1",
                        "simulation_id": "sim-123",
                        "header": {
                            "cliente": "Cliente A",
                            "servicio": "SAC",
                        },
                        "summary_cards": [
                            {"key": "ingreso_mensual", "label": "Ingreso mensual", "value": 100000000.0},
                        ],
                        "sections": [
                            {
                                "id": "ficha_deal",
                                "title": "Ficha del deal",
                                "type": "summary_grid",
                                "items": [
                                    {"key": "cliente", "label": "Cliente", "value": "Cliente A"},
                                ],
                            }
                        ],
                        "charts": {
                            "waterfall": {
                                "id": "waterfall",
                                "title": "Waterfall",
                                "type": "waterfall",
                                "source": "vision_imprimible.waterfall_promedio",
                                "data": [],
                            }
                        },
                        "metadata": {
                            "source": "persisted_pricing_result",
                            "missing_fields": [],
                        },
                    },
                    "error": None,
                    "meta": None,
                }
            ]
        }
    )


__all__ = [
    "VisionImprimibleApiResponseV1",
    "VisionImprimibleDataV1",
]
