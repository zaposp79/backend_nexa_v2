from __future__ import annotations

import copy
from typing import Any

from nexa_engine.db.models.stored_document import StoredDocument


class OPVersionDocumentCodec:
    """Codec para payloads de versión OP sin filtrar metadata técnica."""

    def encode(self, payload: dict[str, Any]) -> StoredDocument:
        version_id = payload["version_id"]
        return StoredDocument(id=str(version_id), payload=copy.deepcopy(payload))

    def decode(self, record: StoredDocument) -> dict[str, Any]:
        if not isinstance(record.payload, dict):
            raise TypeError("La carga útil de la versión OP debe ser un diccionario")
        return copy.deepcopy(record.payload)


__all__ = ["OPVersionDocumentCodec"]
