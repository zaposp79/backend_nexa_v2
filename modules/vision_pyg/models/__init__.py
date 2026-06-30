"""P&G vision models."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class VisionPyGRow:
    """
    Una fila del estado de resultados P&G.

    key/label/seccion/tipo/signo definen la semántica de la fila;
    valores es el array mensual; acumulado/promedio son derivados.
    """
    key: str
    label: str
    seccion: str
    tipo: str
    signo: str
    valores: list[float] = field(default_factory=list)
    acumulado: float = 0.0
    promedio: float = 0.0
    excel_row: int | None = None
    formula: str | None = None


@dataclass(slots=True)
class VisionPyGRowDetalle:
    """Sub-componente que descompone una fila summary del P&G."""
    key: str
    label: str
    parent: str
    seccion: str
    tipo: str
    signo: str
    valores: list[float] = field(default_factory=list)
    acumulado: float = 0.0
    promedio: float = 0.0
    excel_row: int | None = None
    formula: str | None = None


@dataclass(slots=True)
class ResumenEjecutivoPyG:
    meses_contrato: int = 0
    meses_activos: int = 0
    valor_total_deal: float = 0.0
    ingreso_neto_total: float = 0.0
    costo_total_contrato: float = 0.0
    contribucion_total: float = 0.0
    pct_utilidad_promedio: float = 0.0
    cumple_margen_minimo: bool = True
    cliente: str = ""
    tipo_cliente: str = ""
    antiguedad_cliente: str = ""
    linea_negocio: str = ""
    ciudad: str = ""
    sede: str = ""
    fecha_inicio: str = ""
    fecha_fin: str = ""
    duracion_contrato: str = ""
    periodo_pago_dias: int = 0
    divisa: str = "COP"


@dataclass(slots=True)
class VisionPyG:
    resumen: ResumenEjecutivoPyG = field(default_factory=ResumenEjecutivoPyG)
    filas: list[VisionPyGRow] = field(default_factory=list)
    meses_contrato: int = 0
    meses_activos: int = 0
    filas_detalle: list[VisionPyGRowDetalle] = field(default_factory=list)
    puestos_trabajo: float = 0.0
    fechas_meses: list[str] = field(default_factory=list)


__all__ = [
    "VisionPyGRow",
    "VisionPyGRowDetalle",
    "ResumenEjecutivoPyG",
    "VisionPyG",
]
