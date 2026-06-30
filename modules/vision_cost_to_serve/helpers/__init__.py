"""
Service catalog helper — canal_detail_habilitado() and related gates.

Ownership: vision_cost_to_serve · public helper.
calculator_motor imports canal_detail_habilitado() from this package.

This is NOT a formula — it is the service catalog (business gate driven
by Panel!C5 selection). See servicio_catalogo.py for Excel evidence.
"""

from nexa_engine.modules.vision_cost_to_serve.helpers.charts_mapper import (
    build_charts_from_result,
)
from nexa_engine.modules.vision_cost_to_serve.helpers.screen_mapper import (
    build_vision_cts_from_result,
)

__all__ = [
    "build_charts_from_result",
    "build_vision_cts_from_result",
]
