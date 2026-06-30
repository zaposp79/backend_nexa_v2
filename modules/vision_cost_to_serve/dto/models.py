"""Cost-To-Serve vision models — public contract.

Ownership: vision_cost_to_serve · public DTOs.
calculator_motor imports these types to build ResultadoCostToServe.
vision layer imports them to serialize API responses.

These dataclasses define the public API shape for Cost To Serve.
Changes require API version bump.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DesgloseCTSCadenaA:
    """
    Sub-componentes del costo Cadena A.
    Mapeados célula a célula contra la hoja VCS (sección 03 Cadena A).
    """
    # ── Agregados (backward-compat) ───────────────────────────────────────
    nomina: float = 0.0
    no_payroll: float = 0.0

    # ── Sub-componentes de payroll (Excel C036-C043) ──────────────────────
    nomina_loaded: float = 0.0
    salario_fijo: float = 0.0
    salario_variable: float = 0.0
    capacitacion_inicial: float = 0.0
    capacitacion_rotacion: float = 0.0
    examenes: float = 0.0
    estudios_seguridad: float = 0.0
    # GAP-CTS-HIER-1: Crucero (Excel VCS row 43 / channel detail row 107).
    crucero: float = 0.0

    # ── Sub-componentes de no-payroll (Excel C046-C048) ───────────────────
    opex_fijo: float = 0.0
    inversiones: float = 0.0
    costos_fijos_estacion: float = 0.0

    @property
    def total(self) -> float:
        return self.nomina + self.no_payroll


@dataclass(slots=True)
class DesgloseCTSCadenaB:
    """Sub-componentes del costo Cadena B (por unidad de volumen)."""
    componente_fijo: float = 0.0
    opex: float = 0.0
    inversiones: float = 0.0
    soporte_mantenimiento: float = 0.0
    componente_variable: float = 0.0
    tarifa: float = 0.0
    opex_variable: float = 0.0
    tasa_escalamiento: float = 0.0
    hitl: float = 0.0

    @property
    def total(self) -> float:
        return self.componente_fijo + self.componente_variable


@dataclass(slots=True)
class CanalCTSDetalle:
    """GAP-CTS-CHAN-1: per-channel CTS detail (Excel CTS rows 90-125)."""
    canal: str = ""
    modalidad: str = ""
    fte: float = 0.0
    participacion_cadena_a: float = 0.0
    cts: float = 0.0
    payroll: float = 0.0
    nomina_loaded: float = 0.0
    salario_fijo: float = 0.0
    salario_variable: float = 0.0
    capacitacion_inicial: float = 0.0
    capacitacion_rotacion: float = 0.0
    examenes: float = 0.0
    estudios_seguridad: float = 0.0
    crucero: float = 0.0
    no_payroll: float = 0.0
    opex_fijo: float = 0.0
    inversiones: float = 0.0
    costos_fijos: float = 0.0


@dataclass(slots=True)
class ResultadoCostToServe:
    cts_cadena_a: float = 0.0
    cts_cadena_b: float = 0.0
    cts_ponderado: float = 0.0
    participacion_a: float = 0.0
    participacion_b: float = 0.0
    participacion_c: float = 0.0
    fte_cadena_a: float = 0.0
    vol_cadena_b: float = 0.0
    vol_cadena_c: float = 0.0
    cts_cadena_c: float = 0.0
    costo_total_acumulado: float = 0.0
    desglose_a: DesgloseCTSCadenaA = field(default_factory=DesgloseCTSCadenaA)
    desglose_b: DesgloseCTSCadenaB = field(default_factory=DesgloseCTSCadenaB)
    canal_view_habilitado: bool = False
    canales_detalle: list[CanalCTSDetalle] = field(default_factory=list)


__all__ = [
    "DesgloseCTSCadenaA",
    "DesgloseCTSCadenaB",
    "CanalCTSDetalle",
    "ResultadoCostToServe",
]
