"""Repositorio específico de GN."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
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
from nexa_engine.modules.shared.exceptions import NotFoundError, ValidationError
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
        """Guarda una versión GN con status=active y desactiva la versión activa anterior.

        La búsqueda de registros activos previos se hace via query directa al store
        (domain=gn, status=active) para que funcione tanto con Cosmos como con JSON store.
        """
        domain_name = GN_PARAMETRIZATION_COLLECTION.name  # "gn"

        # 1. Buscar IDs activos ANTES de guardar el nuevo (query directa al store)
        previously_active_ids = self._query_active_ids(domain_name)

        # 2. Embeber status y domain en el payload
        status = (metadata or {}).get("status", "active")
        data_to_store = {
            **data,
            "status": status,
            "domain": domain_name,
        } if isinstance(data, dict) else data

        record = self._codec.encode(data_to_store, doc_id=summary.version_id, root_metadata=metadata)
        save_version_payload_and_index(
            store=self._store,
            collection=GN_PARAMETRIZATION_COLLECTION,
            version_index_repository=self._version_index_repository,
            payload_record=record,
            summary=summary,
        )

        # 3. Desactivar todos los registros que estaban activos antes del nuevo
        for vid in previously_active_ids:
            if vid != summary.version_id:
                self._deactivate_in_store(vid)

        return summary.version_id

    def _query_active_ids(self, domain_name: str) -> list:
        """Retorna IDs de versiones activas consultando el store directamente.

        Estrategia:
        1. query(domain=gn, status=active) — funciona en Cosmos y JSON store (con domain en payload)
        2. Fallback al índice filesystem — para registros legacy sin campo 'domain' en payload
        """
        try:
            docs, _ = self._store.query(
                GN_PARAMETRIZATION_COLLECTION,
                {"domain": domain_name, "status": "active"},
            )
            ids = [str(d.get("id", "")) for d in (docs or []) if d.get("id")]
            if ids:
                return ids
        except Exception:
            pass
        # Fallback: índice filesystem (registros sin campo 'domain' en payload)
        try:
            active = self._version_index_repository.get_active()
            if active:
                return [active.version_id]
        except Exception:
            pass
        return []

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

    def get_document_raw(self, version_id: str) -> dict:
        """Obtiene el documento completo de Cosmos filtrando por domain='gn' e id."""
        domain_name = GN_PARAMETRIZATION_COLLECTION.name
        _sys_keys = {"_rid", "_self", "_etag", "_attachments", "_ts"}
        docs, _ = self._store.query(
            GN_PARAMETRIZATION_COLLECTION, {"domain": domain_name, "id": version_id}
        )
        if not docs:
            raise NotFoundError("version", version_id)
        return {k: v for k, v in docs[0].items() if k not in _sys_keys}

    def get_summary(self, version_id: str) -> VersionSummary:
        return self._version_index_repository.get_version(version_id)

    def activate_version(self, version_id: str) -> VersionSummary:
        """Activa la versión indicada en Cosmos y desactiva todas las demás del mismo domain."""
        try:
            if uuid.UUID(version_id).version != 4:
                raise ValueError
        except (ValueError, AttributeError):
            raise ValidationError("El parámetro 'id' debe ser un UUID versión 4 válido.")

        domain_name = GN_PARAMETRIZATION_COLLECTION.name
        _sys_keys = {"id", "domain", "payload", "_rid", "_self", "_etag", "_attachments", "_ts"}

        docs, _ = self._store.query(GN_PARAMETRIZATION_COLLECTION, {"domain": domain_name})
        target_doc = next((d for d in docs if str(d.get("id", "")) == version_id), None)
        if target_doc is None:
            raise NotFoundError("version", version_id)

        self._activate_in_store(version_id)
        for doc in docs:
            other_id = str(doc.get("id", ""))
            if other_id and other_id != version_id:
                self._deactivate_in_store(other_id)

        try:
            self._version_index_repository.activate(version_id)
        except Exception:
            pass

        meta = {k: v for k, v in target_doc.items() if k not in _sys_keys}
        return VersionSummary(
            version_id=version_id,
            filename=meta.get("file_name", ""),
            uploaded_at=meta.get("created_at", ""),
            is_active=True,
            sheet_count=meta.get("sheet_count", 0),
            total_rows=meta.get("total_rows", 0),
            display_version_id=meta.get("version_id"),
            sheets_found=meta.get("sheets_found", []),
        )

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
        return datetime.now(timezone.utc).isoformat()

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
            domain_name = GN_PARAMETRIZATION_COLLECTION.name
            updated_payload = {
                **record.payload,
                "status": "inactive",
                "domain": domain_name,
            } if isinstance(record.payload, dict) else record.payload
            updated_meta = {**record.root_metadata, "status": "inactive"} if record.root_metadata else {"status": "inactive"}
            updated = StoredDocument(
                id=record.id,
                payload=updated_payload,
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
            domain_name = GN_PARAMETRIZATION_COLLECTION.name
            updated_payload = {
                **record.payload,
                "status": "active",
                "domain": domain_name,
            } if isinstance(record.payload, dict) else record.payload
            updated_meta = {**record.root_metadata, "status": "active"} if record.root_metadata else {"status": "active"}
            updated = StoredDocument(
                id=record.id,
                payload=updated_payload,
                partition_value=record.partition_value,
                etag=record.etag,
                root_metadata=updated_meta,
            )
            self._store.upsert_record(GN_PARAMETRIZATION_COLLECTION, updated)
        except Exception:
            pass
