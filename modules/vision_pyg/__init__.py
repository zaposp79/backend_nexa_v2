"""Canonical Vision P&G module.

modules/vision_pyg owns the implementation for:
  - builders
  - services
  - models
  - helpers
  - API endpoints

modules/pyg remains only as backward-compatibility shim.
"""

from __future__ import annotations

from nexa_engine.modules.vision_pyg import api, builders, helpers, models, services

__all__ = [
    "api",
    "builders",
    "helpers",
    "models",
    "services",
]
