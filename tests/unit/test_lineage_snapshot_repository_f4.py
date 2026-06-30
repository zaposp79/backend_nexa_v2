"""
Unit tests for F4 — LineageSnapshotRepository split-brain prevention.

F4 Option A: when a DocumentStore is configured, no filesystem fallback.
  - save() uses DocumentStore exclusively; failures propagate (not silent).
  - load()/exists() use DocumentStore exclusively; misses become FileNotFoundError/False.
  - When store=None, filesystem fallback (local/dev) is preserved.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nexa_engine.db.exceptions import DbNotFoundError
from nexa_engine.modules.lineage.infrastructure.snapshot_repository import (
    LineageSnapshotRepository,
)
from nexa_engine.modules.lineage.domain.models import LineageGraph


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_graph(sim_id: str = "sim-f4-test") -> LineageGraph:
    return LineageGraph(simulation_id=sim_id, nodes=[], roots=[])


def _store_ok() -> MagicMock:
    store = MagicMock()
    store.upsert.return_value = None
    doc = {"id": "sim-f4-test", "schema_version": "lineage_snapshot_v1", "lineage": {"simulation_id": "sim-f4-test", "nodes": [], "roots": [], "parametrization_hashes": {}}}
    store.get.return_value = doc
    return store


def _store_missing() -> MagicMock:
    store = MagicMock()
    store.get.side_effect = DbNotFoundError("not found")
    return store


def _store_returns_none() -> MagicMock:
    store = MagicMock()
    store.get.return_value = None
    return store


def _store_upsert_fails() -> MagicMock:
    store = MagicMock()
    store.upsert.side_effect = RuntimeError("Cosmos unavailable")
    return store


# ─────────────────────────────────────────────────────────────────────────────
# Case 1: with DocumentStore configured, save uses store
# ─────────────────────────────────────────────────────────────────────────────

class TestF4SaveWithStore:

    def test_save_calls_store_upsert(self):
        """save() must call DocumentStore.upsert when store is configured."""
        store = _store_ok()
        repo = LineageSnapshotRepository(store=store)
        graph = _make_graph()

        repo.save(graph)

        store.upsert.assert_called_once()
        call_args = store.upsert.call_args
        doc = call_args[0][1]  # second positional arg
        assert doc["id"] == "sim-f4-test"
        assert doc["schema_version"] == "lineage_snapshot_v1"
        assert "lineage" in doc

    def test_save_does_not_write_to_filesystem_when_store_present(self, tmp_path):
        """save() must not write to filesystem when DocumentStore is present."""
        store = _store_ok()
        repo = LineageSnapshotRepository(store=store, base_dir=tmp_path)
        graph = _make_graph()

        repo.save(graph)

        # No file should be created in the filesystem
        files = list(tmp_path.rglob("*.json"))
        assert files == [], f"Unexpected filesystem write: {files}"

    def test_save_store_failure_propagates_not_silenced(self):
        """save() failure must propagate when DocumentStore is configured — no silent fallback."""
        store = _store_upsert_fails()
        repo = LineageSnapshotRepository(store=store)
        graph = _make_graph()

        with pytest.raises(RuntimeError, match="Cosmos unavailable"):
            repo.save(graph)


# ─────────────────────────────────────────────────────────────────────────────
# Case 2: with DocumentStore configured, load uses store
# ─────────────────────────────────────────────────────────────────────────────

class TestF4LoadWithStore:

    def test_load_calls_store_get(self):
        """load() must call DocumentStore.get when store is configured."""
        store = _store_ok()
        repo = LineageSnapshotRepository(store=store)

        result = repo.load("sim-f4-test")

        store.get.assert_called_once()
        assert result.simulation_id == "sim-f4-test"

    def test_load_does_not_read_filesystem_when_store_present(self, tmp_path):
        """load() must not read filesystem when DocumentStore is present."""
        store = _store_ok()
        repo = LineageSnapshotRepository(store=store, base_dir=tmp_path)

        # Write a lineage file to filesystem — it should be ignored
        fs_path = tmp_path / "sim-f4-test" / "lineage.json"
        fs_path.parent.mkdir(parents=True, exist_ok=True)
        fs_path.write_text(json.dumps({"simulation_id": "from-filesystem", "nodes": [], "roots": []}))

        result = repo.load("sim-f4-test")

        # Must use store value (sim-f4-test), not filesystem value (from-filesystem)
        assert result.simulation_id == "sim-f4-test"


# ─────────────────────────────────────────────────────────────────────────────
# Case 3: with DocumentStore configured, miss/failure does NOT fall back to filesystem
# ─────────────────────────────────────────────────────────────────────────────

class TestF4NoFallbackWhenStoreFails:

    def test_load_raises_file_not_found_on_db_miss(self, tmp_path):
        """load() raises FileNotFoundError on DocumentStore miss — does not fall back to filesystem."""
        store = _store_missing()
        repo = LineageSnapshotRepository(store=store, base_dir=tmp_path)

        # Write a lineage file to filesystem (should be ignored)
        fs_path = tmp_path / "sim-absent" / "lineage.json"
        fs_path.parent.mkdir(parents=True, exist_ok=True)
        fs_path.write_text(json.dumps({"simulation_id": "sim-absent", "nodes": [], "roots": []}))

        # Must raise, not fall back to filesystem
        with pytest.raises(FileNotFoundError):
            repo.load("sim-absent")

    def test_load_raises_file_not_found_when_doc_is_none(self, tmp_path):
        """load() raises FileNotFoundError when DocumentStore returns None."""
        store = _store_returns_none()
        repo = LineageSnapshotRepository(store=store, base_dir=tmp_path)

        with pytest.raises(FileNotFoundError):
            repo.load("sim-absent")

    def test_exists_returns_false_on_db_miss_not_filesystem(self, tmp_path):
        """exists() returns False on DocumentStore miss — does not check filesystem."""
        store = _store_missing()
        repo = LineageSnapshotRepository(store=store, base_dir=tmp_path)

        # Write a lineage file to filesystem (should be ignored)
        fs_path = tmp_path / "sim-absent" / "lineage.json"
        fs_path.parent.mkdir(parents=True, exist_ok=True)
        fs_path.write_text("{}")

        result = repo.exists("sim-absent")

        assert result is False

    def test_save_failure_does_not_write_to_filesystem(self, tmp_path):
        """save() failure must not silently write to filesystem — split-brain prevented."""
        store = _store_upsert_fails()
        repo = LineageSnapshotRepository(store=store, base_dir=tmp_path)
        graph = _make_graph()

        with pytest.raises(RuntimeError):
            repo.save(graph)

        files = list(tmp_path.rglob("*.json"))
        assert files == [], f"Filesystem write detected after DocumentStore failure: {files}"


# ─────────────────────────────────────────────────────────────────────────────
# Case 4: without DocumentStore (store=None), filesystem fallback still works
# ─────────────────────────────────────────────────────────────────────────────

class TestF4FilesystemFallbackPreserved:

    def test_save_writes_to_filesystem_when_no_store(self, tmp_path):
        """save() must write to filesystem when store=None (local/dev mode)."""
        repo = LineageSnapshotRepository(store=None, base_dir=tmp_path)
        graph = _make_graph("sim-local")

        path = repo.save(graph)

        assert path.exists()
        data = json.loads(path.read_text())
        assert data["simulation_id"] == "sim-local"

    def test_load_reads_from_filesystem_when_no_store(self, tmp_path):
        """load() must read from filesystem when store=None."""
        repo = LineageSnapshotRepository(store=None, base_dir=tmp_path)
        graph = _make_graph("sim-local")
        repo.save(graph)

        result = repo.load("sim-local")

        assert result.simulation_id == "sim-local"

    def test_exists_checks_filesystem_when_no_store(self, tmp_path):
        """exists() must check filesystem when store=None."""
        repo = LineageSnapshotRepository(store=None, base_dir=tmp_path)
        graph = _make_graph("sim-local")
        repo.save(graph)

        assert repo.exists("sim-local") is True
        assert repo.exists("sim-nonexistent") is False

    def test_load_raises_file_not_found_for_missing_file_when_no_store(self, tmp_path):
        """load() raises FileNotFoundError for missing file when store=None."""
        repo = LineageSnapshotRepository(store=None, base_dir=tmp_path)

        with pytest.raises(FileNotFoundError):
            repo.load("sim-does-not-exist")
