"""Guardrail tests for Cost-to-Serve contract after calculator_motor migration.

Purpose:
  Freeze current CTS behavior. These tests must pass as-is NOW.
  CTS formulas OWNED by calculator_motor (Block 20C complete).
  vision_cost_to_serve keeps only: api/ (read endpoint), dto/ (DTOs), helpers/.

Guardrail groups:
  1. CostToServeCalculator.calcular() returns ResultadoCostToServe with stable shape
  2. PricingResult stores CTS result
  3. pricing_result_to_dict preserves CTS payload
  4. SimulationSnapshot round-trip preserves CTS payload
  5. vision_cost_to_serve API/router reads stored CTS result (not a new formula path)
  6. DTO/API public fields remain unchanged
  7. Formula ownership is documented (informational, never fails)
  8. calculator_motor CTS builder returns ResultadoCostToServe
  9. engine populates PricingResult through calculator_motor builder
  10. vision_cost_to_serve compatibility wrappers still work (re-export)
"""
from __future__ import annotations

import dataclasses
import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from nexa_engine.modules.calculator_motor.models.results import (
    PricingResult,
    PyGMensual,
)
from nexa_engine.modules.calculator_motor.models.snapshot import SimulationSnapshot
from nexa_engine.modules.calculator_motor.serializers.pricing_result_serializer import (
    _cost_to_serve_to_dict,
    build_simulation_snapshot,
)
from nexa_engine.modules.shared.models import (
    CanalCTSDetalle,
    DesgloseCTSCadenaA,
    DesgloseCTSCadenaB,
    ResultadoCostToServe,
    ResultadoVisionTarifas,
    TarifaCanal,
)
from nexa_engine.modules.vision_cost_to_serve.api.router import get_cost_to_serve
from nexa_engine.modules.calculator_motor.formulas.cts.calculator import (
    CostToServeCalculator,
)


# ─── Group 1: CostToServeCalculator.calcular() result shape ───────────────


class TestCostToServeCalculatorResultShape:
    """Guardrail: CostToServeCalculator.calcular() always returns ResultadoCostToServe."""

    def test_calcular_returns_resultado_cost_to_serve_type(self):
        """Empty inputs produce a valid ResultadoCostToServe with zeros."""
        calc = CostToServeCalculator(
            perfiles_cadena_a=[],
            parametros_cadena_b=SimpleNamespace(canales=[]),
        )
        result = calc.calcular([])
        assert isinstance(result, ResultadoCostToServe)

    def test_calcular_zero_pyg_returns_zero_cts(self):
        """With empty pyg_por_mes, all CTS values are 0.0."""
        calc = CostToServeCalculator(
            perfiles_cadena_a=[],
            parametros_cadena_b=SimpleNamespace(canales=[]),
        )
        result = calc.calcular([])
        assert result.cts_cadena_a == 0.0
        assert result.cts_cadena_b == 0.0
        assert result.cts_cadena_c == 0.0
        assert result.cts_ponderado == 0.0
        assert result.participacion_a == 0.0
        assert result.participacion_b == 0.0
        assert result.participacion_c == 0.0
        assert result.fte_cadena_a == 0.0
        assert result.vol_cadena_b == 0.0
        assert result.vol_cadena_c == 0.0
        assert result.costo_total_acumulado == 0.0
        assert result.canal_view_habilitado is False
        assert result.canales_detalle == []
        assert isinstance(result.desglose_a, DesgloseCTSCadenaA)
        assert isinstance(result.desglose_b, DesgloseCTSCadenaB)

    def test_calcular_with_pyg_produces_non_zero_cts_b(self):
        """With pyg data and no Cadena A, cts_cadena_b should be computable."""
        calc = CostToServeCalculator(
            perfiles_cadena_a=[],
            parametros_cadena_b=SimpleNamespace(canales=[
                SimpleNamespace(volumen_mensual=1000, vol_escalamiento=0),
            ]),
        )
        months = [
            PyGMensual(mes=1, costo_b=500_000),
            PyGMensual(mes=2, costo_b=600_000),
        ]
        result = calc.calcular(months)
        assert result.cts_cadena_a == 0.0
        assert result.cts_cadena_b > 0
        # cts_b = avg(costo_b) / vol_b = 550_000 / 1000 = 550
        assert result.cts_cadena_b == pytest.approx(550.0, rel=1e-9)
        assert result.vol_cadena_b == 1000

    def test_desglose_a_is_desglose_cts_cadena_a_instance(self):
        """desglose_a attribute is typed as DesgloseCTSCadenaA."""
        calc = CostToServeCalculator(
            perfiles_cadena_a=[],
            parametros_cadena_b=SimpleNamespace(canales=[]),
        )
        result = calc.calcular([])
        assert isinstance(result.desglose_a, DesgloseCTSCadenaA)

    def test_desglose_b_is_desglose_cts_cadena_b_instance(self):
        """desglose_b attribute is typed as DesgloseCTSCadenaB."""
        calc = CostToServeCalculator(
            perfiles_cadena_a=[],
            parametros_cadena_b=SimpleNamespace(canales=[]),
        )
        result = calc.calcular([])
        assert isinstance(result.desglose_b, DesgloseCTSCadenaB)


