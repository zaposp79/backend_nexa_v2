"""
nexa_engine/domain/frozen_parametrization.py
==============================================
FASE 6 — Parametrización frozen (versionada e inmutable).

Estructura de datos para una versión frozen de los parámetros del motor,
extraída directamente del Excel V2-6. Esta versión se usa para reproducibilidad
exacta de cálculos y para validar contra el Excel original.

Una vez frozen, los parámetros NO se actualizan automáticamente desde storage/
sino que se cargan desde storage/parametrization/frozen/{version}.json.

Parámetros frozen V2-6:
  - SMMLV: 1,750,905 COP (2025)
  - Auxilio transporte: 249,095 COP
  - Factores de indexación: IPC, SMMLV, mezclas, fijo (años 2025-2030)
  - Tasas de pólizas: 8 pólizas + comisión administración
  - ICA por ciudad: 20 ciudades
  - GMF: 0.4%
  - Rotación, ausentismo por servicio
  - Curva de productividad (9 meses)
  - Costos exámenes médicos, seguridad
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class FrozenParametrizationV26:
    """
    Snapshot inmutable de todos los parámetros V2-6.

    Usada para:
      1. Reproducibilidad exacta (los cálculos siempre usan la misma versión)
      2. Auditoría (qué parámetros se usaron en cada simulación)
      3. Validación (comparar motor vs Excel V2-6 con valores idénticos)
    """
    # ── Parámetros básicos ─────────────────────────────────────────────
    version: str = "v2-6"
    source: str = "Excel Nexa Pricing Simulator V2-6"

    # ── Nómina ─────────────────────────────────────────────────────────
    smmlv: float = 1_750_905.0  # COP, 2025
    auxilio_transporte: float = 249_095.0  # COP
    dotacion_mensual: float = 15_375.0  # COP

    # ── Factores de indexación (6 años: 2025-2030) ──────────────────────
    # Cada lista tiene 6 elementos [año1, año2, ..., año6]
    factor_ipc: List[float] = field(default_factory=lambda: [
        1.0, 1.05, 1.10817729, 1.166578233183, 1.228056906071744, 1.2927755050217247
    ])
    factor_smmlv: List[float] = field(default_factory=lambda: [
        1.0, 1.2378, 1.386336, 1.5526963200000004,
        1.7390198784000006, 1.9477022638080008
    ])
    factor_mix_70_30: List[float] = field(default_factory=list)
    factor_mix_80_20: List[float] = field(default_factory=list)
    factor_mix_20_80: List[float] = field(default_factory=list)
    factor_ipc_plus_1: List[float] = field(default_factory=list)
    factor_fixed: List[float] = field(default_factory=lambda: [1.0] * 6)

    # ── Tasas de pólizas (efectivas) ───────────────────────────────────
    poliza_seriedad: float = 0.005
    poliza_cumplimiento: float = 0.0062
    poliza_salarios: float = 0.0119
    poliza_calidad: float = 0.0119
    poliza_rc_cruzada: float = 0.0275
    poliza_irf: float = 0.0275
    poliza_responsabilidad: float = 0.0069
    poliza_admin_commission: float = 0.0118

    # ── Tasas fiscales ─────────────────────────────────────────────────
    ica_base: float = 0.01966
    gmf: float = 0.004
    timbre_nacional: float = 0.01

    # ── ICA por ciudad (20 ciudades) ───────────────────────────────────
    ica_por_ciudad: Dict[str, float] = field(default_factory=dict)

    # ── Defaults operacionales ─────────────────────────────────────────
    absenteeism_default: float = 0.065  # 6.5%
    rotation_default: float = 0.085  # 8.5%
    target_margin: float = 0.18  # 18%

    # ── Métricas por servicio ──────────────────────────────────────────
    # Absenteeism por servicio (Cobranzas, SAC, Ventas, SACO)
    absenteeism_by_service: Dict[str, float] = field(default_factory=lambda: {
        "cobranzas": 0.0826,
        "sac": 0.0820,
        "ventas_multicanal": 0.1010,
        "saco": 0.0806,
    })

    # Rotación por servicio
    rotation_by_service: Dict[str, float] = field(default_factory=lambda: {
        "cobranzas": 0.1199,
        "sac": 0.0772,
        "ventas_multicanal": 0.0952,
        "saco": 0.0964,
    })

    # ── Curva de productividad (9 meses, 0-8) ──────────────────────────
    # Cada servicio tiene su curva
    experience_ramp: Dict[str, List[float]] = field(default_factory=dict)

    # ── Costos de exámenes médicos ─────────────────────────────────────
    medical_exam_cost_bogota: float = 60_800.0
    medical_exam_cost_other: float = 58_000.0
    security_study_preliminary: float = 54_055.0
    security_study_final: float = 144_879.0

    # ── Salarios por rol (para validación) ──────────────────────────────
    salarios_por_rol: Dict[str, float] = field(default_factory=dict)

    # ── Metadata ───────────────────────────────────────────────────────
    extracted_at: str = ""  # ISO timestamp cuando se extrajo
    excel_file_path: str = ""  # Ruta del archivo Excel origen

    def as_dict(self) -> dict:
        """Exporta a dict Python puro (serializable a JSON)."""
        return {
            "version": self.version,
            "source": self.source,
            "smmlv": self.smmlv,
            "auxilio_transporte": self.auxilio_transporte,
            "dotacion_mensual": self.dotacion_mensual,
            "factor_ipc": self.factor_ipc,
            "factor_smmlv": self.factor_smmlv,
            "factor_mix_70_30": self.factor_mix_70_30,
            "factor_mix_80_20": self.factor_mix_80_20,
            "factor_mix_20_80": self.factor_mix_20_80,
            "factor_ipc_plus_1": self.factor_ipc_plus_1,
            "factor_fixed": self.factor_fixed,
            "poliza_seriedad": self.poliza_seriedad,
            "poliza_cumplimiento": self.poliza_cumplimiento,
            "poliza_salarios": self.poliza_salarios,
            "poliza_calidad": self.poliza_calidad,
            "poliza_rc_cruzada": self.poliza_rc_cruzada,
            "poliza_irf": self.poliza_irf,
            "poliza_responsabilidad": self.poliza_responsabilidad,
            "poliza_admin_commission": self.poliza_admin_commission,
            "ica_base": self.ica_base,
            "gmf": self.gmf,
            "timbre_nacional": self.timbre_nacional,
            "ica_por_ciudad": self.ica_por_ciudad,
            "absenteeism_default": self.absenteeism_default,
            "rotation_default": self.rotation_default,
            "target_margin": self.target_margin,
            "absenteeism_by_service": self.absenteeism_by_service,
            "rotation_by_service": self.rotation_by_service,
            "experience_ramp": self.experience_ramp,
            "medical_exam_cost_bogota": self.medical_exam_cost_bogota,
            "medical_exam_cost_other": self.medical_exam_cost_other,
            "security_study_preliminary": self.security_study_preliminary,
            "security_study_final": self.security_study_final,
            "salarios_por_rol": self.salarios_por_rol,
            "extracted_at": self.extracted_at,
            "excel_file_path": self.excel_file_path,
        }

    @staticmethod
    def from_dict(data: dict) -> "FrozenParametrizationV26":
        """Reconstruye desde dict (lo inverso de as_dict())."""
        return FrozenParametrizationV26(**{
            k: v for k, v in data.items()
            if k in FrozenParametrizationV26.__dataclass_fields__
        })
