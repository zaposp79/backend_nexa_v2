"""calculator_motor tariff formula ownership root."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .builder import build_vision_tarifas_result
    from .reglas import VisionTarifasCalculator

__all__ = ["build_vision_tarifas_result", "VisionTarifasCalculator"]


def __getattr__(name: str):
    if name == "build_vision_tarifas_result":
        from .builder import build_vision_tarifas_result

        return build_vision_tarifas_result
    if name == "VisionTarifasCalculator":
        from .reglas import VisionTarifasCalculator

        return VisionTarifasCalculator
    raise AttributeError(name)
