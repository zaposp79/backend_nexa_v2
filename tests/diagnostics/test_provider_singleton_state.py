"""FASE R.2 — Singleton Contamination Diagnostic Test."""
import json, tempfile, os
import pytest
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[2] / "storage" / "baselines" / "v2-7-certified" / "cases" / "bancamia_full_chains_abc"

def _run_engine(provider=None):
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
    input_dict = json.loads((CASE_DIR / "request.json").read_text())
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(input_dict, tf, default=str); tmp = tf.name
    ui = UserInputLoader().cargar(tmp)
    builder = SimulationContextBuilder(provider=provider) if provider else SimulationContextBuilder()
    req = builder.construir(ui)
    engine = NexaPricingEngine(parametrizacion=provider) if provider else NexaPricingEngine()
    res = engine.calcular(req)
    os.unlink(tmp)
    return res

def _kv(res):
    return {
        "ingreso_mensual":         round(res.kpis.ingreso_mensual, 4),
        "costo_cadena_a_promedio": round(res.kpis.costo_cadena_a_promedio, 4),
        "contribucion_total":      round(res.kpis.contribucion_total, 4),
    }

def test_explicit_vs_singleton():
    """A (explicit provider) vs B (singleton) — must be identical."""
    from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
    res_A = _kv(_run_engine(provider=ParametrizationProvider.build()))
    res_B = _kv(_run_engine(provider=None))
    for k in res_A:
        assert res_A[k] == res_B[k], f"SINGLETON_CONTAMINATION: {k} A={res_A[k]} B={res_B[k]}"

def test_singleton_after_reset():
    """C (after singleton reset) must equal A (explicit)."""
    import nexa_engine.modules.parametrizacion.services.provider as pmod
    from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
    res_A = _kv(_run_engine(provider=ParametrizationProvider.build()))
    orig = pmod._PROVIDER_INSTANCE
    pmod._PROVIDER_INSTANCE = None
    res_C = _kv(_run_engine(provider=None))
    pmod._PROVIDER_INSTANCE = orig
    for k in res_A:
        assert res_A[k] == res_C[k], f"POST_RESET_DIVERGENCE: {k} A={res_A[k]} C={res_C[k]}"

def test_singleton_is_stable():
    """get_provider() returns same object on consecutive calls."""
    from nexa_engine.modules.parametrizacion.services.provider import get_provider
    p1, p2 = get_provider(), get_provider()
    assert id(p1) == id(p2), "get_provider() is NOT a singleton"
    print(f"\n  singleton id={id(p1)} class={p1.__class__.__module__}.{p1.__class__.__name__}")
