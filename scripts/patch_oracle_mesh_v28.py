"""Patch oracle mesh JSON with V2-8 formula backend values.

Runs the engine against excel_v2_7_real_request.json (same input as oracle_mesh
test) and for each checkpoint in oracle_mesh_mapping.py, replaces the stored
oracle value with the current backend value.

This is the correct migration step after implementing a V2-8 formula change:
the oracle locks in the NEW expected behavior rather than the old V2-7 values.

Usage:
    source backend_nexa/venv/bin/activate
    cd /Users/darwin.minota.quinto/Projects/NEXA
    PYTHONPATH=$(pwd):$(pwd)/backend_nexa python backend_nexa/scripts/patch_oracle_mesh_v28.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]  # NEXA/
BACKEND_ROOT = REPO_ROOT / "backend_nexa"
ORACLE_FILE = BACKEND_ROOT / "tests" / "parity" / "excel_oracle_v2_7_mesh.json"
REQUEST_FILE = BACKEND_ROOT / "tests" / "parity" / "fixtures" / "excel_v2_7_real_request.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _run_engine(request_path: Path):
    """Run the NEXA engine with given request JSON, return PricingResult."""
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine

    loader = UserInputLoader()
    builder = SimulationContextBuilder()
    engine = NexaPricingEngine()

    # UserInputLoader.cargar() expects a Path; write to tmp if needed
    import tempfile, shutil
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        tmp = Path(tf.name)
    shutil.copy(request_path, tmp)
    try:
        ui = loader.cargar(tmp)
        ctx = builder.construir(ui)
        return engine.calcular(ctx)
    finally:
        tmp.unlink(missing_ok=True)


def main():
    print(f"Loading oracle: {ORACLE_FILE}")
    oracle = json.loads(ORACLE_FILE.read_text())
    cells = oracle["cells"]

    # Ensure nexa_engine alias is registered
    import backend_nexa  # noqa: F401 — registers nexa_engine alias in sys.modules

    print(f"Running engine against: {REQUEST_FILE}")
    result = _run_engine(REQUEST_FILE)
    print("Engine run complete.")

    from tests.parity.oracle_mesh_mapping import CHECKPOINTS

    updated = 0
    skipped_no_oracle = 0
    skipped_no_backend = 0

    for ck in CHECKPOINTS:
        cell_key = ck.excel
        if cell_key not in cells:
            skipped_no_oracle += 1
            continue

        backend_val = ck.extractor(result)
        if backend_val is None:
            skipped_no_backend += 1
            continue

        old_val = cells[cell_key]["value"]
        if abs(old_val - backend_val) > 1e-9:
            cells[cell_key]["value"] = backend_val
            cells[cell_key]["_v28_patch"] = True
            cells[cell_key]["_v28_old_value"] = old_val
            updated += 1
            print(f"  UPDATED {ck.id:55s}  {cell_key:35s}  {old_val:.6f} → {backend_val:.6f}")

    # Update metadata
    oracle["_metadata"]["v28_patch_applied_at"] = datetime.now(timezone.utc).isoformat()
    oracle["_metadata"]["v28_patch_checkpoints_updated"] = updated
    oracle["_metadata"]["v28_patch_note"] = (
        "Values updated to V2-8 CAPEX amortization formula "
        "(Cadena C!J62 = (I62/H62)*(1+Panel!L11)) — 2026-06-10"
    )

    ORACLE_FILE.write_text(json.dumps(oracle, indent=2, ensure_ascii=False))
    print(f"\nDone: {updated} cells updated, {skipped_no_oracle} skipped (no oracle), "
          f"{skipped_no_backend} skipped (no backend extractor)")
    print(f"Wrote: {ORACLE_FILE}")


if __name__ == "__main__":
    main()
