"""
TASK 2 — Differentiate [] vs null in Policies

Verifica que el motor respete la distinción contractual:
  - None  → usar parametrización defaults
  - []    → CERO pólizas (explícito)
  - [...]  → pólizas específicas del usuario

Esto es crítico para trazabilidad financiera y auditoría.
"""

import pytest
from unittest.mock import Mock, MagicMock

from nexa_engine.modules.calculator_motor.formulas.costos_financieros import CostosFinancierosCalculator
from nexa_engine.modules.vision_imprimible.builders.vision_datasets_builder import VisionDatasetsBuilder
from nexa_engine.modules.shared.models import (
    CadenasActivas,
    CostosFinancierosMes,
    PanelDeControl,
    ParametrosCalculo,
    ParametrosNomina,
    ParametrosNoPayroll,
    ParametrosCadenaB,
    ParametrosCadenaC,
    PerfilCadenaA,
    PolizaContractual,
    PricingRequest,
    PricingResult,
    PyGMensual,
)


# ────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def panel_base():
    """Panel de control base para tests."""
    return PanelDeControl(
        cliente="TEST_CLIENT",
        tipo_cliente="No Grupo Aval",
        linea_negocio="Cobranzas",
        fecha_inicio="2026-01-01",
        meses_contrato=12,
        margen=0.18,
        op_cont=0.025,
        com_cont=0.0,
        markup=0.0,
        descuento=0.0,
        tasa_ica=0.038,
        tasa_gmf=0.004,
        activa_financiacion=True,
        periodo_pago_dias=90,
        tasa_mensual_financ=0.02,
        ciudad="Bogota",
    )


@pytest.fixture
def mock_parametrizacion():
    """Mock de IParametrizationProvider."""
    mock = MagicMock()
    mock.get_tasa_polizas.return_value = 0.0062  # Tasa por defecto storage
    mock.get_factor_periodo.return_value = 1  # Factor de período simple
    return mock


@pytest.fixture
def calculator_with_mock(panel_base, mock_parametrizacion):
    """Factory para crear CostosFinancierosCalculator con diferentes configuraciones de pólizas."""
    def _create(polizas_usuario=None):
        return CostosFinancierosCalculator(
            panel=panel_base,
            parametrizacion=mock_parametrizacion,
            polizas_usuario=polizas_usuario,
        )
    return _create


# ────────────────────────────────────────────────────────────────────────────
# TEST SUITE — CostosFinancierosCalculator
# ────────────────────────────────────────────────────────────────────────────

class TestCostosFinancierosNullVsEmpty:
    """Tests para TASK 2: distinción [] vs None en pólizas."""

    def test_polizas_none_preserved_in_calculator(self, calculator_with_mock):
        """
        CASO 1: polizas_usuario = None

        Verificar que el calculador PRESERVA None sin convertirlo a [].
        Esto es el primer paso de la distinción contractual.
        """
        calc = calculator_with_mock(polizas_usuario=None)

        # Verificar que el calculador tiene None (no [])
        assert calc._polizas_usuario is None
        assert calc._polizas_usuario != []

    def test_polizas_empty_list_preserved_in_calculator(self, calculator_with_mock):
        """
        CASO 2: polizas_usuario = []

        Verificar que el calculador PRESERVA [] sin convertirlo a None.
        Esto es el segundo paso de la distinción contractual.
        """
        calc = calculator_with_mock(polizas_usuario=[])

        # Verificar que el calculador tiene [] (no None)
        assert calc._polizas_usuario == []
        assert calc._polizas_usuario is not None

    def test_polizas_explicit_list_preserved(self, calculator_with_mock):
        """
        CASO 3: polizas_usuario = [PolizaContractual(...)]

        Verificar que usuario que configura pólizas específicas
        las conserva sin corrupción.
        """
        polizas_usuario = [
            PolizaContractual(
                nombre="Seguro Responsabilidad Civil",
                activa=True,
                pct_poliza=0.015,
                pct_atribuible=0.5,
                aplica_a=True,
                aplica_b=False,
                aplica_c=False,
            )
        ]
        calc = calculator_with_mock(polizas_usuario=polizas_usuario)

        # Verificar que se conservó la lista
        assert calc._polizas_usuario == polizas_usuario
        assert len(calc._polizas_usuario) == 1
        assert calc._polizas_usuario[0].nombre == "Seguro Responsabilidad Civil"


# ────────────────────────────────────────────────────────────────────────────
# TEST SUITE — VisionDatasetsBuilder (simple logic check)
# ────────────────────────────────────────────────────────────────────────────

class TestVisionDatasetsNullVsEmpty:
    """Tests para TASK 2 en vision_datasets: lógica de distinción."""

    def test_vision_datasets_builder_preserves_null(self):
        """Verificar que VisionDatasetsBuilder._build_polizas respeta None."""
        from nexa_engine.modules.shared.models import PricingRequest

        solicitud = Mock(spec=PricingRequest)
        solicitud.polizas_usuario = None

        resultado_mock = Mock(spec=PricingResult)
        resultado_mock.pyg_por_mes = []

        builder = VisionDatasetsBuilder()

        # Si polizas_usuario es None, _build_polizas debe retornar None
        # Esto está en la lógica que agregamos en TASK 2
        dataset = builder._build_polizas(solicitud, resultado_mock)
        assert dataset is None

    def test_vision_datasets_builder_creates_empty_dataset_for_empty_list(self):
        """Verificar que VisionDatasetsBuilder._build_polizas crea dataset vacío para []."""
        from nexa_engine.modules.shared.models import PricingRequest

        solicitud = Mock(spec=PricingRequest)
        solicitud.polizas_usuario = []  # Lista explícitamente vacía

        resultado_mock = Mock(spec=PricingResult)
        resultado_mock.pyg_por_mes = []

        builder = VisionDatasetsBuilder()
        dataset = builder._build_polizas(solicitud, resultado_mock)

        # Si polizas_usuario es [], debe crear dataset pero vacío
        assert dataset is not None
        assert len(dataset.polizas_activas) == 0


# ────────────────────────────────────────────────────────────────────────────
# INTEGRATION TESTS
# ────────────────────────────────────────────────────────────────────────────

class TestTask2Integration:
    """Integration tests: verificar flujo completo null vs empty."""

    def test_contract_distinguishes_three_cases(self, calculator_with_mock):
        """
        Integration: Verificar que el contrato respeta la distinción
        en los tres casos: None, [], y [...]
        """
        # Escenario 1: None (NO configuró pólizas)
        calc_none = calculator_with_mock(polizas_usuario=None)
        assert calc_none._polizas_usuario is None
        assert isinstance(calc_none._polizas_usuario, type(None))

        # Escenario 2: [] (EXPLÍCITAMENTE pidió cero pólizas)
        calc_empty = calculator_with_mock(polizas_usuario=[])
        assert calc_empty._polizas_usuario == []
        assert calc_empty._polizas_usuario is not None
        assert isinstance(calc_empty._polizas_usuario, list)

        # Escenario 3: [...] (EXPLÍCITAMENTE pidió estas pólizas)
        polizas = [PolizaContractual(
            nombre="Test",
            activa=True,
            pct_poliza=0.01,
            pct_atribuible=1.0,
        )]
        calc_explicit = calculator_with_mock(polizas_usuario=polizas)
        assert len(calc_explicit._polizas_usuario) == 1
        assert isinstance(calc_explicit._polizas_usuario, list)

        # Verificación crítica: None ≠ []
        assert calc_none._polizas_usuario != calc_empty._polizas_usuario
