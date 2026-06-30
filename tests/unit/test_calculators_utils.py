"""
Unit tests for calculator utility functions — Phase 5I: shared_calc deleted.

Tests now cover the canonical implementations directly:
  - calcular_factor_margenes  → ProfitabilityCalculator.calcular_factor_margenes
  - calcular_factor_aumento   → PayrollCalculator.calcular_factor_aumento
  - calcular_rampup           → parametrizacion.get_rampup (thin wrapper, tested via provider mock)
  - calcular_tasa_polizas     → parametrizacion.get_tasa_polizas_efectiva
  - calcular_factor_periodo   → parametrizacion.get_factor_periodo
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator
from nexa_engine.modules.calculator_motor.formulas.payroll import PayrollCalculator
from nexa_engine.modules.shared.models import PanelDeControl


def calcular_factor_margenes(panel):
    return ProfitabilityCalculator.calcular_factor_margenes(panel)


def calcular_factor_aumento(mes, pct_aumento, mes_aplicacion):
    return PayrollCalculator.calcular_factor_aumento(mes, pct_aumento, mes_aplicacion)


def calcular_rampup(linea_negocio, mes, parametrizacion):
    return parametrizacion.get_rampup(linea_negocio, mes)


def calcular_tasa_polizas(mes, parametrizacion):
    return parametrizacion.get_tasa_polizas_efectiva(mes)


def calcular_factor_periodo(panel, parametrizacion):
    return parametrizacion.get_factor_periodo(panel.periodo_pago_dias)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_panel(
    margen: float = 0.0,
    op_cont: float = 0.0,
    com_cont: float = 0.0,
    markup: float = 0.0,
    descuento: float = 0.0,
    periodo_pago_dias: int = 30,
) -> PanelDeControl:
    return PanelDeControl(
        cliente="Test",
        tipo_cliente="",
        linea_negocio="Cobranzas",
        fecha_inicio="2026-01-01",
        meses_contrato=12,
        margen=margen,
        op_cont=op_cont,
        com_cont=com_cont,
        markup=markup,
        descuento=descuento,
        tasa_ica=0.0,
        tasa_gmf=0.0,
        activa_financiacion=False,
        periodo_pago_dias=periodo_pago_dias,
        tasa_mensual_financ=0.0,
    )


# ---------------------------------------------------------------------------
# calcular_factor_margenes
# ---------------------------------------------------------------------------

class TestCalcularFactorMargenes:
    def test_zero_margins_returns_one(self):
        panel = _make_panel()
        assert calcular_factor_margenes(panel) == pytest.approx(1.0)

    def test_margen_only(self):
        panel = _make_panel(margen=0.17)
        # (1-0.17) = 0.83
        assert calcular_factor_margenes(panel) == pytest.approx(0.83)

    def test_margen_and_op_cont(self):
        panel = _make_panel(margen=0.17, op_cont=0.025)
        # (1-0.17) * (1-0.025) = 0.83 * 0.975
        expected = 0.83 * 0.975
        assert calcular_factor_margenes(panel) == pytest.approx(expected)

    def test_all_margins_combined(self):
        panel = _make_panel(margen=0.10, op_cont=0.02, com_cont=0.03, markup=0.01, descuento=0.05)
        expected = (1 - 0.10) * (1 - 0.02) * (1 - 0.03) * (1 - 0.01) * (1 + 0.05)
        assert calcular_factor_margenes(panel) == pytest.approx(expected)

    def test_descuento_increases_factor(self):
        panel_sin = _make_panel(margen=0.17)
        panel_con = _make_panel(margen=0.17, descuento=0.10)
        assert calcular_factor_margenes(panel_con) > calcular_factor_margenes(panel_sin)

    def test_maximum_margen_approaches_zero(self):
        panel = _make_panel(margen=0.999)
        assert calcular_factor_margenes(panel) == pytest.approx(0.001, rel=1e-3)


# ---------------------------------------------------------------------------
# calcular_factor_aumento
# ---------------------------------------------------------------------------

class TestCalcularFactorAumento:
    def test_before_mes_aplicacion_returns_one(self):
        # Months 1-12 before mes_aplicacion=13 → 1.0
        for mes in range(1, 13):
            assert calcular_factor_aumento(mes, pct_aumento=0.10, mes_aplicacion=13) == pytest.approx(1.0)

    def test_edge_case_mes_equals_mes_aplicacion(self):
        # Exactly at mes_aplicacion → first year → (1+pct)^1
        result = calcular_factor_aumento(13, pct_aumento=0.10, mes_aplicacion=13)
        assert result == pytest.approx(1.10)

    def test_first_year_increase(self):
        # mes 13-24 → (1+0.10)^1
        for mes in range(13, 25):
            result = calcular_factor_aumento(mes, pct_aumento=0.10, mes_aplicacion=13)
            assert result == pytest.approx(1.10), f"Failed at mes={mes}"

    def test_second_year_increase(self):
        # mes 25-36 → (1+0.10)^2 = 1.21
        for mes in range(25, 37):
            result = calcular_factor_aumento(mes, pct_aumento=0.10, mes_aplicacion=13)
            assert result == pytest.approx(1.21), f"Failed at mes={mes}"

    def test_third_year_increase(self):
        # mes 37-48 → (1+0.10)^3 = 1.331
        result = calcular_factor_aumento(37, pct_aumento=0.10, mes_aplicacion=13)
        assert result == pytest.approx(1.331)

    def test_zero_pct_aumento_always_one(self):
        for mes in [1, 13, 25, 36]:
            result = calcular_factor_aumento(mes, pct_aumento=0.0, mes_aplicacion=13)
            assert result == pytest.approx(1.0)

    def test_mes_aplicacion_1_applies_from_start(self):
        # mes_aplicacion=1 → even mes=1 gets the increase
        result = calcular_factor_aumento(1, pct_aumento=0.10, mes_aplicacion=1)
        assert result == pytest.approx(1.10)


# ---------------------------------------------------------------------------
# calcular_rampup
# ---------------------------------------------------------------------------

class TestCalcularRampup:
    def test_delegates_to_provider(self):
        mock_provider = MagicMock()
        mock_provider.get_rampup.return_value = 0.75

        result = calcular_rampup("Cobranzas", mes=3, parametrizacion=mock_provider)

        mock_provider.get_rampup.assert_called_once_with("Cobranzas", 3)
        assert result == 0.75

    def test_different_linea_negocio(self):
        mock_provider = MagicMock()
        mock_provider.get_rampup.return_value = 1.0

        result = calcular_rampup("SAC", mes=1, parametrizacion=mock_provider)

        mock_provider.get_rampup.assert_called_once_with("SAC", 1)
        assert result == 1.0

    def test_full_capacity_returns_one(self):
        mock_provider = MagicMock()
        mock_provider.get_rampup.return_value = 1.0

        result = calcular_rampup("Cobranzas", mes=12, parametrizacion=mock_provider)
        assert result == 1.0


# ---------------------------------------------------------------------------
# calcular_tasa_polizas
# ---------------------------------------------------------------------------

class TestCalcularTasaPolizas:
    def test_delegates_to_provider(self):
        mock_provider = MagicMock()
        mock_provider.get_tasa_polizas_efectiva.return_value = 0.002

        result = calcular_tasa_polizas(mes=5, parametrizacion=mock_provider)

        mock_provider.get_tasa_polizas_efectiva.assert_called_once_with(5)
        assert result == 0.002

    def test_zero_tasa(self):
        mock_provider = MagicMock()
        mock_provider.get_tasa_polizas_efectiva.return_value = 0.0

        result = calcular_tasa_polizas(mes=1, parametrizacion=mock_provider)
        assert result == 0.0

    def test_mes_1_vs_mes_12(self):
        mock_provider = MagicMock()
        mock_provider.get_tasa_polizas_efectiva.side_effect = lambda mes: 0.001 * mes

        assert calcular_tasa_polizas(1, mock_provider) == pytest.approx(0.001)
        assert calcular_tasa_polizas(12, mock_provider) == pytest.approx(0.012)


# ---------------------------------------------------------------------------
# calcular_factor_periodo
# ---------------------------------------------------------------------------

class TestCalcularFactorPeriodo:
    def test_delegates_to_provider(self):
        mock_provider = MagicMock()
        mock_provider.get_factor_periodo.return_value = 2

        panel = _make_panel(periodo_pago_dias=60)
        result = calcular_factor_periodo(panel, mock_provider)

        mock_provider.get_factor_periodo.assert_called_once_with(60)
        assert result == 2

    def test_30_dias_returns_1(self):
        mock_provider = MagicMock()
        mock_provider.get_factor_periodo.return_value = 1

        panel = _make_panel(periodo_pago_dias=30)
        result = calcular_factor_periodo(panel, mock_provider)
        assert result == 1

    def test_90_dias_returns_3(self):
        mock_provider = MagicMock()
        mock_provider.get_factor_periodo.return_value = 3

        panel = _make_panel(periodo_pago_dias=90)
        result = calcular_factor_periodo(panel, mock_provider)
        assert result == 3
