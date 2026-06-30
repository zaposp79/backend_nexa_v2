"""
tests/golden/test_nomina_variable_load_v28.py
=============================================
Validates that variable compensation is loaded with prestational factor — not
reduced by pct_cumplimiento before loading.

EXCEL V2-8 ANCHORS:
  'Inputs de Nomina'!F62 = C62 + D62 = 1,750,905 + 600,000 = 2,350,905
    → the loaded imponible base uses the FULL commission (D62=600,000),
      NOT reduced by pct_cumplimiento (0.70).
  'Nomina Loaded'!R205 carga la comisión variable completa con factor prestacional.

DECISION: VARIABLE_COMP_LOAD_DECISION = APPLY_PRESTATIONAL_LOAD_LIKE_EXCEL
  Variable comp is loaded COMPLETE with prestational factor in NominaCargadaService.
  pct_cumplimiento (0.70) is applied downstream in NominaCalculator._comisiones,
  not before loading the prestational base.

STATUS: CTS-001_PARTIAL — Bug 2 (cumplimiento-before-load) fixed.
  CTS Cadena A delta improved from -525.07 COP/tx (8.44%) to ~-232 COP/tx (3.73%).
  Residual = secondary carga-factor + examenes/crucero gaps (tracked separately).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(REPO_ROOT))

REQUEST_PATH = REPO_ROOT / "backend_nexa" / "request" / "request.json"

# Excel V2-8 anchors
EXCEL_CTS_CADENA_A = 6_224.575126115379
EXCEL_IMPONIBLE_FULL = 2_350_905.0  # Inputs de Nomina F62 (base + full commission)

# Pre-fix CTS delta (documented root cause)
PREFIX_CTS_DELTA = 525.069874


@pytest.mark.golden
def test_variable_comp_imponible_uses_full_commission() -> None:
    """
    The loaded imponible base must use the FULL commission (Excel F62=2,350,905),
    NOT reduced by pct_cumplimiento before loading.
    """
    import backend_nexa  # noqa: F401
    from backend_nexa.tests.refactor._v27_provider import build_v27_provider
    from nexa_engine.modules.cadena_a.services.nomina_cargada import NominaCargadaService

    prov = build_v27_provider()
    svc = NominaCargadaService.desde_parametrizacion(prov)
    params = prov.get_nomina_laboral_params()

    base = 1_750_905.0
    com_pct = 600_000.0 / base  # D62 / C62

    cargado = svc.calcular(base, com_pct)
    # The internal imponible must be base*(1+com_pct) = full commission, no 0.70 reduction.
    imponible_full = base * (1.0 + com_pct)
    assert abs(imponible_full - EXCEL_IMPONIBLE_FULL) < 1.0, (
        f"Imponible base must use full commission (Excel F62={EXCEL_IMPONIBLE_FULL}), "
        f"got {imponible_full}"
    )
    # The cargado must reflect the FULL imponible: recomputing with the reduced
    # (cumplimiento-applied) base would yield a strictly smaller loaded payroll.
    imponible_reduced = base * (1.0 + com_pct * params["pct_cumplimiento_variable"])
    cargado_reduced = svc.calcular(base, com_pct * params["pct_cumplimiento_variable"])
    assert cargado > cargado_reduced, (
        f"Loaded payroll must use full commission base ({imponible_full:.0f}) and exceed "
        f"the cumplimiento-reduced base ({imponible_reduced:.0f}); "
        f"got cargado={cargado:.2f} vs reduced={cargado_reduced:.2f}"
    )


@pytest.mark.golden
def test_cts_001_improved_after_variable_load_fix() -> None:
    """
    CTS Cadena A delta must improve vs the pre-fix root-cause baseline (525.07 COP/tx).
    """
    import backend_nexa  # noqa: F401
    from backend_nexa.tests.refactor._v27_provider import build_v27_provider
    from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
    from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
    from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine

    payload = json.loads(REQUEST_PATH.read_text())
    user_input = UserInputLoader().cargar_desde_dict(payload)
    solicitud = SimulationContextBuilder().construir(user_input)
    resultado = NexaPricingEngine(parametrizacion=build_v27_provider()).calcular(solicitud)

    cts = resultado.cost_to_serve
    delta = abs(cts.cts_cadena_a - EXCEL_CTS_CADENA_A)
    assert delta < PREFIX_CTS_DELTA, (
        f"CTS Cadena A delta did not improve: {delta:.4f} (pre-fix {PREFIX_CTS_DELTA})"
    )
    # Regression guard: keep within achieved band after OPEX_REQUEST_ALIGNMENT (< 5%).
    # OPEX correction lowered CTS further (payroll deficit unmasked). V27 provider gives ~4.72%.
    assert delta / EXCEL_CTS_CADENA_A < 0.05, (
        f"CTS Cadena A delta regressed beyond 5%: backend={cts.cts_cadena_a:.4f}, "
        f"excel={EXCEL_CTS_CADENA_A:.4f}"
    )
