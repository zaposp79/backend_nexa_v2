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
    from nexa_engine.modules.vision_tarifas.models.vt_facts import CanalExtensionFacts




class VisionTarifasMethodsMixin1:
    """Mixin part.
"""

    def _simular_financiero_canal(
        self,
        perfiles_ch: "List[PerfilCadenaA]",
        n: int,
        pol_cfg_fin: "List[tuple]",
        fm_a: float,
        start_idx: int,
    ) -> "tuple[float, float, float]":
        """Computes (c43, c44, c45) for a specific channel profile set.

        Runs the same extension-polizas formula as the main calcular() path,
        but parameterised on the given channel's profiles. This allows per-channel
        attribution in the hierarchical desglose without re-using the deal-wide
        esc_canal values for every escenario.

        Uses pre-computed extension facts from self._vt_facts (no core calculator calls).

        Args:
            perfiles_ch:  Agent+soporte profiles for this channel.
            n:            Number of contract months.
            pol_cfg_fin:  List of (tasa_efectiva, meses_extension) for deal-wide polizas.
            fm_a:         Factor margenes Cadena A.
            start_idx:    Calendar month of contract start (1-12).

        Returns:
            (c43_ch, c44_ch, c45_ch) — annual totals for ICA, GMF, pólizas puras.
            NOT certified against Excel for channels other than esc_canal.
        """
        if not perfiles_ch or not pol_cfg_fin or fm_a <= 0:
            return 0.0, 0.0, 0.0

        canal = (perfiles_ch[0].canal or "").lower() if perfiles_ch else None

        # Use pre-computed extension facts if available
        ext_facts = (
            self._vt_facts.canales_extension.get(canal)
            if self._vt_facts is not None and canal
            else None
        )
        if ext_facts is None:
            return 0.0, 0.0, 0.0

        # Build per-month costs for this channel from facts (no core calculator calls)
        ch_months = [
            nom.total + nop.opex_ti + nop.capex + nop.costos_fijos
            for nom, nop in zip(ext_facts.nomina_por_mes, ext_facts.no_payroll_por_mes)
        ]

        # Extension base for this channel from last-month facts
        ch_agente = [p for p in perfiles_ch if not p.es_soporte]
        nom_last = ext_facts.nomina_ultimo_mes
        nop_last = ext_facts.no_payroll_ultimo_mes
        recurrent_inv_ch = sum(
            getattr(p, "inversiones_mensual_recurrente", 0.0) or 0.0
            for p in ch_agente
        )
        if recurrent_inv_ch > 0:
            inv_avg_ch = sum(getattr(p, "inversiones_mensual", 0.0) or 0.0 for p in ch_agente)
            if inv_avg_ch == 0.0:
                recurrent_inv_ch = 0.0  # F4 normalization: no override mode → ignore inv_rec
        ch_last = (
            nom_last.total + nop_last.opex_ti + recurrent_inv_ch + nop_last.costos_fijos
            if recurrent_inv_ch > 0
            else (ch_months[-1] if ch_months else 0.0)
        )

        umbral   = n + start_idx
        max_dur  = max((dur for _, dur in pol_cfg_fin), default=0)

        c43 = c44 = c45 = 0.0
        for idx in range(1, max(umbral + max_dur, umbral + 1)):
            cp = idx - start_idx
            if 0 <= cp < n:
                base = ch_months[cp]
            elif idx >= umbral:
                base = ch_last
            else:
                base = 0.0
            tasa_m = sum(te for te, dur in pol_cfg_fin if dur >= idx)
            pol_m  = tasa_m * base / fm_a if fm_a > 0 else 0.0
            if pol_m > 0:
                c45 += pol_m
                if 0 <= cp < n and base > 0:
                    c43 += (base / fm_a + pol_m) * self._panel.tasa_ica
                    c44 += (base + pol_m) * self._panel.tasa_gmf

        return c43, c44, c45

    # ──────────────────────────────────────────────────────────────
    # Hierarchical Vision Tarifas Extraction (Excel Reverse-Engineering)
    # ──────────────────────────────────────────────────────────────

    def _extraer_reglas_business(self) -> ReglasBusiness:
        """
        Extrae reglas de negocio del panel — Excel rows 29-37.

        Exact cell mapping:
          G30 = Panel!C67 = panel.op_cont   (Contingencia Operativa)
          G31 = Panel!C68 = panel.com_cont  (Contingencia Comercial)
          G32 = Panel!C69 = panel.markup    (Mark up)
          G33 = Panel!C70 = panel.descuento (Descuento volumen)
          G35 = Panel!C63 = panel.margen    (Margen Cadena A — base margin only, no contingencies)
          G36 = Panel!D63 = panel.margen_b  (Margen Cadena B)
          G37 = Panel!E63 = panel.margen_c  (Margen Cadena C)

        NOTE: G35/G36/G37 in Excel are the RAW margins from Panel (C63/D63/E63).
        They are NOT sum of G29+G35. The G29 total is separate and is only for display.
        """
        return ReglasBusiness(
            cont_operativa=self._panel.op_cont,
            cont_comercial=self._panel.com_cont,
            markup=self._panel.markup,
            descuento_volumen=self._panel.descuento,
            margen_cadena_a=self._panel.margen,
            margen_cadena_b=self._panel.margen_b,
            margen_cadena_c=self._panel.margen_c,
        )

    def _desglose_cadena_por_escenario(
        self,
        escenario: "EscenarioComercial",
        perfiles_canal: List[PerfilCadenaA],
        tarifa_canal: TarifaCanal,
        pyg_por_mes: List[PyGMensual],
        avg_costo_a: float,
        avg_fin_total: float,
        avg_costo_b: float,
        l50: float,
        factor: float,
        fin_sim: "tuple[float,float,float] | None" = None,
    ) -> tuple:
        """
        Construye desglose de costos por cadena para un escenario.

        Cadena A formula (Excel C40-C47):
          C41 = Payroll (from TarifaCanal.payroll_ch × n)
          C42 = No Payroll (from TarifaCanal.no_payroll_ch × n)
          C43 = ICA   — from fin_sim[0] when deal-wide polizas active; else PyG avg × n
          C44 = GMF   — from fin_sim[1]; else PyG avg × n
          C45 = Pólizas — from fin_sim[2]; else PyG avg × n
          C46 = Costos financiación (financiacion component of PyG, proportional)
          C40 = SUM(C41:C46)     → stored as total_costo (annual)
          C47 = C40 / factor     → stored as ingreso_bruto (annual)

        When fin_sim is provided (has_deal_wide_polizas path), C43/C44/C45 use the
        per-canal certified formula values and total_costo/ingreso_bruto are ANNUAL.
        When fin_sim is None (fallback path), legacy monthly averages are used and
        total_costo/ingreso_bruto remain MONTHLY averages for backward compatibility.

        Cadena B formula (Excel C50-C57):
          C51 = Cadena B - Componente Fijo (from cadena_b_atribuible per channel)
          C52 = Cadena B - Componente Variable
          C53 = ICA_b = avg(ica - ica_a - ica_c)
          C54 = GMF_b = avg(gmf - gmf_a - gmf_c)
          C55 = Polizas_b = avg(m.polizas_b)
          C50 = SUM(C51:C56)
          C57 = C50 / ((1-G36)*(1-G30)*(1-G31)*(1-G32)*(1+G33))

        Cadena C formula (Excel C60-C67):
          C61 = Cadena C costs (costo_c_fin per PyGMensual)
          C63 = ICA_c = avg(m.ica_c)
          C64 = GMF_c = avg(m.gmf_c)
          C60 = SUM(C61:C66)
          C67 = C60 / ((1-G35)*(1-G30)*(1-G31)*(1-G32)*(1+G33))  [uses G35, not G37 — intentional Excel anomaly]
        """
        from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator

        n = len(pyg_por_mes)

        # ── Cadena A ──────────────────────────────────────────────
        payroll_ch    = tarifa_canal.payroll_ch
        no_payroll_ch = tarifa_canal.no_payroll_ch

        if fin_sim is not None:
            # Deal-wide polizas path: use per-canal certified values (annual totals).
            # C43, C44, C45 come from the extension formula, not from PyG averages.
            ica_a, gmf_a, pol_a = fin_sim

            # C46: only the financiacion component (excludes ICA/GMF already in fin_sim).
            avg_financiacion = sum(m.financiacion for m in pyg_por_mes) / n if n else 0.0
            op_ch = payroll_ch + no_payroll_ch
            financiacion_annual = (
                avg_financiacion * (op_ch / avg_costo_a) * n
                if avg_costo_a > 0 else 0.0
            )

            # Annual totals — consistent with C40/C47 being contract-wide values.
            total_a   = payroll_ch * n + no_payroll_ch * n + ica_a + gmf_a + pol_a + financiacion_annual
            ingreso_a = ProfitabilityCalculator.calcular_ingreso_desde_costo(total_a, factor, 1.0)

            cadena_a = DesgloseCadenaTarifas(
                payroll               = payroll_ch * n,     # annual
                no_payroll            = no_payroll_ch * n,  # annual
                ica                   = ica_a,               # annual, from certified formula
                gmf                   = gmf_a,               # annual
                polizas               = pol_a,               # annual
                aplica_polizas        = pol_a > 0 or bool(self._polizas_usuario),
                costos_financiacion   = financiacion_annual, # annual, financing only
                total_costo           = total_a,             # annual (= C40 for esc_canal)
                ingreso_bruto         = ingreso_a,           # annual (= C47 for esc_canal)
            )
        else:
            # Fallback path: legacy monthly averages from PyG (backward compatible).
            fin_ch = tarifa_canal.financieros_atribuible
            ica_a  = sum(m.ica_a     for m in pyg_por_mes) / n if n else 0.0
            gmf_a  = sum(m.gmf_a     for m in pyg_por_mes) / n if n else 0.0
            pol_a  = sum(m.polizas_a for m in pyg_por_mes) / n if n else 0.0

            total_a   = payroll_ch + no_payroll_ch + ica_a + gmf_a + pol_a + fin_ch
            ingreso_a = ProfitabilityCalculator.calcular_ingreso_desde_costo(total_a, factor, 1.0)

            cadena_a = DesgloseCadenaTarifas(
                payroll             = payroll_ch,
                no_payroll          = no_payroll_ch,
                ica                 = ica_a,
                gmf                 = gmf_a,
                polizas             = pol_a,
                aplica_polizas      = pol_a > 0 or bool(self._polizas_usuario),
                costos_financiacion = fin_ch,
                total_costo         = total_a,
                ingreso_bruto       = ingreso_a,
            )

        # ── Cadena B ──────────────────────────────────────────────
        # costo_b from TarifaCanal already attributed per channel
        costo_b_ch = tarifa_canal.cadena_b_atribuible
        # ica_b = total_ica - ica_a - ica_c (derived; no direct PyG field)
        ica_b = sum(m.ica - m.ica_a - m.ica_c for m in pyg_por_mes) / n if n else 0.0
        gmf_b = sum(m.gmf - m.gmf_a - m.gmf_c for m in pyg_por_mes) / n if n else 0.0
        pol_b = sum(m.polizas_b for m in pyg_por_mes) / n if n else 0.0

        total_b = costo_b_ch + ica_b + gmf_b + pol_b
        ingreso_b = ProfitabilityCalculator.calcular_ingreso_desde_costo(total_b, factor, 1.0)

        cadena_b = DesgloseCadenaTarifas(
            componente_fijo=costo_b_ch,
            componente_variable=0.0,
            ica=ica_b,
            gmf=gmf_b,
            polizas=pol_b,
            aplica_polizas=pol_b > 0,
            total_costo=total_b,
            ingreso_bruto=ingreso_b,
        )

        # ── Cadena C ──────────────────────────────────────────────
        # costo_c_fin = full Cadena C cost basis for tarifa (Excel C60 derivation)
        costo_c = sum(m.costo_c_fin for m in pyg_por_mes) / n if n else 0.0
        ica_c = sum(m.ica_c for m in pyg_por_mes) / n if n else 0.0
        gmf_c = sum(m.gmf_c for m in pyg_por_mes) / n if n else 0.0
        pol_c = sum(m.polizas_c for m in pyg_por_mes) / n if n else 0.0

        total_c = costo_c + ica_c + gmf_c + pol_c
        ingreso_c = ProfitabilityCalculator.calcular_ingreso_desde_costo(total_c, factor, 1.0)

        cadena_c = DesgloseCadenaTarifas(
            componente_fijo=costo_c,
            componente_variable=0.0,
            ica=ica_c,
            gmf=gmf_c,
            polizas=pol_c,
            aplica_polizas=pol_c > 0,
            total_costo=total_c,
            ingreso_bruto=ingreso_c,
        )

        return cadena_a, cadena_b, cadena_c

    def _construir_componente_fijo(
        self,
        escenario: "EscenarioComercial",
        perfil_agente: Optional[PerfilCadenaA],
    ) -> ComponenteFijo:
        """
        Builds ComponenteFijo detail — Excel rows 104-127.

        Activation: IF(C34="Tiempo","✓ Habilitado","— Deshabilitado")
          → habilitado when escenario.componente_fijo_tipo == "Tiempo"

        Time cascade formulas (rows 121-127):
          C121 = C107 * C109 * C37        (scheduled hours = weekly_h * weeks * fte)
          D124 = C121 * (1 - C124)        (paid hours; C124=0 in Excel → D124 = C121)
          D125 = D124 * (1 - Panel!C19)   (worked hours after absenteeism)
          C126 = SUM(D113:D115)           (improductive pct 1: breaks+training+deslogueos)
          D126 = D125 * (1 - C126)        (logged hours)
          C127 = SUM(D116:D117)           (improductive pct 2: coaching+pausa_activa)
          D127 = D126 * (1 - C127)        (productive hours)

        Improductive breakdown (rows 113-118):
          C113 = 30 min (2 breaks × 15 min)
          C114 = (horas_formacion_mensual/4/6)*60 (training min/day)
          C115 = 5 (deslogueos)
          C116 = 5 (coaching)
          C117 = 5 (pausa activa)
          D_n  = C_n / ((C107/6)*60)     (each as % of daily minutes)
        """
        habilitado = (escenario.componente_fijo_tipo == "Tiempo")
        if not habilitado or perfil_agente is None:
            return ComponenteFijo(habilitado=False)

        fte = perfil_agente.fte
        horas_semana = float(self._rules.horas_semanales)
        semanas_mes = float(self._rules.semanas_al_mes)
        horas_form_mensual = float(self._panel.horas_formacion_mensual or 8)
        pct_ausentismo = self._panel.pct_ausentismo

        # Daily productive minutes denominator: (weekly_hours / 6 days) * 60
        minutos_dia = (horas_semana / 6.0) * 60.0

        # Improductive breakdown per Excel rows 113-117
        breaks_min = 30.0
        training_min = (horas_form_mensual / 4.0 / 6.0) * 60.0
        deslogueos_min = 5.0
        coaching_min = 5.0
        pausa_min = 5.0

        breaks_pct = breaks_min / minutos_dia
        training_pct = training_min / minutos_dia
        deslogueos_pct = deslogueos_min / minutos_dia
        coaching_pct = coaching_min / minutos_dia
        pausa_pct = pausa_min / minutos_dia

        total_imp_min = breaks_min + training_min + deslogueos_min + coaching_min + pausa_min
        total_imp_pct = total_imp_min / minutos_dia

        # Level 1 improductive: breaks + training + deslogueos (affects logged hours)
        pct_nivel1 = breaks_pct + training_pct + deslogueos_pct
        # Level 2 improductive: coaching + pausa_activa (affects productive hours)
        pct_nivel2 = coaching_pct + pausa_pct

        # Time cascade
        scheduled = horas_semana * semanas_mes * fte        # C121
        paid = scheduled                                     # D124 = C121 (C124=0 in Excel)
        worked = paid * (1.0 - pct_ausentismo)               # D125
        logged = worked * (1.0 - pct_nivel1)                 # D126
        productive = logged * (1.0 - pct_nivel2)             # D127

        return ComponenteFijo(
            habilitado=True,
            horas_semana=horas_semana,
            horas_entrenamiento_mes=horas_form_mensual,
            semanas_mes=semanas_mes,
            improductive_breakdown=ImproductiveBreakdown(
                breaks_minutos=breaks_min,
                breaks_pct=breaks_pct,
                training_minutos=training_min,
                training_pct=training_pct,
                deslogueos_minutos=deslogueos_min,
                deslogueos_pct=deslogueos_pct,
                coaching_minutos=coaching_min,
                coaching_pct=coaching_pct,
                pausa_activa_minutos=pausa_min,
                pausa_activa_pct=pausa_pct,
                total_improductive_minutos=total_imp_min,
                total_improductive_pct=total_imp_pct,
            ),
            time_cascade=TimeCascade(
                scheduled_hours=scheduled,
                paid_hours=paid,
                worked_hours=worked,
                logged_hours=logged,
                productive_hours=productive,
            ),
        )

    def _construir_componente_variable(
        self,
        escenario: "EscenarioComercial",
    ) -> ComponenteVariable:
        """
        Builds ComponenteVariable detail — Excel rows 130-143.

        Activation: IF(OR(C35="Honorarios",C35="Resultados"),"✓ Habilitado","— Deshabilitado")
          → habilitado when componente_variable_tipo in ["Honorarios", "Resultados"]

        When habilitado, Excel computes:
          C133 = IF(Panel!C5="SACO", Panel!C124, IF(Panel!C5="Cobranzas", Panel!C155, 0))
          Commission table (rows 136-143): monthly values with difficulty drivers.

        Commission calculation requires service-specific inputs (SACO, Cobranzas) not
        currently available in the generic PanelDeControl model.
        UNDETERMINED — requires workbook validation for specific service types.
        """
        tipo = escenario.componente_variable_tipo or ""
        habilitado = tipo in ("Honorarios", "Resultados")
        return ComponenteVariable(habilitado=habilitado, cant_asesores=0, meses_comisiones=[])

    def _desglose_opex_por_producto(
        self,
        pyg_por_mes: List[PyGMensual],
    ) -> List[DesgloseProductoOpex]:
        """
        Product-level OPEX breakdown — Excel rows 91-98.

        costo_directo — IMPLEMENTED from CanalCadenaB per product:
            Σ(tarifa_unitaria × volumen_mensual + opex_fijo + vol × pct_esc × costo_esc)
            Matches CadenaBCalculator's per-channel cost components
            (costo_variable + opex_fijo + escalamiento) attributed to each product via
            CanalCadenaB.producto. Equivalent to Excel SUMPRODUCT rows 229-243 / Panel!C11
            since volumen_mensual is already a monthly figure.

        costo_financiacion — UNDETERMINED.
            Excel rows 253-267 map to per-channel financing/CAPEX costs.
            In the domain model, ParametrosCadenaB.inversion_mensual is a single aggregate
            not tagged per product. Fix: add inversion_mensual to CanalCadenaB.

        polizas — UNDETERMINED.
            Excel rows 275-334 map to per-channel policy costs.
            PyGMensual.polizas_b is a single aggregate not tagged per product.
            Fix: add tasa_polizas or poliza_mensual to CanalCadenaB.

        S&M and HITL costs (costo_personal_sm, opex_herramientas_sm, costo_personal_hitl,
        opex_herramientas_hitl) are shared-platform aggregates and cannot be attributed
        per product without a product-allocation key.
        """
        productos = sorted({c.producto for c in self._canales_b if c.producto})
        result = []
        for prod in productos:
            canales = [c for c in self._canales_b if c.producto == prod]
            costo_directo = sum(
                cop_round(c.tarifa_unitaria * c.volumen_mensual)
                + c.opex_fijo
                + cop_round(c.volumen_mensual * c.pct_escalamiento * c.costo_escalamiento)
                for c in canales
            )
            result.append(DesgloseProductoOpex(
                producto=prod,
                costo_directo=costo_directo,
                costo_financiacion=None,    # NOT ATTRIBUTABLE — inversion_mensual is platform aggregate
                polizas=None,              # NOT ATTRIBUTABLE — polizas_b is cadena aggregate
                ingreso_producto=costo_directo,  # Partial: financiacion + polizas not attributable
            ))
        return result

    # ──────────────────────────────────────────────────────────────
    # Helper: construir TarifaCanal para un perfil/escenario dado
    # ──────────────────────────────────────────────────────────────


__all__ = ["VisionTarifasMethodsMixin1"]
