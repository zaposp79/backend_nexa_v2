"""Repositorio específico de OP."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from nexa_engine.db.exceptions import DbNotFoundError
from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.parametrizacion.op.mappers.op_version_document_codec import (
    OPVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.op.repositories.collections import (
    OP_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)
from nexa_engine.modules.parametrizacion.shared.repositories.version_payload_persistence import (
    save_version_payload_and_index,
)
from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.parametrizacion.shared.models.version_summary import VersionSummary


class OPRepository:
    """Persistencia semántica de versiones OP."""

    def __init__(
        self,
        store: DocumentStore,
        version_index_repository: VersionIndexRepository,
        codec: OPVersionDocumentCodec,
    ) -> None:
        self._store = store
        self._version_index_repository = version_index_repository
        self._codec = codec

    def save_version(self, summary: VersionSummary, data: dict) -> str:
        """Guarda una versión OP y actualiza el índice con compensación."""
        record = self._codec.encode(data)
        save_version_payload_and_index(
            store=self._store,
            collection=OP_PARAMETRIZATION_COLLECTION,
            version_index_repository=self._version_index_repository,
            payload_record=record,
            summary=summary,
        )
        return summary.version_id

    def list_versions(self) -> List[VersionSummary]:
        return self._version_index_repository.list_versions()

    def get_version(self, version_id: str) -> dict:
        record = self._store.get_record(OP_PARAMETRIZATION_COLLECTION, version_id)
        if record is None:
            raise NotFoundError("version", version_id)
        return self._codec.decode(record)

    def get_summary(self, version_id: str) -> VersionSummary:
        return self._version_index_repository.get_version(version_id)

    def activate_version(self, version_id: str) -> VersionSummary:
        return self._version_index_repository.activate(version_id)

    def set_active(self, version_id: str) -> VersionSummary:
        return self.activate_version(version_id)

    def delete_version(self, version_id: str) -> None:
        self._delete_record_if_present(version_id)
        self._version_index_repository.remove(version_id)

    def get_active_version(self) -> Optional[VersionSummary]:
        return self._version_index_repository.get_active()

    def get_active(self) -> Optional[VersionSummary]:
        return self.get_active_version()

    @staticmethod
    def new_version_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def now_iso() -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _delete_record_if_present(self, version_id: str) -> None:
        try:
            self._store.delete(OP_PARAMETRIZATION_COLLECTION, version_id)
        except DbNotFoundError:
            return
