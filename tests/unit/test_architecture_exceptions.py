"""Guardrails for documented architectural exceptions.

These tests fail if someone attempts an unsafe refactoring of the files
listed in docs/refactor/architecture_exceptions.md without going through
a dedicated phase (ORACLE-FIN, FROZEN-1, etc.).

Each test verifies:
1. The file still exists where expected.
2. The documented pattern is still in place.
3. No forbidden change was applied silently.

DO NOT delete or weaken these tests.  They are the only automated protection
against reintroducing architectural problems that were deliberately accepted.
See docs/refactor/architecture_exceptions.md for the full rationale.
"""

from __future__ import annotations

from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MODULES = BACKEND_ROOT / "modules"
DOCS = BACKEND_ROOT / "docs" / "refactor"


# ---------------------------------------------------------------------------
# 1. costos_financieros/reglas.py — POSTPONE_ORACLE_SENSITIVE
# ---------------------------------------------------------------------------

class TestCostosFinancierosException:
    """costos_financieros/reglas.py must NOT be moved without a dedicated Oracle phase."""

    def test_reglas_no_longer_at_root(self):
        """File was moved to calculators/ in ORACLE-FIN and shim removed in ORACLE-FIN-2.

        The canonical location is now:
          modules/costos_financieros/calculators/costos_financieros_calculator.py

        If reglas.py reappears at root, it must only be a re-export shim.
        """
        legacy = MODULES / "costos_financieros" / "reglas.py"
        if legacy.exists():
            # If it exists, verify it's only a shim (no class definition)
            src = legacy.read_text()
            assert "class CostosFinancierosCalculator" not in src, (
                "costos_financieros/reglas.py contains a full implementation. "
                "The canonical location is calculators/costos_financieros_calculator.py. "
                "reglas.py may only re-export for backward compat."
            )

    def test_costos_financieros_calculator_class_in_canonical_location(self):
        """CostosFinancierosCalculator must live in the canonical location.

        After ORACLE-FIN and calculator_motor refactor, it lives in:
          modules/calculator_motor/formulas/costos_financieros/calculator.py
        """
        canonical = MODULES / "calculator_motor" / "formulas" / "costos_financieros" / "calculator.py"
        legacy = MODULES / "costos_financieros" / "calculators" / "costos_financieros_calculator.py"
        assert canonical.exists(), (
            "calculator_motor/formulas/costos_financieros/calculator.py was removed. "
            "This is the canonical location for CostosFinancierosCalculator."
        )
        assert not legacy.exists(), (
            "costos_financieros/calculators/costos_financieros_calculator.py must not be recreated. "
            "Canonical location is calculator_motor/formulas/costos_financieros/calculator.py."
        )
        src = canonical.read_text()
        assert "class CostosFinancierosCalculator" in src, (
            "CostosFinancierosCalculator class was removed from its canonical file. "
            "This class contains financial formulas. Do not delete without Oracle verification."
        )

    def test_reglas_py_does_not_exist(self):
        """costos_financieros/reglas.py must NOT exist after ORACLE-FIN-2.

        The shim was removed once all consumers were repoinsted to the canonical
        import path:
          from nexa_engine.modules.calculator_motor.formulas.costos_financieros import CostosFinancierosCalculator

        If this file reappears, it must only be as a re-export shim (not an
        implementation), and only if a new consumer requires backward compat.
        """
        legacy = MODULES / "costos_financieros" / "reglas.py"
        if legacy.exists():
            src = legacy.read_text()
            # If it exists, it must be a shim, not an implementation
            assert "class CostosFinancierosCalculator" not in src, (
                "costos_financieros/reglas.py was reintroduced with a full implementation. "
                "The canonical location is calculators/costos_financieros_calculator.py. "
                "If reglas.py is needed for backward compat, it must only re-export."
            )

    def test_public_api_importable_from_package(self):
        """CostosFinancierosCalculator must be importable from calculator_motor.

        After ORACLE-FIN-2, the canonical import is:
          from nexa_engine.modules.calculator_motor.formulas.costos_financieros import CostosFinancierosCalculator
        """
        init_src = (MODULES / "calculator_motor" / "formulas" / "costos_financieros" / "__init__.py").read_text()
        assert "CostosFinancierosCalculator" in init_src, (
            "calculator_motor/formulas/costos_financieros/__init__.py does not export "
            "CostosFinancierosCalculator. The public API must be accessible from the package root."
        )
        legacy_init = MODULES / "costos_financieros" / "__init__.py"
        assert not legacy_init.exists(), (
            "costos_financieros/__init__.py was recreated. "
            "Canonical location is calculator_motor/formulas/costos_financieros."
        )

    def test_no_unauthorized_costos_dirs(self):
        """Only 'calculators' and 'financial' are authorized subdirs in costos_financieros.

        Other directories ('services', 'models', 'constants') require a new Oracle phase.
        """
        authorized_dirs = {"calculators", "financial"}
        for d in MODULES.glob("costos_financieros/*/"):
            if d.is_dir() and not d.name.startswith("__"):
                assert d.name in authorized_dirs, (
                    f"Unauthorized directory created: costos_financieros/{d.name}/. "
                    f"Only {authorized_dirs} are authorized. "
                    f"Adding new subdirs requires a new Oracle verification phase."
                )


