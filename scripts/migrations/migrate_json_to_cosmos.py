"""
migrate_json_to_cosmos.py
=========================
Migra datos desde JsonDocumentStore hacia CosmosDocumentStore.

IMPORTANTE: Este script no activa Cosmos como backend por defecto.
El backend activo sigue siendo JSON hasta que se configure explícitamente
DB_PROVIDER=cosmos en las variables de entorno del servidor.

Uso:
    python -m scripts.migrations.migrate_json_to_cosmos --dry-run
    python -m scripts.migrations.migrate_json_to_cosmos --dry-run --collections gn,hr
    python -m scripts.migrations.migrate_json_to_cosmos --execute --collections gn,hr,op
    python -m scripts.migrations.migrate_json_to_cosmos --execute --fail-fast
    python -m scripts.migrations.migrate_json_to_cosmos --report reports/db/cosmos_migration_report.json

Salida del reporte:
    reports/db/cosmos_migration_report.json  (default)

Opciones:
    --dry-run         Leer y validar sin escribir en Cosmos (default si no se especifica)
    --execute         Escribir en Cosmos (requiere credenciales + confirmación)
    --collections     Colecciones a migrar separadas por coma (default: todas)
    --report          Ruta del reporte JSON (default: reports/db/cosmos_migration_report.json)
    --fail-fast       Abortar al primer error (default: continuar y reportar)

Colecciones soportadas:
    gn, hr, op, simulation_results

Colecciones fuera de alcance (NOT_APPLICABLE):
    snapshots, lineage, certificates
    Motivo: usan filesystem path-based directo, no DocumentStore.
    Migración requiere fase de refactoring separada.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Bootstrap: register nexa_engine alias (same pattern as tests/conftest.py)
# ---------------------------------------------------------------------------
# scripts/migrations/migrate_json_to_cosmos.py is at:
#   backend_nexa/scripts/migrations/migrate_json_to_cosmos.py
# parents[3] → directory containing backend_nexa/ (e.g. NEXA/)
_BACKEND_PARENT = Path(__file__).resolve().parents[3]
if str(_BACKEND_PARENT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_PARENT))

try:
    import backend_nexa  # noqa: F401 — registers nexa_engine alias
except ImportError as _e:
    print(f"ERROR: Cannot import backend_nexa: {_e}")
    print(f"  sys.path[0] = {sys.path[0]}")
    print("  Run this script from the backend_nexa/ directory or its parent.")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("migrate_json_to_cosmos")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIGRATABLE_COLLECTIONS = {
    "gn": {
        "storage_root": "storage/parametrization",
        "description": "GN parametrization versions",
    },
    "hr": {
        "storage_root": "storage/parametrization",
        "description": "HR parametrization versions",
    },
    "op": {
        "storage_root": "storage/parametrization",
        "description": "OP parametrization versions",
    },
    "simulation_results": {
        "storage_root": "storage",
        "description": "Simulation result envelopes",
    },
}

NOT_APPLICABLE_COLLECTIONS = {
    "snapshots": "Path-based filesystem; not using DocumentStore",
    "lineage": "Path-based filesystem; 2000+ files per simulation",
    "certificates": "Path-based filesystem with index.json; requires refactoring",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DocumentResult:
    collection: str
    document_id: str
    source_hash: str
    target_payload_hash: str
    metadata: dict
    status: str  # READY | SKIPPED | WRITTEN | ERROR | CONFLICT | ALREADY_EXISTS
    error: Optional[str] = None


@dataclass
class MigrationReport:
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    mode: str = "dry-run"
    collections: List[str] = field(default_factory=list)
    documents: List[DocumentResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def add(self, result: DocumentResult) -> None:
        self.documents.append(result)

    def finalize(self) -> None:
        counts: Dict[str, int] = {}
        for doc in self.documents:
            counts[doc.status] = counts.get(doc.status, 0) + 1
        self.summary = {
            "total": len(self.documents),
            "by_status": counts,
            "all_hashes_match": all(
                d.source_hash == d.target_payload_hash
                for d in self.documents
                if d.status not in ("ERROR", "SKIPPED")
            ),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(
            {
                "generated_at": self.generated_at,
                "mode": self.mode,
                "collections": self.collections,
                "summary": self.summary,
                "documents": [
                    {
                        "collection": d.collection,
                        "document_id": d.document_id,
                        "source_hash": d.source_hash,
                        "target_payload_hash": d.target_payload_hash,
                        "metadata": d.metadata,
                        "status": d.status,
                        "error": d.error,
                    }
                    for d in self.documents
                ],
            },
            indent=indent,
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# Hash utilities
# ---------------------------------------------------------------------------

def payload_hash(payload: Any) -> str:
    """Canonical SHA-256 hash of a payload for migration verification."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Migration core
# ---------------------------------------------------------------------------

