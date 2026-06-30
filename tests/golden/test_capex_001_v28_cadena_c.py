"""
tests/golden/test_capex_001_v28_cadena_c.py
===========================================
Golden test — CAPEX-001: Cadena C CAPEX financing factor (V2-8).

PURPOSE
-------
Validate that `_costo_amortizacion_inversion` in CadenaCCalculator applies
the financing factor (1 + tasa_mensual_financ) per Condiciones Cadena C!J62:

  J62 = IFERROR((I62/H62)*(1+'Panel de Control General'!$L$11),0)

where:
  I = valor_total  (F × G = precio_unitario × cantidad)
  H = meses_a_diferir
  L11 = tasa_interes_mensual = 0.0153

EXCEL V2-8 REFERENCE VALUES (Condiciones Cadena C, data_only=True)
-------------------------------------------------------------------
  Row 62: valor_total=150_000_000, meses=24  → J62 = 6_345_625.00
  Row 63: valor_total=516_516,     meses=12  → J63 = 43_701.56
  Row 64: valor_total=150_000_000, meses=24  → J64 = 6_345_625.00
  Row 65: valor_total=516_516,     meses=12  → J65 = 43_701.56
  SUM(J62:J65) = 12_778_653.116

FORMULA CHAIN
-------------
  1. Adapter _c_calcular_inversion:
       inversion_anual = sum(valor_total/meses) * 12  (per item, no factor yet)
  2. Reglas _costo_amortizacion_inversion:
       result = inversion_anual / 12 * (1 + tasa_interes_mensual)
       = sum(valor_total/meses) * (1 + tasa)
       = Excel J-column sum ✓

KNOWN CONSTRAINTS
-----------------
  - inversiones_capex[] must be populated in request; empty list → inversiones=0.
  - tasa_interes_mensual injected via ParametrosCadenaC from Panel!L11.
  - Factor was already present in V2-8 implementation (reglas.py line 182).
  - This test pins the formula with V2-8 numerical evidence.
"""

import pytest
from unittest.mock import MagicMock

from nexa_engine.modules.shared.models import ParametrosCadenaC
from nexa_engine.modules.cadena_c.reglas import CadenaCCalculator


# ──────────────────────────────────────────────────────────────────
# Constants from Excel V2-8 (Condiciones Cadena C, data_only=True)
# ──────────────────────────────────────────────────────────────────
_TASA_INTERES_MENSUAL: float = 0.0153  # Panel!L11

# Per-item: (valor_total, meses_a_diferir)
_CAPEX_ITEMS_V28 = [
    (150_000_000.0, 24),   # Row 62: Inbound Voz 2, unitario
    (516_516.0,     12),   # Row 63: Inbound Transversal, unitario
    (150_000_000.0, 24),   # Row 64: Outbound Voz, unitario
    (516_516.0,     12),   # Row 65: Outbound Transversal, unitario
]

# SUM(J62:J65) from Excel (data_only=True)
_EXCEL_TOTAL_INVERSIONES: float = 12_778_653.1158


def _build_calculator(inversion_anual: float) -> CadenaCCalculator:
    """Build CadenaCCalculator with only CAPEX-relevant fields set."""
    parametros = ParametrosCadenaC(
        canales=[],
        equipo_transversal=[],
        costo_equipo_integ=0.0,
        opex_herramientas_integ=0.0,
        costo_personal_hitl=0.0,
        opex_herramientas_hitl=0.0,
        inversion_anual=inversion_anual,
        pct_aumento_tecnologico=0.0,
        tasa_interes_mensual=_TASA_INTERES_MENSUAL,
        mes_aplicacion_aumento=13,
    )
    mock_prov = MagicMock()
    return CadenaCCalculator(parametros, mock_prov)


@pytest.mark.golden
class TestCapex001V28:
    """CAPEX-001: financing factor (1+tasa) applied to amortized monthly CAPEX."""

    def test_formula_unit_single_item_24_months(self):
        """
        EXCEL V2-8: Condiciones Cadena C!J62
        = (150_000_000/24)*(1+0.0153) = 6_345_625.00
        """
        valor_total = 150_000_000.0
        meses = 24
        inversion_anual = (valor_total / meses) * 12  # adapter normalization

        calc = _build_calculator(inversion_anual)
        result = calc._costo_amortizacion_inversion()  # noqa: SLF001

        expected = (valor_total / meses) * (1 + _TASA_INTERES_MENSUAL)
        assert abs(result - expected) < 1.0, (
            f"Expected {expected:.4f}, got {result:.4f} — "
            "factor (1+tasa_mensual) may be missing"
        )

    def test_formula_unit_single_item_12_months(self):
        """
        EXCEL V2-8: Condiciones Cadena C!J63
        = (516_516/12)*(1+0.0153) = 43_701.56
        """
        valor_total = 516_516.0
        meses = 12
        inversion_anual = (valor_total / meses) * 12

        calc = _build_calculator(inversion_anual)
        result = calc._costo_amortizacion_inversion()  # noqa: SLF001

        expected = (valor_total / meses) * (1 + _TASA_INTERES_MENSUAL)
        assert abs(result - expected) < 1.0, (
            f"Expected {expected:.4f}, got {result:.4f}"
        )

    def test_formula_sum_all_v28_items(self):
        """
        SUM(J62:J65) from Condiciones Cadena C V2-8 = 12_778_653.116
        Adapter sums items then ×12; reglas divides by 12 and applies factor.
        Net: sum(I/H)*(1+tasa).
        """
        raw_sum = sum(vt / m for vt, m in _CAPEX_ITEMS_V28)
        inversion_anual = raw_sum * 12  # adapter output

        calc = _build_calculator(inversion_anual)
        result = calc._costo_amortizacion_inversion()  # noqa: SLF001

        assert abs(result - _EXCEL_TOTAL_INVERSIONES) < 1.0, (
            f"Expected Excel SUM(J62:J65)={_EXCEL_TOTAL_INVERSIONES:.4f}, "
            f"got {result:.4f}"
        )

    def test_zero_inversion_returns_zero(self):
        """Edge case: no CAPEX items → inversiones = 0."""
        calc = _build_calculator(0.0)
        result = calc._costo_amortizacion_inversion()  # noqa: SLF001
        assert result == 0.0
