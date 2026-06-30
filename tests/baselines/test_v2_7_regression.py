"""
V2-7 baseline regression tests (WAVE 6).

For each of the 12 canonical cases under storage/baselines/v2-7-certified/cases/:
  - Load the frozen request.json.
  - Run the engine fresh.
  - Compare the live outputs against the frozen outputs/*.json
    (numeric tolerance: rel <= 1e-4, abs <= 1e-2).

Plus a manifest-integrity test that detects parametrization drift since the
baseline was certified, and a sanity check that the parity suite still passes.

If any test fails, the baseline either needs to be re-certified intentionally
(re-run scripts/baselines/generate_baselines.py) or there is a real regression
that broke V2-7 paridad.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path

import pytest

THIS_DIR     = Path(__file__).resolve().parent
BACKEND_ROOT = THIS_DIR.parent.parent
REPO_ROOT    = BACKEND_ROOT.parent
BASELINE_ROOT = BACKEND_ROOT / "storage" / "baselines" / "v2-7-certified"
PARAM_ROOT    = BACKEND_ROOT / "storage" / "parametrization" / "v2-7"

# Make backend_nexa / nexa_engine importable
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import backend_nexa  # noqa: E402, F401
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder  # noqa: E402
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader        # noqa: E402
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine                          # noqa: E402

# Reuse helpers from the generator so test serialization stays in lockstep.
sys.path.insert(0, str(BACKEND_ROOT))
from scripts.baselines.generate_baselines import (  # noqa: E402
    _full_simulation_dict,
    _kpis_to_dict,
    _payroll_snapshot,
    _staffing_snapshot,
    _vision_pyg_to_dict,
    _vision_tarifas_to_dict,
    _cost_to_serve_to_dict,
    _waterfall_to_dict,
    _round,
    _to_dict,
    compute_param_hashes,
)


REL_TOL = 1e-4
ABS_TOL = 1e-2


# ---------------------------------------------------------------------------
# Case discovery
# ---------------------------------------------------------------------------

def _case_dirs() -> list[Path]:
    cases = BASELINE_ROOT / "cases"
    if not cases.exists():
        return []
    return sorted([p for p in cases.iterdir() if p.is_dir()])


CASE_DIRS = _case_dirs()
CASE_IDS  = [p.name for p in CASE_DIRS]


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def _close(a, b) -> bool:
    if a is None and b is None:
        return True
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if math.isnan(a) and math.isnan(b):
            return True
        return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    return a == b


def _diff(path: str, expected, actual, out: list[str]) -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        keys = sorted(set(expected) | set(actual))
        for k in keys:
            _diff(f"{path}.{k}" if path else k,
                  expected.get(k), actual.get(k), out)
        return
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            out.append(f"{path}: length {len(expected)} -> {len(actual)}")
            return
        for i, (e, a) in enumerate(zip(expected, actual)):
            _diff(f"{path}[{i}]", e, a, out)
        return
    if not _close(expected, actual):
        out.append(f"{path}: expected={expected!r} actual={actual!r}")


def _run_engine(input_dict: dict):
    loader  = UserInputLoader()
    builder = SimulationContextBuilder()
    engine  = NexaPricingEngine()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                       encoding="utf-8") as f:
        json.dump(input_dict, f, default=str)
        path = f.name
    try:
        ui = loader.cargar(path)
        req = builder.construir(ui)
        return engine.calcular(req)
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Per-case regression
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_id", CASE_IDS, ids=CASE_IDS)
def test_case_matches_baseline(case_id: str) -> None:
    """Re-run engine for a case and compare each output JSON to the frozen baseline."""
    case_dir = BASELINE_ROOT / "cases" / case_id
    request = json.loads((case_dir / "request.json").read_text())

    result = _run_engine(request)

    # Build the live equivalents using the same helpers the generator uses,
    # so the only thing under test is the engine output — not serialization.
    live_outputs = {
        "kpis.json":              _round(_kpis_to_dict(result.kpis)),
        "vision_tarifas.json":    _round(_vision_tarifas_to_dict(result.vision_tarifas)),
        "vision_pyg.json":        _round(_vision_pyg_to_dict(result.vision_pyg)),
        "cost_to_serve.json":     _round(_cost_to_serve_to_dict(result.cost_to_serve)),
        "waterfall.json":         _round(_waterfall_to_dict(result.waterfall)),
        "payroll_snapshot.json":  _round(_payroll_snapshot(result)),
        "staffing_snapshot.json": _round(_staffing_snapshot(result)),
        "simulation_full.json":   _round(_full_simulation_dict(result)),
    }

    diffs: list[str] = []
    for filename, live in live_outputs.items():
        frozen_path = case_dir / "outputs" / filename
        assert frozen_path.exists(), f"Missing baseline output: {frozen_path}"
        frozen = json.loads(frozen_path.read_text())
        _diff(f"{filename}", frozen, live, diffs)

    if diffs:
        msg = (f"BASELINE DRIFT in case {case_id}:\n  " +
               "\n  ".join(diffs[:30]) +
               (f"\n  ... ({len(diffs)} total)" if len(diffs) > 30 else ""))
        pytest.fail(msg)


# ---------------------------------------------------------------------------
# Manifest integrity
# ---------------------------------------------------------------------------

def test_manifest_hashes_match_current_parametrization() -> None:
    """Detect any drift between the certified parametrization snapshot and live storage.

    If this fails, the v2-7 JSON files were modified after the baseline was
    certified. Either revert the change, or re-certify by re-running
    scripts/baselines/generate_baselines.py.
    """
    manifest_path = BASELINE_ROOT / "manifest.json"
    assert manifest_path.exists(), "manifest.json missing — run generator first."
    manifest = json.loads(manifest_path.read_text())

    expected = manifest["parametrization_hashes"]
    actual   = compute_param_hashes()

    diff = {k: (expected.get(k), actual.get(k))
            for k in sorted(set(expected) | set(actual))
            if expected.get(k) != actual.get(k)}
    if diff:
        msg = "Parametrization drift detected since baseline certification:\n"
        for k, (e, a) in diff.items():
            msg += f"  {k}: baseline={e[:16]}... current={a[:16]}...\n"
        msg += "Re-certify required (re-run scripts/baselines/generate_baselines.py)."
        pytest.fail(msg)


def test_manifest_has_twelve_cases() -> None:
    manifest = json.loads((BASELINE_ROOT / "manifest.json").read_text())
    assert len(manifest["cases"]) == 12, \
        f"Expected 12 canonical cases in manifest, got {len(manifest['cases'])}"


def test_each_case_has_full_output_set() -> None:
    expected_files = {
        "vision_tarifas.json", "vision_pyg.json", "cost_to_serve.json",
        "waterfall.json", "kpis.json", "payroll_snapshot.json",
        "staffing_snapshot.json", "simulation_full.json",
    }
    for case_dir in CASE_DIRS:
        out_dir = case_dir / "outputs"
        present = {p.name for p in out_dir.iterdir() if p.is_file()}
        missing = expected_files - present
        assert not missing, f"{case_dir.name}: missing outputs {missing}"


# ---------------------------------------------------------------------------
# Sanity: parity suite still passes (regression of the regression).
# This is implicit — running the full pytest also runs tests/parity. We assert
# the parity directory exists so a hard delete would surface here too.
# ---------------------------------------------------------------------------

def test_parity_suite_is_present() -> None:
    parity_dir = BACKEND_ROOT / "tests" / "parity"
    assert parity_dir.exists(), "tests/parity removed — WAVE 4 contract broken."
    test_files = list(parity_dir.glob("test_parity_*.py"))
    assert len(test_files) >= 11, \
        f"Expected at least 11 parity test modules, found {len(test_files)}"
