"""
BUSINESS_RULES_FIX_2 + FIX_2B — Tests: RiesgoCalculator usa SMMLV canónico HR.

FIX_2  (2026-06-05): RiesgoCalculator migrado a inyección HR via kwarg smmlv=.
FIX_2B (2026-06-05): Fallback inline eliminado. smmlv es argumento obligatorio.
                      business_rules.smmlv eliminado de canonical YAML y del fallback YAML.

Verifica:
  1. riesgo.yaml NO contiene smmlv en constantes_regulatorias.
  2. RiesgoCalculator requiere smmlv kwarg — TypeError si no se pasa.
  3. RiesgoCalculator falla con ValueError si smmlv <= 0.
  4. RiesgoCalculator usa el SMMLV recibido — no hay fallback a 1,423,500.
  5. Umbral requiere_aprobacion = 1000 × SMMLV_HR = 1,750,905,000 COP.
  6. Engine inyecta get_smmlv() (HR) en producción.
  7. aprobaciones_requeridas removido del backend — API field returns [].
  8. Zona de divergencia documentada: 1B–1.751B.
  9. Cost To Serve no fue tocado.
  10. Frozen payloads no fueron tocados.

Fuente documental: docs/refactor/business_rules_source_of_truth_audit.md
"""
from __future__ import annotations

import inspect
from typing import Any

import pytest

from nexa_engine.modules.calculator_motor.formulas.risk import RiesgoCalculator
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


# ---------------------------------------------------------------------------
# Constantes de referencia (BUSINESS_RULES_FIX_2 / FIX_2B)
# ---------------------------------------------------------------------------

_SMMLV_HR_2026: float  = 2_100_000.0     # Expected active HR SMMLV from current active parametrization.
                                          # Not the frozen v2-7 SMMLV.
_MULTIPLICADOR: float  = 1_000.0         # umbral_aprobacion_smmlv (multiplicador)
_UMBRAL_HR_2026: float = _SMMLV_HR_2026 * _MULTIPLICADOR   # 2,100,000,000


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _panel(**kwargs) -> PanelDeControl:
    defaults = dict(
        cliente="TestCo", tipo_cliente="No Grupo Aval",
        linea_negocio="Cobranzas", fecha_inicio="2026-01-01",
        meses_contrato=12, margen=0.1339,
        op_cont=0.05, com_cont=0.05, markup=0.0, descuento=0.0,
        tasa_ica=0.02, tasa_gmf=0.004, activa_financiacion=True,
        periodo_pago_dias=30, tasa_mensual_financ=0.0153,
        ciudad="Bogotá", sede="Bogotá",
        antiguedad_cliente="Más de 1 año",
        pct_ausentismo=0.03,
        indexacion=Indexacion(componente_humano="IPC", frecuencia="Anual"),
    )
    defaults.update(kwargs)
    return PanelDeControl(**defaults)


def _kpis(valor_total_deal: float = 200_000_000.0) -> KPIsDeal:
    return KPIsDeal(
        costo_mensual_promedio=10_000_000.0,
        costo_cadena_a_promedio=5_000_000.0,
        ingreso_mensual=15_000_000.0,
        facturacion_mensual_proyectada=15_000_000.0,
        ingreso_bruto_total=180_000_000.0,
        ingreso_neto_total=180_000_000.0,
        costo_total_contrato=120_000_000.0,
        contribucion_total=60_000_000.0,
        utilidad_neta_total=60_000_000.0,
        pct_utilidad_neta_total=0.10,
        valor_total_deal=valor_total_deal,
        margen_minimo_requerido=0.0,
        cumple_margen_minimo=True,
    )


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


def _perfil() -> PerfilCadenaA:
    return PerfilCadenaA(
        nombre="Agente básico", modalidad="Inbound", canal="Telefónico",
        fte=5, dias_cap_inicial=7, es_soporte=False,
    )


def _cadena_b() -> ParametrosCadenaB:
    return ParametrosCadenaB(canales=[
        CanalCadenaB(nombre="WhatsApp", modalidad="Inbound",
                     producto="WhatsApp", volumen_mensual=1000)
    ])


def _cadena_c() -> ParametrosCadenaC:
    return ParametrosCadenaC(canales=[])


def _calcular(calc: RiesgoCalculator, valor_total_deal: float) -> Any:
    """Helper que corre el calculador. smmlv debe ser pasado al construir calc."""
    return calc.calcular(
        panel=_panel(), kpis=_kpis(valor_total_deal=valor_total_deal),
        pyg_por_mes=_pyg_lista(),
        perfiles_cadena_a=[_perfil()],
        cadena_b=_cadena_b(), cadena_c=_cadena_c(),
    )


