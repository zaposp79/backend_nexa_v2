"""
tests/refactor/test_cadena_c_fixtures_validation.py

Validate that Cadena C fixtures have real structural differences, not just toggle flags.
These tests run BEFORE engine execution to ensure fixture integrity.

Rules:
- Fixtures must have differing condiciones_cadena_c
- C_ONLY must deactivate A and B
- B_PLUS_C and A_PLUS_B_PLUS_C must keep A active
- Each scenario must have unique tariff/opex/capex values
"""
import json
from pathlib import Path

import pytest


_BACKEND_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = _BACKEND_ROOT / "tests" / "refactor" / "fixtures"

FIXTURE_C_ONLY = FIXTURES_DIR / "request_cadena_c_only.json"
FIXTURE_B_PLUS_C = FIXTURES_DIR / "request_cadena_b_plus_c.json"
FIXTURE_A_PLUS_B_PLUS_C = FIXTURES_DIR / "request_cadena_a_plus_b_plus_c.json"


def _load_fixture(path: Path) -> dict:
    """Load fixture JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


# ============================================================================
# CADENA Activation Tests
# ============================================================================


def test_c_only_deactivates_a_and_b():
    """C_ONLY scenario must deactivate Cadena A and B."""
    fixture = _load_fixture(FIXTURE_C_ONLY)

    assert fixture["volumetria"]["inbound"]["cadenas_activas"]["cadena_a"] is False, (
        "C_ONLY must deactivate cadena_a"
    )
    assert fixture["volumetria"]["inbound"]["cadenas_activas"]["cadena_b"] is False, (
        "C_ONLY must deactivate cadena_b"
    )
    assert fixture["volumetria"]["inbound"]["cadenas_activas"]["cadena_c"] is True, (
        "C_ONLY must activate cadena_c"
    )
    assert fixture["volumetria"]["outbound"]["cadenas_activas"]["cadena_a"] is False
    assert fixture["volumetria"]["outbound"]["cadenas_activas"]["cadena_b"] is False
    assert fixture["volumetria"]["outbound"]["cadenas_activas"]["cadena_c"] is True


def test_b_plus_c_keeps_a_active():
    """B_PLUS_C scenario must keep Cadena A active."""
    fixture = _load_fixture(FIXTURE_B_PLUS_C)

    assert fixture["volumetria"]["inbound"]["cadenas_activas"]["cadena_a"] is True
    assert fixture["volumetria"]["inbound"]["cadenas_activas"]["cadena_b"] is True
    assert fixture["volumetria"]["inbound"]["cadenas_activas"]["cadena_c"] is True


def test_a_plus_b_plus_c_keeps_a_active():
    """A_PLUS_B_PLUS_C scenario must keep Cadena A active."""
    fixture = _load_fixture(FIXTURE_A_PLUS_B_PLUS_C)

    assert fixture["volumetria"]["inbound"]["cadenas_activas"]["cadena_a"] is True
    assert fixture["volumetria"]["inbound"]["cadenas_activas"]["cadena_b"] is True
    assert fixture["volumetria"]["inbound"]["cadenas_activas"]["cadena_c"] is True


# ============================================================================
# Condiciones_Cadena_C Structural Difference Tests
# ============================================================================


def test_condiciones_cadena_c_differ_across_scenarios():
    """Each scenario must have distinct condiciones_cadena_c (tariffs, opex, capex)."""
    c_only = _load_fixture(FIXTURE_C_ONLY)
    b_plus_c = _load_fixture(FIXTURE_B_PLUS_C)
    a_plus_b_plus_c = _load_fixture(FIXTURE_A_PLUS_B_PLUS_C)

    # Extract tariffs for comparison
    c_only_tariff_1 = c_only["condiciones_cadena_c"]["canales"][0]["tarifa_unitaria"]
    b_plus_c_tariff_1 = b_plus_c["condiciones_cadena_c"]["canales"][0]["tarifa_unitaria"]
    a_plus_b_plus_c_tariff_1 = a_plus_b_plus_c["condiciones_cadena_c"]["canales"][0]["tarifa_unitaria"]

    # Tariffs must differ
    assert c_only_tariff_1 != b_plus_c_tariff_1, (
        f"C_ONLY and B_PLUS_C must have different tariffs: {c_only_tariff_1} vs {b_plus_c_tariff_1}"
    )
    assert b_plus_c_tariff_1 != a_plus_b_plus_c_tariff_1, (
        f"B_PLUS_C and A_PLUS_B_PLUS_C must have different tariffs: {b_plus_c_tariff_1} vs {a_plus_b_plus_c_tariff_1}"
    )
    assert c_only_tariff_1 != a_plus_b_plus_c_tariff_1, (
        f"C_ONLY and A_PLUS_B_PLUS_C must have different tariffs: {c_only_tariff_1} vs {a_plus_b_plus_c_tariff_1}"
    )


def test_opex_fijo_differs_across_scenarios():
    """Opex fijo must differ across scenarios."""
    c_only = _load_fixture(FIXTURE_C_ONLY)
    b_plus_c = _load_fixture(FIXTURE_B_PLUS_C)
    a_plus_b_plus_c = _load_fixture(FIXTURE_A_PLUS_B_PLUS_C)

    c_only_opex = c_only["condiciones_cadena_c"]["canales"][0]["opex_fijo_integ"]
    b_plus_c_opex = b_plus_c["condiciones_cadena_c"]["canales"][0]["opex_fijo_integ"]
    a_plus_b_plus_c_opex = a_plus_b_plus_c["condiciones_cadena_c"]["canales"][0]["opex_fijo_integ"]

    assert c_only_opex != b_plus_c_opex
    assert b_plus_c_opex != a_plus_b_plus_c_opex
    assert c_only_opex != a_plus_b_plus_c_opex


def test_inversion_anual_differs_across_scenarios():
    """Annual investment must differ across scenarios."""
    c_only = _load_fixture(FIXTURE_C_ONLY)
    b_plus_c = _load_fixture(FIXTURE_B_PLUS_C)
    a_plus_b_plus_c = _load_fixture(FIXTURE_A_PLUS_B_PLUS_C)

    c_only_inv = c_only["condiciones_cadena_c"]["inversion_anual"]
    b_plus_c_inv = b_plus_c["condiciones_cadena_c"]["inversion_anual"]
    a_plus_b_plus_c_inv = a_plus_b_plus_c["condiciones_cadena_c"]["inversion_anual"]

    assert c_only_inv != b_plus_c_inv
    assert b_plus_c_inv != a_plus_b_plus_c_inv
    assert c_only_inv != a_plus_b_plus_c_inv


# ============================================================================
# Equipo_Transversal Validation Tests
# ============================================================================


def test_c_only_has_no_equipo_transversal():
    """C_ONLY must have empty equipo_transversal (low cost scenario)."""
    fixture = _load_fixture(FIXTURE_C_ONLY)
    assert len(fixture["condiciones_cadena_c"]["equipo_transversal"]) == 0


def test_b_plus_c_has_multiple_roles():
    """B_PLUS_C must have multiple roles in equipo_transversal (high cost scenario)."""
    fixture = _load_fixture(FIXTURE_B_PLUS_C)
    assert len(fixture["condiciones_cadena_c"]["equipo_transversal"]) >= 2


def test_a_plus_b_plus_c_has_single_role():
    """A_PLUS_B_PLUS_C must have single role (medium cost scenario)."""
    fixture = _load_fixture(FIXTURE_A_PLUS_B_PLUS_C)
    assert len(fixture["condiciones_cadena_c"]["equipo_transversal"]) == 1


# ============================================================================
# Fixture Completeness Tests
# ============================================================================


def test_all_fixtures_have_required_keys():
    """All fixtures must have required top-level keys."""
    fixtures = [
        _load_fixture(FIXTURE_C_ONLY),
        _load_fixture(FIXTURE_B_PLUS_C),
        _load_fixture(FIXTURE_A_PLUS_B_PLUS_C),
    ]
    required_keys = {"datos_operativos", "volumetria", "condiciones_cadena_a", "condiciones_cadena_b", "condiciones_cadena_c"}

    for fixture in fixtures:
        assert required_keys.issubset(fixture.keys()), (
            f"Fixture missing required keys: {required_keys - fixture.keys()}"
        )


def test_condiciones_cadena_c_have_canales():
    """All condiciones_cadena_c must have canales array with at least one active canal."""
    fixtures = [
        _load_fixture(FIXTURE_C_ONLY),
        _load_fixture(FIXTURE_B_PLUS_C),
        _load_fixture(FIXTURE_A_PLUS_B_PLUS_C),
    ]

    for fixture in fixtures:
        canales = fixture["condiciones_cadena_c"].get("canales", [])
        assert len(canales) > 0, "Must have at least one canal"
        assert any(c.get("activo", False) for c in canales), "Must have at least one active canal"


# ============================================================================
# Cost Profile Classification Tests
# ============================================================================


def test_c_only_is_low_cost_scenario():
    """C_ONLY must be the lowest cost scenario (low tariffs, low opex, no team)."""
    c_only = _load_fixture(FIXTURE_C_ONLY)
    b_plus_c = _load_fixture(FIXTURE_B_PLUS_C)

    c_only_total_cost = (
        c_only["condiciones_cadena_c"]["inversion_anual"] +
        sum(c["opex_fijo_integ"] for c in c_only["condiciones_cadena_c"]["canales"])
    )
    b_plus_c_total_cost = (
        b_plus_c["condiciones_cadena_c"]["inversion_anual"] +
        sum(c["opex_fijo_integ"] for c in b_plus_c["condiciones_cadena_c"]["canales"])
    )

    assert c_only_total_cost < b_plus_c_total_cost, (
        f"C_ONLY cost ({c_only_total_cost}) must be < B_PLUS_C ({b_plus_c_total_cost})"
    )


def test_b_plus_c_is_high_cost_scenario():
    """B_PLUS_C must be the highest cost scenario."""
    b_plus_c = _load_fixture(FIXTURE_B_PLUS_C)
    a_plus_b_plus_c = _load_fixture(FIXTURE_A_PLUS_B_PLUS_C)

    b_plus_c_total_cost = (
        b_plus_c["condiciones_cadena_c"]["inversion_anual"] +
        sum(c["opex_fijo_integ"] for c in b_plus_c["condiciones_cadena_c"]["canales"])
    )
    a_plus_b_plus_c_total_cost = (
        a_plus_b_plus_c["condiciones_cadena_c"]["inversion_anual"] +
        sum(c["opex_fijo_integ"] for c in a_plus_b_plus_c["condiciones_cadena_c"]["canales"])
    )

    assert b_plus_c_total_cost > a_plus_b_plus_c_total_cost, (
        f"B_PLUS_C cost ({b_plus_c_total_cost}) must be > A_PLUS_B_PLUS_C ({a_plus_b_plus_c_total_cost})"
    )


__all__ = [
    "test_c_only_deactivates_a_and_b",
    "test_b_plus_c_keeps_a_active",
    "test_a_plus_b_plus_c_keeps_a_active",
    "test_condiciones_cadena_c_differ_across_scenarios",
    "test_opex_fijo_differs_across_scenarios",
    "test_inversion_anual_differs_across_scenarios",
    "test_c_only_has_no_equipo_transversal",
    "test_b_plus_c_has_multiple_roles",
    "test_a_plus_b_plus_c_has_single_role",
    "test_all_fixtures_have_required_keys",
    "test_condiciones_cadena_c_have_canales",
    "test_c_only_is_low_cost_scenario",
    "test_b_plus_c_is_high_cost_scenario",
]
