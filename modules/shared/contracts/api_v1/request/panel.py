"""
PanelDeControlRequestV1 — frozen panel input.

Mirrors ``simulation.request_dto.PanelDeControlRequest`` but with strict
typing, value-range validators, and immutability. The legacy ``aplica_ley_1819``
flag is preserved for backward compatibility (ignored downstream).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PanelDeControlRequestV1(BaseModel):
    """Panel de Control (frozen, strict)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cliente: str = ""
    tipo_cliente: str = ""
    linea_negocio: str = ""
    ciudad: str = ""
    sede: str = ""
    fecha_inicio: str = ""
    meses_contrato: int = Field(default=12, ge=1, le=120)
    margen: float = Field(default=0.0, ge=-1.0, le=1.0)
    op_cont: float = Field(default=0.0, ge=0.0, le=1.0)
    com_cont: float = Field(default=0.0, ge=0.0, le=1.0)
    markup: float = Field(default=0.0, ge=-1.0, le=10.0)
    descuento: float = Field(default=0.0, ge=0.0, le=1.0)
    periodo_pago_dias: int = Field(default=90, ge=0, le=365)
    activa_financiacion: bool = True
    antiguedad_cliente: str = ""
    componente_indexacion_humano: str = "IPC"
    componente_indexacion_tecnologico: str = "IPC"
    tasa_ica: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tasa_gmf: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tasa_mensual_financ: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    pct_rotacion: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    pct_ausentismo: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    aplica_ley_1819: bool = True  # legacy; retained for back-compat, ignored

    # ── V2-7 Excel formal fields (Panel) ───────────────────────────────────
    margen_b: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    margen_c: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    mes_ajuste_indexacion: Optional[int] = Field(default=None, ge=1, le=12)
    tasa_interes_mensual: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    imprevistos: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @field_validator("meses_contrato")
    @classmethod
    def _validate_meses(cls, v: int) -> int:
        if not (1 <= int(v) <= 120):
            raise ValueError("meses_contrato must be between 1 and 120")
        return int(v)
