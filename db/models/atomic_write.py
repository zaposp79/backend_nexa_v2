"""Modelos técnicos para escrituras atómicas de documentos."""

from __future__ import annotations

from dataclasses import dataclass

from nexa_engine.db.models.stored_document import StoredDocument


@dataclass(frozen=True)
class AtomicWritePrecondition:
    """Precondición optimista para un registro dentro del batch."""

    logical_id: str
    expected_etag: str


@dataclass(frozen=True)
class AtomicWriteResult:
    """Resultado de un batch atómico de registros."""

    records: tuple[StoredDocument, ...]


__all__ = ["AtomicWritePrecondition", "AtomicWriteResult"]
