"""
Backward compatibility: every baseline request must round-trip through
:class:`EntryDataV1` and arrive at the legacy ``SimulationRequest`` unchanged.

This guarantees existing clients can keep posting the historical shape and
the engine receives an equivalent payload.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexa_engine.modules.shared.contracts.api_v1 import EntryDataV1
from nexa_engine.modules.shared.contracts.api_v1.adapter import (
    entry_data_v1_to_legacy_dict,
    entry_data_v1_to_simulation_request,
)

ROOT = Path(__file__).resolve().parents[2]
BASELINES = ROOT / "storage" / "baselines" / "v2-7-certified" / "cases"

BASELINE_REQUESTS = sorted(BASELINES.glob("*/request.json"))


@pytest.mark.parametrize(
    "request_path",
    BASELINE_REQUESTS,
    ids=[p.parent.name for p in BASELINE_REQUESTS],
)
def test_baseline_round_trip_to_legacy(request_path: Path) -> None:
    raw = json.loads(request_path.read_text(encoding="utf-8"))

    entry = EntryDataV1.model_validate(raw)
    legacy = entry_data_v1_to_legacy_dict(entry)

    # Required legacy keys present
    assert "panel_de_control" in legacy
    assert "cadenas_activas" not in legacy  # lifted out of top-level

    # Panel still contains the legacy nested form
    panel = legacy["panel_de_control"]
    assert "cadenas_activas" in panel
    assert isinstance(panel["cadenas_activas"], dict)

    # The legacy SimulationRequest must accept it
    sim_request = entry_data_v1_to_simulation_request(entry)
    assert sim_request.panel_de_control.cliente == raw["panel_de_control"].get("cliente", "")
    assert sim_request.panel_de_control.meses_contrato == raw["panel_de_control"].get(
        "meses_contrato", 12
    )


def test_count_of_baselines_matches_expected() -> None:
    # WAVE 6 froze 12 cases under v2-7-certified.
    assert len(BASELINE_REQUESTS) == 12
