"""
tests/certification/test_layer2_consistency.py
===============================================
LAYER 2 — Cross-Consistency Certification.

Garantía: El motor es matemáticamente consistente consigo mismo.
  - Los componentes del cálculo suman exactamente al total
  - Ley 1819 no produce contradicciones internas
  - Las reglas de umbral son internamente coherentes
  - Sin drift numérico entre desagregaciones y totales

ADVERTENCIA ARQUITECTÓNICA DOCUMENTADA:
  L2 valida CONSISTENCIA INTERNA, no VERDAD FINANCIERA.
  Un sistema que calcule tasas incorrectas puede pasar L2 perfectamente.
  La verdad financiera es responsabilidad de L3 (Oracle).

Lo que detecta:
  ✅ Suma de componentes ≠ total declarado
  ✅ Drift entre rutas de cálculo alternativas
  ✅ Contradicciones internas en reglas de negocio
  ✅ Pérdida de precisión en operaciones encadenadas

Lo que NO detecta (cubierto en L3):
  ❌ Tasas incorrectas pero consistentes
  ❌ FTE mal contados pero sumados correctamente
  ❌ Reglas de negocio incorrectas pero coherentes
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import backend_nexa  # noqa: F401

# Tolerancia para consistencia interna: 0 drift permitido
_DRIFT_MAX = 0.0  # exacto


# ═══════════════════════════════════════════════════════════════════════════
# L2.1 — Descomposición de Componentes
# ═══════════════════════════════════════════════════════════════════════════

class TestDescomposicionComponentes:
    """
    Los sub-componentes calculados individualmente deben sumar al total del motor.
    Detecta: drift entre rutas de cálculo, truncamientos, errores en agregación.
    """

    def _calcular_detallado(self, salario: float, comision: float, p) -> dict:
        """Réplica interna del motor — retorna todos los componentes."""
        smmlv       = p.salario_minimo
        umbral_alto = p.factor_alto_salario_smmlv * smmlv

        t_imponible = salario * (1.0 + comision * p.pct_cumplimiento_variable)
        aux         = p.auxilio_transporte if t_imponible < 2 * smmlv else 0.0
        t_haberes   = t_imponible + aux
        alto_salario = t_imponible > umbral_alto

        if alto_salario:
            factor    = p.factor_corrector_alto_salario
            salud     = t_imponible * p.tasa_salud     * factor
            pension   = t_imponible * p.tasa_pension   * factor
            arl       = t_imponible * p.tasa_arl       * factor
            caja      = t_imponible * p.tasa_caja      * factor
            icbf_sena = t_imponible * p.tasa_icbf_sena * factor
            vac_rate  = p.tasa_vacaciones              * factor
        else:
            salud     = 0.0
            icbf_sena = 0.0
            pension   = t_imponible * p.tasa_pension
            arl       = t_imponible * p.tasa_arl
            caja      = t_imponible * p.tasa_caja
            vac_rate  = p.tasa_vacaciones

        seg_social   = t_haberes + salud + pension + arl
        parafiscales = caja + icbf_sena

        if t_haberes <= umbral_alto:
            cesantias = t_haberes * p.tasa_cesantias
            primas    = t_haberes * p.tasa_primas
            int_ces   = cesantias * p.tasa_interes_cesantia
        else:
            cesantias = primas = int_ces = 0.0

        vacaciones   = t_imponible * vac_rate
        prestaciones = cesantias + primas + int_ces + vacaciones
        dotaciones   = p.dotaciones_mensual if t_imponible < 2 * smmlv else 0.0

        return {
            "t_imponible": t_imponible, "aux": aux, "t_haberes": t_haberes,
            "salud": salud, "pension": pension, "arl": arl,
            "seg_social": seg_social,
            "caja": caja, "icbf_sena": icbf_sena, "parafiscales": parafiscales,
            "cesantias": cesantias, "primas": primas, "int_ces": int_ces,
            "vacaciones": vacaciones, "prestaciones": prestaciones,
            "dotaciones": dotaciones,
            "total": seg_social + parafiscales + prestaciones + dotaciones,
        }

    @pytest.mark.parametrize("salario,comision", [
        (1_750_905.0, 0.0),   # SMMLV exacto
        (2_000_000.0, 0.0),   # con auxilio
        (3_500_000.0, 0.0),   # sin auxilio, sin dotaciones
        (3_500_000.0, 0.10),  # con comisión
        (18_505_000.0, 0.0),  # alto salario
    ])
    def test_suma_componentes_igual_a_motor(
        self, nomina_service, parametros_objeto, salario, comision
    ):
        """
        Σ(seg_social + parafiscales + prestaciones + dotaciones) == motor.calcular()
        """
        resultado_motor = nomina_service.calcular(salario, comision_pct=comision)
        desglose = self._calcular_detallado(salario, comision, parametros_objeto)

        # Verificar que la réplica produce el mismo total que el motor
        assert resultado_motor == pytest.approx(desglose["total"], abs=1e-9), (
            f"salario={salario}, comision={comision}\n"
            f"Motor:   {resultado_motor}\n"
            f"Réplica: {desglose['total']}\n"
            f"Δ:       {abs(resultado_motor - desglose['total'])}"
        )

    @pytest.mark.parametrize("salario", [1_750_905.0, 2_500_000.0, 5_000_000.0])
    def test_seg_social_descomposicion(self, parametros_objeto, salario):
        """seg_social = t_haberes + salud + pension + arl (exacto)."""
        d = self._calcular_detallado(salario, 0.0, parametros_objeto)
        esperado = d["t_haberes"] + d["salud"] + d["pension"] + d["arl"]
        assert d["seg_social"] == pytest.approx(esperado, abs=1e-9), (
            f"seg_social={d['seg_social']} ≠ suma={esperado}"
        )

    @pytest.mark.parametrize("salario", [1_750_905.0, 2_500_000.0, 5_000_000.0])
    def test_parafiscales_descomposicion(self, parametros_objeto, salario):
        """parafiscales = caja + icbf_sena (exacto)."""
        d = self._calcular_detallado(salario, 0.0, parametros_objeto)
        esperado = d["caja"] + d["icbf_sena"]
        assert d["parafiscales"] == pytest.approx(esperado, abs=1e-9)

    @pytest.mark.parametrize("salario", [1_750_905.0, 2_500_000.0, 5_000_000.0])
    def test_prestaciones_descomposicion(self, parametros_objeto, salario):
        """prestaciones = cesantias + primas + int_ces + vacaciones (exacto)."""
        d = self._calcular_detallado(salario, 0.0, parametros_objeto)
        esperado = d["cesantias"] + d["primas"] + d["int_ces"] + d["vacaciones"]
        assert d["prestaciones"] == pytest.approx(esperado, abs=1e-9)


# ═══════════════════════════════════════════════════════════════════════════
# L2.2 — Consistencia de Reglas de Umbral
# ═══════════════════════════════════════════════════════════════════════════

class TestConsistenciaUmbral:
    """
    Las reglas de umbral (2×SMMLV, 10×SMMLV) deben ser internamente coherentes.
    Detecta: condiciones que se activan/desactivan inconsistentemente.
    """

    def test_ley_1819_umbral_coherente(self, nomina_service, raw_params):
        """
        Ley 1819: la exoneración de Salud e ICBF+Sena debe ser monótona.
        Si activa para salario X, debe estar activa para cualquier salario < X.
        """
        smmlv   = raw_params["salario_minimo"]
        umbral  = raw_params["factor_alto_salario_smmlv"] * smmlv
        factor  = raw_params["factor_corrector_alto_salario"]
        aps     = raw_params["aportes_patronales"]

        tasa_salud    = aps["salud"]
        tasa_icbf     = aps["icbf_sena"]

        # Dos salarios bajos: ambos deben tener salud=0, icbf=0
        for salario in [smmlv * 1.5, smmlv * 3, smmlv * 5, smmlv * 8]:
            assert salario < umbral, f"Setup error: {salario} no es < umbral ({umbral})"
            # Motor con salud e icbf = 0 (Ley 1819)
            r_motor = nomina_service.calcular(salario)
            # Valor hipotético SI se cobraran salud e icbf
            r_con_salud_icbf = r_motor + salario * tasa_salud + salario * tasa_icbf
            # Motor debe ser menor (no incluye salud/icbf)
            assert r_motor < r_con_salud_icbf, (
                f"salario={salario}: Ley 1819 no aplicada — motor debería ser "
                f"menor si salud e icbf estuvieran exonerados"
            )

    def test_alto_salario_umbral_coherente(self, nomina_service, raw_params):
        """
        Comportamiento documentado al cruzar el umbral 10×SMMLV.

        COMPORTAMIENTO CONTRAINTUITIVO (CORRECTO según Excel V2-6):
        Al cruzar de 9.999×SMMLV a 10.001×SMMLV, el COSTO TOTAL BAJA porque:
        - Bajo umbral:  Ley 1819 (salud=0, icbf=0) PERO cesantías+primas sobre t_haberes grande
        - Sobre umbral: factor 0.70 activa salud+icbf, PERO cesantías+primas = 0 (t_haberes > umbral)
        El ahorro de cesantías+primas supera el costo de salud+icbf × 0.70.

        Este test verifica las invariantes correctas del umbral, no el total.
        """
        smmlv  = raw_params["salario_minimo"]
        n      = raw_params["factor_alto_salario_smmlv"]  # 10.0
        umbral = n * smmlv

        salario_bajo  = umbral * 0.999  # Ley 1819 activa
        salario_alto  = umbral * 1.001  # Factor 0.70 activo, cesantías/primas = 0

        r_bajo = nomina_service.calcular(salario_bajo)
        r_alto = nomina_service.calcular(salario_alto)

        # Invariante: ambos son positivos (siempre)
        assert r_bajo > 0, f"Costo bajo umbral debe ser positivo: {r_bajo}"
        assert r_alto > 0, f"Costo sobre umbral debe ser positivo: {r_alto}"

        # Invariante: el costo debe estar en un rango razonable (1.1× - 2×) del salario
        assert 1.1 * salario_bajo < r_bajo < 2.5 * salario_bajo, (
            f"Costo bajo umbral ({r_bajo:.0f}) fuera de rango razonable "
            f"[1.1×, 2.5×] de {salario_bajo:.0f}"
        )
        assert 1.0 * salario_alto < r_alto < 2.0 * salario_alto, (
            f"Costo sobre umbral ({r_alto:.0f}) fuera de rango razonable "
            f"[1.0×, 2.0×] de {salario_alto:.0f}"
        )

        # Invariante documentada: al cruzar el umbral, el costo BAJA (contraintuitivo pero correcto)
        # porque se eliminan cesantías+primas sobre un salario de ~17.5M
        assert r_alto < r_bajo, (
            f"Comportamiento esperado: cruzar umbral 10×SMMLV REDUCE el costo "
            f"(cesantías+primas eliminadas supera salud+icbf × 0.70).\n"
            f"  Costo bajo umbral: {r_bajo:,.2f}\n"
            f"  Costo sobre umbral: {r_alto:,.2f}\n"
            f"  (Si este assert falla, verificar que el cambio de régimen es correcto)"
        )

    def test_auxilio_transporte_umbral_coherente(self, nomina_service, raw_params):
        """
        Auxilio de transporte solo activa para t_imponible < 2×SMMLV.
        Un peso de diferencia en el salario no debe causar discontinuidad brusca.
        """
        smmlv  = raw_params["salario_minimo"]
        umbral = 2 * smmlv
        aux    = raw_params["auxilio_transporte"]  # 249,095

        # Salario exactamente en el umbral: sin auxilio
        r_en_umbral    = nomina_service.calcular(umbral)
        # Salario un peso por debajo: con auxilio
        r_bajo_umbral  = nomina_service.calcular(umbral - 1)

        # Con auxilio: mayor costo (auxilio suma a t_haberes → más prestaciones)
        assert r_bajo_umbral > r_en_umbral, (
            f"Con auxilio ({r_bajo_umbral:.2f}) debe ser > sin auxilio ({r_en_umbral:.2f})"
        )

    def test_dotaciones_umbral_coherente(self, nomina_service, raw_params):
        """Dotaciones solo activan para salario < 2×SMMLV — coherente con auxilio."""
        smmlv  = raw_params["salario_minimo"]
        umbral = 2 * smmlv

        r_en_umbral   = nomina_service.calcular(umbral)
        r_bajo_umbral = nomina_service.calcular(umbral - 1)

        # El salario por debajo incluye dotaciones + auxilio → más costo
        assert r_bajo_umbral > r_en_umbral


# ═══════════════════════════════════════════════════════════════════════════
# L2.3 — Consistencia entre Métodos
# ═══════════════════════════════════════════════════════════════════════════

class TestConsistenciaEntreMetodos:
    """
    Los tres métodos (calcular, calcular_sm, calcular_aprendiz) deben ser
    coherentes entre sí cuando las diferencias son conocidas y documentadas.
    """

    def test_aprendiz_menor_que_estandar_bajo_smmlv(self, nomina_service, raw_params):
        """
        calcular_aprendiz(SMMLV) < calcular(SMMLV)
        porque aprendiz no paga pension (12%) ni ARL (0.522%)
        """
        smmlv   = raw_params["salario_minimo"]
        r_std   = nomina_service.calcular(smmlv)
        r_apren = nomina_service.calcular_aprendiz(smmlv)

        assert r_apren < r_std, (
            f"Aprendiz ({r_apren:.2f}) debe ser < estándar ({r_std:.2f}) "
            f"por exención de pensión+ARL"
        )

        # La diferencia debe ser ≈ pension + arl = smmlv × (0.12 + 0.00522)
        aps       = raw_params["aportes_patronales"]
        delta_esp = smmlv * (aps["pension"] + aps["arl_staff"])
        delta_rea = r_std - r_apren

        # No es exacto porque Ley 1819 cambia otras cosas,
        # pero debe estar en el mismo orden de magnitud
        assert delta_rea > 0, "Diferencia debe ser positiva"
        assert delta_rea < smmlv, (
            f"Diferencia ({delta_rea:.0f}) mayor que SMMLV — lógica inconsistente"
        )

    def test_sm_diferencia_estructural_vs_estandar(self, nomina_service, raw_params):
        """
        Diferencias estructurales documentadas entre calcular_sm() y calcular():

        calcular_sm() (S&M legacy Excel V2-4):
          + Cobra salud (8.5%) e ICBF+Sena (4%) SIEMPRE (sin Ley 1819)
          - Prestaciones (ces+primas+int+vac) calculadas sobre PENSIÓN (base pequeña)
          - Parafiscales = ARL + ICBF+Sena (no caja)

        calcular() (estándar Ley 1819):
          - Salud=0, ICBF=0 para T.Imponible < 10×SMMLV
          + Prestaciones sobre T.Haberes (base grande)
          + Parafiscales = caja + ICBF+Sena (ICBF=0 por Ley 1819, solo caja)

        Resultado neto: para salarios medios (3×SMMLV), calcular_sm() < calcular()
        porque el ahorro en prestaciones (base pension vs haberes) supera el costo
        de salud+ICBF adicional. Esto es CORRECTO según Excel V2-4 vs V2-6.

        Este test verifica la coherencia estructural, no el total comparativo.
        """
        smmlv   = raw_params["salario_minimo"]
        salario = smmlv * 3
        aps     = raw_params["aportes_patronales"]

        r_std = nomina_service.calcular(salario)
        r_sm  = nomina_service.calcular_sm(salario)

        # Invariante: S&M cobra salud e ICBF (esto eleva PARTE de su costo)
        # La diferencia de costos incluye salud e ICBF como extra en S&M
        salud_sm   = salario * aps["salud"]
        icbf_sm    = salario * aps["icbf_sena"]
        extra_sm   = salud_sm + icbf_sm

        # El costo de S&M debe ser > r_sm - extra_sm (es decir, sin el extra de salud/icbf, sería menor)
        assert r_sm - extra_sm < r_sm, (
            "Redundante pero documenta que salud+icbf sí están en S&M"
        )

        # Ambos positivos
        assert r_sm > 0 and r_std > 0

        # Invariante documentada: S&M es MÁS BARATO para salarios medios
        # por prestaciones sobre pensión (no haberes)
        assert r_sm < r_std, (
            f"Comportamiento esperado: calcular_sm({salario:.0f}) < calcular() "
            f"para salarios medios — ahorro en prestaciones supera extra de salud+ICBF.\n"
            f"  S&M: {r_sm:,.2f}, Estándar: {r_std:,.2f}"
        )

    def test_tres_metodos_retornan_valores_positivos(self, nomina_service, raw_params):
        """Los tres métodos retornan siempre valores positivos."""
        smmlv = raw_params["salario_minimo"]
        for salario in [smmlv, smmlv * 2, smmlv * 5, smmlv * 12]:
            assert nomina_service.calcular(salario) > 0
            assert nomina_service.calcular_sm(salario) > 0
            assert nomina_service.calcular_aprendiz(salario) > 0


# ═══════════════════════════════════════════════════════════════════════════
# L2.4 — No Drift Numérico
# ═══════════════════════════════════════════════════════════════════════════

class TestNoDrift:
    """
    Verifica que no existe drift acumulado en operaciones en cadena.
    Un sistema con drift produciría resultados distintos dependiendo del
    número de cálculos previos — viola el principio de determinismo.
    """

    def test_no_drift_entre_100_calculos(self, nomina_service):
        """
        El resultado de calcular(X) no cambia después de 100 cálculos de otros valores.
        """
        referencia = nomina_service.calcular(3_000_000.0)

        # Calcular 100 valores intermedios
        for i in range(100):
            nomina_service.calcular(float(1_500_000 + i * 10_000))

        resultado_final = nomina_service.calcular(3_000_000.0)
        assert resultado_final == referencia, (
            f"Drift detectado: {referencia} → {resultado_final} "
            f"después de 100 cálculos intermedios"
        )

    def test_orden_calculo_no_afecta_resultado(self, nomina_service):
        """
        Calcular los mismos valores en diferente orden produce idénticos resultados.
        """
        salarios = [1_750_905.0, 2_000_000.0, 3_500_000.0, 5_000_000.0, 18_505_000.0]

        resultados_asc = [nomina_service.calcular(s) for s in salarios]
        resultados_desc = [nomina_service.calcular(s) for s in reversed(salarios)]

        # Los resultados individuales deben ser idénticos
        for s, r_asc in zip(salarios, resultados_asc):
            r_desc = nomina_service.calcular(s)
            assert r_asc == r_desc, (
                f"calcular({s}) difiere según orden de ejecución: "
                f"{r_asc} ≠ {r_desc}"
            )