# ---------------------------------------------------------------------------
# 2. frozen_parametrization_repository.py — KEEP_LEGACY_READ_ONLY_WITH_REASON
# ---------------------------------------------------------------------------

class TestFrozenParametrizationException:
    """frozen_parametrization_repository.py must not be migrated to DocumentStore
    without a dedicated FROZEN-1 phase and hash verification."""

    def test_frozen_repo_still_exists_at_original_path(self):
        """File must remain at its current location."""
        p = MODULES / "parametrizacion" / "repositories" / "frozen_parametrization_repository.py"
        assert p.exists(), (
            "frozen_parametrization_repository.py was removed or moved. "
            "This is a certified immutable snapshot repository. "
            "Create phase FROZEN-1 before changing its location or format."
        )

    def test_frozen_repo_still_uses_open_not_document_store(self):
        """File must still use open() — migration to DocumentStore is FROZEN-1 scope."""
        src = (MODULES / "parametrizacion" / "repositories" / "frozen_parametrization_repository.py").read_text()
        assert "open(" in src, (
            "frozen_parametrization_repository.py no longer uses open(). "
            "If it was migrated to DocumentStore without a FROZEN-1 phase, "
            "verify that hash parity of certified snapshots is preserved."
        )
        assert "class FrozenParametrizationRepository" in src, (
            "FrozenParametrizationRepository class was removed. "
            "Its consumers (frozen_parametrization_adapter.py) would break."
        )

    def test_frozen_repo_does_not_import_document_store(self):
        """frozen_parametrization_repository must NOT import DocumentStore.

        If it does, the migration happened without going through FROZEN-1.
        """
        src = (MODULES / "parametrizacion" / "repositories" / "frozen_parametrization_repository.py").read_text()
        assert "DocumentStore" not in src, (
            "frozen_parametrization_repository.py now imports DocumentStore. "
            "This migration must be validated in phase FROZEN-1 with hash verification."
        )


# ---------------------------------------------------------------------------
# 3. resolver.py — KEEP_WITH_REASON (fallback for get_resolver singleton)
# ---------------------------------------------------------------------------

class TestResolverFallbackException:
    """resolver.py fallback must not be removed without updating get_resolver()."""

    def test_resolver_file_exists(self):
        p = MODULES / "parametrizacion" / "services" / "resolver.py"
        assert p.exists(), "parametrizacion/services/resolver.py was removed."

    def test_resolver_has_get_parametrization_store_fallback(self):
        """The fallback in __init__ serves get_resolver() singleton.

        If this fallback is removed, get_resolver() must be updated simultaneously
        to pass all three repos explicitly.  Removing it without updating
        get_resolver() breaks the singleton.
        """
        src = (MODULES / "parametrizacion" / "services" / "resolver.py").read_text()
        # Check that the singleton still exists
        assert "def get_resolver" in src, (
            "get_resolver() was removed from resolver.py. "
            "If intentional, also remove the KEEP_WITH_REASON exception from "
            "docs/refactor/architecture_exceptions.md."
        )
        # Check that either the fallback or get_resolver no longer calls get_parametrization_store
        # (acceptable only if get_resolver was also refactored)
        has_fallback = "get_parametrization_store" in src
        has_explicit_repos = "def get_resolver(" in src and "ParametrizationResolver()" not in src
        # Either the fallback exists (current state) or get_resolver was fixed
        assert has_fallback or has_explicit_repos, (
            "resolver.py fallback was removed but get_resolver() still calls "
            "ParametrizationResolver() without repos.  This breaks the singleton. "
            "Either restore the fallback or update get_resolver() to pass repos explicitly."
        )


