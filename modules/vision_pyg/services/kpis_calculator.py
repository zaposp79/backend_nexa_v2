"""
nexa_engine/calculators/kpis.py
=================================
Calculador de KPIs del deal — Capa 10 del pipeline.

Rol en la arquitectura
----------------------
KPIsCalculator es un SERVICIO INTERNO DE APOYO. Produce KPIsDeal, que es
consumido por otras visiones (VisionPyGBuilder, RiesgoCalculator, serializer).
KPIsDeal aparece como sección 02 de la Visión Imprimible.

RESTRICCIÓN ARQUITECTÓNICA: KPIsCalculator y KPIsDeal NO deben exponerse
como endpoint independiente ni como visión autónoma al frontend.
Las únicas visiones oficiales son:
  - Visión Imprimible (composite)
  - Vision P&G (VisionPyG)
  - Vision Tarifas_Modelo_Cobro (ResultadoVisionTarifas)
  - Vision Cost To Serve (ResultadoCostToServe)

Responsabilidad
---------------
Derivar los indicadores clave de negocio del deal a partir del P&G
mensual completo: costo promedio, tarifa mensual, facturación proyectada
y métricas de rentabilidad.

Lógica de tarifa
----------------
La tarifa mensual del deal se construye en dos pasos:
  1. Costo promedio mensual de Cadena A = Suma(costos_a) / meses_contrato
     (promedio del contrato completo para estabilizar frente a variaciones
     de ramp-up en los primeros meses)
  2. Tarifa = (costo_promedio + costos_financieros_sobre_promedio) / factor_márgenes
     donde factor_márgenes convierte el costo en precio de venta neto

Facturación proyectada
----------------------
Facturación mensual = Tarifa / factor_período_pago
Refleja el importe que el cliente paga por período según su plazo de crédito.

Consume
-------
  - PanelDeControl: márgenes, línea de negocio, período de pago
  - CostosFinancierosCalculator: costos financieros sobre el costo promedio
  - IParametrizationProvider: margen mínimo por línea, factor de período de pago

Produce
-------
  KPIsDeal — consumido internamente por visiones y serializer.
"""

from __future__ import annotations

from typing import Dict, List

from nexa_engine.modules.audit.trace import trace as _audit_trace
from nexa_engine.modules.calculator_motor.formulas.costos_financieros import CostosFinancierosCalculator
from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator
from nexa_engine.modules.shared.models import (
    KPIsDeal,
    PanelDeControl,
    PyGMensual,
)
from nexa_engine.modules.shared.ports.parametrization_provider import IParametrizationProvider


