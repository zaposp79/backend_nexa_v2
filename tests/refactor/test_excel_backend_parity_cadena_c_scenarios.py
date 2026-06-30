"""
tests/refactor/test_excel_backend_parity_cadena_c_scenarios.py
==============================================================

MULTI_SCENARIO_EXCEL_PARITY_STEP1_CADENA_C_CASES

Validar paridad Excel/Backend para escenarios con Cadena C activa.

Escenarios:
  1. a_plus_b — Cadena A + B (sin C) — baseline (compara contra V2-7 canónico)
  2. a_plus_c — Cadena A + C (sin B) — Cadena C activada, B desactivada
  3. a_b_plus_c — Cadena A + B + C — Cadena C + B ambas activas

Oráculos Excel:
  - Cadena C está en Cadena!C (fila variable) cuando activa
  - PyG incluye costo_c en los totales
  - VisionTarifas se computa siempre (requiere Cadena A)
  - CostToServe incluye distribución C cuando activa

Tests:
  1. test_scenario_a_plus_b_parity — A+B == baseline V2-7
  2. test_scenario_a_plus_c_activates_cadena_c — A+C activa C, desactiva B
  3. test_scenario_a_b_plus_c_includes_both — A+B+C incluye ambas
  4. test_costo_c_consistency — Costo C es consistente cuando condiciones_cadena_c es idéntico
  5. test_costo_b_varies — Costo B varía cuando B se activa/desactiva
  6. test_delta_matrix — Matriz de deltas vs Excel canónico
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import backend_nexa  # noqa: F401

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.serializers import (
    pricing_result_to_dict,
    validate_visions_complete,
)
from nexa_engine.modules.calculator_motor.validation.contract_validator import ContractValidator


_BACKEND_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = _BACKEND_ROOT / "tests" / "refactor" / "fixtures"
SNAPSHOTS_DIR = _BACKEND_ROOT / "tests" / "refactor" / "snapshots_cadena_c"

# Fixture paths
FIXTURE_A_PLUS_B = FIXTURES_DIR / "request_cadena_a_plus_b.json"
FIXTURE_A_PLUS_C = FIXTURES_DIR / "request_cadena_a_plus_c.json"
FIXTURE_A_B_PLUS_C = FIXTURES_DIR / "request_cadena_a_b_plus_c.json"

# Snapshot paths (baseline de referencia)
SNAPSHOT_A_PLUS_B = SNAPSHOTS_DIR / "baseline_a_plus_b_v1.json"
SNAPSHOT_A_PLUS_C = SNAPSHOTS_DIR / "baseline_a_plus_c_v1.json"
SNAPSHOT_A_B_PLUS_C = SNAPSHOTS_DIR / "baseline_a_b_plus_c_v1.json"
CADENA_C_EXCEL_ORACLE_MISSING_REASON = (
    "Cadena C Excel parity is blocked until a real Excel/V2-8 oracle exists; "
    "do not recreate snapshots from backend output."
)


def _run_scenario(fixture_path: Path) -> tuple[dict, object]:
    """Execute engine with scenario fixture."""
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if "datos_operativos" in payload:
        ContractValidator().raise_if_invalid(payload)
    loader = UserInputLoader()
    user_input = loader.cargar_desde_dict(payload)
    solicitud = SimulationContextBuilder().construir(user_input)
    resultado = NexaPricingEngine().calcular(solicitud)
    validate_visions_complete(resultado)
    return pricing_result_to_dict(resultado, "scenario"), resultado


def _load_snapshot(snapshot_path: Path) -> dict:
    """Load snapshot baseline."""
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


# Fixtures for scenarios
@pytest.fixture(scope="module")
def scenario_a_plus_b():
    output, resultado = _run_scenario(FIXTURE_A_PLUS_B)
    return output, resultado


@pytest.fixture(scope="module")
def scenario_a_plus_c():
    output, resultado = _run_scenario(FIXTURE_A_PLUS_C)
    return output, resultado


@pytest.fixture(scope="module")
def scenario_a_b_plus_c():
    output, resultado = _run_scenario(FIXTURE_A_B_PLUS_C)
    return output, resultado


@pytest.fixture(scope="module")
def snapshot_a_plus_b():
    return _load_snapshot(SNAPSHOT_A_PLUS_B)


@pytest.fixture(scope="module")
def snapshot_a_plus_c():
    return _load_snapshot(SNAPSHOT_A_PLUS_C)


@pytest.fixture(scope="module")
def snapshot_a_b_plus_c():
    return _load_snapshot(SNAPSHOT_A_B_PLUS_C)


# ============================================================================
# Tests
# ============================================================================


def test_scenario_a_plus_b_runs(scenario_a_plus_b):
    """A+B scenario runs without error."""
    output, _ = scenario_a_plus_b
    assert output is not None
    assert output.get("simulation_id") == "scenario"
    assert len(output.get("pyg_por_mes", [])) == 24


def test_scenario_a_plus_c_runs(scenario_a_plus_c):
    """A+C scenario runs without error."""
    output, _ = scenario_a_plus_c
    assert output is not None
    assert len(output.get("pyg_por_mes", [])) == 24


def test_scenario_a_b_plus_c_runs(scenario_a_b_plus_c):
    """A+B+C scenario runs without error."""
    output, _ = scenario_a_b_plus_c
    assert output is not None
    assert len(output.get("pyg_por_mes", [])) == 24


def test_costo_c_positive_all_scenarios(
    scenario_a_plus_b, scenario_a_plus_c, scenario_a_b_plus_c
):
    """Cadena C produces costo_c > 0 when condiciones_cadena_c is identical."""
    _, r_ab = scenario_a_plus_b
    _, r_ac = scenario_a_plus_c
    _, r_abc = scenario_a_b_plus_c

    # All should have positive costo_c in M1
    assert r_ab.pyg_por_mes[0].costo_c > 0
    assert r_ac.pyg_por_mes[0].costo_c > 0
    assert r_abc.pyg_por_mes[0].costo_c > 0


def test_costo_c_consistency_across_scenarios(
    scenario_a_plus_b, scenario_a_plus_c, scenario_a_b_plus_c
):
    """Costo C is identical when condiciones_cadena_c is identical.

    This validates that Cadena C calculation is independent of B activation.
    """
    _, r_ab = scenario_a_plus_b
    _, r_ac = scenario_a_plus_c
    _, r_abc = scenario_a_b_plus_c

    # Costo C should be identical across all scenarios (condiciones_cadena_c is the same)
    costo_c_ab_m1 = r_ab.pyg_por_mes[0].costo_c
    costo_c_ac_m1 = r_ac.pyg_por_mes[0].costo_c
    costo_c_abc_m1 = r_abc.pyg_por_mes[0].costo_c

    assert math.isclose(costo_c_ab_m1, costo_c_ac_m1, rel_tol=1e-6), (
        f"Costo C inconsistency: a_plus_b={costo_c_ab_m1}, a_plus_c={costo_c_ac_m1}"
    )
    assert math.isclose(costo_c_abc_m1, costo_c_ab_m1, rel_tol=1e-6), (
        f"Costo C inconsistency: a_b_plus_c={costo_c_abc_m1}, a_plus_b={costo_c_ab_m1}"
    )


def test_costo_b_varies_when_disabled(scenario_a_plus_b, scenario_a_plus_c):
    """Costo B varies when Cadena B is disabled (a_plus_c vs a_plus_b).

    This validates that B is truly being disabled in a_plus_c.
    """
    _, r_ab = scenario_a_plus_b
    _, r_ac = scenario_a_plus_c

    costo_b_ab = r_ab.pyg_por_mes[0].costo_b
    costo_b_ac = r_ac.pyg_por_mes[0].costo_b

    # B should be lower in a_plus_c (partial deactivation)
    assert costo_b_ac < costo_b_ab, (
        f"Costo B should decrease when B is disabled: "
        f"a_plus_b={costo_b_ab}, a_plus_c={costo_b_ac}"
    )


def test_costo_a_consistency_across_scenarios(
    scenario_a_plus_b, scenario_a_plus_c, scenario_a_b_plus_c
):
    """Costo A is identical across all scenarios (A always active with same input).

    This validates that A is independent of B/C activation.
    """
    _, r_ab = scenario_a_plus_b
    _, r_ac = scenario_a_plus_c
    _, r_abc = scenario_a_b_plus_c

    costo_a_ab = r_ab.pyg_por_mes[0].costo_a
    costo_a_ac = r_ac.pyg_por_mes[0].costo_a
    costo_a_abc = r_abc.pyg_por_mes[0].costo_a

    assert math.isclose(costo_a_ab, costo_a_ac, rel_tol=1e-6)
    assert math.isclose(costo_a_abc, costo_a_ab, rel_tol=1e-6)


@pytest.mark.baseline
@pytest.mark.cadena_c_excel_oracle_missing(reason=CADENA_C_EXCEL_ORACLE_MISSING_REASON)
def test_snapshot_parity_a_plus_b(scenario_a_plus_b, snapshot_a_plus_b):
    """Output matches frozen snapshot for a_plus_b scenario."""
    output, _ = scenario_a_plus_b

    # Normalize volatile keys (including simulation_id which can vary)
    volatile_keys = {"calculated_at", "calculated_at_utc", "generated_at", "timestamp", "simulation_id"}

    def normalize(obj):
        if isinstance(obj, dict):
            return {k: normalize(v) for k, v in obj.items() if k not in volatile_keys}
        if isinstance(obj, list):
            return [normalize(v) for v in obj]
        return obj

    assert normalize(output) == normalize(snapshot_a_plus_b), (
        "DRIFT detected vs snapshot baseline_a_plus_b_v1.json"
    )


@pytest.mark.baseline
@pytest.mark.cadena_c_excel_oracle_missing(reason=CADENA_C_EXCEL_ORACLE_MISSING_REASON)
def test_snapshot_parity_a_plus_c(scenario_a_plus_c, snapshot_a_plus_c):
    """Output matches frozen snapshot for a_plus_c scenario."""
    output, _ = scenario_a_plus_c

    volatile_keys = {"calculated_at", "calculated_at_utc", "generated_at", "timestamp", "simulation_id"}

    def normalize(obj):
        if isinstance(obj, dict):
            return {k: normalize(v) for k, v in obj.items() if k not in volatile_keys}
        if isinstance(obj, list):
            return [normalize(v) for v in obj]
        return obj

    assert normalize(output) == normalize(snapshot_a_plus_c), (
        "DRIFT detected vs snapshot baseline_a_plus_c_v1.json"
    )


@pytest.mark.baseline
@pytest.mark.cadena_c_excel_oracle_missing(reason=CADENA_C_EXCEL_ORACLE_MISSING_REASON)
def test_snapshot_parity_a_b_plus_c(scenario_a_b_plus_c, snapshot_a_b_plus_c):
    """Output matches frozen snapshot for a_b_plus_c scenario."""
    output, _ = scenario_a_b_plus_c

    volatile_keys = {"calculated_at", "calculated_at_utc", "generated_at", "timestamp", "simulation_id"}

    def normalize(obj):
        if isinstance(obj, dict):
            return {k: normalize(v) for k, v in obj.items() if k not in volatile_keys}
        if isinstance(obj, list):
            return [normalize(v) for v in obj]
        return obj

    assert normalize(output) == normalize(snapshot_a_b_plus_c), (
        "DRIFT detected vs snapshot baseline_a_b_plus_c_v1.json"
    )


def test_vision_tarifas_present_in_all(scenario_a_plus_b, scenario_a_plus_c, scenario_a_b_plus_c):
    """VisionTarifas is computed in all scenarios (requires Cadena A)."""
    for scenario_output, name in [
        (scenario_a_plus_b, "a_plus_b"),
        (scenario_a_plus_c, "a_plus_c"),
        (scenario_a_b_plus_c, "a_b_plus_c"),
    ]:
        output, _ = scenario_output
        assert output.get("vision_tarifas") is not None, (
            f"vision_tarifas missing in {name}"
        )


def test_cost_to_serve_computed_in_all(scenario_a_plus_b, scenario_a_plus_c, scenario_a_b_plus_c):
    """CostToServe is computed in all scenarios."""
    for scenario_output, name in [
        (scenario_a_plus_b, "a_plus_b"),
        (scenario_a_plus_c, "a_plus_c"),
        (scenario_a_b_plus_c, "a_b_plus_c"),
    ]:
        output, _ = scenario_output
        assert output.get("cost_to_serve") is not None, (
            f"cost_to_serve missing in {name}"
        )


def test_kpis_present_in_all(scenario_a_plus_b, scenario_a_plus_c, scenario_a_b_plus_c):
    """KPIs are computed in all scenarios."""
    for scenario_output, name in [
        (scenario_a_plus_b, "a_plus_b"),
        (scenario_a_plus_c, "a_plus_c"),
        (scenario_a_b_plus_c, "a_b_plus_c"),
    ]:
        output, _ = scenario_output
        assert output.get("kpis") is not None, f"kpis missing in {name}"
        assert output["kpis"].get("ingreso_bruto_total") > 0
        assert output["kpis"].get("costo_mensual_promedio") > 0


# ============================================================================
# Comparison Matrix (informational, no assertions)
# ============================================================================


def test_delta_matrix_printed(scenario_a_plus_b, scenario_a_plus_c, scenario_a_b_plus_c):
    """Print comparison matrix across scenarios (informational)."""
    _, r_ab = scenario_a_plus_b
    _, r_ac = scenario_a_plus_c
    _, r_abc = scenario_a_b_plus_c

    scenarios = {
        "a_plus_b": r_ab,
        "a_plus_c": r_ac,
        "a_b_plus_c": r_abc,
    }

    print("\n\n📊 CADENA_C Scenario Comparison Matrix (M1):")
    print("=" * 110)
    print(
        f"{'Scenario':<15} {'Costo A':>16} {'Costo B':>16} {'Costo C':>16} "
        f"{'Total Costo':>16} {'Ingreso':>16}"
    )
    print("-" * 110)

    for scenario_name, resultado in scenarios.items():
        m1 = resultado.pyg_por_mes[0]
        print(
            f"{scenario_name:<15} {m1.costo_a:>16,.0f} {m1.costo_b:>16,.0f} "
            f"{m1.costo_c:>16,.0f} {m1.costo_total:>16,.0f} {m1.ingreso_bruto:>16,.0f}"
        )


__all__ = [
    "test_scenario_a_plus_b_runs",
    "test_scenario_a_plus_c_runs",
    "test_scenario_a_b_plus_c_runs",
    "test_costo_c_positive_all_scenarios",
    "test_costo_c_consistency_across_scenarios",
    "test_costo_b_varies_when_disabled",
    "test_costo_a_consistency_across_scenarios",
    "test_snapshot_parity_a_plus_b",
    "test_snapshot_parity_a_plus_c",
    "test_snapshot_parity_a_b_plus_c",
    "test_vision_tarifas_present_in_all",
    "test_cost_to_serve_computed_in_all",
    "test_kpis_present_in_all",
    "test_delta_matrix_printed",
]
