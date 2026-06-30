"""CadenaB request DTOs (frozen, strict)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class CanalCadenaBV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nombre: str = ""
    modalidad: str = ""
    producto: str = ""
    volumen_mensual: float = Field(default=0.0, ge=0.0)
    activo: bool = True
    opex_fijo: float = Field(default=0.0, ge=0.0)
    tarifa_unitaria: float = Field(default=0.0, ge=0.0)
    pct_escalamiento: float = Field(default=0.0, ge=0.0, le=1.0)
    costo_escalamiento: float = Field(default=0.0, ge=0.0)


class ItemOpexConsumoV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nombre: str = ""
    producto: str = ""
    modalidad: str = ""
    canal: str = ""
    valor_unitario: float = Field(default=0.0, ge=0.0)
    cantidad: float = Field(default=0.0, ge=0.0)
    tipo_cobro: str = "Unitario"


class MiembroEquipoSMV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rol: str = ""
    activo: bool = True
    pct_dedicacion: float = Field(default=0.0, ge=0.0, le=1.0)


class DispositivoSMV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tipo: str = ""
    costo_unitario: float = Field(default=0.0, ge=0.0)
    cantidad: float = Field(default=0.0, ge=0.0)
    meses_amortizacion: int = Field(default=1, ge=1, le=360)


class CadenaBRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    canales: List[CanalCadenaBV1] = Field(default_factory=list)
    opex_consumo_variable: List[ItemOpexConsumoV1] = Field(default_factory=list)
    equipo_sm: List[MiembroEquipoSMV1] = Field(default_factory=list)
    dispositivos_sm: List[DispositivoSMV1] = Field(default_factory=list)
    inversion_plataforma: float = Field(default=0.0, ge=0.0)
    fte_equipo_sm: float = Field(default=1.0, ge=0.0)
    amortizar_dispositivos_sm: bool = True
