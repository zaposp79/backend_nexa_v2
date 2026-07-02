"""Repositorio específico de HR."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from nexa_engine.db.exceptions import DbNotFoundError
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.parametrizacion.hr.mappers.hr_version_document_codec import (
    HRVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.hr.repositories.collections import (
    HR_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)
from nexa_engine.modules.parametrizacion.shared.repositories.version_payload_persistence import (
    save_version_payload_and_index,
)
from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.parametrizacion.shared.models.version_summary import VersionSummary


class HRRepository:
    """Persistencia semántica de versiones HR."""

    def __init__(
        self,
        store: DocumentStore,
        version_index_repository: VersionIndexRepository,
        codec: HRVersionDocumentCodec,
    ) -> None:
        self._store = store
        self._version_index_repository = version_index_repository
        self._codec = codec

    def save_version(self, summary: VersionSummary, data: dict, metadata: dict | None = None) -> str:
        """Guarda una versión HR y actualiza el índice con compensación."""
        previously_active = self._version_index_repository.get_active()
        record = self._codec.encode(data, doc_id=summary.version_id, root_metadata=metadata)
        save_version_payload_and_index(
            store=self._store,
            collection=HR_PARAMETRIZATION_COLLECTION,
            version_index_repository=self._version_index_repository,
            payload_record=record,
            summary=summary,
        )
        if previously_active and previously_active.version_id != summary.version_id:
            self._deactivate_in_store(previously_active.version_id)
        return summary.version_id

    def list_versions(self) -> List[VersionSummary]:
        return self._version_index_repository.list_versions()

    def get_version(self, version_id: str) -> dict:
        record = self._store.get_record(HR_PARAMETRIZATION_COLLECTION, version_id)
        if record is None:
            raise NotFoundError("version", version_id)
        return self._codec.decode(record)

    def get_summary(self, version_id: str) -> VersionSummary:
        return self._version_index_repository.get_version(version_id)

    def activate_version(self, version_id: str) -> VersionSummary:
        currently_active = self._version_index_repository.get_active()
        result = self._version_index_repository.activate(version_id)
        if currently_active and currently_active.version_id != version_id:
            self._deactivate_in_store(currently_active.version_id)
        self._activate_in_store(version_id)
        return result

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
            self._store.delete(HR_PARAMETRIZATION_COLLECTION, version_id)
        except DbNotFoundError:
            return

    def _deactivate_in_store(self, version_id: str) -> None:
        try:
            record = self._store.get_record(HR_PARAMETRIZATION_COLLECTION, version_id)
            if record is None:
                return
            updated_meta = {**record.root_metadata, "status": "inactive"} if record.root_metadata else {"status": "inactive"}
            updated = StoredDocument(
                id=record.id,
                payload=record.payload,
                partition_value=record.partition_value,
                etag=record.etag,
                root_metadata=updated_meta,
            )
            self._store.upsert_record(HR_PARAMETRIZATION_COLLECTION, updated)
        except Exception:
            pass

    def _activate_in_store(self, version_id: str) -> None:
        try:
            record = self._store.get_record(HR_PARAMETRIZATION_COLLECTION, version_id)
            if record is None:
                return
            updated_meta = {**record.root_metadata, "status": "active"} if record.root_metadata else {"status": "active"}
            updated = StoredDocument(
                id=record.id,
                payload=record.payload,
                partition_value=record.partition_value,
                etag=record.etag,
                root_metadata=updated_meta,
            )
            self._store.upsert_record(HR_PARAMETRIZATION_COLLECTION, updated)
        except Exception:
            pass
