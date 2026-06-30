"""CadenaA request DTOs (frozen, strict)."""
from __future__ import annotations

from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


ModeloCobroLiteral = Literal[
    "Fijo FTE",
    "Variable",
    "Híbrido",
    "Hibrido",         # tolerate ASCII variant
    "Volumen",         # baseline shorthand for "Por Volumen"
    "Por Volumen",
    "Por Comisión",
    "Por Comision",
]


class CargoAdicionalV1(BaseModel):
    """Detalle del recurso humano adicional de un escenario de Cadena A."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cargo: str
    salario_base: float = Field(ge=0.0)
    ratio: float = Field(ge=0.0)


class DetalleRecursoHumanoV1(BaseModel):
    """Salario y comisión editables usados por los cálculos de Cadena A."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cargo: str
    salario_base: float = Field(ge=0.0)
    comisiones: float = Field(default=0.0, ge=0.0)


class PerfilCadenaAV1(BaseModel):
    """One operator profile (frozen)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    nombre: str = ""
    rol: str = "Agente Basico"
    canal: str = ""
    modalidad: str = "Inbound"
    fte: float = Field(default=0.0, ge=0.0)
    # EXCEL V2-8: 'Condiciones Cadena A'!E26/F26/G26 ("FTEs cargos adicionales" por escenario = 12/0/7.384615).
    # El objeto conserva el detalle visible en la interfaz; `ratio` mantiene el valor FTE usado por la formula.
    # Aditivo al numerador del FTE de soporte: (fte + cargos_adicionales)/ratio (fórmula F95/G95).
    # Default 0.0 preserva comportamiento legacy. NO se suma al payroll de agentes (evita doble conteo).
    cargos_adicionales: Union[
        Annotated[float, Field(ge=0.0)],
        CargoAdicionalV1,
        List[CargoAdicionalV1],
    ] = 0.0
    # EXCEL V2-8: 'Condiciones Cadena A'!E95 = 9.5 (override manual literal, Supervisor SAC).
    # Override opt-in del FTE de un rol de soporte por escenario: reemplaza el FTE derivado
    # (fte + cargos_adicionales)/ratio por el valor literal del Excel cuando éste fue tecleado a mano
    # (no derivado de la fórmula). Keyed por nombre de rol (normalizado internamente). Default vacío
    # = comportamiento legacy exacto. Solo afecta el FTE del rol indicado de este perfil/escenario.
    fte_soporte_overrides: Dict[str, float] = Field(default_factory=dict)
    pct_presencia: float = Field(default=1.0, ge=0.0, le=1.0)
    comision_pct: float = Field(default=0.0, ge=0.0, le=1.0)
    salario_base: Optional[float] = Field(default=None, ge=0.0)
    incluye_examenes: bool = True
    incluye_seguridad: bool = False
    incluye_crucero: bool = False
    no_payroll_mensual: float = Field(default=0.0, ge=0.0)
    dias_cap_inicial: int = Field(default=10, ge=0, le=365)
    dias_cap_rotacion: int = Field(default=10, ge=0, le=365)
    tmo_segundos: float = Field(default=0.0, ge=0.0)
    modelo_cobro: ModeloCobroLiteral = "Fijo FTE"
    pct_fijo: float = Field(default=1.0, ge=0.0, le=1.0)
    vol_cadena_a_mensual: float = Field(default=0.0, ge=0.0)


class CadenaARequestV1(BaseModel):
    """Cadena A configuration (frozen)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    detalles_recursos_humanos: List[DetalleRecursoHumanoV1] = Field(default_factory=list)
    perfiles: List[PerfilCadenaAV1] = Field(default_factory=list)
