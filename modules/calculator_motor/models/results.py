"""
calculator_motor/models/results.py — Canonical home for pipeline output models.

⚠️  STABILITY CONTRACT
PricingResult is an API-facing payload, serialized and persisted in DB.
Breaking changes require an API version bump + schema migration.

Cross-cutting: consumed by calculator_motor, audit, lineage, vision_imprimible.
Ownership inversion (2026-06-10): moved here from shared/models/results.py.
modules/shared/models/results.py is now a backward-compat adapter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from nexa_engine.modules.shared.exceptions import ValidationError


@dataclass
class ResultadoNomina:
    salario_fijo: float = 0.0
    comisiones: float = 0.0
    capacitacion_inicial: float = 0.0
    capacitacion_rotacion: float = 0.0
    examenes: float = 0.0
    seguridad: float = 0.0
    crucero: float = 0.0

    @property
    def total(self) -> float:
        return (self.salario_fijo + self.comisiones + self.capacitacion_inicial
                + self.capacitacion_rotacion + self.examenes + self.seguridad
                + self.crucero)


@dataclass
class ResultadoNoPayroll:
    opex_ti: float = 0.0
    capex: float = 0.0
    costos_fijos: float = 0.0

    @property
    def total(self) -> float:
        return self.opex_ti + self.capex + self.costos_fijos


@dataclass
class ResultadoCadenaB:
    opex_fijo: float = 0.0
    inversiones: float = 0.0
    soporte_mantenimiento: float = 0.0
    costo_variable: float = 0.0
    escalamiento: float = 0.0
    hitl: float = 0.0

    @property
    def total(self) -> float:
        return (self.opex_fijo + self.inversiones + self.soporte_mantenimiento
                + self.costo_variable + self.escalamiento + self.hitl)


@dataclass
class ResultadoCadenaC:
    tarifa_proveedor: float = 0.0
    opex_fijo_integ: float = 0.0
    opex_var_integ: float = 0.0
    inversiones: float = 0.0
    equipo_integ: float = 0.0
    escalamiento: float = 0.0
    hitl: float = 0.0

    @property
    def total(self) -> float:
        return (self.tarifa_proveedor + self.opex_fijo_integ + self.opex_var_integ
                + self.inversiones + self.equipo_integ + self.escalamiento + self.hitl)

    @property
    def total_pyg(self) -> float:
        """P&G display value — excludes hitl, equipo_integ, opex_var_integ.
        Matches Vision P&G row 55 (Costo C). The excluded components flow
        into the financial cost base (ICA/GMF) via costo_c_fin."""
        return (self.tarifa_proveedor + self.opex_fijo_integ
                + self.inversiones + self.escalamiento)


@dataclass
class CostosTotalesMes:
    mes: int = 0
    payroll_a: float = 0.0
    no_payroll_a: float = 0.0
    costo_b: float = 0.0
    costo_c: float = 0.0
    # Full Cadena C cost including hitl + equipo_integ + opex_var_integ.
    # Used as financial base for ICA/GMF/polizas calculations.
    # costo_c (above) is the P&G display value (excludes those components).
    costo_c_fin: float = 0.0

    @property
    def costo_a(self) -> float:
        return self.payroll_a + self.no_payroll_a

    @property
    def total(self) -> float:
        return self.costo_a + self.costo_b + self.costo_c

    @property
    def total_fin(self) -> float:
        """Total using full Cadena C for financial calculations."""
        return self.costo_a + self.costo_b + self.costo_c_fin


@dataclass
class CostosFinancierosMes:
    financiacion: float = 0.0
    polizas: float = 0.0
    polizas_a: float = 0.0
    polizas_b: float = 0.0
    polizas_c: float = 0.0
    ica: float = 0.0
    ica_a: float = 0.0
    ica_c: float = 0.0
    gmf: float = 0.0
    gmf_a: float = 0.0
    gmf_c: float = 0.0
    # GAP-PYG-3: Comisión de Administración
    comision_administracion: float = 0.0
    # Comisión de administración atribuible a Cadena A (needed for Vision Tarifas C45 attribution)
    comision_admin_cadena_a: float = 0.0
    # VT-specific cadena-A financial sub-total: polizas_a_vt + ica_a_vt + gmf_a_vt.
    # Uses wider poliza tasa (per_canal + non-per_canal with pct_atribuible <= 0.2).
    # Kept separate from PyG fields so pyg.polizas (H69) is unchanged.
    costo_financiero_vt_cadena_a: float = 0.0

    # EXCEL V2-8: HME!C258/C268/C278 — per-cadena proportional financing split.
    # Used by PyGCalculator to compute ingreso base from total cost (opex + financiero).
    fin_a: float = 0.0
    fin_b: float = 0.0
    fin_c: float = 0.0

    # Per-cadena ICA/GMF/ComAdm (B/C mirror of existing A fields).
    # Needed so PyGCalculator can reconstruct costo_total_por_cadena = opex + financiero.
    ica_b: float = 0.0
    gmf_b: float = 0.0
    comision_admin_cadena_b: float = 0.0
    comision_admin_cadena_c: float = 0.0

    @property
    def total(self) -> float:
        return self.financiacion + self.polizas + self.ica + self.gmf + self.comision_administracion


@dataclass
class PyGMensual:
    mes: int = 0
    rampup: float = 1.0
    ingreso_bruto_a: float = 0.0
    ingreso_bruto_b: float = 0.0
    ingreso_bruto_c: float = 0.0
    contingencia_op: float = 0.0
    contingencia_com: float = 0.0
    markup_ingreso: float = 0.0
    descuento_ingreso: float = 0.0
    payroll_a: float = 0.0
    no_payroll_a: float = 0.0
    costo_b: float = 0.0
    costo_c: float = 0.0
    costo_c_fin: float = 0.0
    ica: float = 0.0
    ica_a: float = 0.0
    ica_c: float = 0.0
    gmf_a: float = 0.0
    gmf_c: float = 0.0
    gmf: float = 0.0
    polizas: float = 0.0
    polizas_a: float = 0.0
    polizas_b: float = 0.0
    polizas_c: float = 0.0
    financiacion: float = 0.0
    # GAP-PYG-1: Imprevistos = panel.imprevistos × ingreso_bruto
    imprevistos_ingreso: float = 0.0
    # GAP-PYG-3: Comisión de Administración
    comision_administracion: float = 0.0
    # Comisión de administración atribuible a Cadena A (needed for Vision Tarifas C45 attribution)
    comision_admin_cadena_a: float = 0.0
    # VT-specific cadena-A financial sub-total (wider poliza tasa, see CostosFinancierosMes)
    costo_financiero_vt_cadena_a: float = 0.0

    # ── Acumulados (running totals) ──
    acum_ingreso_bruto: float = 0.0
    acum_ingreso_neto: float = 0.0
    acum_costo_total: float = 0.0
    acum_costos_financieros: float = 0.0
    acum_contribucion: float = 0.0

    def __post_init__(self) -> None:
        # H-02 FIX: Validate mathematically valid P&G results
        # Check for obvious inconsistencies that indicate calculation errors
        if self.ingreso_bruto < 0:
            raise ValidationError(f"PyG mes {self.mes}: ingreso_bruto cannot be negative ({self.ingreso_bruto})", field="pyg")
        if self.costo_operativo < 0:
            raise ValidationError(f"PyG mes {self.mes}: costo_operativo cannot be negative ({self.costo_operativo})", field="pyg")
        if self.costos_financieros < 0:
            raise ValidationError(f"PyG mes {self.mes}: costos_financieros cannot be negative ({self.costos_financieros})", field="pyg")

    @property
    def ingreso_bruto(self) -> float:
        return self.ingreso_bruto_a + self.ingreso_bruto_b + self.ingreso_bruto_c

    @property
    def ingreso_neto(self) -> float:
        return (self.ingreso_bruto
                + self.contingencia_op + self.contingencia_com
                + self.markup_ingreso - self.descuento_ingreso
                - self.imprevistos_ingreso)

    @property
    def costo_a(self) -> float:
        return self.payroll_a + self.no_payroll_a

    @property
    def costos_financieros(self) -> float:
        return self.ica + self.gmf + self.polizas + self.financiacion + self.comision_administracion

    @property
    def costo_operativo(self) -> float:
        return self.costo_a + self.costo_b + self.costo_c

    @property
    def componente_financiero(self) -> float:
        return self.costos_financieros

    @property
    def costo_total(self) -> float:
        return self.costo_a + self.costo_b + self.costo_c

    @property
    def contribucion(self) -> float:
        return self.ingreso_neto - self.costo_total

    @property
    def pct_contribucion(self) -> float:
        return self.contribucion / self.ingreso_neto if self.ingreso_neto else 0.0

    @property
    def utilidad_neta(self) -> float:
        return self.contribucion

    @property
    def pct_utilidad_neta(self) -> float:
        return self.utilidad_neta / self.ingreso_neto if self.ingreso_neto else 0.0


@dataclass
class KPIsDeal:
    costo_mensual_promedio: float = 0.0
    costo_cadena_a_promedio: float = 0.0
    ingreso_mensual: float = 0.0
    facturacion_mensual_proyectada: float = 0.0
    ingreso_bruto_total: float = 0.0
    ingreso_neto_total: float = 0.0
    costo_total_contrato: float = 0.0
    contribucion_total: float = 0.0
    utilidad_neta_total: float = 0.0
    pct_utilidad_neta_total: float = 0.0
    valor_total_deal: float = 0.0
    margen_minimo_requerido: float = 0.0
    cumple_margen_minimo: bool = True


@dataclass
class PricingResult:
    kpis: KPIsDeal
    pyg_por_mes: List[PyGMensual]
    panel: "PanelDeControl"  # type: ignore[name-defined]
    cost_to_serve: Optional["ResultadoCostToServe"] = None  # type: ignore[name-defined]
    vision_tarifas: Optional["ResultadoVisionTarifas"] = None  # type: ignore[name-defined]
    waterfall: Optional["WaterfallPromedio"] = None  # type: ignore[name-defined]
    reglas_negocio: List["ReglaNegocios"] = field(default_factory=list)  # type: ignore[name-defined]
    evaluacion_riesgo: Optional["EvaluacionRiesgo"] = None  # type: ignore[name-defined]
    vision_pyg: Optional["VisionPyG"] = None  # type: ignore[name-defined]
    vision_imprimible: Optional["VisionImprimible"] = None  # type: ignore[name-defined]
    datasets_vision: Optional["DatasetsVision"] = None  # type: ignore[name-defined]
    audit_trace: Optional[dict] = None


__all__ = [
    "ResultadoNomina",
    "ResultadoNoPayroll",
    "ResultadoCadenaB",
    "ResultadoCadenaC",
    "CostosTotalesMes",
    "CostosFinancierosMes",
    "PyGMensual",
    "KPIsDeal",
    "PricingResult",
]
