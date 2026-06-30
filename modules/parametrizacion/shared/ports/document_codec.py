"""Codecs del repositorio entre valores de dominio y registros StoredDocument."""

from __future__ import annotations

from typing import Protocol, TypeVar

from nexa_engine.db.models.stored_document import StoredDocument

T = TypeVar("T")


class DocumentCodec(Protocol[T]):
    def encode(self, value: T) -> StoredDocument:
        ...

    def decode(self, record: StoredDocument) -> T:
        ...


__all__ = ["DocumentCodec"]
