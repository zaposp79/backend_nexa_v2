"""
Phase 6D-B / Phase 8A structural guardrails — updated for calculator_motor rename.

After the rename:
  - modules/calculator_motor/ = engine, formulas, adapters, dto, etc. (was calculator/)
  - modules/calculator/api/   = HTTP endpoints (was calculator_api/)
  - modules/calculator/persistence/ = repos (was calculator_persistence/)

Validates:
  G-6D1: modules/calculator/api/calculate_router.py exists.
  G-6D2: modules/calculator/api/results_router.py exists (moved from traceability/api).
  G-6D3: modules/calculator/api/calculate_dependencies.py exists.
  G-6D4: calculate_router importable from calculator.api canonical path.
  G-6D5: results_router importable from calculator.api canonical path.
  G-6D6: legacy modules/calculator_api/ dir no longer exists.
  G-6D7: No production module imports from legacy modules.calculator_api.* paths.
  G-6D8: modules/calculator_motor/formulas/ does not import calculator.api (no cycle).
  G-6D9: modules/calculator_motor/engine.py does not import calculator.api.
  G-6D10: modules/api_v1/router.py mounts calculate_router from calculator.api.
  G-8A1: modules/traceability/ no longer exists (consolidated).
  G-8A2: results_router now in calculator/api/ (not traceability/api/).
  G-8A3: No production code imports from deprecated traceability_api.
  G-OWN1: calculator/api must not define public vision endpoints.
  G-OWN2: legacy /simulation/{simulation_id}/vision/pyg route must stay absent.
"""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import backend_nexa  # noqa: F401

from nexa_engine.app import create_app

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_MODULES = _BACKEND_ROOT / "modules"
_CALC = _MODULES / "calculator"
_CALC_API = _MODULES / "calculator" / "api"
_CALC_MOTOR = _MODULES / "calculator_motor"


class TestPhase6DBCanonicalPathsExist:
    def test_g_6d1_calculate_router_exists(self):
        assert (_CALC_API / "calculate_router.py").exists()

    def test_g_6d2_results_router_in_calculator_api(self):
        """results_router.py must exist in calculator/api/ (canonical home)."""
        assert (_CALC_API / "results_router.py").exists(), (
            "results_router.py not found in calculator/api/"
        )

    def test_g_6d3_calculate_dependencies_exists(self):
        assert (_CALC_API / "calculate_dependencies.py").exists()

    def test_g_6d4_calculate_router_importable(self):
        from nexa_engine.modules.calculator.api.calculate_router import router  # noqa: F401
        assert router.prefix == "/simulation"

    def test_g_6d5_results_router_importable(self):
        from nexa_engine.modules.calculator.api.results_router import router  # noqa: F401
        assert router.prefix == "/simulation"

    def test_g_6d5_calculate_dto_importable(self):
        from nexa_engine.modules.calculator.api.calculate_dto import CalculationRequest  # noqa: F401
        assert callable(CalculationRequest)

    def test_g_6d5_calculate_dependencies_importable(self):
        from nexa_engine.modules.calculator.api.calculate_dependencies import _results_repo  # noqa: F401
        assert _results_repo is not None


class TestPhase6DBLegacyPathGone:
    def test_g_6d6_old_calculator_api_dir_gone(self):
        """After rename: legacy modules/calculator_api/ must no longer exist."""
        assert not (_MODULES / "calculator_api").exists(), (
            "Legacy modules/calculator_api/ still exists — should have been renamed to calculator/api/"
        )

    def test_g_6d7_no_prod_imports_from_legacy_calculator_api(self):
        """No production module may import from legacy modules.calculator_api.* paths."""
        fragment = "modules.calculator_api."
        violations = []
        for py in _MODULES.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if fragment in text:
                violations.append(str(py.relative_to(_BACKEND_ROOT)))
        assert not violations, (
            "Production modules still import from legacy calculator_api:\n"
            + "\n".join(f"  {v}" for v in violations)
        )


