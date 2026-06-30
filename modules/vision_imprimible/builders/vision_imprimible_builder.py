"""
nexa_engine/calculators/vision_imprimible.py
=============================================
GAP-VIS-1: Visión Imprimible Builder — composición pura de resultados del deal.

Responsabilidad
---------------
Construir la `VisionImprimible` a partir de los resultados ya calculados
por los demás calculadores del pipeline. NO recalcula nada.

Corresponde a la hoja 'Visión Imprimible' del Excel V2-5, que es una vista
de presentación que agrega y organiza datos de todas las demás hojas.

Secciones del Excel → Secciones del modelo:
  01 · FICHA DEL DEAL         → FichaDelDeal
  02 · ECONOMICS              → EconomicsDeal
  03 · CONFIGURACIÓN COMERCIAL → ConfiguracionComercial
  04 · ANÁLISIS GRÁFICO       → EvolucionMensual + WaterfallPromedio
  05 · Escenarios             → escenarios (List[EscenarioComercial])
  Adicional                   → ReglaNegocios + EvaluacionRiesgo

NO importar de engine.py (evitar importación circular).
"""

from __future__ import annotations

from typing import List, Optional

from nexa_engine.modules.vision_imprimible.helpers.canal_builders import (
    _construir_detalle_por_canal,
    _construir_estructura_equipo,
)

from nexa_engine.modules.shared.models import (
    CanalDetalle,
    CanalDetalleModalidad,
    CanalResumen,
    ComparativoEscenario,
    ModalidadCanalMetricas,
    ConfiguracionComercial,
    EconomicsDeal,
    EscenarioComercial,
    EstructuraEquipo,
    EvaluacionRiesgo,
    FichaDelDeal,
    EvolucionMensual,
    GrupoCargoEquipo,
    KPIsDeal,
    PanelDeControl,
    PerfilCadenaA,
    PyGMensual,
    ReglaNegocios,
    ResultadoCostToServe,
    ResultadoVisionTarifas,
    RolEquipo,
    VisionImprimible,
    VisionServicioResumen,
    WaterfallPromedio,
)


