"""Backward compatibility shim for vision_pyg router.

DEPRECATED: Import from nexa_engine.modules.vision_pyg.api.vision_router instead.
This module re-exports for backward compatibility only.
"""
from __future__ import annotations

from nexa_engine.modules.vision_pyg.api.vision_router import (
    router,
    get_vision_pyg,
)

__all__ = [
    "router",
    "get_vision_pyg",
]
