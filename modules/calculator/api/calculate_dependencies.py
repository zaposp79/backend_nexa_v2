"""Shared singletons for the /simulation/calculate handlers.

Instantiated once at import time (same semantics as before the split, when
they lived at module scope in calculate_router.py). Both the normal and the
certified handler import these from here so they share a single instance.

The DocumentStore is resolved at module load time from env vars via
get_provider() — this is the composition root for the calculate flow.
"""

from nexa_engine.db.config import load_config
from nexa_engine.db.factory import build_configuration_document_store, get_provider
from nexa_engine.db.dependencies import _lineage_repo  # canonical owner
from nexa_engine.modules.calculator.persistence.results_repository import ResultsRepository
from nexa_engine.modules.calculator.persistence.snapshots_repository import SnapshotRepository
from nexa_engine.modules.calculator.persistence.traceability_repository import TraceabilityRepository
from nexa_engine.modules.audit.writer import TraceabilityWriter
from nexa_engine.modules.shared.versioning.registry_provider import _version_registry  # F8 singleton

# Resultados de simulación → COSMOS_CONTAINER_SIMULATION (partition key: client_id).
_simulation_store = build_configuration_document_store(load_config())
_results_repo = ResultsRepository(_simulation_store)

# Snapshots, traceabilidad y lineage → JSON local (no van a Cosmos).
_json_store = get_provider()
_trace_repo = TraceabilityRepository(_json_store)
_trace_writer = TraceabilityWriter(repository=_trace_repo)
_snapshot_repo = SnapshotRepository(store=_json_store)

__all__ = [
    "_results_repo",
    "_trace_writer",
    "_snapshot_repo",
    "_trace_repo",
    "_lineage_repo",
    "_version_registry",
]
