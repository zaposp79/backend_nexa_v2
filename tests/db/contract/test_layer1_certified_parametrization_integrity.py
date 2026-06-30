"""Test: Layer 1 Certified Parametrization Integrity

Validates that storage/parametrization/v2-7-certified/ files match
the parametrization_hashes declared in baseline manifest.

This ensures Layer 1 (immutable, certified) parametrization is intact
and can be used for reproducible certified mode execution.

LAYER 1 vs LAYER 2:
  Layer 1: storage/parametrization/v2-7-certified/ (immutable baseline)
  Layer 2: storage/parametrization/v2-7/ (mutable active parameters)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestLayer1CertifiedParametrizationIntegrity:
    """Validate Layer 1 parametrization integrity against manifest hashes."""

    @pytest.fixture(scope="session")
    def manifest(self):
        """Load baseline manifest."""
        manifest_path = (
            Path(__file__).resolve().parents[3]
            / "storage" / "baselines" / "v2-7-certified" / "manifest.json"
        )
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    @pytest.fixture(scope="session")
    def certified_parametrization_dir(self):
        """Get Layer 1 certified parametrization directory."""
        return (
            Path(__file__).resolve().parents[3]
            / "storage" / "parametrization" / "v2-7-certified"
        )

    @staticmethod
    def _compute_canonical_hash(filepath):
        """Compute SHA256 hash of parametrization file (canonical form)."""
        import hashlib

        data = json.loads(filepath.read_text(encoding="utf-8"))
        blob = json.dumps(
            data,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def test_layer1_directory_exists(self, certified_parametrization_dir):
        """Layer 1 certified parametrization directory must exist."""
        assert certified_parametrization_dir.exists(), (
            f"Layer 1 directory not found at {certified_parametrization_dir}"
        )

    def test_all_parametrization_modules_present(
        self, manifest, certified_parametrization_dir
    ):
        """All modules listed in manifest must have files in Layer 1."""
        expected_modules = manifest.get("parametrization_hashes", {}).keys()

        for module in expected_modules:
            module_path = certified_parametrization_dir / f"{module}.json"
            assert module_path.exists(), (
                f"Layer 1 file not found for {module} at {module_path}"
            )

    @pytest.mark.parametrize(
        "module",
        ["business_rules", "hr", "gn", "op"],
    )
    def test_parametrization_hash_matches_manifest(
        self, manifest, certified_parametrization_dir, module
    ):
        """Each Layer 1 parametrization file must match manifest hash."""
        expected_hash = manifest.get("parametrization_hashes", {}).get(module)
        if expected_hash is None:
            pytest.skip(f"Module {module} not in manifest")

        module_path = certified_parametrization_dir / f"{module}.json"
        if not module_path.exists():
            pytest.skip(f"Layer 1 file not found for {module}")

        actual_hash = self._compute_canonical_hash(module_path)

        assert actual_hash == expected_hash, (
            f"Hash mismatch for {module}:\n"
            f"  Expected (manifest): {expected_hash}\n"
            f"  Actual (disk):       {actual_hash}"
        )

    def test_layer1_provides_immutable_baseline(
        self, manifest, certified_parametrization_dir
    ):
        """Layer 1 parametrization serves as immutable baseline."""
        # Verify all hashes in manifest match Layer 1 files
        for module, expected_hash in manifest.get("parametrization_hashes", {}).items():
            module_path = certified_parametrization_dir / f"{module}.json"
            if module_path.exists():
                actual_hash = self._compute_canonical_hash(module_path)
                assert actual_hash == expected_hash, (
                    f"Layer 1 baseline broken for {module}"
                )

    def test_layer1_can_be_used_for_certified_execution(
        self, certified_parametrization_dir
    ):
        """Verify Layer 1 files are valid and can be loaded for execution."""
        for module in ["business_rules", "hr", "gn", "op"]:
            module_path = certified_parametrization_dir / f"{module}.json"
            if module_path.exists():
                # Verify file is valid JSON
                try:
                    data = json.loads(module_path.read_text(encoding="utf-8"))
                    assert isinstance(data, dict), (
                        f"{module}.json must be a JSON object, not {type(data)}"
                    )
                except json.JSONDecodeError as e:
                    pytest.fail(f"{module}.json is not valid JSON: {e}")

    def test_layer1_immutability_guarantee(
        self, manifest, certified_parametrization_dir
    ):
        """Verify that Layer 1 files have not been modified since certification."""
        # Compute all hashes
        layer1_hashes = {}
        for module in ["business_rules", "hr", "gn", "op"]:
            module_path = certified_parametrization_dir / f"{module}.json"
            if module_path.exists():
                layer1_hashes[module] = self._compute_canonical_hash(module_path)

        # Compare against manifest (must be identical)
        manifest_hashes = manifest.get("parametrization_hashes", {})
        for module, expected_hash in manifest_hashes.items():
            actual_hash = layer1_hashes.get(module)
            assert actual_hash == expected_hash, (
                f"Layer 1 {module} was modified post-certification"
            )


__all__ = ["TestLayer1CertifiedParametrizationIntegrity"]
