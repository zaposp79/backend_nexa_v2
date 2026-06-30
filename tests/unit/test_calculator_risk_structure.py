"""
Structural guardrails for risk calculator canonical location.

Ratchet tests — fail if the refactor regresses:
  G-R1: modules/riesgo/ must not exist.
  G-R2: No source file imports nexa_engine.modules.riesgo.
  G-R3: RiesgoCalculator lives at nexa_engine.modules.calculator_motor.formulas.risk.
  G-R4: calculator_motor/formulas/risk does not import API, routers, DocumentStore, Cosmos, or JSON providers.
  G-R5: calculator/risk shim must stay deleted.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).parent.parent.parent  # backend_nexa/
_RISK_SHIM = _BACKEND_ROOT / "modules" / "calculator" / "risk" / "__init__.py"
_FORMULAS_RISK = _BACKEND_ROOT / "modules" / "calculator_motor" / "formulas" / "risk"
_OLD_RIESGO = _BACKEND_ROOT / "modules" / "riesgo"

_FORBIDDEN_IMPORTS_IN_RISK = frozenset(
    [
        "fastapi",
        "starlette",
        "DocumentStore",
        "cosmos",
        "azure",
        "JsonDocumentStore",
        "json_provider",
        "routers",
    ]
)


class TestCalculatorRiskStructure:
    """G-R1: modules/riesgo must not exist after Phase 1 migration."""

    def test_g_r1_modules_riesgo_does_not_exist(self):
        assert not _OLD_RIESGO.exists(), (
            f"G-R1: modules/riesgo still exists at {_OLD_RIESGO}. "
            "It should have been removed after Phase 1 migration to calculator/risk."
        )

    def test_g_r1_modules_riesgo_not_a_python_package(self):
        assert not (_OLD_RIESGO / "__init__.py").exists(), (
            "G-R1b: modules/riesgo/__init__.py still exists."
        )


class TestNoLegacyRiesgoImports:
    """G-R2: No source file should import from nexa_engine.modules.riesgo."""

    def _collect_python_sources(self) -> list[Path]:
        return [
            p
            for p in _BACKEND_ROOT.rglob("*.py")
            if "__pycache__" not in p.parts
        ]

    def test_g_r2_no_imports_from_modules_riesgo(self):
        offenders: list[str] = []
        for source_file in self._collect_python_sources():
            if source_file.name == "test_calculator_risk_structure.py":
                continue
            try:
                tree = ast.parse(source_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and "modules.riesgo" in node.module:
                    offenders.append(str(source_file.relative_to(_BACKEND_ROOT)))
                    break
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "modules.riesgo" in alias.name:
                            offenders.append(str(source_file.relative_to(_BACKEND_ROOT)))
                            break

        assert not offenders, (
            "G-R2: Files still importing from modules.riesgo:\n"
            + "\n".join(f"  {f}" for f in offenders)
        )


class TestRiesgoCalculatorLocation:
    """G-R3: RiesgoCalculator must be importable from calculator_motor.formulas.risk."""

    def test_g_r3_riesgo_calculator_importable_from_canonical_package(self):
        from nexa_engine.modules.calculator_motor.formulas.risk import RiesgoCalculator  # noqa: F401

        assert RiesgoCalculator is not None

    def test_g_r3_riesgo_calculator_module_path(self):
        from nexa_engine.modules.calculator_motor.formulas.risk.riesgo import RiesgoCalculator

        assert "calculator_motor.formulas.risk" in RiesgoCalculator.__module__, (
            f"G-R3: Expected RiesgoCalculator in calculator_motor.formulas.risk, got: {RiesgoCalculator.__module__}"
        )

    def test_g_r3_risk_canonical_file_exists(self):
        assert (_FORMULAS_RISK / "riesgo.py").exists(), (
            f"G-R3: canonical riesgo.py not found at {_FORMULAS_RISK / 'riesgo.py'}"
        )
        assert not (_BACKEND_ROOT / "modules" / "calculator" / "formulas" / "risk").exists(), (
            "G-R3: Legacy modules/calculator_motor/formulas/risk must not be recreated"
        )


class TestCalculatorRiskBoundaries:
    """G-R4: calculator_motor/formulas/risk must not import API, persistence, or infrastructure."""

    def _ast_imports(self, source_path: Path) -> list[str]:
        """Return all module names referenced in import statements."""
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

    def test_g_r4_risk_module_no_forbidden_imports(self):
        offenders: list[str] = []
        for py_file in _FORMULAS_RISK.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            imports = self._ast_imports(py_file)
            for imp in imports:
                for forbidden in _FORBIDDEN_IMPORTS_IN_RISK:
                    if forbidden.lower() in imp.lower():
                        offenders.append(f"{py_file.name}: imports '{imp}'")

        assert not offenders, (
            "G-R4: calculator_motor/formulas/risk imports forbidden symbols (API/persistence):\n"
            + "\n".join(f"  {o}" for o in offenders)
        )


class TestDeletedRiskShim:
    """G-R5: calculator/risk shim must stay deleted."""

    def test_g_r5_calculator_risk_shim_deleted(self):
        assert not _RISK_SHIM.exists(), (
            "G-R5: modules/calculator/risk/__init__.py should remain deleted. "
            "Use nexa_engine.modules.calculator_motor.formulas.risk instead."
        )
