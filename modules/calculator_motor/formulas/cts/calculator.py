"""
nexa_engine/modules/calculator_motor/formulas/cts/calculator.py
===============================================================
Cost To Serve calculator — costo promedio mensual por unidad operativa.

Ownership: calculator_motor (moved from vision_cost_to_serve in Block 20C).

Denominadores:
  denominador_cadena_a = $Sigma_canal_outbound(FTE) + $Sigma_canal_inbound(vol_cadena_a_mensual)
  denominador_cadena_b = $Sigma volumen mensual de canales activos Cadena B
  denominador_cadena_c = $Sigma volumen mensual de canales activos Cadena C

Semántica del denominador de Cadena A:
  - Inbound usa el volumen mensual atendido por Cadena A.
  - Outbound usa FTE como unidad operativa equivalente.

Fórmulas:
  cost_to_serve_cadena_a = avg_costo_a / denominador_cadena_a
  cost_to_serve_cadena_b = avg_costo_b / denominador_cadena_b
  cost_to_serve_cadena_c = avg_costo_c / denominador_cadena_c
  ponderado = suma ponderada por denominadores activos
"""

from __future__ import annotations

import logging
from typing import List, Optional

from nexa_engine.modules.shared.models import (
    CanalCTSDetalle,
    DesgloseCTSCadenaA,
    DesgloseCTSCadenaB,
    ParametrosCadenaB,
    ParametrosCadenaC,
    PerfilCadenaA,
    PyGMensual,
    ResultadoCostToServe,
)
from nexa_engine.modules.vision_cost_to_serve.helpers.servicio_catalogo import (
    canal_detail_habilitado,
)
from nexa_engine.modules.calculator_motor.formulas.cts.cts_facts import CostToServeFacts

logger = logging.getLogger(__name__)


