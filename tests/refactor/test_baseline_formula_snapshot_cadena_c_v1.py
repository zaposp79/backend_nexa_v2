"""
tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py
===========================================================
CADENA_C_ACTIVE_BASELINE — Guardrails para Cadena C.

Snapshot baseline para Cadena C activa (IA/Automation channels).
Preparado como línea de base ANTES de FORMULA_REFACTOR_PHASE4_CADENA_C.

Tests:
  1. test_engine_runs_request        — el motor ejecuta request Cadena C sin error
  2. test_pricing_result_is_valid    — PricingResult tiene todas las visiones
  3. test_snapshot_parity            — output == snapshot congelado (bit a bit)
  4. test_costo_c_positive           — Cadena C produce costo > 0
  5. test_cadena_c_anchor_values     — anclas numéricas explícitas de Cadena C

Input canónico para Cadena C: tests/refactor/request_cadena_c_active.json
Snapshot congelado: tests/refactor/baseline_formula_snapshot_cadena_c_v1.json
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import backend_nexa  # noqa: F401 — registra alias nexa_engine

from backend_nexa.tests.refactor._v27_provider import build_v27_provider
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.serializers import (
    pricing_result_to_dict,
    validate_visions_complete,
)
from nexa_engine.modules.calculator_motor.validation.contract_validator import ContractValidator

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
REQUEST_PATH = _BACKEND_ROOT / "tests" / "refactor" / "request_cadena_c_active.json"
SNAPSHOT_PATH = Path(__file__).resolve().parent / "baseline_formula_snapshot_cadena_c_v1.json"

SIMULATION_ID = "baseline_cadena_c_v1"


def _run_engine_dict() -> dict:
    payload = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    if "datos_operativos" in payload:
        ContractValidator().raise_if_invalid(payload)
    loader = UserInputLoader()
    user_input = loader.cargar_desde_dict(payload)
    solicitud = SimulationContextBuilder().construir(user_input)
    resultado = NexaPricingEngine(parametrizacion=build_v27_provider()).calcular(solicitud)
    validate_visions_complete(resultado)
    return pricing_result_to_dict(resultado, SIMULATION_ID), resultado


@pytest.fixture(scope="module")
def engine_output():
    full, resultado = _run_engine_dict()
    return full, resultado


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def test_engine_runs_request(engine_output):
    full, _ = engine_output
    assert full is not None
    assert isinstance(full, dict)
    assert full.get("simulation_id") == SIMULATION_ID


def test_pricing_result_is_valid(engine_output):
    full, _ = engine_output
    for vision in ("vision_pyg", "cost_to_serve", "vision_tarifas", "kpis", "pyg_por_mes"):
        assert vision in full, f"falta visión {vision} en PricingResult"
    assert full["pyg_por_mes"], "pyg_por_mes vacío"
    assert len(full["pyg_por_mes"]) == 24, "duración esperada 24 meses"


# Claves volátiles (timestamps de ejecución) que no forman parte del cálculo.
_VOLATILE_KEYS = {"calculated_at", "calculated_at_utc", "generated_at", "timestamp"}


def _normalize(obj):
    """Normaliza para comparación estable (ignora claves volátiles de tiempo)."""
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items() if k not in _VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    return obj


@pytest.mark.baseline
def test_snapshot_parity(engine_output, snapshot):
    """Output actual == snapshot congelado (ignorando timestamps)."""
    full, _ = engine_output
    assert _normalize(full) == _normalize(snapshot), (
        "DRIFT detectado vs snapshot baseline_formula_snapshot_cadena_c_v1.json. "
        "Investigar antes de actualizar el snapshot (regla crítica de paridad)."
    )


@pytest.mark.baseline
def test_costo_c_positive(engine_output):
    """Cadena C debe producir costo > 0 para validar que está activa."""
    _, resultado = engine_output
    # Mes 1 debe tener costo_c positivo
    costo_c_mes1 = resultado.pyg_por_mes[0].costo_c
    assert costo_c_mes1 > 0.0, f"costo_c mes1 debe ser > 0, obtenido {costo_c_mes1}"
    # Total del contrato también
    total_costo_c = sum(m.costo_c for m in resultado.pyg_por_mes)
    assert total_costo_c > 0.0, f"costo_c total debe ser > 0, obtenido {total_costo_c}"


@pytest.mark.baseline
def test_cadena_c_anchor_values(engine_output):
    """Anclas numéricas explícitas para Cadena C."""
    _, resultado = engine_output
    m1 = resultado.pyg_por_mes[0]
    # Cadena C mes 1: equipos transversales (IA Engineer 100% + Data Scientist 50%) + OPEX fijo
    # Esperado: ~17M (salarios + opex fijo integrado)
    # EXCEL V2-8: (inversion_anual/12)*(1+tasa_interes_mensual) = (24M/12)*(1+0.0153) = 2030600
    # costo_c = 99200000 (tarifa+opex+equipo+hitl) + 2030600 = 101230600
    assert math.isclose(m1.costo_c, 101230600.0, rel_tol=1e-6, abs_tol=1e-3), (
        f"DRIFT en costo_c mes1: esperado ~101230600.0, obtenido {m1.costo_c}"
    )
