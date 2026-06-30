"""
Phase 6B-1 structural guardrails.

Validates:
  G-6B1: modules/audit/ exists with canonical audit implementations.
  G-6B2: modules/traceability/lineage/ exists with canonical implementation.
  G-6B3: Canonical audit symbols importable from modules.audit paths.
  G-6B4: No production modules import from calculator.audit.* sub-modules.
  G-6B5: No production modules import from calculator.lineage.* sub-modules.
  G-6B6: legacy shared/traceability audit packages are gone.
  G-6B7: no audit-owned code remains under modules/traceability/audit.
  G-6B8: formulas/ does not import traceability (no circular dep).
"""
from __future__ import annotations

from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_MODULES = _BACKEND_ROOT / "modules"
_AUDIT = _MODULES / "audit"
_TRACEABILITY = _MODULES / "traceability"
_CALC = _MODULES / "calculator"
_CALC_MOTOR = _MODULES / "calculator_motor"


class TestPhase6B1CanonicalPathsExist:
    def test_g_6b1_audit_integration_exists(self):
        assert (_AUDIT / "integration.py").exists()

    def test_g_6b1_audit_writer_exists(self):
        assert (_AUDIT / "writer.py").exists()

    def test_g_6b1_audit_registry_exists(self):
        assert (_AUDIT / "registry.py").exists()

    def test_g_6b1_audit_trace_exists(self):
        assert (_AUDIT / "trace.py").exists()

    def test_g_6b2_traceability_lineage_builder_removed(self):
        assert not (_TRACEABILITY / "lineage" / "lineage_builder.py").exists(), (
            "traceability/lineage/lineage_builder.py should have been moved to "
            "modules/lineage/application/builder.py"
        )

    def test_g_6b3_audit_context_importable(self):
        from nexa_engine.modules.audit.integration import audit_context  # noqa: F401
        assert callable(audit_context)

    def test_g_6b3_traceability_writer_importable(self):
        from nexa_engine.modules.audit.writer import TraceabilityWriter  # noqa: F401
        assert "modules.audit.writer" in TraceabilityWriter.__module__

    def test_g_6b3_field_registry_importable(self):
        from nexa_engine.modules.audit.registry import FieldTraceabilityRegistry  # noqa: F401
        assert callable(FieldTraceabilityRegistry)

    def test_g_6b3_audit_tracer_importable(self):
        from nexa_engine.modules.audit.trace import AuditTracer  # noqa: F401
        assert callable(AuditTracer)

    def test_g_6b3_lineage_builder_importable(self):
        from nexa_engine.modules.lineage.application.builder import seed_lineage_from_request  # noqa: F401
        assert callable(seed_lineage_from_request)


