"""Backward compatibility shim for vision_pyg services.

DEPRECATED: Import from nexa_engine.modules.vision_pyg.services instead.
"""
from nexa_engine.modules.vision_pyg.services import (
    CostosTotalesCalculator,
    KPIsCalculator,
    PyGCalculator,
)

__all__ = [
    "CostosTotalesCalculator",
    "KPIsCalculator",
    "PyGCalculator",
]
