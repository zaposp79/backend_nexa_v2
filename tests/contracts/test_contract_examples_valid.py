"""
Examples + baselines must validate against api-v1.

Covers:
  * Every JSON under contracts/api_v1/examples/ that has a known schema.
  * Every request.json under storage/baselines/v2-7-certified/cases/.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexa_engine.modules.shared.contracts.api_v1 import EntryDataV1, KpisV1, VisionTarifasV1

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "contracts" / "api_v1" / "examples"
BASELINES = ROOT / "storage" / "baselines" / "v2-7-certified" / "cases"


# --------------------------------------------------------------------------- #
# 1) Curated examples
# --------------------------------------------------------------------------- #

EXAMPLE_MAP = {
    "bancamia_request.json": EntryDataV1,
    "bancamia_kpis.json": KpisV1,
    "bancamia_vision_tarifas.json": VisionTarifasV1,
}


@pytest.mark.parametrize("filename,model", list(EXAMPLE_MAP.items()))
def test_example_validates(filename: str, model) -> None:
    path = EXAMPLES / filename
    assert path.exists(), f"missing example {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    model.model_validate(data)


# --------------------------------------------------------------------------- #
# 2) Every baseline request.json validates as EntryDataV1
# --------------------------------------------------------------------------- #

BASELINE_REQUESTS = sorted(BASELINES.glob("*/request.json"))


@pytest.mark.parametrize(
    "request_path",
    BASELINE_REQUESTS,
    ids=[p.parent.name for p in BASELINE_REQUESTS],
)
def test_baseline_request_validates_as_entry_data_v1(request_path: Path) -> None:
    data = json.loads(request_path.read_text(encoding="utf-8"))
    entry = EntryDataV1.model_validate(data)
    # cadenas_activas must be non-empty after the validator runs
    assert entry.cadenas_activas, (
        f"{request_path.parent.name}: cadenas_activas is empty after inference"
    )
