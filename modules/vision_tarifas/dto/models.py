"""vision_tarifas DTOs — single-owner calculation types.

Canonical home for EscenarioTarifasResumen and related single-owner types
moved from shared/models/visions_tarifas.py in Fase 2E (2026-06-10).
shared/models/visions_tarifas.py re-exports all names for backward compat.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class EscenarioTarifasResumen:
    """Resumen de un escenario — Excel rows 10-21 per scenario."""
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


@dataclass(slots=True)
class ReglasBusiness:
    """Reglas de negocio aplicadas — Excel rows 29-37."""
    cont_operativa: float = 0.0
    cont_comercial: float = 0.0
    markup: float = 0.0
    descuento_volumen: float = 0.0
    margen_cadena_a: float = 0.0
    margen_cadena_b: float = 0.0
    margen_cadena_c: float = 0.0


@dataclass(slots=True)
class DesgloseCadenaTarifas:
    """Desglose de costos por cadena — Excel rows B40:C47, B50:C57, B60:C67."""
    payroll: float = 0.0
    no_payroll: float = 0.0
    componente_fijo: float = 0.0
    componente_variable: float = 0.0
    ica: float = 0.0
    gmf: float = 0.0
    polizas: float = 0.0
    costos_financiacion: float = 0.0
    aplica_polizas: bool = False
    total_costo: float = 0.0
    ingreso_bruto: float = 0.0


@dataclass(slots=True)
class ImproductiveBreakdown:
    """Sub-components of improductive time — Excel rows 113-118."""
    breaks_minutos: float = 0.0
    breaks_pct: float = 0.0
    training_minutos: float = 0.0
    training_pct: float = 0.0
    deslogueos_minutos: float = 0.0
    deslogueos_pct: float = 0.0
    coaching_minutos: float = 0.0
    coaching_pct: float = 0.0
    pausa_activa_minutos: float = 0.0
    pausa_activa_pct: float = 0.0
    total_improductive_minutos: float = 0.0
    total_improductive_pct: float = 0.0


@dataclass(slots=True)
class TimeCascade:
    """Time cascade computation — Excel rows 121-127."""
    scheduled_hours: float = 0.0
    paid_hours: float = 0.0
    worked_hours: float = 0.0
    logged_hours: float = 0.0
    productive_hours: float = 0.0


@dataclass(slots=True)
class ComponenteFijo:
    """Fixed component detail — Excel rows 104-127."""
    habilitado: bool = False
    horas_semana: float = 42.0
    horas_entrenamiento_mes: float = 8.0
    semanas_mes: float = 4.33
    improductive_breakdown: ImproductiveBreakdown = field(default_factory=ImproductiveBreakdown)
    time_cascade: TimeCascade = field(default_factory=TimeCascade)


@dataclass(slots=True)
class MesComision:
    """Single month in variable component commission table — Excel rows 136-143."""
    mes: int = 0
    comision: float = 0.0
    ingreso_total: float = 0.0
    per_capita: float = 0.0
    portfolio_age: str = ""
    difficulty_driver: float = 0.0
    benchmark: float = 0.0
    calculado: float = 0.0


@dataclass(slots=True)
class ComponenteVariable:
    """Variable component detail — Excel rows 130-143."""
    habilitado: bool = False
    cant_asesores: int = 0
    meses_comisiones: list[MesComision] = field(default_factory=list)


@dataclass(slots=True)
class TarifaXVenta:
    """Monthly sales targets — Excel rows 149-161."""
    mes: int = 0
    tarifa_venta: float = 0.0
    minimo_ventas: float = 0.0


@dataclass(slots=True)
class DesgloseProductoOpex:
    """Product-level OPEX breakdown — Excel rows 91-98."""
    producto: str = ""
    costo_directo: float = 0.0
    costo_financiacion: float | None = None
    polizas: float | None = None
    ingreso_producto: float = 0.0


@dataclass(slots=True)
class TarifasEscenario:
    """Tarifa calculations per scenario — Excel G43-G57 section."""
    facturacion_total: float = 0.0
    ingreso_componente_fijo: float = 0.0
    ingreso_componente_variable: float = 0.0
    tarifa_por_fte: float = 0.0
    tarifa_hora_loggeada: float = 0.0
    tarifa_hora_pagada: float = 0.0
    tarifa_por_transaccion: float = 0.0
    volumen_minimo_transaccion: float = 0.0


@dataclass(slots=True)
class EscenarioTarifasDetalle:
    """Hierarchical detail for a single scenario."""
    meta: EscenarioTarifasResumen = field(default_factory=EscenarioTarifasResumen)
    reglas_business: ReglasBusiness = field(default_factory=ReglasBusiness)
    cadena_a: DesgloseCadenaTarifas = field(default_factory=DesgloseCadenaTarifas)
    cadena_b: DesgloseCadenaTarifas = field(default_factory=DesgloseCadenaTarifas)
    cadena_c: DesgloseCadenaTarifas = field(default_factory=DesgloseCadenaTarifas)
    tarifas: TarifasEscenario = field(default_factory=TarifasEscenario)
    componente_fijo: ComponenteFijo | None = None
    componente_variable: ComponenteVariable | None = None
    tarifas_venta: list[TarifaXVenta] = field(default_factory=list)


__all__ = [
    "EscenarioTarifasResumen",
    "ReglasBusiness",
    "DesgloseCadenaTarifas",
    "ImproductiveBreakdown",
    "TimeCascade",
    "ComponenteFijo",
    "MesComision",
    "ComponenteVariable",
    "TarifaXVenta",
    "DesgloseProductoOpex",
    "TarifasEscenario",
    "EscenarioTarifasDetalle",
]