# ---------------------------------------------------------------------------
# TAREA 4.1 — FIX_2B: smmlv es obligatorio — no existe fallback
# ---------------------------------------------------------------------------

class TestSmmlvObligatorio:
    """BUSINESS_RULES_FIX_2B: sin smmlv → error explícito."""

    def test_sin_smmlv_kwarg_lanza_typeerror(self):
        """RiesgoCalculator sin smmlv kwarg lanza TypeError."""
        with pytest.raises(TypeError, match="smmlv"):
            RiesgoCalculator()  # type: ignore[call-arg]

    def test_con_config_sin_smmlv_lanza_typeerror(self):
        """RiesgoCalculator(riesgo_config) sin smmlv kwarg lanza TypeError."""
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        provider = ParametrizationProvider.build()
        riesgo_config = provider.get_riesgo_config()
        with pytest.raises(TypeError, match="smmlv"):
            RiesgoCalculator(riesgo_config)  # type: ignore[call-arg]

    def test_smmlv_cero_lanza_valueerror(self):
        """smmlv=0 lanza ValueError con mensaje descriptivo."""
        with pytest.raises(ValueError, match="smmlv > 0"):
            RiesgoCalculator(smmlv=0.0)

    def test_smmlv_negativo_lanza_valueerror(self):
        """smmlv negativo lanza ValueError con mensaje descriptivo."""
        with pytest.raises(ValueError, match="smmlv > 0"):
            RiesgoCalculator(smmlv=-1_000_000.0)

    def test_error_menciona_hr_salarios(self):
        """El ValueError menciona HR-Salarios como fuente correcta."""
        with pytest.raises(ValueError, match="HR-Salarios"):
            RiesgoCalculator(smmlv=0.0)


# ---------------------------------------------------------------------------
# TAREA 4.2 — FIX_2B: canonical YAML no contiene smmlv
# ---------------------------------------------------------------------------

class TestCanonicalYamlNoTieneSmmlv:
    """BUSINESS_RULES_FIX_2B: smmlv eliminado de riesgo.yaml."""

    def test_riesgo_yaml_tiene_umbral_aprobacion_smmlv(self):
        """riesgo.yaml: constantes_regulatorias contiene umbral_aprobacion_smmlv (multiplicador)."""
        from nexa_engine.modules.shared.config.business_rules.loader import (
            load_business_rules,
        )
        reg = load_business_rules("riesgo").get("constantes_regulatorias", {})
        assert "umbral_aprobacion_smmlv" in reg, (
            "riesgo.yaml debe tener umbral_aprobacion_smmlv en constantes_regulatorias "
            "(multiplicador 1000)."
        )
        assert reg["umbral_aprobacion_smmlv"] == 1000.0

    def test_riesgo_yaml_no_tiene_smmlv(self):
        """riesgo.yaml no contiene smmlv en constantes_regulatorias. (FIX_2B)"""
        from nexa_engine.modules.shared.config.business_rules.loader import (
            load_business_rules,
        )
        reg = load_business_rules("riesgo").get("constantes_regulatorias", {})
        assert "smmlv" not in reg, (
            "BUSINESS_RULES_FIX_2B: smmlv debe estar eliminado del canonical YAML. "
            f"Claves presentes: {list(reg.keys())}"
        )


# ---------------------------------------------------------------------------
# TAREA 4.3 — RiesgoCalculator usa el SMMLV recibido — sin fallback
# ---------------------------------------------------------------------------

