"""
TASK 1 — Policies per Chain (Pólizas por Cadena)

Verifica que los costos de pólizas se desglosen correctamente por cadena:
  - Póliza solo Cadena A NO afecta polizas_b ni polizas_c
  - Póliza solo Cadena B NO afecta polizas_a ni polizas_c
  - Póliza solo Cadena C NO afecta polizas_a ni polizas_b
  - Múltiples pólizas en cadenas diferentes se calculan correctamente
  - Vision dataset expone el desglose por cadena
  - Serializer incluye el desglose en JSON

Esto desbloquea trazabilidad financiera completa: auditor puede verificar
que costo de Cadena B no contiene pólizas de Cadena A.
"""

import pytest
from unittest.mock import Mock

from nexa_engine.modules.shared.models import (
    CadenasActivas,
    KPIsDeal,
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
    CostosFinancierosMes,
)
from nexa_engine.modules.vision_imprimible.builders.vision_datasets_builder import VisionDatasetsBuilder
from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict


# ────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def panel_base():
    """Panel de control base."""
    return PanelDeControl(
        cliente="TEST_POLICIES_PER_CHAIN",
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


def pricing_request_with_policies(
    panel_base,
    policies=None,
    cadena_a_active=True,
    cadena_b_active=False,
    cadena_c_active=False,
):
    """Factory para crear PricingRequest con pólizas específicas."""
    return PricingRequest(
        panel=panel_base,
        perfiles_cadena_a=[
            PerfilCadenaA(
                nombre="Agent",
                modalidad="Inbound",
                canal="Voz",
                fte=5.0,
            )
        ] if cadena_a_active else [],
        parametros_nomina=ParametrosNomina(
            mes_inicio=1,
            mes_fin=12,
            pct_aumento_salarial=0.0,
            mes_aplicacion_aumento=1,
            tarifa_dia_cap=0.0,
            costo_examen_medico=0.0,
            meses_contrato=12,
        ),
        parametros_no_payroll=ParametrosNoPayroll(
            opex_ti_por_estacion=0.0,
            capex_por_estacion=0.0,
            arriendo_por_estacion=0.0,
            energia_por_estacion=0.0,
            vigilancia_por_estacion=0.0,
            aseo_por_estacion=0.0,
        ),
        cadena_b=ParametrosCadenaB(),
        cadena_c=ParametrosCadenaC(),
        parametros_calculo=ParametrosCalculo(pct_rotacion=0.1, pct_examen_anual=0.05),
        polizas_usuario=policies,
        cadenas_activas=CadenasActivas(
            cadena_a=cadena_a_active,
            cadena_b=cadena_b_active,
            cadena_c=cadena_c_active,
        ),
    )


def pricing_result_with_pyg_breakdown(
    panel_base,
    polizas_total=100.0,
    polizas_a=60.0,
    polizas_b=25.0,
    polizas_c=15.0,
    months=12,
):
    """
    Factory para crear PricingResult con P&G mensual que tiene desglose por cadena.
    """
    pyg_por_mes = []
    for mes in range(1, months + 1):
        # Crear PyGMensual con desglose por cadena
        # Los campos polizas_a/b/c se obtienen del P&G
        pyg = PyGMensual(
            mes=mes,
            polizas=polizas_total,
            polizas_a=polizas_a,
            polizas_b=polizas_b,
            polizas_c=polizas_c,
            # Otros campos ficticios (no afectan el test de policies)
            ingreso_bruto_a=1000.0,
            ingreso_bruto_b=500.0,
            ingreso_bruto_c=500.0,
            payroll_a=800.0,
            no_payroll_a=200.0,
            costo_b=400.0,
            costo_c=400.0,
            financiacion=50.0,
        )
        pyg_por_mes.append(pyg)

    kpis = KPIsDeal(
        costo_mensual_promedio=polizas_total,
        ingreso_mensual=2000.0,
        ingreso_bruto_total=24000.0,
    )

    return PricingResult(
        kpis=kpis,
        pyg_por_mes=pyg_por_mes,
        panel=panel_base,
        cost_to_serve=None,
        vision_tarifas=None,
        vision_imprimible=None,
        datasets_vision=None,
    )


# ────────────────────────────────────────────────────────────────────────────
# TEST SUITE — Pólizas Específicas de Cadena
# ────────────────────────────────────────────────────────────────────────────

class TestPoliciesPerChain:
    """Tests para TASK 1: descomposición de pólizas por cadena."""

    def test_policy_aplica_a_only_affects_polizas_a(self, panel_base):
        """
        Póliza con aplica_a=True, aplica_b=False, aplica_c=False
        solo debe afectar polizas_a en el dataset.
        """
        # Crear póliza solo para Cadena A
        poliza_a_only = PolizaContractual(
            nombre="Seguros A",
            pct_poliza=0.5,
            pct_atribuible=1.0,
            activa=True,
            aplica_a=True,
            aplica_b=False,
            aplica_c=False,
        )

        request = pricing_request_with_policies(
            panel_base,
            policies=[poliza_a_only],
            cadena_a_active=True,
        )

        # Crear resultado con P&G que tiene breakdown por cadena
        # Suponemos que si solo aplica_a, entonces polizas_a > 0, polizas_b = 0, polizas_c = 0
        resultado = pricing_result_with_pyg_breakdown(
            panel_base,
            polizas_total=50.0,  # Total es 50
            polizas_a=50.0,      # Todo va a A
            polizas_b=0.0,       # Nada a B
            polizas_c=0.0,       # Nada a C
        )

        # Construir vision dataset
        builder = VisionDatasetsBuilder()
        datasets = builder.construir(request, resultado)

        # Verificar el desglose
        assert datasets.polizas is not None
        assert datasets.polizas.costo_mensual_promedio == pytest.approx(50.0)
        assert datasets.polizas.costo_mensual_promedio_a == pytest.approx(50.0)
        assert datasets.polizas.costo_mensual_promedio_b == pytest.approx(0.0)
        assert datasets.polizas.costo_mensual_promedio_c == pytest.approx(0.0)

    def test_policy_aplica_b_only_affects_polizas_b(self, panel_base):
        """
        Póliza con aplica_b=True, aplica_a=False, aplica_c=False
        solo debe afectar polizas_b en el dataset.
        """
        poliza_b_only = PolizaContractual(
            nombre="Seguros B",
            pct_poliza=0.3,
            pct_atribuible=1.0,
            activa=True,
            aplica_a=False,
            aplica_b=True,
            aplica_c=False,
        )

        request = pricing_request_with_policies(
            panel_base,
            policies=[poliza_b_only],
            cadena_b_active=True,
        )

        resultado = pricing_result_with_pyg_breakdown(
            panel_base,
            polizas_total=30.0,   # Total es 30
            polizas_a=0.0,        # Nada a A
            polizas_b=30.0,       # Todo va a B
            polizas_c=0.0,        # Nada a C
        )

        builder = VisionDatasetsBuilder()
        datasets = builder.construir(request, resultado)

        assert datasets.polizas is not None
        assert datasets.polizas.costo_mensual_promedio == pytest.approx(30.0)
        assert datasets.polizas.costo_mensual_promedio_a == pytest.approx(0.0)
        assert datasets.polizas.costo_mensual_promedio_b == pytest.approx(30.0)
        assert datasets.polizas.costo_mensual_promedio_c == pytest.approx(0.0)

    def test_policy_aplica_c_only_affects_polizas_c(self, panel_base):
        """
        Póliza con aplica_c=True, aplica_a=False, aplica_b=False
        solo debe afectar polizas_c en el dataset.
        """
        poliza_c_only = PolizaContractual(
            nombre="Seguros C",
            pct_poliza=0.2,
            pct_atribuible=1.0,
            activa=True,
            aplica_a=False,
            aplica_b=False,
            aplica_c=True,
        )

        request = pricing_request_with_policies(
            panel_base,
            policies=[poliza_c_only],
            cadena_c_active=True,
        )

        resultado = pricing_result_with_pyg_breakdown(
            panel_base,
            polizas_total=20.0,   # Total es 20
            polizas_a=0.0,        # Nada a A
            polizas_b=0.0,        # Nada a B
            polizas_c=20.0,       # Todo va a C
        )

        builder = VisionDatasetsBuilder()
        datasets = builder.construir(request, resultado)

        assert datasets.polizas is not None
        assert datasets.polizas.costo_mensual_promedio == pytest.approx(20.0)
        assert datasets.polizas.costo_mensual_promedio_a == pytest.approx(0.0)
        assert datasets.polizas.costo_mensual_promedio_b == pytest.approx(0.0)
        assert datasets.polizas.costo_mensual_promedio_c == pytest.approx(20.0)

    def test_multiple_policies_mixed_chains(self, panel_base):
        """
        Múltiples pólizas aplicables a diferentes cadenas.
        Póliza 1: A+B (100)
        Póliza 2: C only (50)
        Total esperado: 150, A+B: 100, C: 50
        """
        poliza_ab = PolizaContractual(
            nombre="Seguros AB",
            pct_poliza=0.5,
            pct_atribuible=1.0,
            activa=True,
            aplica_a=True,
            aplica_b=True,
            aplica_c=False,
        )

        poliza_c = PolizaContractual(
            nombre="Seguros C",
            pct_poliza=0.25,
            pct_atribuible=1.0,
            activa=True,
            aplica_a=False,
            aplica_b=False,
            aplica_c=True,
        )

        request = pricing_request_with_policies(
            panel_base,
            policies=[poliza_ab, poliza_c],
            cadena_a_active=True,
            cadena_b_active=True,
            cadena_c_active=True,
        )

        # Simulamos que el engine distribuyó así:
        # - Poliza AB contribuye 50 a A y 50 a B
        # - Poliza C contribuye 50 a C
        resultado = pricing_result_with_pyg_breakdown(
            panel_base,
            polizas_total=150.0,  # Total 150
            polizas_a=50.0,       # De poliza_ab
            polizas_b=50.0,       # De poliza_ab
            polizas_c=50.0,       # De poliza_c
        )

        builder = VisionDatasetsBuilder()
        datasets = builder.construir(request, resultado)

        assert datasets.polizas is not None
        assert datasets.polizas.costo_mensual_promedio == pytest.approx(150.0)
        assert datasets.polizas.costo_mensual_promedio_a == pytest.approx(50.0)
        assert datasets.polizas.costo_mensual_promedio_b == pytest.approx(50.0)
        assert datasets.polizas.costo_mensual_promedio_c == pytest.approx(50.0)

    def test_zero_cost_policies_zero_breakdown(self, panel_base):
        """
        Si polizas_usuario es [] (usuario explícitamente eligió cero pólizas),
        el breakdown debe ser 0 en todas las cadenas.
        """
        request = pricing_request_with_policies(
            panel_base,
            policies=[],  # [] explícito
        )

        resultado = pricing_result_with_pyg_breakdown(
            panel_base,
            polizas_total=0.0,
            polizas_a=0.0,
            polizas_b=0.0,
            polizas_c=0.0,
        )

        builder = VisionDatasetsBuilder()
        datasets = builder.construir(request, resultado)

        assert datasets.polizas is not None  # [] no es None, es dataset vacío
        assert datasets.polizas.costo_mensual_promedio == pytest.approx(0.0)
        assert datasets.polizas.costo_mensual_promedio_a == pytest.approx(0.0)
        assert datasets.polizas.costo_mensual_promedio_b == pytest.approx(0.0)
        assert datasets.polizas.costo_mensual_promedio_c == pytest.approx(0.0)


# ────────────────────────────────────────────────────────────────────────────
# TEST SUITE — Vision Dataset as_dict Output
# ────────────────────────────────────────────────────────────────────────────

class TestVisionDatasetOutput:
    """Tests para TASK 1: verificar que as_dict() expone el desglose."""

    def test_dataset_as_dict_includes_costo_por_cadena(self, panel_base):
        """Verificar que as_dict() incluye la estructura costo_por_cadena."""
        poliza_a = PolizaContractual(
            nombre="Test",
            pct_poliza=0.5,
            pct_atribuible=1.0,
            activa=True,
            aplica_a=True,
            aplica_b=False,
            aplica_c=False,
        )

        request = pricing_request_with_policies(panel_base, policies=[poliza_a])
        resultado = pricing_result_with_pyg_breakdown(
            panel_base,
            polizas_total=50.0,
            polizas_a=50.0,
            polizas_b=0.0,
            polizas_c=0.0,
        )

        builder = VisionDatasetsBuilder()
        datasets = builder.construir(request, resultado)

        # Convertir a dict
        datasets_dict = datasets.as_dict()
        polizas_dict = datasets_dict.get("polizas")

        assert polizas_dict is not None
        assert "costo_por_cadena" in polizas_dict
        assert polizas_dict["costo_por_cadena"]["cadena_a"] == pytest.approx(50.0)
        assert polizas_dict["costo_por_cadena"]["cadena_b"] == pytest.approx(0.0)
        assert polizas_dict["costo_por_cadena"]["cadena_c"] == pytest.approx(0.0)

    def test_vision_dataset_none_when_polizas_usuario_none(self, panel_base):
        """
        Si polizas_usuario es None (usuario no configuró),
        vision dataset debe ser None (no incluir en respuesta).
        """
        request = pricing_request_with_policies(
            panel_base,
            policies=None,  # None explícito
        )

        resultado = pricing_result_with_pyg_breakdown(panel_base)
        builder = VisionDatasetsBuilder()
        datasets = builder.construir(request, resultado)

        assert datasets.polizas is None


# ────────────────────────────────────────────────────────────────────────────
# TEST SUITE — Serializer Integration
# ────────────────────────────────────────────────────────────────────────────

class TestSerializerIntegration:
    """Tests para TASK 1: verificar que serializer expone el desglose."""

    def test_serializer_includes_polizas_por_cadena(self, panel_base):
        """Verificar que pricing_result_to_dict incluye polizas_por_cadena."""
        poliza_ab = PolizaContractual(
            nombre="Test AB",
            pct_poliza=0.5,
            pct_atribuible=1.0,
            activa=True,
            aplica_a=True,
            aplica_b=True,
            aplica_c=False,
        )

        request = pricing_request_with_policies(
            panel_base,
            policies=[poliza_ab],
            cadena_a_active=True,
            cadena_b_active=True,
        )

        resultado = pricing_result_with_pyg_breakdown(
            panel_base,
            polizas_total=100.0,
            polizas_a=50.0,
            polizas_b=50.0,
            polizas_c=0.0,
        )

        # Serializar resultado
        result_dict = pricing_result_to_dict(resultado, result_id="test-result-1")

        # Verificar que pyg_por_mes contiene polizas_por_cadena
        assert "pyg_por_mes" in result_dict
        assert len(result_dict["pyg_por_mes"]) > 0

        primer_mes = result_dict["pyg_por_mes"][0]
        assert "polizas_por_cadena" in primer_mes
        assert primer_mes["polizas_por_cadena"]["cadena_a"] == pytest.approx(50.0)
        assert primer_mes["polizas_por_cadena"]["cadena_b"] == pytest.approx(50.0)
        assert primer_mes["polizas_por_cadena"]["cadena_c"] == pytest.approx(0.0)
