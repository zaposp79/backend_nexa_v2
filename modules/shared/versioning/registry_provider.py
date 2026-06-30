"""Shared VersionRegistry singleton for the process lifetime.

Lives in modules/shared/versioning/ to avoid circular imports — this module
has no project-level dependencies (only stdlib via version_registry.py).

Consumers:
  - modules/calculator/api/calculate_normal_handler.py  (reads current metadata)
  - modules/parametrizacion/*/api/router.py             (invalidates on activate)
"""
from __future__ import annotations

from nexa_engine.modules.shared.versioning.version_registry import VersionRegistry

_version_registry = VersionRegistry()

__all__ = ["_version_registry"]
