"""Repositorio específico de GN."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from nexa_engine.db.exceptions import DbNotFoundError
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.parametrizacion.gn.mappers.gn_version_document_codec import (
    GNVersionDocumentCodec,
)
from nexa_engine.modules.parametrizacion.gn.repositories.collections import (
    GN_PARAMETRIZATION_COLLECTION,
)
from nexa_engine.modules.parametrizacion.shared.repositories.version_index_repository import (
    VersionIndexRepository,
)
from nexa_engine.modules.parametrizacion.shared.repositories.version_payload_persistence import (
    save_version_payload_and_index,
)
from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.parametrizacion.shared.models.version_summary import VersionSummary


class GNRepository:
    """Persistencia semántica de versiones GN."""

    def __init__(
        self,
        store: DocumentStore,
        version_index_repository: VersionIndexRepository,
        codec: GNVersionDocumentCodec,
    ) -> None:
        self._store = store
        self._version_index_repository = version_index_repository
        self._codec = codec

    def save_version(self, summary: VersionSummary, data: dict, metadata: dict | None = None) -> str:
        """Guarda una versión GN y actualiza el índice con compensación."""
        previously_active = self._version_index_repository.get_active()
        record = self._codec.encode(data, doc_id=summary.version_id, root_metadata=metadata)
        save_version_payload_and_index(
            store=self._store,
            collection=GN_PARAMETRIZATION_COLLECTION,
            version_index_repository=self._version_index_repository,
            payload_record=record,
            summary=summary,
        )
        if previously_active and previously_active.version_id != summary.version_id:
            self._deactivate_in_store(previously_active.version_id)
        return summary.version_id

    def list_versions(self) -> List[VersionSummary]:
        """Lista versiones consultando Cosmos por domain, con fallback a índice filesystem."""
        domain_name = GN_PARAMETRIZATION_COLLECTION.name

        try:
            docs, _ = self._store.query(
                GN_PARAMETRIZATION_COLLECTION, {"domain": domain_name}
            )
            if docs:
                summaries = []
                for doc in docs:
                    doc_id = str(doc.get("id", ""))
                    if not doc_id:
                        continue
                    summaries.append(VersionSummary(
                        version_id=doc_id,
                        filename=doc.get("file_name", ""),
                        uploaded_at=doc.get("created_at", ""),
                        is_active=doc.get("status") == "active",
                        sheet_count=doc.get("sheet_count", 0),
                        total_rows=doc.get("total_rows", 0),
                        display_version_id=doc.get("version_id"),
                        sheets_found=doc.get("sheets_found", []),
                    ))
                if summaries:
                    return summaries
        except Exception:
            pass

        # Fallback: índice filesystem (solo DB_PROVIDER=json local)
        return self._version_index_repository.list_versions()

    def get_version(self, version_id: str) -> dict:
        record = self._store.get_record(GN_PARAMETRIZATION_COLLECTION, version_id)
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

    def delete_version(self, version_id: str) -> None:
        try:
            self._store.delete(GN_PARAMETRIZATION_COLLECTION, version_id)
        except DbNotFoundError:
            raise NotFoundError("version", version_id)
        try:
            self._version_index_repository.remove(version_id)
        except Exception:
            pass

    def get_active_version(self) -> Optional[VersionSummary]:
        return self._version_index_repository.get_active()

    def get_active(self) -> Optional[VersionSummary]:
        return self.get_active_version()

    def get_active_record(self) -> tuple[Optional[VersionSummary], Optional[dict]]:
        """Obtiene el documento activo consultando Cosmos por domain + status='active'.

        Estrategia:
        1. query(domain=gn, status=active)  — consulta directa Cosmos (principal)
        2. índice filesystem               — fallback solo para DB_PROVIDER=json local
        3. query(domain=gn)                — Cosmos fallback para docs sin campo status
        """
        domain_name = GN_PARAMETRIZATION_COLLECTION.name  # "gn"
        _sys_keys = {"id", "domain", "payload", "_rid", "_self", "_etag", "_attachments", "_ts"}

        def _summary_from_doc(doc: dict) -> tuple[Optional[VersionSummary], Optional[dict]]:
            doc_id = str(doc.get("id", ""))
            payload = doc.get("payload")
            if not isinstance(payload, dict) or not doc_id:
                return None, None
            meta = {k: v for k, v in doc.items() if k not in _sys_keys}
            summary = VersionSummary(
                version_id=doc_id,
                filename=meta.get("file_name", ""),
                uploaded_at=meta.get("created_at", ""),
                is_active=True,
                sheet_count=meta.get("sheet_count", 0),
                total_rows=meta.get("total_rows", 0),
                display_version_id=meta.get("version_id"),
                sheets_found=meta.get("sheets_found", []),
            )
            return summary, payload

        # Step 1: Cosmos — WHERE domain='gn' AND status='active'
        try:
            docs, _ = self._store.query(
                GN_PARAMETRIZATION_COLLECTION, {"domain": domain_name, "status": "active"}
            )
            if docs:
                result = _summary_from_doc(docs[0])
                if result[0] is not None:
                    return result
        except Exception:
            pass

        # Step 2: índice filesystem (solo DB_PROVIDER=json en local)
        try:
            active_summary = self._version_index_repository.get_active()
            if active_summary is not None:
                record = self._store.get_record(GN_PARAMETRIZATION_COLLECTION, active_summary.version_id)
                if record is not None:
                    return active_summary, self._codec.decode(record)
        except Exception:
            pass

        # Step 3: Cosmos fallback — WHERE domain='gn' (docs sin campo status)
        try:
            docs, _ = self._store.query(GN_PARAMETRIZATION_COLLECTION, {"domain": domain_name})
            if docs:
                best = max(docs, key=lambda d: d.get("created_at", ""))
                result = _summary_from_doc(best)
                if result[0] is not None:
                    return result
        except Exception:
            pass

        return None, None

    @staticmethod
    def new_version_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def now_iso() -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _delete_record_if_present(self, version_id: str) -> None:
        try:
            self._store.delete(GN_PARAMETRIZATION_COLLECTION, version_id)
        except DbNotFoundError:
            return

    def _deactivate_in_store(self, version_id: str) -> None:
        try:
            record = self._store.get_record(GN_PARAMETRIZATION_COLLECTION, version_id)
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
            self._store.upsert_record(GN_PARAMETRIZATION_COLLECTION, updated)
        except Exception:
            pass

    def _activate_in_store(self, version_id: str) -> None:
        try:
            record = self._store.get_record(GN_PARAMETRIZATION_COLLECTION, version_id)
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
            self._store.upsert_record(GN_PARAMETRIZATION_COLLECTION, updated)
        except Exception:
            pass
