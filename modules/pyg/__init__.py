"""Backward compatibility shim for vision_pyg.

DEPRECATED: Import from nexa_engine.modules.vision_pyg instead.
This module re-exports for backward compatibility only.
"""
from __future__ import annotations

from nexa_engine.modules.vision_pyg import (
    builders,
    services,
    models,
    api,
    helpers,
)

__all__ = [
    "builders",
    "services",
    "models",
    "api",
    "helpers",
]
