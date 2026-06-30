"""F6 — Build DRIFT_HEATMAP.md from mesh checkpoints vs backend output.

Ejecuta el motor con el request canónico V2-7, compara cada checkpoint
contra Excel y emite:
  - tests/parity/DRIFT_HEATMAP.md (resumen por stage + top drifts)
"""
from __future__ import annotations

import json
import statistics
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT))

import backend_nexa  # noqa
from nexa_engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader

from tests.parity.oracle_mesh_mapping import CHECKPOINTS  # noqa: E402

MESH_FILE = ROOT / "tests" / "parity" / "excel_oracle_v2_7_mesh.json"
REQUEST_FILE = ROOT / "tests" / "parity" / "fixtures" / "excel_v2_7_real_request.json"
OUT = ROOT / "tests" / "parity" / "DRIFT_HEATMAP.md"

REL_TOL = 1e-6
ABS_TOL = 1e-6


def main():
    import tempfile
    mesh = json.loads(MESH_FILE.read_text())["cells"]

    # Run engine
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "req.json"
        p.write_text(REQUEST_FILE.read_text())
        ui = UserInputLoader().cargar(p)
        ctx = SimulationContextBuilder().construir(ui)
        result = NexaPricingEngine().calcular(ctx)

    rows = []  # list of dict per checkpoint
    for c in CHECKPOINTS:
        excel_val = mesh.get(c.excel, {}).get("value")
        backend_val = None
        verdict = "NO_ORACLE"
        drift = None
        try:
            backend_val = c.extractor(result)
        except Exception as e:
            backend_val = None
            verdict = f"EXTRACTOR_ERROR:{type(e).__name__}"

        if excel_val is None:
            verdict = "NO_ORACLE"
        elif backend_val is None:
            verdict = "BACKEND_MISSING"
        elif abs(excel_val) < ABS_TOL:
            verdict = "PASS" if abs(backend_val) < ABS_TOL else "FAIL"
            drift = abs(backend_val - excel_val)
        else:
            drift = abs(backend_val - excel_val) / abs(excel_val)
            verdict = "PASS" if drift < REL_TOL else "FAIL"

        rows.append({
            "id": c.id,
            "stage": c.stage,
            "category": c.category,
            "excel": c.excel,
            "excel_val": excel_val,
            "backend_val": backend_val,
            "drift": drift,
            "verdict": verdict,
        })

    # Aggregate by stage
    by_stage = {}
    for r in rows:
        by_stage.setdefault(r["stage"], []).append(r)

    md = []
    md.append("# F6 — Drift Heatmap (Oracle Validation Mesh)")
    md.append("")
    md.append(f"- Total checkpoints: **{len(rows)}**")
    md.append(f"- Tolerancia técnica: rel < 1e-6 (objetivo conceptual 0.00%)")
    md.append(f"- Request: `tests/parity/fixtures/excel_v2_7_real_request.json` (V2-7 preloaded)")
    md.append(f"- Oracle source: `tests/parity/excel_oracle_v2_7_mesh.json` (V2-7)")
    md.append("")

    overall = {
        "PASS": sum(1 for r in rows if r["verdict"] == "PASS"),
        "FAIL": sum(1 for r in rows if r["verdict"] == "FAIL"),
        "BACKEND_MISSING": sum(1 for r in rows if r["verdict"] == "BACKEND_MISSING"),
        "NO_ORACLE": sum(1 for r in rows if r["verdict"] == "NO_ORACLE"),
    }
    md.append(f"## Resumen global")
    md.append("")
    md.append(f"| Verdict | Count | Pct |")
    md.append(f"|---|---:|---:|")
    for k, v in overall.items():
        pct = (v / len(rows) * 100) if rows else 0
        md.append(f"| {k} | {v} | {pct:.1f}% |")
    md.append("")

    md.append("## Heatmap por stage")
    md.append("")
    md.append("| Stage | Total | PASS | FAIL | MISSING | Min drift | Max drift | Median drift |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for stage in sorted(by_stage.keys()):
        items = by_stage[stage]
        p = sum(1 for r in items if r["verdict"] == "PASS")
        f = sum(1 for r in items if r["verdict"] == "FAIL")
        m = sum(1 for r in items if r["verdict"] == "BACKEND_MISSING")
        drifts = [r["drift"] for r in items
                  if r["verdict"] == "FAIL" and r["drift"] is not None and r["excel_val"] not in (None, 0)
                  and abs(r["excel_val"]) >= ABS_TOL]
        if drifts:
            mn = f"{min(drifts) * 100:.4f}%"
            mx = f"{max(drifts) * 100:.4f}%"
            md_ = f"{statistics.median(drifts) * 100:.4f}%"
        else:
            mn = mx = md_ = "-"
        md.append(f"| {stage} | {len(items)} | {p} | {f} | {m} | {mn} | {mx} | {md_} |")
    md.append("")

    # Top 10 drifts
    fails_with_drift = [r for r in rows
                        if r["verdict"] == "FAIL" and r["drift"] is not None
                        and r["excel_val"] and abs(r["excel_val"]) >= ABS_TOL]
    fails_with_drift.sort(key=lambda r: r["drift"] or 0, reverse=True)
    md.append("## Top 10 checkpoints con mayor drift")
    md.append("")
    md.append("| Stage | Checkpoint | Excel cell | Excel value | Backend value | Drift |")
    md.append("|---|---|---|---:|---:|---:|")
    for r in fails_with_drift[:10]:
        md.append(
            f"| {r['stage']} | `{r['id']}` | `{r['excel']}` | "
            f"{r['excel_val']:,.4f} | {r['backend_val']:,.4f} | "
            f"{r['drift'] * 100:.4f}% |"
        )
    md.append("")

    # Stages limpios (drift <0.01%)
    md.append("## Stages limpios (todos PASS o drift <0.01%)")
    md.append("")
    clean = []
    for stage, items in by_stage.items():
        all_pass = all(r["verdict"] == "PASS" for r in items)
        small_drift = all(
            (r["drift"] is None or r["drift"] < 1e-4)
            for r in items if r["verdict"] != "BACKEND_MISSING"
        )
        if all_pass or small_drift:
            clean.append((stage, len(items),
                          sum(1 for r in items if r["verdict"] == "PASS")))
    if clean:
        for stage, total, p in sorted(clean):
            md.append(f"- **{stage}** — {p}/{total} PASS")
    else:
        md.append("- (ninguno)")
    md.append("")

    # Top 5 stages con mayor fail concentration (>50%)
    md.append("## Top 5 stages con mayor concentración de fallos")
    md.append("")
    md.append("| Stage | FAIL+MISSING | Total | Pct |")
    md.append("|---|---:|---:|---:|")
    stage_fail_counts = []
    for stage, items in by_stage.items():
        bad = sum(1 for r in items if r["verdict"] in ("FAIL", "BACKEND_MISSING"))
        if bad and items:
            stage_fail_counts.append((stage, bad, len(items), bad / len(items)))
    stage_fail_counts.sort(key=lambda x: (-x[3], -x[1]))
    for stage, bad, total, pct in stage_fail_counts[:5]:
        md.append(f"| {stage} | {bad} | {total} | {pct * 100:.1f}% |")
    md.append("")

    # Recomendación de orden de ataque
    md.append("## Recomendación F3.B / F4 / F5 priority")
    md.append("")
    md.append("La concentración de fallos por stage es la mejor señal:")
    md.append("")
    md.append("1. **PAYROLL_A** (factor de indexación + composición SENA) → F3.B sub-wave")
    md.append("2. **COSTOS_FINANCIEROS** (GMF base + ICA base + comisión admin + pólizas) → F4")
    md.append("3. **COSTO_C / VISION_TARIFAS Cadena C** (HITL no modelado) → F5")
    md.append("4. **VISION_CTS** (depende de cadenas A+B+C correctos) — gated por 1-3")
    md.append("")

    # Full table per checkpoint at end
    md.append("## Tabla completa de checkpoints")
    md.append("")
    md.append("<details><summary>Click para expandir</summary>")
    md.append("")
    md.append("| Stage | Checkpoint | Excel | Excel value | Backend value | Drift | Verdict |")
    md.append("|---|---|---|---:|---:|---:|---|")
    for r in sorted(rows, key=lambda r: (r["stage"], r["id"])):
        ev = f"{r['excel_val']:,.4f}" if r['excel_val'] is not None else "-"
        bv = f"{r['backend_val']:,.4f}" if r['backend_val'] is not None else "-"
        dv = f"{r['drift'] * 100:.4f}%" if r['drift'] is not None else "-"
        md.append(f"| {r['stage']} | `{r['id']}` | `{r['excel']}` | {ev} | {bv} | {dv} | {r['verdict']} |")
    md.append("")
    md.append("</details>")
    md.append("")

    OUT.write_text("\n".join(md))
    print(f"Wrote {OUT}")
    print(f"Overall: {overall}")
    print(f"Top 5 stages by fail rate:")
    for stage, bad, total, pct in stage_fail_counts[:5]:
        print(f"  {stage}: {bad}/{total} ({pct*100:.1f}%)")


if __name__ == "__main__":
    main()
