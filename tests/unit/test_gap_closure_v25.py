"""
tests/unit/test_gap_closure_v25.py
====================================
Tests de cierre de gaps de fidelidad funcional vs Excel V2-5.

Gaps cubiertos:
  GAP-PYG-2  — costo_operativo y componente_financiero en PyGMensual
  GAP-PCG-1  — EscenarioComercial model y VisionTarifasCalculator con escenarios
  GAP-PCG-2  — PolizaConfiguracion model con aplica_a/b/c y extensión
  GAP-VIS-1  — VisionImprimibleBuilder composición completa
  GAP-RULES-1 — Archivos YAML de business rules existen
"""

from __future__ import annotations

import os
from dataclasses import field
from typing import List

import pytest

from nexa_engine.modules.shared.models import (
    EscenarioComercial,
    EvaluacionRiesgo,
    KPIsDeal,
    PanelDeControl,
    ParametrosCadenaB,
    PerfilCadenaA,
    PolizaConfiguracion,
    PolizaContractual,
    PyGMensual,
    ResultadoVisionTarifas,
    TarifaCanal,
    WaterfallPromedio,
)
from nexa_engine.modules.calculator_motor.dto.user_inputs import EscenarioComercialInput


# ─── Helpers ────────────────────────────────────────────────────────────────

def _panel_minimal(**overrides) -> PanelDeControl:
    defaults = dict(
        cliente="TestCo", tipo_cliente="No Grupo Aval",
        linea_negocio="SAC", ciudad="Bogota", sede="Bogota",
        fecha_inicio="2026-01-01", meses_contrato=12,
        margen=0.18, op_cont=0.025, com_cont=0.0,
        markup=0.0, descuento=0.0,
        tasa_ica=0.01, tasa_gmf=0.004,
        activa_financiacion=False, periodo_pago_dias=30,
        tasa_mensual_financ=0.0,
    )
    defaults.update(overrides)
    return PanelDeControl(**defaults)


def _pyg_mes(mes: int = 1, **overrides) -> PyGMensual:
    defaults = dict(
        mes=mes, rampup=1.0,
        ingreso_bruto_a=1_000_000.0, ingreso_bruto_b=200_000.0, ingreso_bruto_c=0.0,
        contingencia_op=30_000.0, contingencia_com=0.0,
        markup_ingreso=0.0, descuento_ingreso=0.0,
        payroll_a=600_000.0, no_payroll_a=100_000.0,
        costo_b=200_000.0, costo_c=0.0,
        ica=12_000.0, gmf=4_000.0, polizas=8_000.0, financiacion=0.0,
        imprevistos_ingreso=0.0, comision_administracion=0.0,
    )
    defaults.update(overrides)
    return PyGMensual(**defaults)


# ─── GAP-PYG-2: costo_operativo y componente_financiero ─────────────────────

class TestGapPYG2:
    """
    Valida que PyGMensual exponga costo_operativo y componente_financiero
    como propiedades computadas, y que costo_total == costo_operativo.

    Excel: Visión P&G C30 = costo_operativo (= A+B+C, sin financieros).
           Visión P&G C65 = componente_financiero (suma ICA+GMF+Pólizas+Fin+ComisAdm).
    """

    def test_costo_operativo_equals_costo_total(self):
        """costo_total == costo_operativo siempre (invariante de dominio)."""
        m = _pyg_mes()
        assert m.costo_operativo == m.costo_total
        assert m.costo_operativo == m.payroll_a + m.no_payroll_a + m.costo_b + m.costo_c

    def test_costo_operativo_formula(self):
        """costo_operativo = costo_a + costo_b + costo_c."""
        m = _pyg_mes(payroll_a=500_000, no_payroll_a=100_000, costo_b=200_000, costo_c=50_000)
        assert m.costo_operativo == 850_000.0

    def test_componente_financiero_equals_costos_financieros(self):
        """componente_financiero == costos_financieros siempre."""
        m = _pyg_mes(ica=12_000, gmf=4_000, polizas=8_000, financiacion=0.0, comision_administracion=5_000)
        assert m.componente_financiero == m.costos_financieros
        assert m.componente_financiero == 12_000 + 4_000 + 8_000 + 5_000

    def test_componente_financiero_excludes_operativo(self):
        """Los costos financieros NO están en costo_operativo (separación correcta)."""
        m = _pyg_mes()
        # La suma de operativo + financiero no es redundante — son categorías distintas
        assert m.costo_operativo + m.componente_financiero != m.costo_operativo

    def test_contribucion_uses_costo_operativo_not_financiero(self):
        """
        contribucion = ingreso_neto - costo_total (sin financieros).
        Excel C74 = C27 - C30 (no incluye C65 en la resta).
        """
        m = _pyg_mes(
            ingreso_bruto_a=1_200_000, contingencia_op=36_000, imprevistos_ingreso=0,
            payroll_a=600_000, no_payroll_a=100_000, costo_b=200_000, costo_c=0,
            ica=12_000, gmf=4_000, polizas=8_000,
        )
        ingreso_neto = m.ingreso_neto
        costo_op     = m.costo_operativo
        assert m.contribucion == pytest.approx(ingreso_neto - costo_op)
        # Los financieros NO se restan en contribucion (solo en utilidad_neta si aplica)
        assert m.contribucion != ingreso_neto - costo_op - m.componente_financiero

    def test_costo_operativo_is_computed_not_stored(self):
        """costo_operativo y componente_financiero son @property, no campos almacenados."""
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(PyGMensual)}
        assert "costo_operativo" not in field_names
        assert "componente_financiero" not in field_names


