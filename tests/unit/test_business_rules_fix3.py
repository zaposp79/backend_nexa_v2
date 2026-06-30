"""
BUSINESS_RULES_FIX_3 — politicas_comerciales source-of-truth.

Verifica:
  1. porcentaje_acumulado NO está en politicas_comerciales (eliminado — DEAD_FIELD_LEGACY).
  2. panel_dto.ReglasNegocio NO tiene porcentaje_acumulado.
  3. panel_dto.ReglasNegocio tiene descuento (no descuento_volumen).
  4. descuento mapea a panel.descuento en engine_helpers._calcular_reglas_negocio.
  5. imprevistos mapea a panel.imprevistos directamente (campo real en PanelDeControl).
  6. _calcular_reglas_negocio lanza ValueError si una política no tiene campo Panel mapeado.
  7. Las 5 políticas activas tienen fuente real en PanelDeControl.
  8. Con provider, el engine produce 5 reglas (sin porcentaje_acumulado).
  9. Guard detecta política huérfana antes de evaluar.

Fuente documental: docs/refactor/business_rules_source_of_truth_audit.md (FIX_3)

Canonical source: politicas_comerciales.yaml, no business_rules/v2-7.json.
"""
from __future__ import annotations

import inspect
from typing import List

import pytest

from nexa_engine.modules.calculator_motor.helpers.engine_helpers import _calcular_reglas_negocio
from nexa_engine.modules.shared.config.business_rules.loader import load_business_rules
from nexa_engine.modules.shared.models import (
    CanalCadenaB,
    CanalCadenaC,
    Indexacion,
    KPIsDeal,
    PanelDeControl,
    ParametrosCadenaB,
    ParametrosCadenaC,
    PerfilCadenaA,
    PyGMensual,
)

_POLITICAS_ACTIVAS = {
    "contingencia_operativa",
    "contingencia_comercial",
    "markup",
    "descuento",
    "imprevistos",
}


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

def _panel(**kwargs) -> PanelDeControl:
    defaults = dict(
        cliente="TestCo", tipo_cliente="No Grupo Aval",
        linea_negocio="Cobranzas", fecha_inicio="2026-01-01",
        meses_contrato=12, margen=0.1339,
        op_cont=0.06, com_cont=0.05, markup=0.03, descuento=0.05,
        tasa_ica=0.02, tasa_gmf=0.004, activa_financiacion=True,
        periodo_pago_dias=30, tasa_mensual_financ=0.0153,
        ciudad="Bogotá", sede="Bogotá",
        antiguedad_cliente="Más de 1 año",
        pct_ausentismo=0.03,
        imprevistos=0.02,
        indexacion=Indexacion(componente_humano="IPC", frecuencia="Anual"),
    )
    defaults.update(kwargs)
    return PanelDeControl(**defaults)


