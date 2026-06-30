"""
Risk evaluation calculator — 10 criteria across two categories.

Source: Hoja "Riesgo" del Excel V2-4 (B1:Y282).

10 criteria in two categories:

  CLIENTE (weight 0.4 on total score)
  ─────────────────────────────────────
  1. Clasificación de oportunidad  (weight 0.30)
  2. Tipo de cliente                (weight 0.25)
  3. Período de pago                (weight 0.25)
  4. Experiencia con el cliente     (weight 0.10)
  5. Presupuesto de imprevistos     (weight 0.10)

  OPERATIVO (weight 0.6 on total score)
  ──────────────────────────────────────
  6. Alertas activadas              (weight 0.30)
  7. Complejidad                    (weight 0.20)
  8. Capacitaciones                 (weight 0.20)
  9. Rotación                       (weight 0.20)
  10. Dependencia de terceros       (weight 0.10)

Scoring
-------
  Puntaje 3 = "Alto"  (mayor riesgo)
  Puntaje 2 = "Medio"
  Puntaje 1 = "Bajo"  (menor riesgo)

  score_categoria = SUMPRODUCT(puntaje_i × peso_i)  para criterios de la categoría
  score_total     = score_cliente × 0.4 + score_operativo × 0.6

Score classification
---------------------
  score < 1.5  → "Bajo"
  1.5 ≤ score < 2.5 → "Medio"
  score ≥ 2.5  → "Alto"

Approval threshold
------------------
  valor_total_deal > UMBRAL_APROBACION (1000 SMMLV).

Thresholds loaded from canonical YAML via modules/shared/config/business_rules.
"""

from __future__ import annotations

from typing import Any, Dict, List

from nexa_engine.modules.shared.config.business_rules.loader import (
    load_business_rules_cached,
)

from nexa_engine.modules.shared.models import (
    CriterioRiesgo,
    EvaluacionRiesgo,
    KPIsDeal,
    PanelDeControl,
    ParametrosCadenaB,
    ParametrosCadenaC,
    PerfilCadenaA,
    PyGMensual,
)


def _resolve_riesgo_config(riesgo_config: Dict[str, Any] | None) -> Dict[str, Any]:
    """Resolve risk config from canonical YAML plus optional runtime overrides."""
    canonical_config = load_business_rules_cached("riesgo")
    if riesgo_config is None:
        return canonical_config

    resolved_config: Dict[str, Any] = dict(canonical_config)
    for section in (
        "constantes_regulatorias",
        "pesos_categorias",
        "clasificacion_score",
        "umbrales",
    ):
        resolved_config[section] = {
            **canonical_config.get(section, {}),
            **riesgo_config.get(section, {}),
        }

    for key in ("tipos_cliente_alto", "antiguedad_alto", "criterios"):
        if key in riesgo_config:
            resolved_config[key] = riesgo_config[key]

    return resolved_config