class TestSmmlvUsadoCorrectamente:
    """Verifica que RiesgoCalculator usa exactamente el smmlv pasado."""

    def test_kwarg_smmlv_es_self_smmlv(self):
        """El kwarg smmlv se asigna como self._smmlv."""
        calc = RiesgoCalculator(smmlv=_SMMLV_HR_2026)
        assert calc._smmlv == _SMMLV_HR_2026

    def test_kwarg_smmlv_entero_se_convierte_a_float(self):
        """smmlv int se convierte a float."""
        calc = RiesgoCalculator(smmlv=1_750_905)
        assert isinstance(calc._smmlv, float)
        assert calc._smmlv == 1_750_905.0

    def test_kwarg_distinto_smmlv_produce_umbral_distinto(self):
        """Dos SMMLV distintos producen umbrales distintos — sin fallback compartido."""
        calc_a = RiesgoCalculator(smmlv=1_000_000.0)
        calc_b = RiesgoCalculator(smmlv=2_000_000.0)
        assert calc_a._umbral_aprobacion_smmlv * calc_a._smmlv == 1_000_000_000.0
        assert calc_b._umbral_aprobacion_smmlv * calc_b._smmlv == 2_000_000_000.0

    def test_umbral_hr_2026_formula_exacta(self):
        """Umbral con HR SMMLV = 1000 × 1,750,905 = 1,750,905,000."""
        calc = RiesgoCalculator(smmlv=_SMMLV_HR_2026)
        assert calc._umbral_aprobacion_smmlv * calc._smmlv == _UMBRAL_HR_2026

    def test_umbral_aprobacion_smmlv_multiplicador_sigue_siendo_1000(self):
        """UMBRAL_APROBACION_SMMLV (multiplicador) sigue siendo 1000 — sin cambio."""
        calc = RiesgoCalculator(smmlv=_SMMLV_HR_2026)
        assert calc._umbral_aprobacion_smmlv == 1000.0


# ---------------------------------------------------------------------------
# TAREA 4.4 — requiere_aprobacion usa SMMLV HR
# ---------------------------------------------------------------------------

class TestRequiereAprobacionConHRSMMLV:

    def test_deal_sobre_umbral_hr_requiere_aprobacion(self):
        """Deal >= 1.751B con HR SMMLV: requiere_aprobacion = True."""
        calc = RiesgoCalculator(smmlv=_SMMLV_HR_2026)
        ev = _calcular(calc, _UMBRAL_HR_2026 + 1.0)
        assert ev.requiere_aprobacion is True

    def test_deal_bajo_umbral_hr_no_requiere_aprobacion(self):
        """Deal < 1.751B con HR SMMLV: requiere_aprobacion = False."""
        calc = RiesgoCalculator(smmlv=_SMMLV_HR_2026)
        ev = _calcular(calc, _UMBRAL_HR_2026 - 1.0)
        assert ev.requiere_aprobacion is False

    def test_deal_pequeno_no_requiere_aprobacion(self):
        """Deal = 50M COP: requiere_aprobacion = False."""
        calc = RiesgoCalculator(smmlv=_SMMLV_HR_2026)
        ev = _calcular(calc, 50_000_000.0)
        assert ev.requiere_aprobacion is False

    def test_zona_divergencia_1b_1751b_bool_es_false(self):
        """Deal en 1.5B (zona 1B–1.751B): requiere_aprobacion = False (umbral HR).

        Excel aprobaciones_requeridas tiene Alta Dirección requerida (deal >= 1B).
        Pero bool requiere_aprobacion es False porque 1.5B < umbral HR 1.751B.
        Esta es la zona de divergencia documentada en FIX_2/FIX_2B.
        """
        deal = 1_500_000_000.0  # 1.5B: > 1B (Excel), < 1.751B (HR)
        calc = RiesgoCalculator(smmlv=_SMMLV_HR_2026)
        ev = _calcular(calc, deal)
        assert ev.requiere_aprobacion is False, (
            f"Deal=1.5B < umbral HR 1.751B → requiere_aprobacion=False. "
            f"Zona de divergencia: Excel (aprobaciones_requeridas) dice Alta Dirección "
            f"requerida, pero bool LEGACY dice False. Ver FIX_2B docs."
        )

    def test_smmlv_distinto_produce_umbral_distinto(self):
        """Con SMMLV menor, el umbral baja: deal que antes requería ahora no requiere."""
        # SMMLV bajo → umbral bajo → deal puede estar sobre el umbral
        smmlv_bajo = 1_000_000.0   # umbral = 1B COP
        smmlv_alto = 2_000_000.0   # umbral = 2B COP
        deal = 1_500_000_000.0     # 1.5B: sobre umbral_bajo, bajo umbral_alto

        calc_bajo = RiesgoCalculator(smmlv=smmlv_bajo)
        calc_alto = RiesgoCalculator(smmlv=smmlv_alto)

        ev_bajo = _calcular(calc_bajo, deal)
        ev_alto = _calcular(calc_alto, deal)

        assert ev_bajo.requiere_aprobacion is True,  "1.5B >= 1B (umbral_bajo) → True"
        assert ev_alto.requiere_aprobacion is False, "1.5B < 2B (umbral_alto) → False"