def _pyg_lista(n: int = 12) -> list:
    return [
        PyGMensual(
            mes=i + 1, rampup=1.0,
            payroll_a=5_000_000.0, no_payroll_a=1_000_000.0,
            costo_b=0.0, costo_c=0.0, financiacion=0.0,
            polizas=500_000.0, ica=100_000.0, gmf=50_000.0,
            ingreso_bruto_a=7_000_000.0, ingreso_bruto_b=0.0, ingreso_bruto_c=0.0,
            contingencia_op=350_000.0, contingencia_com=350_000.0,
            markup_ingreso=0.0, descuento_ingreso=0.0,
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# TAREA 1 — Matriz: porcentaje_acumulado eliminado del canonical YAML
# ---------------------------------------------------------------------------

class TestCanonicalPoliticasComerciales:

    def test_politicas_comerciales_no_tiene_porcentaje_acumulado(self):
        """politicas_comerciales.yaml: porcentaje_acumulado no existe."""
        politicas = load_business_rules("politicas_comerciales")["politicas_comerciales"]
        nombres = {p["nombre"] for p in politicas}
        assert "porcentaje_acumulado" not in nombres, (
            "BUSINESS_RULES_FIX_3: porcentaje_acumulado debe estar eliminado de "
            "politicas_comerciales. Era DEAD_FIELD_LEGACY sin fuente en PanelDeControl. "
            f"Políticas presentes: {nombres}"
        )

    def test_politicas_comerciales_tiene_exactamente_5_activas(self):
        """politicas_comerciales.yaml: exactamente 5 políticas activas."""
        politicas = load_business_rules("politicas_comerciales")["politicas_comerciales"]
        nombres = {p["nombre"] for p in politicas}
        assert nombres == _POLITICAS_ACTIVAS, (
            f"Esperadas: {_POLITICAS_ACTIVAS}\n"
            f"Actuales:  {nombres}"
        )

    def test_todas_politicas_tienen_estructura_minima(self):
        """Cada política activa tiene nombre, label, min, max."""
        politicas = load_business_rules("politicas_comerciales")["politicas_comerciales"]
        for p in politicas:
            assert "nombre" in p and "min" in p and "max" in p, (
                f"Política con estructura incompleta: {p}"
            )


# ---------------------------------------------------------------------------
# TAREA 2 — descuento correctamente mapeado
# ---------------------------------------------------------------------------

class TestDescuentoMapeo:

    def test_canonical_tiene_descuento_no_descuento_volumen(self):
        """politicas_comerciales.yaml: 'descuento' existe, 'descuento_volumen' no existe."""
        nombres = {p["nombre"] for p in load_business_rules("politicas_comerciales")["politicas_comerciales"]}
        assert "descuento" in nombres, "politicas_comerciales debe tener 'descuento'"
        assert "descuento_volumen" not in nombres, (
            "'descuento_volumen' fue renombrado a 'descuento' en FIX_1."
        )

    def test_engine_helpers_panel_fields_tiene_descuento(self):
        """engine_helpers._calcular_reglas_negocio usa 'descuento' → panel.descuento."""
        source = inspect.getsource(_calcular_reglas_negocio)
        assert '"descuento"' in source or "'descuento'" in source, (
            "_calcular_reglas_negocio debe mapear 'descuento' a panel.descuento"
        )
        assert "descuento_volumen" not in source, (
            "_calcular_reglas_negocio no debe referenciar 'descuento_volumen'"
        )

    def test_panel_dto_tiene_descuento_no_descuento_volumen(self):
        """panel_dto.ReglasNegocio tiene 'descuento', no 'descuento_volumen'."""
        from nexa_engine.modules.panel.dto.panel_dto import ReglasNegocio
        fields = ReglasNegocio.model_fields
        assert "descuento" in fields, (
            "ReglasNegocio DTO debe tener campo 'descuento' (renombrado de descuento_volumen)."
        )
        assert "descuento_volumen" not in fields, (
            "ReglasNegocio DTO no debe tener 'descuento_volumen' (stale — FIX_3)."
        )

    def test_calcular_reglas_negocio_descuento_usa_panel_descuento(self):
        """_calcular_reglas_negocio con política 'descuento' retorna panel.descuento como aplicado."""
        panel = _panel(descuento=0.07)
        politicas_mock = [{"nombre": "descuento", "label": "Descuento", "min": 0.0, "max": 0.15}]

        class MockProvider:
            def get_politicas_comerciales(self):
                return politicas_mock

        reglas = _calcular_reglas_negocio(panel, parametrizacion=MockProvider())
        descuento_regla = next(r for r in reglas if r.nombre == "descuento")
        assert descuento_regla.aplicado == 0.07, (
            f"aplicado debe ser panel.descuento=0.07. Obtenido: {descuento_regla.aplicado}"
        )

    def test_descuento_min_es_cero(self):
        """descuento.min = 0.0 (acepta descuento cero)."""
        politicas = load_business_rules("politicas_comerciales")["politicas_comerciales"]
        desc = next(p for p in politicas if p["nombre"] == "descuento")
        assert desc["min"] == 0.0, f"descuento.min debe ser 0.0. Actual: {desc['min']}"


# ---------------------------------------------------------------------------
# TAREA 3 — imprevistos correctamente mapeado
# ---------------------------------------------------------------------------

class TestImprevistosMapeo:

    def test_imprevistos_es_campo_real_en_panel_de_control(self):
        """PanelDeControl tiene campo 'imprevistos' (no se necesita getattr)."""
        panel = _panel(imprevistos=0.05)
        assert hasattr(panel, "imprevistos"), "PanelDeControl debe tener campo imprevistos"
        assert panel.imprevistos == 0.05

    def test_engine_helpers_no_usa_getattr_para_imprevistos(self):
        """engine_helpers usa panel.imprevistos directo (no getattr). (FIX_3)"""
        source = inspect.getsource(_calcular_reglas_negocio)
        # Debe usar panel.imprevistos directamente
        assert "panel.imprevistos" in source, (
            "_calcular_reglas_negocio debe usar panel.imprevistos directamente. "
            "FIX_3 eliminó el getattr — el campo es real en PanelDeControl."
        )
        assert 'getattr(panel, "imprevistos"' not in source, (
            "No debe usar getattr para imprevistos. Es un campo real en PanelDeControl."
        )

    def test_calcular_reglas_negocio_imprevistos_usa_panel_imprevistos(self):
        """_calcular_reglas_negocio retorna panel.imprevistos como aplicado."""
        panel = _panel(imprevistos=0.03)
        politicas_mock = [{"nombre": "imprevistos", "label": "Imprevistos", "min": 0.0, "max": 1.0}]

        class MockProvider:
            def get_politicas_comerciales(self):
                return politicas_mock

        reglas = _calcular_reglas_negocio(panel, parametrizacion=MockProvider())
        imp_regla = next(r for r in reglas if r.nombre == "imprevistos")
        assert imp_regla.aplicado == 0.03, (
            f"aplicado debe ser panel.imprevistos=0.03. Obtenido: {imp_regla.aplicado}"
        )


# ---------------------------------------------------------------------------
# TAREA 4 — Guard contra defaults silenciosos
# ---------------------------------------------------------------------------

class TestGuardPoliticaSinFuentePanel:

    def test_politica_sin_campo_panel_lanza_valueerror(self):
        """Política en JSON sin campo Panel mapeado → ValueError (no default 0.0)."""
        panel = _panel()
        politicas_con_huerfana = [
            {"nombre": "campo_inexistente_xyzabc", "label": "Fake", "min": 0.0, "max": 1.0},
        ]

        class MockProvider:
            def get_politicas_comerciales(self):
                return politicas_con_huerfana

        with pytest.raises(ValueError, match="campo_inexistente_xyzabc"):
            _calcular_reglas_negocio(panel, parametrizacion=MockProvider())

    def test_politica_sin_campo_panel_error_menciona_panel_de_control(self):
        """El ValueError menciona PanelDeControl como la fuente requerida."""
        panel = _panel()

        class MockProvider:
            def get_politicas_comerciales(self):
                return [{"nombre": "porcentaje_acumulado", "label": "Test", "min": 0.0, "max": 0.15}]

        with pytest.raises(ValueError, match="PanelDeControl"):
            _calcular_reglas_negocio(panel, parametrizacion=MockProvider())

    def test_porcentaje_acumulado_en_provider_lanza_valueerror(self):
        """Si porcentaje_acumulado volviera a aparecer en el provider → ValueError inmediato."""
        panel = _panel()

        class MockProvider:
            def get_politicas_comerciales(self):
                return [{"nombre": "porcentaje_acumulado", "label": "Dead", "min": 0.0, "max": 0.15}]

        with pytest.raises(ValueError) as exc_info:
            _calcular_reglas_negocio(panel, parametrizacion=MockProvider())

        assert "porcentaje_acumulado" in str(exc_info.value)

    def test_politicas_activas_no_levantan_guard(self):
        """Las 5 políticas activas no disparan el guard — todas mapeadas en Panel."""
        panel = _panel()
        politicas_validas = [
            {"nombre": "contingencia_operativa", "label": "CO", "min": 0.025, "max": 0.12},
            {"nombre": "contingencia_comercial", "label": "CC", "min": 0.04,  "max": 0.07},
            {"nombre": "markup",                 "label": "MK", "min": 0.02,  "max": 0.08},
            {"nombre": "descuento",              "label": "DS", "min": 0.0,   "max": 0.15},
            {"nombre": "imprevistos",            "label": "IM", "min": 0.0,   "max": 1.0},
        ]

        class MockProvider:
            def get_politicas_comerciales(self):
                return politicas_validas

        # No debe lanzar
        reglas = _calcular_reglas_negocio(panel, parametrizacion=MockProvider())
        assert len(reglas) == 5


# ---------------------------------------------------------------------------
# TAREA 5 — Políticas activas correctas (con provider de producción)
# ---------------------------------------------------------------------------

class TestPoliticasActivasConProvider:

    def test_provider_retorna_5_politicas_activas(self):
        """Con provider de producción, get_politicas_comerciales retorna 5 políticas."""
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        provider = ParametrizationProvider.build()
        politicas = provider.get_politicas_comerciales()
        nombres = {p["nombre"] for p in politicas}
        assert nombres == _POLITICAS_ACTIVAS, (
            f"Esperadas: {_POLITICAS_ACTIVAS}\n"
            f"Actuales:  {nombres}"
        )

    def test_calcular_reglas_negocio_con_provider_retorna_5_reglas(self):
        """Engine con provider real produce 5 ReglaNegocios (sin porcentaje_acumulado)."""
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        provider = ParametrizationProvider.build()
        panel = _panel()
        reglas = _calcular_reglas_negocio(panel, pyg_por_mes=_pyg_lista(), parametrizacion=provider)
        nombres = {r.nombre for r in reglas}
        assert nombres == _POLITICAS_ACTIVAS, (
            f"Reglas esperadas: {_POLITICAS_ACTIVAS}\n"
            f"Reglas obtenidas: {nombres}"
        )

    def test_cada_regla_tiene_aplicado_de_panel_real(self):
        """Cada regla tiene el valor real de panel (no un default 0.0 huérfano)."""
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        provider = ParametrizationProvider.build()
        panel = _panel(op_cont=0.06, com_cont=0.05, markup=0.03,
                       descuento=0.05, imprevistos=0.02)
        reglas = _calcular_reglas_negocio(panel, parametrizacion=provider)
        reglas_map = {r.nombre: r for r in reglas}

        assert reglas_map["contingencia_operativa"].aplicado == 0.06
        assert reglas_map["contingencia_comercial"].aplicado == 0.05
        assert reglas_map["markup"].aplicado == 0.03
        assert reglas_map["descuento"].aplicado == 0.05
        assert reglas_map["imprevistos"].aplicado == 0.02

    def test_no_existe_regla_porcentaje_acumulado_en_resultado(self):
        """porcentaje_acumulado no aparece en reglas calculadas con provider real."""
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        provider = ParametrizationProvider.build()
        panel = _panel()
        reglas = _calcular_reglas_negocio(panel, parametrizacion=provider)
        nombres = {r.nombre for r in reglas}
        assert "porcentaje_acumulado" not in nombres, (
            "BUSINESS_RULES_FIX_3: porcentaje_acumulado no debe aparecer en reglas "
            "calculadas. Fue eliminado del JSON y del engine. "
            f"Nombres obtenidos: {nombres}"
        )


# ---------------------------------------------------------------------------
# TAREA 6 — panel_dto y panel_service limpios
# ---------------------------------------------------------------------------

class TestPanelDtoLimpio:

    def test_reglas_negocio_dto_no_tiene_porcentaje_acumulado(self):
        """ReglasNegocio DTO no tiene campo porcentaje_acumulado."""
        from nexa_engine.modules.panel.dto.panel_dto import ReglasNegocio
        fields = set(ReglasNegocio.model_fields.keys())
        assert "porcentaje_acumulado" not in fields, (
            "BUSINESS_RULES_FIX_3: porcentaje_acumulado debe estar eliminado del DTO. "
            f"Campos presentes: {fields}"
        )

    def test_reglas_negocio_dto_tiene_descuento(self):
        """ReglasNegocio DTO tiene campo 'descuento' (no 'descuento_volumen')."""
        from nexa_engine.modules.panel.dto.panel_dto import ReglasNegocio
        fields = set(ReglasNegocio.model_fields.keys())
        assert "descuento" in fields
        assert "descuento_volumen" not in fields

    def test_panel_service_build_no_usa_descuento_volumen(self):
        """PanelService.build_parametros no llama _rango('descuento_volumen')."""
        from nexa_engine.modules.panel.services.panel_service import PanelService
        source = inspect.getsource(PanelService.build_parametros)
        assert "descuento_volumen" not in source, (
            "BUSINESS_RULES_FIX_3: build_parametros no debe referenciar 'descuento_volumen'. "
            "Usar 'descuento' (renombrado en FIX_1)."
        )

    def test_panel_service_build_no_usa_porcentaje_acumulado(self):
        """PanelService.build_parametros no usa porcentaje_acumulado (eliminado FIX_3)."""
        from nexa_engine.modules.panel.services.panel_service import PanelService
        source = inspect.getsource(PanelService.build_parametros)
        assert "porcentaje_acumulado" not in source, (
            "BUSINESS_RULES_FIX_3: build_parametros no debe referenciar 'porcentaje_acumulado'. "
            "Fue eliminado del DTO y del JSON."
        )
