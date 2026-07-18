"""Module-level helpers extracted from engine.py (FASE Z4b — >500 LOC split).

These functions are used exclusively by NexaPricingEngine._calcular_pipeline
and are kept in a separate file for readability. Behaviour is unchanged.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from nexa_engine.modules.shared.models import (
    PanelDeControl,
    PyGMensual,
    ReglaNegocios,
    WaterfallPromedio,
)


def _calcular_waterfall(pyg_por_mes: List[PyGMensual]) -> Optional[WaterfallPromedio]:
    """
    Calcula el promedio mensual de cada componente de costo/ingreso.

    Solo considera meses con ingreso_neto > 0 (meses activos).
    Es fuente de datos para el gráfico waterfall de la Visión Imprimible.
    """
    activos = [m for m in pyg_por_mes if m.ingreso_neto > 0]
    n = len(activos)
    if n == 0:
        return None

    def avg(fn) -> float:
        return sum(fn(m) for m in activos) / n

    contingencias = avg(lambda m: m.contingencia_op + m.contingencia_com)
    markup_desc   = avg(lambda m: m.markup_ingreso - m.descuento_ingreso)

    return WaterfallPromedio(
        payroll_a        = avg(lambda m: m.payroll_a),
        no_payroll_a     = avg(lambda m: m.no_payroll_a),
        costo_b          = avg(lambda m: m.costo_b),
        costo_c          = avg(lambda m: m.costo_c),
        financiacion     = avg(lambda m: m.financiacion),
        polizas          = avg(lambda m: m.polizas),
        ica              = avg(lambda m: m.ica),
        gmf              = avg(lambda m: m.gmf),
        costo_total      = avg(lambda m: m.costo_total),
        ingreso_bruto    = avg(lambda m: m.ingreso_bruto),
        contingencias    = contingencias,
        markup_descuento = markup_desc,
        ingreso_neto     = avg(lambda m: m.ingreso_neto),
        contribucion     = avg(lambda m: m.contribucion),
        meses_activos    = n,
    )


def _calcular_reglas_negocio(
    panel: PanelDeControl,
    pyg_por_mes: Optional[List[PyGMensual]] = None,
    parametrizacion=None,
) -> List[ReglaNegocios]:
    """
    Evalúa las reglas de negocio del deal vs rangos de política.

    Los rangos min/max se cargan desde YAML canónico a través de
    IParametrizationProvider.get_politicas_comerciales().

    BUSINESS_RULES_FIX_3:
        Cada política en politicas_comerciales DEBE tener una fuente real en
        PanelDeControl. Si una política del JSON no tiene campo Panel mapeado,
        se lanza ValueError (no se permiten defaults silenciosos en 0.0).
        porcentaje_acumulado fue eliminado: sin fuente Panel, nunca activo.
        imprevistos usa panel.imprevistos directamente (campo real en PanelDeControl).
    """
    costo_total_acumulado = (
        sum(m.costo_total for m in pyg_por_mes)
        if pyg_por_mes else 0.0
    )

    # Mapa nombre-política → valor real del panel.
    # BUSINESS_RULES_FIX_3: cada clave aquí debe tener fuente real en PanelDeControl.
    # Si una política del JSON no aparece aquí, se lanza ValueError (guard abajo).
    _PANEL_FIELDS = {
        "margen_objetivo_cadena_a": panel.margen,
        "contingencia_operativa":  panel.op_cont,
        "contingencia_comercial":  panel.com_cont,
        "markup":                  panel.markup,
        "descuento":               panel.descuento,
        "imprevistos":             panel.imprevistos,   # campo real (PanelDeControl.imprevistos)
    }

    _helpers_logger = logging.getLogger(__name__)

    if parametrizacion is not None:
        politicas_config = parametrizacion.get_politicas_comerciales()
        # Defensive: get_politicas_comerciales() must return List[Dict].
        # If _parse_yaml_simple fallback was used (no PyYAML), it returns a dict
        # with keys like "- nombre". Normalize to list to prevent TypeError.
        if isinstance(politicas_config, dict):
            _helpers_logger.error(
                "[BUG] get_politicas_comerciales() devolvio dict en lugar de list. "
                "Claves: %s. Verifica que PyYAML este instalado en el entorno del servidor.",
                list(politicas_config.keys()),
            )
            politicas_config = [
                {"nombre": k, **v} if isinstance(v, dict)
                else {"nombre": k, "label": k, "min": None, "max": None}
                for k, v in politicas_config.items()
            ]
        elif not isinstance(politicas_config, list):
            _helpers_logger.error(
                "[BUG] get_politicas_comerciales() devolvio tipo inesperado: %s",
                type(politicas_config).__name__,
            )
            politicas_config = []
    else:
        politicas_config = [
            {"nombre": "margen_objetivo_cadena_a", "label": "Margen objetivo",        "min": None, "max": None},
            {"nombre": "contingencia_operativa", "label": "Contingencia Operativa", "min": 0.05, "max": 0.08},
            {"nombre": "contingencia_comercial", "label": "Contingencia Comercial", "min": 0.04, "max": 0.07},
            {"nombre": "markup",                 "label": "Mark up (complejidad, horarios)", "min": 0.02, "max": 0.08},
            {"nombre": "descuento",              "label": "Descuento volumen",      "min": 0.0,  "max": 0.08},
            {"nombre": "imprevistos",            "label": "Imprevistos",            "min": None, "max": None},
        ]

    reglas: List[ReglaNegocios] = []
    for pol in politicas_config:
        nombre   = pol["nombre"]
        label    = pol["label"]
        min_v    = pol["min"]
        max_v    = pol["max"]

        # BUSINESS_RULES_FIX_3 guard: no se permite default 0.0 para política sin fuente Panel.
        # Si nombre no está en _PANEL_FIELDS, la política en el JSON no tiene campo mapeado.
        if nombre not in _PANEL_FIELDS:
            raise ValueError(
                f"Política comercial '{nombre}' no tiene campo PanelDeControl mapeado "
                f"en _PANEL_FIELDS. BUSINESS_RULES_FIX_3: cada política en "
                f"politicas_comerciales debe tener fuente real en el panel. "
                f"Eliminar '{nombre}' de YAML de políticas comerciales "
                f"o agregar su campo a PanelDeControl y a _PANEL_FIELDS. "
                f"Ver docs/refactor/business_rules_source_of_truth_audit.md."
            )
        aplicado = _PANEL_FIELDS[nombre]

        monto = None
        if costo_total_acumulado > 0 and aplicado != 0.0:
            monto = costo_total_acumulado * aplicado

        if min_v is not None and aplicado < min_v:
            status = "bajo_minimo"
        elif max_v is not None and aplicado > max_v:
            status = "excede_maximo"
        else:
            status = "dentro_rango"

        reglas.append(ReglaNegocios(
            nombre    = nombre,
            label     = label,
            aplicado  = aplicado,
            min_valor = min_v,
            max_valor = max_v,
            status    = status,
            monto     = monto,
        ))

    return reglas


__all__ = ["_calcular_waterfall", "_calcular_reglas_negocio"]
