"""Helper to build a ParametrizationProvider pinned to v2-7 storage files.

Used in snapshot tests to decouple them from the active production parametrization.
Snapshots (v0, v1, cadena_c) were generated with v2-7 (SMMLV=1,750,905) and must
continue to validate against those exact values regardless of which version is active.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import backend_nexa  # noqa: F401 — registers nexa_engine alias

from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver

_V27_DIR = Path(__file__).resolve().parents[2] / "storage" / "parametrization" / "v2-7"


class _V27Repo:
    """Stub repo that returns v2-7 data from filesystem, bypassing versions.json lookup."""

    def __init__(self, path: Path) -> None:
        self._data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    def get_active_data(self) -> Dict[str, Any]:
        return self._data


def build_v27_provider() -> ParametrizationProvider:
    """Return a ParametrizationProvider backed exclusively by v2-7 parametrization files."""
    resolver = ParametrizationResolver(
        hr_repo=_V27Repo(_V27_DIR / "hr.json"),
        gn_repo=_V27Repo(_V27_DIR / "gn.json"),
        op_repo=_V27Repo(_V27_DIR / "op.json"),
    )
    return ParametrizationProvider.build(resolver)
