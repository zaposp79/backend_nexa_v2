"""Guardrails for modules/shared integrity.

Prevents regressions introduced by accidental moves, deletions or additions:

1. Oracle-blocked files (precision.py) must not move. profitability/calculators.py was migrated to calculator_motor/formulas/profitability/.
2. Wire-contract package (contracts/api_v1/) must not move.
3. Certification remains the only public shared/**/api package.
4. shared/helpers/ must not accumulate new files with zero production consumers.
5. shared/lineage/lineage_builder.py must NOT be reintroduced (real file moved to
   calculator/lineage/; shim was removed in FASE SHARED.2).
6. shared/audit/trace_integration.py, traceability_registry.py, traceability_writer.py
   are shims only — real files are in calculator/audit/.
7. loader.py must not be relocated without co-moving its YAML data files.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend_nexa  # noqa: F401

from nexa_engine.app import create_app

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SHARED_ROOT = BACKEND_ROOT / "modules" / "shared"


# ---------------------------------------------------------------------------
# 1. Oracle-blocked files must not be removed or relocated
# ---------------------------------------------------------------------------

class TestOracleBlockedFilesUnmoved:

    def test_precision_py_still_in_shared(self):
        p = SHARED_ROOT / "precision.py"
        assert p.exists(), (
            "precision.py was removed or relocated from shared/. "
            "This file is Oracle-blocked and must never be moved."
        )

    def test_precision_py_exports_cop_round(self):
        """Verify the file content hasn't been gutted."""
        src = (SHARED_ROOT / "precision.py").read_text()
        assert "def cop_round" in src, "precision.py is missing cop_round — possible tampering"

    def test_profitability_calculators_in_canonical_location(self):
        """ProfitabilityCalculator must live in calculator_motor/formulas/profitability/ (canonical)."""
        p = BACKEND_ROOT / "modules" / "calculator_motor" / "formulas" / "profitability" / "calculators.py"
        assert p.exists(), (
            "calculator_motor/formulas/profitability/calculators.py missing — "
            "ProfitabilityCalculator must be in the motor's canonical location."
        )

    def test_profitability_calculators_exports_class(self):
        src = (BACKEND_ROOT / "modules" / "calculator_motor" / "formulas" / "profitability" / "calculators.py").read_text()
        assert "class ProfitabilityCalculator" in src, (
            "calculator_motor/formulas/profitability/calculators.py is missing ProfitabilityCalculator"
        )

    def test_shared_profitability_shim_removed(self):
        """Shim shared/profitability/ must be gone after FASE 2B cleanup."""
        assert not (SHARED_ROOT / "profitability").exists(), (
            "modules/shared/profitability/ still exists — shim should have been removed. "
            "Canonical location: calculator_motor/formulas/profitability/"
        )

    def test_visions_cts_duplicate_removed(self):
        """shared/models/visions_cts.py must be gone — canonical is vision_cost_to_serve/dto/models.py."""
        assert not (SHARED_ROOT / "models" / "visions_cts.py").exists(), (
            "shared/models/visions_cts.py still exists — duplicate removed in Fase 2B. "
            "Canonical: modules/vision_cost_to_serve/dto/models.py"
        )

    def test_visions_pyg_duplicate_removed(self):
        """shared/models/visions_pyg.py must be gone — canonical is vision_pyg/models/."""
        assert not (SHARED_ROOT / "models" / "visions_pyg.py").exists(), (
            "shared/models/visions_pyg.py still exists — duplicate removed in Fase 2B. "
            "Canonical: modules/vision_pyg/models/__init__.py"
        )

    def test_cts_canonical_location_exists(self):
        """CTS DTOs must live in vision_cost_to_serve/dto/models.py."""
        p = BACKEND_ROOT / "modules" / "vision_cost_to_serve" / "dto" / "models.py"
        assert p.exists(), "vision_cost_to_serve/dto/models.py missing — CTS DTOs have no canonical home"

    def test_pyg_models_canonical_location_exists(self):
        """PyG models must live in vision_pyg/models/__init__.py."""
        p = BACKEND_ROOT / "modules" / "vision_pyg" / "models" / "__init__.py"
        assert p.exists(), "vision_pyg/models/__init__.py missing — PyG models have no canonical home"

    def test_visions_shim_deleted(self):
        """shared/models/visions.py must NOT exist after shared-cleanup.

        CTS: import from vision_cost_to_serve/dto/models.py
        PyG: import from vision_pyg/models/
        """
        shim = SHARED_ROOT / "models" / "visions.py"
        assert not shim.exists(), (
            "shared/models/visions.py was recreated. "
            "Shim was deleted in shared-cleanup pass."
        )

    def test_cts_symbol_importable_from_canonical(self):
        """ResultadoCostToServe must be importable from canonical CTS location."""
        from nexa_engine.modules.vision_cost_to_serve.dto.models import ResultadoCostToServe  # noqa: F401

    def test_pyg_symbol_importable_from_canonical(self):
        """VisionPyG must be importable from canonical PyG location."""
        from nexa_engine.modules.vision_pyg.models import VisionPyG  # noqa: F401

    def test_pyg_symbol_importable_from_compat_shim(self):
        """Legacy modules.pyg import path must still work via shim."""
        from nexa_engine.modules.pyg.dto.models import VisionPyG  # noqa: F401