class TestPhase6B1NoLegacyImports:
    """No production code may import from old sub-module paths."""

    def test_g_6b4_no_prod_imports_to_calculator_audit_submodules(self):
        fragment = "modules.calculator.audit."
        violations = []
        for py in _MODULES.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if fragment in text:
                violations.append(str(py.relative_to(_BACKEND_ROOT)))
        assert not violations, (
            "Production modules still import from calculator.audit sub-modules:\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_g_6b5_no_prod_imports_to_calculator_lineage_submodules(self):
        fragment = "modules.calculator.lineage."
        violations = []
        for py in _MODULES.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if fragment in text:
                violations.append(str(py.relative_to(_BACKEND_ROOT)))
        assert not violations, (
            "Production modules still import from calculator.lineage sub-modules:\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_g_6b7_traceability_audit_dir_removed(self):
        assert not (_TRACEABILITY / "audit").exists(), (
            "modules/traceability/audit should be empty/removed after audit boundary completion"
        )

    def test_g_6b2_calculator_audit_dir_has_no_py_files(self):
        """After 6B-2: calculator/audit/ must contain no .py files."""
        py_files = list((_CALC / "audit").rglob("*.py")) if (_CALC / "audit").exists() else []
        assert not py_files, (
            "calculator/audit/ still contains .py files after shim cleanup:\n"
            + "\n".join(f"  {f.relative_to(_BACKEND_ROOT)}" for f in py_files)
        )

    def test_g_6b2_calculator_lineage_dir_has_no_py_files(self):
        """After 6B-2: calculator/lineage/ must contain no .py files."""
        py_files = list((_CALC / "lineage").rglob("*.py")) if (_CALC / "lineage").exists() else []
        assert not py_files, (
            "calculator/lineage/ still contains .py files after shim cleanup:\n"
            + "\n".join(f"  {f.relative_to(_BACKEND_ROOT)}" for f in py_files)
        )


class TestPhase6B1LegacyAuditLocationsGone:
    def test_g_6b6_shared_audit_dir_removed(self):
        assert not (_MODULES / "shared" / "audit").exists(), (
            "modules/shared/audit should be empty/removed after audit boundary completion"
        )

    def test_g_6b6_audit_api_lives_in_modules_audit(self):
        assert (_AUDIT / "api" / "audit_router.py").exists()


class TestPhase6B1NoFormulasTraceability:
    """formulas/ must not directly import traceability or audit modules."""

    def test_g_6b8_formulas_do_not_import_traceability(self):
        formulas_root = _CALC_MOTOR / "formulas"
        violations = []
        for py in formulas_root.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if (
                "modules.traceability" in text
                or "modules.audit.integration" in text
                or "modules.audit.writer" in text
                or "modules.audit.registry" in text
                or "calculator.audit" in text
                or "calculator.lineage" in text
            ):
                violations.append(str(py.relative_to(_BACKEND_ROOT)))
        assert not violations, (
            "formulas/ imports traceability/audit runtime modules (creates cycle):\n"
            + "\n".join(f"  {v}" for v in violations)
        )


_LINEAGE = _MODULES / "lineage"


class TestLineageModuleOwnership:
    """Lineage bounded-context guardrails (post-extraction to modules/lineage/).

    After LINEAGE_BOUNDED_CONTEXT_EXTRACTION:
      - Old scatter locations (shared/lineage/, shared/infrastructure/lineage/,
        traceability/lineage/) are removed.
      - Canonical home is modules/lineage/{domain,infrastructure,application}/.
    """

    # ── G-LINEAGE-1: old scatter locations must not exist ───────────────────

    def test_g_lineage_1_shared_lineage_dir_removed(self):
        """shared/lineage/ must be gone — moved to lineage/domain/."""
        assert not (_MODULES / "shared" / "lineage" / "models.py").exists(), (
            "shared/lineage/models.py still exists — should have been moved to "
            "modules/lineage/domain/models.py"
        )
        assert not (_MODULES / "shared" / "lineage" / "query.py").exists(), (
            "shared/lineage/query.py still exists — should have been moved to "
            "modules/lineage/domain/query.py"
        )

    def test_g_lineage_2_shared_infrastructure_lineage_dir_removed(self):
        """shared/infrastructure/lineage/ must be gone — moved to lineage/infrastructure/."""
        assert not (_MODULES / "shared" / "infrastructure" / "lineage" / "json_lineage_emitter.py").exists(), (
            "shared/infrastructure/lineage/json_lineage_emitter.py still exists — "
            "should have been moved to modules/lineage/infrastructure/json_emitter.py"
        )
        assert not (_MODULES / "shared" / "infrastructure" / "lineage" / "snapshot_repository.py").exists(), (
            "shared/infrastructure/lineage/snapshot_repository.py still exists — "
            "should have been moved to modules/lineage/infrastructure/snapshot_repository.py"
        )

    def test_g_lineage_3_traceability_lineage_builder_removed(self):
        """traceability/lineage/lineage_builder.py must be gone — moved to lineage/application/builder.py."""
        assert not (_TRACEABILITY / "lineage" / "lineage_builder.py").exists(), (
            "traceability/lineage/lineage_builder.py still exists — should have been moved to "
            "modules/lineage/application/builder.py"
        )

    # ── G-LINEAGE-4: canonical symbols importable from new layer paths ───────

    def test_g_lineage_4_domain_models_importable(self):
        from nexa_engine.modules.lineage.domain.models import (  # noqa: F401
            LineageGraph, LineageNode, LineageRef,
        )
        assert "lineage.domain.models" in LineageGraph.__module__
        assert "lineage.domain.models" in LineageNode.__module__
        assert "lineage.domain.models" in LineageRef.__module__

    def test_g_lineage_4_domain_query_importable(self):
        from nexa_engine.modules.lineage.domain.query import LineageQuery  # noqa: F401
        assert "lineage.domain.query" in LineageQuery.__module__

    def test_g_lineage_4_infrastructure_json_emitter_importable(self):
        from nexa_engine.modules.lineage.infrastructure.json_emitter import JsonLineageEmitter  # noqa: F401
        assert "lineage.infrastructure.json_emitter" in JsonLineageEmitter.__module__

    def test_g_lineage_4_infrastructure_null_emitter_importable(self):
        from nexa_engine.modules.lineage.infrastructure.null_emitter import NullLineageEmitter  # noqa: F401
        assert callable(NullLineageEmitter)

    def test_g_lineage_4_infrastructure_snapshot_repository_importable(self):
        from nexa_engine.modules.lineage.infrastructure.snapshot_repository import LineageSnapshotRepository  # noqa: F401
        assert "lineage.infrastructure.snapshot_repository" in LineageSnapshotRepository.__module__

    def test_g_lineage_4_application_builder_importable(self):
        from nexa_engine.modules.lineage.application.builder import (  # noqa: F401
            seed_lineage_from_request, seed_lineage_from_result,
        )
        assert "lineage.application.builder" in seed_lineage_from_request.__module__
        assert "lineage.application.builder" in seed_lineage_from_result.__module__

    # ── G-LINEAGE-5: route unchanged ─────────────────────────────────────────

    def test_g_lineage_5_route_registration(self):
        """GET /api/v1/simulation/{simulation_id}/traceability is still registered."""
        from nexa_engine.app import create_app

        app = create_app()
        routes = {route.path for route in app.routes}
        traceability_route_exists = any(
            "/simulation/{simulation_id}/traceability" in route or
            "/api/v1/simulation/{simulation_id}/traceability" in route
            for route in routes
        )
        assert traceability_route_exists, (
            f"Route /api/v1/simulation/{{simulation_id}}/traceability not found. "
            f"Available routes: {routes}"
        )

    # ── G-LINEAGE-6: consumer snapshot updated to nexa_engine.modules.lineage ─

    def test_g_lineage_6_consumer_snapshot(self):
        """Known consumers now import from nexa_engine.modules.lineage (not old paths)."""
        consumer_paths = [
            # canonical locations after shared-cleanup (shims at old shared/use_cases/ paths)
            _MODULES / "audit" / "use_cases" / "audit_simulation.py",
            _MODULES / "calculator" / "use_cases" / "certified_calculation.py",
            _MODULES / "calculator_motor" / "engine.py",
        ]
        importing_new = []
        importing_old = []
        for path in consumer_paths:
            if not path.exists():
                continue
            src = path.read_text(encoding="utf-8")
            if "from nexa_engine.modules.lineage" in src:
                importing_new.append(str(path.relative_to(_BACKEND_ROOT)))
            if (
                "from nexa_engine.modules.shared.lineage" in src
                or "from nexa_engine.modules.shared.infrastructure.lineage" in src
                or "from nexa_engine.modules.traceability.lineage" in src
            ):
                importing_old.append(str(path.relative_to(_BACKEND_ROOT)))

        assert importing_old == [], (
            "Consumers still import from stale lineage paths:\n"
            + "\n".join(f"  {v}" for v in importing_old)
        )
        assert len(importing_new) >= 2, (
            f"Expected ≥2 consumers importing from modules.lineage; found: {importing_new}"
        )

    # ── Anti-regression: stale paths raise ModuleNotFoundError ───────────────

    def test_g_lineage_anti_regression_shared_lineage_not_importable(self):
        import importlib, sys
        for stale in (
            "nexa_engine.modules.shared.lineage.models",
            "nexa_engine.modules.shared.lineage.query",
        ):
            sys.modules.pop(stale, None)
            try:
                importlib.import_module(stale)
                raise AssertionError(f"{stale} should raise ModuleNotFoundError but imported OK")
            except (ModuleNotFoundError, ImportError):
                pass

    def test_g_lineage_anti_regression_traceability_lineage_not_importable(self):
        import importlib, sys
        stale = "nexa_engine.modules.traceability.lineage.lineage_builder"
        sys.modules.pop(stale, None)
        try:
            importlib.import_module(stale)
            raise AssertionError(f"{stale} should raise ModuleNotFoundError but imported OK")
        except (ModuleNotFoundError, ImportError):
            pass

    # ── Structural: new layer directories and files exist ────────────────────

    def test_g_lineage_structural_domain_layer(self):
        assert (_LINEAGE / "domain" / "models.py").exists()
        assert (_LINEAGE / "domain" / "query.py").exists()

    def test_g_lineage_structural_infrastructure_layer(self):
        assert (_LINEAGE / "infrastructure" / "json_emitter.py").exists()
        assert (_LINEAGE / "infrastructure" / "null_emitter.py").exists()
        assert (_LINEAGE / "infrastructure" / "snapshot_repository.py").exists()

    def test_g_lineage_structural_application_layer(self):
        assert (_LINEAGE / "application" / "builder.py").exists()


class TestPhase6CPersistenceCanonical:
    """G-6C: calculator/persistence/ is the canonical persistence path (was calculator_persistence/)."""

    def test_g_6c1_results_repository_canonical_exists(self):
        assert (_CALC / "persistence" / "results_repository.py").exists()

    def test_g_6c2_traceability_repository_canonical_exists(self):
        assert (_CALC / "persistence" / "traceability_repository.py").exists()

    def test_g_6c3_results_repository_importable(self):
        from nexa_engine.modules.calculator.persistence.results_repository import ResultsRepository  # noqa: F401
        assert "calculator.persistence" in ResultsRepository.__module__

    def test_g_6c4_traceability_repository_importable(self):
        from nexa_engine.modules.calculator.persistence.traceability_repository import TraceabilityRepository  # noqa: F401
        assert callable(TraceabilityRepository)

    def test_g_6c5_no_prod_imports_to_legacy_calculator_persistence(self):
        """Legacy modules.calculator_persistence.* must no longer be imported."""
        fragment = "modules.calculator_persistence."
        violations = []
        for py in _MODULES.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if fragment in text:
                violations.append(str(py.relative_to(_BACKEND_ROOT)))
        assert not violations, (
            "Production modules still import from legacy calculator_persistence:\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_g_6c6_legacy_calculator_persistence_dir_gone(self):
        """After rename: legacy modules/calculator_persistence/ must no longer exist."""
        assert not (_MODULES / "calculator_persistence").exists(), (
            "Legacy modules/calculator_persistence/ still exists — should have been renamed to calculator/persistence/"
        )

    def test_g_6c7_engine_does_not_import_persistence(self):
        engine_src = (_CALC_MOTOR / "engine.py").read_text(encoding="utf-8")
        assert "calculator_persistence" not in engine_src
        assert "calculator.persistence" not in engine_src

    def test_g_6c8_formulas_do_not_import_persistence(self):
        violations = []
        for py in (_CALC_MOTOR / "formulas").rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if "calculator_persistence" in text or "calculator.persistence" in text:
                violations.append(str(py.relative_to(_BACKEND_ROOT)))
        assert not violations
