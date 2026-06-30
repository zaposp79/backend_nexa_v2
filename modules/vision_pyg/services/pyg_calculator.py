"""
nexa_engine/calculators/pyg.py
================================
Calculador del Estado de Resultados mensual — Capa 9 del pipeline.

Responsabilidad
---------------
Combinar los costos operativos de todas las cadenas con los costos
financieros y fiscales para producir el Estado de Resultados (P&G)
completo de cada mes del contrato.

Flujo por mes
-------------
  Costos cadenas A + B + C
         ↓
  CostosTotalesCalculator  →  CostosTotalesMes
         ↓
  CostosFinancierosCalculator  →  CostosFinancierosMes
         ↓
  Ingreso = Costo × (1 + margen) × ramp-up
         ↓
  PyGMensual con todos los componentes

Ingreso
-------
El ingreso se deriva aplicando el margen del deal sobre cada cadena
por separado, multiplicado por el factor de ramp-up operacional del mes.
Esto permite diferentes márgenes por cadena en el futuro.

Consume
-------
  - PanelDeControl: márgenes, número de meses, línea de negocio
  - CostosTotalesCalculator: costos operativos por mes
  - CostosFinancierosCalculator: ICA, GMF, pólizas, financiación
  - IParametrizationProvider: tabla de ramp-up por línea de negocio

Produce
-------
  Lista de PyGMensual (un elemento por mes del contrato).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List

from nexa_engine.modules.audit.trace import trace as _audit_trace
from nexa_engine.modules.calculator_motor.formulas.costos_financieros import CostosFinancierosCalculator
from nexa_engine.modules.vision_pyg.services.costos_totales_calculator import CostosTotalesCalculator
from nexa_engine.modules.shared.models import (
    PanelDeControl,
    PerfilCadenaA,
    PyGMensual,
)
from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider

logger = logging.getLogger(__name__)


def _anio_para_mes(fecha_inicio: str, mes: int) -> int:
    """Map contract month (1-based) to calendar year for annual indexation."""
    start = date.fromisoformat(fecha_inicio[:10])
    month_offset = start.month + mes - 2  # 0-based offset from Jan of start year
    return start.year + month_offset // 12


def _get_indexacion_anual(prov: IParametrizationProvider, componente: str, anio: int) -> float:
    """Annual indexation rate for a component+year. Returns 0.0 if missing or on error."""
    if not componente:
        return 0.0
    try:
        return prov.get_componente_indexacion(componente, anio)
    except Exception:
        return 0.0


class PyGCalculator:
    """
    Genera el Estado de Resultados mensual del contrato.

    Orquesta los calculadores de costos operativos y financieros para
    producir el P&G completo de cada mes, incluyendo ingreso, costo y utilidad.
    """

    class FORMULA_ID:
        """Internal formula identifiers for traceability."""
        INGRESO_CADENA_A         = "PYG.INGRESO_CADENA_A"          # costo_a / factor_billing(margen_a) × rampup
        INGRESO_CADENA_B         = "PYG.INGRESO_CADENA_B"          # costo_b / factor_billing(margen_b) × rampup
        INGRESO_CADENA_C         = "PYG.INGRESO_CADENA_C"          # costo_c / factor_billing(margen_c) × rampup
        INGRESO_BRUTO            = "PYG.INGRESO_BRUTO"             # ingreso_a + ingreso_b + ingreso_c
        IMPREVISTOS              = "PYG.IMPREVISTOS"               # panel.imprevistos × ingreso_bruto
        FACTOR_RAMPUP            = "PYG.FACTOR_RAMPUP"             # calcular_rampup(linea_negocio, mes)
        FACTOR_BILLING_A         = "PYG.FACTOR_BILLING_A"          # ProfitabilityCalculator.calcular_factor_billing(margen_a, ...)
        FACTOR_BILLING_B         = "PYG.FACTOR_BILLING_B"          # ProfitabilityCalculator.calcular_factor_billing(margen_b, ...)
        FACTOR_BILLING_C         = "PYG.FACTOR_BILLING_C"          # ProfitabilityCalculator.calcular_factor_billing(margen_c, ...)
        CONTINGENCIA_OP          = "PYG.CONTINGENCIA_OP"           # panel.op_cont × ingreso_bruto
        CONTINGENCIA_COM         = "PYG.CONTINGENCIA_COM"          # panel.com_cont × ingreso_bruto
        MARKUP_INGRESO           = "PYG.MARKUP_INGRESO"            # panel.markup × ingreso_bruto
        DESCUENTO_INGRESO        = "PYG.DESCUENTO_INGRESO"         # panel.descuento × ingreso_bruto
        ACUM_INGRESO_BRUTO       = "PYG.ACUM_INGRESO_BRUTO"        # running total ingreso_bruto
        ACUM_INGRESO_NETO        = "PYG.ACUM_INGRESO_NETO"         # running total ingreso_neto
        ACUM_COSTO_TOTAL         = "PYG.ACUM_COSTO_TOTAL"          # running total costo_total
        ACUM_COSTOS_FINANCIEROS  = "PYG.ACUM_COSTOS_FINANCIEROS"   # running total costos_financieros
        ACUM_CONTRIBUCION        = "PYG.ACUM_CONTRIBUCION"         # running total contribucion

    def __init__(
        self,
        panel: PanelDeControl,
        calculador_costos: CostosTotalesCalculator,
        calculador_financiero: CostosFinancierosCalculator,
        parametrizacion: IParametrizationProvider,
    ) -> None:
        self._panel                 = panel
        self._calculador_costos     = calculador_costos
        self._calculador_financiero = calculador_financiero
        self._parametrizacion       = parametrizacion

    def calcular_mes(self, perfiles_cadena_a: List[PerfilCadenaA], mes: int,
                     costo_mes_anterior: float | None = None) -> PyGMensual:
        """
        Calcula el Estado de Resultados completo para un mes del contrato.

        Args:
            perfiles_cadena_a:  Perfiles de agentes y staff de Cadena A.
            mes:                Número de mes del contrato (1-based).
            costo_mes_anterior: Costo operativo total del mes ANTERIOR. Para mes=1
                                debe pasarse 0.0 (convención Excel: no hay mes previo).
                                Si es None, se usa el costo del mes actual (legacy).

        Returns:
            PyGMensual con ingresos, costos y resultados del mes.
            Si el mes está fuera del rango del contrato, retorna un PyGMensual vacío.
        """
        if not self._mes_dentro_del_contrato(mes):
            return PyGMensual(mes=mes)

        factor_rampup      = self._parametrizacion.get_rampup(self._panel.linea_negocio, mes)
        costos_operativos  = self._calculador_costos.calcular_para_mes(perfiles_cadena_a, mes)
        costos_financieros = self._calculador_financiero.calcular(
            costos_operativos.total_fin, mes,
            costo_operativo_mes_anterior=costo_mes_anterior,
            costo_a=costos_operativos.costo_a,
            costo_b=costos_operativos.costo_b,
            costo_c=costos_operativos.costo_c_fin,  # full C incl. hitl/equipo/opex_var
        )

        # WAVE 3 (DIV-1, W3-1/W3-2/W3-5): Excel V2-7 usa denominador exacto por cadena con
        # margen específico (Panel!C63 margen_a, D63 margen_b=0.30, E63 margen_c=0.20).
        # Fórmula Excel: ingreso = costo / ((1-margen)(1-cont_op)(1-cont_com)(1-markup)(1+descuento))
        # Ref: ESPECIFICACION_MATEMATICA.md §4.3 (ingreso_desde_costo).
        # NOTA — Anomalía intencional de Excel V2-7 (DEC #5 WAVE 0):
        #   * Vision Tarifas usa margen_a para el precio de Cadena C (replicado en
        #     calculators/vision_tarifas.py vía _factor_billing, que toma panel.margen).
        #   * P&G (este cálculo) usa margen_c para Cadena C, como corresponde.
        # F3: Delegate factor_billing and ingreso_desde_costo to the pure
        # domain calculator (`domain/profitability/calculators.py`).
        # Single source of truth — eliminates dual runtime path.
        from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator
        m_a = self._panel.margen
        m_b = self._panel.margen_b
        m_c = self._panel.margen_c
        op_cont   = self._panel.op_cont
        com_cont  = self._panel.com_cont
        markup    = self._panel.markup
        descuento = self._panel.descuento
        factor_b_a = ProfitabilityCalculator.calcular_factor_billing(m_a, op_cont, com_cont, markup, descuento)
        factor_b_b = ProfitabilityCalculator.calcular_factor_billing(m_b, op_cont, com_cont, markup, descuento)
        factor_b_c = ProfitabilityCalculator.calcular_factor_billing(m_c, op_cont, com_cont, markup, descuento)

        # EXCEL V2-8: HME!C258/C268/C278 — ingreso base = costo opex + costos financieros por cadena.
        # HME!C258 = SUM(payroll, nopayroll, ICA, GMF, ComAdm, Pólizas, Financiación)
        # HME!C296 = C258 / (1 - margen_a)  →  ingreso_a = costo_total_a / (1 - margen_a)
        # The financial items per cadena are already computed above by CostosFinancierosCalculator.
        # No circular dependency: ICA/GMF/Pólizas are computed from opex base (Costos Totales),
        # not from ingreso. The HME cost chain is: opex → financieros(opex) → costo_total → ingreso.
        # Diferencia vs V2-7: V2-7 used costos_operativos.costo_a (opex only) as ingreso base.
        costo_total_cadena_a = (
            costos_operativos.costo_a
            + costos_financieros.ica_a
            + costos_financieros.gmf_a
            + costos_financieros.polizas_a
            + costos_financieros.comision_admin_cadena_a
            + costos_financieros.fin_a
        )
        costo_total_cadena_b = (
            costos_operativos.costo_b
            + costos_financieros.ica_b
            + costos_financieros.gmf_b
            + costos_financieros.polizas_b
            + costos_financieros.comision_admin_cadena_b
            + costos_financieros.fin_b
        )
        costo_total_cadena_c = (
            costos_operativos.costo_c
            + costos_financieros.ica_c
            + costos_financieros.gmf_c
            + costos_financieros.polizas_c
            + costos_financieros.comision_admin_cadena_c
            + costos_financieros.fin_c
        )

        ingreso_cadena_a = ProfitabilityCalculator.calcular_ingreso_desde_costo(costo_total_cadena_a, factor_b_a, factor_rampup)
        ingreso_cadena_b = ProfitabilityCalculator.calcular_ingreso_desde_costo(costo_total_cadena_b, factor_b_b, factor_rampup)
        ingreso_cadena_c = ProfitabilityCalculator.calcular_ingreso_desde_costo(costo_total_cadena_c, factor_b_c, factor_rampup)
        ingreso_bruto    = ingreso_cadena_a + ingreso_cadena_b + ingreso_cadena_c

        # EXCEL V2-8: Visión P&G!C19 (A), C20 (B), C21 (C)
        # factor = (1 + Tasas[componente][YEAR(mes_date)]) per cadena per calendar year
        # - Cadena A  → Panel!L7 = indexacion.componente_humano  (típico "IPC")
        # - Cadena B/C → Panel!L8 = indexacion.componente_tecnologico (típico "20% SMMLV 80% IPC")
        # Diferencia vs V2-7: V2-7 no aplicaba factor de indexación anual sobre ingreso
        if self._panel.indexacion and self._panel.fecha_inicio:
            _anio    = _anio_para_mes(self._panel.fecha_inicio, mes)
            _comp_a  = self._panel.indexacion.componente_humano
            _comp_bc = self._panel.indexacion.componente_tecnologico
            _rate_a  = _get_indexacion_anual(self._parametrizacion, _comp_a,  _anio)
            _rate_bc = _get_indexacion_anual(self._parametrizacion, _comp_bc, _anio)
            ingreso_cadena_a *= (1.0 + _rate_a)
            ingreso_cadena_b *= (1.0 + _rate_bc)
            ingreso_cadena_c *= (1.0 + _rate_bc)

        # GAP-PYG-1: Imprevistos = Panel!C73 × ingreso_bruto (V2-5 nuevo)
        imprevistos = self._panel.imprevistos * ingreso_bruto

        _audit_trace(
            component   = "pyg.ingreso",
            rule        = "PYG.ingreso_cadena = costo / ((1-margen)(1-op_cont)(1-com_cont)(1-markup)(1+descuento)) × factor_rampup",
            formula     = (
                "ingreso_a = costo_a / factor_billing(margen_a) × factor_rampup; "
                "ingreso_b = costo_b / factor_billing(margen_b) × factor_rampup; "
                "ingreso_c = costo_c / factor_billing(margen_c) × factor_rampup; "
                "imprevistos = imprevistos_pct × ingreso_bruto"
            ),
            inputs      = {
                "costo_a":      costos_operativos.costo_a,
                "costo_b":      costos_operativos.costo_b,
                "costo_c":      costos_operativos.costo_c,
                "costo_total_cadena_a": costo_total_cadena_a,
                "costo_total_cadena_b": costo_total_cadena_b,
                "costo_total_cadena_c": costo_total_cadena_c,
                "margen_a":     m_a,
                "margen_b":     m_b,
                "margen_c":     m_c,
                "op_cont":      op_cont,
                "com_cont":     com_cont,
                "markup":       markup,
                "descuento":    descuento,
                "factor_rampup": factor_rampup,
                "imprevistos_pct": self._panel.imprevistos,
            },
            intermediate = {
                "ingreso_cadena_a": ingreso_cadena_a,
                "ingreso_cadena_b": ingreso_cadena_b,
                "ingreso_cadena_c": ingreso_cadena_c,
                "ingreso_bruto":    ingreso_bruto,
                "imprevistos":      imprevistos,
            },
            result      = ingreso_bruto,
            source      = "Panel-Deal (margen, imprevistos), OP-RampUp (factor_rampup)",
            mes         = mes,
            formula_ids = [
                self.FORMULA_ID.INGRESO_CADENA_A,
                self.FORMULA_ID.INGRESO_CADENA_B,
                self.FORMULA_ID.INGRESO_CADENA_C,
                self.FORMULA_ID.INGRESO_BRUTO,
                self.FORMULA_ID.IMPREVISTOS,
                self.FORMULA_ID.FACTOR_RAMPUP,
                self.FORMULA_ID.FACTOR_BILLING_A,
                self.FORMULA_ID.FACTOR_BILLING_B,
                self.FORMULA_ID.FACTOR_BILLING_C,
            ],
        )

        return PyGMensual(
            mes                     = mes,
            rampup                  = factor_rampup,
            ingreso_bruto_a         = ingreso_cadena_a,
            ingreso_bruto_b         = ingreso_cadena_b,
            ingreso_bruto_c         = ingreso_cadena_c,
            contingencia_op         = self._panel.op_cont  * ingreso_bruto,
            contingencia_com        = self._panel.com_cont * ingreso_bruto,
            markup_ingreso          = self._panel.markup    * ingreso_bruto,
            descuento_ingreso       = self._panel.descuento * ingreso_bruto,
            payroll_a               = costos_operativos.payroll_a,
            no_payroll_a            = costos_operativos.no_payroll_a,
            costo_b                 = costos_operativos.costo_b,
            costo_c                 = costos_operativos.costo_c,
            costo_c_fin             = costos_operativos.costo_c_fin,
            ica                     = costos_financieros.ica,
            ica_a                   = costos_financieros.ica_a,
            ica_c                   = costos_financieros.ica_c,
            gmf_a                   = costos_financieros.gmf_a,
            gmf_c                   = costos_financieros.gmf_c,
            gmf                     = costos_financieros.gmf,
            polizas                 = costos_financieros.polizas,
            polizas_a               = costos_financieros.polizas_a,
            polizas_b               = costos_financieros.polizas_b,
            polizas_c               = costos_financieros.polizas_c,
            financiacion            = costos_financieros.financiacion,
            # GAP-PYG-1
            imprevistos_ingreso     = imprevistos,
            # GAP-PYG-3
            comision_administracion = costos_financieros.comision_administracion,
        )

    def calcular_contrato(self, perfiles_cadena_a: List[PerfilCadenaA]) -> List[PyGMensual]:
        """
        Genera el Estado de Resultados para todos los meses del contrato.

        Encadena los meses pasando el costo_total del mes ANTERIOR como base de
        financiación del mes actual (convención Excel V2-4: mes 1 no tiene mes
        previo → financiación=0; mes 2 usa costo de mes 1; etc.).

        Returns:
            Lista ordenada de PyGMensual, uno por mes del contrato (1..N).
        """
        resultados: List[PyGMensual] = []
        costo_anterior: float = 0.0  # mes 1: no hay mes previo, financiación = 0

        # Acumuladores para running totals (Visión P&G)
        acum_bruto = acum_neto = acum_costo = acum_fin = acum_contrib = 0.0

        for mes in range(1, self._panel.meses_contrato + 1):
            pyg = self.calcular_mes(perfiles_cadena_a, mes, costo_mes_anterior=costo_anterior)

            # Acumulados (running totals para gráficos de progreso)
            acum_bruto  += pyg.ingreso_bruto
            acum_neto   += pyg.ingreso_neto
            acum_costo  += pyg.costo_total
            acum_fin    += pyg.costos_financieros
            acum_contrib += pyg.contribucion

            pyg.acum_ingreso_bruto      = acum_bruto
            pyg.acum_ingreso_neto       = acum_neto
            pyg.acum_costo_total        = acum_costo
            pyg.acum_costos_financieros = acum_fin
            pyg.acum_contribucion       = acum_contrib

            resultados.append(pyg)
            costo_anterior = pyg.costo_total  # para el siguiente mes
        # WAVE 5 structured log — aggregate per-contract summary.
        if resultados:
            logger.info(
                "[PRICING_BUILD] op=calcular_contrato inputs={meses:%d,margen_a:%.4f,margen_b:%.4f,"
                "linea:%s} outputs={ingreso_bruto_total:%.2f,costo_total:%.2f,contribucion_total:%.2f} "
                "source=Panel+CostosTotales+CostosFinancieros",
                len(resultados), float(self._panel.margen or 0.0),
                float(getattr(self._panel, "margen_b", 0.0) or 0.0),
                getattr(self._panel, "linea_negocio", "?"),
                acum_bruto, acum_costo, acum_contrib,
            )
        return resultados

    def _mes_dentro_del_contrato(self, mes: int) -> bool:
        return 1 <= mes <= self._panel.meses_contrato
