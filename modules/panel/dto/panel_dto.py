"""Response DTOs for the Panel de Control General endpoint."""
from __future__ import annotations
from typing import List
from pydantic import BaseModel


class DatosOperativos(BaseModel):
    tarifa_diaria_capacitacion: float
    crucero: float
    horas_formacion_mes: float
    pct_ausentismo: float
    pct_rotacion: float
    tasa_ica: float
    tasa_gmf: float


class Poliza(BaseModel):
    nombre: str
    pct_atribuible: float


class MargenObjetivo(BaseModel):
    cadena_a: float
    cadena_b: float
    cadena_c: float


class Rango(BaseModel):
    minimo: float
    maximo: float


class ReglasNegocio(BaseModel):
    """Políticas comerciales activas con rangos min/max del deal.

    BUSINESS_RULES_FIX_3:
        descuento_volumen renombrado a descuento (alineado con politicas_comerciales
        en v2-7.json y con PanelDeControl.descuento). Ver FIX_1 para historial.
        porcentaje_acumulado eliminado: era DEAD_FIELD_LEGACY sin fuente Panel.
    """
    margen_objetivo: MargenObjetivo
    contingencia_operativa: Rango
    contingencia_comercial: Rango
    markup: Rango
    descuento: Rango


class Indexacion(BaseModel):
    tasa_interes_mensual: float


class Volumetria(BaseModel):
    indexacion: Indexacion


class ParametrosPanel(BaseModel):
    datos_operativos: DatosOperativos
    polizas: List[Poliza]
    reglas_negocio: ReglasNegocio
    volumetria: Volumetria
    ciudades: List[str]
    localidades: List[str]
    servicios: List[str]
    clientes: List[str]
    tipos_cliente: List[str]
    periodos_pago: List[str]


__all__ = [
    "DatosOperativos", "Poliza", "MargenObjetivo", "Rango",
    "ReglasNegocio", "Indexacion", "Volumetria", "ParametrosPanel",
]