# ---------------------------------------------------------------------------
# 1b. Nested-support types (Fase 2C) — zero importers ≠ dead code
# ---------------------------------------------------------------------------

class TestNestedSupportTypesProtected:

    def test_nested_support_types_used_by_parents(self):
        """MesComision and TarifaXVenta are NESTED_SUPPORT types nested
        inside ComponenteVariable and ResultadoVisionTarifas respectively.
        Zero direct importers does NOT mean dead code. Protect against
        accidental removal.
        Verified in Fase 2C audit (2026-06-10).
        After shared-cleanup: import from vision_tarifas canonical paths.
        """
        from nexa_engine.modules.vision_tarifas.dto.models import (
            ComponenteVariable,
            EscenarioTarifasDetalle,
            MesComision,
            TarifaXVenta,
        )
        assert "MesComision" in str(ComponenteVariable.__annotations__), (
            "MesComision must remain a field type of ComponenteVariable — "
            "it is a nested support type, not dead code"
        )
        assert "TarifaXVenta" in str(EscenarioTarifasDetalle.__annotations__), (
            "TarifaXVenta must remain a field type of EscenarioTarifasDetalle — "
            "it is a nested support type, not dead code"
        )


# ---------------------------------------------------------------------------
# 1c. Pipeline output models (results.py) — ownership inverted (2026-06-10)
# ---------------------------------------------------------------------------

class TestPipelineResultsOwnership:
    """Ownership inverted: canonical = calculator_motor/models/results.py.
    shared/models/results.py is now a backward-compat adapter.
    Guardrail ensures the adapter remains (backward compat) and canonical
    home has the real definitions."""

    def test_shared_results_adapter_still_exists(self):
        p = SHARED_ROOT / "models" / "results.py"
        assert p.exists(), (
            "shared/models/results.py was removed. It must remain as a "
            "backward-compat adapter pointing to calculator_motor/models/results.py."
        )

    def test_pricing_result_not_defined_in_shared_adapter(self):
        src = (SHARED_ROOT / "models" / "results.py").read_text()
        assert "class PricingResult" not in src, (
            "shared/models/results.py defines PricingResult directly — "
            "it must be an adapter only. Canonical: calculator_motor/models/results.py."
        )

    def test_shared_results_imports_from_canonical(self):
        src = (SHARED_ROOT / "models" / "results.py").read_text()
        assert "calculator_motor.models.results" in src, (
            "shared/models/results.py must import from calculator_motor.models.results "
            "(canonical location after ownership inversion 2026-06-10)."
        )


# ---------------------------------------------------------------------------
# 2. Wire-contract package must not be moved
# ---------------------------------------------------------------------------

class TestWireContractNotMoved:

    def test_contracts_api_v1_init_exists(self):
        p = SHARED_ROOT / "contracts" / "api_v1" / "__init__.py"
        assert p.exists(), (
            "contracts/api_v1/__init__.py was removed or relocated. "
            "This is the frozen public wire contract — never move it."
        )

    def test_entry_data_v1_importable(self):
        from nexa_engine.modules.shared.contracts.api_v1 import EntryDataV1  # noqa: F401

    def test_simulation_result_v1_importable(self):
        from nexa_engine.modules.shared.contracts.api_v1 import SimulationResultV1  # noqa: F401


# ---------------------------------------------------------------------------
# 3. No unmounted shared routers
# ---------------------------------------------------------------------------

