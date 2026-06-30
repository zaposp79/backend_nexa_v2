from __future__ import annotations

import copy

from nexa_engine.db.models.stored_document import StoredDocument


class VersionIndexDocumentCodec:
    """Codec para el payload legacy de versions.json basado en lista."""

    def __init__(self, domain: str, record_id: str | None = None) -> None:
        if not domain:
            raise ValueError("domain is required")
        self._domain = domain
        self._record_id = record_id or f"{domain}-versions-index"

    def encode(self, versions: list[dict]) -> StoredDocument:
        return StoredDocument(
            id=self._record_id,
            payload=copy.deepcopy(versions),
            partition_value=self._domain,
        )

    def decode(self, record: StoredDocument) -> list[dict]:
        if not isinstance(record.payload, list):
            raise TypeError("version index payload must be a list")
        return copy.deepcopy(record.payload)


__all__ = ["VersionIndexDocumentCodec"]
