#!/usr/bin/env python3
"""
Generate / persist the OpenAPI spec for api-v1.

FastAPI already serves the OpenAPI document at runtime (``/openapi.json``);
this script materializes a frozen copy at ``contracts/openapi/api-v1.yaml``
so the contract can be reviewed without running the server. Idempotent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# nexa_engine is a sibling alias resolved via backend_nexa's parent dir
sys.path.insert(0, str(ROOT.parent))

OUT_YAML = ROOT / "contracts" / "openapi" / "api-v1.yaml"
OUT_JSON = ROOT / "contracts" / "openapi" / "api-v1.json"


def _dump_yaml(data) -> str:
    """Best-effort YAML dump without taking on a hard PyYAML dependency."""
    try:
        import yaml  # type: ignore

        return yaml.safe_dump(data, sort_keys=True, allow_unicode=True)
    except Exception:
        # Fallback: emit JSON inside a YAML document (still parseable as YAML)
        return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    # Build the FastAPI app via factory — does not trigger load_app_settings()
    # at import time; routes are registered when create_app() is called here.
    try:
        import backend_nexa  # noqa: F401  ensure nexa_engine alias is registered
        from nexa_engine.app import create_app  # noqa: WPS433
        app = create_app()
    except Exception as exc:
        print(f"[!] could not build FastAPI app ({exc}); emitting contract-only spec")
        app = None

    if app is not None:
        spec = app.openapi()
        # Tag the spec with the contract version
        spec.setdefault("info", {})["x-contract-version"] = "api-v1"
    else:
        # Minimal contract-only spec built from the api-v1 models.
        from nexa_engine.modules.shared.contracts.api_v1 import EntryDataV1, SimulationResultV1

        spec = {
            "openapi": "3.1.0",
            "info": {
                "title": "NEXA Simulator API (api-v1, contract-only)",
                "version": "1.0.0",
                "x-contract-version": "api-v1",
            },
            "paths": {
                "/api/v1/simulation/calculate": {
                    "post": {
                        "summary": "Execute pricing engine (api-v1)",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": EntryDataV1.model_json_schema(),
                                },
                            },
                        },
                        "responses": {
                            "201": {
                                "description": "Simulation accepted",
                                "content": {
                                    "application/json": {
                                        "schema": SimulationResultV1.model_json_schema(),
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }

    OUT_YAML.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    yaml_text = _dump_yaml(spec)
    json_text = json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    for path, text in ((OUT_YAML, yaml_text), (OUT_JSON, json_text)):
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if existing == text:
            print(f"[=] {path.relative_to(ROOT)}")
        else:
            path.write_text(text, encoding="utf-8")
            print(f"[+] {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
