"""
tests/contract/test_vision_imprimible_schema.py
================================================
Contrato de datos: verifica que el JSON producido por pricing_result_to_dict()
contiene TODAS las secciones necesarias para renderizar la Visión Imprimible.

Estos tests son los "guardianes del contrato". Si alguna sección desaparece
del JSON o un campo cambia de tipo, el test falla.

Principio: el frontend NO recalcula. Todo lo que necesita DEBE estar en el JSON.
"""

import json
import pytest
import sys
from pathlib import Path

# WAVE 7: marcado como legacy pre-V2-7 — depende de fixtures V2-4 obsoletas.
# Ver docs/v27/WAVE7_TRIAGE.md (categoría OBSOLETE_FIXTURE).
pytestmark = pytest.mark.legacy

# Setup path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import backend_nexa  # noqa: F401

from nexa_engine.modules.calculator_motor.adapters.user_input_loader import UserInputLoader
from nexa_engine.modules.calculator_motor.context_builder import SimulationContextBuilder
from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict
from nexa_engine.modules.calculator_motor.engine import NexaPricingEngine
from nexa_engine.modules.parametrizacion.services.provider import ParametrizationProvider


# ---------------------------------------------------------------------------
# Fixture: ejecutar el motor con el caso de prueba de referencia
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def result_dict():
    """
    Ejecuta el motor con bancamia_whatsapp_only.json y devuelve el dict JSON.
    Se ejecuta una sola vez para todos los tests del módulo.
    """
    test_case = PROJECT_ROOT / "backend_nexa" / "test_cases" / "bancamia_whatsapp_only.json"
    raw = json.loads(test_case.read_text())
    user_input = UserInputLoader().cargar_desde_dict(raw)

    provider = ParametrizationProvider.build()
    builder = SimulationContextBuilder(provider)
    solicitud = builder.construir(user_input)

    engine = NexaPricingEngine(parametrizacion=provider)
    resultado = engine.calcular(solicitud)

    return pricing_result_to_dict(resultado, result_id="test-contract-run")


# ---------------------------------------------------------------------------
# Sección 01: Ficha del Deal
# ---------------------------------------------------------------------------

class TestFichaDeal:
    CAMPOS_REQUERIDOS = [
        "cliente", "linea_negocio", "ciudad", "sede", "tipo_cliente",
        "antiguedad_cliente", "fecha_inicio", "meses_contrato",
        "periodo_pago_dias", "ajuste_precio_tipo", "ajuste_precio_frecuencia",
    ]

    def test_seccion_presente(self, result_dict):
        assert "ficha_deal" in result_dict

    @pytest.mark.parametrize("campo", CAMPOS_REQUERIDOS)
    def test_campo_presente(self, result_dict, campo):
        assert campo in result_dict["ficha_deal"], f"Falta campo '{campo}' en ficha_deal"

    def test_meses_contrato_es_entero(self, result_dict):
        assert isinstance(result_dict["ficha_deal"]["meses_contrato"], int)

    def test_periodo_pago_dias_es_entero(self, result_dict):
        assert isinstance(result_dict["ficha_deal"]["periodo_pago_dias"], int)

    def test_fecha_inicio_formato_iso(self, result_dict):
        fecha = result_dict["ficha_deal"]["fecha_inicio"]
        assert isinstance(fecha, str) and len(fecha) == 10  # "YYYY-MM-DD"


# ---------------------------------------------------------------------------
# Sección 02: KPIs
# ---------------------------------------------------------------------------

class TestKPIs:
    CAMPOS_REQUERIDOS = [
        "costo_mensual_promedio", "costo_cadena_a_promedio",
        "ingreso_mensual", "facturacion_mensual_proyectada",
        "ingreso_bruto_total", "ingreso_neto_total",
        "costo_total_contrato", "contribucion_total",
        "utilidad_neta_total", "pct_utilidad_neta_total",
        "valor_total_deal", "margen_minimo_requerido", "cumple_margen_minimo",
    ]

    def test_seccion_presente(self, result_dict):
        assert "kpis" in result_dict

    @pytest.mark.parametrize("campo", CAMPOS_REQUERIDOS)
    def test_campo_presente(self, result_dict, campo):
        assert campo in result_dict["kpis"], f"Falta campo '{campo}' en kpis"

    def test_ingreso_mensual_positivo(self, result_dict):
        assert result_dict["kpis"]["ingreso_mensual"] > 0

    def test_valor_total_deal_positivo(self, result_dict):
        assert result_dict["kpis"]["valor_total_deal"] > 0