# ─── Group 2: PricingResult stores CTS result ────────────────────────────


class TestPricingResultStoresCTS:
    """Guardrail: PricingResult.cost_to_serve stores the CTS result."""

    def test_pricing_result_has_cost_to_serve_field(self):
        """cost_to_serve is an optional field on PricingResult."""
        result = PricingResult(kpis=SimpleNamespace(), pyg_por_mes=[], panel=SimpleNamespace())
        assert hasattr(result, "cost_to_serve")
        assert result.cost_to_serve is None

    def test_cost_to_serve_is_optional_and_can_be_set(self):
        """cost_to_serve accepts ResultadoCostToServe."""
        cts = ResultadoCostToServe(cts_cadena_a=123.45)
        result = PricingResult(
            kpis=SimpleNamespace(),
            pyg_por_mes=[],
            panel=SimpleNamespace(),
            cost_to_serve=cts,
        )
        assert result.cost_to_serve is not None
        assert result.cost_to_serve.cts_cadena_a == 123.45

    def test_cost_to_serve_accepts_none(self):
        """cost_to_serve=None is valid when Cadena A is inactive."""
        result = PricingResult(
            kpis=SimpleNamespace(),
            pyg_por_mes=[],
            panel=SimpleNamespace(),
            cost_to_serve=None,
        )
        assert result.cost_to_serve is None


# ─── Group 3: pricing_result_to_dict preserves CTS ───────────────────────


class TestPricingResultToDictPreservesCTS:
    """Guardrail: pricing_result_to_dict serializes cost_to_serve faithfully.

    NOTE: These tests use _cost_to_serve_to_dict directly to focus on CTS
    serialization rather than testing the full PricingResult -> vision_imprimible
    pipeline. The full pipeline requires a fully-constructed PanelDeControl with
    all required fields, which belongs in integration/API tests.
    """

    def test_cost_to_serve_dict_has_all_top_level_fields(self):
        """Serialized CTS dict contains expected top-level fields."""
        cts = ResultadoCostToServe(
            cts_cadena_a=100.0,
            cts_cadena_b=200.0,
            cts_cadena_c=300.0,
            cts_ponderado=150.0,
            participacion_a=0.5,
            participacion_b=0.3,
            participacion_c=0.2,
            fte_cadena_a=1000.0,
            vol_cadena_b=2000.0,
            vol_cadena_c=3000.0,
            costo_total_acumulado=1_000_000.0,
            canal_view_habilitado=True,
            canales_detalle=[
                CanalCTSDetalle(canal="Voz", fte=50, cts=120.0),
            ],
        )
        cts_dict = _cost_to_serve_to_dict(cts)
        expected_keys = {
            "cts_cadena_a", "cts_cadena_b", "cts_cadena_c", "cts_ponderado",
            "participacion_a", "participacion_b", "participacion_c",
            "fte_cadena_a", "vol_cadena_b", "vol_cadena_c",
            "costo_total_acumulado", "canal_view_habilitado",
            "desglose_a", "desglose_b", "canales_detalle",
        }
        assert expected_keys.issubset(cts_dict.keys()), (
            f"Missing keys: {expected_keys - set(cts_dict.keys())}"
        )

    def test_cost_to_serve_serialized_values_match(self):
        """Serialized CTS numeric values match originals."""
        cts = ResultadoCostToServe(cts_cadena_a=123.456, cts_cadena_b=789.012)
        cts_dict = _cost_to_serve_to_dict(cts)
        assert cts_dict["cts_cadena_a"] == 123.456
        assert cts_dict["cts_cadena_b"] == 789.012

    def test_cost_to_serve_desglose_a_serialized_with_total(self):
        """desglose_a dict includes 'total' property."""
        da = DesgloseCTSCadenaA(nomina=100.0, no_payroll=50.0)
        cts = ResultadoCostToServe(desglose_a=da)
        cts_dict = _cost_to_serve_to_dict(cts)
        da_dict = cts_dict["desglose_a"]
        assert da_dict["total"] == 150.0
        assert da_dict["nomina"] == 100.0
        assert da_dict["no_payroll"] == 50.0

    def test_cost_to_serve_desglose_b_serialized_with_total(self):
        """desglose_b dict includes 'total' property."""
        db = DesgloseCTSCadenaB(componente_fijo=200.0, componente_variable=80.0)
        cts = ResultadoCostToServe(desglose_b=db)
        cts_dict = _cost_to_serve_to_dict(cts)
        db_dict = cts_dict["desglose_b"]
        assert db_dict["total"] == 280.0

    def test_cost_to_serve_canales_detalle_serialized(self):
        """canales_detalle list serializes each CanalCTSDetalle."""
        canales = [
            CanalCTSDetalle(canal="Voz", fte=10, cts=500.0),
            CanalCTSDetalle(canal="Chat", fte=5, cts=300.0),
        ]
        cts = ResultadoCostToServe(canales_detalle=canales)
        cts_dict = _cost_to_serve_to_dict(cts)
        assert len(cts_dict["canales_detalle"]) == 2
        assert cts_dict["canales_detalle"][0]["canal"] == "Voz"
        assert cts_dict["canales_detalle"][1]["canal"] == "Chat"
        assert cts_dict["canales_detalle"][0]["cts"] == 500.0


