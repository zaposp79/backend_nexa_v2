"""
nexa_engine/simulation/traceability/repository.py
==================================================
FASE G — TraceabilityRepository: Persistencia agnóstica de traceabilidad completa.

STEP3B MIGRATION: Repository + DocumentStore pattern.

Estructura de almacenamiento (agnóstica):
  DocumentStore collection "simulation_traceability"
    └─ document {
       "id": simulation_id,
       "schema_version": "traceability_v1",
       "request": {...},            ← raw_request (pre-normalización)
       "visions": {
           "vision_pyg": {...},
           "vision_tarifas": {...},
           "cost_to_serve": {...},
           "vision_imprimible": {...}
       },
       "audit": {
           "polizas_source": {...},
           "escenarios_aplicados": {...},
           "panel_summary": {...}
       }
    }

Para JSON provider: storage/simulation_traceability/{simulation_id}.json
Para Cosmos: Azure Cosmos Document

Principios:
  - Persistencia agnóstica: DocumentStore abstrae JSON/Cosmos
  - Documento único: consolidación de 10+ archivos
  - Inmutabilidad: nunca se modifica; nuevas versiones = nuevo simulation_id
  - Fallo no-fatal: errores se loguean, no abortan pipeline
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from nexa_engine.db.ports.document_store import DocumentStore
from nexa_engine.db.exceptions import DbNotFoundError
from nexa_engine.db.models.collection_config import CollectionConfig
from nexa_engine.modules.shared.exceptions import NotFoundError

logger = logging.getLogger(__name__)

_COLLECTION = CollectionConfig(name="simulation_traceability")


class TraceabilityRepository:
    """
    Repositorio agnóstico de traceabilidad completa usando DocumentStore.

    Migrado en STEP3B para soportar JSON + Cosmos sin acceso directo
    a filesystem desde runtime.
    """

    def __init__(self, store: DocumentStore) -> None:
        self._store = store

    def save(self, simulation_id: str, data: Dict[str, Any]) -> None:
        """
        Persiste la traceabilidad completa via DocumentStore.

        Args:
            simulation_id: ID de la simulación.
            data: Documento completo con request, visions, audit, etc.

        Raises:
            No lanza excepciones — errores se loguean y no abortan el pipeline.
        """
        try:
            document: Dict[str, Any] = {
                "id": simulation_id,
                "schema_version": "traceability_v1",
                **data,  # request, visions, audit
            }
            self._store.upsert(_COLLECTION, document)
            logger.info(
                "TraceabilityRepository: traceability guardada via DocumentStore → %s",
                simulation_id,
            )
        except Exception as exc:
            logger.error(
                "TraceabilityRepository: error guardando traceability %s: %s",
                simulation_id, exc,
            )

    def get(self, simulation_id: str) -> Dict[str, Any]:
        """
        Carga la traceabilidad completa desde DocumentStore.

        Args:
            simulation_id: ID de la simulación.

        Returns:
            Documento completo (dict).

        Raises:
            NotFoundError: si no existe traceabilidad para el ID dado.
        """
        try:
            doc = self._store.get(_COLLECTION, simulation_id)
        except DbNotFoundError as exc:
            raise NotFoundError("TraceabilityRecord", simulation_id) from exc
        if doc is None:
            raise NotFoundError("TraceabilityRecord", simulation_id)
        return doc

    def get_audit(self, simulation_id: str, audit_key: str) -> Optional[Dict[str, Any]]:
        """
        Carga un campo específico del audit desde DocumentStore.

        Args:
            simulation_id: ID de la simulación.
            audit_key: 'polizas_source', 'escenarios_aplicados', o 'panel_summary'.

        Returns:
            Dict del campo solicitado o None si no existe el documento o la clave.

        Ejemplo:
            polizas = repo.get_audit(sim_id, 'polizas_source')
        """
        try:
            doc = self.get(simulation_id)
        except NotFoundError:
            return None
        audit = doc.get("audit", {})
        return audit.get(audit_key)

    def exists(self, simulation_id: str) -> bool:
        """Retorna True si existe traceability para el simulation_id dado."""
        try:
            doc = self._store.get(_COLLECTION, simulation_id)
            return doc is not None
        except DbNotFoundError:
            return False
