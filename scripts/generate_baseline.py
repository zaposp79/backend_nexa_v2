"""
scripts/generate_baseline.py
============================
Genera el baseline oficial congelado:
  - reports/baseline_oficial.json       — outputs canónicos esperados
  - reports/storage_checksums.json      — hash SHA256 de cada master JSON
  - reports/excel_version_fingerprint.json — fingerprint del Excel V2-4 y masters

Uso:
    python scripts/generate_baseline.py
    python scripts/generate_baseline.py --verify   # falla si difiere del baseline grabado
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import logging
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")

# Ensure we can import nexa_engine
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend_nexa  # noqa: F401 — registers nexa_engine alias
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader   # noqa: E402
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder  # noqa: E402
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine                     # noqa: E402

BACKEND_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES   = BACKEND_ROOT / "test_cases"
EXCEL_DIR    = BACKEND_ROOT / "excel"
STORAGE_DIR  = BACKEND_ROOT / "storage" / "parametrization"
REPORTS_DIR  = BACKEND_ROOT / "reports"

# Canonical test cases bundled with the repo
CANONICAL_CASES = [
    "bancamia_whatsapp_only",
    "bancamia_excel_match",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_storage_checksums() -> dict:
    out: dict[str, dict] = {}
    for dom in ["hr", "gn", "op"]:
        dom_dir = STORAGE_DIR / dom
        if not dom_dir.is_dir():
            continue
        out[dom] = {}
        for f in sorted(dom_dir.glob("*.json")):
            if f.name == "versions.json":
                continue
            out[dom][f.name] = {
                "sha256": sha256_file(f),
                "size_bytes": f.stat().st_size,
            }
        ver_file = dom_dir / "versions.json"
        if ver_file.exists():
            with open(ver_file) as fh:
                out[dom]["_versions"] = json.load(fh)
    return out


def collect_excel_fingerprint() -> dict:
    out: dict[str, dict] = {}
    for f in sorted(EXCEL_DIR.glob("*.xlsx")):
        out[f.name] = {
            "sha256": sha256_file(f),
            "size_bytes": f.stat().st_size,
            "mtime_iso": datetime.fromtimestamp(
                f.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
        }
    return out


def _pyg_to_dict_canonical(pyg) -> dict:
    """Selecciona campos representativos de PyGMensual para baseline.

    Excluye campos derivados (computables) para evitar drift.
    """
    return {
        "mes": pyg.mes,
        "rampup": round(pyg.rampup, 6),
        "payroll_a": round(pyg.payroll_a, 2),
        "no_payroll_a": round(pyg.no_payroll_a, 2),
        "costo_b": round(pyg.costo_b, 2),
        "costo_c": round(pyg.costo_c, 2),
        "polizas": round(pyg.polizas, 2),
        "ica": round(pyg.ica, 2),
        "gmf": round(pyg.gmf, 2),
        "financiacion": round(pyg.financiacion, 2),
        "ingreso_bruto_a": round(pyg.ingreso_bruto_a, 2),
        "ingreso_bruto_b": round(pyg.ingreso_bruto_b, 2),
        "ingreso_neto": round(pyg.ingreso_neto, 2),
        "pct_utilidad_neta": round(pyg.pct_utilidad_neta, 8),
    }


def run_canonical(case_name: str) -> dict:
    path = TEST_CASES / "input" / f"{case_name}.json"
    if not path.exists():
        return {"_error": f"Test case missing: {path}"}
    loader   = UserInputLoader()
    ui       = loader.cargar(path)
    solic    = SimulationContextBuilder().construir(ui)
    res      = NexaPricingEngine().calcular(solic)

    pyg_mensual = [_pyg_to_dict_canonical(p) for p in res.pyg_por_mes]

    return {
        "test_case_path": str(path.relative_to(BACKEND_ROOT)),
        "test_case_sha256": sha256_file(path),
        "panel": {
            "cliente": res.panel.cliente,
            "linea_negocio": res.panel.linea_negocio,
            "meses_contrato": res.panel.meses_contrato,
            "margen": res.panel.margen,
        },
        "kpis": {
            "ingreso_mensual": round(res.kpis.ingreso_mensual, 2),
            "facturacion_mensual_proyectada": round(res.kpis.facturacion_mensual_proyectada, 2),
            "ingreso_neto_total": round(res.kpis.ingreso_neto_total, 2),
            "costo_total_contrato": round(res.kpis.costo_total_contrato, 2),
            "utilidad_neta_total": round(res.kpis.utilidad_neta_total, 2),
            "pct_utilidad_neta_total": round(res.kpis.pct_utilidad_neta_total, 8),
            "cumple_margen_minimo": res.kpis.cumple_margen_minimo,
            "valor_total_deal": round(res.kpis.valor_total_deal, 2),
        },
        "cost_to_serve": {
            "cts_cadena_a": round(res.cost_to_serve.cts_cadena_a, 2),
            "cts_cadena_b": round(res.cost_to_serve.cts_cadena_b, 2),
            "cts_ponderado": round(res.cost_to_serve.cts_ponderado, 2),
            "fte_cadena_a": round(res.cost_to_serve.fte_cadena_a, 4),
            "vol_cadena_b": round(res.cost_to_serve.vol_cadena_b, 2),
        } if res.cost_to_serve else None,
        "vision_tarifas": {
            "canales": [
                {
                    "nombre": c.nombre_canal,
                    "fte": round(c.fte, 4),
                    "costo_atribuible": round(c.costo_atribuible, 2),
                    "tarifa_fijo_fte": round(c.tarifa_fijo_fte, 2),
                }
                for c in res.vision_tarifas.canales
            ]
        } if res.vision_tarifas else None,
        "pyg_por_mes": pyg_mensual,
    }


def generate(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    storage = collect_storage_checksums()
    excel   = collect_excel_fingerprint()

    baseline = {
        "generated_at": now_iso,
        "schema_version": "1.0",
        "description": "Baseline oficial congelado de outputs del motor NEXA. Cualquier cambio aquí debe ser intencional y revisado.",
        "scenarios": {name: run_canonical(name) for name in CANONICAL_CASES},
    }

    storage_doc = {
        "generated_at": now_iso,
        "schema_version": "1.0",
        "description": "Hash SHA256 de cada master JSON activo. Verificación de inmutabilidad de storage.",
        "files": storage,
    }

    excel_doc = {
        "generated_at": now_iso,
        "schema_version": "1.0",
        "description": "Fingerprint (SHA256 + size + mtime) de los Excel master. Detecta modificaciones al simulador.",
        "files": excel,
    }

    (output_dir / "baseline_oficial.json").write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2)
    )
    (output_dir / "storage_checksums.json").write_text(
        json.dumps(storage_doc, ensure_ascii=False, indent=2)
    )
    (output_dir / "excel_version_fingerprint.json").write_text(
        json.dumps(excel_doc, ensure_ascii=False, indent=2)
    )

    return {"baseline": baseline, "storage": storage_doc, "excel": excel_doc}


def verify(output_dir: Path) -> int:
    """Returns 0 on match, 1 on diff. Used for regression detection."""
    current = generate(output_dir.parent / "_tmp_baseline")
    existing_path = output_dir / "baseline_oficial.json"
    if not existing_path.exists():
        print(f"⚠ No baseline existente en {existing_path}. Generando uno nuevo.")
        generate(output_dir)
        return 0
    with open(existing_path) as f:
        existing = json.load(f)
    drifts = []
    for case, data in current["baseline"]["scenarios"].items():
        old = existing.get("scenarios", {}).get(case)
        if old is None:
            drifts.append(f"  + scenario nuevo: {case}")
            continue
        if old.get("kpis") != data.get("kpis"):
            drifts.append(f"  ! kpis cambió en {case}")
        if old.get("pyg_por_mes") != data.get("pyg_por_mes"):
            drifts.append(f"  ! pyg_por_mes cambió en {case}")
    if drifts:
        print("❌ DRIFT DETECTADO:")
        for d in drifts:
            print(d)
        return 1
    print("✅ Baseline match. Sin drift.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or verify NEXA baseline.")
    parser.add_argument("--verify", action="store_true", help="Verify against existing baseline.")
    args = parser.parse_args()

    if args.verify:
        return verify(REPORTS_DIR)

    out = generate(REPORTS_DIR)
    print(f"✅ Baseline generado en {REPORTS_DIR}/")
    print(f"   - baseline_oficial.json       ({len(out['baseline']['scenarios'])} escenarios)")
    print(f"   - storage_checksums.json      ({sum(len(d) for d in out['storage']['files'].values())} archivos)")
    print(f"   - excel_version_fingerprint.json ({len(out['excel']['files'])} excels)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