# ─── Group 4: SimulationSnapshot round-trip preserves CTS ────────────────


class TestSimulationSnapshotRoundTripPreservesCTS:
    """Guardrail: CTS payload survives SimulationSnapshot serialization."""

    def test_snapshot_round_trip_preserves_cts_data(self):
        """CTS data in pricing_result survives snapshot → dict → from_dict."""
        cts_data = {
            "cts_cadena_a": 150.0,
            "cts_cadena_b": 250.0,
            "cts_cadena_c": 0.0,
            "cts_ponderado": 200.0,
            "participacion_a": 0.6,
            "participacion_b": 0.4,
            "participacion_c": 0.0,
            "fte_cadena_a": 500.0,
            "vol_cadena_b": 1000.0,
            "vol_cadena_c": 0.0,
            "costo_total_acumulado": 5_000_000.0,
            "canal_view_habilitado": True,
            "desglose_a": {"nomina": 100.0, "no_payroll": 50.0, "total": 150.0},
            "desglose_b": {"componente_fijo": 200.0, "componente_variable": 80.0, "total": 280.0},
            "canales_detalle": [],
        }

        snapshot = build_simulation_snapshot(
            simulation_id="test-snap-001",
            raw_input={},
            normalized_input={},
            normalization_log={},
            parametrization_snapshot={
                "smmlv": 1_300_000,
                "auxilio_transporte": 162_000,
                "linea_negocio": "test",
            },
            data_provenance={},
            pricing_result_dict={"cost_to_serve": cts_data},
            panel_summary_data={},
            created_at="2026-06-15T00:00:00Z",
        )
        snapshot_dict = snapshot.as_dict()
        assert snapshot_dict["pricing_result"]["cost_to_serve"] == cts_data

        round_tripped = SimulationSnapshot.from_dict(snapshot_dict)
        assert round_tripped.pricing_result["cost_to_serve"] == cts_data
        assert round_tripped.pricing_result["cost_to_serve"]["cts_cadena_a"] == 150.0

    def test_snapshot_round_trip_with_none_cts(self):
        """None CTS in pricing_result survives snapshot round-trip."""
        snapshot = build_simulation_snapshot(
            simulation_id="test-snap-002",
            raw_input={},
            normalized_input={},
            normalization_log={},
            parametrization_snapshot={
                "smmlv": 1_300_000,
                "auxilio_transporte": 162_000,
                "linea_negocio": "test",
            },
            data_provenance={},
            pricing_result_dict={"cost_to_serve": None},
            panel_summary_data={},
        )
        snapshot_dict = snapshot.as_dict()
        assert snapshot_dict["pricing_result"]["cost_to_serve"] is None

        round_tripped = SimulationSnapshot.from_dict(snapshot_dict)
        assert round_tripped.pricing_result["cost_to_serve"] is None


