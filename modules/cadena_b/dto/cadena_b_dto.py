"""Cadena B — parametrization read model contracts.

Propietario: modules/cadena_b — este módulo es dueño de sus DTOs.
Contrato independiente de Cadena C (aunque inicialmente con los mismos campos).
"""
from __future__ import annotations
from typing import List
from pydantic import BaseModel


class DispositivoRequerido(BaseModel):
    nombre: str


class EquipoHITL(BaseModel):
    nombre: str
    ratio: float | None


class ParametrosCadenaB(BaseModel):
    dispositivos_requeridos: List[DispositivoRequerido]
    equipo_hitl: List[EquipoHITL]


__all__ = ["DispositivoRequerido", "EquipoHITL", "ParametrosCadenaB"]