# ---------------------------------------------------------------------------
# 4. provider_business_rules.py — KEEP_TEMPORARILY_WITH_REASON (with warning)
# ---------------------------------------------------------------------------

class TestProviderBusinessRulesException:
    """provider_business_rules.py fallback must keep the logger.warning for auditability."""

    def test_file_exists(self):
        p = MODULES / "parametrizacion" / "mixins" / "provider_business_rules.py"
        assert p.exists(), "provider_business_rules.py was removed."

    def test_fallback_has_warning_log(self):
        """The fallback must emit a warning so production activations are visible.

        If the warning is removed, the fallback becomes invisible.
        If the fallback is removed entirely, update this test to confirm
        that _br_repo injection is now mandatory everywhere.
        """
        src = (MODULES / "parametrizacion" / "mixins" / "provider_business_rules.py").read_text()
        fallback_removed = "get_parametrization_store" not in src
        if fallback_removed:
            pytest.skip(
                "provider_business_rules.py fallback was removed — "
                "KEEP_TEMPORARILY exception resolved.  Update architecture_exceptions.md."
            )
        # Fallback still present — must have warning
        assert "logger.warning" in src, (
            "provider_business_rules.py fallback no longer emits logger.warning. "
            "The warning is required to detect production activations of the fallback. "
            "See docs/refactor/architecture_exceptions.md."
        )


# ---------------------------------------------------------------------------
# 5. panel_service.py — build_panel_parametros must NOT reappear
# ---------------------------------------------------------------------------

class TestPanelServiceException:
    """build_panel_parametros() was deleted as dead code in GAP-1.
    It must not be reintroduced."""

    def test_build_panel_parametros_not_in_panel_service(self):
        """Dead code function must not be recreated."""
        src = (MODULES / "panel" / "services" / "panel_service.py").read_text()
        assert "def build_panel_parametros" not in src, (
            "build_panel_parametros() was reintroduced in panel_service.py. "
            "This function was deleted in GAP-1 because it had 0 runtime consumers. "
            "Use PanelService with DI instead."
        )

    def test_panel_service_has_no_factory_calls(self):
        """PanelService class itself must not call get_parametrization_store()."""
        src = (MODULES / "panel" / "services" / "panel_service.py").read_text()
        # The function build_panel_parametros was the only place calling this
        assert "get_parametrization_store" not in src, (
            "panel_service.py calls get_parametrization_store() directly. "
            "PanelService should receive repositories by constructor injection. "
            "Check if build_panel_parametros() was reintroduced."
        )

    def test_panel_router_uses_depends(self):
        """Panel router must use Depends — not build repos inline."""
        src = (MODULES / "panel" / "api" / "panel_router.py").read_text()
        assert "Depends(" in src, (
            "panel_router.py no longer uses Depends(). "
            "Panel service must be injected via FastAPI dependency injection."
        )
        assert "get_parametrization_store" not in src, (
            "panel_router.py calls get_parametrization_store() directly. "
            "Routers must not build stores — use Depends(get_panel_service)."
        )


# ---------------------------------------------------------------------------
# 6. calculator root taxonomy shims - RE-EXPORT_TEMPORARY
# ---------------------------------------------------------------------------

