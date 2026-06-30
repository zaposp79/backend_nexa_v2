"""
tests/refactor/test_baseline_formula_snapshot_v1.py
===================================================
FORMULA_REFACTOR_BASELINE_1 (POST-CANONICALIZATION) — Guardrails.

Snapshot v1 congelado DESPUÉS de INPUT_CONTRACT_CANONICALIZATION_1_CLOSEOUT.
Este es el baseline oficial para validar que refactores posteriores (PHASE1, PHASE2, PHASE3, ...)
no introducen drift numérico.

Tests:
  1. test_engine_runs_request        — el motor ejecuta request.json sin error
  2. test_pricing_result_is_valid    — PricingResult tiene todas las visiones
  3. test_snapshot_parity            — output == snapshot congelado (bit a bit)
  4. test_kpis_anchor_values         — anclas numéricas explícitas de KPIs
  5. test_pyg_month1_anchor          — anclas del P&G mes 1

Input canónico: backend_nexa/request/request.json (SAC METROCUADRADO COM SAS, 24m).
Snapshot congelado: tests/refactor/baseline_formula_snapshot_v1.json
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
REQUEST_PATH = _BACKEND_ROOT / "request" / "request.json"
SNAPSHOT_PATH = Path(__file__).resolve().parent / "baseline_formula_snapshot_v1.json"

SIMULATION_ID = "baseline_formula_v1"


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
        "DRIFT detectado vs snapshot baseline_formula_snapshot_v1.json. "
        "Investigar antes de actualizar el snapshot (regla crítica de paridad)."
    )


@pytest.mark.baseline
def test_kpis_anchor_values(engine_output):
    """Anclas numéricas explícitas — fallan si el refactor mueve un KPI."""
    _, resultado = engine_output
    k = resultado.kpis
    # v2-7 parametrization, SAC METROCUADRADO COM SAS deal (Option B), 260 FTE.
    # PYG-001 V2-8: utilidad y pct_utilidad actualizados — indexación IPC anual aplicada
    # (IPC[2026]=0, IPC[2027]=0.055477, IPC[2028]=0.058401). Costos no cambian.
    # Updated 2026-06-11: Excel input reconciliation — Cadena B OPEX cantidad 1→10000,
    # CAPEX valor_mes 6250000→6345625, volumetria Voz2 cadena_b 1→100000,
    # HITL roles deactivated, mes_aplicacion 1→6, contingencias limits corrected.
    # Updated 2026-06-11: V2-8 Panel!L8 — componente_tecnologico = "20% SMMLV 80% IPC"
    # (rate=0.06616 vs IPC=0.0527); higher Cadena C indexation increases total cost.
    # Updated 2026-06-11: VARIABLE_COMP_LOAD_APPLIED (commit 5a72f81) — NominaCargadaService
    # now loads full commission without pct_cumplimiento_variable(0.70) before carga prestacional,
    # matching Excel V2-8 'Inputs de Nomina'!F62. payroll_a +6% → costo_total_contrato +6.6%.
    anchors = {
        "ingreso_mensual": 1732234704.8687618,
        "costo_cadena_a_promedio": 1324343001.8970432,
        "costo_total_contrato": 54874729751.52904,
        "utilidad_neta_total": 18287365411.604336,
        "pct_utilidad_neta_total": 0.24995683038912478,
        "margen_minimo_requerido": 0.21,
    }
    for attr, expected in anchors.items():
        actual = getattr(k, attr)
        assert math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-6), (
            f"DRIFT en KPI {attr}: esperado {expected}, obtenido {actual}"
        )


@pytest.mark.baseline
def test_pyg_month1_anchor(engine_output):
    """Anclas del P&G mes 1 (ramp-up SAC METROCUADRADO = 0.90 canónico Excel)."""
    _, resultado = engine_output
    m1 = resultado.pyg_por_mes[0]
    assert math.isclose(m1.rampup, 0.90, rel_tol=0, abs_tol=1e-9), "ramp-up mes1 SAC != 0.90"
    # Updated 2026-06-11: VARIABLE_COMP_LOAD_APPLIED (commit 5a72f81)
    assert math.isclose(m1.payroll_a, 1136997207.4145489, rel_tol=1e-9, abs_tol=1e-3)
    assert math.isclose(m1.no_payroll_a, 796078847.579866, rel_tol=1e-9, abs_tol=1e-3)
    assert math.isclose(m1.ica_a, 24469317.151828036, rel_tol=1e-9, abs_tol=1e-3)
    assert math.isclose(m1.gmf_a, 7732304.219977659, rel_tol=1e-9, abs_tol=1e-3)