class TestNoUnmountedSharedRouters:
    """Every FastAPI router defined in shared/**/api/ must be reachable from
    the application's api_router (mounted or in the import chain)."""

    def _find_shared_api_routers(self):
        """Return list of (module_path, var_name) for shared api routers."""
        found = []
        for init in (SHARED_ROOT / "certification" / "api",):
            init_file = init / "__init__.py"
            if init_file.exists():
                src = init_file.read_text()
                if "router" in src:
                    found.append(str(init_file))
        return found

    def test_shared_audit_package_removed(self):
        """Audit should no longer live under modules/shared/audit."""
        assert not (SHARED_ROOT / "audit").exists(), (
            "modules/shared/audit should be removed after audit boundary completion"
        )

    def test_audit_router_is_mounted_from_modules_audit(self):
        """audit_router must appear in modules/api_v1/router.py from modules.audit."""
        router_src = (BACKEND_ROOT / "modules" / "api_v1" / "router.py").read_text()
        assert "from nexa_engine.modules.audit.api.audit_router" in router_src, (
            "audit_router is not mounted in modules/api_v1/router.py. "
            "Add: router.include_router(audit_router)"
        )
        assert "modules.shared.audit.api" not in router_src, (
            "api_v1/router.py must not import public audit API from modules/shared/audit/api"
        )

    def test_audit_routes_remain_registered_with_same_paths(self):
        """Public /api/v1/audit/* paths must remain unchanged after module move."""
        client = TestClient(create_app())
        paths = client.get("/openapi.json").json().get("paths", {})

        expected_paths = {
            "/api/v1/audit/simulations",
            "/api/v1/audit/simulation/{simulation_id}",
            "/api/v1/audit/simulation/{simulation_id}/explain",
            "/api/v1/audit/simulation/{simulation_id}/baseline-diff",
        }
        missing = sorted(expected_paths - set(paths))
        assert not missing, f"Missing audit paths after module move: {missing}"

    def test_certification_router_is_mounted_in_api_v1(self):
        """certification_router must appear in modules/api_v1/router.py from canonical path."""
        router_src = (BACKEND_ROOT / "modules" / "api_v1" / "router.py").read_text()
        assert (
            "certification_router" in router_src
            or "from nexa_engine.modules.certification.api" in router_src
        ), (
            "certification_router is not mounted in modules/api_v1/router.py. "
            "Add: router.include_router(certification_router)"
        )


# ---------------------------------------------------------------------------
# 4. shared/helpers/ must not accumulate zero-consumer orphans
# ---------------------------------------------------------------------------

