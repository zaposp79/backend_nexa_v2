"""Conftest for tests/api/ — WAVE 13."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

THIS_DIR     = Path(__file__).resolve().parent
BACKEND_ROOT = THIS_DIR.parent.parent
REPO_ROOT    = BACKEND_ROOT.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import backend_nexa_v2  # noqa: E402, F401  registers `nexa_engine` alias


@pytest.fixture(scope="session")
def project_root() -> Path:
    return BACKEND_ROOT
