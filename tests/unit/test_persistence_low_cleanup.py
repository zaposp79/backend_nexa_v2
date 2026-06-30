"""
Unit tests for F5 and F6 LOW cleanup items.

F5: AuditResponseV1 formula_set default stale — WAVE 14 complete.
F6: SnapshotRepository.list_summaries() stub → real implementation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from pathlib import Path

import pytest

from nexa_engine.modules.shared.contracts.api_v1.response.audit import AuditResponseV1
from nexa_engine.modules.calculator_motor.models.snapshot import PanelSummary, SimulationSnapshot
from nexa_engine.modules.calculator.persistence.snapshots_repository import SnapshotRepository


# ────────────────────────────────────────────────────────────────────────────
# F5 — AuditResponseV1 formula_set contract
# ────────────────────────────────────────────────────────────────────────────

class TestAuditResponseV1FormulaSetContract:

    def test_formula_set_is_required_field(self):
        """AuditResponseV1.formula_set must be explicitly provided (no stale default)."""
        from pydantic import ValidationError
        from nexa_engine.modules.shared.contracts.api_v1.response.audit import (
            AuditLineageSummaryV1,
        )

        lineage_summary = AuditLineageSummaryV1(
            nodes_count=10,
            roots=["root-1"],
            stages_summary={"PAYROLL": 1},
        )

        # formula_set must be explicitly provided (Pydantic requires it)
        with pytest.raises(ValidationError) as exc_info:
            AuditResponseV1(
                simulation_id="sim-123",
                engine_version="engine-v2",
                lineage=lineage_summary,
                # formula_set intentionally omitted
            )
        # Verify the error is about formula_set being required
        assert "formula_set" in str(exc_info.value)

    def test_formula_set_accepts_live_versioning(self):
        """AuditResponseV1 must accept live formula_set values from WAVE 14."""
        from nexa_engine.modules.shared.contracts.api_v1.response.audit import (
            AuditLineageSummaryV1,
        )

        lineage_summary = AuditLineageSummaryV1(
            nodes_count=5,
            roots=["root-1"],
            stages_summary={"PRICING": 1},
        )

        # Live formula_set should be accepted
        live_formula_set = "formula-set-abc123def456"
        response = AuditResponseV1(
            simulation_id="sim-456",
            engine_version="engine-v2",
            formula_set=live_formula_set,
            lineage=lineage_summary,
        )

        assert response.formula_set == live_formula_set
        assert response.formula_set.startswith("formula-set-")

    def test_formula_set_does_not_have_stale_v27_default(self):
        """AuditResponseV1 must not default to 'formula-set-v2-7'."""
        from nexa_engine.modules.shared.contracts.api_v1.response.audit import (
            AuditLineageSummaryV1,
        )

        lineage_summary = AuditLineageSummaryV1(
            nodes_count=3,
            roots=["root-1"],
            stages_summary={"VERIFY": 1},
        )

        response = AuditResponseV1(
            simulation_id="sim-789",
            engine_version="engine-v2",
            formula_set="formula-set-current-live",
            lineage=lineage_summary,
        )

        # The value provided must be used, not replaced with stale default
        assert response.formula_set != "formula-set-v2-7"
        assert response.formula_set == "formula-set-current-live"


# ────────────────────────────────────────────────────────────────────────────
# F6 — SnapshotRepository.list_summaries() implementation
# ────────────────────────────────────────────────────────────────────────────

class TestSnapshotRepositoryListSummaries:

    def test_empty_store_returns_empty_list(self):
        """list_summaries() must return [] when no snapshots are stored."""
        store = MagicMock()
        store.list.return_value = ([], None)

        repo = SnapshotRepository(store=store)
        result = repo.list_summaries()

        assert result == []

    def test_lists_persisted_summaries(self):
        """list_summaries() must enumerate all persisted snapshots."""
        sim_id_1 = "sim-abc-001"
        sim_id_2 = "sim-abc-002"

        # Mock documents returned by DocumentStore.list()
        docs = [
            {
                "id": sim_id_1,
                "schema_version": "snapshot_v1",
                "summary": {
                    "simulation_id": sim_id_1,
                    "cliente": "Client A",
                    "tipo_cliente": "Tipo 1",
                    "linea_negocio": "Line A",
                    "ciudad": "Bogota",
                    "fecha_inicio": "2026-01-01",
                    "meses_contrato": 12,
                    "margen": 0.18,
                    "total_fte": 50.0,
                    "created_at": "2026-01-15T10:00:00Z",
                },
            },
            {
                "id": sim_id_2,
                "schema_version": "snapshot_v1",
                "summary": {
                    "simulation_id": sim_id_2,
                    "cliente": "Client B",
                    "tipo_cliente": "Tipo 2",
                    "linea_negocio": "Line B",
                    "ciudad": "Cali",
                    "fecha_inicio": "2026-02-01",
                    "meses_contrato": 24,
                    "margen": 0.20,
                    "total_fte": 100.0,
                    "created_at": "2026-02-15T11:00:00Z",
                },
            },
        ]

        store = MagicMock()
        store.list.return_value = (docs, None)

        repo = SnapshotRepository(store=store)
        summaries = repo.list_summaries()

        assert len(summaries) == 2
        assert summaries[0].simulation_id == sim_id_1
        assert summaries[0].cliente == "Client A"
        assert summaries[0].total_fte == 50.0
        assert summaries[1].simulation_id == sim_id_2
        assert summaries[1].cliente == "Client B"
        assert summaries[1].total_fte == 100.0

    def test_handles_missing_summary_data(self):
        """list_summaries() must gracefully handle documents with missing summary fields."""
        # Document with minimal/missing data
        docs = [
            {
                "id": "sim-incomplete",
                "schema_version": "snapshot_v1",
                "summary": {
                    "simulation_id": "sim-incomplete",
                    # other fields missing
                },
            },
        ]

        store = MagicMock()
        store.list.return_value = (docs, None)

        repo = SnapshotRepository(store=store)
        summaries = repo.list_summaries()

        # Should still return a PanelSummary with defaults for missing fields
        assert len(summaries) == 1
        assert summaries[0].simulation_id == "sim-incomplete"
        assert summaries[0].cliente == ""
        assert summaries[0].total_fte == 0.0

    def test_skips_malformed_entries(self):
        """list_summaries() must skip entries that cannot be parsed."""
        docs = [
            {
                "id": "sim-good",
                "schema_version": "snapshot_v1",
                "summary": {
                    "simulation_id": "sim-good",
                    "cliente": "Good Client",
                    "meses_contrato": 12,
                },
            },
            {
                "id": "sim-bad",
                "schema_version": "snapshot_v1",
                "summary": {
                    "simulation_id": "sim-bad",
                    "meses_contrato": "not-an-int",  # This will fail int() conversion
                },
            },
            {
                "id": "sim-good-2",
                "schema_version": "snapshot_v1",
                "summary": {
                    "simulation_id": "sim-good-2",
                    "cliente": "Good Client 2",
                    "meses_contrato": 24,
                },
            },
        ]

        store = MagicMock()
        store.list.return_value = (docs, None)

        repo = SnapshotRepository(store=store)
        summaries = repo.list_summaries()

        # Should skip the malformed entry and return the two good ones
        assert len(summaries) == 2
        assert summaries[0].simulation_id == "sim-good"
        assert summaries[1].simulation_id == "sim-good-2"

    def test_handles_store_error_gracefully(self):
        """list_summaries() must handle DocumentStore errors without crashing."""
        store = MagicMock()
        store.list.side_effect = Exception("Store unavailable")

        repo = SnapshotRepository(store=store)
        result = repo.list_summaries()

        # Must return empty list on error, not raise
        assert result == []

    def test_converts_numeric_strings_to_numbers(self):
        """list_summaries() must properly convert string numbers to float/int."""
        docs = [
            {
                "id": "sim-numeric",
                "schema_version": "snapshot_v1",
                "summary": {
                    "simulation_id": "sim-numeric",
                    "meses_contrato": "12",  # String, not int
                    "margen": "0.18",  # String, not float
                    "total_fte": "50.5",  # String, not float
                },
            },
        ]

        store = MagicMock()
        store.list.return_value = (docs, None)

        repo = SnapshotRepository(store=store)
        summaries = repo.list_summaries()

        assert len(summaries) == 1
        assert summaries[0].meses_contrato == 12  # int
        assert summaries[0].margen == 0.18  # float
        assert summaries[0].total_fte == 50.5  # float
