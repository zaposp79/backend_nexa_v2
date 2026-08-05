from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RubroVariable(BaseModel):
    nombre: str
    tipo: str  # input | parametro | computed | context
    fuente: Optional[str] = None
    rubro_fuente: Optional[str] = None
    valor_referencia: Optional[Any] = None
    path_clave: Optional[str] = None
    filtro: Optional[str] = None


class RubroFormula(BaseModel):
    expresion: str
    notas: Optional[str] = None
    subformulas: Optional[Dict[str, str]] = None


class RubroMaestro(BaseModel):
    id: str
    version: str = "v2.8"
    nombre: str
    bloque: str
    capa: int
    descripcion: Optional[str] = None
    orden_calculo: int
    aplica_por_mes: bool = True
    tipo_calculo: str  # formula | aggregated | template
    formula: RubroFormula
    variables: List[RubroVariable] = []
    dependencias: List[str] = []
    cadena: Optional[str] = None


class ResultadoMes(BaseModel):
    mes: int
    valores: Dict[str, float]


class PerfilCTS(BaseModel):
    """Desglose de Cost-to-Serve para un perfil de Cadena A.

    Excel V2-8: 'Visión Cost To Serve' — Estructura del Equipo (filas 122-178)
    """
    nombre: str
    canal: str
    modalidad: str
    fte: int
    # Payroll
    salario_cargado: float
    crucero: float
    payroll: float
    # No Payroll
    opex_it: float
    inversiones: float
    costos_fijos: float
    no_payroll: float
    # Costo Directo
    costo_directo: float
    costo_directo_por_fte: float
    # Financiero (asignado pro-rata a costo_directo)
    financiero: float
    # Totales
    costo_total: float
    costo_total_por_fte: float
    ingreso: float      # costo_total / (1 - margen) — fórmula Excel CTS I160
    tarifa_fte: float   # ingreso / fte


class VisionCostToServe(BaseModel):
    """Visión Cost-to-Serve del deal.

    Excel V2-8: 'Visión Cost To Serve'
    Economics KPIs + desglose por Cadena A + desglose por perfil.
    """
    # Economics (filas 18-20 del Excel CTS)
    cts_mensual: float          # CTS total a 100% ramp (payroll + no_payroll + financiero)
    ingreso_mensual: float      # Ingreso billing a 100% ramp (fórmula HM)
    margen: float               # Margen objetivo Cadena A
    valor_total_contrato: float # Suma de ingreso_bruto de todos los meses del deal
    n_fte_total: int

    # Totales Cadena A (filas 35-48 del Excel CTS)
    payroll_total: float
    no_payroll_total: float
    costo_directo_total: float
    financiero_total: float
    cts_total: float

    # Por FTE/mes Cadena A
    payroll_por_fte: float
    no_payroll_por_fte: float
    costo_directo_por_fte: float
    financiero_por_fte: float
    cts_por_fte: float

    # Desglose por perfil (filas 122-178 del Excel CTS)
    perfiles: List[PerfilCTS] = Field(default_factory=list)


class VisionPyG(BaseModel):
    ingreso_bruto: List[float]
    ingreso_neto: List[float]
    costo_total: List[float]
    contribucion: List[float]
    pct_contribucion: List[float]
    utilidad_neta: List[float]
    pct_utilidad_neta: List[float]
    nomina_total_mensual: List[float]
    no_payroll_total_mensual: List[float]
    componente_financiero_total: List[float]


class SimulationResultV2(BaseModel):
    simulation_id: str
    version: str = "v2"
    cliente: Optional[str] = None
    servicio: Optional[str] = None
    duracion_meses: int
    meses: List[ResultadoMes]
    totales: Dict[str, float]
    vision_pyg: VisionPyG
    vision_cts: Optional[VisionCostToServe] = None
