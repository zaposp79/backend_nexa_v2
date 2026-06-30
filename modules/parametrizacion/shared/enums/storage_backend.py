"""Storage backend enum for parametrization repository selection."""
from __future__ import annotations
from enum import Enum


class StorageBackend(str, Enum):
    JSON  = "json"
    COSMOS = "cosmos"


__all__ = ["StorageBackend"]
