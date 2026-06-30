"""Guardrails read-only para la política de fuentes de parametrización."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
POLICY_DOC = BACKEND_ROOT / "docs/refactor/parametrization_source_policy.md"
BASELINE_MANIFEST = BACKEND_ROOT / "storage/baselines/v2-7-certified/manifest.json"
RUNTIME_BUSINESS_RULES = (
    BACKEND_ROOT
    / "modules/shared/config/business_rules/politicas_comerciales.yaml"
)
FROZEN_DIR = BACKEND_ROOT / "storage/parametrization/frozen"
V2_7_PARAM_ROOT = BACKEND_ROOT / "storage/parametrization/v2-7"
RUNTIME_ROOTS = (
    BACKEND_ROOT / "modules",
    BACKEND_ROOT / "db",
    BACKEND_ROOT / "app.py",
    BACKEND_ROOT / "scripts",
)


def _canonical_hash(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_parametrization_source_policy_doc_exists() -> None:
    assert POLICY_DOC.exists()


def test_parametrization_source_policy_doc_mentions_required_terms() -> None:
    text = POLICY_DOC.read_text(encoding="utf-8")
    required_terms = (
        "storage/baselines/v2-7-certified",
        "storage/parametrization/v2-7",
        "storage/parametrization/frozen",
        "HASH_MISMATCH",
        "recertificación",
        "revert",
    )

    for term in required_terms:
        assert term in text


def test_runtime_business_rules_path_exists() -> None:
    assert RUNTIME_BUSINESS_RULES.exists()


def test_certified_baseline_manifest_exists() -> None:
    assert BASELINE_MANIFEST.exists()


def test_frozen_parametrization_directory_exists() -> None:
    assert FROZEN_DIR.exists()


def test_known_hr_drift_remains_visible() -> None:
    manifest = json.loads(BASELINE_MANIFEST.read_text(encoding="utf-8"))
    expected_hashes = manifest["parametrization_hashes"]

    current_hashes = {
        "hr": _canonical_hash(V2_7_PARAM_ROOT / "hr.json"),
    }
    known_drift = {
        module: (expected_hashes[module], actual_hash)
        for module, actual_hash in current_hashes.items()
        if expected_hashes[module] != actual_hash
    }

    assert set(known_drift) == {"hr"}
    assert "No actualizar hashes para hacer pasar tests" in POLICY_DOC.read_text(
        encoding="utf-8"
    )


def test_v2_7_active_parametrization_files_are_gn_hr_op_only() -> None:
    active_json_files = sorted(path.name for path in V2_7_PARAM_ROOT.glob("*.json"))
    assert active_json_files == ["gn.json", "hr.json", "manifest.json", "op.json"]


def test_runtime_does_not_reference_removed_business_rules_storage_sources() -> None:
    forbidden = (
        "storage/parametrization/business_rules",
        "storage/parametrization/v2-7/business_rules.json",
        "v2-7/business_rules.json",
    )
    offenders: list[str] = []
    for root in RUNTIME_ROOTS:
        files = [root] if root.is_file() else list(root.rglob("*.py"))
        for path in files:
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    offenders.append(f"{path.relative_to(BACKEND_ROOT)}: {token}")

    assert offenders == []
