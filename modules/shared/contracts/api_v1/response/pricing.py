"""Pricing-related response DTOs (api-v1). Reserved for future pricing summary."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PricingLineV1(BaseModel):
    """One row of the headline pricing breakdown (per channel/modality)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    canal: str
    modalidad: str
    producto: Optional[str] = None
    modelo_cobro: str
    tarifa_fijo_fte: float = 0.0
    tarifa_variable: float = 0.0
    ingreso_bruto_mes: float = 0.0


class PricingV1(BaseModel):
    """Wire-level pricing summary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lineas: List[PricingLineV1] = Field(default_factory=list)
    ingreso_total_mes: float = 0.0
