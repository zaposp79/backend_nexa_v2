"""
Structural guardrails for calculator shared taxonomy after final shim deletion.

Ratchet tests — fail if the refactor regresses:
  G-S1: modules/calculator_motor/shared/ must stay deleted after compatibility cleanup.
  G-S2: PricingCalculator is importable from calculator_motor.formulas.pricing.
  G-S3: no productive source should import calculator_motor.shared anymore.
  G-S4: No productive source imports PricingCalculator from pricing.calculators or shared.pricing.
  G-S5: canonical PricingCalculator methods produce identical results to pre-migration values.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).parent.parent.parent
_LEGACY_SHARED_MODULE = _BACKEND_ROOT / "modules" / "calculator" / "shared"
_OLD_PRICING = _BACKEND_ROOT / "modules" / "calculator" / "pricing" / "calculators.py"
_REMOVED_SHARED_MODULE = _BACKEND_ROOT / "modules" / "calculator_motor" / "shared"


class TestCalculatorSharedStructure:
    """G-S1: modules/calculator_motor/shared/ must remain deleted."""

    def test_g_s1_shared_directory_exists(self):
        assert not _REMOVED_SHARED_MODULE.exists(), (
            f"G-S1: {_REMOVED_SHARED_MODULE} should remain deleted."
        )
        assert not _LEGACY_SHARED_MODULE.exists(), (
            "G-S1: Legacy modules/calculator_motor/shared must not be recreated"
        )

    def test_g_s1_pricing_py_shim_deleted(self):
        assert not (_REMOVED_SHARED_MODULE / "pricing.py").exists()

    def test_g_s1_init_py_exists(self):
        assert not (_REMOVED_SHARED_MODULE / "__init__.py").exists()


class TestPricingCalculatorLocation:
    """G-S2: PricingCalculator must be importable from calculator_motor.formulas.pricing."""

    def test_g_s2_pricing_calculator_importable_from_canonical_package(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator  # noqa: F401

        assert PricingCalculator is not None

    def test_g_s2_pricing_calculator_module_path(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator

        assert "calculator_motor.formulas.pricing" in PricingCalculator.__module__, (
            f"G-S2: Expected PricingCalculator canonical path in calculator_motor.formulas.pricing, got: {PricingCalculator.__module__}"
        )

    def test_g_s2_pricing_calculator_has_required_methods(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator

        assert hasattr(PricingCalculator, "calcular_ingreso_bruto")
        assert hasattr(PricingCalculator, "calcular_tarifa_unitaria")
        assert hasattr(PricingCalculator, "calcular_factor_billing")
        assert hasattr(PricingCalculator, "derivar_componentes_label")


class TestSharedBoundaries:
    """G-S3: no productive source should keep calculator_motor.shared imports."""

    def test_g_s3_no_productive_imports_from_removed_shared_package(self):
        offenders: list[str] = []
        for source_file in _BACKEND_ROOT.rglob("*.py"):
            if "__pycache__" in source_file.parts:
                continue
            if source_file.name == "test_calculator_shared_structure.py":
                continue
            try:
                tree = ast.parse(source_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "calculator_motor.shared" in node.module:
                        offenders.append(str(source_file.relative_to(_BACKEND_ROOT)))
                        break
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if "calculator_motor.shared" in alias.name:
                            offenders.append(str(source_file.relative_to(_BACKEND_ROOT)))
                            break

        assert not offenders, (
            "G-S3: Files still importing removed calculator_motor.shared package:\n"
            + "\n".join(f"  {o}" for o in offenders)
        )


class TestNoDirectPricingCalculatorsImports:
    """G-S4: Productive source files must not import PricingCalculator from pricing.calculators."""

    _ALLOWED_FILES = frozenset(
        [
            # The shim itself is the only file allowed to reference the old path.
            "calculators.py",
            # Guardrail test files are allowed to reference it in strings/comments.
            "test_calculator_shared_structure.py",
        ]
    )

    def test_g_s4_no_productive_imports_from_pricing_calculators(self):
        offenders: list[str] = []
        for source_file in _BACKEND_ROOT.rglob("*.py"):
            if "__pycache__" in source_file.parts:
                continue
            if source_file.name in self._ALLOWED_FILES:
                continue
            try:
                tree = ast.parse(source_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "calculator.pricing.calculators" in node.module:
                        offenders.append(str(source_file.relative_to(_BACKEND_ROOT)))
                        break
                    if "calculator.shared.pricing" in node.module:
                        offenders.append(str(source_file.relative_to(_BACKEND_ROOT)))
                        break

        assert not offenders, (
            "G-S4: Files importing PricingCalculator from old path (calculator.pricing.calculators/shared.pricing):\n"
            + "\n".join(f"  {f}" for f in offenders)
            + "\nUpdate to: from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator"
        )


class TestPricingCalculatorNumerics:
    """G-S5: PricingCalculator produces the same results as expected."""

    def test_g_s5_calcular_ingreso_bruto_basic(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator

        assert PricingCalculator.calcular_ingreso_bruto(100.0, 0.5) == pytest.approx(200.0)
        assert PricingCalculator.calcular_ingreso_bruto(100.0, 0.0) == 0.0
        assert PricingCalculator.calcular_ingreso_bruto(100.0, -1.0) == 0.0

    def test_g_s5_calcular_tarifa_unitaria_basic(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator

        assert PricingCalculator.calcular_tarifa_unitaria(1000.0, 10.0) == pytest.approx(100.0)
        assert PricingCalculator.calcular_tarifa_unitaria(1000.0, 0.0) == 0.0
        assert PricingCalculator.calcular_tarifa_unitaria(1000.0, -5.0) == 0.0

    def test_g_s5_derivar_componentes_label_fijo_fte(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator

        assert PricingCalculator.derivar_componentes_label("Fijo FTE", 1.0) == ("FTE", "")

    def test_g_s5_derivar_componentes_label_variable(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator

        assert PricingCalculator.derivar_componentes_label("Variable", 0.0) == ("", "Transacción")

    def test_g_s5_derivar_componentes_label_hibrido(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator

        assert PricingCalculator.derivar_componentes_label("Híbrido", 0.6) == ("FTE", "Transacción")

    def test_g_s5_derivar_componentes_label_fallback(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator

        assert PricingCalculator.derivar_componentes_label("desconocido", 1.0) == ("FTE", "")
        assert PricingCalculator.derivar_componentes_label("desconocido", 0.5) == ("FTE", "Transacción")
        assert PricingCalculator.derivar_componentes_label("desconocido", 0.0) == ("", "Transacción")
