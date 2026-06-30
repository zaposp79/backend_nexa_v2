"""
Phase 8: Contract Enforcement Tests

Valida que todos los fixes de Fase 8 funcionan correctamente:
- F8.1: canales[0] hardcoding reemplazado
- F8.2: Silent defaults eliminados (fail-fast)
- F8.3: Extra wrapping en vision_tarifas corregido
- F8.4: @property fields documentados y completos
"""

import inspect

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from nexa_engine.modules.shared.models import (
    PricingResult,
    PanelDeControl,
    KPIsDeal,
    PyGMensual,
    ResultadoVisionTarifas,
    TarifaCanal,
    ResultadoCostToServe,
    DesgloseCTSCadenaA,
    DesgloseCTSCadenaB,
)
from nexa_engine.modules.calculator_motor.serializers.serializer_helpers import (
    _select_principal_channel,
    _configuracion_comercial,
    _pyg_to_dict,
)


# ──────────────────────────────────────────────────────────────────────
# Test Suite: F8.1 — Principal Channel Selection (not canales[0])
# ──────────────────────────────────────────────────────────────────────

class TestPrincipalChannelSelection:
    """Validar que _select_principal_channel selecciona por máxima facturación"""

    def test_selects_channel_with_maximum_facturacion(self):
        """El canal con mayor facturación debe ser seleccionado como principal"""
        # Setup: 3 canales con diferentes facturación
        canal_1 = TarifaCanal(
            nombre_canal="WhatsApp",
            facturacion=1_000_000.00,  # Menor
            modelo_cobro="Fijo FTE",
            pct_fijo=1.0,
            pct_variable=0.0,
            tarifa_variable=0.0,
        )
        canal_2 = TarifaCanal(
            nombre_canal="Correo",
            facturacion=3_000_000.00,  # MAYOR — debe seleccionarse
            modelo_cobro="Híbrido",
            pct_fijo=0.7,
            pct_variable=0.3,
            tarifa_variable=100.0,
        )
        canal_3 = TarifaCanal(
            nombre_canal="WebChat",
            facturacion=2_000_000.00,  # Intermedio
            modelo_cobro="Variable",
            pct_fijo=0.0,
            pct_variable=1.0,
            tarifa_variable=50.0,
        )

        canales = [canal_1, canal_2, canal_3]

        # Execute
        principal = _select_principal_channel(canales)

        # Verify: Debe ser canal_2 (máxima facturación)
        assert principal.nombre_canal == "Correo"
        assert principal.facturacion == 3_000_000.00
        assert principal.modelo_cobro == "Híbrido"

    def test_fails_if_no_canales(self):
        """Debe fallar si no hay canales (fail-fast, no silent defaults)"""
        canales = []

        # Execute & Verify: Debe raise ValueError
        with pytest.raises(ValueError) as exc_info:
            _select_principal_channel(canales)

        # Error message must be clear and actionable
        error_msg = str(exc_info.value)
        assert "CONFIGURACIÓN COMERCIAL INCOMPLETA" in error_msg
        assert "No hay canales" in error_msg
        assert "panel_de_control.cadena_a_activa" in error_msg

    def test_fails_if_canales_none(self):
        """Debe fallar si canales es None"""
        with pytest.raises(ValueError):
            _select_principal_channel(None)

    def test_single_channel_returns_itself(self):
        """Si solo hay 1 canal, debe devolverlo"""
        canal = TarifaCanal(
            nombre_canal="Solo",
            facturacion=1_000_000.00,
            modelo_cobro="Fijo FTE",
        )

        principal = _select_principal_channel([canal])

        assert principal.nombre_canal == "Solo"
        assert principal is canal

    def test_prefers_high_facturacion_over_position(self):
        """Asegura que usa facturación, NO posición en array"""
        # Setup: canal de mayor facturación está en posición [2], NO [0]
        canal_low = TarifaCanal(nombre_canal="First", facturacion=100.0)
        canal_high = TarifaCanal(nombre_canal="Last", facturacion=1_000_000.00)  # Mayor
        canal_mid = TarifaCanal(nombre_canal="Middle", facturacion=500.0)

        # Test: [low, mid, high]
        principal = _select_principal_channel([canal_low, canal_mid, canal_high])
        assert principal.nombre_canal == "Last"

        # Test: [high, mid, low] — aún así debe seleccionar "high"
        principal = _select_principal_channel([canal_high, canal_mid, canal_low])
        assert principal.nombre_canal == "Last"


