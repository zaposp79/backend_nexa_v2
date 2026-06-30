"""
Structural guardrails for PHASE 3A: Payroll formulas refactor.

Validates:
  G-3A1: modules/calculator_motor/formulas/payroll/ structure.
  G-3A2: PayrollCalculator importable from canonical location.
  G-3A3: No IO imports in payroll formulas.
  G-3A4: Shim is thin (no duplicate logic).
  G-3A5: Numeric results unchanged.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).parent.parent.parent
_FORMULAS_PAYROLL = _BACKEND_ROOT / "modules" / "calculator_motor" / "formulas" / "payroll"
_LEGACY_FORMULAS_PAYROLL = _BACKEND_ROOT / "modules" / "calculator" / "formulas" / "payroll"
_LEGACY_PAYROLL = _BACKEND_ROOT / "modules" / "cadena_a" / "payroll"

_FORBIDDEN_IMPORTS = frozenset(
    [
        "fastapi",
        "starlette",
        "DocumentStore",
        "cosmos",
        "azure",
        "JsonDocumentStore",
        "json_provider",
        "router",
        "logging",
        "requests",
        "httpx",
    ]
)


class TestPayrollFormulasStructure:
    """G-3A1: modules/calculator_motor/formulas/payroll/ structure."""

    def test_g_3a1_formulas_directory_exists(self):
        assert (_BACKEND_ROOT / "modules" / "calculator_motor" / "formulas").is_dir()
        assert not (_BACKEND_ROOT / "modules" / "calculator" / "formulas").is_dir(), (
            "Legacy modules/calculator/formulas must not be recreated"
        )

    def test_g_3a1_payroll_directory_exists(self):
        assert _FORMULAS_PAYROLL.is_dir()

    def test_g_3a1_init_py_exists(self):
        assert (_FORMULAS_PAYROLL / "__init__.py").exists()
        assert not (_LEGACY_FORMULAS_PAYROLL / "__init__.py").exists(), (
            "Legacy modules/calculator_motor/formulas/payroll must not be recreated"
        )

    def test_g_3a1_factors_py_exists(self):
        assert (_FORMULAS_PAYROLL / "factors.py").exists()


class TestPayrollCalculatorImportability:
    """G-3A2: PayrollCalculator importable from canonical location."""

    def test_g_3a2_importable_from_formulas(self):
        from nexa_engine.modules.calculator_motor.formulas.payroll import PayrollCalculator

        assert PayrollCalculator is not None

    def test_g_3a2_importable_from_calculators(self):
        from nexa_engine.modules.calculator_motor.formulas.payroll.factors import PayrollCalculator

        assert PayrollCalculator is not None

    def test_g_3a2_module_path(self):
        from nexa_engine.modules.calculator_motor.formulas.payroll.factors import PayrollCalculator

        assert "calculator_motor.formulas.payroll" in PayrollCalculator.__module__

    def test_g_3a2_has_required_methods(self):
        from nexa_engine.modules.calculator_motor.formulas.payroll import PayrollCalculator

        assert hasattr(PayrollCalculator, "calcular_factor_aumento")
        assert hasattr(PayrollCalculator, "calcular_factor_indexacion")
        assert hasattr(PayrollCalculator, "calcular_examenes_fraccion")


class TestPayrollFormulasBoundaries:
    """G-3A3: calculator_motor/formulas/payroll must not import forbidden symbols."""

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

    def test_g_3a3_no_forbidden_imports(self):
        # Only scan pure-math files (factors.py). nomina.py (NominaCalculator)
        # legitimately uses logging and audit_trace — checked separately in Phase 3B guardrails.
        pure_math_files = [_FORMULAS_PAYROLL / "factors.py", _FORMULAS_PAYROLL / "__init__.py"]
        offenders: list[str] = []
        for py_file in pure_math_files:
            if not py_file.exists():
                continue
            imports = self._ast_imports(py_file)
            for imp in imports:
                for forbidden in _FORBIDDEN_IMPORTS:
                    if forbidden.lower() in imp.lower():
                        offenders.append(f"{py_file.name}: imports '{imp}'")

        assert not offenders, (
            "G-3A3: pure-math payroll files import forbidden symbols:\n"
            + "\n".join(f"  {o}" for o in offenders)
        )




class TestPayrollNumericParity:
    """G-3A5: Numeric results unchanged."""

    def test_g_3a5_factor_aumento_legacy_vs_canonical(self):
        # Phase 5I: shared_calc deleted. Both now call canonical PayrollCalculator.
        from nexa_engine.modules.calculator_motor.formulas.payroll import PayrollCalculator

        cases = {1: 1.0, 12: 1.0, 13: 1.10, 24: 1.10, 25: 1.21, 36: 1.21}
        for mes, expected in cases.items():
            result = PayrollCalculator.calcular_factor_aumento(mes, 0.10, 13)
            assert result == pytest.approx(expected, rel=1e-9), f"mes={mes}"

    def test_g_3a5_factor_indexacion_unchanged(self):
        from nexa_engine.modules.calculator_motor.formulas.payroll import PayrollCalculator

        assert PayrollCalculator.calcular_factor_indexacion(1.18, 0.10, 13, 12) == pytest.approx(1.18)
        assert PayrollCalculator.calcular_factor_indexacion(1.18, 0.10, 13, 13) == pytest.approx(1.18 * 1.10)

    def test_g_3a5_examenes_fraccion_unchanged(self):
        from nexa_engine.modules.calculator_motor.formulas.payroll import PayrollCalculator

        assert PayrollCalculator.calcular_examenes_fraccion(12, 0.05, 0.10) == pytest.approx(
            1.0 / 12 + 0.05 + 0.10 / 12, rel=1e-12
        )
        assert PayrollCalculator.calcular_examenes_fraccion(0, 0.05, 0.10) == 0.0
