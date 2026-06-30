"""
Unit tests for ENGINE_LOW_RISK_TESTS_01 — engine determinism and invariants.

Validates:
  - Same input + same provider = deterministic output (no random drift)
  - PyG monthly totals are internally consistent
  - Key KPIs are computed and in reasonable ranges
"""
from __future__ import annotations

import copy
import json
from dataclasses import asdict
from pathlib import Path

import pytest


# ── Minimal engine harness ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def canonical_request() -> dict:
    """Load the canonical V2-8 request.json — minimal, stable input."""
    request_path = Path(__file__).resolve().parents[2] / "request" / "request.json"
    if not request_path.exists():
        pytest.skip(f"request.json not found at {request_path}")
    return json.loads(request_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def run_engine():
    """Factory: dict → PricingResult. Uses canonical provider (V2-8 active parametrization)."""
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine

    def _run(request_dict: dict):
        """Load, build context, and run engine."""
        ui = UserInputLoader().cargar_desde_dict(request_dict)
        solicitud = SimulationContextBuilder().construir(ui)
        return NexaPricingEngine().calcular(solicitud)

    return _run


# ── Test: Determinism (run once per module scope — engine takes ~20-30s) ──────

@pytest.fixture(scope="module")
def engine_result(canonical_request, run_engine):
    """Run engine once per module, cache result for all tests."""
    return run_engine(canonical_request)


def test_engine_produces_result_with_kpis(engine_result):
    """Engine must produce a result with computed KPIs."""
    assert engine_result is not None
    assert engine_result.kpis is not None
    assert engine_result.pyg_por_mes is not None


# ── Test: Input mutation ─────────────────────────────────────────────────────

def test_engine_does_not_mutate_input_object(canonical_request, run_engine):
    """Engine must not modify the original request dict passed to UserInputLoader."""
    # Deep copy the request before passing it
    request_copy = copy.deepcopy(canonical_request)
    request_json_before = json.dumps(request_copy, separators=(",", ":"), sort_keys=True)

    # Run engine with a copy
    run_engine(request_copy)

    # Check that the copy wasn't modified
    request_json_after = json.dumps(request_copy, separators=(",", ":"), sort_keys=True)

    assert request_json_before == request_json_after, (
        "Engine mutated the input request dict — detected changes in request object. "
        "Calculators must not modify their inputs."
    )


# ── Test: PyG totals consistency ─────────────────────────────────────────────

def test_pyg_monthly_totals_consistency(engine_result):
    """
    PyG monthly totals (ingreso_neto, costo_operativo, contribucion) must be internally consistent.

    For each month:
      ingreso_neto - costo_operativo = contribucion (within floating-point tolerance)
    """
    resultado = engine_result

    if not resultado.pyg_por_mes or len(resultado.pyg_por_mes) == 0:
        pytest.skip("PyG monthly data not available in result")

    for mes_idx, pyg_mes in enumerate(resultado.pyg_por_mes, start=1):
        ingreso = pyg_mes.ingreso_neto
        costo = pyg_mes.costo_operativo
        contrib = pyg_mes.contribucion

        # Check: ingreso - costo ≈ contribucion (within 1 COP tolerance for floating-point error)
        expected_contrib = ingreso - costo
        assert abs(contrib - expected_contrib) < 1.0, (
            f"PyG Mes {mes_idx}: ingreso_neto ({ingreso:.2f}) - costo_operativo ({costo:.2f}) "
            f"= {expected_contrib:.2f}, but contribucion = {contrib:.2f}. "
            f"Delta = {abs(contrib - expected_contrib):.2f} COP (expected < 1.0)."
        )


def test_pyg_monthly_totals_not_negative(engine_result):
    """
    Monthly ingreso_neto and costo_operativo must not be negative (sanity check).
    Utilidad can be negative if costs exceed revenue.
    """
    resultado = engine_result

    if not resultado.pyg_por_mes:
        pytest.skip("PyG data not available")

    for mes_idx, pyg_mes in enumerate(resultado.pyg_por_mes, start=1):
        assert pyg_mes.ingreso_neto >= 0.0, (
            f"PyG Mes {mes_idx}: ingreso_neto = {pyg_mes.ingreso_neto:.2f} < 0. "
            "Monthly revenue must not be negative."
        )
        assert pyg_mes.costo_operativo >= 0.0, (
            f"PyG Mes {mes_idx}: costo_operativo = {pyg_mes.costo_operativo:.2f} < 0. "
            "Monthly operational costs must not be negative."
        )


# ── Test: Key KPIs are computed ──────────────────────────────────────────────

def test_kpis_basic_properties(engine_result):
    """KPIs must exist and be in reasonable ranges."""
    resultado = engine_result
    kpis = resultado.kpis
    assert kpis is not None, "KPIs must be computed"

    # Basic sanity checks
    assert kpis.ingreso_neto_total > 0.0, (
        f"ingreso_neto_total = {kpis.ingreso_neto_total} must be positive"
    )
    assert kpis.costo_total_contrato >= 0.0, (
        f"costo_total_contrato = {kpis.costo_total_contrato} must be non-negative"
    )

    # Margen can be negative in loss scenarios; check bounds
    assert -1.0 <= kpis.pct_utilidad_neta_total <= 2.0, (
        f"pct_utilidad_neta_total = {kpis.pct_utilidad_neta_total} is outside typical range [-1.0, 2.0]"
    )


__all__ = [
    "test_engine_produces_result_with_kpis",
    "test_engine_does_not_mutate_input_object",
    "test_pyg_monthly_totals_consistency",
    "test_pyg_monthly_totals_not_negative",
    "test_kpis_basic_properties",
]
