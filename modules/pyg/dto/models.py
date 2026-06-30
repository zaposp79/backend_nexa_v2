"""Backward compatibility shim for vision_pyg models.

DEPRECATED: Import from nexa_engine.modules.vision_pyg.models instead.
"""
from nexa_engine.modules.vision_pyg.models import (
    VisionPyGRow,
    VisionPyGRowDetalle,
    ResumenEjecutivoPyG,
    VisionPyG,
)

__all__ = [
    "VisionPyGRow",
    "VisionPyGRowDetalle",
    "ResumenEjecutivoPyG",
    "VisionPyG",
]