# ─── GAP-PCG-2: PolizaConfiguracion ─────────────────────────────────────────

class TestGapPCG2PolizaConfiguracion:
    """
    Valida el modelo PolizaConfiguracion con aplica_a/b/c y extensión.
    Excel: Pólizas - Costo Financiacion rows 171-187.
    """

    def test_poliza_configuracion_basica(self):
        """Póliza de Cumplimiento con configuración básica de Cadena A."""
        p = PolizaConfiguracion(
            nombre="Póliza de Cumplimiento",
            activa=True,
            porcentaje_poliza=0.0062,
            porcentaje_atribuible=0.20,
            aplica_a=True, aplica_b=False, aplica_c=False,
        )
        assert p.tasa_efectiva == pytest.approx(0.0062 * 0.20)
        assert p.tasa_efectiva_a == pytest.approx(0.0062 * 0.20)
        assert p.tasa_efectiva_b == 0.0

    def test_poliza_inactiva_tasa_cero(self):
        p = PolizaConfiguracion(
            nombre="Póliza de Salarios", activa=False,
            porcentaje_poliza=0.0119, porcentaje_atribuible=0.10,
        )
        assert p.tasa_efectiva == 0.0
        assert p.tasa_efectiva_a == 0.0
        assert p.tasa_efectiva_b == 0.0

    def test_poliza_cadena_b(self):
        """Póliza de Seriedad solo aplica a Cadena B."""
        p = PolizaConfiguracion(
            nombre="Póliza de Seriedad", activa=True,
            porcentaje_poliza=0.005, porcentaje_atribuible=1.0,
            aplica_a=False, aplica_b=True, aplica_c=False,
        )
        assert p.tasa_efectiva_a == 0.0
        assert p.tasa_efectiva_b == pytest.approx(0.005)

    def test_se_extiende_default_false(self):
        """Por defecto, extensión desactivada (Excel: todos con ¿Se extiende?=False)."""
        p = PolizaConfiguracion(
            nombre="Test", activa=True,
            porcentaje_poliza=0.01, porcentaje_atribuible=0.5,
        )
        assert p.se_extiende is False
        assert p.meses_extension == 0

    def test_poliza_contractual_backward_compat(self):
        """PolizaContractual mantiene aplica_a=True por defecto (backward compat)."""
        p = PolizaContractual(
            nombre="Legacy Poliza", activa=True,
            pct_poliza=0.01, pct_atribuible=0.5,
        )
        assert p.aplica_a is True
        assert p.aplica_b is False
        assert p.aplica_c is False
        assert p.tasa_efectiva == pytest.approx(0.005)

    def test_poliza_contractual_con_aplica_b(self):
        """PolizaContractual puede marcarse para Cadena B."""
        p = PolizaContractual(
            nombre="B Poliza", activa=True,
            pct_poliza=0.0062, pct_atribuible=0.20,
            aplica_a=False, aplica_b=True,
        )
        assert p.aplica_a is False
        assert p.aplica_b is True


# ─── GAP-PCG-1: EscenarioComercial ──────────────────────────────────────────

