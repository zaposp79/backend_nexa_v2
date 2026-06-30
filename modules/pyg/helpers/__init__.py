"""Backward compatibility shim for vision_pyg helpers.

DEPRECATED: Import from nexa_engine.modules.vision_pyg.helpers instead.
This module re-exports for backward compatibility only.
"""
from __future__ import annotations

from nexa_engine.modules.vision_pyg.helpers.screen_mapper import (
    build_vision_pyg_from_result,
)

__all__ = [
    "build_vision_pyg_from_result",
]
