"""Backward compatibility shim for vision_pyg builders.

DEPRECATED: Import from nexa_engine.modules.vision_pyg.builders instead.
"""
from nexa_engine.modules.vision_pyg.builders import (
    VisionPyGBuilder,
    _ROW_DEFINITIONS,
)

__all__ = [
    "VisionPyGBuilder",
    "_ROW_DEFINITIONS",
]
