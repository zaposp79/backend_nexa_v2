"""
domain.staffing.calculators
===========================

Pure staffing calculators. NO IO, NO logging.

Public API
----------

  StaffingCalculator.aplicar_rampup(fte_target, factor_rampup) -> float
  StaffingCalculator.fte_efectivo_para_examenes(fte_base, fraccion_staff_extra) -> float

WAVE9-DEFERRED: ramp-up tables themselves are read from
`IParametrizationProvider.get_rampup()`; that lookup lives in
`application/use_cases/build_staffing.py` (orchestration) rather than here.
"""

from __future__ import annotations


class StaffingCalculator:
    """Pure staffing math. Stateless. Class methods."""

    @staticmethod
    def aplicar_rampup(fte_target: float, factor_rampup: float) -> float:
        """fte_efectivo = fte_target × factor_rampup (clamp negativos a 0)."""
        if fte_target <= 0 or factor_rampup <= 0:
            return 0.0
        return fte_target * factor_rampup

    @staticmethod
    def fte_efectivo_para_examenes(fte_base: float, fraccion_staff_extra: float) -> float:
        """
        FTE efectivo para exámenes médicos:
          fte_examenes = fte_base × (1 + fraccion_staff_extra)
        donde `fraccion_staff_extra` es la suma proporcional de
        supervisores/formadores/monitores que también deben examinarse.
        """
        if fte_base <= 0:
            return 0.0
        return fte_base * (1.0 + max(0.0, fraccion_staff_extra))


__all__ = ["StaffingCalculator"]
