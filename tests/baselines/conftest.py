"""Conftest for V2-7 baseline regression tests."""
from __future__ import annotations

import sys
from pathlib import Path

THIS_DIR    = Path(__file__).resolve().parent
BACKEND_ROOT = THIS_DIR.parent.parent
REPO_ROOT    = BACKEND_ROOT.parent

# Make both 'backend_nexa' and 'nexa_engine' importable
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import backend_nexa  # noqa: E402, F401