def migrate_collection(
    collection_name: str,
    json_store,
    cosmos_store,
    mode: str,
    fail_fast: bool,
    report: MigrationReport,
) -> None:
    """Migrate all documents from json_store to cosmos_store for one collection."""
    from nexa_engine.db.models.collection_config import CollectionConfig
    from nexa_engine.db.models.stored_document import StoredDocument

    coll = CollectionConfig(name=collection_name)

    logger.info("[%s] reading from JSON store...", collection_name)
    try:
        records, _ = json_store.list_records(coll)
    except Exception as exc:
        logger.error("[%s] failed to read from JSON: %s", collection_name, exc)
        report.add(DocumentResult(
            collection=collection_name,
            document_id="(list)",
            source_hash="",
            target_payload_hash="",
            metadata={},
            status="ERROR",
            error=str(exc),
        ))
        if fail_fast:
            raise
        return

    logger.info("[%s] found %d documents", collection_name, len(records))

    for record in records:
        doc_id = record.id
        src_hash = payload_hash(record.payload)
        target_hash = src_hash  # will be validated after write in execute mode

        metadata = {
            "id": doc_id,
            "partition_value": record.partition_value,
            "etag": record.etag,
        }

        if mode == "dry-run":
            # Validate document can be round-tripped without data loss
            try:
                re_serialized = json.loads(
                    json.dumps(record.payload, sort_keys=True, ensure_ascii=False)
                )
                verify_hash = payload_hash(re_serialized)
                if src_hash != verify_hash:
                    raise ValueError(f"Hash mismatch after round-trip: {src_hash} vs {verify_hash}")
                status = "READY"
            except Exception as exc:
                status = "ERROR"
                report.add(DocumentResult(
                    collection=collection_name,
                    document_id=doc_id,
                    source_hash=src_hash,
                    target_payload_hash="",
                    metadata=metadata,
                    status=status,
                    error=str(exc),
                ))
                if fail_fast:
                    raise
                continue

            report.add(DocumentResult(
                collection=collection_name,
                document_id=doc_id,
                source_hash=src_hash,
                target_payload_hash=target_hash,
                metadata=metadata,
                status=status,
            ))
            logger.info("[%s] dry-run %s: READY (hash=%s...)", collection_name, doc_id, src_hash[:12])

        elif mode == "execute":
            try:
                # Check if document already exists
                existing = cosmos_store.get_record(coll, doc_id)
                if existing is not None:
                    existing_hash = payload_hash(existing.payload)
                    if existing_hash == src_hash:
                        report.add(DocumentResult(
                            collection=collection_name,
                            document_id=doc_id,
                            source_hash=src_hash,
                            target_payload_hash=existing_hash,
                            metadata=metadata,
                            status="ALREADY_EXISTS",
                        ))
                        logger.info("[%s] skip %s: ALREADY_EXISTS", collection_name, doc_id)
                        continue
                    else:
                        # Hash differs — abort to prevent silent overwrite
                        report.add(DocumentResult(
                            collection=collection_name,
                            document_id=doc_id,
                            source_hash=src_hash,
                            target_payload_hash=existing_hash,
                            metadata=metadata,
                            status="CONFLICT",
                            error="Cosmos already has this document with a different payload.",
                        ))
                        logger.error(
                            "[%s] CONFLICT %s: JSON hash=%s Cosmos hash=%s",
                            collection_name, doc_id, src_hash[:12], existing_hash[:12],
                        )
                        if fail_fast:
                            raise RuntimeError(f"Hash conflict for {collection_name}/{doc_id}")
                        continue

                # Write to Cosmos
                cosmos_store.upsert_record(coll, StoredDocument(
                    id=doc_id,
                    payload=record.payload,
                    partition_value=record.partition_value,
                ))

                # Read back and verify hash
                written = cosmos_store.get_record(coll, doc_id)
                if written is None:
                    raise RuntimeError(f"Document {doc_id} not found after write")
                written_hash = payload_hash(written.payload)
                if written_hash != src_hash:
                    raise RuntimeError(
                        f"Hash mismatch after write: expected {src_hash[:12]}, got {written_hash[:12]}"
                    )

                report.add(DocumentResult(
                    collection=collection_name,
                    document_id=doc_id,
                    source_hash=src_hash,
                    target_payload_hash=written_hash,
                    metadata=metadata,
                    status="WRITTEN",
                ))
                logger.info("[%s] written %s: OK (hash=%s...)", collection_name, doc_id, src_hash[:12])

            except Exception as exc:
                report.add(DocumentResult(
                    collection=collection_name,
                    document_id=doc_id,
                    source_hash=src_hash,
                    target_payload_hash="",
                    metadata=metadata,
                    status="ERROR",
                    error=str(exc),
                ))
                logger.error("[%s] error %s: %s", collection_name, doc_id, exc)
                if fail_fast:
                    raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_json_store(collection_name: str):
    """Build a JsonDocumentStore for the given collection."""
    from nexa_engine.db.providers.json_document_store import JsonDocumentStore
    from nexa_engine.modules.shared.infrastructure.config import (
        PARAMETRIZATION_DIR,
        STORAGE_BASE,
    )

    parametrization_collections = {"gn", "hr", "op"}
    if collection_name in parametrization_collections:
        return JsonDocumentStore(PARAMETRIZATION_DIR)
    else:
        return JsonDocumentStore(STORAGE_BASE)