# ---------------------------------------------------------------------------
# TAREA 4.5 — Criterio 1 también usa SMMLV del kwarg
# ---------------------------------------------------------------------------

class TestCriterio1ConHRSMMLV:

    def test_criterio_1_deal_sobre_umbral_hr_es_alto(self):
        """Criterio 1: deal > 1000×SMMLV_HR → Alto (puntaje 3)."""
        calc = RiesgoCalculator(smmlv=_SMMLV_HR_2026)
        ev = _calcular(calc, _UMBRAL_HR_2026 + 1.0)
        c1 = next(c for c in ev.criterios if c.id == 1)
        assert c1.calificacion == "Alto"
        assert c1.puntaje == 3

    def test_criterio_1_deal_bajo_umbral_hr_es_bajo(self):
        """Criterio 1: deal < 1000×SMMLV_HR → Bajo (puntaje 1)."""
        calc = RiesgoCalculator(smmlv=_SMMLV_HR_2026)
        ev = _calcular(calc, _UMBRAL_HR_2026 - 1.0)
        c1 = next(c for c in ev.criterios if c.id == 1)
        assert c1.calificacion == "Bajo"
        assert c1.puntaje == 1

    def test_criterio_1_umbral_depende_del_smmlv_pasado(self):
        """Criterio 1 alto/bajo cambia con el SMMLV — no hay valor hardcodeado."""
        deal = 1_500_000_000.0  # 1.5B

        # Con smmlv bajo (umbral 1B): deal > umbral → Alto
        calc_bajo = RiesgoCalculator(smmlv=1_000_000.0)
        ev_bajo = _calcular(calc_bajo, deal)
        c1_bajo = next(c for c in ev_bajo.criterios if c.id == 1)

        # Con smmlv alto (umbral 2B): deal < umbral → Bajo
        calc_alto = RiesgoCalculator(smmlv=2_000_000.0)
        ev_alto = _calcular(calc_alto, deal)
        c1_alto = next(c for c in ev_alto.criterios if c.id == 1)

        assert c1_bajo.calificacion == "Alto",  "1.5B > umbral 1B → Alto"
        assert c1_alto.calificacion == "Bajo",  "1.5B < umbral 2B → Bajo"


# ---------------------------------------------------------------------------
# TAREA 4.6 — Engine inyecta get_smmlv() de provider
# ---------------------------------------------------------------------------

class TestEngineInyectaHRSMMLV:

    def test_engine_llama_get_smmlv_en_pipeline(self):
        """engine._calcular_pipeline llama a self._parametrizacion.get_smmlv()."""
        from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
        source = inspect.getsource(NexaPricingEngine._calcular_pipeline)
        assert "get_smmlv()" in source, (
            "engine._calcular_pipeline debe llamar a self._parametrizacion.get_smmlv() "
            "para inyectar el SMMLV canónico HR a RiesgoCalculator. Ver FIX_2B."
        )

    def test_engine_pasa_smmlv_kwarg_a_riesgo_calculator(self):
        """engine._calcular_pipeline pasa smmlv= a RiesgoCalculator."""
        from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
        source = inspect.getsource(NexaPricingEngine._calcular_pipeline)
        assert "smmlv=" in source, (
            "engine._calcular_pipeline debe pasar smmlv=... a RiesgoCalculator. "
            "Ver FIX_2B."
        )
        assert "RiesgoCalculator" in source

    def test_provider_get_smmlv_retorna_hr_value(self):
        """ParametrizationProvider.get_smmlv() retorna 2,100,000 (HR activo)."""
        from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider
        provider = ParametrizationProvider.build()
        smmlv = provider.get_smmlv()
        assert smmlv == _SMMLV_HR_2026, (
            f"provider.get_smmlv() debe retornar {_SMMLV_HR_2026:,.0f} (HR activo). "
            f"Actual: {smmlv:,.0f}"
        )


# ---------------------------------------------------------------------------
# TAREA 4.7 — aprobaciones_requeridas removido del backend (BLOCK_25)
# ---------------------------------------------------------------------------