class TestGapPCG1EscenarioComercial:
    """
    Valida el modelo EscenarioComercial y su integración en VisionTarifas.
    Excel: Panel!A81:D113.
    """

    def test_escenario_modelo_fijo(self):
        """Escenario 1: Inbound Voz Fijo (pct_fijo=1.0)."""
        e = EscenarioComercial(
            escenario=1, modalidad="Inbound", canal="Voz",
            modelo_cobro="Fijo",
            componente_fijo_tipo="Tiempo", componente_fijo_pct=1.0,
            componente_variable_tipo=None, componente_variable_pct=0.0,
        )
        assert e.componente_fijo_pct + e.componente_variable_pct == pytest.approx(1.0)
        assert e.escenario == 1

    def test_escenario_modelo_hibrido(self):
        """Escenario 3: Inbound WebChat Híbrido (70% fijo / 30% variable)."""
        e = EscenarioComercial(
            escenario=3, modalidad="Inbound", canal="WebChat",
            modelo_cobro="Híbrido",
            componente_fijo_tipo="FTE", componente_fijo_pct=0.7,
            componente_variable_tipo="Transacción", componente_variable_pct=0.3,
        )
        assert e.componente_fijo_pct == pytest.approx(0.7)
        assert e.componente_variable_pct == pytest.approx(0.3)

    def test_escenario_input_mapping(self):
        """EscenarioComercialInput mapea a EscenarioComercial correctamente."""
        inp = EscenarioComercialInput(
            escenario=2, modalidad="Inbound", canal="WhatsApp",
            modelo_cobro="Fijo",
            componente_fijo_tipo="FTE", componente_fijo_pct=1.0,
        )
        # Mapeo manual (como lo hace context_builder)
        e = EscenarioComercial(
            escenario=inp.escenario,
            modalidad=inp.modalidad,
            canal=inp.canal,
            modelo_cobro=inp.modelo_cobro,
            componente_fijo_tipo=inp.componente_fijo_tipo,
            componente_fijo_pct=inp.componente_fijo_pct,
            componente_variable_tipo=inp.componente_variable_tipo,
            componente_variable_pct=inp.componente_variable_pct,
        )
        assert e.canal == "WhatsApp"
        assert e.componente_fijo_pct == 1.0

    def test_vision_tarifas_con_escenario_overrides_pct_fijo(self):
        """
        Cuando VisionTarifasCalculator recibe un escenario, usa su pct_fijo
        en vez del del perfil.
        """
        from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import VisionTarifasCalculator

        perfil = PerfilCadenaA(
            nombre="Inbound Voz", modalidad="Inbound", canal="Voz",
            fte=10.0, salario_base=1_550_000,
            modelo_cobro="Fijo FTE", pct_fijo=1.0,  # perfil dice 100% fijo
        )
        # Escenario dice Híbrido 70/30
        escenario = EscenarioComercial(
            escenario=1, modalidad="Inbound", canal="Voz",
            modelo_cobro="Híbrido",
            componente_fijo_tipo="FTE", componente_fijo_pct=0.7,
            componente_variable_tipo="Transacción", componente_variable_pct=0.3,
        )

        pyg_mes = _pyg_mes(ingreso_bruto_a=1_000_000, costo_b=0, costo_c=0)
        panel = _panel_minimal()
        params_b = ParametrosCadenaB()

        calc = VisionTarifasCalculator(
            [perfil], params_b, panel,
            escenarios=[escenario],
        )
        resultado = calc.calcular([pyg_mes])
        assert len(resultado.canales) == 1
        canal = resultado.canales[0]
        # pct_fijo viene del escenario (0.7), no del perfil (1.0)
        assert canal.pct_fijo == pytest.approx(0.7)
        assert canal.pct_variable == pytest.approx(0.3)
        assert canal.modelo_cobro == "Híbrido"

    def test_vision_tarifas_sin_escenarios_usa_perfil(self):
        """Backward compat: sin escenarios, VisionTarifas usa modelo_cobro del perfil."""
        from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import VisionTarifasCalculator

        perfil = PerfilCadenaA(
            nombre="Inbound Voz", modalidad="Inbound", canal="Voz",
            fte=5.0, salario_base=1_550_000,
            modelo_cobro="Fijo FTE", pct_fijo=1.0,
        )
        pyg_mes = _pyg_mes(ingreso_bruto_a=500_000, costo_b=0)
        panel = _panel_minimal()
        params_b = ParametrosCadenaB()

        calc = VisionTarifasCalculator([perfil], params_b, panel, escenarios=None)
        resultado = calc.calcular([pyg_mes])
        assert len(resultado.canales) == 1
        assert resultado.canales[0].pct_fijo == pytest.approx(1.0)
        assert resultado.canales[0].modelo_cobro == "Fijo FTE"


