"""
nexa_engine/modules/calculator/serializers/pricing_result_serializer.py
====================================================================
Convierte PricingResult (dataclasses con @property) a dicts JSON-serializables.

Problema
--------
`dataclasses.asdict()` serializa todos los campos almacenados de un dataclass,
pero omite completamente los `@property` (derivados). PyGMensual tiene 9 propiedades
clave que el cliente necesita (ingreso_bruto, ingreso_neto, costo_total, etc.) que
no son campos almacenados. Este módulo los captura explícitamente.

Uso
---
    from nexa_engine.modules.calculator_motor.serializers import pricing_result_to_dict

    data = pricing_result_to_dict(resultado, result_id="uuid-...")
    # → dict listo para JSON / almacenamiento
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from nexa_engine.modules.shared.models import (
    DesgloseCTSCadenaA,
    DesgloseCTSCadenaB,
    EvaluacionRiesgo,
    PanelDeControl,
    PricingResult,
    PyGMensual,
    ReglaNegocios,
    ResultadoCostToServe,
    ResultadoVisionTarifas,
    VisionPyG,
    WaterfallPromedio,
)

from nexa_engine.modules.calculator_motor.serializers.serializer_helpers import (  # noqa: F401
    _pyg_to_dict,
    _desglose_cts_to_dict,
    _desglose_cts_b_to_dict,
    _cost_to_serve_to_dict,
    _vision_tarifas_to_dict,
    _ficha_deal_to_dict,
    _reglas_negocio_to_dict,
    _reglas_negocio_to_list,
    _waterfall_to_dict,
    _vision_pyg_to_dict,
    _evaluacion_riesgo_to_dict,
    _vision_ejecutiva_sections,
    _polizas_por_cadena,
    _select_principal_channel,
    _configuracion_comercial,
)

# Serializador principal
# ---------------------------------------------------------------------------

def pricing_result_to_dict(resultado: PricingResult, result_id: str, scenario: str = "base") -> Dict[str, Any]:
    """
    Convierte un PricingResult completo a un dict JSON-serializable.

    Captura explícitamente todos los campos almacenados Y las propiedades
    calculadas (@property) de cada dataclass del resultado.

    El dict resultante es el contrato JSON completo de la Visión Imprimible.
    Contiene todos los datos que el frontend necesita para renderizar la hoja
    sin recalcular ninguna fórmula.

    Arquitectura de visiones:
      Las cuatro visiones oficiales están embebidas en este documento:
        - Vision Imprimible  : el documento completo (este dict)
        - Vision P&G         : clave "vision_pyg"  (VisionPyG estructurado)
        - Vision Tarifas     : clave "vision_tarifas" (ResultadoVisionTarifas)
        - Vision Cost To Serve: clave "cost_to_serve"  (ResultadoCostToServe)

      Campos internos expuestos SOLO dentro de la Visión Imprimible:
        - "kpis"       : sección 02 del composite; producido por KPIsCalculator
                         (servicio interno). NO disponible como endpoint autónomo.
        - "pyg_por_mes": datos mensuales crudos; fuente de gráficos de evolución
                         y del waterfall. NO disponible como endpoint autónomo.
                         La representación oficial al frontend es "vision_pyg".

    Args:
        resultado:  Resultado del motor de precios.
        result_id:  UUID de la ejecución (asignado por el almacenamiento).
        scenario:   Identificador del escenario ("base", "optimista", "conservador", "agresivo").
                    H-12 FIX: Required for multi-scenario support (TASK 5).

    Returns:
        dict con: simulation_id, calculated_at, ficha_deal, kpis (sección 02),
                  pyg_por_mes (fuente interna), waterfall_promedio, configuracion_comercial,
                  reglas_negocio, evaluacion_riesgo, vision_pyg, cost_to_serve,
                  vision_tarifas, panel.
    """
    panel = resultado.panel

    # Configuración comercial — resumen de vision_tarifas + panel
    config_comercial = _configuracion_comercial(resultado)

    return {
        "simulation_id": result_id,
        "scenario": scenario,  # H-12: Multi-scenario support (TASK 5)
        "calculated_at": datetime.now(timezone.utc).isoformat(),

        # ── Visión Ejecutiva Integral: servicio / canal / equipo ───
        **_vision_ejecutiva_sections(resultado),

        # ── Sección 01: Ficha del deal ─────────────────────────────
        "ficha_deal": _ficha_deal_to_dict(panel),

        # ── Sección 02: Economics KPIs ──────────────────────────────
        "kpis": asdict(resultado.kpis),

        # ── P&G mensual (fuente: todos los gráficos de evolución) ───
        "pyg_por_mes": [_pyg_to_dict(p) for p in resultado.pyg_por_mes],

        # ── Sección 04: Waterfall promedio (fuente del gráfico) ─────
        "waterfall_promedio": _waterfall_to_dict(resultado.waterfall),

        # ── Sección 03: Configuración comercial ─────────────────────
        "configuracion_comercial": config_comercial,

        # ── Sección 07: Reglas de negocio / Contingencias ───────────
        "reglas_negocio": _reglas_negocio_to_dict(resultado.reglas_negocio, resultado),

        # ── Sección 06: Evaluación de riesgo ────────────────────────
        "evaluacion_riesgo": _evaluacion_riesgo_to_dict(
            resultado.evaluacion_riesgo,
            valor_total_deal=resultado.kpis.valor_total_deal,
            meses_contrato=resultado.panel.meses_contrato,
        ),

        # ── Vision P&G (structured frontend model) ────────────────────
        "vision_pyg": _vision_pyg_to_dict(resultado.vision_pyg),

        # ── Cost to Serve y Visión Tarifas ───────────────────────────
        "cost_to_serve": (
            _cost_to_serve_to_dict(resultado.cost_to_serve)
            if resultado.cost_to_serve else None
        ),
        "vision_tarifas": (
            _vision_tarifas_to_dict(resultado.vision_tarifas)
            if resultado.vision_tarifas else None
        ),

        # ── Panel completo (inputs del deal) ────────────────────────
        "panel": asdict(panel),
        "polizas": _polizas_por_cadena(resultado),

        # ── FASE 5: Datasets de visión (staffing, pólizas, indexación, volumetría) ──
        # None si el builder no los produjo (backward compat garantizado)
        "datasets_vision": (
            resultado.datasets_vision.as_dict()
            if getattr(resultado, "datasets_vision", None) else None
        ),

        # ── FASE 7: Audit trail financiero ──────────────────────────────────────────
        # Cada valor financiero con fórmula, inputs y fuente documentados
        "audit_trace": getattr(resultado, "audit_trace", None),
    }


# ---------------------------------------------------------------------------
# Validación de completitud de visiones
# ---------------------------------------------------------------------------

class VisionIncompleteError(Exception):
    """
    Se lanza cuando una o más visiones están ausentes o con datos incompletos
    tras la ejecución del pipeline de cálculo.

    Indica una rotura en la cadena de cálculo, no un error de entrada.
    Cada item de `issues` identifica exactamente qué visión o campo falló
    y qué calculadora debería haberlo producido.
    """

    def __init__(self, issues: List[str]) -> None:
        self.issues = issues
        super().__init__(
            f"VISION_INCOMPLETE — {len(issues)} problema(s) detectado(s):\n"
            + "\n".join(f"  · {i}" for i in issues)
        )


def validate_visions_complete(resultado: PricingResult) -> None:
    """
    Verifica que todas las visiones oficiales fueron construidas correctamente.

    Validaciones:
      1. Las 4 visiones oficiales están presentes (no None, no vacías).
      2. P&G mensual existe y tiene valores no triviales (Capas 2–9 ejecutaron).
      3. KPIsCalculator ejecutó — verificado indirectamente desde campos de
         visiones dependientes (ingreso_mensual, valor_total_deal).
      4. No existen arrays vacíos ni None en posiciones críticas.

    Raises:
        VisionIncompleteError: con la lista completa de problemas detectados.
    """
    issues: List[str] = []
    cadenas = getattr(resultado.panel, "cadenas_activas", None)
    cadena_a_active = bool(getattr(cadenas, "cadena_a", True))

    # ── P&G mensual — indica que PyGCalculator (Capa 9) ejecutó ───────────
    if not resultado.pyg_por_mes:
        issues.append(
            "pyg_por_mes vacío — PyGCalculator no ejecutó"
        )
    elif cadena_a_active and resultado.pyg_por_mes[0].payroll_a <= 0:
        issues.append(
            f"pyg_por_mes[0].payroll_a={resultado.pyg_por_mes[0].payroll_a:.2f} "
            f"— nómina Capa 2 es cero; verificar perfiles Cadena A"
        )

    # ── KPIs — validación indirecta de KPIsCalculator (Capa 10) ──────────
    kpis = resultado.kpis
    if kpis is None:
        issues.append("kpis es None — KPIsCalculator no ejecutó")
    else:
        if kpis.ingreso_mensual <= 0:
            issues.append(
                f"kpis.ingreso_mensual={kpis.ingreso_mensual:.2f} (esperado > 0); "
                f"verificar factor_márgenes y costos_totales"
            )
        if kpis.valor_total_deal <= 0:
            issues.append(
                f"kpis.valor_total_deal={kpis.valor_total_deal:.2f} (esperado > 0)"
            )

    # ── Waterfall — promedios mensuales del P&G ───────────────────────────
    if resultado.waterfall is None:
        issues.append(
            "waterfall es None — no se generaron promedios mensuales"
        )

    # ── Evaluación de riesgo ───────────────────────────────────────────────
    if resultado.evaluacion_riesgo is None:
        issues.append("evaluacion_riesgo es None — RiesgoCalculator no ejecutó")
    elif not resultado.evaluacion_riesgo.criterios:
        issues.append(
            "evaluacion_riesgo.criterios vacío — se esperan 10 criterios"
        )

    # ── Reglas de negocio ─────────────────────────────────────────────────
    if not resultado.reglas_negocio:
        issues.append(
            "reglas_negocio vacío — verificar business_rules en parametrización"
        )

    # ── Vision Tarifas_Modelo_Cobro ───────────────────────────────────────
    if resultado.vision_tarifas is None:
        issues.append(
            "vision_tarifas es None — VisionTarifasCalculator no ejecutó"
        )
    elif cadena_a_active and not resultado.vision_tarifas.canales:
        issues.append(
            "vision_tarifas.canales vacío — sin canales procesados; "
            "verificar condiciones_cadena_a.perfiles[]"
        )

    # ── Vision P&G ────────────────────────────────────────────────────────
    if resultado.vision_pyg is None:
        issues.append("vision_pyg es None — VisionPyGBuilder no ejecutó")
    elif not resultado.vision_pyg.filas:
        issues.append(
            "vision_pyg.filas vacío — filas P&G no generadas"
        )

    # ── Vision Cost To Serve ──────────────────────────────────────────────
    if resultado.cost_to_serve is None:
        issues.append(
            "cost_to_serve es None — CostToServeCalculator no ejecutó"
        )

    if issues:
        raise VisionIncompleteError(issues)


def _build_execution_trace(resultado: PricingResult) -> Dict[str, Any]:
    """
    Construye la traza de ejecución del pipeline de cálculo.

    Inferida desde los campos de PricingResult — no requiere instrumentación
    adicional en las calculadoras. Útil para auditoría en Fases 10-11.

    ADVERTENCIA: Solo incluir en respuesta cuando DEBUG_TRACE_CALCULATIONS=true.
    NO exponer en producción.
    """
    vt = resultado.vision_tarifas
    vp = resultado.vision_pyg
    er = resultado.evaluacion_riesgo

    visions_missing = []
    if vt is None:                      visions_missing.append("vision_tarifas")
    if vp is None:                      visions_missing.append("vision_pyg")
    if resultado.cost_to_serve is None: visions_missing.append("cost_to_serve")
    if resultado.waterfall is None:     visions_missing.append("waterfall")

    return {
        # Calculadoras en orden de ejecución del pipeline
        "calculators_executed": [
            "NominaCalculator",
            "NoPayrollCalculator",
            "CadenaBCalculator",
            "CadenaCCalculator",
            "CostosTotalesCalculator",
            "CostosFinancierosCalculator",
            "PyGCalculator",
            "KPIsCalculator",           # interno — no expuesto como endpoint
            "CostToServeCalculator",
            "VisionTarifasCalculator",
            "VisionPyGBuilder",
            "RiesgoCalculator",
        ],
        # Métricas de escala del cálculo
        "months_processed":          len(resultado.pyg_por_mes),
        "channels_processed":        len(vt.canales) if vt else 0,
        "pyg_rows_generated":        len(vp.filas)   if vp else 0,
        "risk_criteria_evaluated":   len(er.criterios) if er else 0,
        "business_rules_evaluated":  len(resultado.reglas_negocio),
        # Estado de visiones
        "visions_generated":         4 - len(visions_missing),
        "visions_missing":           visions_missing,
    }


def pricing_result_to_visions_response(
    resultado: PricingResult,
    result_id: str,
    include_trace: bool = False,
) -> Dict[str, Any]:
    """
    Construye la respuesta del endpoint POST /calculate.

    Expone únicamente las cuatro visiones oficiales del simulador NEXA,
    equivalentes a las hojas de visiones del Excel V2-4:

      - vision_imprimible          : composite completo (9 secciones de datos)
      - vision_tarifas_modelo_cobro: ResultadoVisionTarifas por canal
      - vision_pyg                 : VisionPyG estructurado por secciones/filas
      - vision_cost_to_serve       : CTS con desgloses por cadena

    La Visión Imprimible no incluye metadatos de ejecución (result_id,
    calculated_at) ni el panel de inputs crudos — solo las secciones de datos.

    Precondición: validate_visions_complete(resultado) ya fue llamado.

    Args:
        resultado:     PricingResult validado por el motor.
        result_id:     UUID de la ejecución (para recuperar via GET /results).
        include_trace: Si True, incluye execution_trace para auditoría.
                       SOLO activar con DEBUG_TRACE_CALCULATIONS=true.
    """
    panel = resultado.panel
    config_comercial = _configuracion_comercial(resultado)

    # ── Visión Imprimible — 9 secciones de datos (sin metadatos) ──────────
    vision_imprimible: Dict[str, Any] = {
        "ficha_deal":               _ficha_deal_to_dict(panel),           # S01
        "kpis":                     asdict(resultado.kpis),               # S02
        "configuracion_comercial":  config_comercial,                     # S03
        "waterfall_promedio":       _waterfall_to_dict(resultado.waterfall),  # S04
        "vision_pyg":               _vision_pyg_to_dict(resultado.vision_pyg),  # S05
        "evaluacion_riesgo":        _evaluacion_riesgo_to_dict(  # S06
            resultado.evaluacion_riesgo,
            valor_total_deal=resultado.kpis.valor_total_deal,
            meses_contrato=resultado.panel.meses_contrato,
        ),
        "reglas_negocio":           _reglas_negocio_to_dict(resultado.reglas_negocio, resultado),  # S07
        "cost_to_serve":            (                                     # S08
            _cost_to_serve_to_dict(resultado.cost_to_serve)
            if resultado.cost_to_serve else None
        ),
        "vision_tarifas":           (                                     # S09
            _vision_tarifas_to_dict(resultado.vision_tarifas)
            if resultado.vision_tarifas else None
        ),
        # Fuente interna para gráficos de evolución mensual del frontend
        "pyg_por_mes":              [_pyg_to_dict(p) for p in resultado.pyg_por_mes],
    }

    # ── Visión Ejecutiva Integral — secciones agregadas (S10-S13) ─────────
    # Pobladas solo cuando existen datos reales; las opcionales se omiten en
    # lugar de fabricar estructuras vacías. Mismo helper que el documento guardado.
    vision_imprimible.update(_vision_ejecutiva_sections(resultado))

    response: Dict[str, Any] = {
        "simulation_id":               result_id,
        "calculated_at":               datetime.now(timezone.utc).isoformat(),

        # Las cuatro visiones oficiales
        "vision_imprimible":           vision_imprimible,
        "vision_tarifas_modelo_cobro": (
            _vision_tarifas_to_dict(resultado.vision_tarifas)
            if resultado.vision_tarifas else None
        ),
        "vision_pyg":                  _vision_pyg_to_dict(resultado.vision_pyg),
        "vision_cost_to_serve":        (
            _cost_to_serve_to_dict(resultado.cost_to_serve)
            if resultado.cost_to_serve else None
        ),
    }

    if include_trace:
        response["execution_trace"] = _build_execution_trace(resultado)

    return response


# ---------------------------------------------------------------------------
# FASE 4 — SimulationSnapshot serialization
# ---------------------------------------------------------------------------

def build_simulation_snapshot(
    simulation_id: str,
    raw_input: dict,
    normalized_input: dict,
    normalization_log: dict,
    parametrization_snapshot: dict,
    data_provenance: dict,
    pricing_result_dict: dict,
    panel_summary_data: dict,
    created_at: str = "",
) -> "SimulationSnapshot":  # type: ignore[name-defined]
    """
    FASE 4 — Construye un SimulationSnapshot auto-contenido.

    Reúne todos los artefactos del pipeline para crear el snapshot
    que se persiste en storage/snapshots/{simulation_id}/.

    Args:
        simulation_id:          UUID de la simulación
        raw_input:              JSON original del usuario (sin modificar)
        normalized_input:       JSON post-InputNormalizer (FASE 2)
        normalization_log:      NormalizationLog serializado (FASE 2)
        parametrization_snapshot: Snapshot de parametrización activa (FASE 4)
        data_provenance:        DataProvenance.as_dict() (FASE 3)
        pricing_result_dict:    pricing_result_to_dict() completo
        panel_summary_data:     Dict con campos básicos del deal
        created_at:             Timestamp ISO 8601 (default: ahora)

    Returns:
        SimulationSnapshot listo para persistir.
    """
    from datetime import datetime, timezone
    from nexa_engine.modules.calculator_motor.models.snapshot import (
        ParametrizationSnapshot,
        PanelSummary,
        SimulationSnapshot,
    )

    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()

    param = ParametrizationSnapshot(
        parametrization_id      = parametrization_snapshot.get("parametrization_id", ""),
        captured_at             = parametrization_snapshot.get("captured_at", ""),
        smmlv                   = float(parametrization_snapshot.get("smmlv", 0.0)),
        auxilio_transporte      = float(parametrization_snapshot.get("auxilio_transporte", 0.0)),
        linea_negocio           = parametrization_snapshot.get("linea_negocio", ""),
        pct_rotacion_linea      = float(parametrization_snapshot.get("pct_rotacion_linea", 0.0)),
        pct_ausentismo_linea    = float(parametrization_snapshot.get("pct_ausentismo_linea", 0.0)),
        pct_examen_anual_linea  = float(parametrization_snapshot.get("pct_examen_anual_linea", 0.0)),
        ciudad                  = parametrization_snapshot.get("ciudad", ""),
        tasa_ica_ciudad         = float(parametrization_snapshot.get("tasa_ica_ciudad", 0.0)),
        tasa_gmf                = float(parametrization_snapshot.get("tasa_gmf", 0.0)),
        tasa_mensual_financiacion = float(parametrization_snapshot.get("tasa_mensual_financiacion", 0.0)),
        componente_humano       = parametrization_snapshot.get("componente_humano", "IPC"),
        componente_tecnologico  = parametrization_snapshot.get("componente_tecnologico", "IPC"),
        factores_indexacion     = parametrization_snapshot.get("factores_indexacion", {}),
        constantes_operativas   = parametrization_snapshot.get("constantes_operativas", {}),
        salarios_por_rol        = parametrization_snapshot.get("salarios_por_rol", {}),
    )

    summary = PanelSummary(
        simulation_id  = simulation_id,
        cliente        = panel_summary_data.get("cliente", ""),
        tipo_cliente   = panel_summary_data.get("tipo_cliente", ""),
        linea_negocio  = panel_summary_data.get("linea_negocio", ""),
        ciudad         = panel_summary_data.get("ciudad", ""),
        fecha_inicio   = panel_summary_data.get("fecha_inicio", ""),
        meses_contrato = int(panel_summary_data.get("meses_contrato", 0)),
        margen         = float(panel_summary_data.get("margen", 0.0)),
        total_fte      = float(panel_summary_data.get("total_fte", 0.0)),
        created_at     = created_at,
    )

    return SimulationSnapshot(
        simulation_id       = simulation_id,
        created_at          = created_at,
        raw_input           = raw_input,
        normalized_input    = normalized_input,
        normalization_log   = normalization_log,
        parametrization     = param,
        data_provenance     = data_provenance,
        pricing_result      = pricing_result_dict,
        panel_summary       = summary,
    )


__all__ = [
    "VisionIncompleteError",
    "build_simulation_snapshot",
    "pricing_result_to_dict",
    "pricing_result_to_visions_response",
    "validate_visions_complete",
    "_configuracion_comercial",
    "_cost_to_serve_to_dict",
    "_desglose_cts_b_to_dict",
    "_desglose_cts_to_dict",
    "_evaluacion_riesgo_to_dict",
    "_ficha_deal_to_dict",
    "_polizas_por_cadena",
    "_pyg_to_dict",
    "_reglas_negocio_to_dict",
    "_reglas_negocio_to_list",
    "_select_principal_channel",
    "_vision_ejecutiva_sections",
    "_vision_pyg_to_dict",
    "_vision_tarifas_to_dict",
    "_waterfall_to_dict",
]
