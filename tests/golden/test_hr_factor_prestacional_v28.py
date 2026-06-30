"""
tests/golden/test_hr_factor_prestacional_v28.py
===============================================
HR Prestational Factor Parity — V2-8.

Proves there is NO prestational factor mismatch behind the CTS-001 residual.

EXCEL ANCHOR (Inputs de Nomina, V2-8):
  Row 36 prestational rates (salud 0.085, pension 0.12, arl 0.00522, caja 0.04,
  icbf 0.04, cesantias 0.0833, primas 0.0833, int_ces 0.12, vacaciones 0.0417).
  SAC line (row 62): C62=1,750,905 base, D62=600,000 variable, F62=2,350,905
  imponible, W62 = Costo Empresa = 3,560,973.8626.

The backend NominaCargadaService — fed rates SOLELY from the V27 provider
(no hardcoded factor) — must reproduce W62 exactly. The true per-line carga
factor (W62 / F62) is therefore 1.5147 in BOTH Excel and backend.

This refutes the "backend 1.5256 vs Excel 1.5699" premise: those are aggregate
artifacts (loaded total / raw-commission base), not prestational factors.

Evidence: docs/refactor/hr_param_factor_prestacional_v28.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(REPO_ROOT))

# Excel V2-8 anchors (Inputs de Nomina)
EXCEL_W62_COSTO_EMPRESA = 3_560_973.8626  # SAC line, employer total cost
EXCEL_F62_IMPONIBLE = 2_350_905.0          # C62 + D62
EXCEL_SAC_BASE = 1_750_905.0               # C62
EXCEL_SAC_VARIABLE = 600_000.0             # D62
# True per-line carga factor over imponible (W62 / F62)
EXCEL_PER_LINE_FACTOR = EXCEL_W62_COSTO_EMPRESA / EXCEL_F62_IMPONIBLE  # 1.5147...

# Excel V2-8 prestational rates (Inputs de Nomina!row 36)
EXCEL_RATES = {
    "salud": 0.085,
    "pension": 0.12,
    "arl_staff": 0.00522,
    "caja": 0.04,
    "icbf_sena": 0.04,
}
EXCEL_PRESTACIONES = {
    "cesantias": 0.0833,
    "primas": 0.0833,
    "interes_cesantia": 0.12,
    "vacaciones": 0.0417,
}


def _provider():
    import backend_nexa  # noqa: F401 — registers nexa_engine alias
    from backend_nexa.tests.refactor._v27_provider import build_v27_provider

    return build_v27_provider()


@pytest.mark.parity
def test_prestational_rates_match_excel_v28_no_hardcode() -> None:
    """All prestational rates come from the provider and match Excel V2-8 row 36."""
    datos = _provider().get_nomina_laboral_params()
    aps = datos["aportes_patronales"]
    pre = datos["prestaciones"]

    for k, expected in EXCEL_RATES.items():
        assert aps[k] == pytest.approx(expected, abs=1e-9), (
            f"Rate {k}: provider {aps[k]} != Excel V2-8 row 36 {expected}"
        )
    for k, expected in EXCEL_PRESTACIONES.items():
        assert pre[k] == pytest.approx(expected, abs=1e-9), (
            f"Prestacion {k}: provider {pre[k]} != Excel V2-8 row 36 {expected}"
        )

    assert datos["salario_minimo"] == pytest.approx(1_750_905.0, abs=1.0)
    assert datos["auxilio_transporte"] == pytest.approx(249_095.0, abs=1.0)
    assert datos["pct_cumplimiento_variable"] == pytest.approx(0.70, abs=1e-9)


@pytest.mark.parity
def test_loaded_sac_line_matches_excel_w62() -> None:
    """
    NominaCargadaService.calcular reproduces Excel W62 = 3,560,973.86 for the SAC
    line, proving the loaded prestational factor (1.5147) matches Excel exactly.
    """
    from nexa_engine.modules.cadena_a.services.nomina_cargada import NominaCargadaService

    svc = NominaCargadaService.desde_parametrizacion(_provider())
    com_pct = EXCEL_SAC_VARIABLE / EXCEL_SAC_BASE
    costo = svc.calcular(EXCEL_SAC_BASE, com_pct)

    assert costo == pytest.approx(EXCEL_W62_COSTO_EMPRESA, abs=1.0), (
        f"Loaded SAC line {costo:.4f} != Excel W62 {EXCEL_W62_COSTO_EMPRESA}"
    )

    factor = costo / (EXCEL_SAC_BASE * (1.0 + com_pct))
    assert factor == pytest.approx(EXCEL_PER_LINE_FACTOR, abs=1e-4), (
        f"Per-line carga factor {factor:.6f} != Excel {EXCEL_PER_LINE_FACTOR:.6f}. "
        f"NOTE: 1.5256/1.5699 are aggregate artifacts, not this per-line factor."
    )
