"""Logical collection configuration.

A :class:`CollectionConfig` describes a *logical* collection of the domain — a
named bucket of documents — independently of how the active backend stores it
(a directory of JSON files, a Cosmos container partition, ...).

Design rules (FASE 3):
  * ``name`` is a logical domain collection name, NOT derived from a JSON
    filename.
  * ``partition_key_field``, when set, names a first-level document field the
    provider must validate is present on every persisted document.
  * Every persisted document must carry an ``id`` field; providers raise
    :class:`DbSerializationError` when ``id`` or a required partition key is
    missing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CollectionConfig:
    """Immutable description of a logical collection.

    Attributes:
        name: Logical collection name (e.g. ``"simulation_results"``). Must be
            a stable identifier safe to use as a directory/container segment.
        partition_key_field: Optional name of a first-level document field used
            as the partition key. When provided, providers validate the field
            is present on every document and may use it to scope reads/writes.
    """

    name: str
    partition_key_field: str | None = None

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise ValueError("CollectionConfig.name must be a non-empty string")
        # Keep names filesystem- and container-safe without inventing schemas:
        # disallow path separators that would let a collection escape its root.
        if "/" in self.name or "\\" in self.name or self.name in (".", ".."):
            raise ValueError(f"CollectionConfig.name is not a safe identifier: {self.name!r}")


__all__ = ["CollectionConfig"]
