"""Backward compatibility shim for vision_pyg API.

DEPRECATED: Import from nexa_engine.modules.vision_pyg.api instead.
"""
from nexa_engine.modules.vision_pyg.api.vision_router import (
    get_vision_pyg,
    router,
)

__all__ = [
    "router",
    "get_vision_pyg",
]
