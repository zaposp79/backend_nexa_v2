"""VersionIndexRepository: encapsula el índice versions.json por dominio de parametrización.

Es dueño del formato versions.json basado en lista usado por HR, GN y OP:
    [{version_id, filename, uploaded_at, is_active, sheet_count, total_rows, path?}, ...]

Las reglas de negocio usan otro formato; BusinessRulesRepository es dueño de ese contrato.

Compatibilidad con DocumentStore:
  El formato de lista se conserva como payload lógico completo. Cuando el
  repositorio recibe `store + collection`, usa VersionIndexDocumentCodec para
  persistir esa lista como `versions.json` mediante DocumentStore, sin convertirla
  a un objeto ni agregar `id` dentro del payload.

  DocumentStore se acepta en el constructor para:
    * cumplir DI
    * escribir `versions.json` por `upsert_record`
    * mantener read_json/write_json solo cuando se recibe `domain_dir` legacy

Este es el ÚNICO lugar del código que conoce el formato versions.json basado en lista.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.db.models.stored_document import StoredDocument
from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.parametrizacion.shared.mappers.version_index_document_codec import (
    VersionIndexDocumentCodec,
)
from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.shared.config.config import PARAMETRIZATION_DIR
from nexa_engine.modules.parametrizacion.shared.models.version_summary import (
    VERSIONS_FILE,
    VersionSummary,
)
from nexa_engine.modules.parametrizacion.shared.infrastructure.json_store import (
    read_json,
    write_json,
)


class VersionIndexRepository:
    """Administra el índice de versiones basado en lista para un dominio."""

    def __init__(
        self,
        store: DocumentStore | None,
        domain_dir: Path | None = None,
        collection: CollectionConfig | None = None,
    ) -> None:
        if domain_dir is None and collection is None:
            raise ValueError("VersionIndexRepository requires domain_dir or collection")
        self._store = store
        self._collection = collection
        self._dir = domain_dir or PARAMETRIZATION_DIR / collection.name  # type: ignore[union-attr]
        self._path = self._dir / VERSIONS_FILE
        self._codec = VersionIndexDocumentCodec(
            self._collection.name if self._collection is not None else self._dir.name,
            record_id=Path(VERSIONS_FILE).stem,
        )

    @property
    def index_store(self) -> object | None:
        """Devuelve el store que usa este índice, o None si usa filesystem."""
        return self._store

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def get_active(self) -> Optional[VersionSummary]:
        """Retorna el resumen de versión activa, o None si ninguna está activa."""
        for entry in self._load():
            if entry.get("is_active"):
                return VersionSummary.from_dict(entry)
        return None

    def list_versions(self) -> List[VersionSummary]:
        """Retorna todas las versiones ordenadas por fecha de carga descendente."""
        summaries = [VersionSummary.from_dict(d) for d in self._load()]
        return sorted(summaries, key=lambda s: s.uploaded_at, reverse=True)

    def get_version(self, version_id: str) -> VersionSummary:
        for entry in self._load():
            if entry.get("version_id") == version_id:
                return VersionSummary.from_dict(entry)
        raise NotFoundError("version", version_id)

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def append(self, summary: VersionSummary) -> None:
        """Agrega una nueva versión y la activa, desactivando las demás."""
        self.save_record(self.build_append_record(summary))

    def build_append_record(self, summary: VersionSummary) -> StoredDocument:
        """Construye el registro `versions` actualizado sin persistirlo."""
        loaded_record = self._load_record()
        raw = self._decode_loaded_record(loaded_record)
        for v in raw:
            v["is_active"] = False
        summary.is_active = True
        raw.append(summary.to_dict())
        encoded = self._codec.encode(raw)
        return StoredDocument(
            id=encoded.id,
            payload=encoded.payload,
            partition_value=encoded.partition_value,
            etag=loaded_record.etag if loaded_record is not None else None,
        )

    def save_record(self, record: StoredDocument) -> None:
        """Persiste un registro de índice ya construido."""
        if self._store is not None and self._collection is not None:
            self._store.upsert_record(self._collection, record)
            return
        self._save(self._codec.decode(record))

    def activate(self, version_id: str) -> VersionSummary:
        """Marca *version_id* como activa y desactiva las demás."""
        raw = self._load()
        found = False
        for v in raw:
            if v.get("version_id") == version_id:
                v["is_active"] = True
                found = True
            else:
                v["is_active"] = False
        if not found:
            raise NotFoundError("version", version_id)
        self._save(raw)
        return self.get_version(version_id)

    def remove(self, version_id: str) -> None:
        """Elimina una versión del índice."""
        raw = self._load()
        new_raw = [v for v in raw if v.get("version_id") != version_id]
        if len(new_raw) == len(raw):
            raise NotFoundError("version", version_id)
        self._save(new_raw)

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _load(self) -> List[dict]:
        return self._decode_loaded_record(self._load_record())

    def _load_record(self) -> StoredDocument | None:
        if self._store is not None and self._collection is not None:
            record = self._store.get_record(self._collection, Path(VERSIONS_FILE).stem)
            if record is None:
                return None
            return record
        raw = read_json(self._path)
        payload = raw if isinstance(raw, list) else []
        return self._codec.encode(payload)

    def _decode_loaded_record(self, record: StoredDocument | None) -> List[dict]:
        if record is None:
            return []
        return self._codec.decode(record)

    def _save(self, versions: List[dict]) -> None:
        if self._store is not None and self._collection is not None:
            self._store.upsert_record(self._collection, self._codec.encode(versions))
            return
        write_json(self._path, versions)


__all__ = ["VersionIndexRepository"]
