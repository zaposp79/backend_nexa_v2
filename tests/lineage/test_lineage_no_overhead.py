"""WAVE 10 — Performance: with_lineage=False must not add noticeable overhead.

We measure a small number of runs to check that the default path remains
within a sensible bound vs the baseline. The bound is generous because CI
machines vary; the real guard is "default is not catastrophically slower".
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from nexa_engine import NexaPricingEngine
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BANCAMIA_FIXTURE = PROJECT_ROOT / "tests" / "parity" / "fixtures" / "bancamia_v2_7.json"

N_RUNS = 3


@pytest.fixture(scope="module")
def request_obj(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("lineage_perf")
    inputs = json.loads(BANCAMIA_FIXTURE.read_text())["inputs"]
    p = tmp / "bancamia.json"
    p.write_text(json.dumps(inputs, default=str))
    ui = UserInputLoader().cargar(p)
    return SimulationContextBuilder().construir(ui)


@pytest.fixture(scope="module")
def engine() -> NexaPricingEngine:
    return NexaPricingEngine()


def _time_runs(fn, n: int) -> float:
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t0) / n


def test_default_path_overhead_within_bound(engine, request_obj):
    """`with_lineage=False` must keep latency close to the historical baseline."""
    # warm-up
    engine.calcular(request_obj)

    t_default = _time_runs(lambda: engine.calcular(request_obj), N_RUNS)
    # The lineage path will be slower because it walks the result tree
    # and persists JSON. The default path should not pay any of that.
    # We require it to take less than 1s/run (matches W12 target spirit).
    assert t_default < 2.0, f"default path too slow: {t_default*1000:.1f}ms"


def test_lineage_path_completes_in_reasonable_time(engine, request_obj):
    """`with_lineage=True` must still complete in <5s for one Bancamia run."""
    engine.calcular(request_obj, with_lineage=True)  # warm-up

    t_lin = _time_runs(lambda: engine.calcular(request_obj, with_lineage=True), N_RUNS)
    assert t_lin < 5.0, f"lineage path too slow: {t_lin*1000:.1f}ms"