# ─── Group 5: vision_cost_to_serve API/router reads stored result ────────


class TestVisionCostToServeAPIGuardrails:
    """Guardrail: API endpoint reads stored result, not a new formula path."""

    def test_get_cost_to_serve_is_callable(self):
        """The router handler function is importable and callable."""
        assert callable(get_cost_to_serve)

    def test_router_uses_results_repository(self):
        """The handler depends on ResultsRepository (reads stored result)."""
        import inspect
        sig = inspect.signature(get_cost_to_serve)
        params = list(sig.parameters.keys())
        assert "repo" in params, (
            "get_cost_to_serve must depend on ResultsRepository. "
            "It reads a stored result, not a new formula path."
        )

    def test_router_handler_returns_cts_from_repo(self):
        """The handler extracts cost_to_serve from the repo result."""
        from fastapi import Depends
        import nexa_engine.modules.vision_cost_to_serve.api.router as router_mod

        source = router_mod.__file__
        with open(source, encoding="utf-8") as f:
            content = f.read()
        assert "resultado_simulacion.get(\"cost_to_serve\")" in content, (
            "get_cost_to_serve must read cost_to_serve from the stored "
            "simulation result, not recompute from scratch."
        )


# ─── Group 6: DTO/API public fields ──────────────────────────────────────


# Expected public fields for each CTS DTO — MUST NOT CHANGE without API version bump.
EXPECTED_RESULTADO_COST_TO_SERVE_FIELDS = {
    "cts_cadena_a", "cts_cadena_b", "cts_cadena_c", "cts_ponderado",
    "participacion_a", "participacion_b", "participacion_c",
    "fte_cadena_a", "vol_cadena_b", "vol_cadena_c",
    "costo_total_acumulado",
    "desglose_a", "desglose_b",
    "canal_view_habilitado", "canales_detalle",
}

EXPECTED_DESGLOSE_A_FIELDS = {
    "nomina", "no_payroll",
    "nomina_loaded", "salario_fijo", "salario_variable",
    "capacitacion_inicial", "capacitacion_rotacion", "examenes",
    "estudios_seguridad", "crucero",
    "opex_fijo", "inversiones", "costos_fijos_estacion",
}

EXPECTED_DESGLOSE_B_FIELDS = {
    "componente_fijo", "opex", "inversiones", "soporte_mantenimiento",
    "componente_variable", "tarifa", "opex_variable",
    "tasa_escalamiento", "hitl",
}

EXPECTED_CANAL_CTS_DETALLE_FIELDS = {
    "canal", "modalidad", "fte", "participacion_cadena_a", "cts",
    "payroll", "nomina_loaded", "salario_fijo", "salario_variable",
    "capacitacion_inicial", "capacitacion_rotacion", "examenes",
    "estudios_seguridad", "crucero",
    "no_payroll", "opex_fijo", "inversiones", "costos_fijos",
}


