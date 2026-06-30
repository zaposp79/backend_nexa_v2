"""pytest fixtures for tests/lineage/ — WAVE 10."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# tests/lineage/conftest.py → tests/lineage/ → tests/ → backend_nexa/ → NEXA/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: E402, F401


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def tmp_lineage_dir(tmp_path: Path) -> Path:
    out = tmp_path / "lineage"
    out.mkdir(parents=True, exist_ok=True)
    return out
