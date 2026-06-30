"""Guardrails for PHASE 4A: NoPayrollCalculator move."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).parent.parent.parent
_FORMULAS_NO_PAYROLL = _BACKEND_ROOT / "modules" / "calculator_motor" / "formulas" / "no_payroll"
_LEGACY_NO_PAYROLL_PATH = (
    _BACKEND_ROOT / "modules" / "calculator" / "formulas" / "no_payroll" / "costs.py"
)
_LEGACY_ENGINE_PY = _BACKEND_ROOT / "modules" / "calculator" / "engine.py"
_ENGINE_PY = _BACKEND_ROOT / "modules" / "calculator_motor" / "engine.py"

_HEAVY_IO_FORBIDDEN = frozenset([
    "fastapi", "starlette", "DocumentStore", "cosmos", "azure",
    "JsonDocumentStore", "json_provider", "router", "requests", "httpx",
])


class TestNoPayrollCalculatorStructure:
    """G-4A1: calculator.py exists in canonical no_payroll package."""

    def test_g_4a1_costs_py_exists(self):
        assert (_FORMULAS_NO_PAYROLL / "costs.py").exists()
        assert not _LEGACY_NO_PAYROLL_PATH.exists(), (
            "Legacy modules/calculator/formulas/no_payroll/costs.py must not be recreated"
        )

    def test_g_4a1_init_exports_no_payroll_calculator(self):
        init_content = (_FORMULAS_NO_PAYROLL / "__init__.py").read_text(encoding="utf-8")
        assert "NoPayrollCalculator" in init_content


class TestNoPayrollCalculatorImportability:
    """G-4A2: NoPayrollCalculator importable from canonical location."""

    def test_g_4a2_importable(self):
        from nexa_engine.modules.calculator_motor.formulas.no_payroll import NoPayrollCalculator
        assert NoPayrollCalculator is not None

    def test_g_4a2_has_required_methods(self):
        from nexa_engine.modules.calculator_motor.formulas.no_payroll import NoPayrollCalculator
        assert hasattr(NoPayrollCalculator, "calcular_para_mes")
        assert hasattr(NoPayrollCalculator, "FORMULA_ID")




class TestEngineImportSource:
    """G-4A4: engine.py imports NoPayrollCalculator from canonical, not cadena_a."""

    def test_g_4a4_engine_not_from_cadena_a_no_payroll(self):
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
                if "cadena_a.no_payroll" in module and "NoPayrollCalculator" in names:
                    violations.append(f"from {module} import {', '.join(names)}")
        assert not violations, f"engine.py imports from cadena_a.no_payroll: {violations}"


class TestCalculatorPyBoundaries:
    """G-4A5: no_payroll/calculator.py has no heavy IO."""

    def test_g_4a5_no_heavy_io_imports(self):
        calculator_py = _FORMULAS_NO_PAYROLL / "costs.py"
        source = calculator_py.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        offenders = [
            imp for imp in imports
            for forbidden in _HEAVY_IO_FORBIDDEN
            if forbidden.lower() in imp.lower()
        ]
        assert not offenders, f"Heavy IO imports in no_payroll/calculator.py: {offenders}"
