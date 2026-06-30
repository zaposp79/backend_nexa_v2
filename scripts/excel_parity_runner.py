"""
scripts/excel_parity_runner.py
==============================
Runner de paridad backend <-> Excel V2-8.

Stage 1: ejecuta el motor sobre request/request.json y reporta métricas ancla
junto a los valores cacheados de V2-8, PERO antepone un guard de identidad de
deal. V2-8 trae cargado un deal distinto al de request.json, por lo que una
comparación numérica directa NO es válida hasta alinear inputs (Stage 2).

Salida:
  - reports/v28_parity_runner.md

Uso:
    PYTHONPATH=$(pwd) python scripts/excel_parity_runner.py
"""
from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime, timezone

import openpyxl

import backend_nexa  # noqa: F401 — registra alias nexa_engine
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import (
    UserInputLoader,
)
from nexa_engine.modules.calculator_motor.context_builder import (
    SimulationContextBuilder,
)
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from scripts.excel_map_common import BACKEND_ROOT, EXCEL_V28_PATH, REQUEST_PATH
from scripts.excel_map_vision_pyg import PYG_ANCHOR_CELLS, SHEET_NAME

warnings.filterwarnings("ignore")

REPORTS_DIR = BACKEND_ROOT / "reports"

# Celdas de identidad del deal cargado en V2-8 ('Panel de Control General').
V28_DEAL_IDENTITY_CELLS = {
    "servicio": "C5",
    "cliente": "C6",
    "antiguedad": "C7",
    "tipo_cliente": "C8",
    "duracion_meses": "C11",
    "ciudad": "C12",
}


def _read_request_identity() -> dict:
    d = json.loads(REQUEST_PATH.read_text())
    do = d["datos_operativos"]
    return {
        "servicio": do.get("servicio"),
        "cliente": do.get("cliente"),
        "tipo_cliente": do.get("tipo_cliente"),
        "duracion_meses": do.get("duracion_meses"),
        "ciudad": do.get("ciudad"),
    }


def _read_v28_identity(wb) -> dict:
    panel = wb["Panel de Control General"]
    return {k: panel[v].value for k, v in V28_DEAL_IDENTITY_CELLS.items()}


def _run_backend() -> dict:
    data = json.loads(REQUEST_PATH.read_text())
    ui = UserInputLoader().cargar_desde_dict(data)
    sol = SimulationContextBuilder().construir(ui)
    res = NexaPricingEngine().calcular(sol)
    p1 = res.pyg_por_mes[0]
    return {
        "payroll_a": p1.payroll_a,
        "no_payroll_a": p1.no_payroll_a,
        "costo_b": p1.costo_b,
        "financiacion": p1.financiacion,
        "ingreso_neto": p1.ingreso_neto,
        "pct_utilidad_neta": p1.pct_utilidad_neta,
    }


def _deal_aligned(req_id: dict, v28_id: dict) -> bool:
    # Comparación laxa: servicio + cliente + tipo deben coincidir (strip/upper).
    def norm(x: object) -> str:
        return str(x).strip().upper() if x is not None else ""

    return (
        norm(req_id.get("servicio")) == norm(v28_id.get("servicio"))
        and norm(req_id.get("cliente")) == norm(v28_id.get("cliente"))
        and norm(req_id.get("tipo_cliente")) == norm(v28_id.get("tipo_cliente"))
    )


def main() -> int:
    wb = openpyxl.load_workbook(EXCEL_V28_PATH, data_only=True)
    req_id = _read_request_identity()
    v28_id = _read_v28_identity(wb)
    aligned = _deal_aligned(req_id, v28_id)

    backend = _run_backend()
    sheet = wb[SHEET_NAME]
    excel = {
        metric: sheet[spec["cell"]].value
        for metric, spec in PYG_ANCHOR_CELLS.items()
    }

    lines = [
        "# V2-8 Parity Runner (Stage 1)",
        f"**Generado:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Guard de identidad de deal",
        "",
        "| Campo | request.json | V2-8 cargado |",
        "|-------|--------------|--------------|",
    ]
    for k in ("servicio", "cliente", "tipo_cliente", "duracion_meses", "ciudad"):
        lines.append(f"| {k} | {req_id.get(k)} | {v28_id.get(k)} |")
    lines += [
        "",
        f"**Deal alineado:** {'SI' if aligned else 'NO — INPUT_DEAL_MISMATCH'}",
        "",
    ]
    if not aligned:
        lines += [
            "> ⚠️ **INPUT_DEAL_MISMATCH**: el deal cargado en V2-8 difiere del de",
            "> request.json. La comparación numérica de abajo es **informativa**,",
            "> NO un veredicto de paridad. Para paridad V2-8 real (Stage 2):",
            "> alinear request.json al deal de V2-8 (METROCUADRADO/SAC) o recalcular",
            "> V2-8 en Excel con el deal de request.json para refrescar el cache.",
            "",
        ]
    lines += [
        "## Anclas P&G mes 1 (informativo)",
        "",
        "| Métrica | Backend (request.json) | V2-8 cacheado | Celda |",
        "|---------|------------------------|---------------|-------|",
    ]
    for metric, spec in PYG_ANCHOR_CELLS.items():
        bk = backend.get(metric)
        ex = excel.get(metric)
        bk_s = f"{bk:,.2f}" if isinstance(bk, (int, float)) else str(bk)
        ex_s = f"{ex:,.2f}" if isinstance(ex, (int, float)) else str(ex)
        lines.append(f"| {metric} | {bk_s} | {ex_s} | {spec['cell']} |")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "v28_parity_runner.md").write_text("\n".join(lines) + "\n")

    print(f"Deal aligned: {aligned}")
    if not aligned:
        print("INPUT_DEAL_MISMATCH — comparación numérica diferida a Stage 2")
    print(f"→ {(REPORTS_DIR / 'v28_parity_runner.md').relative_to(BACKEND_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
