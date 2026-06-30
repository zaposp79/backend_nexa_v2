from __future__ import annotations
"""
nexa_engine/calculators/vision_tarifas.py
==========================================
Vision Tarifas — tarifa mensual por canal y perfil operativo.

Para cada canal de Cadena A calcula los costos directos del canal filtrando
los perfiles por canal (agentes + soporte etiquetado al canal), luego deriva
el ingreso usando el denominador exacto del Excel.

Fórmula Excel exacta (Vision Tarifas_Modelo_Cobro):
  C43_ch = Payroll_ch + NoPayroll_ch + ICA_ch + GMF_ch + Pólizas_ch + CostosFinCh
  C50_ch = C43_ch / ((1-margen) × (1-op_cont))

  Los costos financieros por canal se atribuyen proporcionalmente a los costos
  operativos del canal respecto al total: fin_ch = fin_total × (op_ch / total_op)

Facturación y tarifa:
  ingreso_bruto = (op_ch + fin_ch + cadena_b_ch) / ((1-margen) × (1-op_cont))
  facturacion   = ingreso_bruto × pct_fijo
  tarifa_fte    = facturacion / fte

Descomposición por canal (VCS staffing_escenarios):
  payroll_ch     = VisionTarifasFacts.escenarios[i].nomina_por_mes[mes].total
  no_payroll_ch  = VisionTarifasFacts.escenarios[i].no_payroll_por_mes[mes].total
  costo_cadena_a = payroll_ch + no_payroll_ch
  + sub-componentes de payroll (nomina_loaded, salario_fijo, ...)
  + sub-componentes de no-payroll (opex_it, inversiones, costos_fijos)
"""


import logging
from typing import TYPE_CHECKING, List, Optional

from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator
from nexa_engine.modules.shared.precision import cop_round

_logger = logging.getLogger("nexa_engine.vision_tarifas")
from nexa_engine.modules.shared.config.business_rules.loader import get_business_rules
from nexa_engine.modules.shared.models import (
    EscenarioComercial,
    PanelDeControl,
    ParametrosCadenaB,
    PerfilCadenaA,
    PyGMensual,
    ResultadoVisionTarifas,
    TarifaCanal,
    mes_inicio_contrato,
)
from nexa_engine.modules.vision_tarifas.dto.models import (
    ComponenteFijo,
    ComponenteVariable,
    DesgloseCadenaTarifas,
    DesgloseProductoOpex,
    EscenarioTarifasDetalle,
    EscenarioTarifasResumen,
    ImproductiveBreakdown,
    ReglasBusiness,
    TarifasEscenario,
    TimeCascade,
)
if TYPE_CHECKING:
    from nexa_engine.modules.vision_tarifas.models.vt_facts import EscenarioCanalFacts




