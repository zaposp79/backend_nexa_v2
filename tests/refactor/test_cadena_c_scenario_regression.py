"""
tests/refactor/test_cadena_c_scenario_regression.py

BACKEND_SCENARIO_REGRESSION_ONLY — Validar que el motor no regresiona cuando
condiciones_cadena_c varían estructuralmente.

NOTA: Sin oráculos Excel reales, esto es validación de REGRESIÓN, no certificación de paridad.
Status: ⚠️ PARITY PENDING UNTIL EXCEL ORACLE EXISTS

Escenarios ejecutables:
  ✅ b_plus_c — A+B+C (alta inversión, múltiples equipos)
  ✅ a_plus_b_plus_c — A+B+C (media inversión, equipo único)
  ❌ c_only — C solo (sin A) → falla: escenarios_comerciales requiere Cadena A
"""
import json
import math
from pathlib import Path

import pytest

import backend_nexa  # noqa: F401

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict
from nexa_engine.modules.calculator_motor.validation.contract_validator import ContractValidator


_BACKEND_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = _BACKEND_ROOT / "tests" / "refactor" / "fixtures"

FIXTURE_B_PLUS_C = FIXTURES_DIR / "request_cadena_b_plus_c.json"
FIXTURE_A_PLUS_B_PLUS_C = FIXTURES_DIR / "request_cadena_a_plus_b_plus_c.json"
FIXTURE_C_ONLY = FIXTURES_DIR / "request_cadena_c_only.json"


def _run_scenario(fixture_path: Path) -> tuple[dict, object]:
    """Execute engine with scenario fixture."""
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if "datos_operativos" in payload:
        ContractValidator().raise_if_invalid(payload)
    loader = UserInputLoader()
    user_input = loader.cargar_desde_dict(payload)
    solicitud = SimulationContextBuilder().construir(user_input)
    resultado = NexaPricingEngine().calcular(solicitud)
    return pricing_result_to_dict(resultado, "regression"), resultado


# ============================================================================
# Fixture Execution (Regression)
# ============================================================================


@pytest.fixture(scope="module")
def scenario_b_plus_c():
    output, resultado = _run_scenario(FIXTURE_B_PLUS_C)
    return output, resultado


@pytest.fixture(scope="module")
def scenario_a_plus_b_plus_c():
    output, resultado = _run_scenario(FIXTURE_A_PLUS_B_PLUS_C)
    return output, resultado


# ============================================================================
# Test: C_ONLY is not viable (architectural constraint)
# ============================================================================


def test_c_only_fails_architectural_constraint():
    """C_ONLY (without Cadena A) must fail due to escenarios_comerciales validation.

    Architectural constraint: VisionTarifas requires Cadena A.
    When A is deactivated, escenarios_comerciales references orphan canales.

    Status: EXPECTED FAILURE — Not a bug, but an architecture requirement.
    """
    with pytest.raises(ValueError, match="CONTRACT_VALIDATION_ERROR.*orphan canal"):
        _run_scenario(FIXTURE_C_ONLY)


# ============================================================================
# Test: Executable Scenarios Run Without Error
# ============================================================================


def test_b_plus_c_runs(scenario_b_plus_c):
    """B+C scenario executes without error."""
    output, _ = scenario_b_plus_c
    assert output is not None
    assert output.get("simulation_id") == "regression"
    assert len(output.get("pyg_por_mes", [])) == 24


def test_a_plus_b_plus_c_runs(scenario_a_plus_b_plus_c):
    """A+B+C scenario executes without error."""
    output, _ = scenario_a_plus_b_plus_c
    assert output is not None
    assert len(output.get("pyg_por_mes", [])) == 24


# ============================================================================
# Test: Costo C Regression (Differs Between Scenarios)
# ============================================================================


def test_costo_c_differs_across_scenarios(scenario_b_plus_c, scenario_a_plus_b_plus_c):
    """Costo C must differ when condiciones_cadena_c differ structurally.

    This is a REGRESSION test, not parity. It validates that changes to
    condiciones_cadena_c produce different outputs.
    """
    _, r_bpc = scenario_b_plus_c
    _, r_abc = scenario_a_plus_b_plus_c

    costo_c_bpc = r_bpc.pyg_por_mes[0].costo_c
    costo_c_abc = r_abc.pyg_por_mes[0].costo_c

    # Different tariffs/opex/capex should produce different costo_c
    assert costo_c_bpc != costo_c_abc, (
        f"Costo C must differ: b_plus_c={costo_c_bpc:,.0f}, "
        f"a_plus_b_plus_c={costo_c_abc:,.0f}"
    )

    # Verify plausible delta (not wild drift)
    pct_delta = abs(costo_c_bpc - costo_c_abc) / costo_c_bpc
    assert pct_delta < 0.1, (
        f"Costo C delta too large ({pct_delta:.1%}). "
        f"Possible calculation regression."
    )


