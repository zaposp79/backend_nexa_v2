"""Integrity guardrails for frozen parametrization snapshots.

These tests verify:
1. Frozen JSON files exist and have not been modified (hash check).
2. FrozenParametrizationRepository can load the data correctly.
3. FrozenParametrizationAdapter is not accidentally migrated to DocumentStore.
4. The adapter still implements IParametrizationProvider.

Hashes registered in FROZEN-1 (2026-06-04).
Any hash change means an unauthorized modification to certified data.

DO NOT update these hashes without:
  1. Documenting the reason in docs/refactor/architecture_exceptions.md.
  2. Verifying Oracle (parity tests) with Δ=0.
  3. Updating the certification records if applicable.

Note: business_rules.json was intentionally removed from v2-7 frozen payload
during BUSINESS_RULES_CANONICAL_MIGRATION. Business rules now live in canonical
YAML files under config/business_rules/. The v2-7 frozen snapshot covers only
GN, HR, OP payloads and the manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
STORAGE = BACKEND_ROOT / "storage"

# ---------------------------------------------------------------------------
# Registered hashes (FROZEN-1 — 2026-06-04)
# These are SHA-256 hashes of the canonical JSON payload.
# canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",",":"))
# ---------------------------------------------------------------------------
FROZEN_HASHES = {
    "storage/parametrization/frozen/v2-6.json":
        "98c541cefb397323033aaa98037488db1ee329ae48b2d7828c3ef29c6cb70a04",
    "storage/parametrization/v2-7/gn.json":
        "01c9482f7bc96703183be8f0a2638847f46cf4a4a9b41c45ab1910120568867e",
    "storage/parametrization/v2-7/hr.json":
        "7db9b3a5969af9690f89ea0e4b61ea5acd7e29dfcc09c53bae479ea8d3092299",
    "storage/parametrization/v2-7/op.json":
        "e0b323b3e6b8e76e5f8698eff4f12ac2d3fd9d1868577d28a58a946f8c488c07",
    "storage/parametrization/v2-7/manifest.json":
        "09ce477232a8b02be3e322665595a893f6b7dd612dec62a3dcebd6e98106f902",
}


def _payload_hash(path: Path) -> str:
    """SHA-256 of the canonical JSON payload."""
    data = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 1. File existence
# ---------------------------------------------------------------------------

class TestFrozenFilesExist:

    @pytest.mark.parametrize("rel_path", list(FROZEN_HASHES.keys()))
    def test_frozen_file_exists(self, rel_path: str):
        """Every frozen file in FROZEN_HASHES must exist at its expected path."""
        p = BACKEND_ROOT / rel_path
        assert p.exists(), (
            f"{rel_path} was deleted or moved. "
            f"Frozen files are certified historical records and must not be removed. "
            f"See docs/refactor/architecture_exceptions.md."
        )

    def test_business_rules_not_in_frozen_hashes(self):
        """business_rules.json is intentionally absent from v2-7 frozen payload.

        During BUSINESS_RULES_CANONICAL_MIGRATION, the business_rules.json
        snapshot was removed from the v2-7 frozen set. Business rules now
        live exclusively in canonical YAML files under config/business_rules/.
        The v2-7 frozen payload covers only GN, HR, OP and the manifest.
        """
        br_key = "storage/parametrization/v2-7/business_rules.json"
        assert br_key not in FROZEN_HASHES, (
            f"{br_key} must NOT be in FROZEN_HASHES. "
            f"It was intentionally removed during BUSINESS_RULES_CANONICAL_MIGRATION. "
            f"Business rules now live in canonical YAML."
        )


# ---------------------------------------------------------------------------
# 2. Hash integrity
# ---------------------------------------------------------------------------

class TestFrozenFileHashes:
    """Verify that frozen files have not been modified since FROZEN-1 certification."""

    @pytest.mark.parametrize("rel_path,expected_hash", list(FROZEN_HASHES.items()))
    def test_frozen_file_hash_unchanged(self, rel_path: str, expected_hash: str):
        """Frozen file payload hash must match the registered value."""
        p = BACKEND_ROOT / rel_path
        if not p.exists():
            pytest.skip(f"{rel_path} does not exist (checked in TestFrozenFilesExist)")

        actual = _payload_hash(p)
        assert actual == expected_hash, (
            f"Hash mismatch for {rel_path}!\n"
            f"  Expected: {expected_hash}\n"
            f"  Actual:   {actual}\n"
            f"This frozen file has been modified. Frozen files are certified and immutable.\n"
            f"If this change is intentional:\n"
            f"  1. Document reason in docs/refactor/architecture_exceptions.md.\n"
            f"  2. Verify Oracle (parity tests) with Δ=0.\n"
            f"  3. Update FROZEN_HASHES in this test file.\n"
            f"  4. Update certification records if applicable."
        )


# ---------------------------------------------------------------------------
# 3. Repository behaviour
# ---------------------------------------------------------------------------

class TestFrozenRepositoryBehaviour:

    def test_frozen_repository_loads_v2_6(self):
        """FrozenParametrizationRepository.load('v2-6') returns the expected model."""
        frozen_file = BACKEND_ROOT / "storage/parametrization/frozen/v2-6.json"
        if not frozen_file.exists():
            pytest.skip("v2-6.json not in storage — not a regression")

        from nexa_engine.modules.parametrizacion.repositories.frozen_parametrization_repository import (
            FrozenParametrizationRepository,
        )
        result = FrozenParametrizationRepository.load("v2-6")
        assert result is not None, "FrozenParametrizationRepository.load('v2-6') returned None"
        assert hasattr(result, "smmlv"), "FrozenParametrizationV26 missing 'smmlv' attribute"
        assert result.smmlv > 0, "SMMLV must be a positive number"

    def test_frozen_repository_does_not_use_document_store(self):
        """FrozenParametrizationRepository must NOT import DocumentStore.

        Frozen data is immutable certified data — it must NOT be migrated to
        DocumentStore without a dedicated FROZEN-2 phase that verifies hash
        equivalence. See docs/refactor/architecture_exceptions.md.
        """
        src = (
            BACKEND_ROOT
            / "modules/parametrizacion/repositories/frozen_parametrization_repository.py"
        ).read_text()
        assert "DocumentStore" not in src, (
            "frozen_parametrization_repository.py now imports DocumentStore. "
            "This migration must be validated in a FROZEN-2 phase with hash verification. "
            "See docs/refactor/architecture_exceptions.md."
        )

    def test_frozen_repository_is_read_only_in_production_path(self):
        """FrozenParametrizationRepository.save() must exist but be admin-only.

        The save() method is for admin/migration operations, not production CRUD.
        The production path (engine.py → adapter) only uses load().
        """
        src = (
            BACKEND_ROOT
            / "modules/parametrizacion/repositories/frozen_parametrization_repository.py"
        ).read_text()
        assert "def load(" in src, "FrozenParametrizationRepository must have load() method"
        # save() may exist for admin use — we just document that it's not called in prod
        # The key assertion is that engine.py only uses load, not save
        engine_src = (BACKEND_ROOT / "modules/calculator_motor/engine.py").read_text()
        assert "FrozenParametrizationRepository.save" not in engine_src, (
            "engine.py calls FrozenParametrizationRepository.save(). "
            "The production path must only use load(). "
            "save() is for admin/migration only."
        )
        assert not (BACKEND_ROOT / "modules/calculator/engine.py").exists(), (
            "Legacy modules/calculator/engine.py must not be recreated"
        )


# ---------------------------------------------------------------------------
# 4. Adapter protection
# ---------------------------------------------------------------------------

class TestFrozenAdapter:

    def test_adapter_implements_parametrization_provider(self):
        """FrozenParametrizationAdapter must implement IParametrizationProvider."""
        src = (
            BACKEND_ROOT
            / "modules/parametrizacion/shared/repositories/frozen_parametrization_adapter.py"
        ).read_text()
        assert "IParametrizationProvider" in src, (
            "FrozenParametrizationAdapter no longer implements IParametrizationProvider. "
            "The adapter pattern is required for engine.py injection."
        )
        assert "class FrozenParametrizationAdapter" in src, (
            "FrozenParametrizationAdapter class was removed from the adapter module."
        )

    def test_adapter_uses_frozen_repository_not_document_store(self):
        """FrozenParametrizationAdapter must read from FrozenParametrizationRepository.

        The adapter must NOT be changed to read from DocumentStore without a
        FROZEN-2 phase that verifies all hash equivalences.
        """
        src = (
            BACKEND_ROOT
            / "modules/parametrizacion/shared/repositories/frozen_parametrization_adapter.py"
        ).read_text()
        assert "FrozenParametrizationRepository" in src, (
            "FrozenParametrizationAdapter no longer uses FrozenParametrizationRepository. "
            "The adapter must read from the certified frozen files, not DocumentStore."
        )

    def test_engine_uses_adapter_not_document_store_for_frozen(self):
        """engine.py must use FrozenParametrizationAdapter for frozen versions.

        When parametrization_version is specified, the engine must use
        FrozenParametrizationAdapter — not build a DocumentStore-backed provider.
        """
        src = (BACKEND_ROOT / "modules/calculator_motor/engine.py").read_text()
        assert "FrozenParametrizationAdapter" in src, (
            "engine.py no longer uses FrozenParametrizationAdapter. "
            "Frozen version reproducibility depends on this adapter."
        )
