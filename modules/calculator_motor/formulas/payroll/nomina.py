"""
modules.calculator.formulas.payroll.calculator
===============================================

NominaCalculator — Capa 2 del pipeline de cálculo.

Responsabilidad
---------------
Calcular el costo total de nómina para cada perfil de Cadena A en cada mes
del contrato, aplicando el factor de indexación salarial correspondiente.

Los componentes calculados por perfil son:
  - Salario fijo        = salario_cargado × FTE × factor_indexación
  - Capacitación inicial= (días × tarifa × FTE × factor) / meses_contrato
                          (costo de arranque amortizado en todo el contrato)
  - Capacitación rotación = días × tarifa × (FTE × pct_rotacion) × factor
  - Exámenes médicos    = costo_examen × FTE_efectivo × (fracción_total) × factor
                          donde fracción_total = 1/meses + pct_rotacion + pct_anual/12
  - Estudios de seguridad = costo_estudio × FTE × factor

Factor de indexación
--------------------
Cada mes aplica el factor combinado de:
  - Factor base del año de inicio (ej. 1.18227 para el componente 70SMMLV+30IPC en 2026)
  - Factor de aumento anual a partir del mes configurado (ej. mes 13 → +9.98%)

El resultado es que los salarios del año 1 difieren de los del año 2 según
la inflación proyectada para el período del contrato.

Exámenes médicos — tres componentes
-------------------------------------
El costo de exámenes no es un costo mensual fijo. Se compone de:
  1. Nuevos (ingreso inicial): FTE × costo / meses_contrato
     → Examina a todos los contratados al inicio, amortizado en el contrato
  2. Rotación:  FTE × costo × pct_rotacion_mensual
     → Cada mes ingresa personal nuevo por reemplazos
  3. Anual (periódico): FTE × costo × pct_examen_anual / 12
     → Porcentaje de empleados que requieren examen periódico

El FTE efectivo para exámenes (fte_examenes) es mayor que el FTE del perfil
base porque incluye la fracción proporcional de supervisores, formadores y
monitores, quienes también deben examinarse al ingresar.

Consume
-------
  - ParametrosNomina: factor de indexación, costos de capacitación y exámenes
  - ParametrosCalculo: porcentajes de rotación y examen anual
  - Lista de PerfilCadenaA: FTE, salario, flags de elegibilidad y FTE de exámenes

Produce
-------
  ResultadoNomina con todos los componentes de costo sumados para el mes dado.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from nexa_engine.modules.audit.trace import trace as _audit_trace
from nexa_engine.modules.calculator_motor.formulas.payroll.factors import PayrollCalculator
from nexa_engine.modules.shared.models import (
    ParametrosCalculo,
    ParametrosNomina,
    PerfilCadenaA,
    ResultadoNomina,
)

logger = logging.getLogger(__name__)


class NominaCalculator:
    """
    Calcula el costo total de nómina para todos los perfiles de Cadena A en un mes.

    @excel_lineage:
      version: V2-8
      sheet: Nomina Loaded
      cells: [D14:BK14 (date headers), C14:BK{rol} (per-role monthly cost rows)]
      concept: costo_nomina_mensual_cadena_a
    @runtime_sources:
      - storage/parametrization/hr → ParametrosNomina (salario_cargado, tarifa_dia_cap,
        costo_examen_medico, costo_estudio_seg, tarifa_crucero, factor_indexacion_base,
        pct_aumento_salarial, mes_aplicacion_aumento)
      - storage/parametrization/hr → ParametrosCalculo (pct_rotacion, pct_examen_anual)
      - request/request.json → PerfilCadenaA[] (fte, dias_cap_inicial, dias_cap_rotacion,
        incluye_examenes, incluye_seguridad, incluye_crucero, es_soporte)
    @confidence: HIGH
    @forbidden:
      - hardcoded_excel_values (all salary/factor values come from HR parametrization)
    """

    class FORMULA_ID:
        """Trazabilidad de fórmulas de nómina — Capa 2."""
        SALARIO_CARGADO = "NOMINA.SALARIO_CARGADO"
        SALARIO_FIJO = "NOMINA.SALARIO_FIJO"
        FACTOR_INDEXACION = "NOMINA.FACTOR_INDEXACION"
        COMISIONES = "NOMINA.COMISIONES"
        CAPACITACION_INICIAL = "NOMINA.CAPACITACION_INICIAL"
        CAPACITACION_ROTACION = "NOMINA.CAPACITACION_ROTACION"
        EXAMENES_MEDICOS = "NOMINA.EXAMENES_MEDICOS"
        EXAMENES_NUEVOS = "NOMINA.EXAMENES_NUEVOS"
        EXAMENES_ROTACION = "NOMINA.EXAMENES_ROTACION"
        EXAMENES_ANUAL = "NOMINA.EXAMENES_ANUAL"
        SEGURIDAD = "NOMINA.SEGURIDAD"
        CRUCERO = "NOMINA.CRUCERO"
        TOTAL_MENSUAL = "NOMINA.TOTAL_MENSUAL"

    def __init__(self, parametros_nomina: ParametrosNomina,
                 parametros_calculo: ParametrosCalculo) -> None:
        self._nom = parametros_nomina
        self._cal = parametros_calculo

    def calcular_para_mes(self, perfiles: List[PerfilCadenaA], mes: int) -> ResultadoNomina:
        """
        Suma el costo de nómina de todos los perfiles para el mes dado.

        Args:
            perfiles: Lista de perfiles de agentes y staff de Cadena A.
            mes:      Número de mes del contrato (1-based).

        Returns:
            ResultadoNomina con la suma de todos los componentes por todos los perfiles.
        """
        acumulado = ResultadoNomina()
        for perfil in perfiles:
            por_perfil = self._calcular_perfil(perfil, mes)
            acumulado.salario_fijo  += por_perfil.salario_fijo
            acumulado.comisiones    += por_perfil.comisiones
            acumulado.capacitacion_inicial   += por_perfil.capacitacion_inicial
            acumulado.capacitacion_rotacion  += por_perfil.capacitacion_rotacion
            acumulado.examenes      += por_perfil.examenes
            acumulado.seguridad     += por_perfil.seguridad
            acumulado.crucero       += por_perfil.crucero
        # WAVE 5 structured log — one per (mes) call, INFO level, lazy formatting.
        logger.info(
            "[PAYROLL_BUILD] op=calcular_para_mes mes=%s inputs={perfiles:%d} "
            "outputs={salario_fijo:%.2f,comisiones:%.2f,capacitacion_inicial:%.2f,"
            "capacitacion_rotacion:%.2f,examenes:%.2f,seguridad:%.2f,crucero:%.2f} source=HR-Nomina+HR-Med-Seg",
            mes, len(perfiles),
            acumulado.salario_fijo, acumulado.comisiones, acumulado.capacitacion_inicial,
            acumulado.capacitacion_rotacion, acumulado.examenes, acumulado.seguridad,
            acumulado.crucero,
        )
        return acumulado

    def calcular_desglose_por_rol(
        self, perfiles: List[PerfilCadenaA], mes: int
    ) -> Dict[str, float]:
        """
        Costo de nómina cargada total por nombre de perfil para el mes dado.

        Excel V2-8 · 'Nomina Loaded'!B43:B66 — SUMIFS por rol × escenario
        Intermediate output for Graph 2 (Graficos!P4:AF29).

        Reuses _calcular_perfil without altering calcular_para_mes behavior.
        When multiple profiles share the same nombre (e.g. split sub-configs of
        the same role), their costs are summed under that nombre — consistent
        with the Excel SUMIFS aggregation by role name.

        Returns:
            {perfil.nombre: ResultadoNomina.total}
        """
        totales: Dict[str, float] = {}
        for perfil in perfiles:
            costo = self._calcular_perfil(perfil, mes).total
            totales[perfil.nombre] = totales.get(perfil.nombre, 0.0) + costo
        return totales

    # ──────────────────────────────────────────────────────────────
    # Cálculo por perfil
    # ──────────────────────────────────────────────────────────────

    def _calcular_perfil(self, perfil: PerfilCadenaA, mes: int) -> ResultadoNomina:
        if not self._mes_activo(mes):
            return ResultadoNomina()

        return ResultadoNomina(
            salario_fijo = self._salario_fijo(perfil, mes),
            comisiones   = self._comisiones(perfil, mes),
            capacitacion_inicial  = self._cap_inicial(perfil, mes),
            capacitacion_rotacion = self._cap_rotacion(perfil, mes),
            examenes     = self._examenes(perfil, mes),
            seguridad    = self._seguridad(perfil, mes),
            crucero      = self._crucero(perfil, mes),
        )

    def _factor_indexacion(self, mes: int) -> float:
        """
        Factor combinado de indexación salarial para el mes dado.

        Combina el factor base del año de inicio (refleja la inflación acumulada
        desde el año base 2025 hasta el año de inicio del contrato) con el
        factor de incremento anual relativo a partir del mes configurado.
        """
        return self._nom.factor_indexacion_base * PayrollCalculator.calcular_factor_aumento(
            mes,
            self._nom.pct_aumento_salarial,
            self._nom.mes_aplicacion_aumento,
        )

    def _salario_fijo(self, perfil: PerfilCadenaA, mes: int) -> float:
        """
        Costo de salario fijo mensual.

        Usa salario_cargado (nómina cargada completa incluyendo SS sobre comisiones)
        y resta la comisión bruta para que salario_fijo + comisiones = total cargado.
        """
        base = perfil.salario_cargado if perfil.salario_cargado > 0 else perfil.salario_base
        factor_idx = self._factor_indexacion(mes)
        total_cargado = base * perfil.fte * factor_idx
        comisiones = self._comisiones(perfil, mes)
        result = total_cargado - comisiones

        # tipo_laboral: usar el campo del perfil si está poblado, sino default por flag.
        tipo_laboral = getattr(perfil, "tipo_carga", None) or (
            "EQUIPO_SOPORTE_MANTENIMIENTO" if perfil.es_soporte else "EMPLEADO_ESTANDAR"
        )
        _audit_trace(
            component="payroll.salario_fijo",
            rule=f"{tipo_laboral}.salario_fijo = (salario_cargado × FTE × factor_indexacion) − comisiones",
            formula="(salario_cargado × FTE × factor_indexacion) − comisiones",
            inputs={
                "salario_cargado": base,
                "fte": perfil.fte,
                "factor_indexacion": factor_idx,
                "comisiones": comisiones,
            },
            intermediate={"total_cargado": total_cargado},
            result=result,
            source="HR-Nomina + HR-SegSocial + HR-Prestaciones (via NominaCargadaService)",
            tipo_laboral=tipo_laboral,
            rol=perfil.nombre,
            canal=perfil.canal,
            mes=mes,
        )
        return result

    def _comisiones(self, perfil: PerfilCadenaA, mes: int) -> float:
        """
        Costo de comisiones (componente variable bruto = comisión cruda).

        EXCEL V2-8 · 'Nomina Loaded'!205 ← 'Inputs de Nomina'!D62 · fórmula: =C{rol} × factor_indexacion
        El componente variable de Vision CTS (C38 'Salario Variable') es la comisión CRUDA
        (`Inputs de Nomina`!D62 = salario_base × comision_pct, p.ej. 600,000), SIN factor de
        cumplimiento y sin carga social adicional (la carga ya está dentro del salario cargado /
        salario_fijo). Antes el backend aplicaba `× pct_cumplimiento_variable` (0.70), que NO
        existe en la línea de costo del Excel → inflaba salario_fijo (carve-out) y reducía la
        variable. El cumplimiento (0.70) no aplica a la línea de costo de comisiones.
        Nota: salario_fijo = total_cargado − comisiones, por lo que este cambio reparte fijo↔variable
        sin alterar el total cargado (invariante) → C34/PyG/Tarifas no cambian, solo el split C37/C38.
        """
        factor_idx = self._factor_indexacion(mes)
        result = (perfil.salario_base * perfil.fte * perfil.comision_pct
                  * factor_idx)
        if perfil.comision_pct > 0:
            _audit_trace(
                component="payroll.comisiones",
                rule="EMPLEADO.comisiones = salario_base × FTE × comision_pct × factor_idx (comisión cruda, sin cumplimiento — Excel D62)",
                formula="salario_base × FTE × comision_pct × factor_indexacion",
                inputs={
                    "salario_base": perfil.salario_base,
                    "fte": perfil.fte,
                    "comision_pct": perfil.comision_pct,
                    "factor_indexacion": factor_idx,
                },
                result=result,
                source="HR-Nomina.ComisionPct (Excel 'Inputs de Nomina'!D62, comisión cruda)",
                tipo_laboral=("EMPLEADO_ESTANDAR" if not perfil.es_soporte else "SOPORTE_COMISIONABLE"),
                rol=perfil.nombre, canal=perfil.canal, mes=mes,
            )
        return result

    def _cap_inicial(self, perfil: PerfilCadenaA, mes: int) -> float:
        """
        Costo de capacitación inicial amortizado en el contrato.

        El costo total de capacitación de arranque se divide entre todos
        los meses del contrato para distribuirlo uniformemente.
        """
        return (
            perfil.dias_cap_inicial
            * self._nom.tarifa_dia_cap
            * perfil.fte
            * self._factor_indexacion(mes)
            / self._nom.meses_contrato
        )

    def _cap_rotacion(self, perfil: PerfilCadenaA, mes: int) -> float:
        """
        Costo de capacitación mensual por nuevos ingresos (rotación).

        Cada mes, el porcentaje de rotación de la operación implica contratar
        y capacitar nuevas personas para cubrir los reemplazos.
        """
        personas_nuevas_mes = perfil.fte * self._cal.pct_rotacion
        return (
            perfil.dias_cap_rotacion
            * self._nom.tarifa_dia_cap
            * personas_nuevas_mes
            * self._factor_indexacion(mes)
        )

    def _examenes(self, perfil: PerfilCadenaA, mes: int) -> float:
        """
        Costo mensual de exámenes médicos ocupacionales (tres componentes).

        Componente 1 — Ingreso inicial (amortizado):
            FTE × costo × 1/meses_contrato

        Componente 2 — Rotación mensual:
            FTE × costo × pct_rotacion

        Componente 3 — Examen anual periódico (proporcionalizado a mes):
            FTE × costo × (pct_examen_anual / 12)

        El FTE efectivo incluye la fracción proporcional de supervisores,
        formadores y monitores, quienes también deben examinarse.
        """
        if not perfil.incluye_examenes:
            return 0.0

        fte_efectivo = perfil.fte_examenes if perfil.fte_examenes > 0 else perfil.fte
        fraccion_mensual = (
            1.0 / self._nom.meses_contrato
            + self._cal.pct_rotacion
            + self._cal.pct_examen_anual / 12
        )
        return (
            self._nom.costo_examen_medico
            * fte_efectivo
            * fraccion_mensual
            * self._factor_indexacion(mes)
        )

    def _seguridad(self, perfil: PerfilCadenaA, mes: int) -> float:
        """Costo de estudios de seguridad (antecedentes, visitas domiciliarias)."""
        if not perfil.incluye_seguridad:
            return 0.0
        return (self._nom.costo_estudio_seg * perfil.fte * self._factor_indexacion(mes))

    def _crucero(self, perfil: PerfilCadenaA, mes: int) -> float:
        """
        Costo mensual de crucero por agente (Panel!C17 en Excel V2-7).

        Mensual fijo por FTE × tarifa_crucero, aplicando factor de indexación.
        Solo aplica cuando incluye_crucero = True en el perfil.
        """
        if not getattr(perfil, "incluye_crucero", False):
            return 0.0
        if self._nom.tarifa_crucero <= 0:
            return 0.0
        return self._nom.tarifa_crucero * perfil.fte * self._factor_indexacion(mes)

    def _mes_activo(self, mes: int) -> bool:
        return self._nom.mes_inicio <= mes <= self._nom.mes_fin


__all__ = ["NominaCalculator"]
