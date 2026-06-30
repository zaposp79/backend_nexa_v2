"""
tests/refactor/test_formula_trace_runtime_query.py
==================================================
TRACE_DEBUG_CONSUMPTION_PHASE1 — Internal utility test to verify that
FORMULA_ID wiring is queryable at runtime via internal audit traces.

PURPOSE:
  Demonstrate that FORMULA_ID constants connected in FORMULA_TRACE_RUNTIME_WIRING
  PHASE1-7 are accessible and queryable from audit_trace at runtime, without
  impacting public JSON contracts or changing any calculations.

WHAT IS TESTED:
  1. Baseline simulation executes with audit_context enabled
  2. TraceEntry.formula_ids field is populated for wired calculators
  3. Each FORMULA_ID category (NO_PAYROLL, CADENA_B, CADENA_C, COSTOS_FINANCIEROS,
     PYG, KPIS) appears in at least one trace entry
  4. formula_ids field is NOT present in exported JSON (internal only)
  5. Public contracts (ApiResponse, PricingResult) are unchanged

DESIGN:
  - Helper function: `collect_formula_ids_by_calculator()` to query traces
  - No new endpoints, no new fields in payloads, no changes to contracts
  - Query helper lives in test suite only (not in production code)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import defaultdict

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_FIXTURES = Path(__file__).resolve().parent.parent / "golden" / "fixtures"
PARITY_FIXTURES = BACKEND_ROOT / "tests" / "parity" / "fixtures"

if str(BACKEND_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT.parent))

import backend_nexa  # noqa: F401

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.audit.integration import (
    audit_context,
    export_audit_trace,
)


# ─────────────────────────────────────────────────────────────────────────────
# Query Helper — Internal only (for testing/debugging)
# ─────────────────────────────────────────────────────────────────────────────


def collect_formula_ids_by_calculator(tracer) -> dict[str, list[str]]:
    """
    Query internal audit_trace entries to collect FORMULA_ID values grouped by calculator.

    This helper is INTERNAL ONLY — used for debugging and validation.
    It accesses TraceEntry.formula_ids (which is excluded from JSON serialization).

    Returns:
        dict mapping calculator name to list of FORMULA_IDs found in traces.
        Example: {
            "NO_PAYROLL": ["OPEX_TI", "BENEFICIO_NETO", ...],
            "CADENA_B": ["COMPONENTE_FIJO_B", "FACTURACION_B", ...],
            ...
        }
    """
    by_calc: dict[str, set[str]] = defaultdict(set)

    for entry in tracer.entries:
        if entry.formula_ids:
            for fid in entry.formula_ids:
                # Extract prefix (e.g., "NO_PAYROLL" from "NO_PAYROLL.OPEX_TI")
                if "." in fid:
                    prefix = fid.split(".")[0]
                else:
                    prefix = fid
                by_calc[prefix].add(fid)

    # Convert sets to sorted lists
    return {k: sorted(list(v)) for k, v in sorted(by_calc.items())}


def formula_id_summary(formula_ids_dict: dict[str, list[str]]) -> str:
    """Format FORMULA_ID collection for readable output."""
    lines = []
    for calc_name, ids in formula_ids_dict.items():
        lines.append(f"  {calc_name}: {len(ids)} IDs")
        for fid in ids[:3]:  # Show first 3
            lines.append(f"    - {fid}")
        if len(ids) > 3:
            lines.append(f"    ... and {len(ids) - 3} more")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def baseline_request_path():
    """Path to a baseline request for testing."""
    req_path = PARITY_FIXTURES / "excel_v2_7_real_request.json"
    assert req_path.exists(), f"Baseline request not found: {req_path}"
    return req_path


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFormulaTraceRuntimeQuery:
    """
    Verify that FORMULA_ID wiring from FORMULA_TRACE_RUNTIME_WIRING PHASE1-7
    is queryable and accessible at runtime via internal audit traces.
    """

    def test_baseline_simulation_with_audit_context_enabled(self, baseline_request_path):
        """Execute a baseline simulation with audit tracing enabled."""
        ui = UserInputLoader().cargar(baseline_request_path)
        ctx = SimulationContextBuilder().construir(ui)

        with audit_context(enabled=True, simulation_id="test_baseline") as tracer:
            resultado = NexaPricingEngine().calcular(ctx)

        # Verify simulation succeeded
        assert resultado is not None
        assert resultado.kpis is not None
        assert len(tracer.entries) > 0, "No trace entries captured"

    def test_formula_ids_queryable_by_calculator(self, baseline_request_path):
        """
        Verify that FORMULA_ID values from PHASE1-7 wiring are queryable
        from the internal audit traces.
        """
        ui = UserInputLoader().cargar(baseline_request_path)
        ctx = SimulationContextBuilder().construir(ui)

        with audit_context(enabled=True, simulation_id="test_query") as tracer:
            resultado = NexaPricingEngine().calcular(ctx)

        # Query FORMULA_IDs by calculator
        formula_ids_dict = collect_formula_ids_by_calculator(tracer)

        # Verify each wired calculator is present
        assert "NO_PAYROLL" in formula_ids_dict, (
            f"NO_PAYROLL not found in traces. Available: {list(formula_ids_dict.keys())}"
        )
        assert "CADENA_B" in formula_ids_dict, (
            f"CADENA_B not found in traces. Available: {list(formula_ids_dict.keys())}"
        )
        assert "CADENA_C" in formula_ids_dict, (
            f"CADENA_C not found in traces. Available: {list(formula_ids_dict.keys())}"
        )
        assert "COSTOS_FINANCIEROS" in formula_ids_dict, (
            f"COSTOS_FINANCIEROS not found in traces. Available: {list(formula_ids_dict.keys())}"
        )
        assert "PYG" in formula_ids_dict, (
            f"PYG not found in traces. Available: {list(formula_ids_dict.keys())}"
        )
        assert "KPIS" in formula_ids_dict, (
            f"KPIS not found in traces. Available: {list(formula_ids_dict.keys())}"
        )

    def test_each_calculator_has_expected_formula_ids(self, baseline_request_path):
        """
        Verify that each wired calculator has FORMULA_ID entries.
        """
        ui = UserInputLoader().cargar(baseline_request_path)
        ctx = SimulationContextBuilder().construir(ui)

        with audit_context(enabled=True, simulation_id="test_ids_count") as tracer:
            resultado = NexaPricingEngine().calcular(ctx)

        formula_ids_dict = collect_formula_ids_by_calculator(tracer)

        # Verify non-empty FORMULA_ID lists per calculator
        # (These should match PHASE1-7 wiring counts)
        assert len(formula_ids_dict.get("NO_PAYROLL", [])) >= 3, "NO_PAYROLL missing IDs"
        assert len(formula_ids_dict.get("CADENA_B", [])) >= 7, "CADENA_B missing IDs"
        assert len(formula_ids_dict.get("CADENA_C", [])) >= 8, "CADENA_C missing IDs"
        assert len(formula_ids_dict.get("COSTOS_FINANCIEROS", [])) >= 8, (
            "COSTOS_FINANCIEROS missing IDs"
        )
        assert len(formula_ids_dict.get("PYG", [])) >= 9, "PYG missing IDs"
        assert len(formula_ids_dict.get("KPIS", [])) >= 15, "KPIS missing IDs"

    def test_formula_ids_not_in_exported_json(self, baseline_request_path):
        """
        Verify that formula_ids field is NOT present in exported JSON.
        This ensures backward compatibility and contract integrity.
        """
        ui = UserInputLoader().cargar(baseline_request_path)
        ctx = SimulationContextBuilder().construir(ui)

        with audit_context(enabled=True, simulation_id="test_json_export") as tracer:
            resultado = NexaPricingEngine().calcular(ctx)

        # Export trace to dict (as would be serialized to JSON)
        exported = export_audit_trace(tracer)

        # Verify formula_ids is NOT in exported entries
        assert "entries" in exported
        for entry in exported["entries"]:
            assert "formula_ids" not in entry, (
                "formula_ids should be excluded from JSON serialization"
            )

    def test_pricing_result_contract_unchanged(self, baseline_request_path):
        """
        Verify that PricingResult public fields are unchanged
        (no new formula_ids field added to public contracts).
        """
        ui = UserInputLoader().cargar(baseline_request_path)
        ctx = SimulationContextBuilder().construir(ui)

        with audit_context(enabled=True, simulation_id="test_result_contract") as tracer:
            resultado = NexaPricingEngine().calcular(ctx)

        # Verify result structure is intact
        assert hasattr(resultado, "kpis")
        assert hasattr(resultado, "pyg_por_mes")
        assert hasattr(resultado, "vision_imprimible")
        assert hasattr(resultado, "vision_tarifas")
        assert hasattr(resultado, "cost_to_serve")
        assert hasattr(resultado, "vision_pyg")

        # Verify result can be serialized without errors
        # (This would fail if any internal fields leaked into the contract)
        resultado_dict = resultado.__dict__
        assert "formula_ids" not in resultado_dict


class TestFormulaTraceDebugQueries:
    """
    Additional debug queries to demonstrate formula_id queryability.
    """

    def test_print_formula_id_summary(self, baseline_request_path, capsys):
        """
        Execute simulation and print FORMULA_ID summary to stdout.
        This is a debug helper — not a critical test.
        """
        ui = UserInputLoader().cargar(baseline_request_path)
        ctx = SimulationContextBuilder().construir(ui)

        with audit_context(enabled=True, simulation_id="test_debug_print") as tracer:
            resultado = NexaPricingEngine().calcular(ctx)

        formula_ids_dict = collect_formula_ids_by_calculator(tracer)

        summary = formula_id_summary(formula_ids_dict)
        print("\n" + "=" * 70)
        print("FORMULA_ID Runtime Query Results")
        print("=" * 70)
        print(f"Total trace entries: {len(tracer.entries)}")
        print(f"Calculators with FORMULA_ID wiring:\n{summary}")
        print("=" * 70)

        # Verify output was generated
        assert "NO_PAYROLL" in summary or "CADENA_B" in summary


class TestFormulaTraceQueryEdgeCases:
    """
    Edge case tests for formula_id query helper.
    """

    def test_query_helper_handles_empty_traces(self):
        """Query helper should handle empty trace gracefully."""
        from nexa_engine.modules.audit.trace import AuditTracer

        empty_tracer = AuditTracer(enabled=True)
        empty_tracer.start()

        result = collect_formula_ids_by_calculator(empty_tracer)
        assert result == {}, "Empty tracer should return empty dict"

    def test_query_helper_handles_mixed_entries(self):
        """Query helper should handle entries with and without formula_ids."""
        from nexa_engine.modules.audit.trace import AuditTracer

        tracer = AuditTracer(enabled=True)
        tracer.start()

        # Add entry with formula_ids
        tracer.entry(
            component="test",
            rule="test_rule",
            formula="test_formula",
            inputs={},
            result=0.0,
            formula_ids=["TEST.ID1", "TEST.ID2"],
        )

        # Add entry without formula_ids
        tracer.entry(
            component="test",
            rule="test_rule_2",
            formula="test_formula_2",
            inputs={},
            result=0.0,
        )

        result = collect_formula_ids_by_calculator(tracer)
        assert "TEST" in result
        assert len(result["TEST"]) == 2
        assert "ID1" in result["TEST"][0]
