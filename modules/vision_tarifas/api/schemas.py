"""Pydantic schemas for the modelo_cobro screen contract (GET + POST)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from nexa_engine.modules.shared.responses import ApiResponse


# ---------------------------------------------------------------------------
# POST request — recalculation overrides
# ---------------------------------------------------------------------------


class ModeloCobroOverride(BaseModel):
    modelo_cobro: Optional[str] = Field(None, pattern=r"^(Híbrido|Fijo|Variable|0|null)?$")
    componente_fijo: Optional[str] = Field(None, pattern=r"^(FTE|Tiempo|Precio Fijo|0|null)?$")
    proporcion_componente_fijo: Optional[float] = Field(None, ge=0, le=1)
    componente_variable: Optional[str] = Field(None, pattern=r"^(Transacción|Resultados|Honorarios|0|null)?$")
    proporcion_componente_variable: Optional[float] = Field(None, ge=0, le=1)


class ModeloCobroRecalculateRequest(BaseModel):
    view_id: str = Field(..., pattern=r"^(escenario_[1-5]|total)$")
    overrides: ModeloCobroOverride

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "view_id": "total",
                    "overrides": {
                        "modelo_cobro": "Fijo",
                        "componente_fijo": "FTE",
                        "proporcion_componente_fijo": 1,
                        "componente_variable": "Transacción",
                        "proporcion_componente_variable": 0,
                    },
                }
            ]
        }
    )


# ---------------------------------------------------------------------------
# Response data shapes (documentation only — actual response uses ApiResponse)
# ---------------------------------------------------------------------------


class CadenaChain(BaseModel):
    total: float = 0
    ica: float = 0
    gmf: float = 0
    comision_por_administracion: float = 0
    polizas: float = 0
    costos_financiacion: float = 0
    ingreso_mensual: float = 0


class CadenaA(CadenaChain):
    payroll: float = 0
    no_payroll: float = 0


class CadenaBC(CadenaChain):
    componente_fijo: float = 0
    componente_variable: float = 0


class Totales(BaseModel):
    costo_total_mensual: float = 0
    facturacion_total_mensual: float = 0


class ReglasNegocio(BaseModel):
    total_regla_negocio: float = 0
    descuento_cliente: float = 0
    contingencia_operativa: float = 0
    contingencia_comercial: float = 0
    margen_cadena_a: float = 0
    margen_cadena_b: float = 0
    margen_cadena_c: float = 0
    markup: float = 0


class TarifaComponenteFijo(BaseModel):
    ingreso_componente_fijo: float = 0
    tarifa_principal_label: str = "Tarifa por FTE"
    tarifa_principal: float = 0
    tarifa_secundaria_label: str = "Tarifa por minuto pagado"
    tarifa_secundaria: float = 0
    tarifa_por_fte: float = 0
    tarifa_por_minuto_logrado: float = 0
    tarifa_por_minuto_pagado: float = 0


class TarifaComponenteVariable(BaseModel):
    titulo: str = "Tarifa Componente Variable"
    ingreso_componente_variable: float = 0
    tarifa_principal_label: str = "Tarifa por Transacción"
    tarifa_principal: float = 0
    volumen_label: str = "Volumen Mínimo de Transacción"
    volumen: float = 0
    volumetria_label: str = "Volumetría de 1 FTE"
    volumetria_de_1_fte: float = 0
    tarifa_por_transaccion: float = 0
    comisiones_mi: float = 0
    ingreso_por_persona: float = 0


class ModeloCobroDetail(BaseModel):
    escenario: Optional[str] = None
    modalidad: Optional[str] = None
    canal: Optional[str] = None
    modelo_cobro: Optional[str] = None
    componente_fijo: Any = 0
    proporcion_componente_fijo_pct: float = 0
    componente_variable: Optional[str] = None
    proporcion_componente_variable_pct: float = 0
    fte: float = 0
    cadena_a: dict[str, float] = {}
    cadena_b: dict[str, float] = {}
    cadena_c: dict[str, float] = {}
    totales: Totales = Totales()
    reglas_negocio: ReglasNegocio = ReglasNegocio()
    tarifa_componente_fijo: TarifaComponenteFijo = TarifaComponenteFijo()
    tarifa_componente_variable: TarifaComponenteVariable = TarifaComponenteVariable()
    honorarios_cobranza: list[HonorarioCobranzaRow] = Field(default_factory=list)
    honorarios_totales: list[HonorarioTotalesRow] = Field(default_factory=list)
    ventas_multicanal: list[VentasMulticanalRow] = Field(default_factory=list)


class ResumenRow(BaseModel):
    escenario: str
    modalidad: Optional[str] = None
    canal: Optional[str] = None
    modelo_cobro: Optional[str] = None
    componente_fijo: Any = 0
    proporcion_componente_fijo_pct: float = 0
    componente_variable: Optional[str] = None
    proporcion_componente_variable_pct: float = 0
    facturacion_directa: float = 0
    tarifa_componente_fijo: float = 0
    tarifa_componente_variable: float = 0


class DesgloseProductoOpexRow(BaseModel):
    producto: str = ""
    costo_directo: Optional[float] = 0
    costo_financiacion: Optional[float] = 0
    polizas: Optional[float] = 0
    ingreso_por_producto: Optional[float] = 0


class HonorarioCobranzaRow(BaseModel):
    antiguedadCartera: Optional[str] = None
    driver_dificultad: Optional[float] = None
    calculado: Optional[float] = None
    benchmark: Optional[float] = None
    
class HonorarioTotalMesRow(BaseModel):
    mes: Optional[int] = None
    benchmark: Optional[float] = None
    calculado: Optional[float] = None
    
class VentaMulticanalMesRow(BaseModel):
    mes: Optional[int] = None
    valor: Optional[float] = None


class HonorarioTotalesRow(BaseModel):
    concepto: Optional[str] = None
    meses: list[HonorarioTotalMesRow] = Field(default_factory=list)
    
class VentasMulticanalRow(BaseModel):
    concepto: Optional[str] = None
    formato: Optional[str] = None
    tipo: Optional[str] = None
    meses: list[VentaMulticanalMesRow] = Field(default_factory=list)


class ModeloCobroPublicData(BaseModel):
    simulation_id: Optional[str] = None
    header: Optional[dict] = None
    cliente: Optional[str] = None
    servicio: Optional[str] = None
    ciudad: Optional[str] = None
    selected_view_id: Optional[str] = None
    resumen_resultado_escenario: list[ResumenRow] = Field(default_factory=list)
    modelo_cobro: list[ModeloCobroDetail] = Field(default_factory=list)
    desglose_producto_opex: list[DesgloseProductoOpexRow] = Field(default_factory=list)


class ModeloCobroApiResponseV1(ApiResponse[ModeloCobroPublicData]):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "data": {
                        "cliente": "Banco de Bogotá",
                        "servicio": "Atención al cliente",
                        "ciudad": "Bogotá",
                        "selected_view_id": "escenario_1",
                        "resumen_resultado_escenario": [],
                        "modelo_cobro": [],
                        "desglose_producto_opex": [],
                    },
                    "error": None,
                    "meta": None,
                }
            ]
        }
    )