# ---------------------------------------------------------------------------
# P&G por Mes (fuente de gráficos de evolución)
# ---------------------------------------------------------------------------

class TestPyGPorMes:
    CAMPOS_REQUERIDOS = [
        "mes", "rampup", "payroll_a", "no_payroll_a", "costo_b", "costo_c",
        "financiacion", "polizas", "ica", "gmf",
        "ingreso_bruto_a", "ingreso_bruto_b", "ingreso_bruto_c",
        "contingencia_op", "contingencia_com", "markup_ingreso", "descuento_ingreso",
        # propiedades calculadas
        "ingreso_bruto", "ingreso_neto", "costo_a", "costos_financieros",
        "costo_total", "contribucion", "pct_contribucion",
        "utilidad_neta", "pct_utilidad_neta",
    ]

    def test_seccion_presente(self, result_dict):
        assert "pyg_por_mes" in result_dict

    def test_tiene_al_menos_un_mes(self, result_dict):
        assert len(result_dict["pyg_por_mes"]) > 0

    def test_meses_consecutivos_desde_1(self, result_dict):
        meses = [m["mes"] for m in result_dict["pyg_por_mes"]]
        assert meses[0] == 1
        assert meses == list(range(1, len(meses) + 1))

    @pytest.mark.parametrize("campo", CAMPOS_REQUERIDOS)
    def test_primer_mes_tiene_campo(self, result_dict, campo):
        mes1 = result_dict["pyg_por_mes"][0]
        assert campo in mes1, f"Falta campo '{campo}' en pyg_por_mes[0]"

    def test_longitud_igual_a_meses_contrato(self, result_dict):
        meses_contrato = result_dict["ficha_deal"]["meses_contrato"]
        assert len(result_dict["pyg_por_mes"]) == meses_contrato


# ---------------------------------------------------------------------------
# Sección 04a: Waterfall Promedio
# ---------------------------------------------------------------------------

class TestWaterfallPromedio:
    CAMPOS_REQUERIDOS = [
        "payroll_a", "no_payroll_a", "costo_b", "costo_c",
        "financiacion", "polizas", "ica", "gmf", "costo_total",
        "ingreso_bruto", "contingencias", "markup_descuento",
        "ingreso_neto", "contribucion", "meses_activos",
    ]

    def test_seccion_presente(self, result_dict):
        assert "waterfall_promedio" in result_dict
        assert result_dict["waterfall_promedio"] is not None

    @pytest.mark.parametrize("campo", CAMPOS_REQUERIDOS)
    def test_campo_presente(self, result_dict, campo):
        assert campo in result_dict["waterfall_promedio"], \
            f"Falta campo '{campo}' en waterfall_promedio"

    def test_meses_activos_mayor_cero(self, result_dict):
        assert result_dict["waterfall_promedio"]["meses_activos"] > 0

    def test_payroll_positivo(self, result_dict):
        assert result_dict["waterfall_promedio"]["payroll_a"] > 0

    def test_ingreso_neto_positivo(self, result_dict):
        assert result_dict["waterfall_promedio"]["ingreso_neto"] > 0


# ---------------------------------------------------------------------------
# Sección 03: Configuración Comercial
# ---------------------------------------------------------------------------

class TestConfiguracionComercial:
    CAMPOS_REQUERIDOS = [
        "modelo_cobro_principal", "pct_fijo_global", "pct_variable_global",
        "tarifa_fija", "tarifa_variable", "descuento", "volumen_base_mensual",
        "margen_objetivo", "ingreso_mensual", "costo_mensual_total", "valor_total_deal",
    ]

    def test_seccion_presente(self, result_dict):
        assert "configuracion_comercial" in result_dict

    @pytest.mark.parametrize("campo", CAMPOS_REQUERIDOS)
    def test_campo_presente(self, result_dict, campo):
        assert campo in result_dict["configuracion_comercial"], \
            f"Falta campo '{campo}' en configuracion_comercial"

    def test_pct_fijo_mas_variable_igual_1(self, result_dict):
        cc = result_dict["configuracion_comercial"]
        total = cc["pct_fijo_global"] + cc["pct_variable_global"]
        assert abs(total - 1.0) < 0.001


# ---------------------------------------------------------------------------
# Sección 07: Reglas de Negocio / Contingencias
# ---------------------------------------------------------------------------