# ─── GAP-VIS-1: VisionImprimible ────────────────────────────────────────────

class TestGapVIS1VisionImprimible:
    """
    Valida que VisionImprimibleBuilder construye la composición correcta.
    Excel: Hoja 'Visión Imprimible' V2-5.
    """

    def _build_minimal_vision(self):
        from nexa_engine.modules.vision_imprimible.builders.vision_imprimible_builder import VisionImprimibleBuilder

        panel = _panel_minimal(
            cliente="Bancamia", linea_negocio="SAC",
            fecha_inicio="2026-01-01", meses_contrato=12,
            margen=0.18,
        )
        kpis = KPIsDeal(
            contribucion_total=5_000_000.0,
            ingreso_mensual=60_000_000.0,
        )
        pyg_list = [_pyg_mes(mes=i+1) for i in range(12)]

        return VisionImprimibleBuilder().construir(
            panel=panel, kpis=kpis, pyg_por_mes=pyg_list,
        )

    def test_ficha_del_deal(self):
        v = self._build_minimal_vision()
        assert v.ficha.cliente == "Bancamia"
        assert v.ficha.servicio == "SAC"
        assert v.ficha.duracion == "12 meses"
        assert v.ficha.fecha_inicio == "2026-01-01"

    def test_economics_margen(self):
        v = self._build_minimal_vision()
        assert v.economics.margen == pytest.approx(0.18)
        assert v.economics.contribucion_total == pytest.approx(5_000_000.0)

    def test_evolucion_mensual_length(self):
        v = self._build_minimal_vision()
        assert len(v.evolucion_mensual.meses) == 12
        assert len(v.evolucion_mensual.ingresos_neto) == 12
        assert len(v.evolucion_mensual.costos_total) == 12
        assert len(v.evolucion_mensual.contribucion) == 12

    def test_evolucion_mensual_values(self):
        """Cada mes de evolución tiene valores derivados del PyGMensual correspondiente."""
        from nexa_engine.modules.vision_imprimible.builders.vision_imprimible_builder import VisionImprimibleBuilder

        panel = _panel_minimal()
        kpis  = KPIsDeal()
        pyg_list = [_pyg_mes(mes=1), _pyg_mes(mes=2, payroll_a=700_000)]
        v = VisionImprimibleBuilder().construir(panel=panel, kpis=kpis, pyg_por_mes=pyg_list)

        assert v.evolucion_mensual.meses == [1, 2]
        assert v.evolucion_mensual.costos_total[0] == pytest.approx(pyg_list[0].costo_total)
        assert v.evolucion_mensual.costos_total[1] == pytest.approx(pyg_list[1].costo_total)

    def test_waterfall_pasado_correctamente(self):
        from nexa_engine.modules.vision_imprimible.builders.vision_imprimible_builder import VisionImprimibleBuilder

        panel = _panel_minimal()
        kpis  = KPIsDeal()
        wf    = WaterfallPromedio(payroll_a=600_000, ingreso_bruto=1_200_000)
        v = VisionImprimibleBuilder().construir(
            panel=panel, kpis=kpis, pyg_por_mes=[_pyg_mes()],
            waterfall=wf,
        )
        assert v.waterfall is not None
        assert v.waterfall.payroll_a == pytest.approx(600_000)

    def test_escenarios_incluidos(self):
        from nexa_engine.modules.vision_imprimible.builders.vision_imprimible_builder import VisionImprimibleBuilder

        panel = _panel_minimal()
        kpis  = KPIsDeal()
        escenarios = [
            EscenarioComercial(1, "Inbound", "Voz", "Fijo", "Tiempo", 1.0, None, 0.0),
            EscenarioComercial(2, "Inbound", "WhatsApp", "Fijo", "FTE", 1.0, None, 0.0),
        ]
        v = VisionImprimibleBuilder().construir(
            panel=panel, kpis=kpis, pyg_por_mes=[_pyg_mes()],
            escenarios=escenarios,
        )
        assert len(v.escenarios) == 2
        assert v.escenarios[0].canal == "Voz"

    def test_vision_imprimible_en_pricing_result(self):
        """PricingResult tiene campo vision_imprimible (no None cuando engine lo popula)."""
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(__import__(
            "nexa_engine.modules.shared.models", fromlist=["PricingResult"]
        ).PricingResult)}
        assert "vision_imprimible" in field_names


