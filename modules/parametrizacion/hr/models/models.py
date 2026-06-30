"""HR domain models (dataclasses)."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class NivelesLV:
    """Unique value catalogs extracted from HR-LV sheet.

    Each key is a column name (normalized); value is a list of {name: ...} dicts
    with the distinct non-empty values found in that column.
    Dynamic: any column present in the sheet is captured.
    """
    catalogs: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)


@dataclass
class SalarioBasico:
    """Row from HR-SalarioBasico sheet. Reference salary values."""
    servicio: str
    valor: float


@dataclass
class NominaConfig:
    """Row from HR-Nomina sheet. Salaries by tipo and rol."""
    tipo: str
    rol: str
    salario: float


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
    """Row from HR-Ratios sheet. Agent ratios per cargo/service.

    Maps from Excel columns:
    - Cargo → cargo
    - CategoriaServicio → servicio (or categoria_servicio if distinct)
    - Tipo → tipo
    - Agentes → agentes
    """
    cargo: str
    servicio: str
    agentes: float
    tipo: str = ""  # Tipo from Excel (e.g. "Administrativo", "Operacional")
    categoria_servicio: str = ""  # Explicit category from Excel


@dataclass
class RentabilidadConfig:
    """Row from HR-Rentabilidad sheet.

    minimo / margenobjetivo are stored as decimal fractions (e.g. 0.17 = 17%).
    The upload normalizer converts ``"17.00%"`` → ``0.17`` via the
    ``percentage_decimal`` column type.  The downstream repository no longer
    divides by 100 — it uses the value directly.
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
    localidad: str
    servicio: str
    valor: float


@dataclass
class MedSegConfig:
    """Row from HR-Med-Seg sheet."""
    localidad: str
    centrocosto: str
    valor: float


@dataclass
class HRMasterData:
    """Full HR master data for one uploaded version.

    Stores both standard HR sheets (mapped to typed fields) and any additional
    sheets found in the Excel file (stored as raw data in extra_sheets).
    This allows the system to accept new sheets without code changes.
    """
    version_id: str
    niveles: NivelesLV = field(default_factory=NivelesLV)
    salarios: List[SalarioBasico] = field(default_factory=list)
    nomina: List[NominaConfig] = field(default_factory=list)
    recargos: List[RecargosConfig] = field(default_factory=list)
    seg_social: List[SegSocialConfig] = field(default_factory=list)
    prestaciones: List[PrestacionesConfig] = field(default_factory=list)
    ratios: List[RatiosConfig] = field(default_factory=list)
    rentabilidad: List[RentabilidadConfig] = field(default_factory=list)
    campana: List[CampanaConfig] = field(default_factory=list)
    costo_fijo: List[CostoFijoConfig] = field(default_factory=list)
    med_seg: List[MedSegConfig] = field(default_factory=list)
    extra_sheets: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
