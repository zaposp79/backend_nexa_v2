from __future__ import annotations

from types import SimpleNamespace

import inspect

from nexa_engine.modules.calculator_motor.formulas.tarifas import build_vision_tarifas_result
from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import (
    VisionTarifasCalculator as MotorVisionTarifasCalculator,
)
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.shared.models import ResultadoVisionTarifas
from tests.parity.conftest import CANONICAL_INPUT


def test_calculator_motor_owned_builder_returns_resultado_vision_tarifas():
    resultado = build_vision_tarifas_result(
        perfiles_cadena_a=[],
        parametros_cadena_b=SimpleNamespace(canales=[]),
        panel=SimpleNamespace(),
        pyg_por_mes=[],
    )

    assert isinstance(resultado, ResultadoVisionTarifas)


def test_calculator_motor_owns_vision_tarifas_calculator_implementation():
    source = inspect.getsource(MotorVisionTarifasCalculator)
    assert "class VisionTarifasCalculator" in source
    assert "def calcular(" in source


def test_engine_populates_vision_tarifas_through_calculator_motor_builder(monkeypatch):
    from nexa_engine.modules.calculator_motor import engine as engine_mod

    sentinel = ResultadoVisionTarifas(canales=[])

    def _fake_builder(**kwargs):
        assert "pyg_por_mes" in kwargs
        assert "panel" in kwargs
        return sentinel

    monkeypatch.setattr(engine_mod, "build_vision_tarifas_result", _fake_builder)

    engine = NexaPricingEngine()
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder

    import json
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(CANONICAL_INPUT, f, default=str)
        temp_path = Path(f.name)

    try:
        ui = UserInputLoader().cargar(temp_path)
        req = SimulationContextBuilder().construir(ui)
        result = engine.calcular(req)
    finally:
        temp_path.unlink(missing_ok=True)

    assert result.vision_tarifas is sentinel
