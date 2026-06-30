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
from typing import List, Optional

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
from nexa_engine.modules.vision_tarifas.models.vt_facts import VisionTarifasFacts

from nexa_engine.modules.calculator_motor.formulas.tarifas.mixins.reglas_methods import (
    VisionTarifasMethodsMixin,
)


class VisionTarifasCalculator(VisionTarifasMethodsMixin):
    """
    Calcula ResultadoVisionTarifas por escenario.

    Private calculation methods in VisionTarifasMethodsMixin (FASE Z.4.3b).
    """

    class FORMULA_ID:
        """Trazabilidad de fórmulas de Vision Tarifas — Capa 10."""
        TARIFA_FTE = "VISION_TARIFAS.TARIFA_FTE"
        TARIFA_HORA_PAGADA = "VISION_TARIFAS.TARIFA_HORA_PAGADA"
        TARIFA_HORA_LOGGEADA = "VISION_TARIFAS.TARIFA_HORA_LOGGEADA"
        TARIFA_TRANSACCION = "VISION_TARIFAS.TARIFA_TRANSACCION"
        COMPONENTE_FIJO = "VISION_TARIFAS.COMPONENTE_FIJO"
        COMPONENTE_VARIABLE = "VISION_TARIFAS.COMPONENTE_VARIABLE"
        COSTO_CANAL = "VISION_TARIFAS.COSTO_CANAL"
        DESGLOSE_OPEX = "VISION_TARIFAS.DESGLOSE_OPEX"
        DESGLOSE_CAPEX = "VISION_TARIFAS.DESGLOSE_CAPEX"
        FACTOR_BILLING = "VISION_TARIFAS.FACTOR_BILLING"
        FACTOR_MARGENES = "VISION_TARIFAS.FACTOR_MARGENES"
        COSTOS_FINANCIEROS = "VISION_TARIFAS.COSTOS_FINANCIEROS"
        ESCENARIO_COMERCIAL = "VISION_TARIFAS.ESCENARIO_COMERCIAL"

    def __init__(
        self,
        perfiles_cadena_a: List[PerfilCadenaA],
        parametros_cadena_b: ParametrosCadenaB,
        panel: PanelDeControl,
        vt_facts: Optional[VisionTarifasFacts] = None,
        escenarios: Optional[List[EscenarioComercial]] = None,
        strict_mode: bool = False,
        polizas_usuario: Optional[List] = None,
        calc_financiero: "Optional[object]" = None,
    ) -> None:
        self._perfiles        = perfiles_cadena_a
        self._canales_b       = parametros_cadena_b.canales
        self._panel           = panel
        self._vt_facts        = vt_facts
        self._polizas_usuario = polizas_usuario
        self._calc_financiero = calc_financiero
        # GAP-PCG-1: Escenarios comerciales del Panel!A81:D113.
        # Cuando no vacía, se itera cada escenario independientemente (NO lookup único por canal).
        # Excel VT R37 = SUMIFS(CA!FTE, modalidad=escenario.modal, canal=escenario.canal).
        # Múltiples escenarios pueden compartir canal/modalidad → cada uno genera TarifaCanal propio.
        self._escenarios: List[EscenarioComercial] = escenarios or []
        # GAP-RULES-1: constantes operativas para tarifa por hora loggeada/pagada.
        self._rules = get_business_rules()
        # FASE 4: Strict Excel Mode — raise StrictExcelModeError instead of silently skipping.
        self._strict_mode = strict_mode

    def calcular(self, pyg_por_mes: List[PyGMensual]) -> ResultadoVisionTarifas:
        n = len(pyg_por_mes)
        if n == 0:
            return ResultadoVisionTarifas()

        factor = self._factor_billing()
        l50    = self._l50()

        # BUG-2 FIX: Costos financieros promedio del deal (para atribución proporcional).
        # Excel Hoja Maestra C40 = ICA + GMF + Pólizas + Financiación únicamente.
        # Comisión de Administración (Panel!C45) NO forma parte de la tarifa base (C40),
        # se excluye de la atribución proporcional por canal (confirmado Excel V2-5).
        avg_fin_total = sum(
            m.ica + m.gmf + m.polizas + m.financiacion
            for m in pyg_por_mes
        ) / n
        avg_costo_a   = sum(m.costo_a            for m in pyg_por_mes) / n
        avg_costo_b   = sum(m.costo_b            for m in pyg_por_mes) / n

        canales: List[TarifaCanal] = []
        total_cad_a = 0.0

        # GAP-PCG-1: Cuando hay escenarios, iterar sobre ellos independientemente.
        # Cada escenario define un canal con su propio modelo de cobro y pct_fijo.
        # SUMIFS de Cadena A por (modalidad, canal) del escenario → FTE y costos.
        # Múltiples escenarios para el mismo canal producen TarifaCanal distintos.
        # Si no hay escenarios → backward compat: un TarifaCanal por perfil agente.
        if self._escenarios:
            _logger.info(
                "[VT_TRACE] calcular: escenarios=%d perfiles_total=%d perfiles_agente=%d",
                len(self._escenarios),
                len(self._perfiles),
                len([p for p in self._perfiles if not p.es_soporte]),
            )
            _logger.info(
                "[VT_TRACE] available_perfiles=%s",
                [(p.canal, p.modalidad, p.es_soporte, p.fte) for p in self._perfiles if not p.es_soporte],
            )
            _facts_idx = 0
            for escenario in self._escenarios:
                # Perfiles de Cadena A que coinciden con canal + modalidad del escenario.
                # Soporte (es_soporte=True) tiene modalidad="Staff"; se incluye por canal
                # porque Excel NL!C68 = SUM(R43:R66) agrupa agente+soporte del mismo canal.
                perfiles_canal = [
                    p for p in self._perfiles
                    if p.canal.lower() == escenario.canal.lower()
                    and (p.modalidad.lower() == escenario.modalidad.lower() or p.es_soporte)
                ]
                agent_perfiles = [p for p in perfiles_canal if not p.es_soporte]
                _logger.info(
                    "[VT_TRACE] escenario=%d canal=%r modalidad=%r matched_perfiles=%d agent_perfiles=%d",
                    escenario.escenario, escenario.canal, escenario.modalidad,
                    len(perfiles_canal), len(agent_perfiles),
                )
                if not agent_perfiles:
                    if self._strict_mode:
                        from nexa_engine.modules.shared.exceptions import StrictExcelModeError
                        raise StrictExcelModeError(
                            f"Escenario {escenario.escenario}: no se encontró perfil agente "
                            f"para canal='{escenario.canal}', modalidad='{escenario.modalidad}'",
                            component="VisionTarifasCalculator",
                            detail=f"escenario={escenario.escenario}",
                        )
                    continue
                perfil_agente = agent_perfiles[0]

                _esc_facts = (
                    self._vt_facts.escenarios[_facts_idx]
                    if self._vt_facts is not None and _facts_idx < len(self._vt_facts.escenarios)
                    else None
                )
                _facts_idx += 1

                tarifa_canal = self._calcular_tarifa_canal(
                    perfil_agente=perfil_agente,
                    perfiles_canal=perfiles_canal,
                    pyg_por_mes=pyg_por_mes,
                    avg_costo_a=avg_costo_a,
                    avg_fin_total=avg_fin_total,
                    avg_costo_b=avg_costo_b,
                    l50=l50,
                    factor=factor,
                    pct_fijo_efectivo=escenario.componente_fijo_pct,
                    modelo_cobro_efectivo=escenario.modelo_cobro,
                    nombre_canal=f"Escenario {escenario.escenario} – {perfil_agente.nombre}",
                    _esc_facts=_esc_facts,
                )
                total_cad_a += tarifa_canal.costo_cadena_a_ch
                canales.append(tarifa_canal)
        else:
            # Backward compat: un TarifaCanal por perfil agente (no-soporte)
            for perfil in self._perfiles:
                if perfil.es_soporte:
                    continue

                perfiles_canal = [p for p in self._perfiles if p.canal == perfil.canal]

                # Look up pre-computed facts by canal (canales_direct)
                _direct_facts = (
                    self._vt_facts.canales_direct.get(perfil.canal or "")
                    if self._vt_facts is not None
                    else None
                )

                tarifa_canal = self._calcular_tarifa_canal(
                    perfil_agente=perfil,
                    perfiles_canal=perfiles_canal,
                    pyg_por_mes=pyg_por_mes,
                    avg_costo_a=avg_costo_a,
                    avg_fin_total=avg_fin_total,
                    avg_costo_b=avg_costo_b,
                    l50=l50,
                    factor=factor,
                    pct_fijo_efectivo=perfil.pct_fijo,
                    modelo_cobro_efectivo=perfil.modelo_cobro,
                    nombre_canal=perfil.nombre,
                    _esc_facts=_direct_facts,
                )
                total_cad_a += tarifa_canal.costo_cadena_a_ch
                canales.append(tarifa_canal)

        # ── Totals — Oracle VT cell references ───────────────────────────────
        # C40: Annual Voz-channel op costs (payroll + nop, Voz product only) +
        #      annual cadena-A financial costs (ica_a + gmf_a + polizas_a from PyG).
        # C50: Annual cadena-B cost (monthly avg × 12).
        # C60: Annual cadena-C total = sum(costo_c_fin + ica_c + gmf_c) per month.
        # C72: (C40 + C60) / (1-margen_a) — cadenaB excluded per Oracle VT structure.
        from nexa_engine.modules.calculator_motor.formulas.profitability.calculators import ProfitabilityCalculator

        # C40 — cadena-A contract-total op costs.
        # Base temporal = nº de meses del contrato. `n = len(pyg_por_mes)` y, por
        # construcción de PyGCalculator.calcular_contrato (range(1, meses_contrato+1)),
        # n == panel.meses_contrato. Se usa `n` (no el literal 12) para que A/B queden
        # en la MISMA base que C (C60, línea ~258, suma sobre los n meses): total de
        # contrato, no anualización fija. En deals de 12 meses el resultado es idéntico
        # al previo (n==12); en deals ≠12 se corrige la subestimación/sobreestimación.
        # Oracle V2-7 has only a "Voz" channel, so the original formula filtered by
        # producto=="Voz". In the general case (WhatsApp-only, Correo, mixed deals),
        # there may be no "Voz" channels; fall back to summing all cadena-A canales.
        voz_payroll_total = sum(
            ch.payroll_ch * n for ch in canales
            if (ch.producto or "").lower() == "voz"
        )
        voz_nop_total = sum(
            ch.no_payroll_ch * n for ch in canales
            if (ch.producto or "").lower() == "voz"
        )
        if voz_payroll_total == 0 and voz_nop_total == 0 and canales:
            # No Voz channels — use the full set of cadena-A canales as base.
            voz_payroll_total = sum(ch.payroll_ch * n for ch in canales)
            voz_nop_total     = sum(ch.no_payroll_ch * n for ch in canales)
        voz_cost_monthly = (voz_payroll_total + voz_nop_total) / n if n > 0 else 0.0
        voz_frac = voz_cost_monthly / avg_costo_a if avg_costo_a > 0 else 0.0

        # C43/C44/C45 — replicate Excel Pólizas sheet formulas per escenario channel.
        #
        # The formula requires per-month escenario-channel cost. Available when:
        #   (a) calc_nomina + calc_no_payroll are set, AND
        #   (b) polizas_usuario has non-per-canal pólizas with aplica_extension=True (C45 case).
        # When (b) is absent (i.e., per_canal pólizas already handled via costo_financiero_vt),
        # the existing fallback (fin_a_sum from pyg × voz_frac) is used.
        #
        # Condition: use new logic only when there are deal-wide pólizas (per_canal=False)
        # with aplica_extension=True — those require the C45 multi-period formula to
        # distribute the extension cost across channels.
        # For pólizas with per_canal=True or aplica_extension=False, the existing
        # fallback (costo_financiero_vt_cadena_a × voz_frac) produces the correct result.
        # F1/F2: Eligibility predicate shared by both the activation guard and pol_cfg_fin.
        # A póliza contributes to the C45 extension formula only when ALL of these hold:
        #   - activa: póliza is active for this deal
        #   - aplica_a: applies to Cadena A
        #   - not per_canal: deal-wide (not allocated per channel already)
        #   - not is_comision_administracion: excluded; handled separately in PyG
        #   - aplica_extension: explicitly configured to extend past contract end
        #   - meses_extension (truthy): has a positive extension horizon
        # Using a shared predicate eliminates the guard/filter asymmetry: any póliza
        # that passes the guard is guaranteed to also pass the filter, and vice versa.
        def _es_poliza_extension_deal_wide(p) -> bool:
            return (
                not p.per_canal
                and p.activa
                and p.aplica_a
                and not p.is_comision_administracion
                and p.aplica_extension
                and bool(p.meses_extension)
            )

        has_deal_wide_polizas = (
            self._polizas_usuario is not None
            and any(_es_poliza_extension_deal_wide(p) for p in self._polizas_usuario)
        )

        fin_a_sum = 0.0
        if has_deal_wide_polizas and self._vt_facts is not None:

            # Channel selection for the C45 extension base.
            # Uses the first escenario whose canal has agent profiles — matching the
            # order in which the caller (Panel!A81:D113) lists escenarios.
            # KNOWN LIMITATION: The result depends on escenario ordering. No Excel V2-7
            # evidence exists to certify a different criterion (e.g. FTE-max). For the
            # certified case (AMERICAS), escenario 1 is Voz, which is the channel Excel
            # uses for C45. A heuristic based on FTE was considered but rejected because
            # it is not certified against any Excel oracle. Deals must order escenarios
            # with the C45 base channel first.
            esc_canal = None
            if self._escenarios:
                for esc in self._escenarios:
                    esc_c = esc.canal.lower()
                    if any((p.canal or "").lower() == esc_c for p in self._perfiles if not p.es_soporte):
                        esc_canal = esc_c; break
            if esc_canal is None and canales:
                esc_canal = (canales[0].producto or "").lower()

            ext_facts_esc = self._vt_facts.canales_extension.get(esc_canal) if esc_canal else None

            if ext_facts_esc is None:
                # No extension facts available — fallback to 0
                _logger.warning(
                    "[VT_WARN] has_deal_wide_polizas=True pero no se encontraron extension facts "
                    "para canal '%s'. fin_a_sum será 0.",
                    esc_canal,
                )
                ica_a_total = gmf_a_total = pol_a_total = 0.0
                fin_sim_por_canal: "dict[str, tuple[float, float, float]]" = {}
                fin_a_sum = 0.0
            else:
                # Consume pre-computed extension facts from VisionTarifasFacts
                esc_months = [
                    nom.total + nop.opex_ti + nop.capex + nop.costos_fijos
                    for nom, nop in zip(ext_facts_esc.nomina_por_mes, ext_facts_esc.no_payroll_por_mes)
                ]

                perfiles_esc = [p for p in self._perfiles if (p.canal or "").lower() == esc_canal] if esc_canal else self._perfiles
                esc_perfiles_agente = [p for p in perfiles_esc if not p.es_soporte]
                nom_last = ext_facts_esc.nomina_ultimo_mes
                nop_last = ext_facts_esc.no_payroll_ultimo_mes
                recurrent_inv = sum(
                    getattr(p, "inversiones_mensual_recurrente", 0.0) or 0.0
                    for p in esc_perfiles_agente
                )

                # F4: Normalize inv_rec when inv_avg is absent.
                #
                # inversiones_mensual_recurrente (inv_rec) represents the CAPEX cost for
                # months 2..N — the recurring amount after the one-time setup in month 1.
                # It only makes sense as an extension base when inversiones_mensual (inv_avg)
                # is also set, because inv_avg activates the CAPEX override mode in
                # NoPayroll calculator: nop.capex = inv_avg (constant across all months).
                #
                # When inv_avg = 0, the NoPayroll calculator uses parametric CAPEX (variable per
                # month). In that case esc_months[i] and a hypothetical esc_last based on
                # inv_rec would use inconsistent bases — parametric for the contract period
                # and manual override for extension. To avoid silently incorrect results,
                # inv_rec is treated as 0 when inv_avg = 0, falling back to esc_months[-1]
                # as the extension base (consistent with the parametric path).
                if recurrent_inv > 0:
                    inv_avg_total = sum(
                        getattr(p, "inversiones_mensual", 0.0) or 0.0
                        for p in esc_perfiles_agente
                    )
                    if inv_avg_total == 0.0:
                        _logger.warning(
                            "[VT_WARN] inversiones_mensual_recurrente>0 pero inversiones_mensual=0 "
                            "en todos los perfiles del canal '%s'. inv_rec requiere inv_avg para "
                            "establecer el modo override de CAPEX. inv_rec normalizado a 0 — "
                            "esc_last usará el último mes del contrato como base de extensión.",
                            esc_canal,
                        )
                        recurrent_inv = 0.0

                esc_last = (
                    nom_last.total + nop_last.opex_ti + recurrent_inv + nop_last.costos_fijos
                    if recurrent_inv > 0
                    else (esc_months[-1] if esc_months else 0.0)
                )

                # F1: pol_cfg_fin uses the same eligibility predicate as the guard.
                # Only pólizas that satisfy _es_poliza_extension_deal_wide are included,
                # ensuring no póliza with aplica_extension=False can contribute to C45.
                pol_cfg_fin = [
                    (p.tasa_efectiva, p.meses_extension or 0)
                    for p in self._polizas_usuario
                    if _es_poliza_extension_deal_wide(p)
                ]

                fm_a = ProfitabilityCalculator.calcular_factor_margenes(self._panel)
                # F5: Use centralized helper — validated, raises ValueError with clear message.
                start_idx = mes_inicio_contrato(self._panel.fecha_inicio)
                umbral = n + start_idx
                max_dur = max((dur for _, dur in pol_cfg_fin), default=0) if pol_cfg_fin else 0

                c43_sim = c44_sim = c45_sim = 0.0
                for idx in range(1, max(umbral + max_dur, umbral + 1)):
                    contract_pos = idx - start_idx
                    if 0 <= contract_pos < n:
                        base = esc_months[contract_pos]
                    elif idx >= umbral:
                        base = esc_last
                    else:
                        base = 0.0

                    tasa_m = sum(te for te, dur in pol_cfg_fin if dur >= idx) if pol_cfg_fin else 0.0
                    pol_m = tasa_m * base / fm_a if fm_a > 0 else 0.0
                    if pol_m > 0:
                        c45_sim += pol_m
                        if 0 <= contract_pos < n and base > 0:
                            c43_sim += (base / fm_a + pol_m) * self._panel.tasa_ica
                            c44_sim += (base + pol_m) * self._panel.tasa_gmf

                fin_a_sum = c43_sim + c44_sim + c45_sim
                # Preserve individual values for result observability (Excel C43/C44/C45).
                ica_a_total  = c43_sim
                gmf_a_total  = c44_sim
                pol_a_total  = c45_sim

                # Build per-canal fin_sim for hierarchical desglose.
                # esc_canal already computed above. For every OTHER canal that has escenarios,
                # run the same formula with that canal's profiles.
                # These are NOT certified against Excel (no oracle for non-primary channels)
                # but use the identical formula.
                fin_sim_por_canal: "dict[str, tuple[float, float, float]]" = {
                    esc_canal: (c43_sim, c44_sim, c45_sim),
                }
                seen_canales = {esc_canal}
                for esc in self._escenarios:
                    ch = esc.canal.lower()
                    if ch not in seen_canales:
                        perfiles_ch = [p for p in self._perfiles if (p.canal or "").lower() == ch]
                        if perfiles_ch:
                            fin_sim_por_canal[ch] = self._simular_financiero_canal(
                                perfiles_ch, n, pol_cfg_fin, fm_a, start_idx,
                            )
                        seen_canales.add(ch)

        else:
            # Fallback path: individual C43/C44/C45 are not computable as separate
            # certified values. Leave at 0 — fin_a_sum is still exposed via costo_cadena_a_total.
            ica_a_total = gmf_a_total = pol_a_total = 0.0
            fin_sim_por_canal: "dict" = {}
            # Fallback: proportional from deal-wide PyG financials (per_canal pólizas case).
            fin_a_fallback = sum(m.costo_financiero_vt_cadena_a for m in pyg_por_mes)
            if fin_a_fallback == 0.0:
                fin_a_fallback = sum(m.ica_a + m.gmf_a + m.polizas_a for m in pyg_por_mes)
            fin_a_sum = fin_a_fallback * voz_frac

            # Extended per_canal pólizas (post-contract extension months).
            # Only applies to per_canal=True pólizas with aplica_extension=True.
            per_canal_ext = [
                p for p in (self._polizas_usuario or [])
                if p.per_canal and not p.is_comision_administracion
                and p.aplica_a and p.activa and p.aplica_extension and p.meses_extension
            ]
            if per_canal_ext and voz_cost_monthly > 0:
                fm_a = ProfitabilityCalculator.calcular_factor_margenes(self._panel)
                voz_cost_last_month = pyg_por_mes[-1].costo_a * voz_frac if pyg_por_mes else voz_cost_monthly
                max_ext = max(p.meses_extension for p in per_canal_ext)
                for i in range(1, max_ext + 1):
                    tasa_i = sum(p.tasa_efectiva for p in per_canal_ext if p.meses_extension >= i)
                    if tasa_i > 0:
                        fin_a_sum += tasa_i * voz_cost_last_month / fm_a

        costo_cad_a_total = voz_payroll_total + voz_nop_total + fin_a_sum

        # C50 — cadena-B contract-total cost (avg mensual × n meses = Σ sobre el contrato,
        # misma base que C40 y C60; n == panel.meses_contrato).
        costo_b_total = avg_costo_b * n

        # C60 — cadena-C annual cost (costo_c_fin already excludes margin; add ica_c + gmf_c)
        costo_c_total = sum(m.costo_c_fin + m.ica_c + m.gmf_c for m in pyg_por_mes)

        # C65 — deal total cost
        costo_total = costo_cad_a_total + costo_b_total + costo_c_total

        # C47/C67/C72 — revenues (cadena-B excluded per Oracle VT structure)
        ingreso_a = ProfitabilityCalculator.calcular_ingreso_desde_costo(costo_cad_a_total, factor, 1.0)
        ingreso_b = ProfitabilityCalculator.calcular_ingreso_desde_costo(costo_b_total, factor, 1.0)
        ingreso_c = ProfitabilityCalculator.calcular_ingreso_desde_costo(costo_c_total, factor, 1.0)
        ingreso_total = ingreso_a + ingreso_c  # C72 = C47 + C67 (no C57)

        _logger.info(
            "[VISION_BUILD] op=calcular_vision_tarifas inputs={meses:%d,canales:%d,factor_billing:%.6f} "
            "outputs={costo_total:%.2f,ingreso_total:%.2f,costo_a:%.2f,costo_b:%.2f,costo_c:%.2f} "
            "source=PyG+Panel(margen_a)",
            n, len(canales), factor,
            costo_total, ingreso_total, costo_cad_a_total, costo_b_total, costo_c_total,
        )

        # ── Hierarchical Vision Tarifas (Excel Reverse-Engineering) ─────
        # Build per-scenario detailed structure when escenarios exist.
        # canales list was already built in the loop above; map escenario → canal
        # so hierarchical building can reference pre-computed TarifaCanal values.
        escenarios_detalle: List[EscenarioTarifasDetalle] = []
        desglose_opex: List[DesgloseProductoOpex] = []

        if self._escenarios:
            reglas = self._extraer_reglas_business()
            desglose_opex = self._desglose_opex_por_producto(pyg_por_mes)

            # Build escenario_num → TarifaCanal index map (order matches escenarios loop)
            canal_por_escenario: dict = {}
            canal_idx = 0
            for escenario in self._escenarios:
                agent_perfiles = [
                    p for p in self._perfiles
                    if p.canal.lower() == escenario.canal.lower()
                    and p.modalidad.lower() == escenario.modalidad.lower()
                    and not p.es_soporte
                ]
                if agent_perfiles and canal_idx < len(canales):
                    canal_por_escenario[escenario.escenario] = canales[canal_idx]
                    canal_idx += 1

            for escenario in self._escenarios:
                tarifa_canal = canal_por_escenario.get(escenario.escenario)
                if tarifa_canal is None:
                    continue

                perfiles_canal = [
                    p for p in self._perfiles
                    if p.canal.lower() == escenario.canal.lower()
                    and p.modalidad.lower() == escenario.modalidad.lower()
                ]

                # Desglose de costos por cadena.
                # fin_sim: per-canal (c43,c44,c45) annual totals from the certified formula.
                # Provided only when has_deal_wide_polizas=True; None for fallback path.
                fin_sim_ch = fin_sim_por_canal.get(escenario.canal.lower())
                cadena_a, cadena_b, cadena_c = self._desglose_cadena_por_escenario(
                    escenario=escenario,
                    perfiles_canal=perfiles_canal,
                    tarifa_canal=tarifa_canal,
                    pyg_por_mes=pyg_por_mes,
                    avg_costo_a=avg_costo_a,
                    avg_fin_total=avg_fin_total,
                    avg_costo_b=avg_costo_b,
                    l50=l50,
                    factor=factor,
                    fin_sim=fin_sim_ch,
                )

                # Tarifa calculations — from TarifaCanal (Excel G43-G57 section)
                tarifas_esc = TarifasEscenario(
                    facturacion_total=tarifa_canal.ingreso_bruto,
                    ingreso_componente_fijo=tarifa_canal.facturacion,
                    ingreso_componente_variable=tarifa_canal.ingreso_bruto * tarifa_canal.pct_variable,
                    tarifa_por_fte=tarifa_canal.tarifa_fijo_fte,
                    tarifa_hora_loggeada=tarifa_canal.tarifa_hora_loggeada,
                    tarifa_hora_pagada=tarifa_canal.tarifa_hora_pagada,
                    tarifa_por_transaccion=tarifa_canal.tarifa_variable,
                    volumen_minimo_transaccion=tarifa_canal.vol_minimo_transaccion,
                )

                # Resumen del escenario — Excel B10:H21
                meta = EscenarioTarifasResumen(
                    escenario=escenario.escenario,
                    modalidad=escenario.modalidad,
                    canal=escenario.canal,
                    modelo_cobro=escenario.modelo_cobro,
                    componente_fijo_label=escenario.componente_fijo_tipo or "",
                    pct_fijo=escenario.componente_fijo_pct,
                    componente_variable_label=escenario.componente_variable_tipo or "",
                    pct_variable=escenario.componente_variable_pct,
                    facturacion_directo=tarifa_canal.facturacion,
                    tarifa_componente_fijo=tarifa_canal.tarifa_fijo_fte,
                    # Tarifa variable: conditional per Excel C21 formula
                    # IF C16="Transacción" → tarifa_variable (G55)
                    # IF C16 in ["Resultados","Honorarios"] → calculado honorarios
                    tarifa_componente_variable=tarifa_canal.tarifa_variable,
                )

                # Optional: Componente Fijo detail — Excel rows 104-127
                # Habilitado when componente_fijo_tipo == "Tiempo" (Excel: IF(C34="Tiempo",...))
                perfil_agente_list = [p for p in perfiles_canal if not p.es_soporte]
                perfil_agente = perfil_agente_list[0] if perfil_agente_list else None
                comp_fijo = self._construir_componente_fijo(escenario, perfil_agente)
                comp_var = self._construir_componente_variable(escenario)

                # Assemble hierarchical detail
                detalle = EscenarioTarifasDetalle(
                    meta=meta,
                    reglas_business=reglas,
                    cadena_a=cadena_a,
                    cadena_b=cadena_b,
                    cadena_c=cadena_c,
                    tarifas=tarifas_esc,
                    componente_fijo=comp_fijo if comp_fijo.habilitado else None,
                    componente_variable=comp_var if comp_var.habilitado else None,
                    tarifas_venta=[],
                )
                escenarios_detalle.append(detalle)

        return ResultadoVisionTarifas(
            canales              = canales,
            costo_cadena_a_total = costo_cad_a_total,
            costo_cadena_b_total = costo_b_total,
            costo_cadena_c_total = costo_c_total,
            costo_total          = costo_total,
            # Excel V2-8 · 'Vision Tarifas_Modelo_Cobro'!H19 → 'Hoja Maestra Escenarios'!C289
            # H19 = ingreso mensual base = primer mes de producción plena (rampup=1.0, M3+)
            # Delta vs Excel: +1.9% = HME cache architectural delta (ACCEPTED)
            ingreso_mensual      = (pyg_por_mes[2].ingreso_bruto if n >= 3
                                    else ingreso_total / n if n > 0 else 0.0),
            ingreso_cadena_a     = ingreso_a,
            ingreso_cadena_b     = ingreso_b,
            ingreso_cadena_c     = ingreso_c,
            # Excel C43/C44/C45 — exposed for direct individual testing.
            # Non-zero only in the has_deal_wide_polizas path; 0 in fallback path.
            ica_cadena_a         = ica_a_total,
            gmf_cadena_a         = gmf_a_total,
            polizas_cadena_a     = pol_a_total,
            escenarios_detalle   = escenarios_detalle,
            desglose_producto_opex = desglose_opex,
        )

    # ──────────────────────────────────────────────────────────────
    # Financiero per-canal simulation helper
    # ──────────────────────────────────────────────────────────────
