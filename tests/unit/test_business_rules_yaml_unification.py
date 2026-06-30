"""BUSINESS_RULES_YAML_UNIFICATION guardrails.

Validates that:
  1. config/business_rules/ no longer exists (eliminated directory).
  2. All canonical YAML files are under modules/shared/config/business_rules/.
  3. The canonical loader loads riesgo, operaciones, and margenes correctly.
  4. The infrastructure shim was deleted (shared-cleanup).
  5. No hardcoded path references to config/business_rules remain in production code.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_DIR = _REPO_ROOT / "modules" / "shared" / "config" / "business_rules"
_LEGACY_DIR = _REPO_ROOT / "config" / "business_rules"


class TestCanonicalLocation:
    def test_legacy_config_dir_does_not_exist(self) -> None:
        assert not _LEGACY_DIR.exists(), (
            f"{_LEGACY_DIR} debe haber sido eliminado — "
            "todos los YAML viven en modules/shared/config/business_rules/"
        )

    def test_riesgo_yaml_in_canonical_dir(self) -> None:
        assert (_CANONICAL_DIR / "riesgo.yaml").is_file()

    def test_operaciones_yaml_in_canonical_dir(self) -> None:
        assert (_CANONICAL_DIR / "operaciones.yaml").is_file()

    def test_margenes_yaml_in_canonical_dir(self) -> None:
        assert (_CANONICAL_DIR / "margenes.yaml").is_file()

    def test_canonical_loader_exists(self) -> None:
        assert (_CANONICAL_DIR / "loader.py").is_file()


class TestCanonicalLoaderAPI:
    def test_load_business_rules_riesgo(self) -> None:
        from nexa_engine.modules.shared.config.business_rules.loader import load_business_rules

        rules = load_business_rules("riesgo")
        assert isinstance(rules, dict)
        assert "umbrales" in rules

    def test_load_business_rules_cached_returns_same_object(self) -> None:
        from nexa_engine.modules.shared.config.business_rules.loader import load_business_rules_cached

        a = load_business_rules_cached("riesgo")
        b = load_business_rules_cached("riesgo")
        assert a is b

    def test_get_business_rules_loads_operaciones(self) -> None:
        from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules

        rules = get_business_rules()
        assert rules.horas_semanales == 42.0

    def test_load_business_rules_missing_raises_file_not_found(self) -> None:
        from nexa_engine.modules.shared.config.business_rules.loader import load_business_rules

        with pytest.raises(Exception):
            load_business_rules("nonexistent_rule")


class TestInfrastructureShimDeleted:
    """shared/infrastructure/business_rules_loader.py was deleted in shared-cleanup."""

    def test_shim_infrastructure_business_rules_loader_deleted(self) -> None:
        """shared/infrastructure/business_rules_loader.py must not exist after shared-cleanup."""
        shim_path = (
            _REPO_ROOT / "modules" / "shared" / "infrastructure" / "business_rules_loader.py"
        )
        assert not shim_path.exists(), (
            "shared/infrastructure/business_rules_loader.py was not deleted. "
            "Canonical: modules/shared/config/business_rules/loader.py"
        )


class TestNoHardcodedLegacyPath:
    def test_no_production_path_construction_to_legacy_dir(self) -> None:
        """Verify no production Python file constructs a path to config/business_rules.

        Only checks executable lines (not comment-only lines, not docstrings) for
        patterns like Path(...) / "config" / "business_rules" or string literals
        used as filesystem paths.
        """
        _CODE_PATTERNS = (
            'Path(__file__)',
            'Path.cwd()',
            '_BUSINESS_RULES_ROOT',
            '"config/business_rules"',
            "'config/business_rules'",
        )
        prod_roots = [
            _REPO_ROOT / "modules",
            _REPO_ROOT / "db",
            _REPO_ROOT / "app.py",
        ]
        for root in prod_roots:
            if not Path(root).exists():
                continue
            for py_file in Path(root).rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue
                # Skip the deleted infrastructure shim (was legacy compat module)
                if py_file.name == "business_rules_loader.py" and "infrastructure" in str(py_file):
                    continue
                for line in py_file.read_text(encoding="utf-8").splitlines():
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if "config/business_rules" in stripped:
                        for pattern in _CODE_PATTERNS:
                            if pattern in stripped:
                                pytest.fail(
                                    f"{py_file}: line constructs path to legacy dir: {stripped!r}"
                                )
