"""HR domain models (dataclasses)."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class NivelesLV:
    """Unique value catalogs extracted from HR-LV sheet.

    Columns: TipoRecurso, Cargo, Prestaciones, SS&Parafiscales, Recargo.
    Keys are normalized API names (tiporecurso, cargo, prestaciones, ssparafiscales, recargo).
    Each value is a list of {name: ...} dicts with distinct non-empty values.
    """
    catalogs: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)


@dataclass
class SalarioBasico:
    """Row from HR-SalarioBasico sheet. Reference salary values."""
    servicio: str
    valor: float


@dataclass
class NominaConfig:
    """Row from HR-Nomina sheet. Salaries by cargo."""
    cargo: str
    salario: float
    comision: float = 0.0
    tiporecurso: str = ""
    cadena: str = ""


@dataclass
class RecargosConfig:
    """Row from HR-Recargos sheet."""
    recargo: str
    valor: float


@dataclass
class SegSocialConfig:
    """Row from HR-SegSocial sheet."""
    ssparafiscales: str
    proporcion: float


@dataclass
class PrestacionesConfig:
    """Row from HR-Prestaciones sheet."""
    prestaciones: str
    valor: float


@dataclass
class RatiosConfig:
    """Row from HR-Ratios sheet. Agent ratios per cargo, service category and type."""
    cargo: str
    agentes: float
    categoria_servicio: str = ""
    tipo: str = ""


@dataclass
class RentabilidadConfig:
    """Row from HR-Rentabilidad sheet.

    minimo / margenobjetivo stored as decimal fractions (e.g. 0.17 = 17%).
    """
    categoriaservicio: str
    minimo: float
    margenobjetivo: float


@dataclass
class CampanaConfig:
    """Row from HR-Campana sheet."""
    categoriaservicio: str
    mes: int
    valor: float


@dataclass
class CostoFijoConfig:
    """Row from HR-CostoFijo sheet."""
    ciudad: str
    localidad: str
    servicio_publico: str
    valor: float


@dataclass
class MedSegConfig:
    """Row from HR-Med-Seg sheet."""
    ciudad: str
    centrocosto: str
    valor: float


@dataclass
class ComplejidadConfig:
    """Row from HR-Complejidad sheet."""
    complejidad: str
    valor: float


@dataclass
class RatiosHITLConfig:
    """Row from HR-Ratios-HITL sheet."""
    cargo: str
    ratio: float


@dataclass
class HoraGTRConfig:
    """Row from HR-Hora-GTR sheet."""
    cargo: str
    hora: float


@dataclass
class HRMasterData:
    """Full HR master data for one uploaded version."""
    lv: NivelesLV = field(default_factory=NivelesLV)
    salariobasico: List[SalarioBasico] = field(default_factory=list)
    nomina: List[NominaConfig] = field(default_factory=list)
    complejidad: List[ComplejidadConfig] = field(default_factory=list)
    recargos: List[RecargosConfig] = field(default_factory=list)
    seg_social: List[SegSocialConfig] = field(default_factory=list)
    prestaciones: List[PrestacionesConfig] = field(default_factory=list)
    ratios: List[RatiosConfig] = field(default_factory=list)
    rentabilidad: List[RentabilidadConfig] = field(default_factory=list)
    campana: List[CampanaConfig] = field(default_factory=list)
    costo_fijo: List[CostoFijoConfig] = field(default_factory=list)
    med_seg: List[MedSegConfig] = field(default_factory=list)
    ratios_hitl: List[RatiosHITLConfig] = field(default_factory=list)
    hora_gtr: List[HoraGTRConfig] = field(default_factory=list)
    extra_sheets: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
