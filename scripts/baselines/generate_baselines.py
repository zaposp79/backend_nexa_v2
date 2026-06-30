"""
Generate the V2-7 certified baselines (WAVE 6).

For each canonical case in cases_definition.CASES this script:
  1. Writes request.json (the entry_data used as input).
  2. Runs NexaPricingEngine and captures all visions + KPIs.
  3. Serializes outputs to outputs/*.json (deterministic: sorted keys, rounded floats).
  4. Computes SHA-256 of each output JSON and writes checksums.json.
  5. Captures a snapshot of v2-7 parametrization SHA-256 hashes.
  6. Writes metadata.json (case_id, description, dimensions).

After all cases, writes the global manifest.json with parametrization hashes,
engine version, git SHA, and a summary table of every case + its output checksums.

Idempotent: two runs in a row produce byte-identical files (sorted keys, rounded
floats, no timestamps inside per-case outputs; the manifest carries a single
generated_at field).

Usage:
    cd backend_nexa
    source venv/bin/activate
    python scripts/baselines/generate_baselines.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make repo importable
SCRIPT_DIR  = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent.parent          # backend_nexa/
REPO_ROOT    = BACKEND_ROOT.parent               # NEXA/
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

import backend_nexa  # noqa: F401  (registers nexa_engine alias)
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine

from scripts.baselines.cases_definition import CASES

BASELINE_ROOT = BACKEND_ROOT / "storage" / "baselines" / "v2-7-certified"
PARAM_ROOT    = BACKEND_ROOT / "storage" / "parametrization" / "v2-7"

ROUND_DECIMALS = 6


# ----------------------------------------------------------------------------
# Serialization helpers (deterministic)
# ----------------------------------------------------------------------------

def _round(v: Any) -> Any:
    """Round floats to ROUND_DECIMALS, recursively. None / NaN / Inf → None."""
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, ROUND_DECIMALS)
    if isinstance(v, dict):
        return {k: _round(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_round(x) for x in v]
    return v


def _to_dict(obj: Any) -> Any:
    """Convert dataclasses recursively to dicts; pass-through primitives."""
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        return obj
    if is_dataclass(obj) and not isinstance(obj, type):
        return _to_dict(asdict(obj))
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(v) for v in obj]
    # Best-effort fallback (e.g. Enum)
    return str(obj)


def write_json(path: Path, data: Any) -> str:
    """Write data to path as canonical JSON, return its SHA-256 hex digest."""
    payload = _round(_to_dict(data))
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2,
                      separators=(",", ": "))
    blob_bytes = blob.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob_bytes)
    return hashlib.sha256(blob_bytes).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ----------------------------------------------------------------------------
# Result -> serializable dict mapping
# ----------------------------------------------------------------------------

def _kpis_to_dict(kpis) -> dict:
    return _to_dict(kpis)


def _vision_tarifas_to_dict(vt) -> dict:
    if vt is None:
        return {}
    return _to_dict(vt)


def _cost_to_serve_to_dict(cts) -> dict:
    if cts is None:
        return {}
    return _to_dict(cts)


def _waterfall_to_dict(wf) -> dict:
    if wf is None:
        return {}
    return _to_dict(wf)


def _vision_pyg_to_dict(vp) -> dict:
    if vp is None:
        return {}
    return _to_dict(vp)


def _payroll_snapshot(result) -> dict:
    """Synthetic snapshot: per-month payroll_a + no_payroll_a + costo_b/c."""
    return {
        "meses": [
            {
                "mes":          m.mes,
                "rampup":       m.rampup,
                "payroll_a":    m.payroll_a,
                "no_payroll_a": m.no_payroll_a,
                "costo_b":      m.costo_b,
                "costo_c":      m.costo_c,
            }
            for m in result.pyg_por_mes
        ],
        "total_payroll_a":    sum(m.payroll_a for m in result.pyg_por_mes),
        "total_no_payroll_a": sum(m.no_payroll_a for m in result.pyg_por_mes),
        "total_costo_b":      sum(m.costo_b for m in result.pyg_por_mes),
        "total_costo_c":      sum(m.costo_c for m in result.pyg_por_mes),
    }


def _staffing_snapshot(result) -> dict:
    """Synthetic snapshot: panel + perfiles + counts."""
    panel = result.panel
    perfiles = []
    try:
        for p in panel.condiciones_cadena_a.perfiles:
            perfiles.append({
                "nombre":       p.nombre,
                "rol":          getattr(p, "rol", ""),
                "modalidad":    p.modalidad,
                "canal":        p.canal,
                "fte":          p.fte,
                "modelo_cobro": getattr(p, "modelo_cobro", ""),
                "pct_fijo":     getattr(p, "pct_fijo", 1.0),
            })
    except Exception:
        pass
    return {
        "meses_contrato": panel.meses_contrato,
        "linea_negocio":  panel.linea_negocio,
        "perfiles":       perfiles,
        "total_fte":      sum(p.get("fte", 0.0) for p in perfiles),
        "cadenas_activas": _to_dict(panel.cadenas_activas),
    }


def _full_simulation_dict(result) -> dict:
    """Full serialized simulation for forensic comparison."""
    return {
        "kpis":           _kpis_to_dict(result.kpis),
        "pyg_por_mes":    [_to_dict(m) for m in result.pyg_por_mes],
        "vision_tarifas": _vision_tarifas_to_dict(result.vision_tarifas),
        "cost_to_serve":  _cost_to_serve_to_dict(result.cost_to_serve),
        "waterfall":      _waterfall_to_dict(result.waterfall),
        "vision_pyg":     _vision_pyg_to_dict(result.vision_pyg),
        "reglas_negocio": [_to_dict(r) for r in (result.reglas_negocio or [])],
        "evaluacion_riesgo": _to_dict(result.evaluacion_riesgo)
                              if result.evaluacion_riesgo else None,
    }


# ----------------------------------------------------------------------------
# Engine runner
# ----------------------------------------------------------------------------

def run_engine(input_dict: dict):
    """Materialize input via tmp file, then load+build+calculate."""
    loader  = UserInputLoader()
    builder = SimulationContextBuilder()
    engine  = NexaPricingEngine()

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                       encoding="utf-8") as f:
        json.dump(input_dict, f, default=str)
        tmp_path = f.name
    try:
        ui  = loader.cargar(tmp_path)
        req = builder.construir(ui)
        return engine.calcular(req)
    finally:
        os.unlink(tmp_path)


# ----------------------------------------------------------------------------
# Per-case generation
# ----------------------------------------------------------------------------

def generate_case(case: dict) -> dict:
    case_id = case["case_id"]
    case_dir = BASELINE_ROOT / "cases" / case_id
    outputs_dir = case_dir / "outputs"

    print(f"  [{case_id}] running engine...", flush=True)
    result = run_engine(case["request"])

    # Per-output files
    out_files: dict[str, str] = {}
    out_files["vision_tarifas.json"]   = write_json(outputs_dir / "vision_tarifas.json",
                                                      _vision_tarifas_to_dict(result.vision_tarifas))
    out_files["vision_pyg.json"]       = write_json(outputs_dir / "vision_pyg.json",
                                                      _vision_pyg_to_dict(result.vision_pyg))
    out_files["cost_to_serve.json"]    = write_json(outputs_dir / "cost_to_serve.json",
                                                      _cost_to_serve_to_dict(result.cost_to_serve))
    out_files["waterfall.json"]        = write_json(outputs_dir / "waterfall.json",
                                                      _waterfall_to_dict(result.waterfall))
    out_files["kpis.json"]             = write_json(outputs_dir / "kpis.json",
                                                      _kpis_to_dict(result.kpis))
    out_files["payroll_snapshot.json"] = write_json(outputs_dir / "payroll_snapshot.json",
                                                      _payroll_snapshot(result))
    out_files["staffing_snapshot.json"] = write_json(outputs_dir / "staffing_snapshot.json",
                                                       _staffing_snapshot(result))
    out_files["simulation_full.json"]  = write_json(outputs_dir / "simulation_full.json",
                                                      _full_simulation_dict(result))

    # request.json
    request_sha = write_json(case_dir / "request.json", case["request"])

    # checksums.json
    write_json(case_dir / "checksums.json", out_files)

    # metadata.json
    meta = {
        "case_id":     case_id,
        "description": case["description"],
        "dimensions":  case["dimensions"],
    }
    write_json(case_dir / "metadata.json", meta)

    # parametrization snapshot (per-case: hashes only — files live in v2-7/)
    write_json(case_dir / "parametrization_snapshot.json",
               compute_param_hashes())

    return {
        "case_id":      case_id,
        "request_sha":  request_sha,
        "outputs":      out_files,
        "description":  case["description"],
        "dimensions":   case["dimensions"],
    }


# ----------------------------------------------------------------------------
# Parametrization hashing
# ----------------------------------------------------------------------------

def compute_param_hashes() -> dict[str, str]:
    """SHA-256 of v2-7 parametrization files (read as canonicalized JSON bytes)."""
    out: dict[str, str] = {}
    for name in ("hr.json", "gn.json", "op.json"):
        f = PARAM_ROOT / name
        if not f.exists():
            out[name.replace(".json", "")] = "MISSING"
            continue
        # Hash a canonicalized re-serialization so reordering keys in the
        # source file doesn't shift the hash. This makes the hash content-based.
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            blob = json.dumps(data, sort_keys=True, ensure_ascii=False,
                              separators=(",", ":")).encode("utf-8")
            out[name.replace(".json", "")] = hashlib.sha256(blob).hexdigest()
        except Exception:
            out[name.replace(".json", "")] = sha256_file(f)
    return out


def get_git_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=BACKEND_ROOT,
            capture_output=True, text=True, check=False,
        )
        return r.stdout.strip() or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main() -> int:
    print(f"Generating V2-7 certified baselines into: {BASELINE_ROOT}", flush=True)
    BASELINE_ROOT.mkdir(parents=True, exist_ok=True)

    summaries: list[dict] = []
    for case in CASES:
        summaries.append(generate_case(case))

    param_hashes = compute_param_hashes()
    git_sha      = get_git_sha()

    manifest = {
        "baseline_version":   "v2-7-certified",
        "generated_at":       datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "engine_version":     "engine-v2-post-wave5",
        "git_sha":            git_sha,
        "excel_version":      "V2-7",
        "checksum_algorithm": "sha256",
        "tolerance_policy":   "exact_match_for_baseline_drift_detection",
        "parametrization_hashes": param_hashes,
        "cases": [
            {
                "case_id":     s["case_id"],
                "description": s["description"],
                "dimensions":  s["dimensions"],
                "request_sha": s["request_sha"],
                "outputs":     s["outputs"],
            }
            for s in summaries
        ],
    }
    write_json(BASELINE_ROOT / "manifest.json", manifest)

    print(f"\nGenerated {len(summaries)} cases. SHA-256 of simulation_full.json per case:")
    for s in summaries:
        print(f"  {s['case_id']:<35s} {s['outputs']['simulation_full.json'][:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
