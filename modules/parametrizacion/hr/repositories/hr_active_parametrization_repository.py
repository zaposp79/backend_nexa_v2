"""Repositorio de lectura HR: lee la parametrización activa vía DocumentStore.

Usa VersionIndexRepository para el índice de versiones (formato encapsulado).
Usa DocumentStore.get_record para data de versión y conserva read_json solo
como fallback legacy para archivos con path override (../v2-7/hr.json).
"""

from __future__ import annotations

from typing import Any, Dict

from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.parametrizacion.hr.mappers.hr_version_document_codec import (
    HRVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.hr.repositories.collections import (
    HR_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.shared.infrastructure.json_store import read_json
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)
from nexa_engine.modules.shared.exceptions import ParametrizationNotFoundError
from nexa_engine.modules.shared.config.config import HR_DIR


class HRActiveParametrizationRepository:
    """Lee la data de parametrización HR activa."""

    def __init__(self, store: DocumentStore, version_index: VersionIndexRepository) -> None:
        self._store = store
        self._codec = HRVersionDocumentCodec()
        self._version_index = version_index

    def get_active_data(self) -> Dict[str, Any]:
        active = self._version_index.get_active()
        if active is None:
            raise ParametrizationNotFoundError("hr", None)
        record = self._store.get_record(HR_PARAMETRIZATION_COLLECTION, active.version_id)
        if record is not None:
            return self._codec.decode(record)
        if not active.path:
            raise ParametrizationNotFoundError("hr", active.version_id)
        data_path = (HR_DIR / active.path).resolve()
        return read_json(data_path)  # type: ignore[return-value]


__all__ = ["HRActiveParametrizationRepository"]