class TestSharedHelpersNoOrphans:
    """Files in shared/helpers/ must have at least one production importer."""

    def _get_production_importers(self, module_path: str) -> int:
        """Count modules outside shared/ that import from module_path."""
        count = 0
        for py_file in BACKEND_ROOT.rglob("*.py"):
            if "__pycache__" in str(py_file) or ".claude" in str(py_file) or "venv" in str(py_file):
                continue
            if "modules/shared" in str(py_file):
                continue
            if "tests/" in str(py_file):
                continue
            try:
                src = py_file.read_text(encoding="utf-8", errors="replace")
                if module_path in src:
                    count += 1
            except Exception:
                pass
        return count

    def test_certified_helpers_shim_deleted(self):
        """shared/helpers/certified_helpers.py must not exist after shared-cleanup.

        Canonical location: modules/calculator/use_cases/certified_helpers.py
        Removed in: shared-cleanup pass (residual shims elimination).
        """
        shim = SHARED_ROOT / "helpers" / "certified_helpers.py"
        assert not shim.exists(), (
            "shared/helpers/certified_helpers.py was recreated. "
            "Canonical: modules/calculator/use_cases/certified_helpers.py."
        )
        # Verify canonical still exists
        canonical = BACKEND_ROOT / "modules" / "calculator" / "use_cases" / "certified_helpers.py"
        assert canonical.exists(), (
            "canonical certified_helpers.py missing from calculator/use_cases/. "
            "Do not delete the canonical file."
        )

    def test_shared_infrastructure_storage_directory_does_not_exist(self):
        """shared/infrastructure/storage/ must not exist.

        Deleted in FASE DB.6.6 (2026-06-04) after all consumers were migrated:
          - VersionSummary → parametrizacion/shared/models/version_summary.py
          - read_json/write_json/ensure_dir → parametrizacion/shared/infrastructure/json_store.py
          - BaseRepository deleted (no production consumers)
          - Shims removed
        """
        storage_dir = SHARED_ROOT / "infrastructure" / "storage"
        assert not storage_dir.exists(), (
            "shared/infrastructure/storage/ was recreated. "
            "This directory must not exist — all contents were migrated to "
            "parametrizacion/shared/ and the shims were removed in FASE DB.6.6. "
            "Do NOT reintroduce this directory."
        )

    def test_base_repository_class_not_anywhere_in_shared(self):
        """BaseRepository class must not exist anywhere in shared/.

        It was deleted in FASE DB.6.5 — nobody subclasses it.
        GN, HR and OP use DocumentStore directly.
        """
        for py_file in SHARED_ROOT.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            src = py_file.read_text()
            assert "class BaseRepository" not in src, (
                f"BaseRepository class was reintroduced in {py_file}. "
                "It should not exist — GN, HR and OP use DocumentStore directly."
            )

    def test_parallel_parametrization_repos_do_not_exist(self):
        """JsonParametrizationRepository and CosmosParametrizationRepository must not exist.

        These were deleted in FASE DB.6.7 (2026-06-04) — they had zero production
        consumers and were superseded by the DocumentStore-based GN/HR/OP repositories.
        """
        parametrization_shared = BACKEND_ROOT / "modules" / "parametrizacion" / "shared"
        for forbidden in (
            "repositories/json_parametrization_repository.py",
            "repositories/cosmos_parametrization_repository.py",
            "ports/parametrization_repository.py",
            "models/parametrization_version.py",
        ):
            p = parametrization_shared / forbidden
            assert not p.exists(), (
                f"Deleted file was recreated: parametrizacion/shared/{forbidden}. "
                f"These parallel persistence abstractions were removed because all "
                f"GN/HR/OP repositories now use DocumentStore directly."
            )

    def test_no_runtime_imports_to_deleted_storage_path(self):
        """No production module may import from shared.infrastructure.storage.

        That path was deleted in FASE DB.6.6.  All consumers were migrated to
        parametrizacion/shared/ before deletion.

        Docstrings/comments that mention the old path are allowed; only
        actual ``from ... import`` or ``import ...`` statements are forbidden.
        """
        forbidden_import = "from nexa_engine.modules.shared.infrastructure.storage"
        violations = []
        for py_file in BACKEND_ROOT.rglob("*.py"):
            if any(x in str(py_file) for x in ["__pycache__", ".claude", "venv/"]):
                continue
            if str(py_file).startswith(str(BACKEND_ROOT / "tests")):
                continue
            try:
                src = py_file.read_text(encoding="utf-8", errors="replace")
                if forbidden_import in src:
                    violations.append(str(py_file.relative_to(BACKEND_ROOT)))
            except Exception:
                pass
        assert not violations, (
            f"Found runtime imports to deleted path 'shared.infrastructure.storage' in: "
            f"{violations}. Update these imports to use "
            f"parametrizacion/shared/models/version_summary.py or "
            f"parametrizacion/shared/infrastructure/json_store.py."
        )

    def test_lineage_builder_not_reintroduced_in_shared(self):
        """shared/lineage/lineage_builder.py must not be reintroduced.

        Real file lives at calculator/lineage/lineage_builder.py.
        The shim was removed in FASE SHARED.2; its absence is the correct state.
        """
        shim = SHARED_ROOT / "lineage" / "lineage_builder.py"
        assert not shim.exists(), (
            "shared/lineage/lineage_builder.py was reintroduced. "
            "The real file lives at calculator/lineage/lineage_builder.py. "
            "Do not re-create a full copy here — update callers instead."
        )

    def test_audit_single_consumer_files_are_shims_only(self):
        """trace_integration.py, traceability_registry.py, traceability_writer.py
        must be shims (re-exports), not full implementations, since they moved to
        calculator/audit/ in FASE SHARED.2.
        """
        for name in ("trace_integration.py", "traceability_registry.py", "traceability_writer.py"):
            p = SHARED_ROOT / "audit" / name
            if not p.exists():
                continue  # file removed — even better
            src = p.read_text()
            assert "calculator.audit" in src, (
                f"shared/audit/{name} appears to be a full implementation, not a shim. "
                f"Real file is at calculator/audit/{name}. "
                f"Shared file should only re-export from the new location."
            )

    def test_no_get_provider_in_router_module_scope(self):
        """No router API file may call get_provider() at module scope.

        Routers must receive DocumentStore-backed repositories via FastAPI
        Depends() and db/dependencies.py.  Calling get_provider() at import
        time ties the router's store lifecycle to module load, preventing
        proper DI and making Cosmos backend switching unsafe.

        Allowed exceptions:
          - calculate_dependencies.py  (explicit composition root for calculate flow)
          - context_builder.py         (provider fallback for testing — not a router)
          - definition lines (def get_provider, def get_parametrization_store)
        """
        api_dirs = [
            BACKEND_ROOT / "modules" / d
            for d in [
                "calculator/api",
                "vision_cost_to_serve/api",
                "vision_imprimible/api",
                "vision_pyg/api",
                "vision_tarifas/api",
                "pyg/api",
                "panel/api",
                "cadena_a/api",
                "cadena_b/api",
                "cadena_c/api",
            ]
        ]
        allowed_files = {"calculate_dependencies.py"}
        violations = []
        for api_dir in api_dirs:
            if not api_dir.exists():
                continue
            for py_file in api_dir.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue
                if py_file.name in allowed_files:
                    continue
                try:
                    src = py_file.read_text(encoding="utf-8", errors="replace")
                    # Check for module-scope get_provider() call (not inside a def)
                    lines = src.split("\n")
                    for i, line in enumerate(lines, 1):
                        stripped = line.strip()
                        if "get_provider()" in stripped and not stripped.startswith("#"):
                            if not stripped.startswith("def ") and not stripped.startswith("from "):
                                violations.append(f"{py_file.relative_to(BACKEND_ROOT)}:{i}: {stripped[:60]}")
                except Exception:
                    pass
        assert not violations, (
            f"get_provider() called at module scope in router files: {violations}. "
            f"Migrate to Depends(get_results_repository) via db/dependencies.py."
        )

    def test_no_db_providers_import_from_domain_parametrizacion(self):
        """Domain parametrizacion code must not import directly from db.providers.

        Repositories receive DocumentStore by constructor injection.
        Importing db.providers inside domain code creates a hard coupling to the
        concrete provider and breaks testability.

        Allowed exceptions: db/, app.py, container.py, factory.py, dependencies.py.
        """
        parametrizacion_root = BACKEND_ROOT / "modules" / "parametrizacion"
        violations = []
        for py_file in parametrizacion_root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                src = py_file.read_text(encoding="utf-8", errors="replace")
                if "from nexa_engine.db.providers" in src or "import nexa_engine.db.providers" in src:
                    violations.append(str(py_file.relative_to(BACKEND_ROOT)))
            except Exception:
                pass
        assert not violations, (
            f"Domain code in parametrizacion imports from db.providers directly: "
            f"{violations}. Use constructor injection of DocumentStore instead."
        )

    def test_no_new_helper_files_with_zero_consumers(self):
        """Detect any new files added to shared/helpers/ with zero production consumers."""
        helpers_dir = SHARED_ROOT / "helpers"
        known_zero_consumer_exemptions: set[str] = set()
        # After shared-cleanup: certified_helpers.py shim deleted from shared/helpers/.
        # helpers/ should now be empty (no non-__init__ files).
        violations = []
        for helper_file in helpers_dir.glob("*.py"):
            if helper_file.name == "__init__.py":
                continue
            if helper_file.name in known_zero_consumer_exemptions:
                continue
            count = self._get_production_importers(
                f"shared.helpers.{helper_file.stem}"
            )
            if count == 0:
                violations.append(helper_file.name)

        assert not violations, (
            f"New helper files added to shared/helpers/ with 0 production consumers: "
            f"{violations}. Either add a consumer or move to the owning module."
        )


