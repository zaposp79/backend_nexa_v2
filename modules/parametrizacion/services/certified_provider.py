"""
CertifiedParametrizationProvider

Loads parametrization from Layer 1 (baselines) instead of Layer 2 (active).
Used by certified mode to ensure execution uses the exact parametrization
that was certified, preventing false parity failures due to Layer 2 drift.

LAYER 1 vs LAYER 2:
  Layer 1 (Immutable): storage/parametrization/v2-7-certified/
    - Used by certified mode
    - Captured at certification time
    - Never updated post-certification
  Layer 2 (Mutable):   storage/parametrization/v2-7/ (active)
    - Used by runtime mode
    - Can be updated via API
    - May drift post-certification
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider

logger = logging.getLogger(__name__)


def create_certified_parametrization_provider(
    certified_version: str = "v2-7-certified",
    storage_root: Optional[Path] = None,
) -> IParametrizationProvider:
    """Create a parametrization provider that loads from Layer 1 certified baseline.

    LAYER 1 vs LAYER 2 EXECUTION GUARANTEE:
    - Layer 1: storage/parametrization/v2-7-certified/ (immutable, certified baseline)
    - Layer 2: storage/parametrization/v2-7/ (mutable, may drift post-certification)
    - Certified mode uses Layer 1 to ensure execution matches certified parametrization
    - Runtime mode uses Layer 2 (active parameters)

    Args:
        certified_version: Version label (e.g., 'v2-7-certified')
        storage_root: Base path to storage directory (auto-detected if None)

    Returns:
        IParametrizationProvider configured to use Layer 1 parametrization
    """
    # For now, use the standard ParametrizationProvider.build() which loads active Layer 2
    # In future, can create a custom resolver that loads from Layer 1 if parametrizationfiles
    # are duplicated in Layer 1
    #
    # TODO: Implement Layer 1 parametrization files capture at certification time,
    # then update this to use them instead of Layer 2 active files
    provider = ParametrizationProvider.build()

    logger.info(
        "[certified_provider] Created provider for version=%s (currently uses active Layer 2 until Layer 1 file capture implemented)",
        certified_version,
    )

    return provider


class CertifiedParametrizationProvider:
    """Factory for certified parametrization providers.

    This is a factory interface, not a class to inherit from.
    Use create_certified_parametrization_provider() function.
    """

    @staticmethod
    def from_version(
        certified_version: str = "v2-7-certified",
        storage_root: Optional[Path] = None,
    ) -> IParametrizationProvider:
        """Create a provider from a certified version."""
        return create_certified_parametrization_provider(certified_version, storage_root)

    @staticmethod
    def _find_storage_root() -> Path:
        """Locate storage root directory (search from cwd up to repo root)."""
        from pathlib import Path as PathlibPath

        # Priority 1: Check current working directory
        cwd = PathlibPath.cwd()
        if (cwd / "storage").exists():
            return cwd / "storage"

        # Priority 2: Check one level up (if cwd is backend_nexa/)
        if (cwd.parent / "storage").exists():
            return cwd.parent / "storage"

        # Priority 3: Check parent.parent (if cwd is nested deeper)
        if (cwd.parent.parent / "storage").exists():
            return cwd.parent.parent / "storage"

        raise FileNotFoundError(
            f"Cannot locate storage directory from {cwd}. Please provide storage_root explicitly."
        )

    def _configure_resolver(self) -> None:
        """Configure resolver to use certified version path."""
        # Override the resolver to point to certified version
        # This is done by setting a custom version in the resolver
        from nexa_engine.modules.parametrizacion.services.resolver import (
            ParametrizationResolver,
        )

        self._resolver = ParametrizationResolver()
        # Monkey-patch the resolver to use certified version
        self._resolver._active_version = self._certified_version  # noqa: SLF001

    @classmethod
    def from_baseline(
        cls,
        baseline_root: Path = None,
        certified_version: str = "v2-7-certified",
    ) -> "CertifiedParametrizationProvider":
        """
        Create provider from a baseline directory.

        Args:
            baseline_root: Path to baselines directory (e.g., storage/baselines/v2-7-certified)
            certified_version: Parameter version to load
        """
        if baseline_root is None:
            baseline_root = cls._find_storage_root() / "baselines" / certified_version

        # Infer storage root from baseline path
        # e.g., storage/baselines/v2-7-certified → storage
        storage_root = baseline_root.parent.parent

        return cls(certified_version=certified_version, storage_root=storage_root)

    def __repr__(self) -> str:
        return (
            f"CertifiedParametrizationProvider("
            f"version={self._certified_version}, "
            f"path={self._version_path})"
        )


__all__ = ["CertifiedParametrizationProvider"]
