"""Read-only compatibility exports for legacy Vision Tarifas mixin imports.

All mixins now live in calculator_motor. This shim re-exports directly.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexa_engine.modules.calculator_motor.formulas.tarifas.mixins.reglas_methods import (
        VisionTarifasMethodsMixin,
    )
    from nexa_engine.modules.calculator_motor.formulas.tarifas.mixins.reglas_methods_1 import (
        VisionTarifasMethodsMixin1,
    )
    from nexa_engine.modules.calculator_motor.formulas.tarifas.mixins.reglas_methods_2 import (
        VisionTarifasMethodsMixin2,
    )

__all__ = [
    "VisionTarifasMethodsMixin",
    "VisionTarifasMethodsMixin1",
    "VisionTarifasMethodsMixin2",
]


def __getattr__(name: str):
    if name == "VisionTarifasMethodsMixin":
        from nexa_engine.modules.calculator_motor.formulas.tarifas.mixins.reglas_methods import (
            VisionTarifasMethodsMixin,
        )
        return VisionTarifasMethodsMixin
    if name == "VisionTarifasMethodsMixin1":
        from nexa_engine.modules.calculator_motor.formulas.tarifas.mixins.reglas_methods_1 import (
            VisionTarifasMethodsMixin1,
        )
        return VisionTarifasMethodsMixin1
    if name == "VisionTarifasMethodsMixin2":
        from nexa_engine.modules.calculator_motor.formulas.tarifas.mixins.reglas_methods_2 import (
            VisionTarifasMethodsMixin2,
        )
        return VisionTarifasMethodsMixin2
    raise AttributeError(name)
