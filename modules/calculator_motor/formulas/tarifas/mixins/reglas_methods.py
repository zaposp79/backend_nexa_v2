from __future__ import annotations
"""VisionTarifasMethodsMixin re-export (FASE Z.4.3b)."""
from nexa_engine.modules.calculator_motor.formulas.tarifas.mixins.reglas_methods_1 import (
    VisionTarifasMethodsMixin1,
)
from nexa_engine.modules.calculator_motor.formulas.tarifas.mixins.reglas_methods_2 import (
    VisionTarifasMethodsMixin2,
)


class VisionTarifasMethodsMixin(VisionTarifasMethodsMixin1, VisionTarifasMethodsMixin2):
    """All private VisionTarifasCalculator methods."""

__all__ = ["VisionTarifasMethodsMixin"]
