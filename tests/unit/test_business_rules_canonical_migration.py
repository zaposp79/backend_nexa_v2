"""Guardrail tests for BUSINESS_RULES_CANONICAL_MIGRATION.

Verifies that:
- politicas_comerciales.yaml exists and has correct values.
- ProviderBusinessRulesMixin reads from YAML (not storage/).
- db/container.py no longer imports BusinessRulesRepository.
- No production code references storage/parametrization/business_rules.
"""
from __future__ import annotations

import os

import pytest

YAML_DIR = os.path.join(
    os.path.dirname(__file__),
    "../../modules/shared/config/business_rules",
)
CONTAINER_PATH = os.path.join(
    os.path.dirname(__file__), "../../db/container.py"
)
MODULES_DIR = os.path.join(os.path.dirname(__file__), "../../modules")


def test_canonical_yaml_politicas_comerciales_present():
    path = os.path.join(YAML_DIR, "politicas_comerciales.yaml")
    assert os.path.isfile(path), "politicas_comerciales.yaml must exist"


def test_canonical_yaml_returns_5_policies():
    from nexa_engine.modules.shared.config.business_rules.loader import load_business_rules

    rules = load_business_rules("politicas_comerciales")
    politicas = rules["politicas_comerciales"]
    assert len(politicas) == 5, f"Expected 5 policies, got {len(politicas)}"


def test_politicas_values_match_legacy():
    from nexa_engine.modules.shared.config.business_rules.loader import load_business_rules

    politicas = {
        p["nombre"]: p
        for p in load_business_rules("politicas_comerciales")["politicas_comerciales"]
    }

    assert politicas["contingencia_operativa"]["min"] == pytest.approx(0.025)
    assert politicas["contingencia_operativa"]["max"] == pytest.approx(0.12)
    assert politicas["contingencia_comercial"]["min"] == pytest.approx(0.04)
    assert politicas["contingencia_comercial"]["max"] == pytest.approx(0.07)
    assert politicas["markup"]["min"] == pytest.approx(0.02)
    assert politicas["markup"]["max"] == pytest.approx(0.08)
    assert politicas["descuento"]["min"] == pytest.approx(0.0)
    assert politicas["descuento"]["max"] == pytest.approx(0.15)
    assert politicas["imprevistos"]["min"] == pytest.approx(0.0)
    assert politicas["imprevistos"]["max"] == pytest.approx(1.0)


def test_get_riesgo_config_returns_umbrales():
    from nexa_engine.modules.parametrizacion.mixins.provider_business_rules import (
        ProviderBusinessRulesMixin,
    )

    mixin = ProviderBusinessRulesMixin()
    config = mixin.get_riesgo_config()
    assert isinstance(config, dict), "get_riesgo_config must return a dict"
    assert "umbrales" in config, "riesgo config must contain 'umbrales' key"


def test_no_runtime_import_of_business_rules_repository_in_container():
    with open(CONTAINER_PATH, encoding="utf-8") as f:
        content = f.read()
    assert "BusinessRulesRepository" not in content, (
        "db/container.py must not import BusinessRulesRepository after migration"
    )


def test_no_runtime_storage_path_for_business_rules_in_production():
    """No production .py file (outside business_rules_repository.py) should
    reference storage/parametrization/business_rules in executable code
    (open(), Path(), string literals). Comments and docstrings are allowed."""
    target = "storage/parametrization/business_rules"
    # Patterns that indicate runtime use (not comments/docstrings)
    runtime_patterns = ('open(', 'Path(', '"storage/', "'storage/")
    violations = []
    for root, dirs, files in os.walk(MODULES_DIR):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            if fname == "business_rules_repository.py":
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, encoding="utf-8") as f:
                lines = f.readlines()
            for lineno, line in enumerate(lines, 1):
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                if target in line and any(pat in line for pat in runtime_patterns):
                    violations.append(f"{fpath}:{lineno}: {line.rstrip()}")
    assert not violations, (
        "Found runtime storage/parametrization/business_rules references:\n"
        + "\n".join(violations)
    )
