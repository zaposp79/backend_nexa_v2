"""
GAP-CADENA-A-FASE4 — Validación de wiring del margen (warning, no destructiva).

El ingreso de Cadena A usa `panel.margen` (input). El storage tiene el margen por
servicio (`get_margen_minimo`). Si difieren > 0.001, el motor emite un WARNING logged
SIN cambiar el valor usado. Estos tests verifican el warning (y su ausencia).

Ver engine.py :: NexaPricingEngine._calcular_pipeline ("[MARGEN_WIRING]").
"""

import json
import logging
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import backend_nexa  # noqa: F401

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider

_FIXTURE = Path(__file__).resolve().parent.parent.parent / "test_cases" / "input" / "solo_cadena_a.json"
_LOGGER = "nexa_engine.modules.calculator_motor.engine"
_MARKER = "[MARGEN_WIRING]"


def _run(margen: float):
    """Ejecuta el motor con solo_cadena_a.json forzando panel.margen=`margen`."""
    raw = json.loads(_FIXTURE.read_text())
    raw["panel_de_control"]["margen"] = margen
    provider = ParametrizationProvider.build()
    ui = UserInputLoader().cargar_desde_dict(raw)
    sol = SimulationContextBuilder(provider).construir(ui)
    return NexaPricingEngine(parametrizacion=provider).calcular(sol)


COBRANZAS_MARGEN_MINIMO = 0.17


def test_warning_cuando_margen_input_difiere_de_storage(caplog):
    # Cobranzas → get_margen_minimo = 0.17; usamos input 0.1339 (Δ > 0.001) → warning
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        _run(0.1339)
    msgs = [r.getMessage() for r in caplog.records if _MARKER in r.getMessage()]
    assert msgs, "Se esperaba un WARNING [MARGEN_WIRING] cuando margen input != storage"
    assert "0.1339" in msgs[0] and str(COBRANZAS_MARGEN_MINIMO) in msgs[0]


def test_sin_warning_cuando_margen_coincide(caplog):
    # Cobranzas → get_margen_minimo = 0.17; usamos input 0.17 (Δ = 0 < 0.001) → sin warning
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        _run(COBRANZAS_MARGEN_MINIMO)
    msgs = [r.getMessage() for r in caplog.records if _MARKER in r.getMessage()]
    assert not msgs, f"No se esperaba WARNING [MARGEN_WIRING] cuando coinciden; got: {msgs}"
