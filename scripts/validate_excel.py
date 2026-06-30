"""
scripts/validate_excel.py
==========================
Comparador automático Excel V2-7 ↔ Backend.

Pipeline:
  1. Lee Excel V2-7 (data_only=True → valores cacheados).
  2. Ejecuta backend con test case canónico (WhatsApp-only).
  3. Compara componentes clave del P&G celda por celda.
  4. Identifica candidatos de root cause por componente.
  5. Genera diff report (JSON + Markdown).

Uso:
    python scripts/validate_excel.py
    python scripts/validate_excel.py --fail-on-delta 0.01   # CI mode

Outputs:
  - reports/excel_backend_diff.json
  - reports/excel_backend_diff.md
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: E402,F401 — registers nexa_engine alias in sys.modules
import openpyxl  # noqa: E402
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader  # noqa: E402
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder  # noqa: E402
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine  # noqa: E402

BACKEND_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES   = BACKEND_ROOT / "test_cases" / "input"  # Phase 5.5: Use clean input/ structure
EXCEL_PATH   = BACKEND_ROOT / "excel" / "Nexa - Pricing - Simulador - V2-7.xlsx"
REPORTS_DIR  = BACKEND_ROOT / "reports"

# Cell map: backend metric → (sheet, cell, descripción, root cause source)
EXCEL_CELL_MAP = {
    "payroll_a":    ("Visión P&G", "C31", "Payroll Inbound 10 mes 1",
                     "Nomina Loaded!C15 = D93+D238+D287+D349+D407+D182+D455"),
    "no_payroll_a": ("Visión P&G", "C40", "No Payroll mes 1",
                     "OPEX Fijo + Inversiones + Costos Fijos"),
    "costo_b":      ("Visión P&G", "C44", "Costos Cadena B mes 1",
                     "OPEX Fijo + S&M + HITL + Tarifa Canal × volumen"),
    "polizas":      ("Visión P&G", "C64", "Polizas mes 1",
                     "(costo_op / factor_margenes + financiacion) × tasa_efectiva_polizas"),
    "ica":          ("Visión P&G", None, "ICA (no en P&G directo)", "tasa_ica × base con gross-up"),
    "gmf":          ("Visión P&G", None, "GMF (no en P&G directo)", "tasa_gmf × (costo + polizas + financ)"),
    "financiacion": ("Visión P&G", "C65", "Costos Financieros mes 1",
                     "costo_mes_anterior × tasa_financ × factor_periodo"),
    "ingreso_neto": ("Visión P&G", "C26", "Ingreso Neto mes 1",
                     "ingreso_bruto + contingencias + markup - descuento"),
    "pct_utilidad_neta": ("Visión P&G", "C75", "% Utilidad Neta mes 1",
                          "utilidad_neta / ingreso_neto"),
}


def read_excel_cells(path: Path) -> dict:
    """Read named cells from the Excel V2-4 simulator."""
    wb = openpyxl.load_workbook(path, data_only=True)
    out = {}
    for key, (sheet, cell, _desc, _src) in EXCEL_CELL_MAP.items():
        if cell is None:
            continue
        try:
            out[key] = wb[sheet][cell].value
        except Exception as exc:
            out[key] = None
            out[f"_error_{key}"] = str(exc)
    wb.close()
    return out


def run_backend(case_path: Path) -> dict:
    loader = UserInputLoader()
    ui = loader.cargar(case_path)
    solic = SimulationContextBuilder().construir(ui)
    res = NexaPricingEngine().calcular(solic)
    p1 = res.pyg_por_mes[0]
    # IMPORTANTE: Excel V2-4 P&G C64 "Polizas" es semánticamente la SUMA de
    # ICA-section + GMF-section + Polizas-adic-section (etiqueta engañosa en Excel).
    # Backend separa los 3 conceptos, así que para match real comparamos la suma.
    return {
        "payroll_a":         p1.payroll_a,
        "no_payroll_a":      p1.no_payroll_a,
        "costo_b":           p1.costo_b,
        # Match semántico real: Excel "Polizas" P&G == ICA + GMF + Polizas
        "polizas":           p1.polizas + p1.ica + p1.gmf,
        "financiacion":      p1.financiacion,
        "ingreso_neto":      p1.ingreso_neto,
        "pct_utilidad_neta": p1.pct_utilidad_neta,
    }


def compare(excel_vals: dict, backend_vals: dict) -> list[dict]:
    rows: list[dict] = []
    for key, (sheet, cell, desc, root_src) in EXCEL_CELL_MAP.items():
        if cell is None:
            continue
        ex = excel_vals.get(key)
        bk = backend_vals.get(key)
        if ex is None or bk is None:
            rows.append({
                "metric": key, "sheet": sheet, "cell": cell, "description": desc,
                "excel": ex, "backend": bk, "delta": None, "delta_pct": None,
                "status": "missing", "root_cause_candidate": root_src,
            })
            continue
        delta = bk - ex
        denom = abs(ex) if abs(ex) > 1e-9 else 1.0
        delta_pct = (delta / denom * 100) if abs(ex) > 1e-9 else (0 if delta == 0 else None)
        # Classification
        abs_pct = abs(delta_pct) if delta_pct is not None else 0
        if abs_pct < 0.01:
            status = "match"
        elif abs_pct < 0.5:
            status = "minor"
        elif abs_pct < 2:
            status = "moderate"
        else:
            status = "major"
        rows.append({
            "metric": key, "sheet": sheet, "cell": cell, "description": desc,
            "excel": ex, "backend": bk, "delta": delta, "delta_pct": delta_pct,
            "status": status, "root_cause_candidate": root_src,
        })
    return rows


def render_markdown(rows: list[dict], case: str) -> str:
    lines = [
        f"# Excel V2-4 ↔ Backend Diff Report — `{case}`",
        f"**Generado:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Tabla de diff por componente",
        "",
        "| Componente | Sheet | Cell | Excel | Backend | Delta | Delta % | Estado | Root cause candidate |",
        "|------------|-------|------|-------|---------|-------|---------|--------|----------------------|",
    ]
    for r in rows:
        ex = r["excel"]
        bk = r["backend"]
        delta = r["delta"]
        delta_pct = r["delta_pct"]
        def fmt(v):
            if v is None: return "—"
            if isinstance(v, float):
                if abs(v) < 0.01: return f"{v:.4f}"
                return f"{v:,.2f}"
            return str(v)
        emoji = {"match": "✅", "minor": "⚠️", "moderate": "⚠️", "moderate": "⚠️", "major": "❌"}.get(r["status"], "❓")
        lines.append(
            f"| `{r['metric']}` | {r['sheet']} | `{r['cell']}` | {fmt(ex)} | {fmt(bk)} | "
            f"{fmt(delta) if delta is not None else '—'} | "
            f"{f'{delta_pct:+.5f}%' if delta_pct is not None else '—'} | "
            f"{emoji} {r['status']} | {r['root_cause_candidate']} |"
        )

    matches = sum(1 for r in rows if r["status"] == "match")
    lines.extend([
        "",
        f"**Resumen:** {matches}/{len(rows)} componentes con match exacto (delta < 0.01%)",
        "",
        "## Top desviaciones",
        "",
    ])
    sorted_rows = sorted(rows, key=lambda r: abs(r["delta_pct"] or 0), reverse=True)
    for r in sorted_rows[:5]:
        if r["delta_pct"] is None or abs(r["delta_pct"]) < 0.01:
            continue
        lines.append(f"- `{r['metric']}`: **{r['delta_pct']:+.5f}%** ({r['root_cause_candidate']})")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate backend output against Excel V2-4.")
    parser.add_argument("--case", default="bancamia_whatsapp_only", help="Test case name")
    parser.add_argument("--excel", default=str(EXCEL_PATH), help="Excel V2-4 path")
    parser.add_argument("--fail-on-delta", type=float, default=None,
                        help="Exit with code 1 if max delta pct exceeds this threshold.")
    args = parser.parse_args()

    case_path = TEST_CASES / f"{args.case}.json"
    if not case_path.exists():
        print(f"❌ Test case missing: {case_path}", file=sys.stderr)
        return 2

    excel_path = Path(args.excel)
    if not excel_path.exists():
        print(f"❌ Excel missing: {excel_path}", file=sys.stderr)
        return 2

    excel_vals   = read_excel_cells(excel_path)
    backend_vals = run_backend(case_path)
    rows         = compare(excel_vals, backend_vals)

    json_out = {
        "case": args.case,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "excel_path": str(excel_path.relative_to(BACKEND_ROOT)),
        "test_case_path": str(case_path.relative_to(BACKEND_ROOT)),
        "rows": rows,
        "summary": {
            "total": len(rows),
            "match": sum(1 for r in rows if r["status"] == "match"),
            "minor": sum(1 for r in rows if r["status"] == "minor"),
            "moderate": sum(1 for r in rows if r["status"] == "moderate"),
            "major": sum(1 for r in rows if r["status"] == "major"),
            "missing": sum(1 for r in rows if r["status"] == "missing"),
            "max_delta_pct": max((abs(r["delta_pct"]) for r in rows if r["delta_pct"] is not None), default=0),
            "avg_delta_pct": (
                sum(abs(r["delta_pct"]) for r in rows if r["delta_pct"] is not None) /
                max(sum(1 for r in rows if r["delta_pct"] is not None), 1)
            ),
        },
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "excel_backend_diff.json").write_text(json.dumps(json_out, ensure_ascii=False, indent=2))
    (REPORTS_DIR / "excel_backend_diff.md").write_text(render_markdown(rows, args.case))

    # CLI summary
    print(f"\n=== Excel V2-4 vs Backend (case: {args.case}) ===")
    print(f"{'Metric':<22} {'Excel':>16} {'Backend':>16} {'Delta %':>12}  Status")
    for r in rows:
        ex = r["excel"]; bk = r["backend"]
        ex_s = f"{ex:>16,.2f}" if isinstance(ex, (int, float)) else f"{str(ex):>16}"
        bk_s = f"{bk:>16,.2f}" if isinstance(bk, (int, float)) else f"{str(bk):>16}"
        dp = r["delta_pct"]
        dp_s = f"{dp:>+11.5f}%" if dp is not None else "—"
        print(f"  {r['metric']:<20} {ex_s} {bk_s} {dp_s}  {r['status']}")

    s = json_out["summary"]
    print(f"\n  Max delta: {s['max_delta_pct']:.5f}% · Avg delta: {s['avg_delta_pct']:.5f}%")
    print(f"  Match/Minor/Moderate/Major/Missing: {s['match']}/{s['minor']}/{s['moderate']}/{s['major']}/{s['missing']}")
    print(f"  → {REPORTS_DIR}/excel_backend_diff.{{json,md}}")

    if args.fail_on_delta is not None and s["max_delta_pct"] > args.fail_on_delta:
        print(f"\n❌ FAIL: max delta {s['max_delta_pct']:.5f}% > threshold {args.fail_on_delta:.5f}%")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
