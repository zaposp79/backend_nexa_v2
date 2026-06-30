"""pytest fixtures for tests/versioning/ — WAVE 14."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# tests/versioning/ → tests/ → backend_nexa/ → NEXA/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: E402, F401


@pytest.fixture
def fake_storage(tmp_path: Path) -> Path:
    """
    Build a minimal valid ``storage/parametrization`` layout so that
    `VersionRegistry` resolves a deterministic version without depending
    on the production parametrization tree.
    """
    root = tmp_path / "storage" / "parametrization"
    v_dir = root / "v2-7"
    v_dir.mkdir(parents=True)

    # active version JSONs (real bytes — used for SHA-256)
    (v_dir / "hr.json").write_text(json.dumps({"hr": "ok"}), encoding="utf-8")
    (v_dir / "gn.json").write_text(json.dumps({"gn": "ok"}), encoding="utf-8")
    (v_dir / "op.json").write_text(json.dumps({"op": "ok"}), encoding="utf-8")
    (v_dir / "manifest.json").write_text(
        json.dumps(
            {
                "version": "v2-7",
                "source_file": "Nexa - Pricing - Simulador - V2-7.xlsx",
            }
        ),
        encoding="utf-8",
    )

    # versions.json files (active = v2-7)
    for module in ("hr", "gn", "op"):
        (root / module).mkdir()
        (root / module / "versions.json").write_text(
            json.dumps(
                [
                    {
                        "version_id": "v2-7",
                        "is_active": True,
                        "path": f"../v2-7/{module}.json",
                    }
                ]
            ),
            encoding="utf-8",
        )
    return tmp_path / "storage"
