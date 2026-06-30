"""Internal read-model for VisionTarifasCalculator.

Pre-computed Nomina/NoPayroll results from the engine.
Not a public API contract — only internal transport engine → VT.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from nexa_engine.modules.shared.models.results import ResultadoNomina, ResultadoNoPayroll


@dataclass
class EscenarioCanalFacts:
    """Pre-computed facts for one escenario's canal+modalidad profile subset."""

    canal: str
    modalidad: str
    nomina_por_mes: List[ResultadoNomina]       # for perfiles_canal (all), len = numero_meses
    nomina_agente_por_mes: List[ResultadoNomina]   # for agent_perfiles only
    no_payroll_por_mes: List[ResultadoNoPayroll]   # empty if no_payroll_mensual override


@dataclass
class CanalExtensionFacts:
    """Pre-computed facts for all profiles in a canal (extension pólizas formula)."""

    canal: str
    nomina_por_mes: List[ResultadoNomina]            # months 1..n (from interleaved loop)
    no_payroll_por_mes: List[ResultadoNoPayroll]     # months 1..n (from interleaved loop)
    nomina_ultimo_mes: ResultadoNomina               # month n — separate call (audit trace)
    no_payroll_ultimo_mes: ResultadoNoPayroll        # month n — separate call (audit trace)


@dataclass
class VisionTarifasFacts:
    """Read-model: pre-computed facts for VisionTarifasCalculator.

    Engine computes these once; VisionTarifasCalculator consumes without re-calculating.
    escenarios: one entry per active escenario (those with agent_perfiles), in order.
    canales_extension: per canal_lower (for extension pólizas formula).
    canales_direct: per canal (original case) for backward compat path (no escenarios).
                    Keyed by canal value (case-preserving from PerfilCadenaA.canal).
    """

    escenarios: List[EscenarioCanalFacts] = field(default_factory=list)
    canales_extension: Dict[str, CanalExtensionFacts] = field(default_factory=dict)
    canales_direct: Dict[str, EscenarioCanalFacts] = field(default_factory=dict)


__all__ = ["EscenarioCanalFacts", "CanalExtensionFacts", "VisionTarifasFacts"]
