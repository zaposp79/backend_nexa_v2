"""CadenaC request DTOs (frozen, strict)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class CanalCadenaCV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nombre: str = ""
    modalidad: str = ""
    volumen_mensual: float = Field(default=0.0, ge=0.0)
    activo: bool = True
    opex_fijo_integ: float = Field(default=0.0, ge=0.0)
    opex_var_integ: float = Field(default=0.0, ge=0.0)
    pct_escalamiento: float = Field(default=0.0, ge=0.0, le=1.0)
    costo_escalamiento: float = Field(default=0.0, ge=0.0)


class MiembroEquipoTransversalV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rol: str = ""
    activo: bool = True
    pct_dedicacion: float = Field(default=0.0, ge=0.0, le=1.0)


class CadenaCRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    canales: List[CanalCadenaCV1] = Field(default_factory=list)
    equipo_transversal: List[MiembroEquipoTransversalV1] = Field(default_factory=list)
    inversion_anual: float = Field(default=0.0, ge=0.0)