def test_costo_a_and_b_consistent_across_scenarios(scenario_b_plus_c, scenario_a_plus_b_plus_c):
    """Costo A and B must remain constant (same volumetria, same condiciones_cadena_a/b)."""
    _, r_bpc = scenario_b_plus_c
    _, r_abc = scenario_a_plus_b_plus_c

    costo_a_bpc = r_bpc.pyg_por_mes[0].costo_a
    costo_a_abc = r_abc.pyg_por_mes[0].costo_a
    costo_b_bpc = r_bpc.pyg_por_mes[0].costo_b
    costo_b_abc = r_abc.pyg_por_mes[0].costo_b

    # A and B should be identical (same inputs)
    assert math.isclose(costo_a_bpc, costo_a_abc, rel_tol=1e-6), (
        f"Costo A inconsistency: {costo_a_bpc} vs {costo_a_abc}"
    )
    assert math.isclose(costo_b_bpc, costo_b_abc, rel_tol=1e-6), (
        f"Costo B inconsistency: {costo_b_bpc} vs {costo_b_abc}"
    )


# ============================================================================
# Test: Vision Completeness (Regression)
# ============================================================================


def test_vision_tarifas_exists_in_both(scenario_b_plus_c, scenario_a_plus_b_plus_c):
    """VisionTarifas must be computed in both scenarios (Cadena A active)."""
    for scenario_name, scenario_data in [
        ("b_plus_c", scenario_b_plus_c),
        ("a_plus_b_plus_c", scenario_a_plus_b_plus_c),
    ]:
        output, _ = scenario_data
        assert output.get("vision_tarifas") is not None, (
            f"vision_tarifas missing in {scenario_name}"
        )


def test_cost_to_serve_computed_in_both(scenario_b_plus_c, scenario_a_plus_b_plus_c):
    """CostToServe must be computed in both scenarios."""
    for scenario_name, scenario_data in [
        ("b_plus_c", scenario_b_plus_c),
        ("a_plus_b_plus_c", scenario_a_plus_b_plus_c),
    ]:
        output, _ = scenario_data
        assert output.get("cost_to_serve") is not None, (
            f"cost_to_serve missing in {scenario_name}"
        )


def test_kpis_computed_in_both(scenario_b_plus_c, scenario_a_plus_b_plus_c):
    """KPIs must be computed in both scenarios."""
    for scenario_name, scenario_data in [
        ("b_plus_c", scenario_b_plus_c),
        ("a_plus_b_plus_c", scenario_a_plus_b_plus_c),
    ]:
        output, _ = scenario_data
        assert output.get("kpis") is not None, f"kpis missing in {scenario_name}"
        assert output["kpis"].get("ingreso_bruto_total") > 0
        assert output["kpis"].get("costo_mensual_promedio") > 0


# ============================================================================
# Test: Output Structure Regression
# ============================================================================


def test_pyg_por_mes_structure_valid(scenario_b_plus_c, scenario_a_plus_b_plus_c):
    """PyG monthly structure must be complete and valid."""
    for scenario_name, scenario_data in [
        ("b_plus_c", scenario_b_plus_c),
        ("a_plus_b_plus_c", scenario_a_plus_b_plus_c),
    ]:
        output, resultado = scenario_data
        pyg_list = output.get("pyg_por_mes", [])

        assert len(pyg_list) == 24, f"{scenario_name}: 24 months expected"

        for mes, pyg_entry in enumerate(pyg_list, start=1):
            assert pyg_entry.get("mes") == mes
            assert pyg_entry.get("ingreso_bruto") > 0, (
                f"{scenario_name} M{mes}: ingreso_bruto must be > 0"
            )
            assert pyg_entry.get("costo_total") > 0, (
                f"{scenario_name} M{mes}: costo_total must be > 0"
            )


# ============================================================================
# Informational: Comparison Matrix
# ============================================================================


def test_scenario_comparison_matrix(scenario_b_plus_c, scenario_a_plus_b_plus_c):
    """Print scenario comparison matrix for documentation."""
    _, r_bpc = scenario_b_plus_c
    _, r_abc = scenario_a_plus_b_plus_c

    scenarios = {
        "b_plus_c (HIGH)": r_bpc,
        "a_plus_b_plus_c (MEDIUM)": r_abc,
    }

    print("\n\n📊 CADENA_C Scenario Regression Matrix (M1):")
    print("=" * 120)
    print(
        f"{'Scenario':<25} {'Costo A':>16} {'Costo B':>16} {'Costo C':>16} "
        f"{'Total Costo':>16} {'Ingreso':>16} {'Contribución':>16}"
    )
    print("-" * 120)

    for scenario_name, resultado in scenarios.items():
        m1 = resultado.pyg_por_mes[0]
        print(
            f"{scenario_name:<25} {m1.costo_a:>16,.0f} {m1.costo_b:>16,.0f} "
            f"{m1.costo_c:>16,.0f} {m1.costo_total:>16,.0f} "
            f"{m1.ingreso_bruto:>16,.0f} {m1.contribucion:>16,.0f}"
        )

    print("\n✅ Matrix complete. Status: REGRESSION_ONLY (no Excel oracle)")


__all__ = [
    "test_c_only_fails_architectural_constraint",
    "test_b_plus_c_runs",
    "test_a_plus_b_plus_c_runs",
    "test_costo_c_differs_across_scenarios",
    "test_costo_a_and_b_consistent_across_scenarios",
    "test_vision_tarifas_exists_in_both",
    "test_cost_to_serve_computed_in_both",
    "test_kpis_computed_in_both",
    "test_pyg_por_mes_structure_valid",
    "test_scenario_comparison_matrix",
]
