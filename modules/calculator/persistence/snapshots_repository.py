"""
nexa_engine/simulation/snapshots/repository.py
================================================
FASE 4 — SnapshotRepository: Persistencia agnóstica de SimulationSnapshot.

STEP3A MIGRATION: Repository + DocumentStore pattern.

Estructura de almacenamiento (agnóstica):
  DocumentStore collection "simulation_snapshots"
    └─ document {
       "id": simulation_id,
       "schema_version": "snapshot_v1",
       "snapshot": {...},          ← SimulationSnapshot.as_dict()
       "summary": {...}            ← PanelSummary.as_dict()
    }

Para JSON provider: storage/simulation_snapshots/{simulation_id}.json
Para Cosmos: Azure Cosmos Document

Principios:
  - Persistencia agnóstica: DocumentStore abstrae JSON/Cosmos
  - Documento único: snapshot + summary consolidados
  - Inmutabilidad: nunca se modifica; nuevas versiones = nuevo simulation_id
  - Fallo no-fatal: errores se loguean, no abortan pipeline
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.db.exceptions import DbNotFoundError
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.modules.calculator_motor.models.snapshot import PanelSummary, SimulationSnapshot
from nexa_engine.modules.shared.exceptions import NotFoundError

logger = logging.getLogger(__name__)

_COLLECTION = CollectionConfig(name="simulation_snapshots")


class SnapshotRepository:
    """
    Repositorio agnóstico de SimulationSnapshot usando DocumentStore.

    Migrado en STEP3A para soportar JSON + Cosmos sin acceso directo
    a filesystem desde runtime.
    """

    def __init__(
        self,
        store: DocumentStore,
        base_dir=None,  # deprecated, kept for backward compat only
    ) -> None:
        self._store = store
        # base_dir is ignored — we use DocumentStore for all persistence

    # ──────────────────────────────────────────────────────────────────
    # Escritura
    # ──────────────────────────────────────────────────────────────────

    def save(self, snapshot: SimulationSnapshot) -> None:
        """
        Persiste un SimulationSnapshot via DocumentStore.

        Args:
            snapshot: El snapshot a persistir.

        Raises:
            No lanza excepciones — errores se loguean y no abortan el pipeline.
        """
        simulation_id = snapshot.simulation_id
        try:
            document: Dict[str, Any] = {
                "id": simulation_id,
                "schema_version": "snapshot_v1",
                "snapshot": snapshot.as_dict(),
                "summary": snapshot.panel_summary.as_dict(),
            }
            self._store.upsert(_COLLECTION, document)
            logger.info(
                "SnapshotRepository: snapshot guardado via DocumentStore → %s",
                simulation_id,
            )
        except Exception as exc:
            logger.error(
                "SnapshotRepository: error guardando snapshot %s: %s",
                simulation_id, exc,
            )

    # ──────────────────────────────────────────────────────────────────
    # Lectura
    # ──────────────────────────────────────────────────────────────────

    def get(self, simulation_id: str) -> SimulationSnapshot:
        """
        Carga un SimulationSnapshot desde DocumentStore.

        Args:
            simulation_id: ID de la simulación a cargar.

        Returns:
            SimulationSnapshot reconstruido.

        Raises:
            NotFoundError: si no existe snapshot para el ID dado.
        """
        try:
            doc = self._store.get(_COLLECTION, simulation_id)
        except DbNotFoundError as exc:
            raise NotFoundError("SimulationSnapshot", simulation_id) from exc

        if doc is None:
            raise NotFoundError("SimulationSnapshot", simulation_id)

        snapshot_data = doc.get("snapshot", {})
        return SimulationSnapshot.from_dict(snapshot_data)

    def get_summary(self, simulation_id: str) -> PanelSummary:
        """
        Carga el PanelSummary de una simulación desde DocumentStore.

        Args:
            simulation_id: ID de la simulación.

        Returns:
            PanelSummary con los datos básicos del deal.

        Raises:
            NotFoundError: si no existe snapshot para el ID dado.
        """
        try:
            doc = self._store.get(_COLLECTION, simulation_id)
        except DbNotFoundError as exc:
            raise NotFoundError("SimulationSnapshot", simulation_id) from exc

        if doc is None:
            raise NotFoundError("SimulationSnapshot", simulation_id)

        summary_data = doc.get("summary", {})
        return PanelSummary(
            simulation_id  = summary_data.get("simulation_id", simulation_id),
            cliente        = summary_data.get("cliente", ""),
            tipo_cliente   = summary_data.get("tipo_cliente", ""),
            linea_negocio  = summary_data.get("linea_negocio", ""),
            ciudad         = summary_data.get("ciudad", ""),
            fecha_inicio   = summary_data.get("fecha_inicio", ""),
            meses_contrato = int(summary_data.get("meses_contrato", 0)),
            margen         = float(summary_data.get("margen", 0.0)),
            total_fte      = float(summary_data.get("total_fte", 0.0)),
            created_at     = summary_data.get("created_at", ""),
        )

    def exists(self, simulation_id: str) -> bool:
        """Retorna True si existe snapshot para el simulation_id dado."""
        try:
            doc = self._store.get(_COLLECTION, simulation_id)
            return doc is not None
        except DbNotFoundError:
            return False

    def list_summaries(self) -> list[PanelSummary]:
        """
        Lista todos los PanelSummary disponibles en el repositorio.

        Nota: Esta operación requiere scan de todos los documentos.
        Para grandes volúmenes, considerar índices en DocumentStore.

        Returns:
            Lista de PanelSummary en orden de recuperación del DocumentStore.
            Retorna lista vacía si no hay snapshots guardados.
        """
        logger.debug("SnapshotRepository.list_summaries() enumerando snapshots via DocumentStore")
        summaries = []
        try:
            docs, _ = self._store.list(_COLLECTION)
            for doc in docs:
                try:
                    summary_data = doc.get("summary", {})
                    summary_id = summary_data.get("simulation_id", doc.get("id", ""))
                    summary = PanelSummary(
                        simulation_id=summary_id,
                        cliente=summary_data.get("cliente", ""),
                        tipo_cliente=summary_data.get("tipo_cliente", ""),
                        linea_negocio=summary_data.get("linea_negocio", ""),
                        ciudad=summary_data.get("ciudad", ""),
                        fecha_inicio=summary_data.get("fecha_inicio", ""),
                        meses_contrato=int(summary_data.get("meses_contrato", 0)),
                        margen=float(summary_data.get("margen", 0.0)),
                        total_fte=float(summary_data.get("total_fte", 0.0)),
                        created_at=summary_data.get("created_at", ""),
                    )
                    summaries.append(summary)
                except Exception as exc:
                    logger.warning(
                        "SnapshotRepository.list_summaries() failed to parse summary from doc id=%s: %s",
                        doc.get("id", "?"), exc
                    )
            logger.info("SnapshotRepository.list_summaries() recovered %d summaries", len(summaries))
        except Exception as exc:
            logger.error("SnapshotRepository.list_summaries() error listing from DocumentStore: %s", exc)
        return summaries