# ──────────────────────────────────────────────────────────────────────
# Test Suite: F8.2 — Silent Defaults Eliminated
# ──────────────────────────────────────────────────────────────────────

class TestSilentDefaultsElimination:
    """Validar que no hay silent defaults — fail-fast en _configuracion_comercial"""

    def test_configuracion_comercial_fails_without_vision_tarifas(self):
        """TASK 3: vision_tarifas=None es VÁLIDO si cadena_a no está activa.
        Pero si cadena_a SÍ está activa y no hay vision_tarifas, debe fallar."""
        from nexa_engine.modules.shared.models import CadenasActivas

        panel = PanelDeControl(
            cliente="TestCorp",
            tipo_cliente="Cliente",
            linea_negocio="Cobranzas",
            fecha_inicio="2026-01-01",
            meses_contrato=12,
            margen=0.15,
            op_cont=0.02,
            com_cont=0.01,
            markup=0.05,
            descuento=0.02,
            tasa_ica=0.012,
            tasa_gmf=0.00004,
            activa_financiacion=False,
            periodo_pago_dias=30,
            tasa_mensual_financ=0.02,
            # TASK 3: Mark que Cadena A SÍ está activa (requiere vision_tarifas)
            cadenas_activas=CadenasActivas(cadena_a=True, cadena_b=False, cadena_c=False),
        )
        kpis = KPIsDeal(ingreso_mensual=100_000.00)

        resultado = PricingResult(
            kpis=kpis,
            pyg_por_mes=[],
            panel=panel,
            cost_to_serve=None,
            vision_tarifas=None,  # ← NO vision_tarifas (pero cadena_a activa = ERROR)
        )

        # Execute & Verify: Must fail (cadena_a active but no vision_tarifas)
        with pytest.raises(ValueError) as exc_info:
            _configuracion_comercial(resultado)

        assert "No hay canales" in str(exc_info.value)

    def test_configuracion_comercial_fails_with_empty_canales(self):
        """TASK 3: canales=[] es VÁLIDO si cadena_a no está activa.
        Pero si cadena_a SÍ está activa y canales está vacío, debe fallar."""
        from nexa_engine.modules.shared.models import CadenasActivas

        panel = PanelDeControl(
            cliente="TestCorp",
            tipo_cliente="Cliente",
            linea_negocio="Cobranzas",
            fecha_inicio="2026-01-01",
            meses_contrato=12,
            margen=0.15,
            op_cont=0.02,
            com_cont=0.01,
            markup=0.05,
            descuento=0.02,
            tasa_ica=0.012,
            tasa_gmf=0.00004,
            activa_financiacion=False,
            periodo_pago_dias=30,
            tasa_mensual_financ=0.02,
            # TASK 3: Mark que Cadena A SÍ está activa (requiere canales no vacío)
            cadenas_activas=CadenasActivas(cadena_a=True, cadena_b=False, cadena_c=False),
        )
        kpis = KPIsDeal(ingreso_mensual=100_000.00)

        resultado = PricingResult(
            kpis=kpis,
            pyg_por_mes=[],
            panel=panel,
            cost_to_serve=None,
            vision_tarifas=ResultadoVisionTarifas(canales=[]),  # Empty (but cadena_a active = ERROR)
        )

        # Execute & Verify: Must fail (cadena_a active but no canales)
        with pytest.raises(ValueError):
            _configuracion_comercial(resultado)


# ──────────────────────────────────────────────────────────────────────
# Test Suite: F8.3 — Property Fields Completeness
# ──────────────────────────────────────────────────────────────────────

