"""Helper to build a ParametrizationProvider pinned to v2-8 storage files.

Used in parity tests that validate CTS and formula outputs against
Excel V2-8 (HR_productiva_2026-06-10.xlsx, GN/OP V2-8 productiva).

Snapshot was frozen on 2026-06-11 from the active V2-8 parametrization:
  HR: version_id=6506b1fa-b0d2-4bf9-9e87-d27f3f4fc73b (HR_productiva_2026-06-10.xlsx)
  GN: version_id=60031c65-c3db-45cf-ae4f-a24658322aa1 (GN_productiva_2026-06-10.xlsx)
  OP: version_id=14da70ab-b199-4587-8793-34b8a872ab66 (OP_productiva_2026-06-10.xlsx)

Use ONLY in parity tests — not in production.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import backend_nexa  # noqa: F401 — registers nexa_engine alias

from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
from nexa_engine.modules.parametrizacion.services.resolver import ParametrizationResolver

_V28_DIR = Path(__file__).resolve().parents[2] / "storage" / "parametrization" / "v2-8"


class _V28Repo:
    """Stub repo that returns v2-8 data from filesystem, bypassing versions.json lookup."""

    def __init__(self, path: Path) -> None:
        self._data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    def get_active_data(self) -> Dict[str, Any]:
        return self._data


def build_v28_provider() -> ParametrizationProvider:
    """Return a ParametrizationProvider backed exclusively by v2-8 parametrization files.

    HR snapshot trazado desde Excel HR_productiva_2026-06-10.xlsx (V2-8).
    Usar SOLO en tests parity — no en producción.
    """
    resolver = ParametrizationResolver(
        hr_repo=_V28Repo(_V28_DIR / "hr.json"),
        gn_repo=_V28Repo(_V28_DIR / "gn.json"),
        op_repo=_V28Repo(_V28_DIR / "op.json"),
    )
    return ParametrizationProvider.build(resolver)
