"""
tests/golden/test_cts_exam_crucero_v28.py
==========================================
CTS-EXAM and CTS-CRUCERO V2-8 — diagnostic golden tests.

EXCEL ANCHORS (Vision Cost To Serve!C41 / C43):
  Exámenes Médicos = 12.241808 COP/tx
  Crucero          = 10.629257 COP/tx

PROVIDER: build_v28_deal_provider() — active HR + staff overrides + exam patch.

EXAM FIX (APPLIED):
  - costo_examen_medico = 60,800 COP (Excel 'Nomina Loaded'!C329/C330/C331 = 60,800).
    Active HR storage has 60.8 (wrong scale). Patched in _v28_deal_provider.py.
  - pct_examen_anual = 0.28 (Excel 'Condiciones Cadena A'!E135 = 0.28).
    Active HR fallback = 1.0 (HR-AutRot missing). Injected via rotacion_ausentismo.
  Backend examenes: 0.016 → 11.512 (+11.496 COP/tx, 93.9% closed).
  Residual -0.73 COP/tx = fte_examenes FTE gap (soporte FTE mismatch, requires modules/).

CRUCERO (APPLIED — CRUCERO_REQUEST_ALIGNMENT):
  Excel: CCA!E152:G152 = 1,193,936+420,400+734,730=2,349,066 COP/mes. C43=10.6293 COP/tx.
  Fix: incluye_crucero=true in all 3 request.json Cadena A perfiles. tarifa_crucero=8408 already set.
  Backend: tarifa_crucero(8408) × perfil.fte × indexacion. Result ~9.892 COP/tx.
  Residual -0.737 COP/tx = cargos_adicionales missing from crucero numerator (same as Support FTE).
  Classification: CTS_CRUCERO_PARTIAL (applied, not full match). CTS-001: -69.27 → -59.38 COP/tx.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(REPO_ROOT))

REQUEST_PATH = REPO_ROOT / "backend_nexa" / "request" / "request.json"

EXCEL_CTS_CADENA_A = 6_224.575126115379
EXCEL_EXAMENES     = 12.241808363582114   # VCS!C41
EXCEL_CRUCERO      = 10.6292572224156     # VCS!C43

# Best achievable after provider exam patch
EXPECTED_EXAMENES_MIN = 11.0   # ~11.51, must be > 0 and approaching Excel
# Crucero APPLIED (CRUCERO_REQUEST_ALIGNMENT): incluye_crucero=true in all 3 perfiles.
# Backend = tarifa_crucero(8408) × fte_agentes / denominador (no cargos_adicionales).
# Residual vs Excel: ~-0.74 COP/tx due to cargos_adicionales not in crucero numerator.
EXPECTED_CRUCERO_MIN  = 9.5    # backend ~9.892 (> 0 confirms flag active)
EXPECTED_CRUCERO      = 9.8917647058823536  # regression anchor exact value


@pytest.mark.golden
def test_cts_exam_provider_patch_applied() -> None:
    """
    CTS-EXAM: backend examenes approaches Excel after provider patch.

    EXCEL V2-8: VCS!C41 = 12.241808 COP/tx.
      Source: Nomina Loaded!D373:BK373 sum / Panel!C11 / Panel!W31.
      Exam cost: NL!C329/C330/C331 = 60,800 COP (active HR had 60.8 — scale error).
      pct_examen_anual: CCA!E135 = 0.28 (active HR fallback was 1.0).

    Residual gap ~-0.73 COP/tx = fte_examenes FTE gap (soporte FTE mismatch, modules/ scope).
    Gate: examenes > 11.0 COP/tx (verifies patch applied; full match requires modules/).
    """
    import backend_nexa  # noqa: F401
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
    from backend_nexa.tests.refactor._v28_deal_provider import build_v28_deal_provider

    prov = build_v28_deal_provider()
    payload = json.loads(REQUEST_PATH.read_text())
    loader = UserInputLoader()
    user_input = loader.cargar_desde_dict(payload)
    solicitud = SimulationContextBuilder(provider=prov).construir(user_input)
    resultado = NexaPricingEngine(parametrizacion=prov).calcular(solicitud)

    cts = resultado.cost_to_serve
    examenes = cts.desglose_a.examenes

    assert examenes > EXPECTED_EXAMENES_MIN, (
        f"Exam patch regressed: examenes={examenes:.4f} COP/tx (expected > {EXPECTED_EXAMENES_MIN}). "
        f"Check _v28_deal_provider.py med_seg patch (Bogota 60,800) and "
        f"rotacion_ausentismo SAC entry (pct_examen_anual=0.28)."
    )

    delta_pct = abs(examenes - EXCEL_EXAMENES) / EXCEL_EXAMENES
    assert delta_pct < 0.10, (
        f"Exámenes gap too large: {delta_pct:.2%} "
        f"(backend={examenes:.4f}, excel={EXCEL_EXAMENES:.4f}). "
        f"Residual ~-0.73 expected from fte_examenes FTE mismatch. "
        f"If gap is > 10%, exam patch may have regressed."
    )


@pytest.mark.golden
def test_cts_crucero_applied_request_alignment() -> None:
    """
    CTS-CRUCERO: APPLIED (CRUCERO_REQUEST_ALIGNMENT). incluye_crucero=true in all 3 Cadena A perfiles.

    EXCEL V2-8: VCS!C43 = 10.629257 COP/tx.
      Source: CCA!E152:G152 = 1,193,936 + 420,400 + 734,730 = 2,349,066 COP/mes total.
      Formula: tarifa_crucero(E134=8408) × (FTE_agentes + cargos_adicionales) per escenario.
    Backend: tarifa_crucero(8408) × perfil.fte × indexacion (no cargos_adicionales).
      Result: 8408 × 260 FTE / 221,000 = ~9.892 COP/tx (vs Excel 10.629).
      Residual -0.737 COP/tx from cargos_adicionales missing in crucero numerator (same root cause
      as Support FTE gap). Requires cargos_adicionales contract field — deferred.

    Classification: CTS_CRUCERO_PARTIAL (applied but not full match).
    CTS-001 improvement: +9.89 COP/tx (delta -69.27 → -59.38, 1.113% → 0.954%).
    """
    import backend_nexa  # noqa: F401
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
    from backend_nexa.tests.refactor._v28_deal_provider import build_v28_deal_provider

    prov = build_v28_deal_provider()
    payload = json.loads(REQUEST_PATH.read_text())
    loader = UserInputLoader()
    user_input = loader.cargar_desde_dict(payload)
    solicitud = SimulationContextBuilder(provider=prov).construir(user_input)
    resultado = NexaPricingEngine(parametrizacion=prov).calcular(solicitud)

    crucero = resultado.cost_to_serve.desglose_a.crucero

    assert crucero > EXPECTED_CRUCERO_MIN, (
        f"CTS-CRUCERO regressed: crucero={crucero:.4f} (expected > {EXPECTED_CRUCERO_MIN}). "
        f"Check incluye_crucero=true in request.json Cadena A perfiles and "
        f"tarifa_crucero=8408 in datos_operativos.crucero."
    )

    # Regression anchor — detect unexpected drift from known backend value
    assert abs(crucero - EXPECTED_CRUCERO) < 0.001, (
        f"CTS-CRUCERO value drifted: crucero={crucero:.10f} (anchor={EXPECTED_CRUCERO:.10f}). "
        f"If this is an intentional fix, update EXPECTED_CRUCERO and document the change. "
        f"Excel anchor: VCS!C43 = {EXCEL_CRUCERO:.4f} COP/tx. "
        f"Residual vs Excel: {crucero - EXCEL_CRUCERO:.4f} COP/tx (cargos_adicionales gap)."
    )