# ---------------------------------------------------------------------------
# 5. shared/ invariant — no business domain imports
# ---------------------------------------------------------------------------

class TestSharedInvariantNoBusinessDomainImports:
    """shared/ must not import from business-domain modules.

    Invariant: shared = técnico, mínimo, transversal, sin negocio.

    Permitted exceptions (explicit adapters, documented):
      - models/visions.py: backward-compat re-exporter for CTS / PyG / tarifas / imprimible.

    Technical cross-cutting modules (lineage, calculator_motor) are NOT in the
    forbidden list — use_cases in shared legitimately depend on them for audit/
    certified-calculation flows.

    Documented in: docs/refactor/shared_models_audit.md (Fase 2 cleanup)
    """

    # Business domain modules that shared/ must never import from.
    # These own specific business capabilities and should only be consumed by
    # application-layer use cases outside shared/, not by shared infrastructure.
    _FORBIDDEN_PREFIXES: frozenset[str] = frozenset({
        "nexa_engine.modules.nomina",
        "nexa_engine.modules.no_payroll",
        "nexa_engine.modules.vision_tarifas",
        "nexa_engine.modules.vision_imprimible",
        "nexa_engine.modules.vision_cost_to_serve",
        "nexa_engine.modules.pyg",
        "nexa_engine.modules.vision_pyg",
        "nexa_engine.modules.panel",
        "nexa_engine.modules.cadena_a",
        "nexa_engine.modules.cadena_b",
        "nexa_engine.modules.cadena_c",
        "nexa_engine.modules.parametrizacion",
    })

    # Files that are explicit adapters and may import from domain modules.
    # After shared-cleanup: panel.py, visions_tarifas.py, visions.py deleted.
    # models/__init__.py is the single-surface re-exporter — inherently aggregates domain exports.
    _ALLOWED_ADAPTER_FILES: frozenset[str] = frozenset({
        "models/__init__.py",  # single-surface re-exporter: aggregates domain model exports
    })

    def test_shared_has_no_business_domain_imports(self) -> None:
        """No shared/ file (except explicit adapters) may import from domain modules."""
        violations: list[str] = []
        for py_file in SHARED_ROOT.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            relative = str(py_file.relative_to(SHARED_ROOT))
            if relative in self._ALLOWED_ADAPTER_FILES:
                continue
            try:
                src = py_file.read_text(encoding="utf-8", errors="replace")
                for prefix in self._FORBIDDEN_PREFIXES:
                    if prefix in src:
                        violations.append(f"{relative}: imports from {prefix}")
                        break
            except Exception:
                pass

        assert not violations, (
            f"shared/ files importing from business domain modules: {violations}. "
            f"Invariant: shared = técnico, mínimo, transversal, sin negocio. "
            f"Move the import to the owning module or introduce an interface in shared/ports/."
        )


# ---------------------------------------------------------------------------
# 6. vision_tarifas/dto/ — single-owner DTOs moved from shared (Fase 2E)
# ---------------------------------------------------------------------------

