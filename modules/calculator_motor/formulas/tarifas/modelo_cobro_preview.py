"""Modelo de Cobro preview recalculation.

Lightweight stateless preview for modelo_cobro overrides.
This module provides the label/tariff-label recomputation logic.

Excel V2-8: 'Vision Tarifas_Modelo_Cobro' sheet
Overrides only affect tariff labels and display values,
not base cost calculations.
"""
from __future__ import annotations

from typing import Any, Optional


def recompute_tariff_labels(
    overrides: dict[str, Any],
    tarifa_fijo: Optional[dict[str, Any]] = None,
    tarifa_var: Optional[dict[str, Any]] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recompute tariff labels based on overrides.

    Args:
        overrides: User-provided override dict.
        tarifa_fijo: Existing fixed tariff detail (mutated in place).
        tarifa_var: Existing variable tariff detail (mutated in place).

    Returns:
        Updated (tarifa_fijo, tarifa_var) tuple.
    """
    fijo = dict(tarifa_fijo or {})
    var = dict(tarifa_var or {})

    cf = overrides.get("componente_fijo")
    if cf and cf not in ("0", "null", ""):
        is_fte = cf in ("FTE", "Fijo FTE")
        fijo["tarifa_principal_label"] = "Tarifa por FTE" if is_fte else "Tarifa por minuto loggeado"
        fijo["tarifa_secundaria_label"] = "Tarifa por minuto pagado"

    cv = overrides.get("componente_variable")
    if cv and cv not in ("0", "null", ""):
        is_transaccion = cv in ("Transacción", "Transaccion")
        var["titulo"] = f"Tarifa Componente Variable - {cv}"
        var["tarifa_principal_label"] = "Tarifa por Transacción" if is_transaccion else "Comisiones M1"
        var["volumen_label"] = "Volumen Mínimo de Transacción" if is_transaccion else "Ingreso por persona"

    return fijo, var