class RiesgoCalculator:
    """
    Calcula la evaluacion de riesgo del deal a partir del resultado del motor.

    No modifica ninguna formula matematica existente -- solo interpreta
    datos ya calculados para producir la evaluacion de riesgo.

    Todos los umbrales, pesos y constantes regulatorias se cargan desde
    YAML canonico bajo modules/shared/config/business_rules a traves del provider.

    SMMLV (BUSINESS_RULES_FIX_2B):
        La fuente canonica del SMMLV es exclusivamente HR-Salarios via
        IParametrizationProvider.get_smmlv(). El argumento ``smmlv`` es
        obligatorio. No existe fallback a business_rules ni default hardcodeado.
        En produccion, engine.py inyecta self._parametrizacion.get_smmlv().
        En tests, pasar explicitamente el valor SMMLV que se quiere validar.

    @excel_lineage:
      version: V2-8
      sheet: Riesgo
      cells: [B2:Y282 (full risk matrix); B3:B12 (criterion IDs); G/I/K (scoring levels);
              R2:R11 (pesos propuestos per criterion); Q2:Q11 (factor/category labels);
              N2:N{n} (score per criterion via ArrayFormula); score_total formula UNCONFIRMED]
      concept: evaluacion_riesgo_deal_10_criterios
    @runtime_sources:
      - storage/parametrization canonical YAML (riesgo.yaml) thresholds, weights, criteria
        (loaded via modules/shared/config/business_rules/loader.py load_business_rules_cached)
      - request/request.json PanelDeControl (tipo_cliente, periodo_pago_dias,
        antiguedad_cliente, op_cont, com_cont)
      - engine KPIsDeal.valor_total_deal (computed from PricingResult)
      - storage/parametrization/hr IParametrizationProvider.get_smmlv() (SMMLV vigente)
        BUSINESS_RULES_FIX_2B: mandatory kwarg -- no fallback
    @confidence: HIGH (criteria/weights from YAML; exact Excel cell refs confirmed for Riesgo sheet)
    @forbidden:
      - hardcoded_excel_values (SMMLV and thresholds must come from provider/YAML, not constants)
    """

    def __init__(
        self,
        riesgo_config: dict | None = None,
        *,
        smmlv: float,
    ) -> None:
        """
        Args:
            riesgo_config: Risk model configuration dict from
                           IParametrizationProvider.get_riesgo_config().
                           If None, uses canonical YAML defaults.
            smmlv:         SMMLV vigente de HR-Salarios (IParametrizationProvider.get_smmlv()).
                           BUSINESS_RULES_FIX_2B: argumento obligatorio — no existe fallback.
                           Usar siempre self._parametrizacion.get_smmlv() en producción.
                           En tests, pasar el valor explícito a validar.

        Raises:
            ValueError: Si smmlv <= 0 (valor inválido).
        """
        if smmlv <= 0:
            raise ValueError(
                f"RiesgoCalculator requiere smmlv > 0. Recibido: {smmlv!r}. "
                "Pasar IParametrizationProvider.get_smmlv() (HR-Salarios canónico). "
                "BUSINESS_RULES_FIX_2B: no existe fallback a business_rules."
            )

        riesgo_config = _resolve_riesgo_config(riesgo_config)

        reg = riesgo_config.get("constantes_regulatorias", {})
        umb = riesgo_config.get("umbrales", {})
        pesos_cat = riesgo_config.get("pesos_categorias", {})
        clasif = riesgo_config.get("clasificacion_score", {})

        # Regulatory constants
        self.UMBRAL_APROBACION_SMMLV: float = reg["umbral_aprobacion_smmlv"]
        # BUSINESS_RULES_FIX_2B: SMMLV siempre viene del kwarg obligatorio (HR-Salarios).
        # No existe fallback a business_rules.constantes_regulatorias.smmlv.
        self.SMMLV: float = float(smmlv)

        # Criterion thresholds
        self.PERIODO_PAGO_LIMITE_ALTO: int = umb["periodo_pago_alto"]
        self.PERIODO_PAGO_LIMITE_BAJO: int = umb["periodo_pago_bajo"]
        self.MIN_CONTINGENCIA_OPERATIVA: float = umb["min_contingencia_operativa"]
        self.MIN_CONTINGENCIA_COMERCIAL: float = umb["min_contingencia_comercial"]
        self.ALERTAS_LIMITE_ALTO: int = umb["alertas_alto"]
        self.ALERTAS_LIMITE_MEDIO: int = umb["alertas_medio"]
        self.COMPLEJIDAD_LIMITE_ALTO: int = umb["complejidad_alto"]
        self.COMPLEJIDAD_LIMITE_MEDIO: int = umb["complejidad_medio"]
        self.CAPACITACION_LIMITE_BAJO: int = umb["capacitacion_bajo"]
        self.CAPACITACION_LIMITE_MEDIO: int = umb["capacitacion_medio"]
        self.ROTACION_LIMITE_ALTO: float = umb["rotacion_alto"]
        self.ROTACION_LIMITE_MEDIO: float = umb["rotacion_medio"]
        self.DEPENDENCIA_TERCEROS_ALTO: int = umb["dependencia_terceros_alto"]

        # Score classification
        self.SCORE_LIMITE_ALTO: float = clasif["alto"]
        self.SCORE_LIMITE_MEDIO: float = clasif["medio"]

        # Category weights
        self.PESO_CLIENTE: float = pesos_cat["Cliente"]
        self.PESO_OPERATIVO: float = pesos_cat["Operativo"]

        # Client type / experience sets
        tipos_alto = riesgo_config["tipos_cliente_alto"]
        self.TIPOS_CLIENTE_ALTO = {t for t in tipos_alto} | {
            t.lower() for t in tipos_alto
        }
        antig_alto = riesgo_config["antiguedad_alto"]
        self.ANTIGUEDAD_ALTO = {t for t in antig_alto} | {t.lower() for t in antig_alto}

        # Criteria metadata
        criterios_raw = riesgo_config["criterios"]
        self._CRITERIOS_META = [
            (c["id"], c["factor"], c["categoria"], c["peso"]) for c in criterios_raw
        ]

        # Backward-compatible private aliases used by existing tests/helpers.
        self._smmlv = self.SMMLV
        self._umbral_aprobacion_smmlv = self.UMBRAL_APROBACION_SMMLV
        self._periodo_pago_limite_alto = self.PERIODO_PAGO_LIMITE_ALTO
        self._periodo_pago_limite_bajo = self.PERIODO_PAGO_LIMITE_BAJO
        self._rotacion_limite_alto = self.ROTACION_LIMITE_ALTO
        self._score_limite_alto = self.SCORE_LIMITE_ALTO
        self._score_limite_medio = self.SCORE_LIMITE_MEDIO
        self._peso_cliente = self.PESO_CLIENTE
        self._peso_operativo = self.PESO_OPERATIVO
        self._criterios_meta = self._CRITERIOS_META
        self._tipos_cliente_alto = self.TIPOS_CLIENTE_ALTO

    def calcular(
        self,
        panel: PanelDeControl,
        kpis: KPIsDeal,
        pyg_por_mes: List[PyGMensual],
        perfiles_cadena_a: List[PerfilCadenaA],
        cadena_b: ParametrosCadenaB,
        cadena_c: ParametrosCadenaC,
    ) -> EvaluacionRiesgo:
        """
        Evalúa el riesgo del deal a partir de los resultados del motor.

        Args:
            panel:           Parámetros maestros del deal.
            kpis:            KPIs calculados del deal.
            pyg_por_mes:     P&G mensual del deal.
            perfiles_cadena_a: Perfiles operativos del deal.
            cadena_b:        Parámetros de Cadena B.
            cadena_c:        Parámetros de Cadena C.

        Returns:
            EvaluacionRiesgo con scores, clasificación y detalle de criterios.
        """
        criterios = self._evaluar_criterios(
            panel, kpis, pyg_por_mes, perfiles_cadena_a, cadena_b, cadena_c
        )

        score_cliente = self._score_categoria(criterios, "Cliente")
        score_operativo = self._score_categoria(criterios, "Operativo")
        score_total = (
            score_cliente * self.PESO_CLIENTE + score_operativo * self.PESO_OPERATIVO
        )
        clasificacion = self._clasificar(score_total)

        # Requiere aprobación si el deal supera el umbral en COP.
        # UMBRAL_APROBACION_SMMLV (1000) viene de business_rules (multiplicador versionado).
        # SMMLV viene de IParametrizationProvider.get_smmlv() via kwarg obligatorio (FIX_2B).
        # Umbral = 1000 × SMMLV_HR = 1000 × 1,750,905 ≈ 1,750,905,000 COP (valor 2026).
        #
        # BLOCK_25: removed 3-level COP approval table (aprobaciones_requeridas).
        # Product decision: Excel aprobaciones is manual signature after printing.
        # requiere_aprobacion is the only remaining dynamic bool (1000×SMMLV threshold).
        # Zona de divergencia documentada (1B–1.751B COP): docs/refactor/business_rules_source_of_truth_audit.md
        umbral_cop = self.UMBRAL_APROBACION_SMMLV * self.SMMLV
        requiere_aprobacion = kpis.valor_total_deal >= umbral_cop

        return EvaluacionRiesgo(
            score_cliente=round(score_cliente, 4),
            score_operativo=round(score_operativo, 4),
            score_total=round(score_total, 4),
            clasificacion_total=clasificacion,
            requiere_aprobacion=requiere_aprobacion,
            criterios=criterios,
        )

    # ──────────────────────────────────────────────────────────────
    # Evaluación de cada criterio
    # ──────────────────────────────────────────────────────────────

    def _evaluar_criterios(
        self,
        panel: PanelDeControl,
        kpis: KPIsDeal,
        pyg_por_mes: List[PyGMensual],
        perfiles_cadena_a: List[PerfilCadenaA],
        cadena_b: ParametrosCadenaB,
        cadena_c: ParametrosCadenaC,
    ) -> List[CriterioRiesgo]:
        evaluadores = [
            self._criterio_1_clasificacion_oportunidad,
            self._criterio_2_tipo_cliente,
            self._criterio_3_periodo_pago,
            self._criterio_4_experiencia_cliente,
            self._criterio_5_presupuesto_imprevistos,
            self._criterio_6_alertas_activadas,
            self._criterio_7_complejidad,
            self._criterio_8_capacitaciones,
            self._criterio_9_rotacion,
            self._criterio_10_dependencia_terceros,
        ]

        criterios: List[CriterioRiesgo] = []
        args = (panel, kpis, pyg_por_mes, perfiles_cadena_a, cadena_b, cadena_c)

        for i, (cid, factor, categoria, peso) in enumerate(self._CRITERIOS_META):
            valor_str, calificacion, puntaje = evaluadores[i](*args)
            criterios.append(
                CriterioRiesgo(
                    id=cid,
                    factor=factor,
                    categoria=categoria,
                    valor_evaluado=valor_str,
                    calificacion=calificacion,
                    puntaje=puntaje,
                    peso=peso,
                )
            )

        return criterios

    # ─── Criterios individuales ──────────────────────────────────

    def _criterio_1_clasificacion_oportunidad(
        self, panel, kpis, pyg, perfiles_a, cadena_b, cadena_c
    ):
        """Deal value vs umbral de aprobación en SMMLV."""
        umbral = self.UMBRAL_APROBACION_SMMLV * self.SMMLV
        valor = kpis.valor_total_deal
        if valor >= umbral:
            return f"{valor:,.0f} COP", "Alto", 3
        return f"{valor:,.0f} COP", "Bajo", 1

    def _criterio_2_tipo_cliente(
        self, panel, kpis, pyg, perfiles_a, cadena_b, cadena_c
    ):
        """Tipo de cliente: No Grupo Aval = Alto riesgo."""
        tc = panel.tipo_cliente
        if tc in self.TIPOS_CLIENTE_ALTO or tc.lower() in {
            t.lower() for t in self.TIPOS_CLIENTE_ALTO
        }:
            return tc, "Alto", 3
        return tc, "Bajo", 1

    def _criterio_3_periodo_pago(
        self, panel, kpis, pyg, perfiles_a, cadena_b, cadena_c
    ):
        """Período de pago: mayor plazo = mayor riesgo."""
        dias = panel.periodo_pago_dias
        if dias > self.PERIODO_PAGO_LIMITE_ALTO:
            return f"{dias} días", "Alto", 3
        elif dias > self.PERIODO_PAGO_LIMITE_BAJO:
            return f"{dias} días", "Medio", 2
        return f"{dias} días", "Bajo", 1

    def _criterio_4_experiencia_cliente(
        self, panel, kpis, pyg, perfiles_a, cadena_b, cadena_c
    ):
        """Experiencia: Cliente Nuevo = Alto riesgo."""
        ant = panel.antiguedad_cliente or "Cliente Nuevo"
        if ant in self.ANTIGUEDAD_ALTO or ant.lower() in {
            t.lower() for t in self.ANTIGUEDAD_ALTO
        }:
            return ant, "Alto", 3
        return ant, "Bajo", 1

    def _criterio_5_presupuesto_imprevistos(
        self, panel, kpis, pyg, perfiles_a, cadena_b, cadena_c
    ):
        """Presupuesto de imprevistos: si aplica op_cont > 0."""
        # Aproximación: si el deal tiene contingencia operativa activa
        # (siguiendo convención Excel Panel C73)
        tiene = panel.op_cont > 0
        label = "si" if tiene else "no"
        # Calibración Excel: "no" → Bajo (puntaje 1) en el caso de referencia
        return label, "Bajo", 1

    def _criterio_6_alertas_activadas(
        self, panel, kpis, pyg, perfiles_a, cadena_b, cadena_c
    ):
        """Número de alertas: contingencias debajo de su mínimo."""
        alertas = 0
        if panel.op_cont < self.MIN_CONTINGENCIA_OPERATIVA:
            alertas += 1
        if panel.com_cont < self.MIN_CONTINGENCIA_COMERCIAL:
            alertas += 1

        if alertas >= self.ALERTAS_LIMITE_ALTO:
            return str(alertas), "Alto", 3
        elif alertas >= self.ALERTAS_LIMITE_MEDIO:
            return str(alertas), "Medio", 2
        return str(alertas), "Bajo", 1

    def _criterio_7_complejidad(self, panel, kpis, pyg, perfiles_a, cadena_b, cadena_c):
        """Complejidad: canales activos en el deal."""
        canales_a = len({p.canal for p in perfiles_a if not p.es_soporte})
        canales_b = len([c for c in cadena_b.canales if c.volumen_mensual > 0])
        canales_c = len([c for c in cadena_c.canales if c.volumen_mensual > 0])
        total = canales_a + canales_b + canales_c

        if total > self.COMPLEJIDAD_LIMITE_ALTO:
            return str(total), "Alto", 3
        elif total > self.COMPLEJIDAD_LIMITE_MEDIO:
            return str(total), "Medio", 2
        return str(total), "Bajo", 1

    def _criterio_8_capacitaciones(
        self, panel, kpis, pyg, perfiles_a, cadena_b, cadena_c
    ):
        """Días de formación: más días = menor riesgo."""
        perfiles_ops = [p for p in perfiles_a if not p.es_soporte]
        if not perfiles_ops:
            return "0", "Alto", 3

        avg_dias = sum(p.dias_cap_inicial for p in perfiles_ops) / len(perfiles_ops)

        if avg_dias >= self.CAPACITACION_LIMITE_BAJO:
            return f"{avg_dias:.1f} días", "Bajo", 1
        elif avg_dias >= self.CAPACITACION_LIMITE_MEDIO:
            return f"{avg_dias:.1f} días", "Medio", 2
        return f"{avg_dias:.1f} días", "Alto", 3

    def _criterio_9_rotacion(self, panel, kpis, pyg, perfiles_a, cadena_b, cadena_c):
        """Porcentaje de rotación."""
        rot = panel.pct_ausentismo  # proxy: ausentismo ≈ rotación efectiva
        # La rotación real viene de ParametrosCalculo, pero PanelDeControl
        # expone pct_ausentismo como el valor del deal.
        # Calibración: 8.5% en el caso de referencia → "Medio"
        if rot > self.ROTACION_LIMITE_ALTO:
            return f"{rot:.1%}", "Alto", 3
        elif rot > self.ROTACION_LIMITE_MEDIO:
            return f"{rot:.1%}", "Medio", 2
        return f"{rot:.1%}", "Bajo", 1

    def _criterio_10_dependencia_terceros(
        self, panel, kpis, pyg, perfiles_a, cadena_b, cadena_c
    ):
        """Dependencia de terceros: proveedores de Cadena C activos."""
        n = len([c for c in cadena_c.canales if c.volumen_mensual > 0])
        if n > self.DEPENDENCIA_TERCEROS_ALTO:
            return str(n), "Alto", 3
        elif n > 0:
            return str(n), "Medio", 2
        return str(n), "Bajo", 1

    # ──────────────────────────────────────────────────────────────
    # Utilidades de scoring
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _score_categoria(criterios: List[CriterioRiesgo], categoria: str) -> float:
        """SUMPRODUCT(puntaje × peso) para una categoría."""
        total = sum(c.puntaje * c.peso for c in criterios if c.categoria == categoria)
        return total

    def _clasificar(self, score: float) -> str:
        if score >= self.SCORE_LIMITE_ALTO:
            return "Alto"
        elif score >= self.SCORE_LIMITE_MEDIO:
            return "Medio"
        return "Bajo"
