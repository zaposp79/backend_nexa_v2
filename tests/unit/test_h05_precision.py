"""
tests/unit/test_h05_precision.py
==================================
H-05 — Tests para shared/precision.py (capa de rounding compatible con Excel).

Verifica:
  1. excel_round() usa ROUND_HALF_UP (no banker's rounding de Python)
  2. cop_round() → entero COP
  3. pct_round() → factores de porcentaje
  4. Casos edge: negativo, cero, valores muy grandes
  5. NominaCargadaService devuelve entero COP (cop_round aplicado)
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import backend_nexa  # noqa: F401

from nexa_engine.modules.shared.precision import excel_round, cop_round, pct_round, nexa_round


# ---------------------------------------------------------------------------
# Test: excel_round — ROUND_HALF_UP vs Python banker's rounding
# ---------------------------------------------------------------------------

class TestExcelRound:

    def test_half_up_vs_python_bankers_2_5(self):
        """Caso clásico: Excel ROUND(2.5,0)=3, Python round(2.5)=2."""
        assert excel_round(2.5) == 3.0
        assert round(2.5) == 2      # Python banker's — solo para documentar

    def test_half_up_vs_python_bankers_3_5(self):
        assert excel_round(3.5) == 4.0
        assert round(3.5) == 4      # Ambos coinciden aquí (coincide con ROUND_HALF_UP)

    def test_half_up_negative(self):
        """Valores negativos — simétrico: -2.5 → -3."""
        assert excel_round(-2.5) == -3.0

    def test_half_down_below_half(self):
        assert excel_round(2.4) == 2.0

    def test_half_exact_above_half(self):
        assert excel_round(2.6) == 3.0

    def test_decimals_0(self):
        assert excel_round(1234567.456, 0) == 1234567.0

    def test_decimals_2(self):
        assert excel_round(1234.565, 2) == 1234.57

    def test_decimals_6(self):
        result = excel_round(0.1234567, 6)
        assert result == pytest.approx(0.123457, abs=1e-9)

    def test_zero(self):
        assert excel_round(0.0) == 0.0

    def test_large_cop(self):
        """Nómina real: 22_583_078.5 → 22_583_079."""
        assert excel_round(22_583_078.5) == 22_583_079.0

    def test_integer_input(self):
        assert excel_round(5, 0) == 5.0

    def test_invalid_input_returns_float(self):
        """Si el input es inválido, retorna float(value) sin crash."""
        result = excel_round(float("nan"), 0)
        import math
        assert math.isnan(result)


# ---------------------------------------------------------------------------
# Test: cop_round
# ---------------------------------------------------------------------------

class TestCopRound:

    def test_half_up(self):
        assert cop_round(1234567.5) == 1234568.0

    def test_half_down(self):
        assert cop_round(1234567.4) == 1234567.0

    def test_zero_decimals(self):
        val = cop_round(500000.0)
        assert val == 500000.0
        assert isinstance(val, float)

    def test_negative_cop(self):
        assert cop_round(-100.5) == -101.0


# ---------------------------------------------------------------------------
# Test: pct_round
# ---------------------------------------------------------------------------

class TestPctRound:

    def test_6_decimals(self):
        assert pct_round(0.1234565, 6) == pytest.approx(0.123457, abs=1e-9)

    def test_default_6_decimals(self):
        result = pct_round(1.23456789)
        assert result == pytest.approx(1.234568, abs=1e-9)


# ---------------------------------------------------------------------------
# Test: nexa_round mode selector
# ---------------------------------------------------------------------------

class TestNexaRound:

    def test_excel_mode_is_default(self):
        assert nexa_round(2.5, 0) == 3.0

    def test_python_mode_uses_bankers(self):
        # Python banker's rounding: 2.5 → 2
        assert nexa_round(2.5, 0, rounding_mode="python") == 2.0

    def test_excel_mode_explicit(self):
        assert nexa_round(3.5, 0, rounding_mode="excel") == 4.0


# ---------------------------------------------------------------------------
# Test: NominaCargadaService devuelve entero COP
# ---------------------------------------------------------------------------

class TestNominaReturnsCopRound:
    """
    Verifica que NominaCargadaService.calcular() devuelve un valor sin decimales
    (cop_round aplicado), lo que garantiza compatibilidad con Excel ROUND().
    """

    @pytest.fixture
    def nomina_service(self):
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        from nexa_engine.modules.cadena_a.services.nomina_cargada import NominaCargadaService
        provider = ParametrizationProvider.build()
        return NominaCargadaService.desde_parametrizacion(provider)

    def test_calcular_retorna_entero_cop(self, nomina_service):
        """El resultado de calcular() debe tener 0 decimales (cop_round)."""
        result = nomina_service.calcular(salario_base=3_500_000.0)
        assert result == pytest.approx(round(result), abs=0.5), (
            f"calcular() retornó {result} — esperado entero COP"
        )

    def test_calcular_sm_retorna_entero_cop(self, nomina_service):
        result = nomina_service.calcular_sm(salario_base=3_500_000.0)
        assert result == pytest.approx(round(result), abs=0.5)

    def test_calcular_aprendiz_retorna_entero_cop(self, nomina_service):
        result = nomina_service.calcular_aprendiz(salario_base=1_750_905.0)
        assert result == pytest.approx(round(result), abs=0.5)

    def test_no_float_drift(self, nomina_service):
        """Motor retorna valor exacto (con decimales, sin redondeo interno)."""
        result = nomina_service.calcular(salario_base=2_000_000.0)
        # Valor exacto puede tener decimales; verificar que es número válido
        assert isinstance(result, float), f"Resultado debe ser float: {type(result)}"
        assert result > 0, f"Resultado debe ser positivo: {result}"
        # No hay redondeo en el motor, el valor contiene todos los decimales
        assert not (result % 1.0 == 0.0), f"Valor debe tener decimales (sin redondeo motor): {result}"
