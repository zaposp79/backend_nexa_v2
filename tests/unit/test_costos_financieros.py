"""
Unit tests for nexa_engine/calculators/costos_financieros.py

Tests cover CostosFinancierosCalculator.calcular() across all four financial
components: financiacion, polizas (gross-up), ica (gross-up), gmf (flat).
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from nexa_engine.modules.calculator_motor.formulas.costos_financieros import CostosFinancierosCalculator
from nexa_engine.modules.shared.models import PanelDeControl, PolizaContractual


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_panel(**overrides) -> PanelDeControl:
    """Return a base PanelDeControl suitable for financial cost tests."""
    defaults = dict(
        cliente="Test",
        tipo_cliente="",
        linea_negocio="Cobranzas",
        fecha_inicio="2026-01-01",
        meses_contrato=12,
        margen=0.17,
        op_cont=0.025,
        com_cont=0.0,
        markup=0.0,
        descuento=0.0,
        tasa_ica=0.0097,
        tasa_gmf=0.004,
        activa_financiacion=True,
        periodo_pago_dias=60,
        tasa_mensual_financ=0.01,
        ciudad="Bogota",
        sede="",
        antiguedad_cliente="",
        pct_ausentismo=0.0,
        horas_formacion_mensual=0,
        indexacion=None,
        aplica_ley_1819=True,
    )
    defaults.update(overrides)
    return PanelDeControl(**defaults)


def _make_provider(tasa_polizas: float = 0.002, factor_periodo: int = 2) -> MagicMock:
    provider = MagicMock()
    provider.get_tasa_polizas_efectiva.return_value = tasa_polizas
    provider.get_factor_periodo.return_value = factor_periodo
    return provider


def _make_calculator(panel: PanelDeControl = None,
                     provider: MagicMock = None) -> CostosFinancierosCalculator:
    if panel is None:
        panel = _make_panel()
    if provider is None:
        provider = _make_provider()
    return CostosFinancierosCalculator(panel, provider)


# ---------------------------------------------------------------------------
# Financiación
# ---------------------------------------------------------------------------

class TestFinanciacion:
    def test_financiacion_inactiva_returns_zero(self):
        panel = _make_panel(activa_financiacion=False)
        calc = _make_calculator(panel)
        result = calc.calcular(costo_operativo=1_000_000, mes=1,
                               costo_operativo_mes_anterior=1_000_000)
        assert result.financiacion == 0.0

    def test_financiacion_mes_1_con_anterior_cero(self):
        """Mes 1: base_financiacion=0 → financiacion=0 (Excel convention)."""
        calc = _make_calculator()
        result = calc.calcular(costo_operativo=1_000_000, mes=1,
                               costo_operativo_mes_anterior=0.0)
        assert result.financiacion == 0.0

    def test_financiacion_usa_costo_anterior(self):
        """
        Timing convention: financiacion se calcula sobre costo del mes anterior,
        no sobre el costo actual.
        """
        panel = _make_panel(
            activa_financiacion=True,
            tasa_mensual_financ=0.01,
            tasa_ica=0.0,
            tasa_gmf=0.0,
        )
        provider = _make_provider(tasa_polizas=0.0, factor_periodo=2)
        calc = CostosFinancierosCalculator(panel, provider)

        costo_anterior = 500_000.0
        costo_actual = 1_000_000.0
        result = calc.calcular(costo_operativo=costo_actual, mes=2,
                               costo_operativo_mes_anterior=costo_anterior)

        # financiacion = factor_periodo × tasa × costo_anterior = 2 × 0.01 × 500_000
        expected_fin = 2 * 0.01 * costo_anterior
        assert result.financiacion == pytest.approx(expected_fin)

    def test_financiacion_sin_anterior_usa_costo_actual(self):
        """
        Backward compatibility: when costo_operativo_mes_anterior is None,
        financiacion uses the current cost.
        """
        panel = _make_panel(
            activa_financiacion=True,
            tasa_mensual_financ=0.01,
            tasa_ica=0.0,
            tasa_gmf=0.0,
        )
        provider = _make_provider(tasa_polizas=0.0, factor_periodo=1)
        calc = CostosFinancierosCalculator(panel, provider)

        costo = 1_000_000.0
        result = calc.calcular(costo_operativo=costo, mes=2,
                               costo_operativo_mes_anterior=None)
        expected_fin = 1 * 0.01 * costo
        assert result.financiacion == pytest.approx(expected_fin)


# ---------------------------------------------------------------------------
# Pólizas — gross-up
# ---------------------------------------------------------------------------

class TestPolizas:
    def test_polizas_gross_up_formula(self):
        """
        polizas = tasa_efectiva × (costo_op + financiacion) / factor_margenes

        Uses: factor_margenes = (1-0.17)×(1-0.025) = 0.83×0.975 = 0.80925
        PolizaContractual(pct_poliza=0.002, pct_atribuible=1.0) → tasa_efectiva=0.002
        """
        panel = _make_panel(
            margen=0.17, op_cont=0.025,
            activa_financiacion=False,  # isolate polizas
            tasa_ica=0.0, tasa_gmf=0.0,
        )
        provider = _make_provider(tasa_polizas=0.002, factor_periodo=1)
        poliza = PolizaContractual(
            nombre="TestPoliza", activa=True,
            pct_poliza=0.002, pct_atribuible=1.0,
            aplica_a=True, aplica_b=False, aplica_c=False,
        )
        calc = CostosFinancierosCalculator(panel, provider, polizas_usuario=[poliza])

        costo_op = 1_000_000.0
        result = calc.calcular(costo_op, mes=1, costo_operativo_mes_anterior=0.0)

        factor_margenes = (1 - 0.17) * (1 - 0.025)
        financiacion = 0.0  # activa=False
        expected_polizas = 0.002 * (costo_op + financiacion) / factor_margenes
        assert result.polizas == pytest.approx(expected_polizas, rel=1e-6)

    def test_polizas_zero_when_tasa_zero(self):
        provider = _make_provider(tasa_polizas=0.0, factor_periodo=1)
        calc = _make_calculator(provider=provider)
        result = calc.calcular(1_000_000.0, mes=1, costo_operativo_mes_anterior=0.0)
        assert result.polizas == 0.0


# ---------------------------------------------------------------------------
# ICA — gross-up
# ---------------------------------------------------------------------------

class TestICA:
    def test_ica_gross_up_formula(self):
        """
        ica = (costo_op/factor_margenes + polizas + financiacion) × tasa_ica
        """
        panel = _make_panel(
            margen=0.17, op_cont=0.025,
            tasa_ica=0.0097,
            tasa_gmf=0.0,
            activa_financiacion=False,
        )
        provider = _make_provider(tasa_polizas=0.0, factor_periodo=1)
        calc = CostosFinancierosCalculator(panel, provider)

        costo_op = 1_000_000.0
        result = calc.calcular(costo_op, mes=1, costo_operativo_mes_anterior=0.0)

        factor_margenes = (1 - 0.17) * (1 - 0.025)
        financiacion = 0.0
        polizas = 0.0
        expected_ica = (costo_op / factor_margenes + polizas + financiacion) * 0.0097
        assert result.ica == pytest.approx(expected_ica, rel=1e-6)

    def test_ica_zero_when_tasa_zero(self):
        panel = _make_panel(tasa_ica=0.0)
        provider = _make_provider(tasa_polizas=0.0)
        calc = CostosFinancierosCalculator(panel, provider)
        result = calc.calcular(1_000_000.0, mes=1, costo_operativo_mes_anterior=0.0)
        assert result.ica == 0.0


# ---------------------------------------------------------------------------
# GMF — no gross-up
# ---------------------------------------------------------------------------

class TestGMF:
    def test_gmf_no_gross_up_formula(self):
        """
        gmf = (costo_op + polizas + financiacion) × tasa_gmf
        No gross-up: applies directly on cash flow, not on gross income equivalent.
        """
        panel = _make_panel(
            tasa_gmf=0.004,
            tasa_ica=0.0,
            activa_financiacion=False,
        )
        provider = _make_provider(tasa_polizas=0.0, factor_periodo=1)
        calc = CostosFinancierosCalculator(panel, provider)

        costo_op = 1_000_000.0
        result = calc.calcular(costo_op, mes=1, costo_operativo_mes_anterior=0.0)

        financiacion = 0.0
        polizas = 0.0
        expected_gmf = (costo_op + polizas + financiacion) * 0.004
        assert result.gmf == pytest.approx(expected_gmf, rel=1e-6)

    def test_gmf_zero_when_tasa_zero(self):
        panel = _make_panel(tasa_gmf=0.0)
        calc = _make_calculator(panel)
        result = calc.calcular(1_000_000.0, mes=1, costo_operativo_mes_anterior=0.0)
        assert result.gmf == 0.0


# ---------------------------------------------------------------------------
# Zero inputs
# ---------------------------------------------------------------------------

class TestZeroInputs:
    def test_todos_cero_cuando_costo_cero(self):
        """All components → 0 when costo_operativo = 0."""
        calc = _make_calculator()
        result = calc.calcular(
            costo_operativo=0.0, mes=1, costo_operativo_mes_anterior=0.0
        )
        assert result.financiacion == 0.0
        assert result.polizas == 0.0
        assert result.ica == 0.0
        assert result.gmf == 0.0
        assert result.total == 0.0


# ---------------------------------------------------------------------------
# CostosFinancierosMes.total property
# ---------------------------------------------------------------------------

class TestCostosFinancierosTotal:
    def test_total_es_suma_de_componentes(self):
        """CostosFinancierosMes.total should equal sum of all four components."""
        panel = _make_panel(
            margen=0.17, op_cont=0.025,
            activa_financiacion=True,
            tasa_mensual_financ=0.01,
            tasa_ica=0.0097,
            tasa_gmf=0.004,
        )
        provider = _make_provider(tasa_polizas=0.002, factor_periodo=2)
        calc = CostosFinancierosCalculator(panel, provider)

        costo = 2_000_000.0
        result = calc.calcular(costo, mes=2, costo_operativo_mes_anterior=1_800_000.0)

        expected_total = result.financiacion + result.polizas + result.ica + result.gmf
        assert result.total == pytest.approx(expected_total, rel=1e-10)

    def test_componentes_todos_positivos_con_inputs_normales(self):
        """Under normal inputs, all four components are non-negative."""
        calc = _make_calculator()
        result = calc.calcular(1_000_000.0, mes=3, costo_operativo_mes_anterior=950_000.0)
        assert result.financiacion >= 0.0
        assert result.polizas >= 0.0
        assert result.ica >= 0.0
        assert result.gmf >= 0.0