class TestDTOFieldsStable:
    """Guardrail: DTO fields must remain unchanged (public API contract)."""

    def test_resultado_cost_to_serve_fields_match_expected(self):
        actual = {f.name for f in dataclasses.fields(ResultadoCostToServe)}
        assert actual == EXPECTED_RESULTADO_COST_TO_SERVE_FIELDS, (
            f"ResultadoCostToServe fields changed! "
            f"Expected: {EXPECTED_RESULTADO_COST_TO_SERVE_FIELDS}, "
            f"Got: {actual}, "
            f"Added: {actual - EXPECTED_RESULTADO_COST_TO_SERVE_FIELDS}, "
            f"Removed: {EXPECTED_RESULTADO_COST_TO_SERVE_FIELDS - actual}"
        )

    def test_desglose_a_fields_match_expected(self):
        actual = {f.name for f in dataclasses.fields(DesgloseCTSCadenaA)}
        assert actual == EXPECTED_DESGLOSE_A_FIELDS, (
            f"DesgloseCTSCadenaA fields changed! "
            f"Expected: {EXPECTED_DESGLOSE_A_FIELDS}, "
            f"Got: {actual}, "
            f"Added: {actual - EXPECTED_DESGLOSE_A_FIELDS}, "
            f"Removed: {EXPECTED_DESGLOSE_A_FIELDS - actual}"
        )

    def test_desglose_b_fields_match_expected(self):
        actual = {f.name for f in dataclasses.fields(DesgloseCTSCadenaB)}
        assert actual == EXPECTED_DESGLOSE_B_FIELDS, (
            f"DesgloseCTSCadenaB fields changed! "
            f"Expected: {EXPECTED_DESGLOSE_B_FIELDS}, "
            f"Got: {actual}, "
            f"Added: {actual - EXPECTED_DESGLOSE_B_FIELDS}, "
            f"Removed: {EXPECTED_DESGLOSE_B_FIELDS - actual}"
        )

    def test_canal_cts_detalle_fields_match_expected(self):
        actual = {f.name for f in dataclasses.fields(CanalCTSDetalle)}
        assert actual == EXPECTED_CANAL_CTS_DETALLE_FIELDS, (
            f"CanalCTSDetalle fields changed! "
            f"Expected: {EXPECTED_CANAL_CTS_DETALLE_FIELDS}, "
            f"Got: {actual}, "
            f"Added: {actual - EXPECTED_CANAL_CTS_DETALLE_FIELDS}, "
            f"Removed: {EXPECTED_CANAL_CTS_DETALLE_FIELDS - actual}"
        )


# ─── Group 7: Formula ownership documented (informational) ───────────────

# FORMULA_OWNERSHIP_CTS (Block 20C complete)
# Owner: modules/calculator_motor/formulas/cts/
#   - calculator.py: CostToServeCalculator (CTS formulas)
#   - cts_facts.py: CostToServeFacts, CanalCTSFacts (pre-computed facts)
#   - builder.py: build_cost_to_serve_result (composition root)
#   - __init__.py: lazy-import facade
# vision_cost_to_serve keeps only: api/ (read endpoint), dto/ (contracts),
#   helpers/ (servicio_catalogo)
# Legacy compat wrapper cost_to_serve_calculator.py removed (Block 28).
# models/cts_facts.py still provides backward-compat re-export.
# Migration completed: Block 20C (commit pending)

CTS_OWNER = "modules/calculator_motor/formulas/cts/"
VISION_LAYER_REEXPORT = None  # removed in Block 28
MIGRATION_COMPLETED = "Block 20C"


class TestFormulaOwnershipDocumented:
    """Informational: CTS formula ownership is documented, never fails.

    Block 20C complete: calculator_motor owns CTS formulas/orchestration.
    vision_cost_to_serve re-export wrappers provide backward compat.
    """

    def test_owner_in_calculator_motor(self):
        assert CTS_OWNER is not None
        assert "calculator_motor" in CTS_OWNER

    def test_vision_layer_reexport_removed(self):
        assert VISION_LAYER_REEXPORT is None

    def test_migration_completed(self):
        assert MIGRATION_COMPLETED == "Block 20C"


# ─── Group 8: calculator_motor CTS builder returns ResultadoCostToServe ─────


class TestCalculatorMotorCTSBuilder:
    """Guardrail: build_cost_to_serve_result returns ResultadoCostToServe."""

    def test_builder_imports_and_is_callable(self):
        from nexa_engine.modules.calculator_motor.formulas.cts import (
            build_cost_to_serve_result,
        )

        assert callable(build_cost_to_serve_result)

    def test_builder_returns_resultado_cost_to_serve_with_empty_inputs(self):
        from nexa_engine.modules.calculator_motor.formulas.cts import (
            build_cost_to_serve_result,
        )

        result = build_cost_to_serve_result(
            perfiles_cadena_a=[],
            parametros_cadena_b=SimpleNamespace(canales=[]),
            pyg_por_mes=[],
        )
        assert isinstance(result, ResultadoCostToServe)

    def test_builder_delegates_to_cost_to_serve_calculator(self):
        """The builder instantiates CostToServeCalculator from calculator_motor."""
        from nexa_engine.modules.calculator_motor.formulas.cts.builder import (
            build_cost_to_serve_result as builder_fn,
        )
        import inspect

        source = inspect.getsource(builder_fn)
        assert "CostToServeCalculator" in source, (
            "Builder must instantiate CostToServeCalculator from calculator_motor"
        )
        assert "vision_cost_to_serve.services" not in source, (
            "Builder must not import from vision_cost_to_serve. "
            "Use calculator_motor.formulas.cts.calculator directly (Block 20C)."
        )

    def test_builder_produces_identical_cts_to_direct_call(self):
        """Direct CostToServeCalculator vs builder produce identical result."""
        from nexa_engine.modules.calculator_motor.formulas.cts import (
            build_cost_to_serve_result,
        )
        from nexa_engine.modules.calculator_motor.formulas.cts.calculator import (
            CostToServeCalculator,
        )

        params = {
            "perfiles_cadena_a": [],
            "parametros_cadena_b": SimpleNamespace(canales=[
                SimpleNamespace(volumen_mensual=1000, vol_escalamiento=0),
            ]),
        }
        pyg = [PyGMensual(mes=1, costo_b=500_000)]

        direct = CostToServeCalculator(
            params["perfiles_cadena_a"],
            params["parametros_cadena_b"],
        ).calcular(pyg)

        via_builder = build_cost_to_serve_result(
            **params,
            pyg_por_mes=pyg,
        )

        assert direct.cts_cadena_b == via_builder.cts_cadena_b
        assert direct.cts_cadena_a == via_builder.cts_cadena_a
        assert direct.cts_ponderado == via_builder.cts_ponderado
        assert direct.costo_total_acumulado == via_builder.costo_total_acumulado


