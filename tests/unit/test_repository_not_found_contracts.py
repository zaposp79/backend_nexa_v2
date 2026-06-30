"""
Unit tests for F2 and F7 — repository not-found contract normalization.

F2: SnapshotRepository.get() / get_summary() must raise domain NotFoundError,
    not builtin FileNotFoundError.
F7: TraceabilityRepository.get() must raise domain NotFoundError on miss,
    not return None.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from nexa_engine.db.exceptions import DbNotFoundError
from nexa_engine.modules.shared.exceptions import NotFoundError
from nexa_engine.modules.calculator.persistence.snapshots_repository import SnapshotRepository
from nexa_engine.modules.calculator.persistence.traceability_repository import TraceabilityRepository


# ────────────────────────────────────────────────────────────────────────────
# Helpers — mock DocumentStore that always raises DbNotFoundError
# ────────────────────────────────────────────────────────────────────────────

def _missing_store() -> MagicMock:
    """DocumentStore whose .get() always raises DbNotFoundError."""
    store = MagicMock()
    store.get.side_effect = DbNotFoundError("not found")
    return store


def _none_store() -> MagicMock:
    """DocumentStore whose .get() returns None."""
    store = MagicMock()
    store.get.return_value = None
    return store


# ────────────────────────────────────────────────────────────────────────────
# F2 — SnapshotRepository.get()
# ────────────────────────────────────────────────────────────────────────────

class TestSnapshotRepositoryNotFoundContract:

    def test_get_raises_domain_not_found_error_on_db_miss(self):
        """SnapshotRepository.get() raises NotFoundError when DocumentStore misses."""
        repo = SnapshotRepository(store=_missing_store())
        with pytest.raises(NotFoundError):
            repo.get("sim-id-absent")

    def test_get_does_not_raise_builtin_file_not_found_error(self):
        """SnapshotRepository.get() must NOT leak FileNotFoundError."""
        repo = SnapshotRepository(store=_missing_store())
        with pytest.raises(NotFoundError):
            repo.get("sim-id-absent")
        # Verify the raised exception is NOT the builtin FileNotFoundError
        try:
            repo.get("sim-id-absent")
        except NotFoundError:
            pass  # correct — domain error raised
        except FileNotFoundError:
            pytest.fail("SnapshotRepository.get() leaked builtin FileNotFoundError")

    def test_get_raises_domain_not_found_error_on_none_doc(self):
        """SnapshotRepository.get() raises NotFoundError when DocumentStore returns None."""
        repo = SnapshotRepository(store=_none_store())
        with pytest.raises(NotFoundError):
            repo.get("sim-id-none-doc")

    def test_get_not_found_error_message_does_not_expose_filesystem_path(self):
        """NotFoundError message must not contain filesystem path details."""
        repo = SnapshotRepository(store=_missing_store())
        try:
            repo.get("sim-123")
        except NotFoundError as exc:
            assert "/Users/" not in exc.message
            assert "/home/" not in exc.message
            assert "storage/" not in exc.message
            assert "backend_nexa/" not in exc.message
        else:
            pytest.fail("Expected NotFoundError was not raised")

    def test_get_not_found_error_has_correct_resource(self):
        """NotFoundError must identify the resource correctly."""
        repo = SnapshotRepository(store=_missing_store())
        with pytest.raises(NotFoundError) as exc_info:
            repo.get("sim-abc")
        assert exc_info.value.resource == "SimulationSnapshot"
        assert exc_info.value.identifier == "sim-abc"

    def test_get_summary_raises_domain_not_found_error(self):
        """SnapshotRepository.get_summary() raises NotFoundError on miss."""
        repo = SnapshotRepository(store=_missing_store())
        with pytest.raises(NotFoundError):
            repo.get_summary("sim-id-absent")

    def test_get_summary_does_not_raise_builtin_file_not_found_error(self):
        """SnapshotRepository.get_summary() must NOT leak FileNotFoundError."""
        repo = SnapshotRepository(store=_missing_store())
        try:
            repo.get_summary("sim-id-absent")
        except NotFoundError:
            pass  # correct
        except FileNotFoundError:
            pytest.fail("SnapshotRepository.get_summary() leaked builtin FileNotFoundError")

    def test_exists_still_returns_false_on_miss(self):
        """exists() contract is unchanged — returns False on miss, not raises."""
        repo = SnapshotRepository(store=_missing_store())
        result = repo.exists("sim-id-absent")
        assert result is False


# ────────────────────────────────────────────────────────────────────────────
# F7 — TraceabilityRepository.get()
# ────────────────────────────────────────────────────────────────────────────

class TestTraceabilityRepositoryNotFoundContract:

    def test_get_raises_domain_not_found_error_on_db_miss(self):
        """TraceabilityRepository.get() raises NotFoundError when DocumentStore misses."""
        repo = TraceabilityRepository(store=_missing_store())
        with pytest.raises(NotFoundError):
            repo.get("sim-id-absent")

    def test_get_does_not_return_none_on_miss(self):
        """TraceabilityRepository.get() must NOT return None on miss."""
        repo = TraceabilityRepository(store=_missing_store())
        result = None
        try:
            result = repo.get("sim-id-absent")
        except NotFoundError:
            pass  # correct
        else:
            pytest.fail(f"Expected NotFoundError, got {result!r}")

    def test_get_raises_domain_not_found_error_on_none_doc(self):
        """TraceabilityRepository.get() raises NotFoundError when DocumentStore returns None."""
        repo = TraceabilityRepository(store=_none_store())
        with pytest.raises(NotFoundError):
            repo.get("sim-id-none-doc")

    def test_get_not_found_error_has_correct_resource(self):
        """NotFoundError must identify the resource correctly."""
        repo = TraceabilityRepository(store=_missing_store())
        with pytest.raises(NotFoundError) as exc_info:
            repo.get("sim-xyz")
        assert exc_info.value.resource == "TraceabilityRecord"
        assert exc_info.value.identifier == "sim-xyz"

    def test_get_audit_returns_none_on_missing_document(self):
        """get_audit() convenience helper returns None when document is absent.

        get_audit() has an Optional return contract — callers check for None.
        It must not propagate NotFoundError to its own callers.
        """
        repo = TraceabilityRepository(store=_missing_store())
        result = repo.get_audit("sim-id-absent", "polizas_source")
        assert result is None

    def test_exists_still_returns_false_on_miss(self):
        """exists() contract is unchanged — returns False on miss, not raises."""
        repo = TraceabilityRepository(store=_missing_store())
        result = repo.exists("sim-id-absent")
        assert result is False
