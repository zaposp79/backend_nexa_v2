"""infrastructure.certification.certificate_repository
========================================================

JSON-file persistence for ``ExecutionCertificate``.

Storage layout::

    storage/
      certificates/
        <certificate_id>.json
        index.json            # maps simulation_id → certificate_id

Files are deterministic (``sort_keys=True``, fixed indent). Read paths
are idempotent.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.modules.certification.models import ExecutionCertificate


class CertificateRepository:
    """Read/write ``ExecutionCertificate`` artefacts.

    ``store`` es aceptado por constructor para cumplir el contrato de inyección
    de dependencias (FASE DB.2). La implementación interna sigue siendo
    Path-based porque el layout usa ``{id}.json`` + ``index.json`` (dos tipos
    de archivo con semántica distinta). Migración interna POSTPONED (FASE 13
    batch certificación).
    """

    def __init__(
        self,
        store: DocumentStore | None = None,
        root: Optional[Path] = None,
    ) -> None:
        self._store = store  # reserved for future internal migration
        if root is None:
            root = Path(os.getcwd()) / "storage"
        # ``root`` points at the top-level storage dir; cert files live in
        # ``<root>/certificates/`` so other tests can inject their own root.
        self._root = Path(root) / "certificates"
        self._index_path = self._root / "index.json"

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def save(self, cert: ExecutionCertificate) -> Path:
        self._root.mkdir(parents=True, exist_ok=True)
        path = self._path_for(cert.certificate_id)
        text = json.dumps(cert.to_dict(), sort_keys=True, indent=2)
        path.write_text(text, encoding="utf-8")
        self._update_index(cert)
        return path

    def load(self, certificate_id: str) -> ExecutionCertificate:
        path = self._path_for(certificate_id)
        if not path.exists():
            raise FileNotFoundError(
                f"Certificate not found: certificate_id={certificate_id!r}"
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        return ExecutionCertificate.from_dict(data)

    def exists(self, certificate_id: str) -> bool:
        return self._path_for(certificate_id).exists()

    def list_recent(self, limit: int = 50) -> List[ExecutionCertificate]:
        if not self._root.exists():
            return []
        files = [
            p
            for p in self._root.iterdir()
            if p.is_file()
            and p.suffix == ".json"
            and p.name != "index.json"
        ]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        items: List[ExecutionCertificate] = []
        for f in files[:limit]:
            try:
                items.append(
                    ExecutionCertificate.from_dict(
                        json.loads(f.read_text(encoding="utf-8"))
                    )
                )
            except (OSError, json.JSONDecodeError, KeyError):
                continue
        return items

    def find_by_simulation_id(
        self, simulation_id: str
    ) -> Optional[ExecutionCertificate]:
        index = self._load_index()
        cid = index.get(simulation_id)
        if cid and self.exists(cid):
            return self.load(cid)
        # Fallback: scan files (slow path, only when index is stale).
        for cert in self.list_recent(limit=500):
            if cert.simulation_id == simulation_id:
                return cert
        return None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _path_for(self, certificate_id: str) -> Path:
        safe = "".join(
            c if c.isalnum() or c in ("-", "_", ".") else "_"
            for c in str(certificate_id or "unknown")
        )
        return self._root / f"{safe}.json"

    def _load_index(self) -> dict:
        if not self._index_path.exists():
            return {}
        try:
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _update_index(self, cert: ExecutionCertificate) -> None:
        idx = self._load_index()
        idx[cert.simulation_id] = cert.certificate_id
        self._index_path.write_text(
            json.dumps(idx, sort_keys=True, indent=2), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    @property
    def root(self) -> Path:
        return self._root


def now_iso() -> str:
    """Return a UTC ISO-8601 timestamp (helper for cert ``issued_at``)."""
    return datetime.now(timezone.utc).isoformat()


__all__ = ["CertificateRepository", "now_iso"]