# ─── Group 9: engine populates PricingResult through calculator_motor builder ──


class TestEnginePopulatesCTSThroughBuilder:
    """Guardrail: engine.populate calls calculator_motor's CTS builder."""

    def test_engine_imports_build_cost_to_serve_result(self):
        """engine.py must import the CTS builder from calculator_motor."""
        from nexa_engine.modules.calculator_motor import engine as engine_mod
        import inspect

        source = inspect.getsource(engine_mod)
        assert "build_cost_to_serve_result" in source, (
            "engine.py must import and use build_cost_to_serve_result "
            "from calculator_motor.formulas.cts"
        )
        assert "from nexa_engine.modules.calculator_motor.formulas.cts import" in source, (
            "Import must come from calculator_motor, not vision_cost_to_serve"
        )

    def test_engine_no_longer_imports_cts_from_vision_cost_to_serve(self):
        """engine.py must not import CTS classes from vision_cost_to_serve."""
        from nexa_engine.modules.calculator_motor import engine as engine_mod
        import inspect

        source = inspect.getsource(engine_mod)
        assert "vision_cost_to_serve.services.cost_to_serve_calculator" not in source, (
            "engine.py must not import CostToServeCalculator directly. "
            "Use build_cost_to_serve_result from calculator_motor."
        )
        assert "vision_cost_to_serve.models.cts_facts" not in source, (
            "engine.py must not import CTS facts from vision_cost_to_serve. "
            "Use calculator_motor.formulas.cts.cts_facts (Block 20C)."
        )


# ─── Group 10: vision_cost_to_serve compatibility wrappers (re-export) ────