class TestPhase6DBNoCycles:
    def test_g_6d8_formulas_do_not_import_calculator_api(self):
        """calculator_motor/formulas/ must not import calculator.api (would create cycle)."""
        violations = []
        for py in (_CALC_MOTOR / "formulas").rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if "modules.calculator_api" in text or "modules.calculator.api" in text:
                violations.append(str(py.relative_to(_BACKEND_ROOT)))
        assert not violations, (
            "formulas/ imports calculator.api (creates cycle):\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_g_6d9_engine_does_not_import_calculator_api(self):
        """calculator_motor/engine.py must not import calculator.api."""
        engine_src = (_CALC_MOTOR / "engine.py").read_text(encoding="utf-8")
        assert "calculator_api" not in engine_src
        assert "modules.calculator.api" not in engine_src


class TestPhase6DBMountPreserved:
    def test_g_6d10_api_v1_router_mounts_correctly(self):
        """api_v1/router.py: both calculate_router and results_router from calculator.api."""
        router_src = (_MODULES / "api_v1" / "router.py").read_text(encoding="utf-8")
        assert "modules.calculator.api.calculate_router" in router_src, (
            "api_v1/router.py must import calculate_router from calculator.api"
        )
        assert "modules.calculator.api.results_router" in router_src, (
            "api_v1/router.py must import results_router from calculator.api"
        )
        assert "modules.calculator_api.results_router" not in router_src, (
            "api_v1/router.py still references legacy calculator_api.results_router"
        )
        assert "modules.traceability_api.results_router" not in router_src, (
            "api_v1/router.py still references deprecated traceability_api path"
        )
        assert "modules.traceability.api.results_router" not in router_src, (
            "api_v1/router.py still references deprecated traceability.api path"
        )
        assert "modules.calculator_api.calculate_router" not in router_src, (
            "api_v1/router.py still references legacy calculator_api path"
        )

    def test_g_6d10_calculate_router_prefix_unchanged(self):
        """POST /simulation/calculate prefix must remain /simulation."""
        from nexa_engine.modules.calculator.api.calculate_router import router
        assert router.prefix == "/simulation"

    def test_g_6d10_results_router_prefix_unchanged(self):
        """GET /simulation/{id}/results prefix must remain /simulation."""
        from nexa_engine.modules.calculator.api.results_router import router
        assert router.prefix == "/simulation"


class TestPhase7LineageRepoOwnership:
    """G-7: _lineage_repo ownership moved to db.dependencies (Phase 7)."""

    def test_g_7_1_lineage_repo_importable_from_db_dependencies(self):
        from nexa_engine.db.dependencies import _lineage_repo  # noqa: F401
        assert _lineage_repo is not None

    def test_g_7_2_shared_certification_does_not_import_calculator_api(self):
        """shared/certification/ must not import from legacy modules.calculator_api."""
        cert_root = _MODULES / "shared" / "certification"
        violations = []
        for py in cert_root.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if "modules.calculator_api" in text:
                violations.append(str(py.relative_to(_BACKEND_ROOT)))
        assert not violations, (
            "shared/certification imports from legacy calculator_api:\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_g_7_3_lineage_repo_same_instance_in_calculator_api(self):
        """calculator/api/_lineage_repo must be the same object as db.dependencies._lineage_repo."""
        from nexa_engine.db.dependencies import _lineage_repo as canonical
        from nexa_engine.modules.calculator.api.calculate_dependencies import _lineage_repo as calc_lr
        assert canonical is calc_lr, "_lineage_repo in calculator.api must be the db.dependencies singleton"

    def test_g_7_4_calculator_api_does_not_instantiate_lineage_repo(self):
        """calculate_dependencies.py must not instantiate LineageSnapshotRepository itself."""
        src = (_CALC_API / "calculate_dependencies.py").read_text(encoding="utf-8")
        assert "LineageSnapshotRepository(" not in src, (
            "calculator/api/calculate_dependencies.py must not instantiate LineageSnapshotRepository — "
            "import from db.dependencies instead"
        )


class TestPhase8ATraceabilityConsolidated:
    """G-8A: modules/traceability/ removed; results_router consolidated into calculator/api/."""

    def test_g_8a1_traceability_module_removed(self):
        """modules/traceability/ must no longer exist."""
        assert not (_MODULES / "traceability").exists(), (
            "modules/traceability/ still exists — should have been removed. "
            "results_router is now in calculator/api/; traceability/audit was in modules/audit/"
        )

    def test_g_8a1_deprecated_traceability_api_dir_gone(self):
        """Legacy modules/traceability_api/ must also be absent."""
        assert not (_MODULES / "traceability_api").exists(), (
            "Deprecated modules/traceability_api directory should be removed"
        )

    def test_g_8a2_results_router_in_calculator_api(self):
        """calculator/api/results_router.py is the canonical home."""
        assert (_CALC_API / "results_router.py").exists(), (
            "results_router.py not found in calculator/api/"
        )

    def test_g_8a3_no_production_import_of_deprecated_traceability_paths(self):
        """No production module may import from deprecated traceability paths."""
        violations = []
        for py in _MODULES.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if "modules.traceability_api." in text or "modules.traceability.api." in text:
                violations.append(str(py.relative_to(_BACKEND_ROOT)))
        assert not violations, (
            "Production modules import from deprecated traceability paths:\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_g_8a4_results_router_importable_from_calculator_api(self):
        from nexa_engine.modules.calculator.api.results_router import router  # noqa: F401
        assert router.prefix == "/simulation"


class TestModuleEndpointOwnershipGuardrails:
    def test_g_own1_calculator_api_router_only_exposes_calculate(self):
        from nexa_engine.modules.calculator.api.calculate_router import router

        route_paths = {
            route.path
            for route in router.routes
            if getattr(route, "path", None)
        }
        assert route_paths == {"/simulation/calculate"}, (
            "calculator/api must expose only POST /simulation/calculate; "
            f"found {sorted(route_paths)}"
        )

    def test_g_own1_calculator_api_has_no_vision_route_fragments(self):
        violations = []
        forbidden_patterns = [
            '@router.get("/{simulation_id}/results/vision-',
            '@router.post("/{simulation_id}/results/vision-',
            '@router.get("/{simulation_id}/vision/pyg"',
            '@router.post("/{simulation_id}/vision/pyg"',
        ]
        for py in _CALC_API.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if any(pattern in text for pattern in forbidden_patterns):
                violations.append(str(py.relative_to(_BACKEND_ROOT)))
        assert not violations, (
            "calculator/api defines vision routes that belong in vision modules:\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_g_own2_openapi_keeps_legacy_vision_pyg_removed(self):
        client = TestClient(create_app())
        schema = client.get("/openapi.json").json()
        paths = schema.get("paths", {})

        assert "/api/v1/simulation/{simulation_id}/vision/pyg" not in paths
        assert "/api/v1/simulation/{simulation_id}/results/vision-pyg" in paths
