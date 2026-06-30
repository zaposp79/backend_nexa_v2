"""
Unit tests for Fix 1 — list_simulations DocumentStore support.

Verifies that:
1. list_simulations returns stored simulations with a DocumentStore-backed repo.
2. list_simulations still works in local filesystem mode.
3. Empty store returns [].
4. Repository operational failure propagates (not silently empty list).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nexa_engine.db.exceptions import DbNotFoundError
from nexa_engine.modules.lineage.infrastructure.snapshot_repository import (
    LineageSnapshotRepository,
)
from nexa_engine.modules.lineage.domain.models import LineageGraph
from nexa_engine.modules.audit.use_cases.audit_simulation import AuditSimulationUseCase


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _graph_doc(sim_id: str) -> dict:
    graph = LineageGraph(simulation_id=sim_id, nodes=[], roots=[])
    return {
        "id": sim_id,
        "schema_version": "lineage_snapshot_v1",
        "lineage": graph.to_dict(include_timestamps=False),
    }


def _store_with_docs(*sim_ids: str) -> MagicMock:
    store = MagicMock()
    docs = [_graph_doc(sid) for sid in sim_ids]
    store.list.return_value = (docs, None)
    return store


def _empty_store() -> MagicMock:
    store = MagicMock()
    store.list.return_value = ([], None)
    return store


def _failing_store() -> MagicMock:
    store = MagicMock()
    store.list.side_effect = RuntimeError("Cosmos unavailable")
    return store


# ─────────────────────────────────────────────────────────────────────────────
# list_graphs — repository level
# ─────────────────────────────────────────────────────────────────────────────

class TestListGraphsDocumentStore:

    def test_returns_graphs_from_store(self):
        """list_graphs() must return graphs from DocumentStore when store is configured."""
        store = _store_with_docs("sim-001", "sim-002")
        repo = LineageSnapshotRepository(store=store)
        graphs = repo.list_graphs()
        assert len(graphs) == 2
        sim_ids = {g.simulation_id for g in graphs}
        assert "sim-001" in sim_ids
        assert "sim-002" in sim_ids

    def test_empty_store_returns_empty_list(self):
        """list_graphs() returns [] when DocumentStore has no documents."""
        repo = LineageSnapshotRepository(store=_empty_store())
        assert repo.list_graphs() == []

    def test_store_failure_propagates(self):
        """list_graphs() must propagate DocumentStore errors (not return [])."""
        repo = LineageSnapshotRepository(store=_failing_store())
        with pytest.raises(RuntimeError, match="Cosmos unavailable"):
            repo.list_graphs()

    def test_skips_malformed_documents(self):
        """list_graphs() must skip individual malformed documents and continue."""
        store = MagicMock()
        good_doc = _graph_doc("sim-good")
        bad_doc = {"id": "sim-bad", "schema_version": "lineage_snapshot_v1", "lineage": {"INVALID": True}}
        store.list.return_value = ([good_doc, bad_doc], None)
        repo = LineageSnapshotRepository(store=store)
        graphs = repo.list_graphs()
        # good doc parsed, bad doc skipped
        assert len(graphs) == 1
        assert graphs[0].simulation_id == "sim-good"

    def test_respects_limit_parameter(self):
        """list_graphs() passes limit to DocumentStore.list()."""
        store = MagicMock()
        store.list.return_value = ([], None)
        repo = LineageSnapshotRepository(store=store)
        repo.list_graphs(limit=10)
        store.list.assert_called_once()
        call_kwargs = store.list.call_args[1]
        assert call_kwargs.get("limit") == 10


class TestListGraphsFilesystem:

    def test_returns_graphs_from_filesystem(self, tmp_path):
        """list_graphs() returns graphs from filesystem when store=None."""
        repo = LineageSnapshotRepository(store=None, base_dir=tmp_path)
        graph = LineageGraph(simulation_id="sim-local", nodes=[], roots=[])
        repo.save(graph)
        graphs = repo.list_graphs()
        assert len(graphs) == 1
        assert graphs[0].simulation_id == "sim-local"

    def test_empty_directory_returns_empty_list(self, tmp_path):
        """list_graphs() returns [] for empty directory when store=None."""
        repo = LineageSnapshotRepository(store=None, base_dir=tmp_path)
        assert repo.list_graphs() == []

    def test_nonexistent_base_dir_returns_empty_list(self, tmp_path):
        """list_graphs() returns [] when base_dir doesn't exist and store=None."""
        repo = LineageSnapshotRepository(store=None, base_dir=tmp_path / "nonexistent")
        assert repo.list_graphs() == []


# ─────────────────────────────────────────────────────────────────────────────
# list_simulations — use case level
# ─────────────────────────────────────────────────────────────────────────────

class TestListSimulationsDocumentStore:

    def test_returns_summaries_from_store(self):
        """list_simulations() returns SimulationSummary for each DocumentStore graph."""
        store = _store_with_docs("sim-cosmos-001", "sim-cosmos-002")
        repo = LineageSnapshotRepository(store=store)
        uc = AuditSimulationUseCase(lineage_repo=repo)
        summaries = uc.list_simulations()
        sim_ids = {s.simulation_id for s in summaries}
        assert "sim-cosmos-001" in sim_ids
        assert "sim-cosmos-002" in sim_ids

    def test_empty_store_returns_empty_list(self):
        """list_simulations() returns [] when DocumentStore is empty."""
        repo = LineageSnapshotRepository(store=_empty_store())
        uc = AuditSimulationUseCase(lineage_repo=repo)
        assert uc.list_simulations() == []

    def test_store_failure_propagates_not_silent(self):
        """list_simulations() must propagate store failures — not return [] silently."""
        repo = LineageSnapshotRepository(store=_failing_store())
        uc = AuditSimulationUseCase(lineage_repo=repo)
        with pytest.raises(RuntimeError, match="Cosmos unavailable"):
            uc.list_simulations()

    def test_returns_summaries_from_filesystem(self, tmp_path):
        """list_simulations() returns summaries from filesystem when store=None."""
        repo = LineageSnapshotRepository(store=None, base_dir=tmp_path)
        graph = LineageGraph(simulation_id="sim-local-uc", nodes=[], roots=[])
        repo.save(graph)
        uc = AuditSimulationUseCase(lineage_repo=repo)
        summaries = uc.list_simulations()
        assert len(summaries) == 1
        assert summaries[0].simulation_id == "sim-local-uc"
