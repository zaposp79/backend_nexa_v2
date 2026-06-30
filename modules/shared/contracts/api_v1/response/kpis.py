"""KPIs response DTO (api-v1).

Units: monetary values in COP (Colombian Pesos), percentages as 0..1.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class KpisV1(BaseModel):
    """Top-level KPIs for the simulated deal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    costo_mensual_promedio: float = 0.0           # COP/mes
    costo_cadena_a_promedio: float = 0.0          # COP/mes
    ingreso_mensual: float = 0.0                  # COP/mes
    facturacion_mensual_proyectada: float = 0.0   # COP/mes
    ingreso_bruto_total: float = 0.0              # COP
    ingreso_neto_total: float = 0.0               # COP
    costo_total_contrato: float = 0.0             # COP
    contribucion_total: float = 0.0               # COP
    utilidad_neta_total: float = 0.0              # COP
    pct_utilidad_neta_total: float = Field(default=0.0)  # 0..1
    valor_total_deal: float = 0.0                 # COP
    margen_minimo_requerido: float = Field(default=0.0)  # 0..1
    cumple_margen_minimo: bool = True
