"""
Structural guardrails for PHASE 5B: PricingCalculator move to formulas/pricing.

Validates:
  G-5B1: modules/calculator_motor/formulas/pricing/pricing.py exists.
  G-5B2: PricingCalculator importable from canonical formulas.pricing path.
  G-5B3: formulas/pricing does not import heavy IO (FastAPI, routers, DocumentStore, Cosmos).
  G-5B4: calculator_motor/shared compatibility package is removed after cleanup.
  G-5B5: canonical imports stay available from calculator_motor.formulas.pricing.
  G-5B6: numeric parity — methods produce identical results.
  G-5B7: no productive imports from old paths (calculator.pricing.calculators).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).parent.parent.parent
_FORMULAS_PRICING = _BACKEND_ROOT / "modules" / "calculator_motor" / "formulas" / "pricing"
_CANONICAL_PRICING = _FORMULAS_PRICING / "pricing.py"
_LEGACY_PRICING_SHARED = _BACKEND_ROOT / "modules" / "calculator" / "shared" / "pricing.py"
_LEGACY_FORMULAS_PRICING = _BACKEND_ROOT / "modules" / "calculator" / "formulas" / "pricing"
_OLD_PRICING_CALCULATORS = _BACKEND_ROOT / "modules" / "calculator" / "pricing" / "calculators.py"
_LEGACY_ENGINE_PY = _BACKEND_ROOT / "modules" / "calculator" / "engine.py"
_ENGINE_PY = _BACKEND_ROOT / "modules" / "calculator_motor" / "engine.py"

_HEAVY_IO_FORBIDDEN = frozenset([
    "fastapi", "starlette", "DocumentStore", "cosmos", "azure",
    "JsonDocumentStore", "json_provider", "router", "requests", "httpx",
])


class TestPricingCalculatorStructure:
    """G-5B1: formulas/pricing/pricing.py exists in canonical location."""

    def test_g_5b1_canonical_pricing_py_exists(self):
        assert _CANONICAL_PRICING.exists(), (
            "G-5B1: modules/calculator_motor/formulas/pricing/pricing.py not found."
        )
        assert not _LEGACY_FORMULAS_PRICING.exists(), (
            "G-5B1: Legacy modules/calculator_motor/formulas/pricing must not be recreated"
        )

    def test_g_5b1_formulas_pricing_init_exports(self):
        init_content = (_FORMULAS_PRICING / "__init__.py").read_text(encoding="utf-8")
        assert "PricingCalculator" in init_content, (
            "G-5B1: __init__.py does not export PricingCalculator."
        )


class TestPricingCalculatorImportability:
    """G-5B2: PricingCalculator importable from canonical formulas.pricing path."""

    def test_g_5b2_importable_from_formulas_pricing(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator
        assert PricingCalculator is not None

    def test_g_5b2_importable_from_canonical_pricing_py(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing.pricing import PricingCalculator
        assert PricingCalculator is not None

    def test_g_5b2_module_path_is_canonical(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing.pricing import PricingCalculator
        assert "calculator_motor.formulas.pricing" in PricingCalculator.__module__, (
            f"G-5B2: PricingCalculator.__module__ is '{PricingCalculator.__module__}', "
            "expected 'calculator_motor.formulas.pricing' in it."
        )

    def test_g_5b2_has_required_methods(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator
        assert hasattr(PricingCalculator, "calcular_ingreso_bruto")
        assert hasattr(PricingCalculator, "calcular_tarifa_unitaria")
        assert hasattr(PricingCalculator, "calcular_factor_billing")
        assert hasattr(PricingCalculator, "derivar_componentes_label")


class TestPricingCalculatorBoundaries:
    """G-5B3: formulas/pricing must not import heavy IO."""

    def _ast_imports(self, source_path: Path) -> list[str]:
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.append(node.module)
        return names

    def test_g_5b3_no_heavy_io_imports(self):
        imports = self._ast_imports(_CANONICAL_PRICING)
        offenders: list[str] = []
        for imp in imports:
            for forbidden in _HEAVY_IO_FORBIDDEN:
                if forbidden.lower() in imp.lower():
                    offenders.append(f"imports '{imp}'")
        assert not offenders, (
            "G-5B3: formulas/pricing/pricing.py imports heavy IO:\n"
            + "\n".join(f"  {o}" for o in offenders)
        )


class TestSharedPricingShim:
    """G-5B4: calculator_motor/shared compatibility package must stay deleted."""

    def test_g_5b4_shim_deleted(self):
        assert not _LEGACY_PRICING_SHARED.exists(), (
            "G-5B4: modules/calculator/shared/pricing.py should remain deleted after final shim cleanup."
        )

    def test_g_5b4_calculator_motor_shared_package_deleted(self):
        assert not (_BACKEND_ROOT / "modules" / "calculator_motor" / "shared").exists(), (
            "G-5B4: modules/calculator_motor/shared should remain deleted after compatibility cleanup."
        )


class TestBackwardCompatibility:
    """G-5B5: canonical imports remain available after shared cleanup."""

    def test_g_5b5_importable_from_formulas_pricing(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator
        assert PricingCalculator is not None

    def test_g_5b5_importable_from_canonical_pricing_py(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing.pricing import PricingCalculator
        assert PricingCalculator is not None

    def test_g_5b5_no_calculator_motor_shared_package(self):
        assert not (_BACKEND_ROOT / "modules" / "calculator_motor" / "shared").exists(), (
            "G-5B5: calculator_motor/shared should not reappear as a compatibility package"
        )


class TestPricingCalculatorParity:
    """G-5B6: numeric parity — methods produce identical results."""

    def test_g_5b6_calcular_ingreso_bruto(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator

        test_cases = [
            (100.0, 0.5),
            (100.0, 0.0),
            (100.0, -1.0),
            (1000.0, 0.8),
            (0.0, 0.5),
        ]
        for costo, factor_billing in test_cases:
            result = PricingCalculator.calcular_ingreso_bruto(costo, factor_billing)
            assert isinstance(result, float)
            if factor_billing <= 0:
                assert result == 0.0
            else:
                assert result == pytest.approx(costo / factor_billing, rel=1e-12)

    def test_g_5b6_calcular_tarifa_unitaria(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator

        test_cases = [
            (1000.0, 10.0),
            (1000.0, 0.0),
            (1000.0, -5.0),
            (500.0, 5.0),
            (0.0, 10.0),
        ]
        for facturacion, divisor in test_cases:
            result = PricingCalculator.calcular_tarifa_unitaria(facturacion, divisor)
            assert isinstance(result, float)
            if divisor <= 0:
                assert result == 0.0
            else:
                assert result == pytest.approx(facturacion / divisor, rel=1e-12)

    def test_g_5b6_derivar_componentes_label(self):
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator

        test_cases = [
            ("Fijo FTE", 1.0, ("FTE", "")),
            ("Variable", 0.0, ("", "Transacción")),
            ("Híbrido", 0.6, ("FTE", "Transacción")),
            ("desconocido", 1.0, ("FTE", "")),
            ("desconocido", 0.5, ("FTE", "Transacción")),
            ("desconocido", 0.0, ("", "Transacción")),
        ]
        for modelo_cobro, pct_fijo, expected in test_cases:
            result = PricingCalculator.derivar_componentes_label(modelo_cobro, pct_fijo)
            assert result == expected, (
                f"modelo={modelo_cobro}, pct={pct_fijo}: got {result}, expected {expected}"
            )


class TestNoProductiveOldImports:
    """G-5B7: no productive source imports from old paths."""

    def test_g_5b7_old_pricing_calculators_deleted(self):
        assert not _OLD_PRICING_CALCULATORS.exists(), (
            "G-5B7: modules/calculator/pricing/calculators.py should be deleted (was shim)"
        )

    def test_g_5b7_no_imports_from_old_path(self):
        assert not _LEGACY_ENGINE_PY.exists(), (
            "Legacy modules/calculator/engine.py must not be recreated"
        )
        source = _ENGINE_PY.read_text(encoding="utf-8")
        tree = ast.parse(source)
        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                if "calculator.pricing.calculators" in module and "PricingCalculator" in names:
                    violations.append(f"from {module} import {', '.join(names)}")
        assert not violations, (
            "G-5B7: engine.py or other production files import from old calculator.pricing.calculators:\n"
            + "\n".join(f"  {v}" for v in violations)
        )
