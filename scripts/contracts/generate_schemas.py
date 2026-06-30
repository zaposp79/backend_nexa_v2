#!/usr/bin/env python3
"""
Generate JSONSchema for all api-v1 contract models.

Idempotent — re-running produces byte-equal files.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow `python scripts/contracts/generate_schemas.py` from repo root
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from nexa_engine.modules.shared.contracts.api_v1 import (  # noqa: E402
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
from nexa_engine.modules.shared.contracts.api_v1.response.audit import (  # noqa: E402
    AuditResponseV1,
    AuditSimulationSummaryV1,
    AuditValueExplanationV1,
)
from nexa_engine.modules.vision_imprimible.api.response_models import (  # noqa: E402
    VisionImprimibleApiResponseV1,
)

OUT_DIR = ROOT / "contracts" / "api_v1" / "schema"

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
    # WAVE 13 — audit DTOs
    "audit_response": AuditResponseV1,
    "audit_value_explanation": AuditValueExplanationV1,
    "audit_simulation_summary": AuditSimulationSummaryV1,
}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, model in MODELS.items():
        schema = model.model_json_schema()
        out = OUT_DIR / f"{name}.schema.json"
        # Sort keys for deterministic, idempotent output
        text = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        existing = out.read_text(encoding="utf-8") if out.exists() else ""
        if existing == text:
            print(f"[=] {out.relative_to(ROOT)}")
        else:
            out.write_text(text, encoding="utf-8")
            print(f"[+] {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
