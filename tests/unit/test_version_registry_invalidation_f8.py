"""
Unit tests for F8 — VersionRegistry invalidation after parametrization activation.

F8 Option A: after successful HR/GN/OP parametrization activation, the shared
VersionRegistry singleton must have its cache invalidated so the next
calculation request reads fresh metadata from storage.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mock_summary():
    """Minimal version summary returned by service.activate()."""
    s = MagicMock()
    s.model_dump.return_value = {"version_id": "v-test", "is_active": True}
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Case 1-3: Successful activation invalidates cache
# ─────────────────────────────────────────────────────────────────────────────

class TestSuccessfulActivationInvalidatesCache:

    def test_hr_activate_invalidates_version_registry(self):
        """Successful HR activation must call _version_registry.invalidate_cache()."""
        from nexa_engine.modules.parametrizacion.hr.api.router import activate_hr

        mock_service = MagicMock()
        mock_service.activate.return_value = _mock_summary()

        with patch(
            "nexa_engine.modules.parametrizacion.hr.api.router._version_registry"
        ) as mock_registry:
            activate_hr(version_id="v-hr-001", service=mock_service)

        mock_registry.invalidate_cache.assert_called_once()

    def test_gn_activate_invalidates_version_registry(self):
        """Successful GN activation must call _version_registry.invalidate_cache()."""
        from nexa_engine.modules.parametrizacion.gn.api.router import activate_gn

        mock_service = MagicMock()
        mock_service.activate.return_value = _mock_summary()

        with patch(
            "nexa_engine.modules.parametrizacion.gn.api.router._version_registry"
        ) as mock_registry:
            activate_gn(version_id="v-gn-001", service=mock_service)

        mock_registry.invalidate_cache.assert_called_once()

    def test_op_activate_invalidates_version_registry(self):
        """Successful OP activation must call _version_registry.invalidate_cache()."""
        from nexa_engine.modules.parametrizacion.op.api.router import activate_op

        mock_service = MagicMock()
        mock_service.activate.return_value = _mock_summary()

        with patch(
            "nexa_engine.modules.parametrizacion.op.api.router._version_registry"
        ) as mock_registry:
            activate_op(version_id="v-op-001", service=mock_service)

        mock_registry.invalidate_cache.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Case 4-6: Failed activation does NOT invalidate cache
# ─────────────────────────────────────────────────────────────────────────────

class TestFailedActivationDoesNotInvalidateCache:

    def test_hr_activate_not_found_does_not_invalidate(self):
        """Failed HR activation (NotFoundError) must NOT invalidate cache."""
        from nexa_engine.modules.shared.exceptions import NotFoundError
        from nexa_engine.modules.parametrizacion.hr.api.router import activate_hr

        mock_service = MagicMock()
        mock_service.activate.side_effect = NotFoundError("HRVersion", "v-missing")

        with patch(
            "nexa_engine.modules.parametrizacion.hr.api.router._version_registry"
        ) as mock_registry:
            activate_hr(version_id="v-missing", service=mock_service)

        mock_registry.invalidate_cache.assert_not_called()

    def test_gn_activate_not_found_does_not_invalidate(self):
        """Failed GN activation (NotFoundError) must NOT invalidate cache."""
        from nexa_engine.modules.shared.exceptions import NotFoundError
        from nexa_engine.modules.parametrizacion.gn.api.router import activate_gn

        mock_service = MagicMock()
        mock_service.activate.side_effect = NotFoundError("GNVersion", "v-missing")

        with patch(
            "nexa_engine.modules.parametrizacion.gn.api.router._version_registry"
        ) as mock_registry:
            activate_gn(version_id="v-missing", service=mock_service)

        mock_registry.invalidate_cache.assert_not_called()

    def test_op_activate_not_found_does_not_invalidate(self):
        """Failed OP activation (NotFoundError) must NOT invalidate cache."""
        from nexa_engine.modules.shared.exceptions import NotFoundError
        from nexa_engine.modules.parametrizacion.op.api.router import activate_op

        mock_service = MagicMock()
        mock_service.activate.side_effect = NotFoundError("OPVersion", "v-missing")

        with patch(
            "nexa_engine.modules.parametrizacion.op.api.router._version_registry"
        ) as mock_registry:
            activate_op(version_id="v-missing", service=mock_service)

        mock_registry.invalidate_cache.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Structural: registry_provider singleton is shared
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistryProviderSingleton:

    def test_registry_provider_exports_singleton(self):
        """registry_provider must export a VersionRegistry instance."""
        from nexa_engine.modules.shared.versioning.registry_provider import _version_registry
        from nexa_engine.modules.shared.versioning.version_registry import VersionRegistry

        assert isinstance(_version_registry, VersionRegistry)

    def test_invalidate_cache_clears_cached_metadata(self, tmp_path):
        """invalidate_cache() must clear _cached so next get_current() re-reads storage."""
        from nexa_engine.modules.shared.versioning.version_registry import VersionRegistry

        registry = VersionRegistry(storage_root=tmp_path)

        # Prime the cache
        meta1 = registry.get_current()
        assert registry._cached is not None

        # Invalidate
        registry.invalidate_cache()
        assert registry._cached is None

        # Next call re-reads (returns a new object)
        meta2 = registry.get_current()
        assert registry._cached is not None

    def test_calculate_dependencies_exports_version_registry(self):
        """calculate_dependencies must export _version_registry for wiring."""
        from nexa_engine.modules.calculator.api import calculate_dependencies as deps
        from nexa_engine.modules.shared.versioning.version_registry import VersionRegistry

        assert hasattr(deps, "_version_registry")
        assert isinstance(deps._version_registry, VersionRegistry)