class TestReglasNegocio:
    NOMBRES_ESPERADOS = [
        "margen_objetivo",
        "contingencia_operativa",
        "contingencia_comercial",
        "markup",
        "descuento",
    ]
    CAMPOS_POR_REGLA = ["nombre", "label", "aplicado", "status"]
    STATUS_VALIDOS = {"dentro_rango", "bajo_minimo", "excede_maximo"}

    def test_seccion_presente(self, result_dict):
        assert "reglas_negocio" in result_dict

    def test_tiene_5_reglas(self, result_dict):
        assert len(result_dict["reglas_negocio"]) == 5

    def test_nombres_correctos(self, result_dict):
        nombres = [r["nombre"] for r in result_dict["reglas_negocio"]]
        assert nombres == self.NOMBRES_ESPERADOS

    @pytest.mark.parametrize("campo", CAMPOS_POR_REGLA)
    def test_primera_regla_tiene_campo(self, result_dict, campo):
        assert campo in result_dict["reglas_negocio"][0], \
            f"Falta campo '{campo}' en reglas_negocio[0]"

    def test_todos_los_status_son_validos(self, result_dict):
        for regla in result_dict["reglas_negocio"]:
            assert regla["status"] in self.STATUS_VALIDOS, \
                f"Status inválido '{regla['status']}' en regla '{regla['nombre']}'"

    def test_aplicado_es_numerico(self, result_dict):
        for regla in result_dict["reglas_negocio"]:
            assert isinstance(regla["aplicado"], (int, float)), \
                f"Campo 'aplicado' no es numérico en regla '{regla['nombre']}'"


# ---------------------------------------------------------------------------
# Sección 06: Evaluación de Riesgo
# ---------------------------------------------------------------------------

class TestEvaluacionRiesgo:
    CAMPOS_REQUERIDOS = [
        "score_cliente", "score_operativo", "score_total",
        "clasificacion_total", "requiere_aprobacion", "criterios",
    ]
    CAMPOS_CRITERIO = [
        "id", "factor", "categoria", "valor_evaluado",
        "calificacion", "puntaje", "peso",
    ]
    CLASIFICACIONES_VALIDAS = {"Alto", "Medio", "Bajo"}

    def test_seccion_presente(self, result_dict):
        assert "evaluacion_riesgo" in result_dict
        assert result_dict["evaluacion_riesgo"] is not None

    @pytest.mark.parametrize("campo", CAMPOS_REQUERIDOS)
    def test_campo_presente(self, result_dict, campo):
        assert campo in result_dict["evaluacion_riesgo"], \
            f"Falta campo '{campo}' en evaluacion_riesgo"

    def test_tiene_10_criterios(self, result_dict):
        assert len(result_dict["evaluacion_riesgo"]["criterios"]) == 10

    def test_clasificacion_es_valida(self, result_dict):
        cls = result_dict["evaluacion_riesgo"]["clasificacion_total"]
        assert cls in self.CLASIFICACIONES_VALIDAS

    def test_scores_son_numericos(self, result_dict):
        ev = result_dict["evaluacion_riesgo"]
        assert isinstance(ev["score_cliente"], (int, float))
        assert isinstance(ev["score_operativo"], (int, float))
        assert isinstance(ev["score_total"], (int, float))

    def test_requiere_aprobacion_es_bool(self, result_dict):
        assert isinstance(result_dict["evaluacion_riesgo"]["requiere_aprobacion"], bool)

    @pytest.mark.parametrize("campo", CAMPOS_CRITERIO)
    def test_primer_criterio_tiene_campo(self, result_dict, campo):
        c0 = result_dict["evaluacion_riesgo"]["criterios"][0]
        assert campo in c0, f"Falta campo '{campo}' en criterios[0]"


# ---------------------------------------------------------------------------
# Vision Tarifas — campos enriquecidos (Sección 05)
# ---------------------------------------------------------------------------

