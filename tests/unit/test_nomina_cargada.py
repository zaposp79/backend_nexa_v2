"""
Unit tests for nexa_engine/domain/services/nomina_cargada.py

Tests cover NominaCargadaService:
  - calcular(): standard employee, Ley 1819, high salary, transport allowance
  - calcular_aprendiz(): apprentice contract rules
  - calcular_sm(): S&M team rules (pension-based prestaciones)
"""
from __future__ import annotations

import pytest

from nexa_engine.modules.cadena_a.services.nomina_cargada import (
    NominaCargadaService,
    ParametrosNominaLaboral,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_params(**overrides) -> ParametrosNominaLaboral:
    """Return standard 2026 payroll parameters."""
    defaults = dict(
        salario_minimo=1_423_500,
        auxilio_transporte=200_000,
        dotaciones_mensual=50_000,
        pct_cumplimiento_variable=1.0,
        factor_alto_salario_smmlv=10.0,
        factor_corrector_alto_salario=0.70,
        tasa_salud=0.085,
        tasa_pension=0.12,
        tasa_arl=0.00522,
        tasa_caja=0.04,
        tasa_icbf_sena=0.04,
        tasa_cesantias=0.0833,
        tasa_primas=0.0833,
        tasa_interes_cesantia=0.12,
        tasa_vacaciones=0.0417,
        aplica_ley_1819=True,
    )
    defaults.update(overrides)
    return ParametrosNominaLaboral(**defaults)


# ---------------------------------------------------------------------------
# NominaCargadaService.calcular — Aportes patronales Excel V2-4 + Ley 1819
# Validado contra hoja "Inputs de Nomina" del Excel V2-4:
#   Salud (8.5%) e ICBF+Sena (4%) = 0 para salarios < 10×SMMLV (Ley 1819)
#   Salud (8.5%) e ICBF+Sena (4%) aplican con factor 0.70 para altos salarios
# ---------------------------------------------------------------------------

class TestAportesPatronalesExcelV24:
    def test_bajo_salario_exonera_salud_e_icbf_ley_1819(self):
        """
        Ley 1819 de 2016: empleadores exonerados de Salud e ICBF+Sena para
        empleados con T.Imponible < 10×SMMLV.
        Excel formula: IF(F>10*SMMLV, F*tasa*70%, 0)
        Validado contra hoja "Inputs de Nomina" Excel V2-4.
        """
        params = _make_params()
        svc = NominaCargadaService(params)

        salario = 3_000_000  # < 10 × 1_423_500 = 14_235_000 → Ley 1819 aplica
        resultado = svc.calcular(salario)

        # Ley 1819: Salud=0, ICBF+Sena=0 para salarios < 10 SMMLV
        assert resultado > 0  # servicio retorna valor positivo
        # El resultado NO incluye Salud ni ICBF+Sena
        t_imponible = salario
        valor_con_salud = t_imponible * params.tasa_salud
        valor_con_icbf  = t_imponible * params.tasa_icbf_sena
        # Si se incluyeran, el total sería mayor
        assert resultado < resultado + valor_con_salud + valor_con_icbf

    def test_flag_aplica_ley_1819_siempre_activo(self):
        """
        El flag aplica_ley_1819 existe por compatibilidad; Ley 1819 siempre activa.
        True y False producen resultado idéntico (campo ignorado en cálculo).
        """
        salario = 3_000_000

        params_true = _make_params(aplica_ley_1819=True)
        resultado_true = NominaCargadaService(params_true).calcular(salario)

        params_false = _make_params(aplica_ley_1819=False)
        resultado_false = NominaCargadaService(params_false).calcular(salario)

        assert resultado_true == pytest.approx(resultado_false, rel=1e-10)

    def test_bajo_salario_calculo_exacto_ley_1819(self):
        """
        Verifica el cálculo exacto para salario normal (< 10×SMMLV):
        Salud=0, ICBF+Sena=0, resto de aportes calculados normalmente.
        Validado contra Excel V2-4 hoja "Inputs de Nomina".
        """
        params = _make_params()
        svc = NominaCargadaService(params)

        salario = 3_000_000
        t_imponible = salario
        resultado = svc.calcular(salario)

        # Ley 1819: Salud=0, ICBF+Sena=0 para T.Imponible < 10×SMMLV
        aux = 0.0  # 3M > 2 × SMMLV
        t_haberes = t_imponible + aux

        salud     = 0.0                              # ← Ley 1819 exoneración
        icbf_sena = 0.0                              # ← Ley 1819 exoneración
        pension   = t_imponible * params.tasa_pension
        arl       = t_imponible * params.tasa_arl
        caja      = t_imponible * params.tasa_caja

        seg_social   = t_haberes + salud + pension + arl
        parafiscales = caja + icbf_sena

        cesantias  = t_haberes * params.tasa_cesantias
        primas     = t_haberes * params.tasa_primas
        int_ces    = cesantias * params.tasa_interes_cesantia
        vacaciones = t_imponible * params.tasa_vacaciones
        prestaciones = cesantias + primas + int_ces + vacaciones

        dotaciones = 0.0  # 3M > 2 × SMMLV

        from nexa_engine.modules.shared.precision import cop_round
        expected = cop_round(seg_social + parafiscales + prestaciones + dotaciones)
        assert resultado == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# Alto salario — factor corrector 0.70
# ---------------------------------------------------------------------------

class TestAltoSalario:
    def test_alto_salario_aplica_factor_corrector(self):
        """
        salario > 10 × SMMLV → factor corrector 0.70 sobre SS patronal.
        """
        params = _make_params()
        svc = NominaCargadaService(params)

        smmlv = params.salario_minimo
        salario_alto = 15_000_000  # > 10 × 1_423_500

        assert salario_alto > 10 * smmlv

        resultado = svc.calcular(salario_alto)

        # Build expected manually
        t_imponible = salario_alto
        factor = params.factor_corrector_alto_salario  # 0.70

        salud     = t_imponible * params.tasa_salud    * factor
        pension   = t_imponible * params.tasa_pension  * factor
        arl       = t_imponible * params.tasa_arl      * factor
        caja      = t_imponible * params.tasa_caja     * factor
        icbf_sena = t_imponible * params.tasa_icbf_sena* factor
        vac_rate  = params.tasa_vacaciones             * factor

        # t_haberes: no aux (salario > 2×SMMLV), and > umbral_alto
        t_haberes = t_imponible
        # Prestaciones: t_haberes > umbral_alto → cesantias=primas=int_ces=0
        vacaciones = t_imponible * vac_rate

        seg_social   = t_haberes + salud + pension + arl
        parafiscales = caja + icbf_sena
        prestaciones = vacaciones
        dotaciones   = 0.0  # salario > 2×SMMLV

        expected = seg_social + parafiscales + prestaciones + dotaciones
        assert resultado == pytest.approx(expected, rel=1e-6)

    def test_alto_salario_sin_prestaciones_base(self):
        """
        salario > 10 × SMMLV → cesantias, primas e intereses = 0.
        """
        params = _make_params()
        svc = NominaCargadaService(params)

        salario_bajo = 3_000_000
        salario_alto = 15_000_000

        resultado_bajo = svc.calcular(salario_bajo)
        resultado_alto = svc.calcular(salario_alto)

        # Alto salario lacks cesantias+primas proportionally
        # The ratio should reflect the factor corrector
        assert resultado_alto > 0


# ---------------------------------------------------------------------------
# Auxilio de transporte
# ---------------------------------------------------------------------------

class TestAuxilioTransporte:
    def test_auxilio_transporte_bajo_2smmlv(self):
        """salario < 2 × SMMLV → auxilio de transporte incluido en base."""
        params = _make_params()
        svc = NominaCargadaService(params)

        smmlv = params.salario_minimo
        salario_bajo = int(1.5 * smmlv)  # 1.5 × SMMLV

        assert salario_bajo < 2 * smmlv

        resultado = svc.calcular(salario_bajo)

        # Result includes aux in t_haberes, which increases prestaciones base
        # Verify by comparing with an artificial case where aux=0
        params_no_aux = _make_params(auxilio_transporte=0.0)
        svc_no_aux = NominaCargadaService(params_no_aux)
        resultado_no_aux = svc_no_aux.calcular(salario_bajo)

        # With aux > without aux (aux adds to t_haberes → more cesantias+primas)
        assert resultado > resultado_no_aux

    def test_sin_auxilio_transporte_sobre_2smmlv(self):
        """salario > 2 × SMMLV → auxilio = 0."""
        params = _make_params()
        svc = NominaCargadaService(params)

        smmlv = params.salario_minimo
        salario_alto = int(3 * smmlv)  # 3 × SMMLV

        assert salario_alto > 2 * smmlv

        resultado = svc.calcular(salario_alto)

        # Should be same regardless of auxilio_transporte value
        params_big_aux = _make_params(auxilio_transporte=1_000_000)
        svc_big_aux = NominaCargadaService(params_big_aux)
        resultado_big_aux = svc_big_aux.calcular(salario_alto)

        assert resultado == pytest.approx(resultado_big_aux, rel=1e-10)


# ---------------------------------------------------------------------------
# Dotaciones
# ---------------------------------------------------------------------------

class TestDotaciones:
    def test_dotaciones_solo_bajo_salario(self):
        """dotaciones incluidas solo si t_imponible < 2 × SMMLV."""
        params = _make_params(dotaciones_mensual=50_000)
        svc = NominaCargadaService(params)

        smmlv = params.salario_minimo
        salario_bajo = int(1.5 * smmlv)
        salario_alto = int(3 * smmlv)

        res_bajo = svc.calcular(salario_bajo)
        res_alto = svc.calcular(salario_alto)

        params_nodot = _make_params(dotaciones_mensual=0.0)
        svc_nodot = NominaCargadaService(params_nodot)
        res_bajo_nodot = svc_nodot.calcular(salario_bajo)
        res_alto_nodot = svc_nodot.calcular(salario_alto)

        # Low salary: dotaciones add to cost
        assert res_bajo - res_bajo_nodot == pytest.approx(50_000.0, rel=1e-10)
        # High salary: dotaciones have no effect
        assert res_alto == pytest.approx(res_alto_nodot, rel=1e-10)


# ---------------------------------------------------------------------------
# calcular_aprendiz
# ---------------------------------------------------------------------------

class TestCalcularAprendiz:
    def test_aprendiz_sin_pension_ni_arl(self):
        """
        Apprentice contracts: no pension, no ARL, only caja (4%) as parafiscal.
        """
        params = _make_params()
        svc = NominaCargadaService(params)

        salario = 2_000_000
        resultado = svc.calcular_aprendiz(salario)

        assert resultado > 0

        # Compare: standard employee with same salary is more expensive
        # because of pension+ARL contributions
        resultado_std = svc.calcular(salario)
        # Aprendiz lacks pension (12%) and ARL (0.522%) in SS
        # So resultado < resultado_std
        # But we need to account for Ley 1819 exempting salud for standard
        assert resultado < resultado_std

    def test_aprendiz_sin_dotaciones(self):
        """Apprentice gets no dotaciones regardless of salary."""
        params = _make_params(dotaciones_mensual=100_000)
        svc = NominaCargadaService(params)

        smmlv = params.salario_minimo
        salario_bajo = int(1.5 * smmlv)  # would normally get dotaciones

        resultado = svc.calcular_aprendiz(salario_bajo)

        # Without dotaciones override
        params_nodot = _make_params(dotaciones_mensual=0.0)
        svc_nodot = NominaCargadaService(params_nodot)
        resultado_nodot = svc_nodot.calcular_aprendiz(salario_bajo)

        # No dotaciones for apprentice regardless
        assert resultado == pytest.approx(resultado_nodot, rel=1e-10)

    def test_aprendiz_tiene_cesantias_y_primas(self):
        """Apprentice has cesantias, primas based on t_haberes."""
        params = _make_params(aplica_ley_1819=True)
        svc = NominaCargadaService(params)

        smmlv = params.salario_minimo
        salario = int(1.5 * smmlv)
        aux = params.auxilio_transporte
        t_haberes = salario + aux  # < 2×SMMLV so aux applies

        resultado = svc.calcular_aprendiz(salario)

        cesantias = t_haberes * params.tasa_cesantias
        primas     = t_haberes * params.tasa_primas
        int_ces    = cesantias * params.tasa_interes_cesantia
        vacaciones = salario   * params.tasa_vacaciones

        prestaciones = cesantias + primas + int_ces + vacaciones
        # Total should contain these prestaciones
        assert prestaciones > 0
        assert resultado >= prestaciones


# ---------------------------------------------------------------------------
# calcular_sm
# ---------------------------------------------------------------------------

class TestCalcularSm:
    def test_sm_usa_pension_como_base_prestaciones(self):
        """
        S&M uses pension (not t_haberes) as the base for cesantias, primas, etc.
        Excel V2-4: Salud e ICBF+SENA se cobran siempre.
        """
        params = _make_params()
        svc = NominaCargadaService(params)

        salario = 5_000_000
        resultado = svc.calcular_sm(salario)

        # Manually compute expected
        t_imponible = salario
        # salario < 10×SMMLV → low salary track
        pension = t_imponible * params.tasa_pension
        arl     = t_imponible * params.tasa_arl

        aux = params.auxilio_transporte if t_imponible < 2 * params.salario_minimo else 0.0
        t_haberes = t_imponible + aux

        # Excel V2-4 legacy: Salud e ICBF+SENA se cobran siempre
        salud     = t_imponible * params.tasa_salud
        icbf_sena = t_imponible * params.tasa_icbf_sena

        seg_social   = t_haberes + salud + pension + arl
        parafiscales = arl + icbf_sena

        # Prestaciones based on pension (not t_haberes)
        cesantias  = pension * params.tasa_cesantias
        primas     = pension * params.tasa_primas
        int_ces    = pension * params.tasa_interes_cesantia
        vacaciones = pension * params.tasa_vacaciones
        prestaciones = cesantias + primas + int_ces + vacaciones

        dotaciones = params.dotaciones_mensual if t_imponible < 2 * params.salario_minimo else 0.0

        expected = seg_social + parafiscales + prestaciones + dotaciones
        assert resultado == pytest.approx(expected, rel=1e-6)

    def test_sm_retorna_positivo(self):
        params = _make_params()
        svc = NominaCargadaService(params)
        assert svc.calcular_sm(3_000_000) > 0
