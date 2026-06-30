"""Read-only public layer for Vision Tarifas.

Formula ownership lives in calculator_motor. This package keeps the public API,
result models, and backward-compatible imports for callers that still import
VisionTarifasCalculator from vision_tarifas.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import VisionTarifasCalculator

__all__ = ["VisionTarifasCalculator"]


def __getattr__(name: str):
    if name == "VisionTarifasCalculator":
        from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import VisionTarifasCalculator

        return VisionTarifasCalculator
    raise AttributeError(name)