# ─── GAP-RULES-1: Archivos YAML de business rules ───────────────────────────

class TestGapRules1YamlFiles:
    """
    Valida que los archivos YAML de business rules existen y tienen contenido.
    """

    BASE = os.path.join(
        os.path.dirname(__file__), "..", "..", "modules", "shared", "config", "business_rules"
    )

    def test_operaciones_yaml_exists(self):
        path = os.path.join(self.BASE, "operaciones.yaml")
        assert os.path.isfile(path), f"Falta: {path}"

    def test_margenes_yaml_exists(self):
        path = os.path.join(self.BASE, "margenes.yaml")
        assert os.path.isfile(path), f"Falta: {path}"

    def test_operaciones_yaml_has_required_keys(self):
        """Los campos requeridos por el task están presentes en el archivo YAML."""
        path = os.path.join(self.BASE, "operaciones.yaml")
        with open(path) as f:
            content = f.read()
        assert "horas_semanales" in content
        assert "semanas_al_mes" in content
        assert "breaks_diarios_min" in content
        assert "42" in content        # horas_semanales: 42
        assert "4.33" in content      # semanas_al_mes: 4.33

    def test_margenes_yaml_has_required_keys(self):
        """Los márgenes mínimos por línea están documentados."""
        path = os.path.join(self.BASE, "margenes.yaml")
        with open(path) as f:
            content = f.read()
        assert "margen_minimo_por_linea" in content
        assert "Cobranzas" in content
        assert "SAC" in content
        assert "0.17" in content      # margen mínimo Cobranzas


# ─── FASE 3 — GAP-RULES-1: BusinessRulesConfig loader ───────────────────────

class TestGapRules1Loader:
    """
    Valida que el loader de business rules lee los YAML correctamente
    y expone las constantes operativas y márgenes en runtime.
    """

    def test_loader_importable(self):
        from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules, BusinessRulesConfig
        rules = get_business_rules()
        assert isinstance(rules, BusinessRulesConfig)

    def test_horas_semanales(self):
        from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules
        rules = get_business_rules()
        assert rules.horas_semanales == pytest.approx(42.0)

    def test_semanas_al_mes(self):
        from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules
        rules = get_business_rules()
        assert rules.semanas_al_mes == pytest.approx(4.33)

    def test_total_breaks_min(self):
        """total_breaks = 30+20+5+5+5 = 65 min/día según operaciones.yaml (HM R18C10=65).
        Incluye formacion_min=20 (HM R14C10=20, "Promedio de capacitaciones al día")."""
        from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules
        rules = get_business_rules()
        expected = rules.breaks_diarios_min + rules.formacion_min + rules.deslogueos_min + rules.coaching_min + rules.pausa_activa_min
        assert rules.total_breaks_min == pytest.approx(expected)
        assert rules.total_breaks_min == pytest.approx(65.0)

    def test_horas_loggeadas_semanales_menos_que_semanales(self):
        from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules
        rules = get_business_rules()
        assert rules.horas_loggeadas_semanales < rules.horas_semanales

    def test_margen_minimo_cobranzas(self):
        from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules
        rules = get_business_rules()
        assert rules.margen_minimo("Cobranzas") == pytest.approx(0.17)

    def test_margen_minimo_sac(self):
        from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules
        rules = get_business_rules()
        assert rules.margen_minimo("SAC") == pytest.approx(0.17)

    def test_margen_objetivo_cobranzas(self):
        from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules
        rules = get_business_rules()
        assert rules.margen_objetivo("Cobranzas") == pytest.approx(0.18)

    def test_margen_linea_desconocida_none(self):
        from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules
        rules = get_business_rules()
        assert rules.margen_minimo("LineaInexistente") is None

    def test_singleton_cached(self):
        """get_business_rules() devuelve la misma instancia (lru_cache)."""
        from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules
        a = get_business_rules()
        b = get_business_rules()
        assert a is b


# ─── FASE 3 — GAP-PCG-1: Multi-escenario iteration ──────────────────────────

