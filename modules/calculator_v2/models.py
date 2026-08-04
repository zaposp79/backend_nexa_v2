from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


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