class TestAprobacionesRemovidoDelBackend:
    """Verifica que aprobaciones_requeridas helper y constantes UMBRAL_* 
    fueron removidos del código de producción."""

    def test_aprobaciones_helper_removido(self):
        """modules/vision_imprimible/helpers/aprobaciones.py ya no existe."""
        import importlib.util
        spec = importlib.util.find_spec("nexa_engine.modules.vision_imprimible.helpers.aprobaciones")
        assert spec is None, (
            "REGRESIÓN: modules/vision_imprimible/helpers/aprobaciones.py "
            "debe haber sido eliminado (BLOCK_25)"
        )

    def test_serializer_helpers_sin_aprobaciones_wrapper(self):
        """serializer_helpers ya no tiene _aprobaciones_requeridas ni import de helpers.aprobaciones."""
        import inspect
        from nexa_engine.modules.calculator_motor.serializers import serializer_helpers
        source = inspect.getsource(serializer_helpers)
        assert "_aprobaciones_requeridas" not in source
        assert "aprobaciones_requeridas as _aprobaciones_requeridas_vi" not in source
        assert "UMBRAL_GERENCIA_FINANCIERA_COP" not in source
        assert "UMBRAL_GERENCIA_GENERAL_COP" not in source
        assert "UMBRAL_ALTA_DIRECCION_COP" not in source

    def test_serializer_helpers_sin_aprobaciones_en_all(self):
        """_aprobaciones_requeridas no está en __all__ de serializer_helpers."""
        from nexa_engine.modules.calculator_motor.serializers import serializer_helpers
        assert "_aprobaciones_requeridas" not in serializer_helpers.__all__

    def test_vision_imprimible_helpers_sin_aprobaciones_export(self):
        """vision_imprimible.helpers.__init__ no exporta aprobaciones ni UMBRAL_*."""
        from nexa_engine.modules.vision_imprimible.helpers import __all__ as helpers_all
        assert "aprobaciones_requeridas" not in helpers_all
        assert "UMBRAL_GERENCIA_FINANCIERA_COP" not in helpers_all
        assert "UMBRAL_GERENCIA_GENERAL_COP" not in helpers_all
        assert "UMBRAL_ALTA_DIRECCION_COP" not in helpers_all


# ---------------------------------------------------------------------------
# TAREA 4.8 — Cost To Serve no fue tocado
# ---------------------------------------------------------------------------

class TestCostToServeNoTocado:

    def test_cost_to_serve_no_importa_riesgo_calculator(self):
        """Módulo cost_to_serve no importa RiesgoCalculator ni SMMLV."""
        try:
            from nexa_engine.modules.vision_cost_to_serve.calculator import CostToServeCalculator
            source = inspect.getsource(CostToServeCalculator)
        except ImportError:
            pytest.skip("CostToServeCalculator no encontrado — módulo no activo")
            return
        assert "RiesgoCalculator" not in source

    def test_riesgo_calculator_no_importa_cost_to_serve(self):
        """RiesgoCalculator no referencia módulo cost_to_serve."""
        source = inspect.getsource(RiesgoCalculator)
        assert "cost_to_serve" not in source.lower()


# ---------------------------------------------------------------------------
# TAREA 4.9 — Frozen payloads no fueron modificados
# ---------------------------------------------------------------------------

class TestFrozenPayloadsNoModificados:

    def test_frozen_adapter_get_smmlv_retorna_frozen_smmlv(self):
        """FrozenParametrizationAdapter.get_smmlv() retorna el smmlv del snapshot frozen."""
        from nexa_engine.modules.parametrizacion.shared.repositories.frozen_parametrization_adapter import (
            FrozenParametrizationAdapter,
        )
        source = inspect.getsource(FrozenParametrizationAdapter.get_smmlv)
        assert "self._frozen.smmlv" in source, (
            "FrozenParametrizationAdapter.get_smmlv() debe retornar self._frozen.smmlv"
        )

    def test_frozen_adapter_get_smmlv_no_llama_hr(self):
        """FrozenParametrizationAdapter.get_smmlv() usa frozen snapshot, no HR live."""
        from nexa_engine.modules.parametrizacion.shared.repositories.frozen_parametrization_adapter import (
            FrozenParametrizationAdapter,
        )
        source = inspect.getsource(FrozenParametrizationAdapter.get_smmlv)
        assert "get_nomina_laboral_params" not in source, (
            "FrozenParametrizationAdapter.get_smmlv() no debe llamar a HR live. "
            "Debe usar el snapshot frozen."
        )

    def test_frozen_adapter_compila_correctamente(self):
        """FrozenParametrizationAdapter importa sin error — firma no fue rota."""
        from nexa_engine.modules.parametrizacion.shared.repositories.frozen_parametrization_adapter import (
            FrozenParametrizationAdapter,
        )
        assert hasattr(FrozenParametrizationAdapter, "get_smmlv")
        assert hasattr(FrozenParametrizationAdapter, "from_version")