class CostToServeCalculator:

    class FORMULA_ID:
        """Trazabilidad de fórmulas de Cost To Serve — Capa 9."""

        DENOMINADOR_CADENA_A = "CTS.DENOMINADOR_CADENA_A"
        DENOMINADOR_CADENA_B = "CTS.DENOMINADOR_CADENA_B"
        DENOMINADOR_CADENA_C = "CTS.DENOMINADOR_CADENA_C"
        COSTO_CADENA_A = "CTS.COSTO_CADENA_A"
        COSTO_CADENA_B = "CTS.COSTO_CADENA_B"
        COSTO_CADENA_C = "CTS.COSTO_CADENA_C"
        COSTO_PONDERADO = "CTS.COSTO_PONDERADO"
        DESGLOSE_CADENA_A = "CTS.DESGLOSE_CADENA_A"
        DESGLOSE_CADENA_B = "CTS.DESGLOSE_CADENA_B"
        CANALES_DETALLE = "CTS.CANALES_DETALLE"
        PARTICIPACION_A = "CTS.PARTICIPACION_A"
        PARTICIPACION_B = "CTS.PARTICIPACION_B"
        PARTICIPACION_C = "CTS.PARTICIPACION_C"

    def __init__(
        self,
        perfiles_cadena_a: List[PerfilCadenaA],
        parametros_cadena_b: ParametrosCadenaB,
        parametros_cadena_c: Optional[ParametrosCadenaC] = None,
        linea_negocio: str = "",
        cts_facts: Optional[CostToServeFacts] = None,
    ) -> None:
        self._perfiles = perfiles_cadena_a
        self._canales_b = parametros_cadena_b.canales
        self._canales_c = parametros_cadena_c.canales if parametros_cadena_c else []
        self._linea_negocio = linea_negocio
        self._facts = cts_facts

    def calcular(self, pyg_por_mes: List[PyGMensual]) -> ResultadoCostToServe:
        numero_meses = len(pyg_por_mes)
        if numero_meses == 0:
            return ResultadoCostToServe()

        denominador_cadena_a = self._denominador_cadena_a()
        denominador_cadena_b = self._denominador_cadena_b()
        denominador_cadena_c = self._denominador_cadena_c()

        avg_payroll_a = (
            sum(pyg_mensual.payroll_a for pyg_mensual in pyg_por_mes) / numero_meses
        )
        avg_no_payroll_a = (
            sum(pyg_mensual.no_payroll_a for pyg_mensual in pyg_por_mes) / numero_meses
        )
        avg_costo_b = (
            sum(pyg_mensual.costo_b for pyg_mensual in pyg_por_mes) / numero_meses
        )
        avg_costo_c = (
            sum(pyg_mensual.costo_c_fin for pyg_mensual in pyg_por_mes) / numero_meses
        )

        cost_to_serve_cadena_a = (
            (avg_payroll_a + avg_no_payroll_a) / denominador_cadena_a
            if denominador_cadena_a > 0
            else 0.0
        )
        cost_to_serve_cadena_b = (
            avg_costo_b / denominador_cadena_b if denominador_cadena_b > 0 else 0.0
        )
        cost_to_serve_cadena_c = (
            avg_costo_c / denominador_cadena_c if denominador_cadena_c > 0 else 0.0
        )

        denominador_total_cost_to_serve = (
            denominador_cadena_a + denominador_cadena_b + denominador_cadena_c
        )
        cost_to_serve_ponderado = (
            (
                cost_to_serve_cadena_a * denominador_cadena_a
                + cost_to_serve_cadena_b * denominador_cadena_b
                + cost_to_serve_cadena_c * denominador_cadena_c
            )
            / denominador_total_cost_to_serve
            if denominador_total_cost_to_serve > 0
            else 0.0
        )

        desglose_a = self._calcular_desglose_a(
            numero_meses,
            denominador_cadena_a,
            avg_payroll_a,
            avg_no_payroll_a,
        )
        desglose_b = self._calcular_desglose_b(numero_meses, denominador_cadena_b)
        canales_detalle = self._calcular_canales_detalle(numero_meses)

        costo_total_acumulado = sum(
            pyg_mensual.costo_total for pyg_mensual in pyg_por_mes
        )

        logger.info(
            "[VISION_BUILD] op=calcular_cost_to_serve inputs={meses:%d,denominador_cadena_a:%.4f,denominador_cadena_b:%.4f,denominador_cadena_c:%.4f} "
            "outputs={cost_to_serve_cadena_a:%.4f,cost_to_serve_cadena_b:%.4f,cost_to_serve_cadena_c:%.4f,cost_to_serve_ponderado:%.4f} source=PyG+Cadenas",
            numero_meses,
            denominador_cadena_a,
            denominador_cadena_b,
            denominador_cadena_c,
            cost_to_serve_cadena_a,
            cost_to_serve_cadena_b,
            cost_to_serve_cadena_c,
            cost_to_serve_ponderado,
        )
        return ResultadoCostToServe(
            cts_cadena_a=cost_to_serve_cadena_a,
            cts_cadena_b=cost_to_serve_cadena_b,
            cts_cadena_c=cost_to_serve_cadena_c,
            cts_ponderado=cost_to_serve_ponderado,
            participacion_a=(
                denominador_cadena_a / denominador_total_cost_to_serve
                if denominador_total_cost_to_serve > 0
                else 0.0
            ),
            participacion_b=(
                denominador_cadena_b / denominador_total_cost_to_serve
                if denominador_total_cost_to_serve > 0
                else 0.0
            ),
            participacion_c=(
                denominador_cadena_c / denominador_total_cost_to_serve
                if denominador_total_cost_to_serve > 0
                else 0.0
            ),
            fte_cadena_a=denominador_cadena_a,
            vol_cadena_b=denominador_cadena_b,
            vol_cadena_c=denominador_cadena_c,
            desglose_a=desglose_a,
            desglose_b=desglose_b,
            costo_total_acumulado=costo_total_acumulado,
            canal_view_habilitado=canal_detail_habilitado(self._linea_negocio),
            canales_detalle=canales_detalle,
        )

    def _denominador_cadena_a(self) -> float:
        return sum(
            self._contribucion_denominador_cadena_a(perfil)
            for perfil in self._perfiles
            if not perfil.es_soporte
        )

    def _contribucion_denominador_cadena_a(self, perfil: "PerfilCadenaA") -> float:
        modalidad = (perfil.modalidad or "").strip().lower()
        if modalidad == "outbound":
            return perfil.fte
        return perfil.vol_cadena_a_mensual

    def _denominador_cadena_b(self) -> float:
        return sum(
            canal_cadena_b.volumen_mensual + canal_cadena_b.vol_escalamiento
            for canal_cadena_b in self._canales_b
        )

    def _denominador_cadena_c(self) -> float:
        return sum(canal_cadena_c.volumen_mensual for canal_cadena_c in self._canales_c)

    def _calcular_desglose_a(
        self,
        numero_meses: int,
        denominador_cadena_a: float,
        avg_payroll_a: float,
        avg_no_payroll_a: float,
    ) -> DesgloseCTSCadenaA:
        nomina_agg = (
            avg_payroll_a / denominador_cadena_a if denominador_cadena_a > 0 else 0.0
        )
        no_payroll_agg = (
            avg_no_payroll_a / denominador_cadena_a if denominador_cadena_a > 0 else 0.0
        )

        facts_disponibles = (
            self._facts is not None
            and len(self._facts.nomina_por_mes) == numero_meses
            and len(self._facts.no_payroll_por_mes) == numero_meses
        )
        if denominador_cadena_a == 0 or not facts_disponibles:
            return DesgloseCTSCadenaA(
                nomina=nomina_agg,
                no_payroll=no_payroll_agg,
            )

        salario_fijo_acumulado = 0.0
        comisiones_acumuladas = 0.0
        capacitacion_inicial_acumulada = 0.0
        capacitacion_rotacion_acumulada = 0.0
        examenes_acumulados = 0.0
        seguridad_acumulada = 0.0
        crucero_acumulado = 0.0
        opex_ti_acumulado = 0.0
        capex_acumulado = 0.0
        costos_fijos_acumulados = 0.0

        assert self._facts is not None
        for resultado_nomina_mes, resultado_no_payroll_mes in zip(
            self._facts.nomina_por_mes, self._facts.no_payroll_por_mes
        ):
            salario_fijo_acumulado += resultado_nomina_mes.salario_fijo
            comisiones_acumuladas += resultado_nomina_mes.comisiones
            capacitacion_inicial_acumulada += resultado_nomina_mes.capacitacion_inicial
            capacitacion_rotacion_acumulada += (
                resultado_nomina_mes.capacitacion_rotacion
            )
            examenes_acumulados += resultado_nomina_mes.examenes
            seguridad_acumulada += resultado_nomina_mes.seguridad
            crucero_acumulado += resultado_nomina_mes.crucero
            opex_ti_acumulado += resultado_no_payroll_mes.opex_ti
            capex_acumulado += resultado_no_payroll_mes.capex
            costos_fijos_acumulados += resultado_no_payroll_mes.costos_fijos

        def avg_div(valor_acumulado: float) -> float:
            return (valor_acumulado / numero_meses) / denominador_cadena_a

        return DesgloseCTSCadenaA(
            nomina=nomina_agg,
            no_payroll=no_payroll_agg,
            nomina_loaded=avg_div(salario_fijo_acumulado + comisiones_acumuladas),
            salario_fijo=avg_div(salario_fijo_acumulado),
            salario_variable=avg_div(comisiones_acumuladas),
            capacitacion_inicial=avg_div(capacitacion_inicial_acumulada),
            capacitacion_rotacion=avg_div(capacitacion_rotacion_acumulada),
            examenes=avg_div(examenes_acumulados),
            estudios_seguridad=avg_div(seguridad_acumulada),
            crucero=avg_div(crucero_acumulado),
            opex_fijo=avg_div(opex_ti_acumulado),
            inversiones=avg_div(capex_acumulado),
            costos_fijos_estacion=avg_div(costos_fijos_acumulados),
        )

    def _calcular_canales_detalle(self, numero_meses: int) -> "List[CanalCTSDetalle]":
        if self._facts is None or numero_meses == 0 or not self._facts.canales:
            return []

        detalles_por_canal: "List[CanalCTSDetalle]" = []
        for canal_facts in sorted(
            self._facts.canales, key=lambda c: (c.canal, c.modalidad)
        ):
            fte_del_canal = canal_facts.fte_del_canal
            if fte_del_canal <= 0:
                continue

            salario_fijo_acumulado = 0.0
            comisiones_acumuladas = 0.0
            capacitacion_inicial_acumulada = 0.0
            capacitacion_rotacion_acumulada = 0.0
            examenes_acumulados = 0.0
            seguridad_acumulada = 0.0
            crucero_acumulado = 0.0
            opex_ti_acumulado = 0.0
            capex_acumulado = 0.0
            costos_fijos_acumulados = 0.0
            for resultado_nomina_mes, resultado_no_payroll_mes in zip(
                canal_facts.nomina_por_mes, canal_facts.no_payroll_por_mes
            ):
                salario_fijo_acumulado += resultado_nomina_mes.salario_fijo
                comisiones_acumuladas += resultado_nomina_mes.comisiones
                capacitacion_inicial_acumulada += (
                    resultado_nomina_mes.capacitacion_inicial
                )
                capacitacion_rotacion_acumulada += (
                    resultado_nomina_mes.capacitacion_rotacion
                )
                examenes_acumulados += resultado_nomina_mes.examenes
                seguridad_acumulada += resultado_nomina_mes.seguridad
                crucero_acumulado += resultado_nomina_mes.crucero
                opex_ti_acumulado += resultado_no_payroll_mes.opex_ti
                capex_acumulado += resultado_no_payroll_mes.capex
                costos_fijos_acumulados += resultado_no_payroll_mes.costos_fijos
            canal = canal_facts.canal
            modalidad = canal_facts.modalidad

            def avg_div(valor_acumulado: float) -> float:
                return (valor_acumulado / numero_meses) / fte_del_canal

            nomina_loaded_del_canal = avg_div(
                salario_fijo_acumulado + comisiones_acumuladas
            )
            payroll_del_canal = avg_div(
                salario_fijo_acumulado
                + comisiones_acumuladas
                + capacitacion_inicial_acumulada
                + capacitacion_rotacion_acumulada
                + examenes_acumulados
                + seguridad_acumulada
                + crucero_acumulado
            )
            no_payroll_del_canal = avg_div(
                opex_ti_acumulado + capex_acumulado + costos_fijos_acumulados
            )

            participacion_del_canal = 0.0

            detalles_por_canal.append(
                CanalCTSDetalle(
                    canal=canal,
                    modalidad=modalidad,
                    fte=fte_del_canal,
                    participacion_cadena_a=participacion_del_canal,
                    cts=payroll_del_canal + no_payroll_del_canal,
                    payroll=payroll_del_canal,
                    nomina_loaded=nomina_loaded_del_canal,
                    salario_fijo=avg_div(salario_fijo_acumulado),
                    salario_variable=avg_div(comisiones_acumuladas),
                    capacitacion_inicial=avg_div(capacitacion_inicial_acumulada),
                    capacitacion_rotacion=avg_div(capacitacion_rotacion_acumulada),
                    examenes=avg_div(examenes_acumulados),
                    estudios_seguridad=avg_div(seguridad_acumulada),
                    crucero=avg_div(crucero_acumulado),
                    no_payroll=no_payroll_del_canal,
                    opex_fijo=avg_div(opex_ti_acumulado),
                    inversiones=avg_div(capex_acumulado),
                    costos_fijos=avg_div(costos_fijos_acumulados),
                )
            )
        return detalles_por_canal

    def _calcular_desglose_b(
        self,
        numero_meses: int,
        denominador_cadena_b: float,
    ) -> DesgloseCTSCadenaB:
        facts_b_disponibles = (
            self._facts is not None
            and len(self._facts.cadena_b_por_mes) == numero_meses
        )
        if denominador_cadena_b == 0 or not facts_b_disponibles:
            return DesgloseCTSCadenaB()

        opex_fijo_acumulado = 0.0
        inversiones_acumuladas = 0.0
        soporte_mantenimiento_acumulado = 0.0
        costo_variable_acumulado = 0.0
        escalamiento_acumulado = 0.0
        hitl_acumulado = 0.0

        assert self._facts is not None
        for resultado_cadena_b_mes in self._facts.cadena_b_por_mes:
            opex_fijo_acumulado += resultado_cadena_b_mes.opex_fijo
            inversiones_acumuladas += resultado_cadena_b_mes.inversiones
            soporte_mantenimiento_acumulado += (
                resultado_cadena_b_mes.soporte_mantenimiento
            )
            costo_variable_acumulado += resultado_cadena_b_mes.costo_variable
            escalamiento_acumulado += resultado_cadena_b_mes.escalamiento
            hitl_acumulado += resultado_cadena_b_mes.hitl

        def avg_div(valor_acumulado: float) -> float:
            return (valor_acumulado / numero_meses) / denominador_cadena_b

        opex_unitario = avg_div(opex_fijo_acumulado)
        inversiones_unitarias = avg_div(inversiones_acumuladas)
        soporte_mantenimiento_unitario = avg_div(soporte_mantenimiento_acumulado)
        tarifa_unitaria = avg_div(costo_variable_acumulado)
        escalamiento_unitario = avg_div(escalamiento_acumulado)
        hitl_unitario = avg_div(hitl_acumulado)

        return DesgloseCTSCadenaB(
            componente_fijo=opex_unitario
            + inversiones_unitarias
            + soporte_mantenimiento_unitario,
            opex=opex_unitario,
            inversiones=inversiones_unitarias,
            soporte_mantenimiento=soporte_mantenimiento_unitario,
            componente_variable=tarifa_unitaria + escalamiento_unitario + hitl_unitario,
            tarifa=tarifa_unitaria,
            opex_variable=0.0,
            tasa_escalamiento=escalamiento_unitario,
            hitl=hitl_unitario,
        )
