"""WAVE 13 — Schema stability for the audit DTOs.

Mirrors `test_contract_schema_stable.py` for the audit response/explanation
contracts. The committed JSONSchema is frozen; if the DTO changes the wire
shape, regenerate with `python scripts/contracts/generate_schemas.py`
(intentional change) or bump to api-v2 (breaking change).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexa_engine.modules.shared.contracts.api_v1.response.audit import (
    AuditResponseV1,
    AuditSimulationSummaryV1,
    AuditValueExplanationV1,
)


SCHEMA_DIR = Path(__file__).resolve().parents[2] / "contracts" / "api_v1" / "schema"

AUDIT_MODELS = {
    "audit_response": AuditResponseV1,
    "audit_value_explanation": AuditValueExplanationV1,
    "audit_simulation_summary": AuditSimulationSummaryV1,
}


@pytest.mark.parametrize("name,model", list(AUDIT_MODELS.items()))
def test_audit_schema_stable(name: str, model) -> None:
    schema_file = SCHEMA_DIR / f"{name}.schema.json"
    assert schema_file.exists(), (
        f"missing committed schema {schema_file}; run "
        f"`python scripts/contracts/generate_schemas.py`"
    )
    committed = json.loads(schema_file.read_text(encoding="utf-8"))
    fresh = json.loads(json.dumps(model.model_json_schema(), sort_keys=True))
    committed_norm = json.loads(json.dumps(committed, sort_keys=True))
    assert fresh == committed_norm, (
        f"JSONSchema drift for {name}. "
        f"Re-run `python scripts/contracts/generate_schemas.py` if intentional, "
        f"or bump to api-v2 if this is a breaking change."
    )


def test_audit_response_required_top_level_keys() -> None:
    """Lock the binding wire contract: these keys must always be present."""
    schema = AuditResponseV1.model_json_schema()
    required = set(schema.get("required", []))
    # api_version, engine_version, formula_set have defaults so they are
    # not in 'required' — but they must always be in properties.
    for key in (
        "simulation_id",
        "lineage",
        "formulas",
        "parameters_used",
        "parametrization_hashes",
        "api_version",
        "engine_version",
        "formula_set",
    ):
        assert key in schema["properties"], f"missing key in schema: {key}"
    # simulation_id is the only required field; everything else has defaults.
    assert "simulation_id" in required


def test_audit_response_extra_forbid() -> None:
    """`extra='forbid'` must be encoded in the schema."""
    schema = AuditResponseV1.model_json_schema()
    assert schema.get("additionalProperties") is False
