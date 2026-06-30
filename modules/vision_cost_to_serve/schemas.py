"""Pydantic schemas for Cost To Serve vision.

Response DTOs for the /simulation/{id}/results/cost-to-serve endpoint.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CostToServeResponse(BaseModel):
    """Cost To Serve response payload.

    Validates the shape of vision_cost_to_serve data returned to frontend.
    All fields are optional to support backward compatibility with
    partial or legacy results.
    """

    model_config = ConfigDict(extra="allow")

    cost_to_serve: dict | None = None
    vision_por_servicio: list = []
    vision_por_canal: list = []
    detalle_por_canal: list = []
    estructura_equipo: dict | None = None
    charts: dict | None = None