class TestVisionTarifasDtoCanonical:
    """Ensures single-owner DTOs live in vision_tarifas/dto/ and the shared
    adapter still re-exports them for backward compat.

    Documented in: docs/refactor/shared_models_phase2c_visions_audit.md
    """

    _VT_DTO_ROOT = BACKEND_ROOT / "modules" / "vision_tarifas" / "dto"

    _SINGLE_OWNER_CLASSES: frozenset[str] = frozenset({
        "EscenarioTarifasResumen",
        "ReglasBusiness",
        "DesgloseCadenaTarifas",
        "ImproductiveBreakdown",
        "TimeCascade",
        "ComponenteFijo",
        "MesComision",
        "ComponenteVariable",
        "TarifaXVenta",
        "DesgloseProductoOpex",
        "TarifasEscenario",
        "EscenarioTarifasDetalle",
    })

    def test_vision_tarifas_dto_models_exists(self) -> None:
        """canonical DTOs file must exist at vision_tarifas/dto/models.py."""
        assert (self._VT_DTO_ROOT / "models.py").exists(), (
            "vision_tarifas/dto/models.py missing — single-owner DTOs must live here "
            "(moved from shared/models/visions_tarifas.py in Fase 2E)."
        )

    def test_single_owner_classes_defined_in_dto(self) -> None:
        """All 12 single-owner classes must be defined in vision_tarifas/dto/models.py."""
        src = (self._VT_DTO_ROOT / "models.py").read_text()
        missing = [cls for cls in self._SINGLE_OWNER_CLASSES if f"class {cls}" not in src]
        assert not missing, (
            f"Classes missing from vision_tarifas/dto/models.py: {missing}. "
            f"Do not move them back to shared/models/visions_tarifas.py."
        )

    def test_shared_visions_tarifas_shim_no_longer_exists(self) -> None:
        """shared/models/visions_tarifas.py must NOT exist after shared-cleanup.

        The shim was removed; consumers must import directly from:
          - vision_tarifas/models/visions_tarifas.py (TarifaCanal, CriterioRiesgo, etc.)
          - vision_tarifas/dto/models.py (EscenarioTarifasResumen, etc.)
        """
        shim = SHARED_ROOT / "models" / "visions_tarifas.py"
        assert not shim.exists(), (
            "shared/models/visions_tarifas.py was recreated. "
            "Shim was deleted in shared-cleanup pass. "
            "Direct imports must use vision_tarifas/models/ or vision_tarifas/dto/."
        )

    def test_resultado_vision_tarifas_not_in_dto(self) -> None:
        """ResultadoVisionTarifas is cross-cutting and must NOT be in vision_tarifas/dto/models.py."""
        src = (self._VT_DTO_ROOT / "models.py").read_text()
        assert "class ResultadoVisionTarifas" not in src, (
            "ResultadoVisionTarifas was moved to vision_tarifas/dto/models.py. "
            "It is a cross-cutting stability contract and must remain in "
            "vision_tarifas/models/visions_tarifas.py (canonical) or shared/models/visions_tarifas.py (adapter)."
        )


# ---------------------------------------------------------------------------
# 7. CriterioRiesgo — DEFER (circular import blocker, Fase 2F)
# ---------------------------------------------------------------------------

class TestCriterioRiesgoCanonical:
    """CriterioRiesgo canonical location is vision_tarifas/models/visions_tarifas.py.

    After ownership inversion (2026-06-10):
      canonical: modules/vision_tarifas/models/visions_tarifas.py
      adapter:   modules/shared/models/visions_tarifas.py (re-exports for legacy consumers)

    WHY IT CANNOT MOVE TO calculator_motor/formulas/risk/models.py:
      The import chain would be:
        calculator_motor/formulas/risk/__init__.py → riesgo.py → shared.models
        → shared.models.visions_tarifas (adapter) → vision_tarifas.models.visions_tarifas
        → vision_tarifas.dto.models
      This is NOT a cycle (no backedge to risk/).
      The blocker was specifically moving it INSIDE calculator_motor/formulas/risk/
      which would cause: risk/__init__.py → riesgo.py → shared.models → risk/ (cycle).

    Documented: Fase 2F audit (2026-06-10), Ownership inversion (2026-06-10).
    """

    def test_criterio_riesgo_in_vision_tarifas_canonical(self) -> None:
        """CriterioRiesgo must be defined in vision_tarifas/models/visions_tarifas.py."""
        canonical = BACKEND_ROOT / "modules" / "vision_tarifas" / "models" / "visions_tarifas.py"
        assert canonical.exists(), "vision_tarifas/models/visions_tarifas.py must exist"
        src = canonical.read_text()
        assert "class CriterioRiesgo" in src, (
            "CriterioRiesgo was removed from vision_tarifas/models/visions_tarifas.py. "
            "Do not move it to calculator_motor/formulas/risk/ — that would create a cycle. "
            "See TestCriterioRiesgoCanonical docstring for context."
        )

    def test_criterio_riesgo_not_in_calculator_motor_risk(self) -> None:
        """CriterioRiesgo must not be defined inside calculator_motor/formulas/risk/."""
        risk_dir = BACKEND_ROOT / "modules" / "calculator_motor" / "formulas" / "risk"
        for py_file in risk_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or py_file.name == "riesgo.py":
                continue
            src = py_file.read_text(encoding="utf-8", errors="replace")
            assert "class CriterioRiesgo" not in src, (
                f"CriterioRiesgo defined in {py_file.relative_to(BACKEND_ROOT)}. "
                f"Canonical: vision_tarifas/models/visions_tarifas.py. "
                f"Duplicate here causes identity mismatch (isinstance checks fail)."
            )