class VisionImprimibleBuilder:
    """
    Ensambla la Visión Imprimible a partir de los outputs del pipeline de cálculo.

    Uso:
        builder = VisionImprimibleBuilder()
        vision = builder.construir(
            panel=solicitud.panel,
            kpis=kpis,
            pyg_por_mes=pyg_contrato,
            vision_tarifas=vision_tarifas,
            waterfall=waterfall,
            reglas_negocio=reglas,
            evaluacion_riesgo=evaluacion_riesgo,
            escenarios=solicitud.escenarios,
            cost_to_serve=cost_to_serve,
        )
    """

    class FORMULA_ID:
        """Trazabilidad de fórmulas de Vision Imprimible — Composición pura."""
        FICHA_DEL_DEAL = "VISION_IMPRIMIBLE.FICHA_DEL_DEAL"
        ECONOMICS_DEAL = "VISION_IMPRIMIBLE.ECONOMICS_DEAL"
        CONFIGURACION_COMERCIAL = "VISION_IMPRIMIBLE.CONFIGURACION_COMERCIAL"
        EVOLUCION_MENSUAL = "VISION_IMPRIMIBLE.EVOLUCION_MENSUAL"
        COMPARATIVO_ESCENARIOS = "VISION_IMPRIMIBLE.COMPARATIVO_ESCENARIOS"
        VISION_SERVICIO = "VISION_IMPRIMIBLE.VISION_SERVICIO"
        VISION_POR_CANAL = "VISION_IMPRIMIBLE.VISION_POR_CANAL"
        DETALLE_POR_CANAL = "VISION_IMPRIMIBLE.DETALLE_POR_CANAL"
        ESTRUCTURA_EQUIPO = "VISION_IMPRIMIBLE.ESTRUCTURA_EQUIPO"
        VISION_IMPRIMIBLE_RESULTADO = "VISION_IMPRIMIBLE.RESULTADO"

    def construir(
        self,
        panel: PanelDeControl,
        kpis: KPIsDeal,
        pyg_por_mes: List[PyGMensual],
        vision_tarifas: Optional[ResultadoVisionTarifas] = None,
        waterfall: Optional[WaterfallPromedio] = None,
        reglas_negocio: Optional[List[ReglaNegocios]] = None,
        evaluacion_riesgo: Optional[EvaluacionRiesgo] = None,
        escenarios: Optional[List[EscenarioComercial]] = None,
        cost_to_serve: Optional[ResultadoCostToServe] = None,
        perfiles_cadena_a: Optional[List[PerfilCadenaA]] = None,
    ) -> VisionImprimible:
        """
        Ensambla todas las secciones de la Visión Imprimible.

        Args:
            panel:             PanelDeControl del deal (fuente: Ficha, Economics, Config).
            kpis:              KPIs calculados (fuente: Economics).
            pyg_por_mes:       P&G mensual completo (fuente: Evolución Mensual).
            vision_tarifas:    Tarifas por canal (fuente: Configuración Comercial).
            waterfall:         Promedios waterfall (fuente: Análisis Gráfico).
            reglas_negocio:    Reglas y rangos del deal.
            evaluacion_riesgo: Evaluación de riesgo del deal.
            escenarios:        Escenarios comerciales del Panel!A81:D113.
            cost_to_serve:     CTS calculado (fuente: Economics).
            perfiles_cadena_a: Perfiles operativos (fuente: Estructura del Equipo).

        Returns:
            VisionImprimible con todas las secciones populadas.
        """
        ficha               = self._construir_ficha(panel)
        economics           = self._construir_economics(panel, kpis, cost_to_serve, vision_tarifas)
        configuracion       = self._construir_configuracion(vision_tarifas)
        evolucion           = self._construir_evolucion(pyg_por_mes)

        # GAP-VIS-1 Sección 05: Comparativo de Escenarios (Excel VI rows 73-78)
        comparativo = self._construir_comparativo(escenarios)

        # ── Visión Ejecutiva Integral — secciones agregadas ───────────────
        # Composición pura sobre resultados ya calculados; cada sección se
        # puebla solo cuando existen datos reales (sin fabricar valores).
        vision_servicio = self._construir_vision_servicio(
            panel, kpis, cost_to_serve, vision_tarifas, perfiles_cadena_a,
        )
        vision_canal = self._construir_vision_por_canal(
            vision_tarifas, cost_to_serve, perfiles_cadena_a,
        )
        detalle_canal = self._construir_detalle_por_canal(
            vision_tarifas, cost_to_serve, perfiles_cadena_a,
        )
        estructura_equipo = self._construir_estructura_equipo(perfiles_cadena_a)

        return VisionImprimible(
            ficha                   = ficha,
            economics               = economics,
            configuracion_comercial = configuracion,
            evolucion_mensual       = evolucion,
            waterfall               = waterfall,
            reglas_negocio          = reglas_negocio or [],
            evaluacion_riesgo       = evaluacion_riesgo,
            escenarios              = escenarios or [],
            comparativo_escenarios  = comparativo,
            vision_por_servicio     = vision_servicio,
            vision_por_canal        = vision_canal,
            detalle_por_canal       = detalle_canal,
            estructura_equipo       = estructura_equipo,
        )

    # ──────────────────────────────────────────────────────────────
    # Sección 01 — Ficha del Deal
    # ──────────────────────────────────────────────────────────────

    # OWNERSHIP: BUILDER_ONLY — DUPLICATED_PENDING_DEPRECATION
    # VisionImprimible.ficha (FichaDelDeal, 4 campos) NO es leído por el serializer.
    # El documento JSON persistido usa _ficha_deal_to_dict(panel) en serializer_helpers.py
    # que produce 25+ campos. NO cambiar la fuente del serializer (perdería datos).
    # Vivo porque tests de contrato del builder verifican estos 4 campos:
    #   test_gap_closure_v25.py::TestGapVIS1 y test_certificacion_final_v25.py::TestFase5Snapshot
    @staticmethod
    def _construir_ficha(panel: PanelDeControl) -> FichaDelDeal:
        """
        Excel Visión Imprimible rows 7-13:
          CLIENTE / FECHA DE INICIO / SERVICIO / DURACIÓN
        """
        return FichaDelDeal(
            cliente      = panel.cliente,
            fecha_inicio = panel.fecha_inicio,
            servicio     = panel.linea_negocio,
            duracion     = f"{panel.meses_contrato} meses",
        )

    # ──────────────────────────────────────────────────────────────
    # Sección 02 — Economics
    # ──────────────────────────────────────────────────────────────

    # OWNERSHIP: BUILDER_ONLY — DUPLICATED_PENDING_DEPRECATION
    # VisionImprimible.economics (EconomicsDeal, 5 campos) NO es leído por el serializer.
    # El documento JSON persistido usa asdict(resultado.kpis) en pricing_result_serializer.py
    # que serializa el KPIsDeal completo (muchos más campos).
    # Vivo porque tests verifican: v.economics.margen, v.economics.contribucion_total.
    @staticmethod
    def _construir_economics(
        panel: PanelDeControl,
        kpis: KPIsDeal,
        cost_to_serve: Optional[ResultadoCostToServe],
        vision_tarifas: Optional[ResultadoVisionTarifas],
    ) -> EconomicsDeal:
        """
        Excel Visión Imprimible rows 15-30:
          INGRESO MENSUAL / COST TO SERVE MENSUAL / MARGEN / CONTRIBUCION
        """
        ingreso_mensual = (
            vision_tarifas.ingreso_mensual
            if vision_tarifas else kpis.ingreso_mensual
        )
        cts_mensual = (
            cost_to_serve.cts_ponderado
            if cost_to_serve else 0.0
        )
        return EconomicsDeal(
            ingreso_mensual     = ingreso_mensual,
            cts_mensual         = cts_mensual,
            margen              = panel.margen,
            contribucion_total  = kpis.contribucion_total,
            escenario_referencia = "Escenario 1",
        )

    # ──────────────────────────────────────────────────────────────
    # Sección 03 — Configuración Comercial
    # ──────────────────────────────────────────────────────────────

    # OWNERSHIP: BUILDER_ONLY — DUPLICATED_PENDING_DEPRECATION + DIVERGENCIA_CONOCIDA
    # VisionImprimible.configuracion_comercial (ConfiguracionComercial, 4 campos) NO es
    # leído por el serializer. El documento JSON usa _configuracion_comercial(resultado)
    # en serializer_helpers.py que produce 12+ campos con lógica diferente:
    #   Builder: primer canal con ingreso_bruto > 0
    #   Serializer: canal con mayor facturacion (via _select_principal_channel)
    # DIVERGENCIA CONOCIDA: la selección del canal principal puede diferir entre builder y serializer.
    @staticmethod
    def _construir_configuracion(
        vision_tarifas: Optional[ResultadoVisionTarifas],
    ) -> ConfiguracionComercial:
        """
        Excel Visión Imprimible rows 32-39:
          MODELO DE COBRO / TARIFA FIJA / TARIFA VARIABLE
        """
        if not vision_tarifas or not vision_tarifas.canales:
            return ConfiguracionComercial()

        # Canal principal = primer canal con tarifa > 0
        canal_principal = next(
            (c for c in vision_tarifas.canales if c.ingreso_bruto > 0),
            vision_tarifas.canales[0],
        )

        return ConfiguracionComercial(
            modelo_cobro    = canal_principal.modelo_cobro,
            tarifa_fija     = canal_principal.tarifa_fijo_fte,
            tarifa_variable = canal_principal.tarifa_variable,
            canales         = vision_tarifas.canales,
        )

    # ──────────────────────────────────────────────────────────────
    # Sección 04 — Evolución Mensual
    # ──────────────────────────────────────────────────────────────

    # ──────────────────────────────────────────────────────────────
    # Sección 05 — Comparativo de Escenarios
    # OWNERSHIP: BUILDER_CANONICAL — serializado via _vision_ejecutiva_sections()
    # en serializer_helpers.py. VisionImprimible.comparativo_escenarios ES leído
    # por el serializer (via resultado.vision_imprimible). Cadena limpia.
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _construir_comparativo(
        escenarios: Optional[List[EscenarioComercial]],
    ) -> List[ComparativoEscenario]:
        """
        GAP-VIS-1 Sección 05: Comparativo de Escenarios.
        Excel: Visión Imprimible rows 73-78.
        Columnas: Escenario | Modalidad - Canal | Modelo de cobro.

        Cada EscenarioComercial del Panel se convierte en una fila.
        Composición pura — NO recalcula nada.
        """
        if not escenarios:
            return []
        return [
            ComparativoEscenario(
                escenario      = f"Escenario {e.escenario}",
                modalidad_canal = f"{e.modalidad} - {e.canal}",
                modelo_cobro   = e.modelo_cobro,
            )
            for e in escenarios
        ]

    # ──────────────────────────────────────────────────────────────
    # Sección 04 — Evolución Mensual
    # OWNERSHIP: BUILDER_ONLY — DUPLICATED_PENDING_DEPRECATION
    # VisionImprimible.evolucion_mensual (EvolucionMensual, 5 arrays condensados) NO es
    # leído por el serializer. El documento JSON usa [_pyg_to_dict(p) for p in resultado.pyg_por_mes]
    # en pricing_result_serializer.py que serializa el objeto PyGMensual completo
    # incluyendo @properties (ingreso_bruto, ingreso_neto, costo_total, etc.).
    # Vivo porque tests verifican: v.evolucion_mensual.meses, costos_total, ingresos_neto.
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _construir_evolucion(pyg_por_mes: List[PyGMensual]) -> EvolucionMensual:
        """
        Excel Visión Imprimible rows 56-80:
          Ingreso Neto proyectado / Costo Total / Contribución / Margen mensual.
        Arrays de valores por mes del contrato.
        """
        return EvolucionMensual(
            meses          = [m.mes for m in pyg_por_mes],
            ingresos_neto  = [m.ingreso_neto for m in pyg_por_mes],
            costos_total   = [m.costo_total for m in pyg_por_mes],
            contribucion   = [m.contribucion for m in pyg_por_mes],
            margen_mensual = [m.pct_utilidad_neta for m in pyg_por_mes],
        )

    # ──────────────────────────────────────────────────────────────
    # Visión General por Servicio
    # OWNERSHIP: BUILDER_CANONICAL — serializado via _vision_ejecutiva_sections()
    # en serializer_helpers.py, que lee resultado.vision_imprimible.vision_por_servicio.
    # Cadena limpia: Builder → VisionImprimible → Serializer → JSON doc → GET endpoint.
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _construir_vision_servicio(
        panel: PanelDeControl,
        kpis: KPIsDeal,
        cost_to_serve: Optional[ResultadoCostToServe],
        vision_tarifas: Optional[ResultadoVisionTarifas],
        perfiles_cadena_a: Optional[List[PerfilCadenaA]],
    ) -> List[VisionServicioResumen]:
        """
        Visión General por Servicio — rollup del deal bajo su servicio.

        Un deal tiene un único servicio (panel.linea_negocio). Se devuelve una
        lista de un elemento (estable para futuro multi-servicio). Composición
        pura: todas las métricas provienen de resultados ya calculados.

        Si no hay servicio identificable → lista vacía (no se fabrica).
        """
        servicio = (panel.linea_negocio or "").strip()
        if not servicio:
            return []

        perfiles = perfiles_cadena_a or []
        fte_total = sum(p.fte for p in perfiles if not p.es_soporte)

        ingreso_mensual = (
            vision_tarifas.ingreso_mensual if vision_tarifas else kpis.ingreso_mensual
        )
        cts_ponderado = cost_to_serve.cts_ponderado if cost_to_serve else 0.0

        # Volumen mensual: suma de volúmenes Cadena A por canal (insumo real).
        volumen_mensual = sum(p.vol_cadena_a_mensual for p in perfiles if not p.es_soporte)

        cadenas = getattr(panel, "cadenas_activas", None)
        activas: List[str] = []
        if cadenas is not None:
            if getattr(cadenas, "cadena_a", False):
                activas.append("A")
            if getattr(cadenas, "cadena_b", False):
                activas.append("B")
            if getattr(cadenas, "cadena_c", False):
                activas.append("C")

        return [
            VisionServicioResumen(
                servicio           = servicio,
                ingreso_mensual    = ingreso_mensual,
                cts_ponderado      = cts_ponderado,
                costo_mensual      = kpis.costo_mensual_promedio,
                margen             = panel.margen,
                contribucion_total = kpis.contribucion_total,
                fte_total          = fte_total,
                volumen_mensual    = volumen_mensual,
                meses_contrato     = panel.meses_contrato,
                cadenas_activas    = activas,
            )
        ]

    # ──────────────────────────────────────────────────────────────
    # Visión General por Canal
    # OWNERSHIP: BUILDER_CANONICAL — serializado via _vision_ejecutiva_sections()
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _construir_vision_por_canal(
        vision_tarifas: Optional[ResultadoVisionTarifas],
        cost_to_serve: Optional[ResultadoCostToServe],
        perfiles_cadena_a: Optional[List[PerfilCadenaA]] = None,
    ) -> List[CanalResumen]:
        """
        Visión General por Canal — una fila por canal real con split Inbound/Outbound.

        Fuente primaria: cost_to_serve.canales_detalle (los canales reales con CTS).
        Fuente secundaria: vision_tarifas.canales (tarifas/facturación por canal).
        Fuente terciaria: perfiles_cadena_a (split por modalidad).

        SIEMPRE retorna lista (puede estar vacía si no hay canales ni perfiles).
        """
        # Index tarifa info by canal name (lower)
        tarifa_por_canal: dict = {}
        if vision_tarifas and vision_tarifas.canales:
            for c in vision_tarifas.canales:
                key = (c.producto or c.nombre_canal or "").lower()
                tarifa_por_canal[key] = c

        # Mapa canal → {modalidad: {fte, payroll}} desde perfiles
        perfiles_por_canal: dict = {}
        for p in (perfiles_cadena_a or []):
            if p.es_soporte:
                continue
            canal_key = (p.canal or "").lower()
            mod = (p.modalidad or "Inbound").strip().lower()
            entry = perfiles_por_canal.setdefault(canal_key, {})
            mod_entry = entry.setdefault(mod, {"fte": 0.0, "payroll": 0.0, "no_payroll": 0.0})
            mod_entry["fte"] += p.fte
            mod_entry["payroll"] += p.salario_cargado * p.fte

        # Collect all canal keys from ALL sources
        seen: set = set()
        canal_keys_ordered: list = []

        # Priority 1: canales from CTS (real operational canales)
        if cost_to_serve and cost_to_serve.canales_detalle:
            for cd in cost_to_serve.canales_detalle:
                key = (cd.canal or "").lower()
                if key and key not in seen:
                    seen.add(key)
                    canal_keys_ordered.append(key)

        # Priority 2: canales from perfiles (may have canales not in CTS)
        for p in (perfiles_cadena_a or []):
            if p.es_soporte:
                continue
            key = (p.canal or "").lower()
            if key and key not in seen:
                seen.add(key)
                canal_keys_ordered.append(key)

        # Priority 3: canales from vision_tarifas (escenario-based — may differ)
        if vision_tarifas and vision_tarifas.canales:
            for c in vision_tarifas.canales:
                key = (c.producto or c.nombre_canal or "").lower()
                if key and key not in seen:
                    seen.add(key)
                    canal_keys_ordered.append(key)

        # Build CTS detail index
        cts_por_canal: dict = {}
        if cost_to_serve and cost_to_serve.canales_detalle:
            for cd in cost_to_serve.canales_detalle:
                cts_por_canal[(cd.canal or "").lower()] = cd

        filas: List[CanalResumen] = []
        for canal_key in canal_keys_ordered:
            cd = cts_por_canal.get(canal_key)
            tc = tarifa_por_canal.get(canal_key)

            # Canal name: prefer CTS (real), then tarifa, then key
            canal_nombre = (cd.canal if cd else None) or \
                           (tc.nombre_canal if tc else None) or \
                           canal_key.title()
            modalidad = (cd.modalidad if cd else None) or \
                        (tc.modalidad if tc else None) or ""
            fte = (cd.fte if cd else None) or (tc.fte if tc else 0.0)
            estado = "Activo" if fte > 0 else "No Activado"

            # Build Inbound / Outbound split from perfiles
            mods = perfiles_por_canal.get(canal_key, {})
            costo_ref = (cd.cts * fte if cd else 0.0) or 1.0
            inbound = outbound = None
            if "inbound" in mods:
                m = mods["inbound"]
                ct = m["payroll"] + m.get("no_payroll", 0.0)
                inbound = ModalidadCanalMetricas(
                    fte=m["fte"], payroll=m["payroll"],
                    no_payroll=m.get("no_payroll", 0.0), costo_total=ct,
                    pct_participacion=ct / costo_ref if costo_ref else 0.0,
                )
            if "outbound" in mods:
                m = mods["outbound"]
                ct = m["payroll"] + m.get("no_payroll", 0.0)
                outbound = ModalidadCanalMetricas(
                    fte=m["fte"], payroll=m["payroll"],
                    no_payroll=m.get("no_payroll", 0.0), costo_total=ct,
                    pct_participacion=ct / costo_ref if costo_ref else 0.0,
                )

            filas.append(
                CanalResumen(
                    canal                  = canal_nombre,
                    modalidad              = modalidad,
                    modelo_cobro           = tc.modelo_cobro if tc else "",
                    estado                 = estado,
                    fte                    = fte,
                    participacion_cadena_a = cd.participacion_cadena_a if cd else 0.0,
                    volumen_mensual        = tc.vol_mensual if tc else 0,
                    facturacion            = tc.facturacion if tc else 0.0,
                    ingreso_bruto          = tc.ingreso_bruto if tc else 0.0,
                    costo_atribuible       = tc.costo_atribuible if tc else (cd.cts * fte if cd else 0.0),
                    pct_fijo               = tc.pct_fijo if tc else 0.0,
                    pct_variable           = tc.pct_variable if tc else 0.0,
                    inbound                = inbound,
                    outbound               = outbound,
                )
            )
        return filas

    # ──────────────────────────────────────────────────────────────
    # Vista Detallada por Canal (delegated to canal_builders)
    # OWNERSHIP: BUILDER_CANONICAL — serializado via _vision_ejecutiva_sections()
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _construir_detalle_por_canal(
        vision_tarifas,
        cost_to_serve,
        perfiles_cadena_a=None,
    ):
        return _construir_detalle_por_canal(vision_tarifas, cost_to_serve, perfiles_cadena_a)

    # ──────────────────────────────────────────────────────────────
    # Estructura del Equipo (delegated to canal_builders)
    # OWNERSHIP: BUILDER_CANONICAL — serializado via _vision_ejecutiva_sections()
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _construir_estructura_equipo(perfiles_cadena_a):
        return _construir_estructura_equipo(perfiles_cadena_a)