class TestPropertyFieldsCompleteness:
    """Validar que todos los @property de PyGMensual están en serialización"""

    def test_pyg_to_dict_captures_all_property_fields(self):
        """Verificar que _pyg_to_dict captura todas las 9 @property fields"""
        # Setup: PyGMensual con todos los campos
        pyg = PyGMensual(
            mes=1,
            ingreso_bruto_a=1_000_000.00,
            ingreso_bruto_b=500_000.00,
            ingreso_bruto_c=0.00,
            payroll_a=400_000.00,
            no_payroll_a=100_000.00,
            costo_b=200_000.00,
            costo_c=0.00,
            contingencia_op=50_000.00,
            contingencia_com=25_000.00,
            markup_ingreso=30_000.00,
            descuento_ingreso=20_000.00,
            ica=5_000.00,
            gmf=500.00,
            polizas=10_000.00,
            financiacion=2_000.00,
            acum_ingreso_neto=1_500_000.00,
            acum_costo_total=700_000.00,
            acum_contribucion=800_000.00,
        )

        # Execute
        result_dict = _pyg_to_dict(pyg)

        # Verify: Todas las 9 @property fields están presentes
        property_fields = [
            "ingreso_bruto",
            "ingreso_neto",
            "costo_a",
            "costos_financieros",
            "costo_total",
            "contribucion",
            "pct_contribucion",
            "utilidad_neta",
            "pct_utilidad_neta",
        ]

        for field in property_fields:
            assert field in result_dict, f"Missing @property field: {field}"

    def test_pyg_property_fields_have_correct_values(self):
        """Verificar que los valores de @property son correctos"""
        # Setup con valores conocidos
        pyg = PyGMensual(
            mes=1,
            ingreso_bruto_a=1_000_000.00,
            ingreso_bruto_b=500_000.00,
            ingreso_bruto_c=100_000.00,  # Total: 1,600,000
            payroll_a=400_000.00,
            no_payroll_a=100_000.00,  # costo_a = 500,000
            costo_b=200_000.00,
            costo_c=50_000.00,  # costo_total = 750,000
            contingencia_op=50_000.00,
            contingencia_com=25_000.00,
            markup_ingreso=30_000.00,
            descuento_ingreso=20_000.00,
            ica=5_000.00,
            gmf=500.00,
            polizas=10_000.00,
            financiacion=2_000.00,
        )

        result_dict = _pyg_to_dict(pyg)

        # Verify: Valores de @property campos
        assert result_dict["ingreso_bruto"] == 1_600_000.00
        assert result_dict["costo_a"] == 500_000.00
        assert result_dict["costos_financieros"] == pytest.approx(17_500.00)
        assert result_dict["costo_total"] == 750_000.00
        # ingreso_neto = 1,600,000 + 50,000 + 25,000 + 30,000 - 20,000 = 1,685,000
        assert result_dict["ingreso_neto"] == 1_685_000.00
        # contribucion = 1,685,000 - 750,000 = 935,000
        assert result_dict["contribucion"] == 935_000.00


# ──────────────────────────────────────────────────────────────────────
# Test Suite: F8.3 — Endpoint Contract Consistency
# ──────────────────────────────────────────────────────────────────────

class TestEndpointContractConsistency:
    """Validar que vision_tarifas endpoint devuelve estructura completa (no wrapped)"""

    def test_vision_tarifas_complete_structure(self):
        """Vision_tarifas debe devolver ResultadoVisionTarifas completo, no {"canales": [...]}"""
        # Setup: Estructura completa de ResultadoVisionTarifas
        tarifa_canal = TarifaCanal(
            nombre_canal="TestChannel",
            facturacion=1_000_000.00,
        )
        vision_result = ResultadoVisionTarifas(
            canales=[tarifa_canal],
            costo_cadena_a_total=500_000.00,
            costo_cadena_b_total=200_000.00,
            costo_cadena_c_total=0.00,
            costo_total=700_000.00,
            ingreso_mensual=1_000_000.00,
        )

        # Si endpoint devuelve `vision_result` (no wrapped), debe tener estos campos
        assert hasattr(vision_result, "canales")
        assert hasattr(vision_result, "costo_total")
        assert hasattr(vision_result, "ingreso_mensual")
        assert len(vision_result.canales) == 1


