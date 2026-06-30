"""Repositorio de lectura GN: lee la parametrización GN activa vía DocumentStore."""

from __future__ import annotations

from typing import Any, Dict

from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.parametrizacion.gn.mappers.gn_version_document_codec import (
    GNVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.gn.repositories.collections import (
    GN_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.shared.infrastructure.json_store import read_json
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)
from nexa_engine.modules.shared.exceptions import ParametrizationNotFoundError
from nexa_engine.modules.shared.config.config import GN_DIR


class GNActiveParametrizationRepository:
    """Lee la data de parametrización GN activa."""

    def __init__(self, store: DocumentStore) -> None:
        self._store = store
        self._codec = GNVersionDocumentCodec()
        self._version_index = VersionIndexRepository(store=store, collection=GN_PARAMETRIZATION_COLLECTION)

    def get_active_data(self) -> Dict[str, Any]:
        active = self._version_index.get_active()
        if active is None:
            raise ParametrizationNotFoundError("gn", None)
        record = self._store.get_record(GN_PARAMETRIZATION_COLLECTION, active.version_id)
        if record is not None:
            return self._codec.decode(record)
        if not active.path:
            raise ParametrizationNotFoundError("gn", active.version_id)
        data_path = (GN_DIR / active.path).resolve()
        return read_json(data_path)  # type: ignore[return-value]


__all__ = ["GNActiveParametrizationRepository"]