class TestGapPCG1MultiEscenario:
    """
    Valida que VisionTarifasCalculator itera escenarios independientemente.
    Cada EscenarioComercial produce su propio TarifaCanal.
    Múltiples escenarios con el mismo canal → múltiples TarifaCanal.
    """

    def _perfil(self, canal="Voz", modalidad="Inbound", pct_fijo=1.0, modelo_cobro="Fijo FTE", **kw):
        from nexa_engine.modules.shared.models import PerfilCadenaA
        return PerfilCadenaA(
            nombre=f"{modalidad} {canal}", modalidad=modalidad, canal=canal,
            fte=10.0, salario_base=1_500_000, pct_fijo=pct_fijo, modelo_cobro=modelo_cobro,
            **kw,
        )

    def _run_calc(self, perfiles, escenarios, avg_costo_a=700_000):
        from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import VisionTarifasCalculator
        from nexa_engine.modules.shared.models import ParametrosCadenaB

        panel = _panel_minimal()
        params_b = ParametrosCadenaB()
        pyg_mes = _pyg_mes(payroll_a=avg_costo_a)
        calc = VisionTarifasCalculator(perfiles, params_b, panel, escenarios=escenarios)
        return calc.calcular([pyg_mes])

    def test_dos_escenarios_distintos_dos_canales(self):
        """2 escenarios con canales distintos → 2 TarifaCanal."""
        perfiles = [self._perfil("Voz", "Inbound"), self._perfil("Chat", "Inbound")]
        escenarios = [
            EscenarioComercial(1, "Inbound", "Voz", "Fijo FTE", "FTE", 1.0, None, 0.0),
            EscenarioComercial(2, "Inbound", "Chat", "Fijo FTE", "FTE", 1.0, None, 0.0),
        ]
        r = self._run_calc(perfiles, escenarios)
        assert len(r.canales) == 2

    def test_dos_escenarios_mismo_canal_dos_tarifas(self):
        """2 escenarios con mismo canal/modalidad → 2 TarifaCanal independientes (no Dict drop)."""
        perfiles = [self._perfil("Voz", "Inbound")]
        escenarios = [
            EscenarioComercial(1, "Inbound", "Voz", "Fijo FTE", "FTE", 1.0, None, 0.0),
            EscenarioComercial(2, "Inbound", "Voz", "Híbrido", "FTE", 0.7, "Transacción", 0.3),
        ]
        r = self._run_calc(perfiles, escenarios)
        # Ambos escenarios producen TarifaCanal — no se descarta el segundo
        assert len(r.canales) == 2
        pct_fijos = sorted(c.pct_fijo for c in r.canales)
        assert pct_fijos[0] == pytest.approx(0.7)
        assert pct_fijos[1] == pytest.approx(1.0)

    def test_escenario_sin_perfil_matchante_ignorado(self):
        """Escenario sin perfil Cadena A coincidente no genera TarifaCanal."""
        perfiles = [self._perfil("Voz", "Inbound")]
        escenarios = [
            EscenarioComercial(1, "Inbound", "Voz", "Fijo FTE", "FTE", 1.0, None, 0.0),
            EscenarioComercial(2, "Outbound", "Chat", "Fijo FTE", "FTE", 1.0, None, 0.0),
        ]
        r = self._run_calc(perfiles, escenarios)
        assert len(r.canales) == 1  # Chat Outbound no tiene perfil → ignorado

    def test_sin_escenarios_fallback_por_perfil(self):
        """Sin escenarios, produce 1 TarifaCanal por perfil agente (backward compat)."""
        perfiles = [self._perfil("Voz", "Inbound"), self._perfil("Chat", "Inbound")]
        r = self._run_calc(perfiles, escenarios=None)
        assert len(r.canales) == 2

    def test_escenario_override_pct_fijo(self):
        """pct_fijo del escenario sobreescribe al del perfil."""
        perfiles = [self._perfil("Voz", "Inbound", pct_fijo=1.0)]
        escenarios = [
            EscenarioComercial(1, "Inbound", "Voz", "Híbrido", "FTE", 0.6, "Transacción", 0.4),
        ]
        r = self._run_calc(perfiles, escenarios)
        assert r.canales[0].pct_fijo == pytest.approx(0.6)
        assert r.canales[0].pct_variable == pytest.approx(0.4)

    def test_escenario_override_modelo_cobro(self):
        """modelo_cobro del escenario sobreescribe al del perfil."""
        perfiles = [self._perfil("Voz", "Inbound", modelo_cobro="Fijo FTE")]
        escenarios = [
            EscenarioComercial(1, "Inbound", "Voz", "Variable", None, 0.0, "Transacción", 1.0),
        ]
        r = self._run_calc(perfiles, escenarios)
        assert r.canales[0].modelo_cobro == "Variable"


