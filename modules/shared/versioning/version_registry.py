"""application.versioning.version_registry
==========================================

VersionRegistry — central source of truth for engine version metadata.

Design rules:
    * No mutable global state — instantiated by callers (engine, audit).
    * IO is minimal and cached per instance: hashes are computed only on
      the first request and reused for the lifetime of the registry.
    * Defaults are wired to the v2-7 parametrization storage layout.
    * Backward compatible: when storage is incomplete the registry
      falls back to sensible literals ("unknown", "engine-v2", ...).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Optional

_logger = logging.getLogger("nexa.versioning")


# ---------------------------------------------------------------------------
# Immutable container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VersionMetadata:
    """Immutable metadata snapshot for a single simulation run.

    All fields are JSON-serializable strings/dicts so the snapshot can be
    embedded into lineage graphs and API responses without further
    coercion.
    """

    excel_version: str = "unknown"
    parametrization_version: str = "unknown"
    engine_version: str = "engine-v2"
    api_version: str = "api-v1"
    formula_set: str = "formula-set-v2-7"
    baseline_version: Optional[str] = None
    parametrization_hashes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "excel_version": self.excel_version,
            "parametrization_version": self.parametrization_version,
            "engine_version": self.engine_version,
            "api_version": self.api_version,
            "formula_set": self.formula_set,
            "baseline_version": self.baseline_version,
            "parametrization_hashes": dict(self.parametrization_hashes),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VersionMetadata":
        return cls(
            excel_version=str(data.get("excel_version", "unknown")),
            parametrization_version=str(data.get("parametrization_version", "unknown")),
            engine_version=str(data.get("engine_version", "engine-v2")),
            api_version=str(data.get("api_version", "api-v1")),
            formula_set=str(data.get("formula_set", "formula-set-v2-7")),
            baseline_version=(
                str(data["baseline_version"])
                if data.get("baseline_version") is not None
                else None
            ),
            parametrization_hashes=dict(data.get("parametrization_hashes", {})),
        )

    def with_overrides(self, **overrides: Any) -> "VersionMetadata":
        """Return a copy with the given fields replaced (immutable)."""
        return replace(self, **overrides)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class VersionRegistry:
    """Central registry of versions emitted by the engine.

    Reads:
        * Active parametrization version from
          ``storage/parametrization/<module>/versions.json``.
        * Excel version & file hashes from the baseline manifest at
          ``storage/parametrization/<version>/manifest.json``.
    Falls back to literals when the storage layout is partially
    populated (e.g. unit tests with mock storage roots).
    """

    # Constants — única fuente para engine/api version literals.
    ENGINE_VERSION: str = "engine-v2"
    API_VERSION: str = "api-v1"

    # Module → relative json path inside ``storage/parametrization/<ver>/``.
    PARAM_MODULES = ("hr", "gn", "op")

    def __init__(self, storage_root: Optional[Path] = None) -> None:
        if storage_root is None:
            storage_root = Path(os.getcwd()) / "storage"
        self._storage_root = Path(storage_root)
        self._cached: Optional[VersionMetadata] = None
        self._cached_hashes: Optional[Dict[str, str]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_current(self, baseline_version: Optional[str] = None) -> VersionMetadata:
        """Return current `VersionMetadata` (cached after first call)."""
        if self._cached is not None and baseline_version is None:
            return self._cached

        param_version = self.get_active_parametrization_version()
        excel_version = self._read_excel_version(param_version)
        hashes = self.compute_parametrization_hashes()
        formula_set = self._derive_formula_set(param_version)

        meta = VersionMetadata(
            excel_version=excel_version,
            parametrization_version=param_version,
            engine_version=self.ENGINE_VERSION,
            api_version=self.API_VERSION,
            formula_set=formula_set,
            baseline_version=baseline_version,
            parametrization_hashes=hashes,
        )
        # Only cache the default (no baseline override) snapshot.
        if baseline_version is None:
            self._cached = meta
        return meta

    def invalidate_cache(self) -> None:
        """Drop cached metadata. Useful when storage changes mid-process."""
        self._cached = None
        self._cached_hashes = None

    def get_active_parametrization_version(self) -> str:
        """
        Return the active version identifier from
        ``storage/parametrization/<module>/versions.json``.

        Strategy:
          1. Probe each PARAM_MODULES file for an entry where
             ``is_active`` or ``status == "active"``.
          2. If the manifest exposes a stable ``path`` pointing to
             ``../v2-7/...``, prefer the human-readable ``v2-7`` id over
             a UUID one.
          3. Fall back to ``unknown`` when nothing is detected.
        """
        for module in self.PARAM_MODULES:
            version = self._read_active_from_versions_file(module)
            if version:
                return version
        return "unknown"

    def compute_parametrization_hashes(self) -> Dict[str, str]:
        """
        SHA-256 of each active parametrization JSON.

        Idempotent and cached: subsequent calls return the same dict
        unless ``invalidate_cache()`` is invoked.
        """
        if self._cached_hashes is not None:
            return dict(self._cached_hashes)

        version = self.get_active_parametrization_version()
        hashes: Dict[str, str] = {}
        baseline_dir = self._storage_root / "parametrization" / version
        for module in self.PARAM_MODULES:
            path = baseline_dir / f"{module}.json"
            if not path.exists():
                # fall back to module-specific lookup (e.g. uuid path)
                path = self._resolve_active_path(module)
                if path is None or not path.exists():
                    continue
            try:
                raw = path.read_bytes()
                hashes[module] = hashlib.sha256(raw).hexdigest()
            except OSError as exc:  # pragma: no cover — defensive
                _logger.warning(
                    "[versioning] failed to hash module=%s path=%s err=%s",
                    module,
                    path,
                    exc,
                )
        self._cached_hashes = dict(hashes)
        return dict(hashes)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _read_active_from_versions_file(self, module: str) -> Optional[str]:
        path = self._storage_root / "parametrization" / module / "versions.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        # hr/gn/op use [{"version_id": "...", "is_active": true}, ...]
        if isinstance(data, list):
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                if entry.get("is_active") or entry.get("status") == "active":
                    vid = entry.get("version_id") or entry.get("id")
                    if vid:
                        return str(vid)
        return None

    def _resolve_active_path(self, module: str) -> Optional[Path]:
        """When the active entry has an explicit ``path`` field, resolve it."""
        path = self._storage_root / "parametrization" / module / "versions.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        candidates = []
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
            candidates = data.get("versions", [])

        for entry in candidates:
            if not isinstance(entry, dict):
                continue
            is_active = entry.get("is_active") or entry.get("status") == "active"
            if not is_active:
                continue
            rel = entry.get("path")
            if rel:
                base = self._storage_root / "parametrization" / module
                return (base / rel).resolve()
            vid = entry.get("version_id") or entry.get("id")
            if vid:
                # uuid storage convention: <module>/<uuid>.json
                return self._storage_root / "parametrization" / module / f"{vid}.json"
        return None

    def _read_excel_version(self, param_version: str) -> str:
        """Best-effort: read ``version`` from the v2-x manifest."""
        manifest = (
            self._storage_root / "parametrization" / param_version / "manifest.json"
        )
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                source = data.get("source_file") or data.get("source") or ""
                version = data.get("version")
                if version:
                    return f"V{version.upper().lstrip('V')}" if not str(version).upper().startswith("V") else str(version).upper()
                if source:
                    # crude extraction: "V2-7" out of "Simulador - V2-7.xlsx"
                    for token in source.replace(".", " ").split():
                        u = token.upper()
                        if u.startswith("V") and "-" in u:
                            return u
            except (OSError, json.JSONDecodeError):
                pass
        # fall back to param_version converted (v2-7 → V2-7)
        if param_version and param_version != "unknown":
            return param_version.upper()
        return "unknown"

    @staticmethod
    def _derive_formula_set(param_version: str) -> str:
        if not param_version or param_version == "unknown":
            return "formula-set-v2-7"
        return f"formula-set-{param_version}"

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    @property
    def storage_root(self) -> Path:
        return self._storage_root


__all__ = ["VersionMetadata", "VersionRegistry"]
