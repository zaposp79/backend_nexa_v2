"""Root conftest — shared fixtures available to every test module.

Registers the `nexa_engine` alias (via `import backend_nexa_v2`) and provides
a default FastAPI app fixture for tests that need a running server.

Tests that need specific settings (production CORS, specific DB backend)
should call create_app() directly with an explicit AppSettings instance.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure the directory containing `backend_nexa_v2/` is on sys.path.
# parents[2] from backend_nexa_v2/tests/conftest.py → project root's parent.
_PROJECT_PARENT = Path(__file__).resolve().parents[2]
if str(_PROJECT_PARENT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_PARENT))

import backend_nexa_v2  # noqa: E402, F401 — registers nexa_engine alias

from nexa_engine.app import create_app  # noqa: E402


@pytest.fixture(scope="session")
def default_app():
    """Single-session FastAPI app built with development defaults."""
    return create_app()


@pytest.fixture(scope="session")
def default_client(default_app):
    """TestClient over the default development app (lifespan included)."""
    with TestClient(default_app) as c:
        yield c
