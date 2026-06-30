"""
tests/golden/conftest.py
=========================
Fixtures compartidos para los tests de certificación final Excel V2-5.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Asegurar que el proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: E402, F401  — registra alias nexa_engine

GOLDEN_DIR = Path(__file__).parent


@pytest.fixture(scope="session")
def golden_data() -> dict:
    with open(GOLDEN_DIR / "bancamia_sac_v25_golden.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def input_path() -> Path:
    return GOLDEN_DIR / "bancamia_sac_v25_input.json"


@pytest.fixture(scope="session")
def resultado_v25(input_path):
    """Ejecuta el motor con el input canónico V2-5 y retorna PricingResult."""
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine

    ui = UserInputLoader().cargar(input_path)
    solicitud = SimulationContextBuilder().construir(ui)
    return NexaPricingEngine().calcular(solicitud)