class KPIsCalculator:
    """
    Calcula los indicadores clave del deal (KPIs) a partir del P&G completo.

    Los KPIs cubren rentabilidad (utilidad neta, margen %), tarifa comercial
    (ingreso mensual, facturación proyectada) y cumplimiento del margen mínimo.
    """

    class FORMULA_ID:
        """Internal formula identifiers for traceability."""
        COSTO_MENSUAL_PROMEDIO       = "KPIS.COSTO_MENSUAL_PROMEDIO"        # costo_total_contrato / meses_contrato
        COSTO_CADENA_A_PROMEDIO      = "KPIS.COSTO_CADENA_A_PROMEDIO"       # Σ(costo_a per mes) / meses_contrato
        TARIFA_MENSUAL               = "KPIS.TARIFA_MENSUAL"                # (costo_promedio_a + costos_fin) / factor_margenes
        FACTURACION_PROYECTADA       = "KPIS.FACTURACION_PROYECTADA"        # ingreso_tarifa / factor_periodo
        FACTOR_MARGENES              = "KPIS.FACTOR_MARGENES"               # calcular_factor_margenes(panel)
        FACTOR_PERIODO               = "KPIS.FACTOR_PERIODO"                # calcular_factor_periodo(panel, parametrizacion)
        COSTOS_FIN_SOBRE_PROMEDIO    = "KPIS.COSTOS_FIN_SOBRE_PROMEDIO"     # CostosFinancierosCalculator.calcular(costo_promedio_a)
        INGRESO_BRUTO_TOTAL          = "KPIS.INGRESO_BRUTO_TOTAL"           # Σ ingreso_bruto per mes
        INGRESO_NETO_TOTAL           = "KPIS.INGRESO_NETO_TOTAL"            # Σ ingreso_neto per mes
        COSTO_TOTAL_CONTRATO         = "KPIS.COSTO_TOTAL_CONTRATO"          # Σ costo_total per mes
        CONTRIBUCION_TOTAL           = "KPIS.CONTRIBUCION_TOTAL"            # Σ contribucion per mes
        UTILIDAD_NETA_TOTAL          = "KPIS.UTILIDAD_NETA_TOTAL"           # Σ utilidad_neta per mes
        PCT_UTILIDAD_NETA            = "KPIS.PCT_UTILIDAD_NETA"             # utilidad_neta_total / ingreso_neto_total
        MARGEN_MINIMO_REQUERIDO      = "KPIS.MARGEN_MINIMO_REQUERIDO"       # parametrizacion.get_margen_minimo(linea_negocio)
        CUMPLE_MARGEN_MINIMO         = "KPIS.CUMPLE_MARGEN_MINIMO"          # panel.margen >= margen_minimo

    def __init__(
        self,
        panel: PanelDeControl,
        calculador_financiero: CostosFinancierosCalculator,
        parametrizacion: IParametrizationProvider,
    ) -> None:
        self._panel                 = panel
        self._calculador_financiero = calculador_financiero
        self._parametrizacion       = parametrizacion

    def calcular(self, pyg_contrato: List[PyGMensual]) -> KPIsDeal:
        """
        Calcula todos los KPIs del deal a partir del P&G mensual completo.

        Args:
            pyg_contrato: Lista de PyGMensual (uno por mes del contrato).

        Returns:
            KPIsDeal con métricas de rentabilidad, tarifa y cumplimiento.
        """
        totales         = self._sumar_totales(pyg_contrato)
        datos_tarifa    = self._calcular_tarifa(pyg_contrato)
        margen_minimo   = self._parametrizacion.get_margen_minimo(self._panel.linea_negocio)
        meses           = self._panel.meses_contrato
        costo_mensual_prom = totales["costo_total"] / meses if meses else 0.0

        _audit_trace(
            component   = "kpis",
            rule        = "KPIS.tarifa + facturacion + rentabilidad",
            formula     = (
                "costo_mensual_promedio = costo_total_contrato / meses_contrato; "
                "ingreso_mensual = (costo_promedio_a + costos_financieros_sobre_promedio) / factor_margenes; "
                "facturacion_mensual = ingreso_mensual / factor_periodo; "
                "pct_utilidad = utilidad_neta / ingreso_neto"
            ),
            inputs      = {
                "costo_total_contrato": totales["costo_total"],
                "meses_contrato":       meses,
                "ingreso_neto_total":   totales["ingreso_neto"],
                "utilidad_neta_total":  totales["utilidad_neta"],
                "margen_minimo":        margen_minimo,
                "margen_deal":          self._panel.margen,
            },
            intermediate = {
                "costo_mensual_promedio":    costo_mensual_prom,
                "costo_cadena_a_promedio":   datos_tarifa["costo_promedio_a"],
                "ingreso_mensual_tarifa":    datos_tarifa["ingreso_mensual_tarifa"],
                "facturacion_mensual":       datos_tarifa["facturacion_mensual"],
                "pct_utilidad":              self._pct_utilidad(totales),
            },
            result      = datos_tarifa["ingreso_mensual_tarifa"],
            source      = "PyG-Contrato (P&G mensual), OP-Config (margen_minimo, factor_periodo)",
            mes         = 0,  # KPIs son del contrato completo, no por mes
            notes       = f"cumple_margen_minimo={self._panel.margen >= margen_minimo}",
            formula_ids = [
                self.FORMULA_ID.COSTO_MENSUAL_PROMEDIO,
                self.FORMULA_ID.COSTO_CADENA_A_PROMEDIO,
                self.FORMULA_ID.TARIFA_MENSUAL,
                self.FORMULA_ID.FACTURACION_PROYECTADA,
                self.FORMULA_ID.FACTOR_MARGENES,
                self.FORMULA_ID.FACTOR_PERIODO,
                self.FORMULA_ID.COSTOS_FIN_SOBRE_PROMEDIO,
                self.FORMULA_ID.INGRESO_BRUTO_TOTAL,
                self.FORMULA_ID.INGRESO_NETO_TOTAL,
                self.FORMULA_ID.COSTO_TOTAL_CONTRATO,
                self.FORMULA_ID.CONTRIBUCION_TOTAL,
                self.FORMULA_ID.UTILIDAD_NETA_TOTAL,
                self.FORMULA_ID.PCT_UTILIDAD_NETA,
                self.FORMULA_ID.MARGEN_MINIMO_REQUERIDO,
                self.FORMULA_ID.CUMPLE_MARGEN_MINIMO,
            ],
        )

        return KPIsDeal(
            costo_mensual_promedio         = costo_mensual_prom,
            costo_cadena_a_promedio        = datos_tarifa["costo_promedio_a"],
            ingreso_mensual                = datos_tarifa["ingreso_mensual_tarifa"],
            facturacion_mensual_proyectada = datos_tarifa["facturacion_mensual"],
            ingreso_bruto_total            = totales["ingreso_bruto"],
            ingreso_neto_total             = totales["ingreso_neto"],
            costo_total_contrato           = totales["costo_total"],
            contribucion_total             = totales["contribucion"],
            utilidad_neta_total            = totales["utilidad_neta"],
            pct_utilidad_neta_total        = self._pct_utilidad(totales),
            valor_total_deal               = totales["ingreso_neto"],
            margen_minimo_requerido        = margen_minimo,
            cumple_margen_minimo           = self._panel.margen >= margen_minimo,
        )

    # ──────────────────────────────────────────────────────────────
    # Cálculos internos
    # ──────────────────────────────────────────────────────────────

    def _sumar_totales(self, pyg_contrato: List[PyGMensual]) -> Dict[str, float]:
        """Agrega los totales del contrato sumando todos los meses del P&G."""
        return {
            "ingreso_bruto": sum(m.ingreso_bruto  for m in pyg_contrato),
            "ingreso_neto":  sum(m.ingreso_neto   for m in pyg_contrato),
            "costo_total":   sum(m.costo_total    for m in pyg_contrato),
            "contribucion":  sum(m.contribucion   for m in pyg_contrato),
            "utilidad_neta": sum(m.utilidad_neta  for m in pyg_contrato),
        }

    def _pct_utilidad(self, totales: Dict[str, float]) -> float:
        """Porcentaje de utilidad neta sobre ingreso neto total."""
        return (totales["utilidad_neta"] / totales["ingreso_neto"]
                if totales["ingreso_neto"] else 0.0)

    def _calcular_tarifa(self, pyg_contrato: List[PyGMensual]) -> Dict[str, float]:
        """
        Calcula la tarifa mensual y la facturación proyectada del deal.

        La tarifa se basa en el costo promedio mensual de Cadena A durante todo
        el contrato, para suavizar el efecto del ramp-up de los primeros meses.
        """
        n = self._panel.meses_contrato
        costo_promedio_a = (
            sum(m.costo_a for m in pyg_contrato) / n if pyg_contrato else 0.0
        )

        costos_fin_sobre_promedio = self._calculador_financiero.calcular(costo_promedio_a, mes=1)
        factor_margenes           = ProfitabilityCalculator.calcular_factor_margenes(self._panel)

        if factor_margenes == 0:
            ingreso_tarifa = 0.0
        else:
            ingreso_tarifa = (
                (costo_promedio_a + costos_fin_sobre_promedio.total) / factor_margenes
            )

        factor_periodo = self._parametrizacion.get_factor_periodo(self._panel.periodo_pago_dias)
        facturacion    = ingreso_tarifa / factor_periodo if factor_periodo else ingreso_tarifa

        return {
            "costo_promedio_a":       costo_promedio_a,
            "ingreso_mensual_tarifa": ingreso_tarifa,
            "facturacion_mensual":    facturacion,
        }
