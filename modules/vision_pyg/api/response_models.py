"""Typed public contract for the screen-ready Vision P&G response."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from nexa_engine.modules.shared.responses import ApiResponse


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VisionPygDataV1(StrictModel):
    version: str
    simulation_id: str | None = None
    header: dict[str, Any]
    periods: list[dict[str, Any]]
    totales: dict[str, Any]
    metadata: dict[str, Any]


class VisionPygApiResponseV1(ApiResponse[VisionPygDataV1]):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "data": {
                        "version": "v1",
                        "simulation_id": "sim-123",
                        "header": {
                            "cliente": "Banco de Bogotá",
                            "servicio": "Atención al cliente",
                        },
                        "periods": [],
                        "totales": {},
                        "metadata": {
                            "source": "persisted_pricing_result",
                            "omitted_empty_fields": True,
                        },
                    },
                    "error": None,
                    "meta": None,
                }
            ]
        }
    )


__all__ = [
    "VisionPygApiResponseV1",
    "VisionPygDataV1",
]