class TestCalculatorTaxonomyShims:
    """calculator_motor constants and serializers must remain in canonical locations."""

    def test_constants_package_in_calculator_motor(self):
        """Constants live in calculator_motor/constants/, not legacy calculator/constants/."""
        package_init = MODULES / "calculator_motor" / "constants" / "__init__.py"
        canonical = MODULES / "calculator_motor" / "constants" / "global_constants.py"
        legacy_init = MODULES / "calculator" / "constants" / "__init__.py"

        assert package_init.exists(), (
            "calculator_motor/constants/__init__.py was removed. "
            "Constants must live under calculator_motor/constants/."
        )
        assert canonical.exists(), (
            "calculator_motor/constants/global_constants.py was removed. "
            "Calculator constants must live under calculator_motor/constants/."
        )
        assert not legacy_init.exists(), (
            "Legacy calculator/constants/ was recreated. "
            "Constants now live in calculator_motor/constants/."
        )

        src = package_init.read_text()
        assert "global_constants import" in src
        assert "MES_INICIO_AJUSTE_ANUAL" in src
        assert "DIAS_LABORALES_POR_MES" not in src
        assert "HORAS_LABORALES_POR_DIA" not in src
        assert "SEMANAS_POR_MES" not in src

    def test_serializer_in_calculator_motor(self):
        """Serializer lives in calculator_motor/serializers/, not legacy calculator/serializers/."""
        canonical = MODULES / "calculator_motor" / "serializers" / "pricing_result_serializer.py"
        legacy_canonical = MODULES / "calculator" / "serializers" / "pricing_result_serializer.py"

        assert canonical.exists(), (
            "calculator_motor/serializers/pricing_result_serializer.py was removed. "
            "Pricing serialization must live under calculator_motor/serializers/."
        )
        assert not legacy_canonical.exists(), (
            "Legacy calculator/serializers/pricing_result_serializer.py was recreated. "
            "Canonical location is calculator_motor/serializers/."
        )
        serializer_root = MODULES / "calculator_motor" / "serializers" / "serializer_helpers.py"
        assert serializer_root.exists(), (
            "calculator_motor/serializers/serializer_helpers.py was removed. "
            "Serializer helpers must live under calculator_motor/serializers/."
        )


# ---------------------------------------------------------------------------
# 7. Empty package markers must not be reintroduced
# ---------------------------------------------------------------------------

class TestNoEmptyTaxonomyPackageMarkers:
    """Previously empty taxonomy packages must only return with real content."""

    EMPTY_PACKAGE_MARKERS = [
        MODULES / "parametrizacion" / "gn" / "constants" / "__init__.py",
        MODULES / "parametrizacion" / "gn" / "enums" / "__init__.py",
        MODULES / "parametrizacion" / "gn" / "helpers" / "__init__.py",
        MODULES / "parametrizacion" / "hr" / "constants" / "__init__.py",
        MODULES / "parametrizacion" / "hr" / "enums" / "__init__.py",
        MODULES / "parametrizacion" / "hr" / "helpers" / "__init__.py",
        MODULES / "parametrizacion" / "op" / "constants" / "__init__.py",
        MODULES / "parametrizacion" / "op" / "enums" / "__init__.py",
        MODULES / "parametrizacion" / "op" / "helpers" / "__init__.py",
        MODULES / "pyg" / "use_cases" / "__init__.py",
        MODULES / "shared" / "services" / "__init__.py",
        MODULES / "shared" / "validation" / "__init__.py",
        MODULES / "vision_tarifas" / "builders" / "__init__.py",
        MODULES / "vision_tarifas" / "services" / "__init__.py",
    ]

    def test_deleted_empty_package_markers_stay_deleted_until_real_content_exists(self):
        violations = []
        for marker in self.EMPTY_PACKAGE_MARKERS:
            package_dir = marker.parent
            if not marker.exists():
                continue
            real_files = [
                p
                for p in package_dir.rglob("*.py")
                if p.name != "__init__.py" and "__pycache__" not in p.parts
            ]
            if not real_files:
                violations.append(str(marker.relative_to(BACKEND_ROOT)))

        assert violations == [], (
            "Empty taxonomy package markers were reintroduced without real content: "
            f"{violations}. Add a real module or leave the directory absent."
        )


# ---------------------------------------------------------------------------
# 8. Architecture exceptions document must exist and reference all files
# ---------------------------------------------------------------------------

class TestExceptionsDocumentIntegrity:
    """The exceptions document must exist and reference all four exceptions."""

    def test_document_exists(self):
        p = DOCS / "architecture_exceptions.md"
        assert p.exists(), (
            "docs/refactor/architecture_exceptions.md was deleted. "
            "This document records architectural decisions that protect "
            "Oracle-sensitive and certified-data files from unsafe refactoring."
        )

    def test_document_references_all_exceptions(self):
        """Every documented exception must be referenced in the document."""
        src = (DOCS / "architecture_exceptions.md").read_text()
        expected_refs = [
            "costos_financieros",
            "frozen_parametrization_repository",
            "resolver.py",
            "provider_business_rules",
        ]
        missing = [ref for ref in expected_refs if ref not in src]
        assert not missing, (
            f"architecture_exceptions.md is missing references to: {missing}. "
            f"Update the document when adding or removing exceptions."
        )