class VisionTarifasMethodsMixin2:
    """Mixin part.
"""

    def _calcular_tarifa_canal(
        self,
        perfil_agente: PerfilCadenaA,
        perfiles_canal: List[PerfilCadenaA],
        pyg_por_mes: List[PyGMensual],
        avg_costo_a: float,
        avg_fin_total: float,
        avg_costo_b: float,
        l50: float,
        factor: float,
        pct_fijo_efectivo: float,
        modelo_cobro_efectivo: str,
        nombre_canal: str,
        _esc_facts: "Optional[EscenarioCanalFacts]" = None,
    ) -> TarifaCanal:
        """
        Computa un TarifaCanal completo dado un perfil agente y parámetros de billing.
        Reutilizado tanto por la iteración de escenarios como por la de perfiles.
        """
        decomp = self._costo_op_canal_decomposed(
            perfil_agente, perfiles_canal, pyg_por_mes, avg_costo_a, _esc_facts=_esc_facts,
        )

        payroll_ch    = decomp["payroll"]
        no_payroll_ch = decomp["no_payroll"]
        op_ch = payroll_ch + no_payroll_ch

        # Costos financieros: override de Excel si disponible, si no proporcional
        if perfil_agente.costos_financieros_mensual > 0:
            fin_ch = perfil_agente.costos_financieros_mensual
        else:
            fin_ch = avg_fin_total * (op_ch / avg_costo_a) if avg_costo_a > 0 else 0.0

        # Costos Cadena B: override de Excel si disponible, si no proporcional por vol
        vol_b_display = self._vol_canal_b(perfil_agente.canal)
        if perfil_agente.cadena_b_mensual > 0:
            cadena_b_ch = perfil_agente.cadena_b_mensual
        else:
            cadena_b_ch = avg_costo_b * vol_b_display / l50 if l50 > 0 else 0.0

        costo_ch = op_ch + fin_ch + cadena_b_ch
        # F3: Delegate to pure domain calculator. ramp=1.0 because vision tarifas
        # uses averaged costs already (rampup not applied at this layer).
        from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator
        ingreso = ProfitabilityCalculator.calcular_ingreso_desde_costo(costo_ch, factor, 1.0)

        facturacion = ingreso * pct_fijo_efectivo
        tarifa_fte  = facturacion / perfil_agente.fte if perfil_agente.fte > 0 else 0.0

        pct_variable   = round(1.0 - pct_fijo_efectivo, 10)
        ingreso_var    = ingreso * pct_variable

        # Tarifa variable por transacción (ingreso variable / volumen)
        tarifa_variable = ingreso_var / vol_b_display if vol_b_display > 0 else 0.0

        # Volumen mínimo de transacción para cubrir el costo variable
        costo_variable_ch = costo_ch * pct_variable
        vol_minimo = (
            costo_variable_ch / tarifa_variable
            if tarifa_variable > 0 else 0.0
        )

        # Etiquetas de componentes según modelo de cobro efectivo
        componente_fijo, componente_variable = self._componentes_label(
            modelo_cobro_efectivo, pct_fijo_efectivo
        )

        nomina_agente = decomp.get("nomina_agente_basico", 0.0)
        costo_a_ch = payroll_ch + no_payroll_ch

        # GAP-RULES-1: Tarifas por hora loggeada y pagada.
        # Excel Hoja Maestra R21C7 = IFERROR(IF(C10="FTE", G19/C13, G19/L26), 0)
        # R23C7 = IFERROR(IF(C10="Tiempo", G19/L24, 0), 0)
        # G19 = facturacion (ingreso componente fijo)
        # L24 = FTE × horas_semanales × semanas_al_mes
        # L26 = FTE × horas_loggeadas_semanales × semanas_al_mes
        fte = perfil_agente.fte
        horas_pagadas_mes = fte * self._rules.horas_semanales * self._rules.semanas_al_mes
        horas_loggeadas_mes = fte * self._rules.horas_loggeadas_semanales * self._rules.semanas_al_mes
        tarifa_hora_pagada   = facturacion / horas_pagadas_mes   if horas_pagadas_mes   > 0 else 0.0
        tarifa_hora_loggeada = facturacion / horas_loggeadas_mes if horas_loggeadas_mes > 0 else 0.0

        return TarifaCanal(
            nombre_canal           = nombre_canal,
            modalidad              = perfil_agente.modalidad,
            producto               = perfil_agente.canal,
            fte                    = fte,
            vol_mensual            = vol_b_display,
            modelo_cobro           = modelo_cobro_efectivo,
            pct_fijo               = pct_fijo_efectivo,
            pct_variable           = pct_variable,
            componente_fijo        = componente_fijo,
            componente_variable    = componente_variable,
            costo_atribuible       = costo_ch,
            ingreso_bruto          = ingreso,
            facturacion            = facturacion,
            tarifa_fijo_fte        = tarifa_fte,
            tarifa_variable        = tarifa_variable,
            vol_minimo_transaccion = vol_minimo,
            # Decomposed costs
            payroll_ch             = payroll_ch,
            no_payroll_ch          = no_payroll_ch,
            costo_cadena_a_ch      = costo_a_ch,
            # Payroll sub-components
            nomina_loaded_ch       = decomp.get("nomina_loaded", 0.0),
            salario_fijo_ch        = decomp.get("salario_fijo", 0.0),
            salario_variable_ch    = decomp.get("salario_variable", 0.0),
            capacitacion_inicial_ch         = decomp.get("capacitacion_inicial", 0.0),
            capacitacion_rotacion_ch        = decomp.get("capacitacion_rotacion", 0.0),
            examenes_ch            = decomp.get("examenes", 0.0),
            estudios_seguridad_ch  = decomp.get("estudios_seguridad", 0.0),
            # No-payroll sub-components
            opex_it_ch             = decomp.get("opex_it", 0.0),
            inversiones_ch         = decomp.get("inversiones", 0.0),
            costos_fijos_ch        = decomp.get("costos_fijos", 0.0),
            # Attribution
            cadena_b_atribuible    = cadena_b_ch,
            financieros_atribuible = fin_ch,
            # Agent metrics
            nomina_agente_basico   = nomina_agente,
            salario_cargado_ch     = perfil_agente.salario_cargado,
            # GAP-RULES-1: Tarifas horarias
            tarifa_hora_loggeada   = tarifa_hora_loggeada,
            tarifa_hora_pagada     = tarifa_hora_pagada,
        )

    # ──────────────────────────────────────────────────────────────
    # Costo operativo por canal — with decomposition
    # ──────────────────────────────────────────────────────────────

    def _costo_op_canal_decomposed(
        self,
        perfil_agente: PerfilCadenaA,
        perfiles_canal: List[PerfilCadenaA],
        pyg_por_mes: List[PyGMensual],
        avg_costo_a_total: float,
        _esc_facts: "Optional[EscenarioCanalFacts]" = None,
    ) -> dict:
        """
        Calcula el costo operativo promedio mensual para un canal específico,
        devolviendo los sub-componentes descompuestos.

        When _esc_facts is provided, uses pre-computed Nomina/NoPayroll results
        instead of calling core calculator methods directly.

        Returns:
            dict with keys: payroll, no_payroll, nomina_loaded, salario_fijo,
            salario_variable, capacitacion_inicial, capacitacion_rotacion, examenes,
            estudios_seguridad, opex_it, inversiones, costos_fijos,
            nomina_agente_basico.
        """
        result = {
            "payroll": 0.0, "no_payroll": 0.0,
            "nomina_loaded": 0.0, "salario_fijo": 0.0, "salario_variable": 0.0,
            "capacitacion_inicial": 0.0, "capacitacion_rotacion": 0.0, "examenes": 0.0,
            "estudios_seguridad": 0.0,
            "opex_it": 0.0, "inversiones": 0.0, "costos_fijos": 0.0,
            "nomina_agente_basico": 0.0,
        }

        if _esc_facts is not None:
            meses = [m.mes for m in pyg_por_mes]
            n = len(meses)
            agent_perfiles = [p for p in perfiles_canal if not p.es_soporte]

            # Payroll from pre-computed facts (same computation as old for-mes loop)
            sf = com = cap_i = cap_r = exam = seg = total_payroll = 0.0
            for nom in _esc_facts.nomina_por_mes:
                total_payroll += nom.total
                sf    += nom.salario_fijo
                com   += nom.comisiones
                cap_i += nom.capacitacion_inicial
                cap_r += nom.capacitacion_rotacion
                exam  += nom.examenes
                seg   += nom.seguridad
            result["payroll"]              = total_payroll / n
            result["salario_fijo"]         = sf / n
            result["salario_variable"]     = com / n
            result["nomina_loaded"]        = (sf + com) / n
            result["capacitacion_inicial"] = cap_i / n
            result["capacitacion_rotacion"]= cap_r / n
            result["examenes"]             = exam / n
            result["estudios_seguridad"]   = seg / n

            # Agent nomina from pre-computed facts
            if _esc_facts.nomina_agente_por_mes:
                agent_payroll = sum(nom.total for nom in _esc_facts.nomina_agente_por_mes) / n
                result["nomina_agente_basico"] = agent_payroll

            # No-payroll: prefer override, then per-channel items, then facts.
            # inversiones_mensual / costos_fijos_mensual (Excel No payroll R186/R248) se suman
            # al override de no_payroll_mensual (OPEX Fijo, R107) para reproducir C42 Excel.
            if perfil_agente.no_payroll_mensual > 0:
                inv_men = getattr(perfil_agente, "inversiones_mensual", 0.0) or 0.0
                cf_men  = getattr(perfil_agente, "costos_fijos_mensual", 0.0) or 0.0
                result["no_payroll"] = perfil_agente.no_payroll_mensual + inv_men + cf_men
                result["opex_it"]    = perfil_agente.no_payroll_mensual
            elif _esc_facts.no_payroll_por_mes:
                # Facts-based no-payroll (same as old elif self._calc_no_payroll branch)
                opex_ti = capex = cf = total_nop = 0.0
                # Per-channel opex TI from PerfilCadenaA.opex_fijo_mensual (channel-specific items)
                ch_opex_ti = sum(
                    p.opex_fijo_mensual for p in agent_perfiles
                    if getattr(p, "opex_fijo_mensual", 0.0) > 0
                )
                has_ch_opex = ch_opex_ti > 0
                # Per-channel CAPEX items from PerfilCadenaA.inversiones_amortizables
                ch_inv_items = [
                    it for p in agent_perfiles
                    for it in getattr(p, "inversiones_amortizables", [])
                ]
                has_ch_inv = bool(ch_inv_items)
                for mes, nop in zip(meses, _esc_facts.no_payroll_por_mes):
                    # Override opex_ti with per-channel value when available
                    eff_opex = ch_opex_ti if has_ch_opex else nop.opex_ti
                    # Override capex with per-channel items when available
                    if has_ch_inv:
                        eff_capex = sum(
                            it["precio_mensual"] * it["cantidad"] * it.get("factor", 1.0)
                            for it in ch_inv_items
                            if mes <= it["meses"]
                        )
                    else:
                        eff_capex = nop.capex
                    total_nop += eff_opex + eff_capex + nop.costos_fijos
                    opex_ti   += eff_opex
                    capex     += eff_capex
                    cf        += nop.costos_fijos
                result["no_payroll"]   = total_nop / n
                result["opex_it"]      = opex_ti / n
                result["inversiones"]  = capex / n
                result["costos_fijos"] = cf / n
            else:
                # No facts and no override — FTE proportional fallback
                fte_canal = sum(p.fte for p in perfiles_canal if not p.es_soporte)
                fte_total = sum(p.fte for p in self._perfiles if not p.es_soporte)
                avg_no_payroll_total = avg_costo_a_total - result["payroll"]
                result["no_payroll"] = (
                    avg_no_payroll_total * (fte_canal / fte_total)
                    if fte_total > 0 else 0.0
                )
        else:
            # No facts available — FTE proportional fallback
            _logger.warning(
                "[VT_WARN] _costo_op_canal_decomposed llamado sin _esc_facts. "
                "Usando atribución proporcional FTE (degraded path)."
            )
            fte_canal = sum(p.fte for p in perfiles_canal if not p.es_soporte)
            fte_total = sum(p.fte for p in self._perfiles if not p.es_soporte)
            if fte_total > 0:
                total = avg_costo_a_total * (fte_canal / fte_total)
                result["payroll"] = total * 0.5  # rough split
                result["no_payroll"] = total * 0.5

        return result

    # ──────────────────────────────────────────────────────────────
    # Utilidades
    # ──────────────────────────────────────────────────────────────

    def _l50(self) -> float:
        return sum(c.volumen_mensual for c in self._canales_b)

    def _vol_canal_b(self, canal: str) -> float:
        canal_lower = canal.lower()
        return sum(
            c.volumen_mensual
            for c in self._canales_b
            if c.producto.lower() == canal_lower
        )

    @staticmethod
    def _componentes_label(modelo_cobro: str, pct_fijo: float):
        """
        Devuelve (componente_fijo_label, componente_variable_label).

        Delegates to the pure PricingCalculator in calculator.formulas.pricing.
        """
        from nexa_engine.modules.calculator_motor.formulas.pricing import PricingCalculator
        return PricingCalculator.derivar_componentes_label(modelo_cobro, pct_fijo)

    def _factor_billing(self) -> float:
        """
        Factor denominador para convertir costo total en ingreso bruto.

        Fórmula Excel V2-5/V2-7 exacta (Vision Tarifas_Modelo_Cobro + Hoja Maestra Escenarios C23):
            (1 - margen_a) × (1 - cont_op) × (1 - cont_com) × (1 - markup) × (1 + descuento)

        # EXCEL V2-7 INTENTIONAL ANOMALY (DEC #5 WAVE 0):
        # Vision Tarifas usa `margen_a` (Panel!C63) para TODOS los canales — incluido
        # el precio que se atribuye a Cadena C. Esto difiere de P&G, que sí usa
        # `margen_b`/`margen_c` por cadena (ref: calculators/pyg.py).
        # `calcular_factor_margenes(panel)` lee `panel.margen` (== margen_a) por diseño,
        # replicando literalmente Vision Tarifas!Hoja Maestra C23.
        """
        return ProfitabilityCalculator.calcular_factor_margenes(self._panel)

__all__ = ["VisionTarifasMethodsMixin"]

__all__ = ["VisionTarifasMethodsMixin2"]