# ─── FASE 3 — GAP-VIS-1: ComparativoEscenario (Sección 05) ─────────────────

class TestGapVIS1Seccion05:
    """
    Valida que VisionImprimibleBuilder construye la Sección 05
    (Comparativo de Escenarios) correctamente.
    Excel: Visión Imprimible rows 73-78.
    """

    def test_comparativo_vacio_sin_escenarios(self):
        from nexa_engine.modules.vision_imprimible.builders.vision_imprimible_builder import VisionImprimibleBuilder
        v = VisionImprimibleBuilder().construir(
            panel=_panel_minimal(), kpis=KPIsDeal(), pyg_por_mes=[_pyg_mes()],
        )
        assert v.comparativo_escenarios == []

    def test_comparativo_una_fila_por_escenario(self):
        from nexa_engine.modules.vision_imprimible.builders.vision_imprimible_builder import VisionImprimibleBuilder
        escenarios = [
            EscenarioComercial(1, "Inbound", "Voz", "Fijo FTE", "FTE", 1.0, None, 0.0),
            EscenarioComercial(2, "Inbound", "Chat", "Híbrido", "FTE", 0.7, "Transacción", 0.3),
        ]
        v = VisionImprimibleBuilder().construir(
            panel=_panel_minimal(), kpis=KPIsDeal(), pyg_por_mes=[_pyg_mes()],
            escenarios=escenarios,
        )
        assert len(v.comparativo_escenarios) == 2

    def test_comparativo_campos_correctos(self):
        from nexa_engine.modules.vision_imprimible.builders.vision_imprimible_builder import VisionImprimibleBuilder
        escenarios = [
            EscenarioComercial(1, "Inbound", "Voz", "Fijo FTE", "FTE", 1.0, None, 0.0),
        ]
        v = VisionImprimibleBuilder().construir(
            panel=_panel_minimal(), kpis=KPIsDeal(), pyg_por_mes=[_pyg_mes()],
            escenarios=escenarios,
        )
        row = v.comparativo_escenarios[0]
        assert row.escenario == "Escenario 1"
        assert row.modalidad_canal == "Inbound - Voz"
        assert row.modelo_cobro == "Fijo FTE"

    def test_comparativo_escenario_dataclass_en_models(self):
        """ComparativoEscenario es importable desde domain.models."""
        from nexa_engine.modules.shared.models import ComparativoEscenario
        c = ComparativoEscenario(
            escenario="Escenario 1",
            modalidad_canal="Inbound - Voz",
            modelo_cobro="Fijo FTE",
        )
        assert c.escenario == "Escenario 1"


# ─── FASE 3 — GAP-PCG-2: Pólizas extension per-mes ─────────────────────────

