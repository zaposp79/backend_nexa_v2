"""WAVE 14 — VersionRegistry behavior."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexa_engine.modules.shared.versioning.version_registry import VersionMetadata, VersionRegistry


def test_get_current_returns_valid_metadata(fake_storage: Path):
    reg = VersionRegistry(storage_root=fake_storage)
    meta = reg.get_current()
    assert isinstance(meta, VersionMetadata)
    assert meta.engine_version == "engine-v2"
    assert meta.api_version == "api-v1"
    assert meta.parametrization_version == "v2-7"
    assert meta.formula_set == "formula-set-v2-7"
    assert set(meta.parametrization_hashes.keys()) == {"hr", "gn", "op"}


def test_compute_parametrization_hashes_idempotent(fake_storage: Path):
    reg = VersionRegistry(storage_root=fake_storage)
    h1 = reg.compute_parametrization_hashes()
    h2 = reg.compute_parametrization_hashes()
    assert h1 == h2
    assert len(h1) == 3
    # SHA-256 is 64 hex chars
    for v in h1.values():
        assert len(v) == 64
        int(v, 16)  # parseable as hex


def test_hashes_change_when_json_changes(fake_storage: Path):
    reg = VersionRegistry(storage_root=fake_storage)
    h1 = reg.compute_parametrization_hashes()
    # mutate hr.json
    hr_path = fake_storage / "parametrization" / "v2-7" / "hr.json"
    hr_path.write_text(json.dumps({"hr": "different"}), encoding="utf-8")
    reg.invalidate_cache()
    h2 = reg.compute_parametrization_hashes()
    assert h1["hr"] != h2["hr"]
    assert h1["gn"] == h2["gn"]


def test_get_active_parametrization_version(fake_storage: Path):
    reg = VersionRegistry(storage_root=fake_storage)
    assert reg.get_active_parametrization_version() == "v2-7"


def test_get_active_version_falls_back_to_unknown(tmp_path: Path):
    reg = VersionRegistry(storage_root=tmp_path / "empty")
    assert reg.get_active_parametrization_version() == "unknown"
    meta = reg.get_current()
    assert meta.parametrization_version == "unknown"


def test_version_metadata_serialization_roundtrip():
    meta = VersionMetadata(
        excel_version="V2-7",
        parametrization_version="v2-7",
        engine_version="engine-v2",
        api_version="api-v1",
        formula_set="formula-set-v2-7",
        baseline_version="v2-7-certified",
        parametrization_hashes={"hr": "abc", "gn": "def"},
    )
    d = meta.to_dict()
    rebuilt = VersionMetadata.from_dict(d)
    assert rebuilt == meta


def test_baseline_version_override(fake_storage: Path):
    reg = VersionRegistry(storage_root=fake_storage)
    meta = reg.get_current(baseline_version="v2-7-certified")
    assert meta.baseline_version == "v2-7-certified"
    # Default cached snapshot still doesn't carry baseline.
    default_meta = reg.get_current()
    assert default_meta.baseline_version is None


def test_with_overrides_immutable():
    base = VersionMetadata()
    new = base.with_overrides(engine_version="engine-v3")
    assert base.engine_version == "engine-v2"
    assert new.engine_version == "engine-v3"
