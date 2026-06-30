"""Typed public contract for the screen-ready Cost To Serve response."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from nexa_engine.modules.shared.responses import ApiResponse


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VisionCostToServeDataV1(StrictModel):
    version: str
    simulation_id: str | None = None
    header: dict[str, Any]
    summary_cards: list[dict[str, Any]]
    sections: list[dict[str, Any]]
    charts: dict[str, Any]
    metadata: dict[str, Any]


class VisionCostToServeApiResponseV1(ApiResponse[VisionCostToServeDataV1]):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "data": {
                        "version": "v1",
                        "simulation_id": "sim-123",
                        "header": {
                            "cliente": "Cliente Demo",
                            "servicio": "SAC",
                        },
                        "summary_cards": [],
                        "sections": [],
                        "charts": {},
                        "metadata": {
                            "source": "persisted_pricing_result",
                            "sources": [],
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
    "VisionCostToServeApiResponseV1",
    "VisionCostToServeDataV1",
]
