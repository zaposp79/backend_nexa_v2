"""
FASE R — Oracle Regression Root Cause Analysis
================================================
Diagnostic script to identify why moving a Python file produces numerical
changes in Oracle C40-C47 results.

Usage:
    # Step 1: capture state BEFORE moving any file
    python scripts/diagnose_oracle_regression.py --phase baseline

    # Step 2: move the candidate file (manually or git mv)

    # Step 3: capture state AFTER the move
    python scripts/diagnose_oracle_regression.py --phase after

    # Step 4: compare
    python scripts/diagnose_oracle_regression.py --phase compare

Key finding from initial investigation (FASE R):
    The 13 baseline test failures exist at P12 (pre-refactoring) and are
    PART OF the 56 pre-existing failures in the gate baseline.
    They are NOT introduced by file moves.
    Confirmed by running tests against P12 commit: same 13 failures.

Remaining open question:
    When Batch C (provider.py + profitability_repo moves) was applied,
    the hash mismatch failure appeared. That specific failure
    (test_manifest_hashes_match_current_parametrization) changed from
    pre-existing to "new failure pattern" — still under investigation.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import logging
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.WARNING)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT   = Path(__file__).resolve().parent.parent   # backend_nexa/
PARENT_ROOT = REPO_ROOT.parent                          # NEXA/

# Register nexa_engine alias
if str(PARENT_ROOT) not in sys.path:
    sys.path.insert(0, str(PARENT_ROOT))
try:
    import backend_nexa  # noqa: F401 — registers nexa_engine alias
except ImportError:
    pass

SNAPSHOT_DIR   = REPO_ROOT / "scripts" / "_regression_snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
CASE_DIR       = REPO_ROOT / "storage" / "baselines" / "v2-7-certified" / "cases" / "bancamia_full_chains_abc"
INPUT_FILE     = CASE_DIR / "request.json"
FROZEN_KPI     = CASE_DIR / "outputs" / "kpis.json"

# Modules to watch
WATCHED_MODULES = [
    "nexa_engine.modules.calculator_motor.context_builder",
    "nexa_engine.modules.calculator_motor.context_builder_methods",
    "nexa_engine.modules.calculator_motor.engine",
    "nexa_engine.modules.parametrizacion.provider",
    "nexa_engine.modules.parametrizacion.provider_fin_op",
    "nexa_engine.modules.parametrizacion.profitability_parametrization_repository",
    "nexa_engine.modules.parametrizacion.financial_parametrization_repository",
    "nexa_engine.modules.parametrizacion.payroll_parametrization_repository",
    "nexa_engine.modules.parametrizacion.resolver",
    "nexa_engine.modules.vision_tarifas.reglas",
    "nexa_engine.modules.vision_tarifas.reglas_methods",
]

WATCHED_CLASSES = [
    ("nexa_engine.modules.calculator_motor.context_builder", "SimulationContextBuilder"),
    ("nexa_engine.modules.calculator_motor.engine", "NexaPricingEngine"),
    ("nexa_engine.modules.parametrizacion.provider", "ParametrizationProvider"),
    ("nexa_engine.modules.shared.ports.parametrization_provider", "IParametrizationProvider"),
    ("nexa_engine.modules.vision_tarifas.reglas", "VisionTarifasCalculator"),
]


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------

def probe_modules() -> Dict[str, Any]:
    snap: Dict[str, Any] = {}
    for mod_name in WATCHED_MODULES:
        mod = sys.modules.get(mod_name)
        snap[mod_name] = {
            "loaded": mod is not None,
            "file":   getattr(mod, "__file__", None) if mod else None,
            "id":     id(mod) if mod else None,
        }
    return snap


def probe_classes() -> Dict[str, Any]:
    snap: Dict[str, Any] = {}
    for mod_name, cls_name in WATCHED_CLASSES:
        mod = sys.modules.get(mod_name)
        if mod:
            cls = getattr(mod, cls_name, None)
            if cls:
                snap[f"{mod_name}.{cls_name}"] = {
                    "id": id(cls),
                    "module": getattr(cls, "__module__", None),
                    "mro_ids": [id(c) for c in cls.__mro__],
                    "mro_names": [f"{c.__module__}.{c.__qualname__}" for c in cls.__mro__],
                }
    return snap


def probe_provider_singleton() -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    try:
        import nexa_engine.modules.parametrizacion.services.provider as pmod
        inst = getattr(pmod, "_PROVIDER_INSTANCE", None)
        result["singleton_present"] = inst is not None
        result["singleton_id"] = id(inst) if inst else None
        if inst:
            try: result["tasa_financiacion"] = inst.tasa_mensual_financiacion
            except Exception as e: result["tasa_financiacion"] = f"ERR:{e}"
            try: result["gmf"] = inst.get_gmf()
            except Exception as e: result["gmf"] = f"ERR:{e}"
            try: result["margen_cobranzas"] = inst.get_margen_minimo("Cobranzas")
            except Exception as e: result["margen_cobranzas"] = f"ERR:{e}"
            try: result["rampup_cobranzas_m1"] = inst.get_rampup("Cobranzas", 1)
            except Exception as e: result["rampup_cobranzas_m1"] = f"ERR:{e}"
    except Exception as e:
        result["error"] = str(e)
    return result


def probe_file_hashes() -> Dict[str, Any]:
    """Check if any __file__ references resolve to unexpected locations."""
    result: Dict[str, Any] = {}
    for mod_name in WATCHED_MODULES:
        mod = sys.modules.get(mod_name)
        if not mod: continue
        f = getattr(mod, "__file__", None)
        if f:
            # Does the file contain __file__-relative paths?
            try:
                text = Path(f).read_text(errors="ignore")
                tree = ast.parse(text)
                file_refs = [n.lineno for n in ast.walk(tree)
                             if isinstance(n, ast.Name) and n.id == "__file__"]
                if file_refs:
                    result[mod_name] = {"lines": file_refs, "file": f}
            except Exception:
                pass
    return result


def run_oracle() -> Dict[str, Any]:
    """Run pricing engine on bancamia test case and return Oracle values."""
    result: Dict[str, Any] = {"success": False, "values": {}, "param_used": {}}

    if not INPUT_FILE.exists():
        result["error"] = f"Missing: {INPUT_FILE}"
        return result

    # Load frozen expected values for comparison
    frozen: Dict[str, Any] = {}
    if FROZEN_KPI.exists():
        try:
            frozen = json.loads(FROZEN_KPI.read_text())
        except Exception:
            pass
    result["frozen_kpis"] = {
        k: frozen.get(k) for k in [
            "costo_cadena_a_promedio", "ingreso_mensual",
            "contribucion_total", "pct_utilidad_neta_total"
        ]
    }

    try:
        from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
        from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
        from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider

        # Build fresh provider (no singleton) for reproducibility
        provider = ParametrizationProvider.build()
        result["param_used"]["provider_id"] = id(provider)
        result["param_used"]["tasa_financiacion"] = provider.tasa_mensual_financiacion
        result["param_used"]["gmf"] = provider.get_gmf()
        result["param_used"]["margen_cobranzas"] = provider.get_margen_minimo("Cobranzas")
        result["param_used"]["rampup_cobranzas_m1"] = provider.get_rampup("Cobranzas", 1)

        if hasattr(provider, "_profitability"):
            result["param_used"]["profitability_repo_id"] = id(provider._profitability)
        if hasattr(provider, "_financial"):
            result["param_used"]["financial_repo_id"] = id(provider._financial)

        input_dict = json.loads(INPUT_FILE.read_text())
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump(input_dict, tf, default=str)
            tmp_path = tf.name

        import os
        loader = UserInputLoader()
        ui = loader.cargar(tmp_path)
        builder = SimulationContextBuilder(provider=provider)
        req = builder.construir(ui)
        engine = NexaPricingEngine(parametrizacion=provider)
        res = engine.calcular(req)
        os.unlink(tmp_path)

        kpis = res.kpis
        vt   = res.vision_tarifas
        pyg  = res.pyg_por_mes

        result["values"] = {
            "ingreso_mensual":          round(kpis.ingreso_mensual, 4),
            "costo_mensual_promedio":   round(kpis.costo_mensual_promedio, 4),
            "costo_cadena_a_promedio":  round(kpis.costo_cadena_a_promedio, 4),
            "contribucion_total":       round(kpis.contribucion_total, 4),
            "pct_utilidad_neta_total":  round(kpis.pct_utilidad_neta_total, 6),
            "vt_costo_cadena_a_total":  round(vt.costo_cadena_a_total, 4) if vt else None,
            "vt_costo_total":           round(vt.costo_total, 4) if vt else None,
            "vt_ingreso_mensual":       round(vt.ingreso_mensual, 4) if vt else None,
            "pyg_m1_payroll_a":         round(pyg[0].payroll_a, 4) if pyg else None,
            "pyg_m1_ingreso_bruto":     round(pyg[0].ingreso_bruto, 4) if pyg else None,
            "pyg_m1_costo_total":       round(pyg[0].costo_total, 4) if pyg else None,
        }

        # Δ vs frozen
        if frozen:
            result["delta_vs_frozen"] = {}
            for k, actual in result["values"].items():
                expected = frozen.get(k)
                if expected is not None and isinstance(actual, (int, float)):
                    pct = (actual - expected) / abs(expected) * 100 if expected != 0 else None
                    result["delta_vs_frozen"][k] = {
                        "expected": expected, "actual": actual,
                        "pct": round(pct, 4) if pct is not None else None,
                        "match": abs(pct) < 0.001 if pct is not None else False
                    }

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()

    return result


# ---------------------------------------------------------------------------
# Full diagnostic snapshot
# ---------------------------------------------------------------------------

def full_snapshot(label: str) -> Dict[str, Any]:
    print(f"\n[FASE R] Snapshot: {label}")

    # Force imports
    try:
        import nexa_engine.modules.calculator_motor.context_builder
        import nexa_engine.modules.calculator_motor.engine
        import nexa_engine.modules.parametrizacion.provider
        import nexa_engine.modules.vision_tarifas.reglas
        print("  imports: OK")
    except Exception as e:
        print(f"  imports: ERROR {e}")

    snap: Dict[str, Any] = {"label": label}
    snap["modules"]   = probe_modules()
    snap["classes"]   = probe_classes()
    snap["singleton"] = probe_provider_singleton()
    snap["file_refs"] = probe_file_hashes()
    print("  probes: OK")

    print("  oracle: running...", end=" ", flush=True)
    snap["oracle"] = run_oracle()
    print("OK" if snap["oracle"]["success"] else f"ERROR: {snap['oracle'].get('error','?')}")

    return snap


def save(snap: Dict, name: str) -> Path:
    p = SNAPSHOT_DIR / f"{name}.json"
    p.write_text(json.dumps(snap, indent=2, default=str))
    return p


def load(name: str) -> Optional[Dict]:
    p = SNAPSHOT_DIR / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare(before: Dict, after: Dict) -> None:
    print("\n" + "=" * 65)
    print("FASE R — DIFF REPORT")
    print("=" * 65)

    # Oracle Δ
    bv = before.get("oracle", {}).get("values", {})
    av = after.get("oracle", {}).get("values", {})
    bf = before.get("oracle", {}).get("frozen_kpis", {})

    print("\n── Oracle Values ──────────────────────────────────────────────")
    print(f"  {'Key':<38} {'Before':>16} {'After':>16} {'Δ%':>8}")
    print("  " + "-" * 80)
    changed_oracle = []
    for k in sorted(set(list(bv) + list(av))):
        b = bv.get(k, "N/A"); a = av.get(k, "N/A")
        pct = ""
        if isinstance(b, (int, float)) and isinstance(a, (int, float)) and b != 0:
            pct_val = (a - b) / abs(b) * 100
            pct = f"{pct_val:+.2f}%"
            if abs(pct_val) > 0.01:
                changed_oracle.append(k)
        tag = " ◀ CHANGED" if b != a else ""
        # Also show vs frozen
        frozen_v = bf.get(k, "")
        print(f"  {k:<38} {str(b):>16} {str(a):>16} {pct:>8}{tag}")
        if frozen_v:
            print(f"    frozen expected: {frozen_v}")

    # Structural diffs
    structural: List[str] = []

    # Module file paths
    bm = before.get("modules", {}); am = after.get("modules", {})
    for mod in WATCHED_MODULES:
        if bm.get(mod, {}).get("file") != am.get(mod, {}).get("file"):
            structural.append(f"MODULE_PATH: {mod}")
            print(f"\n  ◀ MODULE PATH CHANGED: {mod}")
            print(f"    before: {bm.get(mod,{}).get('file')}")
            print(f"    after:  {am.get(mod,{}).get('file')}")

    # Class identity + MRO
    bc = before.get("classes", {}); ac = after.get("classes", {})
    for cls_key in set(list(bc) + list(ac)):
        if bc.get(cls_key, {}).get("id") != ac.get(cls_key, {}).get("id"):
            structural.append(f"CLASS_ID: {cls_key}")
            print(f"\n  ◀ CLASS IDENTITY CHANGED: {cls_key}")
        if bc.get(cls_key, {}).get("mro_names") != ac.get(cls_key, {}).get("mro_names"):
            structural.append(f"MRO: {cls_key}")
            print(f"\n  ◀ MRO CHANGED: {cls_key}")
            bmro = bc.get(cls_key, {}).get("mro_names", [])
            amro = ac.get(cls_key, {}).get("mro_names", [])
            for i, (bm_item, am_item) in enumerate(zip(bmro, amro)):
                if bm_item != am_item:
                    print(f"    mro[{i}] before: {bm_item}")
                    print(f"    mro[{i}] after:  {am_item}")

    # Singleton
    bs = before.get("singleton", {}); as_ = after.get("singleton", {})
    for k in ["tasa_financiacion", "gmf", "margen_cobranzas", "rampup_cobranzas_m1"]:
        if bs.get(k) != as_.get(k):
            structural.append(f"SINGLETON: {k}")
            print(f"\n  ◀ SINGLETON CHANGED: {k}")
            print(f"    before: {bs.get(k)}  after: {as_.get(k)}")

    # Provider param
    bp = before.get("oracle", {}).get("param_used", {})
    ap = after.get("oracle", {}).get("param_used", {})
    for k in ["tasa_financiacion", "gmf", "margen_cobranzas", "rampup_cobranzas_m1"]:
        if bp.get(k) != ap.get(k):
            structural.append(f"PARAM: {k}")
            print(f"\n  ◀ PARAMETRIZATION USED CHANGED: {k}")
            print(f"    before: {bp.get(k)}  after: {ap.get(k)}")

    # New __file__ references introduced
    bfr = before.get("file_refs", {}); afr = after.get("file_refs", {})
    new_file_refs = set(afr) - set(bfr)
    if new_file_refs:
        structural.append(f"NEW_FILE_REFS: {new_file_refs}")
        print(f"\n  ◀ NEW __file__ REFS INTRODUCED: {new_file_refs}")

    # Conclusion
    print("\n── CONCLUSIÓN ─────────────────────────────────────────────────")
    if not changed_oracle and not structural:
        print("  Oracle: SIN DIFERENCIAS.")
        print("  El movimiento no afecta resultados numéricos.")
    elif changed_oracle and structural:
        print(f"  Oracle: {len(changed_oracle)} valores cambiaron.")
        print(f"  Cambios estructurales detectados: {structural[:3]}")
        print(f"\n  HIPÓTESIS CANDIDATA (no confirmada):")
        print(f"    El cambio en {structural[0]} podría explicar el Δ Oracle.")
        print(f"    Para confirmar: verificar que el structural diff")
        print(f"    ocurre ANTES de la primera divergencia en la cadena.")
    elif changed_oracle and not structural:
        print(f"  Oracle: {len(changed_oracle)} valores cambiaron.")
        print("  Sin cambios estructurales detectados por estos probes.")
        print("\n  CAUSA RAÍZ: NO IDENTIFICADA con los probes actuales.")
        print("  Sugerencias para FASE R.2:")
        print("    1. Agregar probes dentro de SimulationContextBuilder._construir_panel")
        print("    2. Agregar probes dentro de VisionTarifasCalculator.calcular")
        print("    3. Verificar si algún .pyc stale está siendo cargado")
        print("    4. Comparar id() de los métodos de instancia, no solo de las clases")
    elif structural and not changed_oracle:
        print("  Oracle: sin diferencias.")
        print(f"  Cambios estructurales: {structural} — sin efecto numérico.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="FASE R diagnostic")
    ap.add_argument("--phase",
                    choices=["baseline", "after", "compare", "state"],
                    default="baseline")
    ap.add_argument("--label", default=None)
    args = ap.parse_args()

    if args.phase == "state":
        for mod_name in WATCHED_MODULES:
            mod = sys.modules.get(mod_name)
            status = f"LOADED  {getattr(mod,'__file__','?')}" if mod else "NOT_LOADED"
            print(f"  {mod_name}: {status}")
        return

    if args.phase in ("baseline", "after"):
        label = args.label or args.phase
        snap = full_snapshot(label)
        path = save(snap, label)
        print(f"  Saved: {path}")

        oracle = snap["oracle"]
        if oracle["success"]:
            vals = oracle["values"]
            deltas = oracle.get("delta_vs_frozen", {})
            print(f"\n  Oracle summary ({label}):")
            for k in ["costo_cadena_a_promedio", "vt_costo_cadena_a_total", "ingreso_mensual"]:
                actual = vals.get(k, "N/A")
                d = deltas.get(k, {})
                expected = d.get("expected", "?")
                pct = d.get("pct")
                match = "✓" if d.get("match") else "✗" if "match" in d else ""
                pct_s = f"Δ{pct:+.2f}%" if pct is not None else ""
                print(f"    {k}: {actual} (frozen={expected} {pct_s}) {match}")
        else:
            print(f"  Oracle ERROR: {oracle.get('error','?')}")

    elif args.phase == "compare":
        bl = load("baseline")
        af = load(args.label or "after")
        if bl is None or af is None:
            print("ERROR: Run --phase baseline and --phase after first.")
            return
        compare(bl, af)
        diff_report = SNAPSHOT_DIR / "diff_report.json"
        diff_report.write_text(json.dumps({"bl": bl.get("label"), "af": af.get("label")},
                                          indent=2))


if __name__ == "__main__":
    main()
