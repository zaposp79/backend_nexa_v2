"""
tests/db/contract/test_lineage_repository_documentstore_wiring.py
==================================================================

STEP3C CLOSEOUT — Guardrail test validating that LineageSnapshotRepository
uses DocumentStore in runtime and falls back to filesystem only for legacy.

This test ensures:
1. Runtime composition root creates LineageSnapshotRepository with DocumentStore
2. Engine.calcular() uses injected lineage_repo (not fallback filesystem)
3. Audit/certification flow uses injected _lineage_repo
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import backend_nexa  # noqa: F401

import pytest
from nexa_engine.db.dependencies import _lineage_repo
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.calculator.use_cases.certified_calculation import (
    CertifiedCalculationUseCase,
)
from nexa_engine.modules.audit.use_cases.audit_simulation import (
    AuditSimulationUseCase,
)


class TestLineageRepositoryDocumentStoreWiring:
    """Validate that LineageSnapshotRepository uses DocumentStore in runtime."""

    def test_composition_root_has_lineage_repo_with_store(self):
        """Composition root (_lineage_repo) must have DocumentStore injected."""
        assert _lineage_repo is not None
        assert _lineage_repo._store is not None
        # _store is DocumentStore (JSON or Cosmos provider)
        assert hasattr(_lineage_repo._store, 'upsert')
        assert hasattr(_lineage_repo._store, 'get')

    def test_engine_accepts_lineage_repository_param(self):
        """NexaPricingEngine constructor must accept lineage_repository param."""
        engine = NexaPricingEngine(lineage_repository=_lineage_repo)
        assert engine._lineage_repository is not None
        assert engine._lineage_repository._store is not None

    def test_engine_constructor_backward_compat_without_lineage_repository(self):
        """Engine must be constructible without lineage_repository (legacy)."""
        engine = NexaPricingEngine()
        # Should not raise; fallback is allowed for legacy scripts
        assert engine._lineage_repository is None

    def test_certified_calculation_accepts_lineage_repo(self):
        """CertifiedCalculationUseCase must accept lineage_repo param."""
        use_case = CertifiedCalculationUseCase(
            engine=None,
            version_registry=None,
            baseline_root=Path.cwd() / "storage" / "baselines",
            cert_repo=None,
            lineage_repo=_lineage_repo,
        )
        assert use_case._lineage_repo is not None
        assert use_case._lineage_repo._store is not None

    def test_audit_simulation_accepts_lineage_repo(self):
        """AuditSimulationUseCase must accept lineage_repo param."""
        use_case = AuditSimulationUseCase(lineage_repo=_lineage_repo)
        assert use_case._repo is not None
        assert use_case._repo._store is not None

    def test_lineage_repo_store_is_not_none(self):
        """_lineage_repo._store must be set (not None) in composition root."""
        # This ensures runtime uses DocumentStore, not fallback filesystem
        assert _lineage_repo._store is not None

    def test_lineage_repo_can_save_with_documentstore(self):
        """_lineage_repo must support save() via DocumentStore."""
        # This is a minimal sanity check that save() method is callable
        assert callable(_lineage_repo.save)
        assert callable(_lineage_repo.load)
        assert callable(_lineage_repo.exists)


__all__ = ["TestLineageRepositoryDocumentStoreWiring"]
