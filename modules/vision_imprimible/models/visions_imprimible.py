"""
Pricing visions — API contracts (Visión Imprimible composite).

⚠️ STABILITY CONTRACT
VisionImprimible is an API-facing payload, persisted in DB.
Breaking changes (field renames, type changes, removals) require
an API version bump + schema migration.
See: docs/refactor/shared_models_phase2c_visions_audit.md
"""
from __future__ import annotations

from dataclasses import dataclass, field

from nexa_engine.modules.vision_tarifas.models.visions_tarifas import (
    TarifaCanal,
    ReglaNegocios,
    WaterfallPromedio,
    EvaluacionRiesgo,
)


@dataclass(slots=True)
class FichaDelDeal:
    cliente: str = ""
    fecha_inicio: str = ""
    servicio: str = ""
    duracion: str = ""


@dataclass(slots=True)
class EconomicsDeal:
    ingreso_mensual: float = 0.0
    cts_mensual: float = 0.0
    margen: float = 0.0
    contribucion_total: float = 0.0
    escenario_referencia: str = ""


@dataclass(slots=True)
class ConfiguracionComercial:
    modelo_cobro: str = ""
    tarifa_fija: float = 0.0
    tarifa_variable: float = 0.0
    canales: list[TarifaCanal] = field(default_factory=list)


@dataclass(slots=True)
class EvolucionMensual:
    meses: list[int] = field(default_factory=list)
    ingresos_neto: list[float] = field(default_factory=list)
    costos_total: list[float] = field(default_factory=list)
    contribucion: list[float] = field(default_factory=list)
    margen_mensual: list[float] = field(default_factory=list)


@dataclass(slots=True)
class ComparativoEscenario:
    escenario: str
    modalidad_canal: str
    modelo_cobro: str


@dataclass(slots=True)
class VisionServicioResumen:
    """Visión General por Servicio — rollup agregado del deal bajo su servicio."""
    servicio: str = ""
    ingreso_mensual: float = 0.0
    cts_ponderado: float = 0.0
    costo_mensual: float = 0.0
    margen: float = 0.0
    contribucion_total: float = 0.0
    fte_total: float = 0.0
    volumen_mensual: float = 0.0
    meses_contrato: int = 0
    cadenas_activas: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ModalidadCanalMetricas:
    """Métricas de una modalidad (Inbound / Outbound) dentro de un canal."""
    fte: float = 0.0
    payroll: float = 0.0
    no_payroll: float = 0.0
    costo_total: float = 0.0
    pct_participacion: float = 0.0


@dataclass(slots=True)
class CanalResumen:
    """Visión General por Canal — fila consolidada por canal con split Inbound/Outbound."""
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
    inbound: ModalidadCanalMetricas | None = None
    outbound: ModalidadCanalMetricas | None = None


@dataclass(slots=True)
class CanalDetalleModalidad:
    """Desglose de una modalidad (Inbound/Outbound) dentro de un canal."""
    fte: float = 0.0
    payroll: float = 0.0
    no_payroll: float = 0.0
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
    cts: float = 0.0
    pct_participacion: float = 0.0


@dataclass(slots=True)
class CanalDetalle:
    """Vista Detallada por Canal — desglose completo con split Inbound/Outbound."""
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
    inbound: CanalDetalleModalidad | None = None
    outbound: CanalDetalleModalidad | None = None


@dataclass(slots=True)
class RolEquipo:
    """Un rol/cargo de la estructura del equipo — un PerfilCadenaA."""
    rol: str = ""
    cargo_tipo: str = ""
    canal: str = ""
    modalidad: str = ""
    fte: float = 0.0
    es_soporte: bool = False
    salario_cargado_unitario: float = 0.0
    costo_mensual: float = 0.0


@dataclass(slots=True)
class GrupoCargoEquipo:
    """Agregación por tipo de cargo (CargoTipo) — subtotales de la estructura."""
    cargo_tipo: str = ""
    fte_total: float = 0.0
    costo_total: float = 0.0
    num_roles: int = 0


@dataclass(slots=True)
class EstructuraEquipo:
    """Estructura del Equipo — roles, FTE, costos y agregación por tipo de cargo."""
    roles: list[RolEquipo] = field(default_factory=list)
    por_cargo: list[GrupoCargoEquipo] = field(default_factory=list)
    fte_total: float = 0.0
    fte_agentes: float = 0.0
    fte_soporte: float = 0.0
    costo_total_mensual: float = 0.0


@dataclass(slots=True)
class VisionImprimible:
    """STABILITY CONTRACT: aggregate raíz del resultado imprimible. Consumed across
    ≥2 bounded contexts (vision_imprimible, api, serializers, tests). API-facing
    and persisted in DB. Breaking changes require API version bump + schema migration.
    Verified cross-cutting in Fase 2C audit (2026-06-10).
    See: docs/refactor/shared_models_phase2c_visions_audit.md

    GAP-VIS-1: Composición pura de todos los resultados del deal."""
    ficha: FichaDelDeal = field(default_factory=FichaDelDeal)
    economics: EconomicsDeal = field(default_factory=EconomicsDeal)
    configuracion_comercial: ConfiguracionComercial = field(default_factory=ConfiguracionComercial)
    evolucion_mensual: EvolucionMensual = field(default_factory=EvolucionMensual)
    waterfall: WaterfallPromedio | None = None
    reglas_negocio: list[ReglaNegocios] = field(default_factory=list)
    evaluacion_riesgo: EvaluacionRiesgo | None = None
    escenarios: list["EscenarioComercial"] = field(default_factory=list)  # type: ignore[name-defined]
    comparativo_escenarios: list[ComparativoEscenario] = field(default_factory=list)
    vision_por_servicio: list[VisionServicioResumen] = field(default_factory=list)
    vision_por_canal: list[CanalResumen] = field(default_factory=list)
    detalle_por_canal: list[CanalDetalle] = field(default_factory=list)
    estructura_equipo: EstructuraEquipo | None = None


__all__ = [
    "FichaDelDeal",
    "EconomicsDeal",
    "ConfiguracionComercial",
    "EvolucionMensual",
    "ComparativoEscenario",
    "VisionServicioResumen",
    "ModalidadCanalMetricas",
    "CanalResumen",
    "CanalDetalleModalidad",
    "CanalDetalle",
    "RolEquipo",
    "GrupoCargoEquipo",
    "EstructuraEquipo",
    "VisionImprimible",
]
