"""
nexa_engine/domain/services/nomina_cargada.py
===============================================
Servicio de dominio: cálculo de nómina cargada por FTE.

Responsabilidad
---------------
Transforma un salario base en el costo mensual total que le representa
al empleador contratar a un FTE en Colombia, aplicando las reglas laborales
vigentes: seguridad social, parafiscales, prestaciones sociales y beneficios.

Reglas de negocio
-----------------
1. Base imponible (T. Imponible) = salario_base × (1 + comision × cumplimiento)
2. Auxilio de transporte y dotaciones aplican solo si T.Imponible < 2 × SMMLV
3. Prestaciones (cesantías, primas) = 0 si T.Imponible ≥ 10 × SMMLV
4. Para altos salarios (> 10 × SMMLV): factor corrector 0.70 sobre salud,
   pensión, caja, ICBF+SENA, ARL y vacaciones
5. Contratos de aprendizaje (SENA, Inclusión):
   - Sin pensión ni ARL
   - Sin dotaciones
   - Solo caja (4%) como parafiscal

Parámetros de entrada
---------------------
Los parámetros se reciben vía inyección desde MasterDataRepository:
  - aportes_patronales: tasas de salud, pensión, ARL, caja, ICBF+SENA
  - prestaciones:       tasas de cesantías, primas, interés cesantías, vacaciones
  - salario_minimo:     SMMLV vigente (umbral para auxilio, dotaciones, prestaciones)
  - auxilio_transporte: valor mensual del auxilio
  - dotaciones_mensual: costo mensual proporcional de dotaciones
  - pct_cumplimiento_variable: factor de cumplimiento aplicado a comisiones

Integración
-----------
Consumido por SimulationContextBuilder para calcular el salario_cargado
de cada perfil antes de pasar al motor de cálculo.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParametrosNominaLaboral:
    """
    Tasas y valores que definen el costo laboral según la normativa vigente.

    Todos los campos son fraccionarios (ej. 0.085 para 8.5%), excepto
    los valores monetarios (auxilio_transporte, dotaciones_mensual).

    Todos los campos son obligatorios — no existen defaults hardcodeados.
    Los valores provienen exclusivamente de storage/parametrization/
    a través de ParametrizationProvider.get_nomina_laboral_params().
    """
    salario_minimo: float
    auxilio_transporte: float
    dotaciones_mensual: float
    pct_cumplimiento_variable: float
    # Umbrales de alto salario — fuente: OP-Config
    factor_alto_salario_smmlv: float       # Umbral: salarios > N × SMMLV (ej. 10.0)
    factor_corrector_alto_salario: float   # Corrector patronal alto salario (ej. 0.70)
    tasa_salud: float
    tasa_pension: float
    tasa_arl: float
    tasa_caja: float
    tasa_icbf_sena: float
    tasa_cesantias: float
    tasa_primas: float
    tasa_interes_cesantia: float
    tasa_vacaciones: float
    # Ley 1819 de 2016 — ACTIVA (confirmado por validación contra Excel V2-4).
    # T.Imponible < 10×SMMLV → Salud=0, ICBF+Sena=0 (exoneración patronal).
    # T.Imponible ≥ 10×SMMLV → se cobran con factor corrector 0.70.
    # Campo retenido para compatibilidad con payloads existentes.
    aplica_ley_1819: bool = True


class NominaCargadaService:
    """
    Calcula el costo mensual total por FTE (nómina cargada).

    Encapsula las reglas del derecho laboral colombiano para la liquidación
    de nómina: aportes patronales, prestaciones sociales y beneficios.

    No tiene estado interno — todos los cálculos son deterministas a partir
    de los parámetros inyectados al construir la instancia.
    """

    def __init__(self, parametros: ParametrosNominaLaboral) -> None:
        self._p = parametros

    # ──────────────────────────────────────────────────────────────
    # Interfaz pública
    # ──────────────────────────────────────────────────────────────

    def calcular(self, salario_base: float, comision_pct: float = 0.0) -> float:
        """
        Calcula la nómina cargada estándar para un empleado de planta.

        La base imponible incorpora la comisión esperada ajustada por el
        factor de cumplimiento variable configurado en los parámetros.

        Args:
            salario_base:  Salario contractual mensual del empleado.
            comision_pct:  Porcentaje de comisión sobre el salario base
                           (ej. 0.10 para 10%). Default 0.

        Returns:
            Costo mensual total por FTE a cargo del empleador.
        """
        p = self._p
        smmlv = p.salario_minimo
        umbral_alto = self._p.factor_alto_salario_smmlv * smmlv

        # Excel V2-8 · 'Inputs de Nomina'!F62 = C62 + D62 (=2,350,905) · base+comisión COMPLETA
        # 'Nomina Loaded'!R205 carga la comisión variable completa con factor prestacional.
        # El factor de cumplimiento (pct_cumplimiento_variable) NO reduce la base imponible
        # cargada — se aplica aguas abajo en NominaCalculator._comisiones, no aquí.
        # VARIABLE_COMP_LOAD_DECISION = APPLY_PRESTATIONAL_LOAD_LIKE_EXCEL.
        t_imponible = salario_base * (1.0 + comision_pct)
        aux         = p.auxilio_transporte if t_imponible < 2 * smmlv else 0.0
        t_haberes   = t_imponible + aux

        alto_salario = t_imponible > umbral_alto

        # Aportes patronales de seguridad social
        # Ley 1819 de 2016: empleadores exonerados de Salud (8.5%) e ICBF+Sena (4%)
        # para empleados con T.Imponible < 10×SMMLV (fórmula Excel: IF(F>10*SMMLV,...,0))
        if alto_salario:
            factor = p.factor_corrector_alto_salario
            salud     = t_imponible * p.tasa_salud    * factor
            pension   = t_imponible * p.tasa_pension  * factor
            arl       = t_imponible * p.tasa_arl      * factor
            caja      = t_imponible * p.tasa_caja     * factor
            icbf_sena = t_imponible * p.tasa_icbf_sena* factor
            vac_rate  = p.tasa_vacaciones             * factor
        else:
            # Salarios < 10×SMMLV: Ley 1819 exonera Salud e ICBF+Sena (= 0)
            # Excel formula: I_col = IF(F>10*SMMLV, F*tasa*70%, 0)
            #                O_col = IF(F>10*SMMLV, F*tasa*70%, 0)
            salud     = 0.0
            icbf_sena = 0.0
            pension   = t_imponible * p.tasa_pension
            arl       = t_imponible * p.tasa_arl
            caja      = t_imponible * p.tasa_caja
            vac_rate  = p.tasa_vacaciones

        seg_social   = t_haberes + salud + pension + arl
        parafiscales = caja + icbf_sena

        # Prestaciones sociales (sobre T.Haberes; excluidas para altos salarios)
        if t_haberes <= umbral_alto:
            cesantias = t_haberes * p.tasa_cesantias
            primas    = t_haberes * p.tasa_primas
            int_ces   = cesantias * p.tasa_interes_cesantia
        else:
            cesantias = primas = int_ces = 0.0

        vacaciones   = t_imponible * vac_rate
        prestaciones = cesantias + primas + int_ces + vacaciones

        # Beneficios en especie
        dotaciones = p.dotaciones_mensual if t_imponible < 2 * smmlv else 0.0

        return seg_social + parafiscales + prestaciones + dotaciones

    def calcular_sm(self, salario_base: float) -> float:
        """
        Nómina cargada para roles del equipo S&M (Cadena B).

        Diferencias respecto a la nómina estándar:
          - Prestaciones (cesantías, primas, int_ces, vacaciones) se calculan
            sobre el MONTO de pensión, no sobre haberes
          - Sin caja (4%) como parafiscal
          - ARL se incluye tanto en seg_social como en parafiscales
        """
        p = self._p
        smmlv = p.salario_minimo
        umbral_alto = self._p.factor_alto_salario_smmlv * smmlv

        t_imponible = salario_base
        aux         = p.auxilio_transporte if t_imponible < 2 * smmlv else 0.0
        t_haberes   = t_imponible + aux

        alto_salario = t_imponible > umbral_alto

        if alto_salario:
            factor    = p.factor_corrector_alto_salario
            salud     = t_imponible * p.tasa_salud    * factor
            pension   = t_imponible * p.tasa_pension  * factor
            arl       = t_imponible * p.tasa_arl      * factor
            icbf_sena = t_imponible * p.tasa_icbf_sena* factor
        else:
            # Excel V2-4 legacy: Salud e ICBF+SENA se cobran siempre.
            salud     = t_imponible * p.tasa_salud
            pension   = t_imponible * p.tasa_pension
            arl       = t_imponible * p.tasa_arl
            icbf_sena = t_imponible * p.tasa_icbf_sena

        seg_social   = t_haberes + salud + pension + arl
        parafiscales = arl + icbf_sena

        cesantias  = pension * p.tasa_cesantias
        primas     = pension * p.tasa_primas
        int_ces    = pension * p.tasa_interes_cesantia
        vacaciones = pension * p.tasa_vacaciones
        prestaciones = cesantias + primas + int_ces + vacaciones

        dotaciones = p.dotaciones_mensual if t_imponible < 2 * smmlv else 0.0

        return seg_social + parafiscales + prestaciones + dotaciones

    def calcular_aprendiz(self, salario_base: float) -> float:
        """
        Nómina cargada para contratos de aprendizaje (SENA e Inclusión).

        Diferencias respecto a la nómina estándar:
          - Sin pensión ni ARL (exentos por ley en contratos de aprendizaje)
          - Sin ICBF+SENA
          - Solo parafiscal de caja (4%)
          - Sin dotaciones

        Args:
            salario_base: Apoyo de sostenimiento mensual del aprendiz.

        Returns:
            Costo mensual total por aprendiz a cargo del empleador.
        """
        p     = self._p
        smmlv = p.salario_minimo

        t_imponible = salario_base
        aux         = p.auxilio_transporte if t_imponible < 2 * smmlv else 0.0
        t_haberes   = t_imponible + aux

        # Contratos de aprendizaje: sin pensión, sin ARL, sin ICBF+SENA
        caja         = t_imponible * p.tasa_caja
        seg_social   = t_haberes  # solo haberes, sin aportes de SS
        parafiscales = caja

        cesantias    = t_haberes * p.tasa_cesantias
        primas       = t_haberes * p.tasa_primas
        int_ces      = cesantias * p.tasa_interes_cesantia
        vacaciones   = t_imponible * p.tasa_vacaciones
        prestaciones = cesantias + primas + int_ces + vacaciones

        return seg_social + parafiscales + prestaciones

    @classmethod
    def desde_parametrizacion(cls, provider, aplica_ley_1819: bool = True) -> "NominaCargadaService":
        """
        Construye el servicio a partir de un IParametrizationProvider.

        Lee los parámetros desde la versión activa de parametrización HR,
        que contiene salarios, aportes patronales y prestaciones vigentes.

        Args:
            provider: Instancia de ParametrizationProvider (o cualquier proveedor
                      que implemente get_nomina_laboral_params()).
            aplica_ley_1819: Retenido para compatibilidad con callers existentes.
                             Valor ignorado — Salud e ICBF+SENA se cobran siempre
                             (modo Excel V2-4 legacy).

        Returns:
            NominaCargadaService configurado con las tasas de la parametrización activa.
        """
        datos = provider.get_nomina_laboral_params()
        aps   = datos["aportes_patronales"]
        pre   = datos["prestaciones"]

        params = ParametrosNominaLaboral(
            salario_minimo                = datos["salario_minimo"],
            auxilio_transporte            = datos["auxilio_transporte"],
            dotaciones_mensual            = datos["dotaciones_mensual"],
            pct_cumplimiento_variable     = datos["pct_cumplimiento_variable"],
            factor_alto_salario_smmlv     = datos["factor_alto_salario_smmlv"],
            factor_corrector_alto_salario = datos["factor_corrector_alto_salario"],
            tasa_salud                    = aps["salud"],
            tasa_pension                  = aps["pension"],
            tasa_arl                      = aps["arl_staff"],
            tasa_caja                     = aps["caja"],
            tasa_icbf_sena                = aps["icbf_sena"],
            tasa_cesantias                = pre["cesantias"],
            tasa_primas                   = pre["primas"],
            tasa_interes_cesantia         = pre["interes_cesantia"],
            tasa_vacaciones               = pre["vacaciones"],
            aplica_ley_1819               = aplica_ley_1819,
        )
        return cls(params)
