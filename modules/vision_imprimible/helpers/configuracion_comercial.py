"""Configuración Comercial — Visión Imprimible sección 03 (Excel VI rows 32-39).

El helper solo proyecta valores ya calculados por `vision_tarifas` y `kpis`.
No recalcula fórmulas comerciales.

Regla Superior: Excel V2-7 es canónico. No leer storage ni calculators en runtime.
"""
from __future__ import annotations

from typing import Any, Dict, List

from nexa_engine.modules.shared.models import PricingResult


def select_principal_channel(canales: List) -> Any:
    """Selecciona el canal principal basado en mayor facturación. FIX F8.1.

    Raises:
        ValueError: Si la lista de canales está vacía.
    """
    if not canales:
        raise ValueError(
            "CONFIGURACIÓN COMERCIAL INCOMPLETA: No hay canales en vision_tarifas. "
            "El deal debe tener al menos 1 canal activo (Cadena A) para calcular tarifa principal. "
            "Verificar: panel_de_control.cadena_a_activa y condiciones_cadena_a.perfiles[]"
        )
    return max(canales, key=lambda c: c.facturacion)


def configuracion_comercial_to_dict(resultado: PricingResult) -> Dict[str, Any]:
    """Resumen de la configuración comercial del deal — Sección 03 Visión Imprimible.

    Produce 12 campos con selección de canal principal y lectura de tarifa almacenada.
    Si no hay canales activos (Cadena A inactiva), devuelve campos en cero.
    """
    panel  = resultado.panel
    kpis   = resultado.kpis
    canales = resultado.vision_tarifas.canales if resultado.vision_tarifas else []
    cadenas = getattr(panel, "cadenas_activas", None)

    if not canales and not bool(getattr(cadenas, "cadena_a", True)):
        return {
            "modelo_cobro_principal": "",
            "pct_fijo_global":        0.0,
            "pct_variable_global":    0.0,
            "tarifa_fija":            0.0,
            "tarifa_variable":        0.0,
            "descuento":              panel.descuento,
            "margen_objetivo":        panel.margen,
            "volumen_base_mensual":   resultado.cost_to_serve.vol_cadena_b if resultado.cost_to_serve else 0.0,
            "ingreso_mensual":        kpis.ingreso_mensual,
            "costo_mensual_total":    kpis.costo_mensual_promedio,
            "valor_total_deal":       kpis.valor_total_deal,
        }

    canal_principal  = select_principal_channel(canales)
    pct_fijo_global  = canal_principal.pct_fijo
    tarifa_fija      = canal_principal.tarifa_fijo_fte

    return {
        "modelo_cobro_principal": canal_principal.modelo_cobro,
        "pct_fijo_global":        pct_fijo_global,
        "pct_variable_global":    canal_principal.pct_variable,
        "tarifa_fija":            tarifa_fija,
        "tarifa_variable":        canal_principal.tarifa_variable,
        "descuento":              panel.descuento,
        "margen_objetivo":        panel.margen,
        "volumen_base_mensual":   resultado.cost_to_serve.vol_cadena_b if resultado.cost_to_serve else 0.0,
        "ingreso_mensual":        (
            resultado.vision_tarifas.ingreso_mensual
            if resultado.vision_tarifas else kpis.ingreso_mensual
        ),
        "costo_mensual_total":    (
            resultado.vision_tarifas.costo_cadena_a_total + resultado.vision_tarifas.costo_cadena_c_total
            if resultado.vision_tarifas else kpis.costo_mensual_promedio
        ),
        "valor_total_deal":       kpis.valor_total_deal,
    }
