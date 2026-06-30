"""Cadena A — parametrization read model contracts.

Propietario: modules/cadena_a — este módulo es dueño de sus DTOs.
"""
from __future__ import annotations
from typing import List
from pydantic import BaseModel


class Ratio(BaseModel):
    cargo: str
    servicio: str
    agentes: float
    tipo: str


class OpexFijoItem(BaseModel):
    item: str
    valor: float


class HardSoftItem(BaseModel):
    item: str
    valor: float
    cantidad_meses: float
    tipo: str


class ParametrosCadenaA(BaseModel):
    ratios: List[Ratio]
    opex_fijo: List[OpexFijoItem]
    hardware_software: List[HardSoftItem]
    modalidades: List[str]
    canales: List[str]


__all__ = ["Ratio", "OpexFijoItem", "HardSoftItem", "ParametrosCadenaA"]
