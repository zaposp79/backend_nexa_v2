from __future__ import annotations

import copy
from typing import Any

from nexa_engine.db.models.stored_document import StoredDocument


class HRVersionDocumentCodec:
    """Codec para payloads de versión HR sin filtrar metadata técnica."""

    def encode(self, payload: dict[str, Any]) -> StoredDocument:
        version_id = payload["version_id"]
        return StoredDocument(id=str(version_id), payload=copy.deepcopy(payload))

    def decode(self, record: StoredDocument) -> dict[str, Any]:
        if not isinstance(record.payload, dict):
            raise TypeError("HR version payload must be a dict")
        return copy.deepcopy(record.payload)


__all__ = ["HRVersionDocumentCodec"]
