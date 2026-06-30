"""
Phase 5K structural guardrails.

Validates:
  G-5KB1: Shim calculator/risk/__init__.py deleted.
  G-5KB2: Shim calculator/serializer.py deleted.
  G-5KB3: Shim calculator/shared/pricing.py deleted.
  G-5KC1: UserInputLoader canonical location is adapters/.
  G-5KC2: No production imports to old calculator.user_input_loader path.
  G-5KC3: formulas/ does not import user_input_loader.
  G-5KC4: user_input_loader (adapters) does not import forbidden IO boundaries.
  G-5KC5: InputNormalizer not imported via user_input_loader.
"""
from __future__ import annotations

import ast
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_MODULES = _BACKEND_ROOT / "modules"
_TESTS = _BACKEND_ROOT / "tests"


class TestPhase5KBShimsDeleted:
    """G-5KB: Shims from 5K-B must not exist."""

    def test_g_5kb1_risk_shim_deleted(self):
        assert not (_MODULES / "calculator" / "risk" / "__init__.py").exists(), (
            "calculator/risk/__init__.py shim should have been deleted in 5K-B"
        )

    def test_g_5kb2_serializer_shim_deleted(self):
        assert not (_MODULES / "calculator" / "serializer.py").exists(), (
            "calculator/serializer.py shim should have been deleted in 5K-B"
        )

    def test_g_5kb3_shared_pricing_shim_deleted(self):
        assert not (_MODULES / "calculator" / "shared" / "pricing.py").exists(), (
            "calculator/shared/pricing.py shim should have been deleted in 5K-B"
        )


class TestPhase5KCUserInputLoader:
    """G-5KC: UserInputLoader canonical location is calculator_motor/adapters/."""

    def test_g_5kc1_canonical_file_exists(self):
        assert (_MODULES / "calculator_motor" / "adapters" / "user_input_loader.py").exists()
        assert not (_MODULES / "calculator" / "adapters" / "user_input_loader.py").exists(), (
            "Legacy modules/calculator/adapters/user_input_loader.py must not be recreated"
        )

    def test_g_5kc2_importable_from_adapters(self):
        from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
        assert "calculator_motor.adapters" in UserInputLoader.__module__

    def test_g_5kc3_no_root_shim_exists(self):
        assert not (_MODULES / "calculator" / "user_input_loader.py").exists(), (
            "Root shim calculator/user_input_loader.py should not exist after clean break"
        )

    def test_g_5kc4_no_production_imports_to_old_path(self):
        old_path_fragment = "calculator.user_input_loader"
        violations: list[str] = []
        for py in _MODULES.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if old_path_fragment in text:
                violations.append(str(py.relative_to(_BACKEND_ROOT)))
        assert not violations, (
            "Production modules still import from old path:\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    def test_g_5kc5_formulas_do_not_import_user_input_loader(self):
        formulas_root = _MODULES / "calculator_motor" / "formulas"
        violations: list[str] = []
        for py in formulas_root.rglob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "user_input_loader" in node.module:
                        violations.append(f"{py.relative_to(_BACKEND_ROOT)}: imports {node.module}")
        assert not violations

    def test_g_5kc6_adapters_loader_no_forbidden_imports(self):
        loader_path = _MODULES / "calculator_motor" / "adapters" / "user_input_loader.py"
        forbidden = frozenset(["fastapi", "starlette", "DocumentStore", "cosmos", "azure",
                                "JsonDocumentStore", "json_provider", "requests", "httpx"])
        tree = ast.parse(loader_path.read_text(encoding="utf-8"))
        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for fb in forbidden:
                    if fb.lower() in node.module.lower():
                        violations.append(f"imports {node.module}")
        assert not violations, "calculator_motor/adapters/user_input_loader imports forbidden symbols:\n" + "\n".join(violations)

    def test_g_5kc7_input_normalizer_not_via_user_input_loader(self):
        """InputNormalizer must be imported from input_normalizer, not via user_input_loader."""
        this_file = Path(__file__)
        violations: list[str] = []
        for py in list(_MODULES.rglob("*.py")) + list(_TESTS.rglob("*.py")):
            if py == this_file:
                continue
            text = py.read_text(encoding="utf-8")
            if "user_input_loader import InputNormalizer" in text:
                violations.append(str(py.relative_to(_BACKEND_ROOT)))
        assert not violations, (
            "InputNormalizer imported via user_input_loader (must use input_normalizer directly):\n"
            + "\n".join(f"  {v}" for v in violations)
        )
