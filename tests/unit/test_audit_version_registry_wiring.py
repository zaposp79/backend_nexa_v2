"""
Unit tests for Fix 2 — AuditSimulationUseCase wired to shared VersionRegistry.

Verifies that:
1. get_audit_use_case passes the shared VersionRegistry singleton.
2. AuditSimulationUseCase uses the injected registry, not a fresh one per request.
3. Existing audit version metadata behavior remains stable.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nexa_engine.modules.audit.use_cases.audit_simulation import AuditSimulationUseCase
from nexa_engine.modules.shared.versioning.version_registry import VersionRegistry, VersionMetadata
from nexa_engine.modules.shared.versioning.registry_provider import _version_registry
from nexa_engine.modules.lineage.infrastructure.snapshot_repository import LineageSnapshotRepository


# ─────────────────────────────────────────────────────────────────────────────
# Shared singleton identity
# ─────────────────────────────────────────────────────────────────────────────

class TestSharedRegistrySingleton:

    def test_registry_provider_singleton_is_version_registry(self):
        """The shared singleton from registry_provider must be a VersionRegistry."""
        assert isinstance(_version_registry, VersionRegistry)

    def test_audit_use_case_accepts_injected_registry(self, tmp_path):
        """AuditSimulationUseCase must accept an externally provided VersionRegistry."""
        repo = LineageSnapshotRepository(store=None, base_dir=tmp_path)
        custom_registry = VersionRegistry(storage_root=tmp_path)
        uc = AuditSimulationUseCase(lineage_repo=repo, version_registry=custom_registry)
        assert uc._version_registry is custom_registry

    def test_audit_use_case_without_registry_creates_own(self, tmp_path):
        """Without injection, AuditSimulationUseCase creates its own registry (existing fallback)."""
        repo = LineageSnapshotRepository(store=None, base_dir=tmp_path)
        uc = AuditSimulationUseCase(lineage_repo=repo)
        assert isinstance(uc._version_registry, VersionRegistry)

    def test_audit_use_case_with_shared_singleton_uses_it(self, tmp_path):
        """When shared singleton is passed, AuditSimulationUseCase uses it (not a new one)."""
        repo = LineageSnapshotRepository(store=None, base_dir=tmp_path)
        uc = AuditSimulationUseCase(lineage_repo=repo, version_registry=_version_registry)
        assert uc._version_registry is _version_registry


# ─────────────────────────────────────────────────────────────────────────────
# get_audit_use_case DI wiring
# ─────────────────────────────────────────────────────────────────────────────

class TestGetAuditUseCaseWiring:

    def test_get_audit_use_case_passes_shared_registry(self):
        """get_audit_use_case must inject the shared _version_registry singleton."""
        from nexa_engine.db import dependencies as deps
        from nexa_engine.modules.lineage.infrastructure.snapshot_repository import LineageSnapshotRepository

        mock_repo = MagicMock(spec=LineageSnapshotRepository)
        uc = deps.get_audit_use_case(lineage_repo=mock_repo)

        assert isinstance(uc, AuditSimulationUseCase)
        assert uc._version_registry is deps._version_registry

    def test_get_audit_use_case_shared_registry_is_same_as_provider(self):
        """The registry in db.dependencies must be the same object as registry_provider._version_registry."""
        from nexa_engine.db import dependencies as deps
        from nexa_engine.modules.shared.versioning.registry_provider import _version_registry as provider_reg

        assert deps._version_registry is provider_reg


# ─────────────────────────────────────────────────────────────────────────────
# Invalidation benefit: shared registry invalidation visible to audit use case
# ─────────────────────────────────────────────────────────────────────────────

class TestInvalidationVisibility:

    def test_invalidate_clears_cache_shared_by_audit_and_calculate(self, tmp_path):
        """Invalidating the shared registry clears the cache seen by AuditSimulationUseCase."""
        registry = VersionRegistry(storage_root=tmp_path)

        # Prime the cache
        _ = registry.get_current()
        assert registry._cached is not None

        # Invalidate (as activation router would do)
        registry.invalidate_cache()
        assert registry._cached is None

        # Audit use case using the same instance would read fresh next call
        repo = LineageSnapshotRepository(store=None, base_dir=tmp_path)
        uc = AuditSimulationUseCase(lineage_repo=repo, version_registry=registry)
        meta = uc._version_registry.get_current()
        assert isinstance(meta, VersionMetadata)