class TestGapPCG2ExtensionPerMes:
    """
    Valida que CostosFinancierosCalculator aplica lógica de extensión por mes.
    Cuando mes > meses_contrato y poliza.aplica_extension=False → tasa = 0.
    Cuando aplica_extension=True → tasa sigue activa.
    Excel: Pólizas R172C7 = IF(F172=TRUE, duración_extension, meses_contrato).
    """

    def _make_calc(self, polizas, meses_contrato=12):
        from nexa_engine.modules.calculator_motor.formulas.costos_financieros import CostosFinancierosCalculator
        from unittest.mock import MagicMock
        panel = _panel_minimal(
            meses_contrato=meses_contrato,
            activa_financiacion=False,
            tasa_ica=0.0, tasa_gmf=0.0,
            tasa_comision_administracion=0.0,
        )
        param = MagicMock()
        param.get_factor_periodo.return_value = 0
        param.get_tasa_polizas_por_mes.return_value = 0.05  # dummy storage rate
        return CostosFinancierosCalculator(panel, param, polizas_usuario=polizas)

    def test_poliza_sin_extension_inactiva_despues_del_contrato(self):
        """aplica_extension=False → póliza inactiva cuando mes > meses_contrato."""
        poliza = PolizaContractual(
            nombre="Poliza A", activa=True,
            pct_poliza=0.01, pct_atribuible=1.0,
            aplica_extension=False,
        )
        calc = self._make_calc([poliza], meses_contrato=12)

        # Mes 12 (dentro del contrato) → poliza activa
        result_12 = calc.calcular(costo_operativo=1_000_000, mes=12)
        # Mes 13 (fuera del contrato) → poliza inactiva
        result_13 = calc.calcular(costo_operativo=1_000_000, mes=13)

        assert result_12.polizas > 0, "Póliza debe estar activa en mes 12"
        assert result_13.polizas == pytest.approx(0.0), "Póliza debe ser 0 en mes 13 (sin extensión)"

    def test_poliza_con_extension_activa_despues_del_contrato(self):
        """aplica_extension=True → póliza sigue activa cuando mes > meses_contrato."""
        poliza = PolizaContractual(
            nombre="Poliza B", activa=True,
            pct_poliza=0.01, pct_atribuible=1.0,
            aplica_extension=True,
        )
        calc = self._make_calc([poliza], meses_contrato=12)

        result_12 = calc.calcular(costo_operativo=1_000_000, mes=12)
        result_13 = calc.calcular(costo_operativo=1_000_000, mes=13)

        assert result_12.polizas > 0
        assert result_13.polizas > 0, "Póliza con extensión debe seguir activa en mes 13"

    def test_poliza_inactiva_siempre_cero(self):
        """activa=False → tasa siempre 0, independiente de extensión o mes."""
        poliza = PolizaContractual(
            nombre="Poliza C", activa=False,
            pct_poliza=0.01, pct_atribuible=1.0,
            aplica_extension=True,
        )
        calc = self._make_calc([poliza], meses_contrato=12)
        result = calc.calcular(costo_operativo=1_000_000, mes=5)
        assert result.polizas == pytest.approx(0.0)


# ─── FASE 3 — GAP-RULES-1: Tarifa hora en TarifaCanal ───────────────────────

class TestGapRules1TarifaHora:
    """
    Valida que VisionTarifasCalculator calcula tarifa_hora_loggeada y
    tarifa_hora_pagada usando las constantes operativas del YAML.
    Excel:
      R21C7 = IFERROR(IF(C10="FTE", G19/C13, G19/L26), 0)
      R23C7 = IFERROR(IF(C10="Tiempo", G19/L24, 0), 0)
      L24 = FTE × horas_semanales × semanas_al_mes
      L26 = FTE × horas_loggeadas_semanales × semanas_al_mes
    """

    def test_tarifa_hora_campos_en_tarifa_canal(self):
        """TarifaCanal expone tarifa_hora_loggeada y tarifa_hora_pagada."""
        import dataclasses
        from nexa_engine.modules.shared.models import TarifaCanal
        field_names = {f.name for f in dataclasses.fields(TarifaCanal)}
        assert "tarifa_hora_loggeada" in field_names
        assert "tarifa_hora_pagada" in field_names

    def test_tarifa_hora_calculada_en_vision_tarifas(self):
        """VisionTarifasCalculator popula tarifa_hora_loggeada con valor > 0."""
        from nexa_engine.modules.calculator_motor.formulas.tarifas.reglas import VisionTarifasCalculator
        from nexa_engine.modules.shared.models import ParametrosCadenaB, PerfilCadenaA
        from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules

        perfil = PerfilCadenaA(
            nombre="Agente Voz", modalidad="Inbound", canal="Voz",
            fte=10.0, salario_base=1_500_000, pct_fijo=1.0, modelo_cobro="Fijo FTE",
        )
        panel = _panel_minimal(margen=0.18, op_cont=0.025)
        params_b = ParametrosCadenaB()
        pyg_mes = _pyg_mes(payroll_a=700_000)

        calc = VisionTarifasCalculator([perfil], params_b, panel)
        r = calc.calcular([pyg_mes])

        assert len(r.canales) == 1
        canal = r.canales[0]

        rules = get_business_rules()
        fte = perfil.fte
        horas_pagadas_mes = fte * rules.horas_semanales * rules.semanas_al_mes
        expected_hora_pagada = canal.facturacion / horas_pagadas_mes

        assert canal.tarifa_hora_pagada == pytest.approx(expected_hora_pagada, rel=1e-6)
        assert canal.tarifa_hora_loggeada > 0
        assert canal.tarifa_hora_loggeada > canal.tarifa_hora_pagada  # loggeada < horas_pagadas → tarifa mayor