class TestVisionCostToServeReexportWrappers:
    """Guardrail: vision_cost_to_serve compatibility wrappers.

    After Block 20C, vision_cost_to_serve/services/cost_to_serve_calculator.py
    was a re-export wrapper. Block 28 removed it — callers should import from
    calculator_motor directly. models/cts_facts.py still provides compat.
    """

    def test_cost_to_serve_calculator_reexport_removed(self):
        """cost_to_serve_calculator.py compat wrapper was removed (Block 28)."""
        from pathlib import Path

        calculator_file = (
            Path(__file__).parents[2]
            / "modules"
            / "vision_cost_to_serve"
            / "services"
            / "cost_to_serve_calculator.py"
        )
        assert not calculator_file.exists(), (
            "Block 28: cost_to_serve_calculator.py re-export wrapper was deleted. "
            "Import CostToServeCalculator from calculator_motor directly."
        )

    def test_cts_facts_reexport_works(self):
        """Import through vision_cost_to_serve must resolve to calculator_motor class."""
        from nexa_engine.modules.vision_cost_to_serve.models import (
            CostToServeFacts as LegacyFacts,
        )
        from nexa_engine.modules.calculator_motor.formulas.cts.cts_facts import (
            CostToServeFacts as CanonicalFacts,
        )

        assert LegacyFacts is CanonicalFacts, (
            "vision_cost_to_serve re-export must resolve to the same "
            "calculator_motor CostToServeFacts class"
        )

    def test_canal_cts_facts_reexport_works(self):
        from nexa_engine.modules.vision_cost_to_serve.models import (
            CanalCTSFacts as LegacyCanal,
        )
        from nexa_engine.modules.calculator_motor.formulas.cts.cts_facts import (
            CanalCTSFacts as CanonicalCanal,
        )

        assert LegacyCanal is CanonicalCanal, (
            "vision_cost_to_serve re-export must resolve to the same "
            "calculator_motor CanalCTSFacts class"
        )

    def test_vision_package_no_formula_implementation(self):
        """vision_cost_to_serve should not contain CTS formula implementation."""
        from pathlib import Path

        services_init = (
            Path(__file__).parents[2]
            / "modules"
            / "vision_cost_to_serve"
            / "services"
            / "__init__.py"
        ).read_text(encoding="utf-8")

        assert "class " not in services_init, (
            "vision_cost_to_serve/services must not define any classes. "
            "CostToServeCalculator was removed in Block 28."
        )

    def test_canonical_cost_to_serve_calculator_in_calculator_motor(self):
        """Canonical CostToServeCalculator lives in calculator_motor."""
        from nexa_engine.modules.calculator_motor.formulas.cts.calculator import (
            CostToServeCalculator,
        )
        assert "calculator_motor" in CostToServeCalculator.__module__, (
            f"Expected calculator_motor, got {CostToServeCalculator.__module__}"
        )
        assert "vision_cost_to_serve" not in CostToServeCalculator.__module__, (
            "Canonical CostToServeCalculator must not be in vision_cost_to_serve"
        )

    def test_canonical_cost_to_serve_facts_in_calculator_motor(self):
        """Canonical CostToServeFacts lives in calculator_motor."""
        from nexa_engine.modules.calculator_motor.formulas.cts.cts_facts import (
            CostToServeFacts,
        )
        assert "calculator_motor" in CostToServeFacts.__module__, (
            f"Expected calculator_motor, got {CostToServeFacts.__module__}"
        )

    def test_dto_models_defined_in_vision_cost_to_serve(self):
        """DTO types are defined in vision_cost_to_serve, not calculator_motor."""
        from nexa_engine.modules.vision_cost_to_serve.dto.models import (
            ResultadoCostToServe,
        )
        assert "vision_cost_to_serve" in ResultadoCostToServe.__module__, (
            f"DTO must be in vision_cost_to_serve, got {ResultadoCostToServe.__module__}"
        )

    def test_dto_init_exports_from_dto_models(self):
        """dto/__init__.py re-exports from dto/models.py, not from calculator_motor."""
        from pathlib import Path

        dto_init = (
            Path(__file__).parents[2]
            / "modules"
            / "vision_cost_to_serve"
            / "dto"
            / "__init__.py"
        ).read_text(encoding="utf-8")

        assert "from nexa_engine.modules.vision_cost_to_serve.dto.models import" in dto_init, (
            "dto/__init__.py must import from dto/models.py"
        )
        # The import line must reference dto.models, not calculator_motor
        import_lines = [
            l for l in dto_init.splitlines()
            if l.strip().startswith("from ") or l.strip().startswith("import ")
        ]
        for line in import_lines:
            assert "calculator_motor" not in line, (
                f"dto/__init__.py import line must not reference calculator_motor: {line}"
            )

    def test_models_init_reexports_directly_from_calculator_motor(self):
        """models/__init__.py re-exports directly from calculator_motor (Block 30)."""
        from pathlib import Path

        models_init = (
            Path(__file__).parents[2]
            / "modules"
            / "vision_cost_to_serve"
            / "models"
            / "__init__.py"
        ).read_text(encoding="utf-8")

        assert "calculator_motor.formulas.cts.cts_facts" in models_init, (
            "models/__init__.py must import directly from calculator_motor (Block 30). "
            "models/cts_facts.py wrapper was deleted."
        )

    def test_services_init_no_formula_classes(self):
        """services/__init__.py must not define any formula classes."""
        from pathlib import Path

        services_init = (
            Path(__file__).parents[2]
            / "modules"
            / "vision_cost_to_serve"
            / "services"
            / "__init__.py"
        ).read_text(encoding="utf-8")

        assert "class " not in services_init, (
            "services/__init__.py must not define any classes. "
            "It is a thin re-export layer."
        )
