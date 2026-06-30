"""
infrastructure.lineage.snapshot_repository
==========================================

Persistence for `LineageGraph` objects.

STEP3C MIGRATION: Repository + DocumentStore pattern (agnóstico JSON/Cosmos).

Storage layout:

AGNÓSTICO (si store está disponible):
  DocumentStore collection "lineage_snapshots"
    └─ document {
       "id": simulation_id,
       "schema_version": "lineage_snapshot_v1",
       "lineage": {...}
    }

FALLBACK (si store=None):
  storage/
    lineage/
      <simulation_id>/
        lineage.json

Nota: Documento JSON es determinístico (sort_keys, fixed indent, sin timestamps).
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, Any, Dict

from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.db.exceptions import DbNotFoundError
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.modules.lineage.domain.models import LineageGraph

logger = logging.getLogger(__name__)

_INVALID_ID = re.compile(r"[^A-Za-z0-9_.\-]+")
_COLLECTION = CollectionConfig(name="lineage_snapshots")


class LineageSnapshotRepository:
    """Read/write ``LineageGraph`` JSON files (agnóstico JSON/Cosmos).

    STEP3C MIGRATION: Usa DocumentStore si está inyectado;
    fallback a filesystem si store=None (legacy support para scripts offline).

    Interfaz pública compatible: save(), load(), exists(), save_lineage(), load_lineage().
    """

    def __init__(
        self,
        store: DocumentStore | None = None,
        base_dir: Optional[Path] = None,
    ) -> None:
        self._store = store  # DocumentStore (agnóstico) o None (fallback filesystem)
        if base_dir is None:
            # default to repo storage/lineage relative to working dir
            base_dir = Path(os.getcwd()) / "storage" / "lineage"
        self._base_dir = Path(base_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def save(self, graph: LineageGraph) -> Path:
        """Persist `graph` via DocumentStore (if available) or filesystem.

        Returns the filesystem path (legacy contract).

        When a DocumentStore is configured, only DocumentStore is used — no
        filesystem fallback.  The filesystem path is only used when store=None
        (local/dev mode).  This prevents split-brain in multi-pod deployments
        where pod-local filesystems are ephemeral and invisible to other pods.
        """
        simulation_id = graph.simulation_id
        payload = graph.to_dict(include_timestamps=False)

        if self._store is not None:
            # DocumentStore configured: use it exclusively; let failures propagate
            # so the caller (engine) can log the warning.  No silent split-brain.
            document: Dict[str, Any] = {
                "id": simulation_id,
                "schema_version": "lineage_snapshot_v1",
                "lineage": payload,
            }
            self._store.upsert(_COLLECTION, document)
            logger.info(
                "LineageSnapshotRepository: saved via DocumentStore → %s",
                simulation_id,
            )
            return self._path_for(simulation_id)

        # store=None: local/dev filesystem fallback only
        return self._save_filesystem(graph, payload)

    def _save_filesystem(self, graph: LineageGraph, payload: Dict[str, Any]) -> Path:
        """Save to filesystem (fallback when no DocumentStore)."""
        path = self._path_for(graph.simulation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, sort_keys=True, indent=2, default=str)
        path.write_text(text, encoding="utf-8")
        return path

    # Backwards-friendly aliases (the WAVE 10 plan uses these names)
    def save_lineage(self, simulation_id: str, graph: LineageGraph) -> Path:
        # accept mismatch but persist the graph as-given
        if simulation_id and simulation_id != graph.simulation_id:
            graph = LineageGraph(
                simulation_id=simulation_id,
                nodes=graph.nodes,
                roots=graph.roots,
                parametrization_hashes=graph.parametrization_hashes,
            )
        return self.save(graph)

    def load(self, simulation_id: str) -> LineageGraph:
        """Load from DocumentStore (if available) or filesystem.

        When a DocumentStore is configured, only DocumentStore is queried — no
        filesystem fallback (F4: prevent split-brain in multi-pod deployments).
        """
        if self._store is not None:
            try:
                doc = self._store.get(_COLLECTION, simulation_id)
            except DbNotFoundError:
                raise FileNotFoundError(
                    f"Lineage snapshot not found for simulation_id={simulation_id!r}"
                )
            if doc is None:
                raise FileNotFoundError(
                    f"Lineage snapshot not found for simulation_id={simulation_id!r}"
                )
            payload = doc.get("lineage", {})
            return LineageGraph.from_dict(payload)

        # store=None: local/dev filesystem fallback only
        return self._load_filesystem(simulation_id)

    def _load_filesystem(self, simulation_id: str) -> LineageGraph:
        """Load from filesystem (fallback when no DocumentStore or not found)."""
        path = self._path_for(simulation_id)
        if not path.exists():
            raise FileNotFoundError(
                f"Lineage snapshot not found for simulation_id={simulation_id!r} "
                f"at {path}"
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        return LineageGraph.from_dict(data)

    def load_lineage(self, simulation_id: str) -> LineageGraph:
        return self.load(simulation_id)

    def exists(self, simulation_id: str) -> bool:
        """Check if lineage exists in DocumentStore or filesystem.

        When a DocumentStore is configured, only DocumentStore is queried (F4).
        """
        if self._store is not None:
            try:
                doc = self._store.get(_COLLECTION, simulation_id)
                return doc is not None
            except (DbNotFoundError, Exception):
                return False

        # store=None: filesystem fallback
        return self._path_for(simulation_id).exists()

    def list_graphs(self, limit: int = 50) -> list[LineageGraph]:
        """Return up to `limit` stored LineageGraphs.

        When a DocumentStore is configured, enumerates via the store (supports
        Cosmos and JSON providers).  When store=None (local/offline), falls back
        to iterating the filesystem directory — preserving the legacy behaviour.

        Errors from individual documents are logged and skipped; a DocumentStore
        failure raises so callers can distinguish "store unavailable" from "empty
        list".
        """
        if self._store is not None:
            docs, _ = self._store.list(_COLLECTION, limit=limit)
            graphs: list[LineageGraph] = []
            for doc in docs:
                try:
                    payload = doc.get("lineage", {})
                    graphs.append(LineageGraph.from_dict(payload))
                except Exception as exc:
                    logger.warning(
                        "LineageSnapshotRepository.list_graphs: skipping malformed doc id=%s: %s",
                        doc.get("id", "?"), exc,
                    )
            return graphs

        # store=None: filesystem fallback
        if not self._base_dir.exists():
            return []
        graphs = []
        for child in sorted(self._base_dir.iterdir()):
            if len(graphs) >= limit:
                break
            if not child.is_dir():
                continue
            file = child / "lineage.json"
            if not file.exists():
                continue
            try:
                graph = self.load(child.name)
                graphs.append(graph)
            except Exception as exc:
                logger.warning(
                    "LineageSnapshotRepository.list_graphs: skipping unloadable dir=%s: %s",
                    child.name, exc,
                )
        return graphs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _path_for(self, simulation_id: str) -> Path:
        safe = _INVALID_ID.sub("_", str(simulation_id or "unknown"))
        return self._base_dir / safe / "lineage.json"

    @property
    def base_dir(self) -> Path:
        return self._base_dir


__all__ = ["LineageSnapshotRepository"]
