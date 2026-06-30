"""Shared fixtures for the transversal persistence (FASE DB) test suites."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root's parent is on sys.path so `backend_nexa` is importable
# (mirrors tests/parity/conftest.py). parents[3] == directory containing
# backend_nexa/ for a file at backend_nexa/tests/db/conftest.py.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: E402, F401  (registers nexa_engine alias)
