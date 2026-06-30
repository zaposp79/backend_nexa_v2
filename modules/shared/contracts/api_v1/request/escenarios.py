"""Escenarios comerciales (frozen)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class EscenarioComercialV1(BaseModel):
    """
    Commercial scenario referencing a channel/modality.

    The wider engine accepts heterogeneous scenario shapes; this contract
    locks the canonical subset used by the V2-7 baseline cases.
    """

    model_config = ConfigDict(extra="allow", frozen=True)

    nombre: str = ""
    canal: str = ""
    modalidad: str = ""
    modelo_cobro: Optional[str] = None
    margen: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    parametros: Dict[str, Any] = Field(default_factory=dict)