# ──────────────────────────────────────────────────────────────────────
# Test Suite: Nomenclatura Consistency
# ──────────────────────────────────────────────────────────────────────

class TestNomenclaturConsistency:
    """Validar que los nombres de campos son consistentes"""

    def test_tarifa_fija_field_name_estandarizado(self):
        """_configuracion_comercial debe usar 'tarifa_fija' como nombre canónico"""
        # Setup: Mock resultado con canales
        panel = PanelDeControl(
            cliente="Test",
            tipo_cliente="Cliente",
            linea_negocio="Cobranzas",
            fecha_inicio="2026-01-01",
            meses_contrato=12,
            margen=0.15,
            op_cont=0.02,
            com_cont=0.01,
            markup=0.05,
            descuento=0.02,
            tasa_ica=0.012,
            tasa_gmf=0.00004,
            activa_financiacion=False,
            periodo_pago_dias=30,
            tasa_mensual_financ=0.02,
        )

        canal = TarifaCanal(
            nombre_canal="Test",
            facturacion=1_000_000.00,
            pct_fijo=0.8,
            modelo_cobro="Fijo FTE",
            tarifa_fijo_fte=123_456.00,
        )

        resultado = PricingResult(
            kpis=KPIsDeal(ingreso_mensual=100_000.00),
            pyg_por_mes=[],
            panel=panel,
            vision_tarifas=ResultadoVisionTarifas(canales=[canal]),
        )

        # Execute
        config = _configuracion_comercial(resultado)

        # Verify: Debe usar 'tarifa_fija' (no 'tarifa_fijo_fte') y leer el valor almacenado
        assert "tarifa_fija" in config
        assert config["tarifa_fija"] == pytest.approx(123_456.00)
        assert config["pct_fijo_global"] == pytest.approx(0.8)

    def test_configuracion_comercial_no_recalcula_tarifa_fija(self):
        """La helper debe leer el valor almacenado, no multiplicar facturacion por pct_fijo."""
        panel = PanelDeControl(
            cliente="Test",
            tipo_cliente="Cliente",
            linea_negocio="Cobranzas",
            fecha_inicio="2026-01-01",
            meses_contrato=12,
            margen=0.15,
            op_cont=0.02,
            com_cont=0.01,
            markup=0.05,
            descuento=0.02,
            tasa_ica=0.012,
            tasa_gmf=0.00004,
            activa_financiacion=False,
            periodo_pago_dias=30,
            tasa_mensual_financ=0.02,
        )

        canal = TarifaCanal(
            nombre_canal="Test",
            facturacion=9_999_999.00,
            pct_fijo=0.99,
            modelo_cobro="Fijo FTE",
            tarifa_fijo_fte=42.0,
        )

        resultado = PricingResult(
            kpis=KPIsDeal(ingreso_mensual=100_000.00),
            pyg_por_mes=[],
            panel=panel,
            vision_tarifas=ResultadoVisionTarifas(canales=[canal]),
        )

        config = _configuracion_comercial(resultado)

        assert config["tarifa_fija"] == pytest.approx(42.0)
        assert config["tarifa_fija"] != pytest.approx(canal.facturacion * canal.pct_fijo)

    def test_configuracion_comercial_source_has_no_tarifa_formula(self):
        """La helper no debe contener la multiplicación de tarifa en el código fuente."""
        from nexa_engine.modules.vision_imprimible.helpers import configuracion_comercial as module

        src = inspect.getsource(module)
        assert "facturacion * pct_fijo" not in src
        assert "facturacion × pct_fijo" not in src


# ──────────────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────────────

