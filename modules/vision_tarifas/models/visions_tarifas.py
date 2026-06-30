"""
Pricing visions — API contracts (Tarifas + Riesgo + Waterfall).

⚠️ STABILITY CONTRACT
ResultadoVisionTarifas is an API-facing payload, persisted in DB.
Breaking changes (field renames, type changes, removals) require
an API version bump + schema migration.
See: docs/refactor/shared_models_phase2c_visions_audit.md

Ownership inversion (2026-06-10): canonical class definitions live here.
modules/shared/models/visions_tarifas.py is a backward-compat adapter.

NOTE: CriterioRiesgo cannot be moved to calculator_motor/formulas/risk/ due to
circular import via risk/__init__.py → riesgo.py → shared.models → visions_tarifas.
See TestCriterioRiesgoDefer for details on unblock path.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from nexa_engine.modules.vision_tarifas.dto.models import (  # noqa: F401
    EscenarioTarifasResumen,
    ReglasBusiness,
    DesgloseCadenaTarifas,
    ImproductiveBreakdown,
    TimeCascade,
    ComponenteFijo,
    MesComision,
    ComponenteVariable,
    TarifaXVenta,
    DesgloseProductoOpex,
    TarifasEscenario,
    EscenarioTarifasDetalle,
)


@dataclass(slots=True)
class TarifaCanal:
    """STABILITY CONTRACT: consumed across ≥2 bounded contexts (calculator_motor,
    vision_tarifas, vision_imprimible). API-facing and persisted in DB.
    Breaking changes require API version bump + schema migration.
    Verified cross-cutting in Fase 2C audit (2026-06-10).
    See: docs/refactor/shared_models_phase2c_visions_audit.md"""

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
    nomina_loaded_ch: float = 0.0
    salario_fijo_ch: float = 0.0
    salario_variable_ch: float = 0.0
    capacitacion_inicial_ch: float = 0.0
    capacitacion_rotacion_ch: float = 0.0
    examenes_ch: float = 0.0
    estudios_seguridad_ch: float = 0.0
    opex_it_ch: float = 0.0
    inversiones_ch: float = 0.0
    costos_fijos_ch: float = 0.0
    cadena_b_atribuible: float = 0.0
    financieros_atribuible: float = 0.0
    nomina_agente_basico: float = 0.0
    salario_cargado_ch: float = 0.0
    tarifa_hora_loggeada: float = 0.0
    tarifa_hora_pagada: float = 0.0


@dataclass(slots=True)
class ResultadoVisionTarifas:
    """STABILITY CONTRACT: consumed across ≥2 bounded contexts (calculator_motor,
    vision_tarifas, vision_imprimible, pyg). API-facing and persisted in DB.
    Breaking changes require API version bump + schema migration.
    Verified cross-cutting in Fase 2C audit (2026-06-10).
    See: docs/refactor/shared_models_phase2c_visions_audit.md"""

    canales: list[TarifaCanal] = field(default_factory=list)
    costo_cadena_a_total: float = 0.0
    costo_cadena_b_total: float = 0.0
    costo_cadena_c_total: float = 0.0
    costo_total: float = 0.0
    ingreso_mensual: float = 0.0
    ingreso_cadena_a: float = 0.0
    ingreso_cadena_b: float = 0.0
    ingreso_cadena_c: float = 0.0
    ica_cadena_a: float = 0.0
    gmf_cadena_a: float = 0.0
    polizas_cadena_a: float = 0.0
    escenarios_detalle: list[EscenarioTarifasDetalle] = field(default_factory=list)
    desglose_producto_opex: list[DesgloseProductoOpex] = field(default_factory=list)

    @property
    def costo_total_scenario(self) -> float:
        return self.costo_cadena_a_total + self.costo_cadena_c_total


@dataclass(slots=True)
class ReglaNegocios:
    """STABILITY CONTRACT: consumed across ≥2 bounded contexts (calculator_motor,
    vision_imprimible). API-facing and persisted in DB.
    Breaking changes require API version bump + schema migration.
    Verified cross-cutting in Fase 2C audit (2026-06-10).
    See: docs/refactor/shared_models_phase2c_visions_audit.md

    Regla de negocio con rango aplicado vs mínimo/máximo del deal."""
    nombre: str
    label: str
    aplicado: float
    min_valor: float | None
    max_valor: float | None
    status: str
    monto: float | None = None


@dataclass(slots=True)
class WaterfallPromedio:
    """STABILITY CONTRACT: consumed across ≥2 bounded contexts (calculator_motor,
    vision_imprimible). API-facing and persisted in DB.
    Breaking changes require API version bump + schema migration.
    Verified cross-cutting in Fase 2C audit (2026-06-10).
    See: docs/refactor/shared_models_phase2c_visions_audit.md

    Promedio mensual de cada componente — fuente del gráfico waterfall."""
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


@dataclass(slots=True)
class CriterioRiesgo:
    id: int
    factor: str
    categoria: str
    valor_evaluado: str
    calificacion: str
    puntaje: int
    peso: float


@dataclass(slots=True)
class EvaluacionRiesgo:
    """STABILITY CONTRACT: consumed across ≥2 bounded contexts (calculator_motor,
    vision_imprimible). API-facing and persisted in DB.
    Breaking changes require API version bump + schema migration.
    Verified cross-cutting in Fase 2C audit (2026-06-10).
    See: docs/refactor/shared_models_phase2c_visions_audit.md"""

    score_cliente: float = 0.0
    score_operativo: float = 0.0
    score_total: float = 0.0
    clasificacion_total: str = "Bajo"
    requiere_aprobacion: bool = False
    criterios: list[CriterioRiesgo] = field(default_factory=list)


__all__ = [
    # Re-exported from vision_tarifas/dto/models.py (single-owner, canonical location)
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
    # Cross-cutting stability contracts (canonical here, adapter at shared/models/visions_tarifas.py)
    "TarifaCanal",
    "ResultadoVisionTarifas",
    "ReglaNegocios",
    "WaterfallPromedio",
    "CriterioRiesgo",
    "EvaluacionRiesgo",
]
