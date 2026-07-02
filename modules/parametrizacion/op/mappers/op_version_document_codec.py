from __future__ import annotations

import copy
from typing import Any

from nexa_engine.db.models.stored_document import StoredDocument


class OPVersionDocumentCodec:
    """Codec para payloads de versión OP sin filtrar metadata técnica."""

    def encode(self, payload: dict[str, Any], doc_id: str | None = None, root_metadata: dict | None = None) -> StoredDocument:
        cosmos_id = doc_id if doc_id is not None else payload["version_id"]
        return StoredDocument(id=str(cosmos_id), payload=copy.deepcopy(payload), root_metadata=root_metadata)

    def decode(self, record: StoredDocument) -> dict[str, Any]:
        if not isinstance(record.payload, dict):
            raise TypeError("La carga útil de la versión OP debe ser un diccionario")
        return copy.deepcopy(record.payload)


__all__ = ["OPVersionDocumentCodec"]
