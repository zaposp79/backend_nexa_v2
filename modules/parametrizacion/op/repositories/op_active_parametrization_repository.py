"""Repositorio de lectura OP: lee la parametrización OP activa vía DocumentStore."""

from __future__ import annotations

from typing import Any, Dict

from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.parametrizacion.op.mappers.op_version_document_codec import (
    OPVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.op.repositories.collections import (
    OP_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.shared.infrastructure.json_store import read_json
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)
from nexa_engine.modules.shared.exceptions import ParametrizationNotFoundError
from nexa_engine.modules.shared.config.config import OP_DIR


class OPActiveParametrizationRepository:
    """Lee la data de parametrización OP activa."""

    def __init__(self, store: DocumentStore, version_index: VersionIndexRepository) -> None:
        self._store = store
        self._codec = OPVersionDocumentCodec()
        self._version_index = version_index

    def get_active_data(self) -> Dict[str, Any]:
        active = self._version_index.get_active()
        if active is not None:
            record = self._store.get_record(OP_PARAMETRIZATION_COLLECTION, active.version_id)
            if record is not None:
                data = self._codec.decode(record)
                if "version_id" not in data:
                    data = {**data, "version_id": active.version_id}
                return data
            if not active.path:
                raise ParametrizationNotFoundError("op", active.version_id)
            data_path = (OP_DIR / active.path).resolve()
            return read_json(data_path)  # type: ignore[return-value]

        # Fallback: query directa cuando el índice 'versions' no existe en Cosmos
        try:
            docs, _ = self._store.query(
                OP_PARAMETRIZATION_COLLECTION,
                {"domain": "op", "status": "active"},
            )
            if docs:
                doc = docs[0]
                payload = doc.get("payload")
                if isinstance(payload, dict):
                    if "version_id" not in payload:
                        payload = {**payload, "version_id": doc.get("id", "unknown")}
                    return payload
        except Exception:
            pass

        raise ParametrizationNotFoundError("op", None)


__all__ = ["OPActiveParametrizationRepository"]
