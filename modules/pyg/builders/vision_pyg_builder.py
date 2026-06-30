"""Backward compatibility shim for vision_pyg builder.

DEPRECATED: Import from nexa_engine.modules.vision_pyg.builders.vision_pyg_builder instead.
"""
from nexa_engine.modules.vision_pyg.builders.vision_pyg_builder import (
    VisionPyGBuilder,
    _ROW_DEFINITIONS,
)

__all__ = [
    "VisionPyGBuilder",
    "_ROW_DEFINITIONS",
]
