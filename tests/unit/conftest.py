"""pytest fixtures comunes para tests unitarios del motor NEXA."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# tests/unit/ is 4 levels below the project root:
# tests/unit/conftest.py → tests/unit/ → tests/ → backend_nexa/ → NEXA/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Trigger nexa_engine alias registration
import backend_nexa  # noqa: E402, F401


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT
