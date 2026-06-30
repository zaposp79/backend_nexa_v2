"""calculator_motor CTS formula ownership root."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .builder import build_cost_to_serve_result
    from .calculator import CostToServeCalculator

__all__ = ["build_cost_to_serve_result", "CostToServeCalculator"]


def __getattr__(name: str):
    if name == "build_cost_to_serve_result":
        from .builder import build_cost_to_serve_result

        return build_cost_to_serve_result
    if name == "CostToServeCalculator":
        from .calculator import CostToServeCalculator

        return CostToServeCalculator
    raise AttributeError(name)
