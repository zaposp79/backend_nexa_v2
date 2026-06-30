"""
nexa_engine/modules/calculator/serializers/serializer_helpers.py
===============================================================
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


# ---------------------------------------------------------------------------
# Helpers por tipo
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Serialization helpers (extracted from serializer.py, FASE Z4g)
# ---------------------------------------------------------------------------

def _pyg_to_dict(p: PyGMensual) -> Dict[str, Any]:
    """Serializa PyGMensual incluyendo todas sus propiedades calculadas.

    H-09 FIX: Ensure all @property methods are exposed in JSON output.
    """
    d: Dict[str, Any] = asdict(p)
    # Agrega propiedades (@property) que asdict() omite
    d["ingreso_bruto"]     = p.ingreso_bruto
    d["ingreso_neto"]      = p.ingreso_neto
    d["costo_a"]           = p.costo_a
    d["costo_operativo"]   = p.costo_operativo  # H-09: Was missing
    d["costos_financieros"] = p.costos_financieros
    d["componente_financiero"] = p.componente_financiero  # H-09: Was missing
    d["polizas_por_cadena"] = {
        "cadena_a": p.polizas_a,
        "cadena_b": p.polizas_b,
        "cadena_c": p.polizas_c,
    }
    d["costo_total"]       = p.costo_total
    d["contribucion"]      = p.contribucion
    d["pct_contribucion"]  = p.pct_contribucion
    d["utilidad_neta"]     = p.utilidad_neta
    d["pct_utilidad_neta"] = p.pct_utilidad_neta
    # Acumulados are stored fields — already in asdict(). Verify presence.
    return d


def _desglose_cts_to_dict(d: DesgloseCTSCadenaA) -> Dict[str, Any]:
    raw: Dict[str, Any] = asdict(d)
    raw["total"] = d.total
    return raw


def _desglose_cts_b_to_dict(d: DesgloseCTSCadenaB) -> Dict[str, Any]:
    """Serializa DesgloseCTSCadenaB incluyendo la property total."""
    raw: Dict[str, Any] = asdict(d)
    raw["total"] = d.total
    return raw


def _cost_to_serve_to_dict(cts: ResultadoCostToServe) -> Dict[str, Any]:
    raw: Dict[str, Any] = asdict(cts)
    # Reemplaza desglose_a con versión que incluye su property total
    raw["desglose_a"] = _desglose_cts_to_dict(cts.desglose_a)
    # Reemplaza desglose_b con versión que incluye su property total
    raw["desglose_b"] = _desglose_cts_b_to_dict(cts.desglose_b)
    return raw


def _vision_tarifas_to_dict(vt: ResultadoVisionTarifas) -> Dict[str, Any]:
    """
    Serializa Vision Tarifas con canales filtrados a campos de la hoja VT del Excel.

    TarifaCanal tiene 35 campos pero la hoja Vision Tarifas solo muestra ~18.
    Los sub-componentes de payroll (nomina_loaded_ch, salario_fijo_ch, capacitacion_inicial_ch,
    etc.) y no-payroll (opex_it_ch, inversiones_ch, costos_fijos_ch) pertenecen a
    la hoja Vision Cost To Serve, no a Vision Tarifas.
    """
    # Campos de TarifaCanal visibles en la hoja Vision Tarifas del Excel (rows 10-21)
    # Resumen Resultado Escenarios: modalidad, canal, modelo_cobro, componentes, tarifas
    # Excluidos: sub-componentes de costo (payroll_ch, no_payroll_ch, etc.) → pertenecen a CTS
    # Excluidos: tarifa_hora_loggeada/pagada → están en escenarios_detalle.tarifas
    # Excluidos: vol_minimo_transaccion → está en escenarios_detalle.tarifas
    _VT_CANAL_FIELDS = {
        "nombre_canal", "modalidad", "producto", "fte", "vol_mensual",
        "modelo_cobro", "pct_fijo", "pct_variable",
        "componente_fijo", "componente_variable",
        "costo_atribuible", "ingreso_bruto", "facturacion",
        "tarifa_fijo_fte", "tarifa_variable",
    }
    raw = asdict(vt)
    raw["canales"] = [
        {k: v for k, v in canal.items() if k in _VT_CANAL_FIELDS}
        for canal in raw.get("canales", [])
    ]
    return raw


# FORMULA_OWNERSHIP_2: _ficha_deal_to_dict pertenece a modules/vision_imprimible.
from nexa_engine.modules.vision_imprimible.helpers.ficha import (
    ficha_deal_to_dict as _ficha_deal_to_dict_vi,
)


def _ficha_deal_to_dict(panel: PanelDeControl) -> Dict[str, Any]:
    """Delegación al helper canónico en modules/vision_imprimible/helpers/ficha.py.

    FORMULA_OWNERSHIP_2: la lógica de ficha del deal (VI sección 01) vive en
    modules/vision_imprimible, no en el serializer.
    """
    return _ficha_deal_to_dict_vi(panel)


# FORMULA_OWNERSHIP_4: F-02 pertenece a modules/vision_imprimible.
from nexa_engine.modules.vision_imprimible.helpers.reglas_negocio import (
    reglas_negocio_to_dict as _reglas_negocio_to_dict_vi,
)


def _reglas_negocio_to_dict(
    reglas: List[ReglaNegocios],
    resultado: "PricingResult",
) -> Dict[str, Any]:
    """Delegación al helper canónico en modules/vision_imprimible/helpers/reglas_negocio.py."""
    return _reglas_negocio_to_dict_vi(reglas, resultado)


def _reglas_negocio_to_list(reglas: List[ReglaNegocios]) -> list:
    """
    Serializa la lista de reglas de negocio (backward-compat — solo la lista).
    Fuente: Sección 07 (Contingencias) de la Visión Imprimible.
    """
    return [asdict(r) for r in reglas]


def _waterfall_to_dict(wf: Optional[WaterfallPromedio]) -> Optional[Dict[str, Any]]:
    if wf is None:
        return None
    return asdict(wf)


def _vision_pyg_to_dict(vp: Optional[VisionPyG]) -> Optional[Dict[str, Any]]:
    """
    Serializa VisionPyG con estructura jerárquica por secciones.

    Produce `secciones`: array ordenado donde cada sección agrupa sus filas,
    y cada fila lleva su `detalle` anidado (sub-componentes de filas_detalle).

    Estructura:
      resumen: {...}
      secciones: [
        { key, label, filas: [
            { key, label, tipo, signo, excel_row, formula, valores, acumulado, promedio,
              detalle: [ { key, label, ... } ]
            }
        ]}
      ]
      puestos_trabajo: float
      fechas_meses: [str]
      meses_contrato: int
      meses_activos: int
    """
    if vp is None:
        return None

    # Index filas_detalle by parent key
    detalle_por_parent: Dict[str, list] = {}
    for fd in (vp.filas_detalle or []):
        parent = fd.parent
        if parent not in detalle_por_parent:
            detalle_por_parent[parent] = []
        detalle_por_parent[parent].append(asdict(fd))

    # Section definitions — order matches Excel layout
    _SECTION_META = [
        ("ingresos",   "Ingresos"),
        ("costos_op",  "Costos Operativos"),
        ("costos_fin", "Componente Financiero"),
        ("resultados", "Resultados"),
        ("operativo",  "Operativo"),
    ]

    secciones = []
    for sec_key, sec_label in _SECTION_META:
        filas_seccion = []
        for fila in (vp.filas or []):
            if fila.seccion != sec_key:
                continue
            fila_dict = asdict(fila)
            fila_dict["detalle"] = detalle_por_parent.get(fila.key, [])
            filas_seccion.append(fila_dict)
        if filas_seccion:
            secciones.append({
                "key": sec_key,
                "label": sec_label,
                "filas": filas_seccion,
            })

    return {
        "resumen":         asdict(vp.resumen),
        "secciones":       secciones,
        "puestos_trabajo": vp.puestos_trabajo,
        "fechas_meses":    vp.fechas_meses,
        "meses_contrato":  vp.meses_contrato,
        "meses_activos":   vp.meses_activos,
    }


def _evaluacion_riesgo_to_dict(
    ev: Optional[EvaluacionRiesgo],
    *,
    valor_total_deal: float = 0.0,
    meses_contrato: int = 0,
) -> Optional[Dict[str, Any]]:
    """Serializa la evaluación de riesgo — Sección 06 (Control de Riesgo) de la Visión Imprimible.

    Retorna None cuando la evaluación no fue calculada — no se sustituye por ceros.

    Agrega:
    - `riesgo_actual` en cada criterio (alias de `calificacion` — columna visual).

    Nota: `requiere_aprobacion` (bool) se conserva como campo legacy/no-canónico para
    Visión Imprimible — calculado por RiesgoCalculator con umbral 1000×SMMLV.
    """
    if ev is None:
        return None
    raw = asdict(ev)
    # Enriquecer criterios con riesgo_actual (alias de calificacion — columna visual)
    for c in raw.get("criterios", []):
        c["riesgo_actual"] = c.get("calificacion", "")
    return raw


def _vision_ejecutiva_sections(resultado: PricingResult) -> Dict[str, Any]:
    """
    Secciones de la Visión Ejecutiva Integral derivadas de resultado.vision_imprimible.

    TODAS las secciones se emiten SIEMPRE — con valores en cero o listas vacías
    cuando no hay datos, en lugar de omitirlas. El frontend necesita las claves
    presentes para renderizar las secciones del dashboard (incluso en cero).
    """
    vi = getattr(resultado, "vision_imprimible", None)
    if vi is None:
        return {
            "vision_por_servicio": [],
            "vision_por_canal": [],
            "detalle_por_canal": [],
            "estructura_equipo": None,
            "comparativo_escenarios": [],
        }
    return {
        "vision_por_servicio": [asdict(s) for s in (vi.vision_por_servicio or [])],
        "vision_por_canal": [asdict(c) for c in (vi.vision_por_canal or [])],
        "detalle_por_canal": [asdict(c) for c in (vi.detalle_por_canal or [])],
        "estructura_equipo": asdict(vi.estructura_equipo) if vi.estructura_equipo else None,
        # GAP-VIS-1 cerrado: Sección 05 Comparativo de Escenarios (Excel VI rows 73-78)
        "comparativo_escenarios": [asdict(e) for e in (vi.comparativo_escenarios or [])],
    }


# FORMULA_OWNERSHIP_3: F-03+F-04 pertenecen a modules/vision_imprimible.
from nexa_engine.modules.vision_imprimible.helpers.configuracion_comercial import (
    select_principal_channel as _select_principal_channel_vi,
    configuracion_comercial_to_dict as _configuracion_comercial_vi,
)


def _select_principal_channel(canales: "List") -> "Any":  # type: ignore[name-defined]
    """Delegación al helper canónico en modules/vision_imprimible/helpers/configuracion_comercial.py."""
    return _select_principal_channel_vi(canales)


def _configuracion_comercial(resultado: "PricingResult") -> "Dict[str, Any]":  # type: ignore[name-defined]
    """Delegación al helper canónico en modules/vision_imprimible/helpers/configuracion_comercial.py."""
    return _configuracion_comercial_vi(resultado)


def _polizas_por_cadena(resultado: "PricingResult") -> "Dict[str, float]":  # type: ignore[name-defined]
    pyg = resultado.pyg_por_mes or []
    if not pyg:
        return {"cadena_a": 0.0, "cadena_b": 0.0, "cadena_c": 0.0}
    return {
        "cadena_a": sum(p.polizas_a for p in pyg),
        "cadena_b": sum(p.polizas_b for p in pyg),
        "cadena_c": sum(p.polizas_c for p in pyg),
    }


# ---------------------------------------------------------------------------

__all__ = [
    "_pyg_to_dict",
    "_desglose_cts_to_dict",
    "_desglose_cts_b_to_dict",
    "_cost_to_serve_to_dict",
    "_vision_tarifas_to_dict",
    "_ficha_deal_to_dict",
    "_reglas_negocio_to_dict",
    "_reglas_negocio_to_list",
    "_waterfall_to_dict",
    "_vision_pyg_to_dict",
    "_evaluacion_riesgo_to_dict",
    "_vision_ejecutiva_sections",
    "_polizas_por_cadena",
    "_select_principal_channel",
    "_configuracion_comercial",
]
