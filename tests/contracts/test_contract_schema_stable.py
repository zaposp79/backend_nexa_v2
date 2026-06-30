"""
Schema stability — regenerated JSONSchema must match the committed one.

Protects api-v1 from accidental drift. If a DTO is edited in a way that
changes the wire shape, this test fails with a diff and forces the author
to bump to api-v2 (or update the committed schema deliberately).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexa_engine.modules.shared.contracts.api_v1 import (
    EntryDataV1,
    PanelDeControlRequestV1,
    CadenaARequestV1,
    CadenaBRequestV1,
    CadenaCRequestV1,
    EscenarioComercialV1,
    VisionTarifasV1,
    VisionPyGV1,
    CostToServeV1,
    WaterfallV1,
    VisionsBundleV1,
    KpisV1,
    SimulationResultV1,
)
from nexa_engine.modules.vision_imprimible.api.response_models import VisionImprimibleApiResponseV1

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "contracts" / "api_v1" / "schema"

MODELS = {
    "entry_data": EntryDataV1,
    "panel": PanelDeControlRequestV1,
    "cadena_a": CadenaARequestV1,
    "cadena_b": CadenaBRequestV1,
    "cadena_c": CadenaCRequestV1,
    "escenario": EscenarioComercialV1,
    "vision_tarifas": VisionTarifasV1,
    "vision_pyg": VisionPyGV1,
    "cost_to_serve": CostToServeV1,
    "waterfall": WaterfallV1,
    "visions_bundle": VisionsBundleV1,
    "kpis": KpisV1,
    "simulation_result": SimulationResultV1,
    "vision_imprimible_public_response": VisionImprimibleApiResponseV1,
}


@pytest.mark.parametrize("name,model", list(MODELS.items()))
def test_committed_schema_matches_pydantic(name: str, model) -> None:
    schema_file = SCHEMA_DIR / f"{name}.schema.json"
    assert schema_file.exists(), (
        f"missing committed schema {schema_file}; run "
        f"`python scripts/contracts/generate_schemas.py`"
    )
    committed = json.loads(schema_file.read_text(encoding="utf-8"))
    fresh = json.loads(json.dumps(model.model_json_schema(), sort_keys=True))
    # Normalize key order on both sides for a stable comparison
    committed_norm = json.loads(json.dumps(committed, sort_keys=True))
    assert fresh == committed_norm, (
        f"JSONSchema drift for {name}. "
        f"Re-run `python scripts/contracts/generate_schemas.py` if intentional, "
        f"or bump to api-v2 if this is a breaking change."
    )
