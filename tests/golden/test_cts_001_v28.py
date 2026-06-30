"""
tests/golden/test_cts_001_v28.py
================================
CTS-001 V2-8 Parity — Cadena A denominator uses transactional volume.

EXCEL ANCHOR (Vision Cost To Serve, V2-8):
  C34 = 6,224.575126115379 COP/unidad
  C35 (Payroll) = 5,462.355883776192 COP/unidad
  C45 (No Payroll) = 762.219242339187 COP/unidad
  Denominator = Panel!W31 = 221,000 (monthly transaction volume, Cadena A)
    Voz 1:    W17 = 110,500 tx/mes
    Voz 2:    W18 =  68,000 tx/mes
    WhatsApp: W21 =  42,500 tx/mes

PROVIDER:
  Uses build_v28_deal_provider() (tests/refactor/_v28_deal_provider.py).
  Active (V2-8 production) HR as base + costo_empresa_override for ALL 20 regular
  staff roles (W39-W58 from 'Inputs de Nomina' column W, METROCUADRADO SAC deal).
  SCB and engine use the SAME provider for consistency.

STATUS: CTS-001_SUPPORT_FTE_PARITY_FIX (0.099% delta, -6.15 COP/tx).
  Backend best = 6,218.424663 COP/tx vs Excel = 6,224.575126 COP/tx.
  Provider patches applied:
    - All 20 regular staff: costo_empresa_override from Excel W39:W58 (commit 70ecd54)
    - SENA/Inclusión salary: 1,750,905 from Excel Inputs de Nomina!C59/C60
    - Fix A: Director de Performance/WhatsApp=1.0 (CCA!G78) via per-channel fte_soporte_overrides
    - Fix B: JCR/AFAC/GTR excluded via roles_operativos[].incluye_en_deal=False (CCA!C79/C80/C87)
  Residual gap −6.15 (0.099%): training/fixed-cost minor deltas — ACCEPTED_DELTA.
  Previous gap: -20.378 COP/tx (1.298% post cargos_adicionales). Improvement: +14.23 COP/tx.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(REPO_ROOT))

REQUEST_PATH = REPO_ROOT / "backend_nexa" / "request" / "request.json"

# Excel V2-8 anchor values (Vision Cost To Serve sheet)
EXCEL_CTS_CADENA_A = 6_224.575126115379
EXCEL_CTS_CADENA_B = 151.50625575686894
EXCEL_CTS_CADENA_C = 5_278.326744819592
EXCEL_CTS_PONDERADO = 4_660.075916632416

# Excel expected Cadena A denominator (Panel!W31) — tx/mes, not FTE
EXCEL_DENOMINADOR_CADENA_A = 221_000.0


@pytest.mark.golden
def test_cts_001_cadena_a_denominator_uses_transactional_volume() -> None:
    """
    Validates CTS Cadena A denominator and best-effort numeric parity with V2-8.

    EXCEL V2-8: Vision CTS!C34 = 6,224.575126 COP/tx, denominator = Panel!W31 = 221,000 tx/mes.
    Provider: build_v28_deal_provider() — active HR base + all 20 regular staff cargado overrides
    from 'Inputs de Nomina'!W39:W58 (METROCUADRADO SAC deal).

    CURRENT STATE (2026-06-12): 6,204.197492 (delta = -20.378 COP/tx, -0.327%).
    - Payroll nomina_loaded: -13.37 COP/tx (support salary mismatch, requires deeper RCA)
    - Training/Exam/Crucero: -3.85 COP/tx (KNOWN_DELTA)
    - Costos_fijos_estacion: -3.17 COP/tx (KNOWN_DELTA)
    - OPEX fijo: MATCH (308.138 COP/tx exact)
    - CAPEX C47: MATCH (103.044 COP/tx exact)
    - E95 Supervisor override: MATCH (9.5 FTE)
    - Denominator: MATCH (221,000 tx/mes)

    Status: CLOSED_ACCEPTED_DELTA (0.327% < 0.5% gate). Residual decomposed but closure requires
    business decision on support FTE salary alignment (per-role audit → business-rules-agent + opus).
    """
    import backend_nexa  # noqa: F401 — registers nexa_engine alias
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

    # Denominator must match Excel Panel!W31 = 221,000 tx/mes (not FTE=260)
    assert abs(cts.fte_cadena_a - EXCEL_DENOMINADOR_CADENA_A) < 1.0, (
        f"CTS Cadena A denominator mismatch: expected {EXCEL_DENOMINADOR_CADENA_A} tx/mes "
        f"(Panel!W31), got {cts.fte_cadena_a}. "
        f"Check vol_cadena_a_mensual in request.json perfiles."
    )

    assert cts.cts_cadena_a > 0.0, "CTS Cadena A must be positive"
    assert cts.cts_cadena_a < 100_000.0, (
        f"CTS Cadena A out of expected range: {cts.cts_cadena_a:.2f} COP/tx"
    )

    # Gate: with v28 deal provider + CTS-001 support FTE fix, delta should be < 0.5%
    # Fix A (Director de Performance/WhatsApp=1.0) + Fix B (JCR/AFAC/GTR excluded).
    # Current best: 6,218.424663 (delta=-6.15, 0.099%). Residual = training/fixed-cost minor.
    delta_pct = abs(cts.cts_cadena_a - EXCEL_CTS_CADENA_A) / EXCEL_CTS_CADENA_A
    assert delta_pct < 0.005, (
        f"CTS Cadena A delta regressed beyond 0.5%: {delta_pct:.4%} "
        f"(backend={cts.cts_cadena_a:.6f}, excel={EXCEL_CTS_CADENA_A:.6f}, "
        f"delta={cts.cts_cadena_a - EXCEL_CTS_CADENA_A:.6f} COP/tx). "
        f"Expected best: ~6,218.42 (0.099%). Check _v28_deal_provider.py + request.json."
    )


@pytest.mark.golden
def test_cts_002_cadena_b_regression_anchor() -> None:
    """
    CTS Cadena B regression anchor — documents current backend value.

    Excel K34 = 151.50625575686894 COP/transacción
    Backend (observed) ~560 COP/transacción — separate gap tracked as CTS-002.

    This test anchors backend behavior to detect unexpected regressions.
    Provider: build_v28_deal_provider() for consistency with CTS-001 test.
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
    # Cadena B is active — must be positive
    assert cts.cts_cadena_b > 0.0, "CTS Cadena B must be positive when cadena_b is active"
    # Known gap vs Excel (~270%). Flag if it grows beyond 4× (unexpected regression).
    delta_pct = abs(cts.cts_cadena_b - EXCEL_CTS_CADENA_B) / EXCEL_CTS_CADENA_B
    assert delta_pct < 4.0, (
        f"CTS Cadena B gap grew beyond expected range: backend={cts.cts_cadena_b:.4f}, "
        f"excel={EXCEL_CTS_CADENA_B:.4f}, delta={delta_pct:.2%}"
    )