# ---------------------------------------------------------------------------
# 8. Ownership inversion (2026-06-10) — canonical locations
# ---------------------------------------------------------------------------

class TestOwnershipInversionCanonical:
    """Verifies the inverted ownership: domain modules are now canonical,
    shared/models/ files are backward-compat adapters.

    Invariant: the real class definitions live in the domain owners.
    shared/models/ must NOT contain 'class' definitions for these symbols.
    """

    def test_vision_tarifas_classes_defined_in_domain(self) -> None:
        """TarifaCanal etc. must be defined in vision_tarifas/models/visions_tarifas.py."""
        canonical = BACKEND_ROOT / "modules" / "vision_tarifas" / "models" / "visions_tarifas.py"
        assert canonical.exists(), "vision_tarifas/models/visions_tarifas.py must exist"
        src = canonical.read_text()
        for cls in ("TarifaCanal", "ResultadoVisionTarifas", "ReglaNegocios",
                    "WaterfallPromedio", "CriterioRiesgo", "EvaluacionRiesgo"):
            assert f"class {cls}" in src, (
                f"{cls} must be defined in vision_tarifas/models/visions_tarifas.py (canonical). "
                f"Do not move class definitions back to shared/models/visions_tarifas.py."
            )

    def test_shared_visions_tarifas_shim_deleted(self) -> None:
        """shared/models/visions_tarifas.py must NOT exist after shared-cleanup.

        Canonical: vision_tarifas/models/visions_tarifas.py
        Removed in: shared-cleanup pass (residual shims elimination).
        """
        shim = SHARED_ROOT / "models" / "visions_tarifas.py"
        assert not shim.exists(), (
            "shared/models/visions_tarifas.py still exists. "
            "It was deleted in the shared-cleanup pass. "
            "Canonical: modules/vision_tarifas/models/visions_tarifas.py."
        )

    def test_panel_classes_defined_in_domain(self) -> None:
        """PanelDeControl etc. must be defined in panel/models/panel.py."""
        canonical = BACKEND_ROOT / "modules" / "panel" / "models" / "panel.py"
        assert canonical.exists(), "panel/models/panel.py must exist"
        src = canonical.read_text()
        for cls in ("PanelDeControl", "PricingRequest", "PerfilCadenaA",
                    "PolizaContractual", "EscenarioComercial"):
            assert f"class {cls}" in src, (
                f"{cls} must be defined in panel/models/panel.py (canonical). "
                f"Do not move class definitions back to shared/models/panel.py."
            )

    def test_shared_panel_shim_deleted(self) -> None:
        """shared/models/panel.py must NOT exist after shared-cleanup.

        Canonical: panel/models/panel.py
        Removed in: shared-cleanup pass (residual shims elimination).
        """
        shim = SHARED_ROOT / "models" / "panel.py"
        assert not shim.exists(), (
            "shared/models/panel.py still exists. "
            "It was deleted in the shared-cleanup pass. "
            "Canonical: modules/panel/models/panel.py."
        )

    def test_results_classes_defined_in_domain(self) -> None:
        """PricingResult etc. must be defined in calculator_motor/models/results.py."""
        canonical = BACKEND_ROOT / "modules" / "calculator_motor" / "models" / "results.py"
        assert canonical.exists(), "calculator_motor/models/results.py must exist"
        src = canonical.read_text()
        for cls in ("PricingResult", "PyGMensual", "KPIsDeal",
                    "ResultadoNomina", "CostosTotalesMes"):
            assert f"class {cls}" in src, (
                f"{cls} must be defined in calculator_motor/models/results.py (canonical). "
                f"Do not move class definitions back to shared/models/results.py."
            )

    def test_shared_results_is_adapter_not_source(self) -> None:
        """shared/models/results.py must be an adapter (no class definitions)."""
        adapter = SHARED_ROOT / "models" / "results.py"
        src = adapter.read_text()
        for cls in ("PricingResult", "PyGMensual", "KPIsDeal"):
            assert f"class {cls}" not in src, (
                f"shared/models/results.py defines '{cls}' — it must be an adapter only. "
                f"Canonical: calculator_motor/models/results.py."
            )