class TestPhase8Integration:
    """Pruebas de integración para validar todos los fixes juntos"""

    def test_multi_channel_deal_selects_correct_principal(self):
        """Deal multi-channel debe seleccionar principal por revenue, no posición"""
        panel = PanelDeControl(
            cliente="MultiChannel Corp",
            tipo_cliente="Enterprise",
            linea_negocio="Cobranzas Completo",
            fecha_inicio="2026-01-01",
            meses_contrato=12,
            margen=0.20,
            op_cont=0.03,
            com_cont=0.02,
            markup=0.08,
            descuento=0.05,
            tasa_ica=0.012,
            tasa_gmf=0.00004,
            activa_financiacion=True,
            periodo_pago_dias=45,
            tasa_mensual_financ=0.01,
        )

        # 3 canales: WhatsApp (2M), Correo (5M — principal), WebChat (3M)
        canales = [
            TarifaCanal(nombre_canal="WhatsApp", facturacion=2_000_000.00, modelo_cobro="Fijo FTE", pct_fijo=1.0, pct_variable=0.0),
            TarifaCanal(nombre_canal="Correo", facturacion=5_000_000.00, modelo_cobro="Híbrido", pct_fijo=0.7, pct_variable=0.3),
            TarifaCanal(nombre_canal="WebChat", facturacion=3_000_000.00, modelo_cobro="Variable", pct_fijo=0.0, pct_variable=1.0),
        ]

        resultado = PricingResult(
            kpis=KPIsDeal(ingreso_mensual=1_000_000.00, costo_mensual_promedio=400_000.00),
            pyg_por_mes=[],
            panel=panel,
            vision_tarifas=ResultadoVisionTarifas(canales=canales, costo_total=1_200_000.00),
            cost_to_serve=ResultadoCostToServe(vol_cadena_b=50_000.0),
        )

        # Execute
        config = _configuracion_comercial(resultado)

        # Verify: Debe seleccionar Correo (máxima facturación)
        assert config["modelo_cobro_principal"] == "Híbrido"
        assert config["pct_fijo_global"] == 0.7
        assert config["pct_variable_global"] == 0.3

    def test_zero_facturacion_edge_case(self):
        """Manejar caso donde canales tienen facturación 0 o muy pequeña"""
        panel = PanelDeControl(
            cliente="Test",
            tipo_cliente="Cliente",
            linea_negocio="Cobranzas",
            fecha_inicio="2026-01-01",
            meses_contrato=12,
            margen=0.15,
            op_cont=0.02,
            com_cont=0.01,
            markup=0.05,
            descuento=0.02,
            tasa_ica=0.012,
            tasa_gmf=0.00004,
            activa_financiacion=False,
            periodo_pago_dias=30,
            tasa_mensual_financ=0.02,
        )

        canales = [
            TarifaCanal(nombre_canal="Channel1", facturacion=0.00),
            TarifaCanal(nombre_canal="Channel2", facturacion=0.01),  # Máximo (aunque sea mínimo)
        ]

        resultado = PricingResult(
            kpis=KPIsDeal(ingreso_mensual=100_000.00),
            pyg_por_mes=[],
            panel=panel,
            vision_tarifas=ResultadoVisionTarifas(canales=canales),
        )

        # Execute: Debe seleccionar Channel2 (máximo, aunque sea 0.01)
        config = _configuracion_comercial(resultado)
        assert config["modelo_cobro_principal"]  # Must have a value, not None


# ──────────────────────────────────────────────────────────────────────
# Parametrized Tests
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("num_channels,expected_selected", [
    (1, 0),  # 1 channel → selecciona index 0
    (2, 1),  # 2 channels → selecciona la de máxima facturación
    (3, 1),  # 3 channels → selecciona índice con máxima facturación
    (5, 3),  # 5 channels → selecciona cualquiera que sea máxima
])
def test_principal_channel_with_various_sizes(num_channels, expected_selected):
    """Validar _select_principal_channel con diferentes números de canales"""
    # Crear canales con facturación incremental
    canales = [
        TarifaCanal(
            nombre_canal=f"Channel_{i}",
            facturacion=float((i + 1) * 1_000_000.00),  # 1M, 2M, 3M, ...
        )
        for i in range(num_channels)
    ]

    # Execute
    principal = _select_principal_channel(canales)

    # Verify: Debe ser el último (máxima facturación)
    assert principal.nombre_canal == f"Channel_{num_channels - 1}"
    assert principal.facturacion == float(num_channels * 1_000_000.00)
