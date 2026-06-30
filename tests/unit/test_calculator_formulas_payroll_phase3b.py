"""
Structural guardrails for PHASE 3B: NominaCalculator move to canonical payroll package.

Validates:
  G-3B1: modules/calculator_motor/formulas/payroll/calculator.py exists and is importable.
  G-3B2: NominaCalculator importable from canonical path.
  G-3B3: cadena_a/nomina.py is a thin shim (no duplicate logic).
  G-3B4: engine.py does NOT import NominaCalculator from cadena_a.nomina.
  G-3B5: calculator.py does not import heavy IO (FastAPI, DocumentStore, Cosmos).
  G-3B6: NoPayrollCalculator, StaffingCalculator, NominaCargadaService, BuildPayrollUseCase
         are NOT present in calculator_motor/formulas/payroll/.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).parent.parent.parent
_FORMULAS_PAYROLL = _BACKEND_ROOT / "modules" / "calculator_motor" / "formulas" / "payroll"
_LEGACY_FORMULAS_PAYROLL = _BACKEND_ROOT / "modules" / "calculator" / "formulas" / "payroll"
_LEGACY_NOMINA = _BACKEND_ROOT / "modules" / "calculator" / "formulas" / "payroll" / "nomina.py"
_LEGACY_ENGINE_PY = _BACKEND_ROOT / "modules" / "calculator" / "engine.py"
_ENGINE_PY = _BACKEND_ROOT / "modules" / "calculator_motor" / "engine.py"

# Forbidden in calculator.py: heavy IO only (logging and audit_trace are allowed)
_HEAVY_IO_FORBIDDEN = frozenset([
    "fastapi",
    "starlette",
    "DocumentStore",
    "cosmos",
    "azure",
    "JsonDocumentStore",
    "json_provider",
    "router",
    "requests",
    "httpx",
    "openpyxl",
    "xlrd",
    "pandas",
])

# Classes that must NOT be moved to formulas/payroll/
_CLASSES_NOT_MOVED = frozenset([
    "NoPayrollCalculator",
    "StaffingCalculator",
    "NominaCargadaService",
    "BuildPayrollUseCase",
])


class TestNominaCalculatorStructure:
    """G-3B1: nomina.py exists in canonical payroll package."""

    def test_g_3b1_calculator_py_exists(self):
        assert (_FORMULAS_PAYROLL / "nomina.py").exists(), (
            "G-3B1: modules/calculator_motor/formulas/payroll/nomina.py not found."
        )
        assert not _LEGACY_FORMULAS_PAYROLL.exists(), (
            "G-3B1: Legacy modules/calculator_motor/formulas/payroll must not be recreated"
        )

    def test_g_3b1_init_exports_nomina_calculator(self):
        init_content = (_FORMULAS_PAYROLL / "__init__.py").read_text(encoding="utf-8")
        assert "NominaCalculator" in init_content, (
            "G-3B1: __init__.py does not export NominaCalculator."
        )


class TestNominaCalculatorImportability:
    """G-3B2: NominaCalculator importable from canonical location."""

    def test_g_3b2_importable_from_formulas_payroll(self):
        from nexa_engine.modules.calculator_motor.formulas.payroll import NominaCalculator
        assert NominaCalculator is not None

    def test_g_3b2_importable_from_calculator_module(self):
        from nexa_engine.modules.calculator_motor.formulas.payroll.nomina import NominaCalculator
        assert NominaCalculator is not None

    def test_g_3b2_module_path_is_canonical(self):
        from nexa_engine.modules.calculator_motor.formulas.payroll.nomina import NominaCalculator
        assert "calculator_motor.formulas.payroll" in NominaCalculator.__module__, (
            f"G-3B2: NominaCalculator.__module__ is '{NominaCalculator.__module__}', "
            "expected 'calculator_motor.formulas.payroll' in it."
        )

    def test_g_3b2_has_required_public_interface(self):
        from nexa_engine.modules.calculator_motor.formulas.payroll import NominaCalculator
        assert hasattr(NominaCalculator, "calcular_para_mes")
        assert hasattr(NominaCalculator, "FORMULA_ID")


class TestEngineImportSource:
    """G-3B4: engine.py imports NominaCalculator from canonical location, not cadena_a.nomina."""

    def test_g_3b4_engine_not_from_cadena_a_nomina(self):
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
                if "cadena_a.nomina" in module and "NominaCalculator" in names:
                    violations.append(f"from {module} import {', '.join(names)}")
        assert not violations, (
            "G-3B4: engine.py still imports NominaCalculator from cadena_a.nomina:\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_g_3b4_engine_imports_from_canonical(self):
        source = _ENGINE_PY.read_text(encoding="utf-8")
        assert "calculator_motor.formulas.payroll" in source and "NominaCalculator" in source, (
            "G-3B4: engine.py does not import NominaCalculator from calculator_motor.formulas.payroll."
        )


class TestCalculatorPyBoundaries:
    """G-3B5: calculator.py must not import heavy IO (FastAPI, DocumentStore, Cosmos, etc.)."""

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

    def test_g_3b5_no_heavy_io_imports(self):
        calculator_py = _FORMULAS_PAYROLL / "nomina.py"
        imports = self._ast_imports(calculator_py)
        offenders: list[str] = []
        for imp in imports:
            for forbidden in _HEAVY_IO_FORBIDDEN:
                if forbidden.lower() in imp.lower():
                    offenders.append(f"imports '{imp}'")
        assert not offenders, (
            "G-3B5: calculator_motor/formulas/payroll/nomina.py imports heavy IO:\n"
            + "\n".join(f"  {o}" for o in offenders)
        )


class TestClassesNotMoved:
    """G-3B6: Forbidden classes must NOT appear in nomina.py."""

    def test_g_3b6_nomoved_classes_absent(self):
        source = (_FORMULAS_PAYROLL / "nomina.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        present: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in _CLASSES_NOT_MOVED:
                present.append(node.name)
        assert not present, (
            "G-3B6: Classes that must NOT be moved are present in nomina.py:\n"
            + "\n".join(f"  {c}" for c in present)
        )

    def test_g_3b6_no_payroll_calculator_not_in_package(self):
        for py_file in _FORMULAS_PAYROLL.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "NoPayrollCalculator":
                    pytest.fail(
                        f"G-3B6: NoPayrollCalculator is defined in {py_file}. "
                        "It must NOT be moved to calculator_motor/formulas/payroll/."
                    )