# ---------------------------------------------------------------------------
# 9. Shared-cleanup shims deleted (added after residual shims elimination)
# ---------------------------------------------------------------------------

class TestResidualShimsDeleted:
    """Verifies all residual backward-compat shims were deleted from shared/.

    Added in the shared-cleanup pass (2026-06-10). Each test is a ratchet:
    once a shim is removed, it must never be recreated.
    """

    def test_shared_models_panel_shim_gone(self) -> None:
        """shared/models/panel.py deleted — canonical: panel/models/panel.py."""
        assert not (SHARED_ROOT / "models" / "panel.py").exists(), (
            "shared/models/panel.py was recreated. Canonical: panel/models/panel.py."
        )

    def test_shared_models_visions_tarifas_shim_gone(self) -> None:
        """shared/models/visions_tarifas.py deleted — canonical: vision_tarifas/models/."""
        assert not (SHARED_ROOT / "models" / "visions_tarifas.py").exists(), (
            "shared/models/visions_tarifas.py was recreated. "
            "Canonical: vision_tarifas/models/visions_tarifas.py."
        )

    def test_shared_models_visions_shim_gone(self) -> None:
        """shared/models/visions.py deleted — consumers use canonical domain paths."""
        assert not (SHARED_ROOT / "models" / "visions.py").exists(), (
            "shared/models/visions.py was recreated. "
            "Use vision_cost_to_serve/dto/models.py, vision_pyg/models/, "
            "vision_tarifas/models/, vision_imprimible/models/ directly."
        )

    def test_shared_use_cases_audit_simulation_shim_gone(self) -> None:
        """shared/use_cases/audit_simulation.py deleted — canonical: audit/use_cases/."""
        assert not (SHARED_ROOT / "use_cases" / "audit_simulation.py").exists(), (
            "shared/use_cases/audit_simulation.py was recreated. "
            "Canonical: modules/audit/use_cases/audit_simulation.py."
        )

    def test_shared_use_cases_certified_calculation_shim_gone(self) -> None:
        """shared/use_cases/certified_calculation.py deleted — canonical: calculator/use_cases/."""
        assert not (SHARED_ROOT / "use_cases" / "certified_calculation.py").exists(), (
            "shared/use_cases/certified_calculation.py was recreated. "
            "Canonical: modules/calculator/use_cases/certified_calculation.py."
        )

    def test_shared_helpers_certified_helpers_shim_gone(self) -> None:
        """shared/helpers/certified_helpers.py deleted — canonical: calculator/use_cases/."""
        assert not (SHARED_ROOT / "helpers" / "certified_helpers.py").exists(), (
            "shared/helpers/certified_helpers.py was recreated. "
            "Canonical: modules/calculator/use_cases/certified_helpers.py."
        )

    def test_shared_infrastructure_app_settings_shim_gone(self) -> None:
        """shared/infrastructure/app_settings.py deleted — canonical: shared/config/."""
        assert not (SHARED_ROOT / "infrastructure" / "app_settings.py").exists(), (
            "shared/infrastructure/app_settings.py was recreated. "
            "Canonical: modules/shared/config/app_settings.py."
        )

    def test_shared_infrastructure_business_rules_loader_shim_gone(self) -> None:
        """shared/infrastructure/business_rules_loader.py deleted — canonical: config/business_rules/loader."""
        assert not (SHARED_ROOT / "infrastructure" / "business_rules_loader.py").exists(), (
            "shared/infrastructure/business_rules_loader.py was recreated. "
            "Canonical: modules/shared/config/business_rules/loader.py."
        )

    def test_shared_infrastructure_config_shim_gone(self) -> None:
        """shared/infrastructure/config.py deleted — canonical: shared/config/config.py."""
        assert not (SHARED_ROOT / "infrastructure" / "config.py").exists(), (
            "shared/infrastructure/config.py was recreated. "
            "Canonical: modules/shared/config/config.py."
        )

    def test_shared_infrastructure_middlewares_shim_gone(self) -> None:
        """shared/infrastructure/middlewares.py deleted — canonical: shared/middleware/."""
        assert not (SHARED_ROOT / "infrastructure" / "middlewares.py").exists(), (
            "shared/infrastructure/middlewares.py was recreated. "
            "Canonical: modules/shared/middleware/middlewares.py."
        )

    def test_shared_certification_dir_gone(self) -> None:
        """shared/certification/ deleted — canonical: modules/certification/."""
        assert not (SHARED_ROOT / "certification").exists(), (
            "shared/certification/ was recreated. "
            "Canonical: modules/certification/."
        )

    def test_shared_persistence_dir_gone(self) -> None:
        """shared/persistence/ deleted — canonical: modules/calculator/persistence/."""
        assert not (SHARED_ROOT / "persistence").exists(), (
            "shared/persistence/ was recreated. "
            "Canonical: modules/calculator/persistence/."
        )
