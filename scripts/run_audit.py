"""
scripts/run_audit.py
====================
Ejecuta el motor con debug_trace=True para los test_cases canónicos.
Exporta reports/audit/trace_<case>.{json,csv}
"""
from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: E402, F401 — init nexa_engine alias

from nexa_engine.modules.audit.trace import get_tracer                                  # noqa: E402
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader       # noqa: E402
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder # noqa: E402
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine                          # noqa: E402

BACKEND_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES   = BACKEND_ROOT / "test_cases"
AUDIT_DIR    = BACKEND_ROOT / "reports" / "audit"

CANONICAL = ["bancamia_whatsapp_only", "bancamia_excel_match"]


def run_one(case: str) -> dict:
    case_path = TEST_CASES / f"{case}.json"
    if not case_path.exists():
        print(f"⚠ skipping {case}: file not found")
        return {}
    tracer = get_tracer()
    tracer.start(case=case)
    ui = UserInputLoader().cargar(case_path)
    solic = SimulationContextBuilder().construir(ui)
    NexaPricingEngine().calcular(solic)
    tracer.stop()

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = AUDIT_DIR / f"trace_{case}.json"
    csv_path  = AUDIT_DIR / f"trace_{case}.csv"
    tracer.export(json_path)
    tracer.export_csv(csv_path)
    summary = tracer.to_dict()["summary"]
    print(f"✅ {case}: {summary['total_entries']} entries → {json_path.name}, {csv_path.name}")
    return summary


def main() -> int:
    for case in CANONICAL:
        run_one(case)
    return 0


if __name__ == "__main__":
    sys.exit(main())
