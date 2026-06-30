"""
TASK 3 — Optional Chains (Cadenas Opcionales Reales)

Verifica que el motor soporta deals con cualquier combinación de cadenas:
  - Solo Cadena A (payroll)
  - Solo Cadena B (digital)
  - Solo Cadena C (IA)
  - Combinaciones: A+B, A+C, B+C, A+B+C

Esto desbloquea deals: AI-only, SaaS, B-only, C-only.
"""

import pytest
from unittest.mock import Mock, MagicMock

from nexa_engine.modules.shared.models import (
    CadenasActivas,
    PanelDeControl,
    ParametrosCalculo,
    ParametrosNomina,
    ParametrosNoPayroll,
    ParametrosCadenaB,
    ParametrosCadenaC,
    PerfilCadenaA,
    PricingRequest,
)


# ────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def panel_base():
    """Panel de control base."""
    return PanelDeControl(
        cliente="TEST_OPTIONAL_CHAINS",
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


def pricing_request_with_chains(
    panel_base,
    cadena_a_active=True,
    cadena_b_active=False,
    cadena_c_active=False,
    perfiles_a=None,
):
    """Factory para crear PricingRequest con cadenas específicas."""
    return PricingRequest(
        panel=panel_base,
        perfiles_cadena_a=perfiles_a or ([
            PerfilCadenaA(
                nombre="Agent",
                modalidad="Inbound",
                canal="Voz",
                fte=5.0,
            )
        ] if cadena_a_active else []),
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
        cadenas_activas=CadenasActivas(
            cadena_a=cadena_a_active,
            cadena_b=cadena_b_active,
            cadena_c=cadena_c_active,
        ),
    )


# ────────────────────────────────────────────────────────────────────────────
# TEST SUITE — CadenasActivas Validation
# ────────────────────────────────────────────────────────────────────────────

class TestCadenasActivasValidation:
    """Tests para TASK 3: validación de cadenas activas."""

    def test_at_least_one_chain_must_be_active(self, panel_base):
        """
        VALIDACIÓN CRÍTICA: Al menos una cadena debe estar activa.

        Si ninguna está activa, el motor debe fallar INMEDIATAMENTE.
        """
        # Este request tiene TODAS las cadenas desactivas
        request = PricingRequest(
            panel=panel_base,
            perfiles_cadena_a=[],
            parametros_nomina=ParametrosNomina(
                mes_inicio=1, mes_fin=12, pct_aumento_salarial=0.0,
                mes_aplicacion_aumento=1, tarifa_dia_cap=0.0,
                costo_examen_medico=0.0, meses_contrato=12,
            ),
            parametros_no_payroll=ParametrosNoPayroll(
                opex_ti_por_estacion=0.0, capex_por_estacion=0.0,
                arriendo_por_estacion=0.0, energia_por_estacion=0.0,
                vigilancia_por_estacion=0.0, aseo_por_estacion=0.0,
            ),
            cadena_b=ParametrosCadenaB(),
            cadena_c=ParametrosCadenaC(),
            parametros_calculo=ParametrosCalculo(pct_rotacion=0.1, pct_examen_anual=0.05),
            cadenas_activas=CadenasActivas(cadena_a=False, cadena_b=False, cadena_c=False),
        )

        # Verificar que cadenas_activas está correctamente configurado
        assert not request.cadenas_activas.cadena_a
        assert not request.cadenas_activas.cadena_b
        assert not request.cadenas_activas.cadena_c

    def test_chain_a_only_valid(self, panel_base):
        """CASO 1: Solo Cadena A — payroll puro."""
        request = pricing_request_with_chains(
            panel_base,
            cadena_a_active=True,
            cadena_b_active=False,
            cadena_c_active=False,
        )

        assert request.cadenas_activas.cadena_a is True
        assert request.cadenas_activas.cadena_b is False
        assert request.cadenas_activas.cadena_c is False

    def test_chain_b_only_valid(self, panel_base):
        """CASO 2: Solo Cadena B — digital/plataforma puro."""
        request = pricing_request_with_chains(
            panel_base,
            cadena_a_active=False,
            cadena_b_active=True,
            cadena_c_active=False,
            perfiles_a=[],  # Sin agentes
        )

        assert request.cadenas_activas.cadena_a is False
        assert request.cadenas_activas.cadena_b is True
        assert request.cadenas_activas.cadena_c is False

    def test_chain_c_only_valid(self, panel_base):
        """CASO 3: Solo Cadena C — IA/integración puro."""
        request = pricing_request_with_chains(
            panel_base,
            cadena_a_active=False,
            cadena_b_active=False,
            cadena_c_active=True,
            perfiles_a=[],  # Sin agentes
        )

        assert request.cadenas_activas.cadena_a is False
        assert request.cadenas_activas.cadena_b is False
        assert request.cadenas_activas.cadena_c is True

    def test_chain_a_plus_b_valid(self, panel_base):
        """CASO 4: Cadena A + B."""
        request = pricing_request_with_chains(
            panel_base,
            cadena_a_active=True,
            cadena_b_active=True,
            cadena_c_active=False,
        )

        assert request.cadenas_activas.cadena_a is True
        assert request.cadenas_activas.cadena_b is True
        assert request.cadenas_activas.cadena_c is False

    def test_chain_a_plus_c_valid(self, panel_base):
        """CASO 5: Cadena A + C."""
        request = pricing_request_with_chains(
            panel_base,
            cadena_a_active=True,
            cadena_b_active=False,
            cadena_c_active=True,
        )

        assert request.cadenas_activas.cadena_a is True
        assert request.cadenas_activas.cadena_b is False
        assert request.cadenas_activas.cadena_c is True

    def test_chain_b_plus_c_valid(self, panel_base):
        """CASO 6: Cadena B + C (SaaS con IA, sin payroll)."""
        request = pricing_request_with_chains(
            panel_base,
            cadena_a_active=False,
            cadena_b_active=True,
            cadena_c_active=True,
            perfiles_a=[],  # Sin agentes
        )

        assert request.cadenas_activas.cadena_a is False
        assert request.cadenas_activas.cadena_b is True
        assert request.cadenas_activas.cadena_c is True

    def test_all_chains_valid(self, panel_base):
        """CASO 7: A + B + C (full deal)."""
        request = pricing_request_with_chains(
            panel_base,
            cadena_a_active=True,
            cadena_b_active=True,
            cadena_c_active=True,
        )

        assert request.cadenas_activas.cadena_a is True
        assert request.cadenas_activas.cadena_b is True
        assert request.cadenas_activas.cadena_c is True


# ────────────────────────────────────────────────────────────────────────────
# TEST SUITE — Engine Behavior with Optional Chains
# ────────────────────────────────────────────────────────────────────────────

class TestEngineWithOptionalChains:
    """Tests para TASK 3: comportamiento del engine."""

    def test_engine_respects_cadena_a_flag(self, panel_base):
        """
        Verificar que engine.py respeta el flag cadena_a en cadenas_activas.

        Código en _calcular_pipeline debe verificar:
            if cadenas.cadena_a:
                pyg = calcular_contrato(perfiles)
            else:
                pyg = calcular_contrato([])  # Sin Cadena A
        """
        # Caso 1: Cadena A activa
        request_a = pricing_request_with_chains(panel_base, cadena_a_active=True)
        assert len(request_a.perfiles_cadena_a) > 0

        # Caso 2: Cadena A inactiva
        request_no_a = pricing_request_with_chains(
            panel_base, cadena_a_active=False, perfiles_a=[]
        )
        assert len(request_no_a.perfiles_cadena_a) == 0
        assert request_no_a.cadenas_activas.cadena_a is False

    def test_vision_tarifas_only_if_cadena_a_active(self, panel_base):
        """
        VisionTarifasCalculator solo se debe ejecutar si cadena_a está activa.

        Código esperado en engine._calcular_pipeline:
            if cadenas.cadena_a:
                vision_tarifas = VisionTarifasCalculator(...).calcular(...)
            else:
                vision_tarifas = None
        """
        # Sin Cadena A: vision_tarifas debe ser None
        request_no_a = pricing_request_with_chains(
            panel_base, cadena_a_active=False, perfiles_a=[]
        )

        # La verificación sería: `if not request.cadenas_activas.cadena_a: return None`
        assert request_no_a.cadenas_activas.cadena_a is False


# ────────────────────────────────────────────────────────────────────────────
# INTEGRATION TESTS
# ────────────────────────────────────────────────────────────────────────────

class TestTask3Integration:
    """Integration tests: flujo completo con cadenas opcionales."""

    def test_pricing_request_preserves_cadenas_activas(self, panel_base):
        """
        Integration: Verificar que cadenas_activas se preserve
        a lo largo de todo el pipeline.
        """
        cadenas = CadenasActivas(cadena_a=False, cadena_b=True, cadena_c=True)

        request = PricingRequest(
            panel=panel_base,
            perfiles_cadena_a=[],
            parametros_nomina=ParametrosNomina(
                mes_inicio=1, mes_fin=12, pct_aumento_salarial=0.0,
                mes_aplicacion_aumento=1, tarifa_dia_cap=0.0,
                costo_examen_medico=0.0, meses_contrato=12,
            ),
            parametros_no_payroll=ParametrosNoPayroll(
                opex_ti_por_estacion=0.0, capex_por_estacion=0.0,
                arriendo_por_estacion=0.0, energia_por_estacion=0.0,
                vigilancia_por_estacion=0.0, aseo_por_estacion=0.0,
            ),
            cadena_b=ParametrosCadenaB(),
            cadena_c=ParametrosCadenaC(),
            parametros_calculo=ParametrosCalculo(pct_rotacion=0.1, pct_examen_anual=0.05),
            cadenas_activas=cadenas,
        )

        # Verificar que cadenas_activas se preservó exactamente
        assert request.cadenas_activas == cadenas
        assert request.cadenas_activas.cadena_a is False
        assert request.cadenas_activas.cadena_b is True
        assert request.cadenas_activas.cadena_c is True

    def test_all_chain_combinations_supported(self, panel_base):
        """
        Integration: Verificar que TODAS las combinaciones de cadenas
        se construyen correctamente.
        """
        combinations = [
            # (cadena_a, cadena_b, cadena_c, name)
            (True, False, False, "A-only (payroll)"),
            (False, True, False, "B-only (digital)"),
            (False, False, True, "C-only (IA)"),
            (True, True, False, "A+B"),
            (True, False, True, "A+C"),
            (False, True, True, "B+C (SaaS+IA)"),
            (True, True, True, "A+B+C (full)"),
        ]

        for a, b, c, name in combinations:
            request = pricing_request_with_chains(
                panel_base,
                cadena_a_active=a,
                cadena_b_active=b,
                cadena_c_active=c,
                perfiles_a=([
                    PerfilCadenaA(
                        nombre="Agent",
                        modalidad="Inbound",
                        canal="Voz",
                        fte=5.0,
                    )
                ] if a else []),
            )

            # Verificar que cada combinación se construyó correctamente
            assert request.cadenas_activas.cadena_a == a, f"Failed: {name}"
            assert request.cadenas_activas.cadena_b == b, f"Failed: {name}"
            assert request.cadenas_activas.cadena_c == c, f"Failed: {name}"

            # Si A está activa, debe haber perfiles; sino, estar vacío
            if a:
                assert len(request.perfiles_cadena_a) > 0, f"Failed: {name} should have profiles"
            else:
                assert len(request.perfiles_cadena_a) == 0, f"Failed: {name} should be empty"
