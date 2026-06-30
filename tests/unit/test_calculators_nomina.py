"""
Unit tests for nexa_engine/calculators/nomina.py

Tests cover NominaCalculator.calcular_para_mes() and its private computation
methods via the public interface:
  - salario_fijo básico
  - capacitacion_inicial (amortized in contrato)
  - capacitacion_rotacion
  - examenes (tres componentes)
  - mes fuera de rango → ResultadoNomina zeros
  - factor_indexacion before/after mes_aplicacion_aumento
  - perfil sin examenes → 0
"""
from __future__ import annotations

import pytest

from nexa_engine.modules.calculator_motor.formulas.payroll import NominaCalculator
from nexa_engine.modules.shared.models import (
    ParametrosCalculo,
    ParametrosNomina,
    PerfilCadenaA,
    ResultadoNomina,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_parametros_nomina(**overrides) -> ParametrosNomina:
    defaults = dict(
        mes_inicio=1,
        mes_fin=24,
        pct_aumento_salarial=0.10,
        mes_aplicacion_aumento=13,
        tarifa_dia_cap=100_000,
        costo_examen_medico=80_000,
        costo_estudio_seg=50_000,
        meses_contrato=24,
        factor_indexacion_base=1.0,
    )
    defaults.update(overrides)
    return ParametrosNomina(**defaults)


def _make_parametros_calculo(**overrides) -> ParametrosCalculo:
    defaults = dict(
        pct_rotacion=0.03,
        pct_examen_anual=0.1,
        pct_cumplimiento_variable=0.8,
    )
    defaults.update(overrides)
    return ParametrosCalculo(**defaults)


def _make_perfil(**overrides) -> PerfilCadenaA:
    defaults = dict(
        nombre="Agente",
        modalidad="Presencial",
        canal="Telefono",
        fte=10.0,
        salario_base=2_000_000,
        salario_cargado=3_200_000,
        comision_pct=0.0,
        dias_cap_inicial=5,
        dias_cap_rotacion=5,
        incluye_examenes=True,
        incluye_seguridad=False,
        fte_examenes=11.0,
    )
    defaults.update(overrides)
    return PerfilCadenaA(**defaults)


def _make_calc(**nomina_overrides) -> NominaCalculator:
    return NominaCalculator(
        _make_parametros_nomina(**nomina_overrides),
        _make_parametros_calculo(),
    )


# ---------------------------------------------------------------------------
# Salario fijo básico
# ---------------------------------------------------------------------------

class TestSalarioFijo:
    def test_salario_fijo_basico_mes_1(self):
        """
        salario_fijo = salario_cargado × FTE × factor_indexacion − comisiones
        (mes=1, no comisiones, factor_indexacion=1.0)
        """
        nom = _make_parametros_nomina(factor_indexacion_base=1.0)
        cal = _make_parametros_calculo()
        calc = NominaCalculator(nom, cal)

        perfil = _make_perfil(
            salario_cargado=3_200_000,
            fte=10.0,
            comision_pct=0.0,
        )

        result = calc.calcular_para_mes([perfil], mes=1)

        # factor_indexacion = 1.0 × 1.0 (mes 1 < mes_aplicacion 13)
        # total_cargado = 3_200_000 × 10 × 1.0 = 32_000_000
        # comisiones = 0
        expected = 3_200_000 * 10.0 * 1.0
        assert result.salario_fijo == pytest.approx(expected)

    def test_salario_fijo_usa_salario_cargado_si_positivo(self):
        """When salario_cargado > 0, it takes priority over salario_base."""
        nom = _make_parametros_nomina()
        cal = _make_parametros_calculo()
        calc = NominaCalculator(nom, cal)

        perfil_cargado = _make_perfil(salario_base=2_000_000, salario_cargado=3_200_000, comision_pct=0.0, fte=1.0)
        perfil_base    = _make_perfil(salario_base=2_000_000, salario_cargado=0.0,       comision_pct=0.0, fte=1.0)

        res_cargado = calc.calcular_para_mes([perfil_cargado], mes=1)
        res_base    = calc.calcular_para_mes([perfil_base],    mes=1)

        assert res_cargado.salario_fijo == pytest.approx(3_200_000.0)
        assert res_base.salario_fijo    == pytest.approx(2_000_000.0)


# ---------------------------------------------------------------------------
# Capacitación inicial (amortizada en contrato)
# ---------------------------------------------------------------------------

class TestCapInicial:
    def test_cap_inicial_amortizada_en_contrato(self):
        """
        capacitacion_inicial = dias_cap_inicial × tarifa_dia_cap × FTE × factor / meses_contrato
        """
        nom = _make_parametros_nomina(
            tarifa_dia_cap=100_000,
            meses_contrato=24,
            factor_indexacion_base=1.0,
        )
        cal = _make_parametros_calculo()
        calc = NominaCalculator(nom, cal)

        perfil = _make_perfil(
            dias_cap_inicial=5,
            fte=10.0,
            incluye_examenes=False,
            salario_cargado=0.0,  # isolate capacitacion_inicial
            salario_base=0.0,
        )

        result = calc.calcular_para_mes([perfil], mes=1)

        # 5 × 100_000 × 10 × 1.0 / 24
        expected = 5 * 100_000 * 10.0 * 1.0 / 24
        assert result.capacitacion_inicial == pytest.approx(expected)

    def test_cap_inicial_es_igual_cada_mes(self):
        """Capacitacion inicial should be the same amount every month (amortized)."""
        nom = _make_parametros_nomina(factor_indexacion_base=1.0, pct_aumento_salarial=0.0)
        calc = NominaCalculator(nom, _make_parametros_calculo())

        perfil = _make_perfil(dias_cap_inicial=3, fte=5.0,
                              salario_cargado=0.0, salario_base=0.0,
                              incluye_examenes=False)

        res_1  = calc.calcular_para_mes([perfil], mes=1)
        res_12 = calc.calcular_para_mes([perfil], mes=12)
        assert res_1.capacitacion_inicial == pytest.approx(res_12.capacitacion_inicial)


# ---------------------------------------------------------------------------
# Capacitación por rotación
# ---------------------------------------------------------------------------

class TestCapRotacion:
    def test_cap_rotacion_formula(self):
        """
        capacitacion_rotacion = dias_cap_rotacion × tarifa × (FTE × pct_rotacion) × factor
        """
        nom = _make_parametros_nomina(
            tarifa_dia_cap=100_000,
            factor_indexacion_base=1.0,
        )
        cal = _make_parametros_calculo(pct_rotacion=0.03)
        calc = NominaCalculator(nom, cal)

        perfil = _make_perfil(
            dias_cap_rotacion=5,
            fte=10.0,
            salario_cargado=0.0,
            salario_base=0.0,
            incluye_examenes=False,
            dias_cap_inicial=0,
        )

        result = calc.calcular_para_mes([perfil], mes=1)

        # personas_nuevas_mes = 10 × 0.03 = 0.3
        # capacitacion_rotacion = 5 × 100_000 × 0.3 × 1.0 = 150_000
        expected = 5 * 100_000 * (10.0 * 0.03) * 1.0
        assert result.capacitacion_rotacion == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Exámenes médicos (tres componentes)
# ---------------------------------------------------------------------------

class TestExamenes:
    def test_examenes_tres_componentes(self):
        """
        fraccion_mensual = 1/meses_contrato + pct_rotacion + pct_examen_anual/12
        examenes = costo_examen × fte_examenes × fraccion_mensual × factor
        """
        nom = _make_parametros_nomina(
            costo_examen_medico=80_000,
            meses_contrato=24,
            factor_indexacion_base=1.0,
        )
        cal = _make_parametros_calculo(pct_rotacion=0.03, pct_examen_anual=0.1)
        calc = NominaCalculator(nom, cal)

        perfil = _make_perfil(
            fte=10.0,
            fte_examenes=11.0,
            incluye_examenes=True,
            salario_cargado=0.0,
            salario_base=0.0,
            dias_cap_inicial=0,
            dias_cap_rotacion=0,
        )

        result = calc.calcular_para_mes([perfil], mes=1)

        fraccion = 1.0 / 24 + 0.03 + 0.1 / 12
        expected = 80_000 * 11.0 * fraccion * 1.0
        assert result.examenes == pytest.approx(expected, rel=1e-6)

    def test_perfil_sin_examenes_retorna_cero(self):
        """incluye_examenes=False → examenes = 0."""
        nom = _make_parametros_nomina()
        calc = NominaCalculator(nom, _make_parametros_calculo())

        perfil = _make_perfil(incluye_examenes=False)
        result = calc.calcular_para_mes([perfil], mes=1)
        assert result.examenes == 0.0

    def test_examenes_usa_fte_examenes_cuando_positivo(self):
        """When fte_examenes > 0, it is used instead of fte."""
        nom = _make_parametros_nomina(costo_examen_medico=80_000, meses_contrato=24,
                                       factor_indexacion_base=1.0)
        cal = _make_parametros_calculo(pct_rotacion=0.0, pct_examen_anual=0.0)
        calc = NominaCalculator(nom, cal)

        perfil_con = _make_perfil(fte=10.0, fte_examenes=15.0, incluye_examenes=True,
                                   salario_cargado=0.0, salario_base=0.0,
                                   dias_cap_inicial=0, dias_cap_rotacion=0)
        perfil_sin = _make_perfil(fte=10.0, fte_examenes=0.0, incluye_examenes=True,
                                   salario_cargado=0.0, salario_base=0.0,
                                   dias_cap_inicial=0, dias_cap_rotacion=0)

        res_con = calc.calcular_para_mes([perfil_con], mes=1)
        res_sin = calc.calcular_para_mes([perfil_sin], mes=1)

        # fte_examenes=15 > fte=10 → more cost
        assert res_con.examenes > res_sin.examenes


# ---------------------------------------------------------------------------
# Mes fuera de rango
# ---------------------------------------------------------------------------

class TestMesFueraDeRango:
    def test_mes_antes_de_inicio_retorna_cero(self):
        """mes < mes_inicio → ResultadoNomina all zeros."""
        nom = _make_parametros_nomina(mes_inicio=3, mes_fin=24)
        calc = NominaCalculator(nom, _make_parametros_calculo())

        perfil = _make_perfil()
        result = calc.calcular_para_mes([perfil], mes=2)

        assert result.salario_fijo == 0.0
        assert result.capacitacion_inicial  == 0.0
        assert result.capacitacion_rotacion == 0.0
        assert result.examenes     == 0.0
        assert result.total        == 0.0

    def test_mes_cero_retorna_cero(self):
        """mes=0 → always before mes_inicio ≥ 1."""
        nom = _make_parametros_nomina(mes_inicio=1)
        calc = NominaCalculator(nom, _make_parametros_calculo())

        perfil = _make_perfil()
        result = calc.calcular_para_mes([perfil], mes=0)
        assert result.total == 0.0

    def test_mes_despues_de_fin_retorna_cero(self):
        """mes > mes_fin → ResultadoNomina all zeros."""
        nom = _make_parametros_nomina(mes_inicio=1, mes_fin=12)
        calc = NominaCalculator(nom, _make_parametros_calculo())

        perfil = _make_perfil()
        result = calc.calcular_para_mes([perfil], mes=13)
        assert result.total == 0.0


# ---------------------------------------------------------------------------
# Factor de indexación
# ---------------------------------------------------------------------------

class TestFactorIndexacion:
    def test_factor_indexacion_antes_aumento(self):
        """
        mes < mes_aplicacion → factor = factor_base × 1.0
        """
        nom = _make_parametros_nomina(
            factor_indexacion_base=1.18227,
            pct_aumento_salarial=0.10,
            mes_aplicacion_aumento=13,
        )
        cal = _make_parametros_calculo(pct_rotacion=0.0, pct_examen_anual=0.0)
        calc = NominaCalculator(nom, cal)

        perfil = _make_perfil(
            salario_cargado=1_000_000,
            fte=1.0,
            comision_pct=0.0,
            incluye_examenes=False,
            dias_cap_inicial=0,
            dias_cap_rotacion=0,
        )

        result = calc.calcular_para_mes([perfil], mes=1)
        expected = 1_000_000 * 1.0 * 1.18227
        assert result.salario_fijo == pytest.approx(expected, rel=1e-5)

    def test_factor_indexacion_primer_aumento(self):
        """
        mes >= mes_aplicacion_aumento → factor = factor_base × (1+pct)^1
        """
        nom = _make_parametros_nomina(
            factor_indexacion_base=1.18227,
            pct_aumento_salarial=0.10,
            mes_aplicacion_aumento=13,
        )
        cal = _make_parametros_calculo(pct_rotacion=0.0, pct_examen_anual=0.0)
        calc = NominaCalculator(nom, cal)

        perfil = _make_perfil(
            salario_cargado=1_000_000,
            fte=1.0,
            comision_pct=0.0,
            incluye_examenes=False,
            dias_cap_inicial=0,
            dias_cap_rotacion=0,
        )

        result = calc.calcular_para_mes([perfil], mes=13)
        expected = 1_000_000 * 1.0 * 1.18227 * 1.10
        assert result.salario_fijo == pytest.approx(expected, rel=1e-5)

    def test_factor_indexacion_segundo_aumento(self):
        """mes=25 → factor = factor_base × (1+pct)^2"""
        nom = _make_parametros_nomina(
            factor_indexacion_base=1.0,
            pct_aumento_salarial=0.10,
            mes_aplicacion_aumento=13,
            mes_inicio=1,
            mes_fin=36,
            meses_contrato=36,
        )
        cal = _make_parametros_calculo(pct_rotacion=0.0, pct_examen_anual=0.0)
        calc = NominaCalculator(nom, cal)

        perfil = _make_perfil(
            salario_cargado=1_000_000,
            fte=1.0,
            comision_pct=0.0,
            incluye_examenes=False,
            dias_cap_inicial=0,
            dias_cap_rotacion=0,
        )

        result = calc.calcular_para_mes([perfil], mes=25)
        expected = 1_000_000 * 1.0 * 1.21
        assert result.salario_fijo == pytest.approx(expected, rel=1e-5)


# ---------------------------------------------------------------------------
# Multiple profiles accumulate
# ---------------------------------------------------------------------------

class TestAcumulacionPerfiles:
    def test_dos_perfiles_suman(self):
        """calcular_para_mes with two profiles accumulates correctly."""
        nom = _make_parametros_nomina(factor_indexacion_base=1.0, pct_aumento_salarial=0.0)
        cal = _make_parametros_calculo(pct_rotacion=0.0, pct_examen_anual=0.0)
        calc = NominaCalculator(nom, cal)

        p1 = _make_perfil(salario_cargado=1_000_000, fte=5.0, comision_pct=0.0,
                           incluye_examenes=False, dias_cap_inicial=0, dias_cap_rotacion=0)
        p2 = _make_perfil(salario_cargado=2_000_000, fte=3.0, comision_pct=0.0,
                           incluye_examenes=False, dias_cap_inicial=0, dias_cap_rotacion=0)

        result = calc.calcular_para_mes([p1, p2], mes=1)

        expected = 1_000_000 * 5.0 + 2_000_000 * 3.0
        assert result.salario_fijo == pytest.approx(expected)

    def test_lista_vacia_retorna_ceros(self):
        """Empty profile list → all zeros."""
        calc = _make_calc()
        result = calc.calcular_para_mes([], mes=1)
        assert result.total == 0.0