def build_cosmos_store():
    """Build a CosmosDocumentStore from environment variables."""
    from nexa_engine.db.config import load_config
    from nexa_engine.db.constants.provider_constants import (
        ENV_COSMOS_ENDPOINT,
        ENV_COSMOS_KEY,
        PROVIDER_COSMOS,
        ENV_DB_PROVIDER,
    )
    from nexa_engine.db.factory import build_provider

    if not os.getenv(ENV_COSMOS_ENDPOINT) or not os.getenv(ENV_COSMOS_KEY):
        raise RuntimeError(
            "COSMOS_ENDPOINT and COSMOS_KEY must be set for --execute mode. "
            "See docs/db/cosmos_readiness.md for required environment variables."
        )

    config = load_config({ENV_DB_PROVIDER: PROVIDER_COSMOS})
    return build_provider(config)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate NEXA data from JsonDocumentStore to CosmosDocumentStore.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true", default=True,
                            help="Validate without writing (default)")
    mode_group.add_argument("--execute", action="store_true", default=False,
                            help="Write to Cosmos (requires credentials + confirmation)")
    parser.add_argument("--collections", default="",
                        help="Comma-separated collection names (default: all migratable)")
    parser.add_argument("--report", default="reports/db/cosmos_migration_report.json",
                        help="Report output path")
    parser.add_argument("--fail-fast", action="store_true", default=False,
                        help="Abort on first error")
    args = parser.parse_args()

    # Resolve mode
    mode = "execute" if args.execute else "dry-run"

    # Resolve collections
    requested = [c.strip() for c in args.collections.split(",") if c.strip()]
    if not requested:
        requested = list(MIGRATABLE_COLLECTIONS.keys())
    invalid = [c for c in requested if c not in MIGRATABLE_COLLECTIONS]
    if invalid:
        not_applicable = [c for c in invalid if c in NOT_APPLICABLE_COLLECTIONS]
        truly_invalid = [c for c in invalid if c not in NOT_APPLICABLE_COLLECTIONS]
        if not_applicable:
            for c in not_applicable:
                logger.warning("Collection '%s' is NOT_APPLICABLE: %s", c, NOT_APPLICABLE_COLLECTIONS[c])
            requested = [c for c in requested if c not in not_applicable]
        if truly_invalid:
            logger.error("Unknown collections: %s", truly_invalid)
            return 1

    # Execute mode: require explicit confirmation
    if mode == "execute":
        print("\n" + "=" * 60)
        print("WARNING: --execute mode will write data to Cosmos DB.")
        print(f"Collections: {', '.join(requested)}")
        print("JSON source will NOT be deleted.")
        print("=" * 60)
        confirm = input("\nType 'yes, migrate' to confirm: ").strip()
        if confirm != "yes, migrate":
            print("Aborted.")
            return 1

    # Build stores
    logger.info("Mode: %s | Collections: %s", mode, ", ".join(requested))
    cosmos_store = None
    if mode == "execute":
        logger.info("Connecting to Cosmos DB...")
        try:
            cosmos_store = build_cosmos_store()
        except Exception as exc:
            logger.error("Failed to connect to Cosmos: %s", exc)
            return 1

    # Run migration
    report = MigrationReport(mode=mode, collections=requested)
    exit_code = 0

    for collection_name in requested:
        json_store = build_json_store(collection_name)
        try:
            migrate_collection(
                collection_name=collection_name,
                json_store=json_store,
                cosmos_store=cosmos_store,
                mode=mode,
                fail_fast=args.fail_fast,
                report=report,
            )
        except Exception as exc:
            logger.error("Fatal error in collection %s: %s", collection_name, exc)
            exit_code = 1
            if args.fail_fast:
                break

    report.finalize()

    # Write report
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.to_json(), encoding="utf-8")
    logger.info("Report written to: %s", report_path)

    # Summary
    summary = report.summary
    logger.info(
        "Summary: total=%d by_status=%s all_hashes_match=%s",
        summary.get("total", 0),
        summary.get("by_status", {}),
        summary.get("all_hashes_match"),
    )

    if not summary.get("all_hashes_match", True):
        logger.error("HASH MISMATCH DETECTED — migration is NOT safe to execute")
        exit_code = 1

    if summary.get("by_status", {}).get("ERROR", 0) > 0:
        logger.error("Errors encountered — check report for details")
        exit_code = 1

    if summary.get("by_status", {}).get("CONFLICT", 0) > 0:
        logger.error("Conflicts detected — manual review required")
        exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
