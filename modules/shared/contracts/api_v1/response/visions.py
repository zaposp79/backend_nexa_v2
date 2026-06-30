"""Visions bundle (api-v1).

All monetary fields in COP, percentages 0..1, FTE in headcount-equivalent
units, ``vol`` in transactions/month.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Vision: Cost To Serve
# ---------------------------------------------------------------------------


class CostToServeDesgloseAV1(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    # Aggregates
    nomina: float = 0.0
    no_payroll: float = 0.0
    total: float = 0.0
    # Payroll sub-components (Excel VCS C036-C043)
    nomina_loaded: float = 0.0
    salario_fijo: float = 0.0
    salario_variable: float = 0.0
    capacitacion_inicial: float = 0.0
    capacitacion_rotacion: float = 0.0
    examenes: float = 0.0
    estudios_seguridad: float = 0.0
    crucero: float = 0.0  # GAP-CTS-HIER-1: non-zero for cruiser-service deals
    # No-payroll sub-components (Excel VCS C046-C048)
    opex_fijo: float = 0.0
    inversiones: float = 0.0
    costos_fijos_estacion: float = 0.0


class CostToServeDesgloseBV1(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    # Aggregates
    componente_fijo: float = 0.0
    componente_variable: float = 0.0
    total: float = 0.0
    # Componente Fijo sub-components (Excel VCS G035-G038)
    opex: float = 0.0
    inversiones: float = 0.0
    soporte_mantenimiento: float = 0.0
    # Componente Variable sub-components (Excel VCS G041-G045)
    tarifa: float = 0.0
    opex_variable: float = 0.0
    tasa_escalamiento: float = 0.0
    hitl: float = 0.0


class CanalCTSDetalleV1(BaseModel):
    """Per-channel CTS detail — Excel CTS rows 90-125."""
    model_config = ConfigDict(extra="allow", frozen=True)

    canal: str = ""
    modalidad: str = ""
    fte: float = 0.0
    participacion_cadena_a: float = 0.0
    cts: float = 0.0
    # Payroll sub-components (/fte/month each)
    payroll: float = 0.0
    nomina_loaded: float = 0.0
    salario_fijo: float = 0.0
    salario_variable: float = 0.0
    capacitacion_inicial: float = 0.0
    capacitacion_rotacion: float = 0.0
    examenes: float = 0.0
    estudios_seguridad: float = 0.0
    crucero: float = 0.0
    # No-payroll sub-components
    no_payroll: float = 0.0
    opex_fijo: float = 0.0
    inversiones: float = 0.0
    costos_fijos: float = 0.0


class CostToServeV1(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    cts_cadena_a: float = 0.0
    cts_cadena_b: float = 0.0
    cts_cadena_c: float = 0.0
    cts_ponderado: float = 0.0
    participacion_a: float = Field(default=0.0)  # 0..1
    participacion_b: float = Field(default=0.0)
    participacion_c: float = Field(default=0.0)
    fte_cadena_a: float = 0.0
    vol_cadena_b: float = 0.0
    costo_total_acumulado: float = 0.0
    desglose_a: Optional[CostToServeDesgloseAV1] = None
    desglose_b: Optional[CostToServeDesgloseBV1] = None
    # GAP-CTS-ACT-1: Excel CTS!C58/C87 gate — controls channel-detail section visibility
    canal_view_habilitado: bool = False
    # GAP-CTS-CHAN-1: per-channel detail (Excel CTS rows 90-125)
    canales_detalle: List[CanalCTSDetalleV1] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Vision: Tarifas
# ---------------------------------------------------------------------------


class TarifaCanalV1(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    nombre_canal: str = ""
    modalidad: str = ""
    producto: str = ""
    fte: float = 0.0
    vol_mensual: float = 0.0
    modelo_cobro: str = "Fijo FTE"
    pct_fijo: float = 1.0
    pct_variable: float = 0.0
    componente_fijo: str = "FTE"
    componente_variable: str = ""
    costo_atribuible: float = 0.0
    ingreso_bruto: float = 0.0
    facturacion: float = 0.0
    tarifa_fijo_fte: float = 0.0
    tarifa_variable: float = 0.0
    vol_minimo_transaccion: float = 0.0
    payroll_ch: float = 0.0
    no_payroll_ch: float = 0.0
    costo_cadena_a_ch: float = 0.0
    cadena_b_atribuible: float = 0.0
    financieros_atribuible: float = 0.0
    nomina_agente_basico: float = 0.0
    tarifa_hora_loggeada: float = 0.0
    tarifa_hora_pagada: float = 0.0


class ReglasBusinessV1(BaseModel):
    """Excel rows 29-37: margins and contingencies per scenario."""
    model_config = ConfigDict(extra="allow", frozen=True)

    cont_operativa: float = 0.0
    cont_comercial: float = 0.0
    markup: float = 0.0
    descuento_volumen: float = 0.0
    margen_cadena_a: float = 0.0
    margen_cadena_b: float = 0.0
    margen_cadena_c: float = 0.0


class DesgloseCadenaTarifasV1(BaseModel):
    """Excel rows B40:C47, B50:C57, B60:C67: cost breakdown per chain."""
    model_config = ConfigDict(extra="allow", frozen=True)

    payroll: float = 0.0
    no_payroll: float = 0.0
    componente_fijo: float = 0.0
    componente_variable: float = 0.0
    ica: float = 0.0
    gmf: float = 0.0
    polizas: float = 0.0
    costos_financiacion: float = 0.0
    total_costo: float = 0.0
    ingreso_bruto: float = 0.0


class TarifasEscenarioV1(BaseModel):
    """Excel G43-G57: tariff calculations per scenario."""
    model_config = ConfigDict(extra="allow", frozen=True)

    facturacion_total: float = 0.0
    ingreso_componente_fijo: float = 0.0
    ingreso_componente_variable: float = 0.0
    tarifa_por_fte: float = 0.0
    tarifa_hora_loggeada: float = 0.0
    tarifa_hora_pagada: float = 0.0
    tarifa_por_transaccion: float = 0.0
    volumen_minimo_transaccion: float = 0.0


class EscenarioTarifasResumenV1(BaseModel):
    """Excel B10:H21: per-scenario summary."""
    model_config = ConfigDict(extra="allow", frozen=True)

    escenario: int = 0
    modalidad: str = ""
    canal: str = ""
    modelo_cobro: str = ""
    componente_fijo_label: str = ""
    pct_fijo: float = 0.0
    componente_variable_label: str = ""
    pct_variable: float = 0.0
    facturacion_directo: float = 0.0
    tarifa_componente_fijo: float = 0.0
    tarifa_componente_variable: float = 0.0


class EscenarioTarifasDetalleV1(BaseModel):
    """Hierarchical per-scenario detail container."""
    model_config = ConfigDict(extra="allow", frozen=True)

    meta: EscenarioTarifasResumenV1 = Field(default_factory=EscenarioTarifasResumenV1)
    reglas_business: ReglasBusinessV1 = Field(default_factory=ReglasBusinessV1)
    cadena_a: DesgloseCadenaTarifasV1 = Field(default_factory=DesgloseCadenaTarifasV1)
    cadena_b: DesgloseCadenaTarifasV1 = Field(default_factory=DesgloseCadenaTarifasV1)
    cadena_c: DesgloseCadenaTarifasV1 = Field(default_factory=DesgloseCadenaTarifasV1)
    tarifas: TarifasEscenarioV1 = Field(default_factory=TarifasEscenarioV1)
    componente_fijo: Optional[dict] = None
    componente_variable: Optional[dict] = None
    tarifas_venta: List[dict] = Field(default_factory=list)


class DesgloseProductoOpexV1(BaseModel):
    """Excel rows 91-98: product-level OPEX breakdown.

    ``costo_financiacion`` and ``polizas`` are ``null`` when the workbook
    does not support per-product attribution (financing is platform-level,
    polizas are cadena-level). ``null`` means *not attributable*, not zero.
    """
    model_config = ConfigDict(extra="allow", frozen=True)

    producto: str = ""
    costo_directo: float = 0.0
    costo_financiacion: Optional[float] = None
    polizas: Optional[float] = None
    ingreso_producto: float = 0.0


class VisionTarifasV1(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    canales: List[TarifaCanalV1] = Field(default_factory=list)
    costo_cadena_a_total: float = 0.0
    costo_cadena_b_total: float = 0.0
    costo_cadena_c_total: float = 0.0
    costo_total: float = 0.0
    ingreso_mensual: float = 0.0
    # Hierarchical Vision Tarifas (from Excel reverse-engineering)
    escenarios_detalle: List[EscenarioTarifasDetalleV1] = Field(default_factory=list)
    desglose_producto_opex: List[DesgloseProductoOpexV1] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Vision: P&G
# ---------------------------------------------------------------------------


class VisionPyGRowV1(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    key: str
    label: str
    seccion: str
    tipo: str
    signo: str
    valores: List[float] = Field(default_factory=list)
    acumulado: float = 0.0
    promedio: float = 0.0


class ResumenEjecutivoPyGV1(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    meses_contrato: int = 0
    meses_activos: int = 0
    valor_total_deal: float = 0.0
    ingreso_neto_total: float = 0.0
    costo_total_contrato: float = 0.0
    contribucion_total: float = 0.0
    pct_utilidad_promedio: float = 0.0
    cumple_margen_minimo: bool = True


class VisionPyGV1(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    resumen: ResumenEjecutivoPyGV1 = Field(default_factory=ResumenEjecutivoPyGV1)
    filas: List[VisionPyGRowV1] = Field(default_factory=list)
    meses_contrato: int = 0
    meses_activos: int = 0


# ---------------------------------------------------------------------------
# Waterfall
# ---------------------------------------------------------------------------


class WaterfallV1(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    payroll_a: float = 0.0
    no_payroll_a: float = 0.0
    costo_b: float = 0.0
    costo_c: float = 0.0
    financiacion: float = 0.0
    polizas: float = 0.0
    ica: float = 0.0
    gmf: float = 0.0
    costo_total: float = 0.0
    ingreso_bruto: float = 0.0
    contingencias: float = 0.0
    markup_descuento: float = 0.0
    ingreso_neto: float = 0.0
    contribucion: float = 0.0
    meses_activos: int = 0


# ---------------------------------------------------------------------------
# Visión Ejecutiva Integral — secciones agregadas (servicio / canal / equipo)
# ---------------------------------------------------------------------------


class VisionServicioResumenV1(BaseModel):
    """Visión General por Servicio — rollup del deal bajo su servicio."""
    model_config = ConfigDict(extra="allow", frozen=True)

    servicio: str = ""
    ingreso_mensual: float = 0.0
    cts_ponderado: float = 0.0
    costo_mensual: float = 0.0
    margen: float = 0.0
    contribucion_total: float = 0.0
    fte_total: float = 0.0
    volumen_mensual: float = 0.0
    meses_contrato: int = 0
    cadenas_activas: List[str] = Field(default_factory=list)


class CanalResumenV1(BaseModel):
    """Visión General por Canal — fila consolidada por canal."""
    model_config = ConfigDict(extra="allow", frozen=True)

    canal: str = ""
    modalidad: str = ""
    modelo_cobro: str = ""
    estado: str = "Activo"
    fte: float = 0.0
    participacion_cadena_a: float = 0.0
    volumen_mensual: float = 0.0
    facturacion: float = 0.0
    ingreso_bruto: float = 0.0
    costo_atribuible: float = 0.0
    pct_fijo: float = 0.0
    pct_variable: float = 0.0


class CanalDetalleV1(BaseModel):
    """Vista Detallada por Canal — desglose completo de un canal."""
    model_config = ConfigDict(extra="allow", frozen=True)

    canal: str = ""
    modalidad: str = ""
    datos_disponibles: bool = True
    fte: float = 0.0
    payroll: float = 0.0
    no_payroll: float = 0.0
    cadena_b_atribuible: float = 0.0
    financieros_atribuible: float = 0.0
    costo_cadena_a: float = 0.0
    cts: float = 0.0
    nomina_loaded: float = 0.0
    salario_fijo: float = 0.0
    salario_variable: float = 0.0
    capacitacion_inicial: float = 0.0
    capacitacion_rotacion: float = 0.0
    examenes: float = 0.0
    estudios_seguridad: float = 0.0
    crucero: float = 0.0
    opex_fijo: float = 0.0
    inversiones: float = 0.0
    costos_fijos: float = 0.0
    tarifa_fijo_fte: float = 0.0
    tarifa_variable: float = 0.0
    facturacion: float = 0.0
    ingreso_bruto: float = 0.0


class RolEquipoV1(BaseModel):
    """Un rol/cargo de la estructura del equipo."""
    model_config = ConfigDict(extra="allow", frozen=True)

    rol: str = ""
    cargo_tipo: str = ""
    canal: str = ""
    modalidad: str = ""
    fte: float = 0.0
    es_soporte: bool = False
    salario_cargado_unitario: float = 0.0
    costo_mensual: float = 0.0


class GrupoCargoEquipoV1(BaseModel):
    """Agregación por tipo de cargo."""
    model_config = ConfigDict(extra="allow", frozen=True)

    cargo_tipo: str = ""
    fte_total: float = 0.0
    costo_total: float = 0.0
    num_roles: int = 0


class EstructuraEquipoV1(BaseModel):
    """Estructura del Equipo — roles, FTE, costos y agregación por cargo."""
    model_config = ConfigDict(extra="allow", frozen=True)

    roles: List[RolEquipoV1] = Field(default_factory=list)
    por_cargo: List[GrupoCargoEquipoV1] = Field(default_factory=list)
    fte_total: float = 0.0
    fte_agentes: float = 0.0
    fte_soporte: float = 0.0
    costo_total_mensual: float = 0.0


# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------


class VisionsBundleV1(BaseModel):
    """All four official visions in a single envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tarifas: Optional[VisionTarifasV1] = None
    pyg: Optional[VisionPyGV1] = None
    cost_to_serve: Optional[CostToServeV1] = None
    waterfall: Optional[WaterfallV1] = None