class TestVisionTarifasEnriquecida:
    CAMPOS_CANAL = [
        "nombre_canal", "modalidad", "producto", "fte", "vol_mensual",
        "modelo_cobro", "pct_fijo", "pct_variable",
        "componente_fijo", "componente_variable",
        "costo_atribuible", "ingreso_bruto", "facturacion",
        "tarifa_fijo_fte", "tarifa_variable", "vol_minimo_transaccion",
    ]

    def test_seccion_presente(self, result_dict):
        assert "vision_tarifas" in result_dict
        assert result_dict["vision_tarifas"] is not None

    def test_tiene_al_menos_un_canal(self, result_dict):
        assert len(result_dict["vision_tarifas"]["canales"]) > 0

    @pytest.mark.parametrize("campo", CAMPOS_CANAL)
    def test_primer_canal_tiene_campo(self, result_dict, campo):
        canal = result_dict["vision_tarifas"]["canales"][0]
        assert campo in canal, f"Falta campo '{campo}' en vision_tarifas.canales[0]"

    def test_pct_fijo_mas_variable_igual_1(self, result_dict):
        for canal in result_dict["vision_tarifas"]["canales"]:
            total = canal["pct_fijo"] + canal["pct_variable"]
            assert abs(total - 1.0) < 0.001, \
                f"pct_fijo + pct_variable ≠ 1 en canal '{canal['nombre_canal']}'"

    def test_facturacion_positiva(self, result_dict):
        for canal in result_dict["vision_tarifas"]["canales"]:
            assert canal["facturacion"] >= 0


# ---------------------------------------------------------------------------
# Cost to Serve
# ---------------------------------------------------------------------------

class TestCostToServe:
    CAMPOS_REQUERIDOS = [
        "cts_cadena_a", "cts_cadena_b", "cts_ponderado",
        "participacion_a", "participacion_b",
        "fte_cadena_a", "vol_cadena_b", "desglose_a",
    ]
    CAMPOS_DESGLOSE = ["nomina", "no_payroll", "total"]

    def test_seccion_presente(self, result_dict):
        assert "cost_to_serve" in result_dict
        assert result_dict["cost_to_serve"] is not None

    @pytest.mark.parametrize("campo", CAMPOS_REQUERIDOS)
    def test_campo_presente(self, result_dict, campo):
        assert campo in result_dict["cost_to_serve"], \
            f"Falta campo '{campo}' en cost_to_serve"

    @pytest.mark.parametrize("campo", CAMPOS_DESGLOSE)
    def test_desglose_a_tiene_campo(self, result_dict, campo):
        assert campo in result_dict["cost_to_serve"]["desglose_a"], \
            f"Falta campo '{campo}' en cost_to_serve.desglose_a"


# ---------------------------------------------------------------------------
# Parity test: matemática inalterada
# ---------------------------------------------------------------------------

class TestParidadMatematica:
    """Verifica que los nuevos campos no hayan alterado los resultados matemáticos."""

    def test_payroll_mes_1_sigue_igual(self, result_dict):
        """payroll_a mes 1 debe ser exactamente 30,017,216.53 COP (Excel match)."""
        mes1 = result_dict["pyg_por_mes"][0]
        assert abs(mes1["payroll_a"] - 30_017_216.53) < 1.0

    def test_financiacion_mes_1_es_cero(self, result_dict):
        """financiacion mes 1 = 0 (no hay mes anterior)."""
        assert result_dict["pyg_por_mes"][0]["financiacion"] == 0.0

    def test_ingreso_neto_mes_1_positivo(self, result_dict):
        """ingreso_neto debe ser positivo (aunque utilidad sea negativa)."""
        assert result_dict["pyg_por_mes"][0]["ingreso_neto"] > 0

    def test_waterfall_payroll_igual_avg_pyg(self, result_dict):
        """waterfall_promedio.payroll_a debe ser el promedio de pyg_por_mes."""
        meses_activos = [m for m in result_dict["pyg_por_mes"]
                         if m["ingreso_neto"] > 0]
        avg_payroll = sum(m["payroll_a"] for m in meses_activos) / len(meses_activos)
        wf_payroll = result_dict["waterfall_promedio"]["payroll_a"]
        assert abs(wf_payroll - avg_payroll) < 0.01  # diferencia < 1 COP

    def test_reglas_negocio_aplican_valores_del_panel(self, result_dict):
        """Los valores 'aplicado' en reglas_negocio coinciden con los del panel."""
        panel = result_dict["panel"]
        reglas = {r["nombre"]: r["aplicado"] for r in result_dict["reglas_negocio"]}

        assert abs(reglas["margen_objetivo"] - panel["margen"]) < 0.00001
        assert abs(reglas["contingencia_operativa"] - panel["op_cont"]) < 0.00001
        assert abs(reglas["contingencia_comercial"] - panel["com_cont"]) < 0.00001
        assert abs(reglas["markup"] - panel["markup"]) < 0.00001
        assert abs(reglas["descuento"] - panel["descuento"]) < 0.00001
