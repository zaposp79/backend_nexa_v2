"""Stateless preview recalculation for modelo_cobro overrides.

This service applies user overrides to a persisted result and returns
an updated preview without mutating persisted data.

Overrides only affect:
- modelo_cobro (Fijo/Híbrido/Variable)
- tarifa_componente_fijo labels
- tarifa_componente_variable labels
"""
from __future__ import annotations

from typing import Any, Optional

from nexa_engine.modules.vision_tarifas.helpers.modelo_cobro_mapper import (
    build_modelo_cobro_from_result,
)

_ALLOWED_MODELO_COBRO = {"Híbrido", "Fijo", "Variable", "0", None}
_ALLOWED_COMPONENTE_FIJO = {"FTE", "Tiempo", "Precio Fijo", "0", None}
_ALLOWED_COMPONENTE_VARIABLE = {"Transacción", "Resultados", "Honorarios", "0", None}


class OverrideValidationError(ValueError):
    def __init__(self, message: str, details: Optional[list] = None):
        self.message = message
        self.details = details or []
        super().__init__(message)


def validate_overrides(overrides: dict) -> None:
    errors: list[str] = []

    mc = overrides.get("modelo_cobro")
    if mc is not None and mc not in _ALLOWED_MODELO_COBRO and mc not in ("",):
        errors.append(f"Invalid modelo_cobro: {mc!r}")

    cf = overrides.get("componente_fijo")
    if cf is not None and cf not in _ALLOWED_COMPONENTE_FIJO and cf not in ("",):
        errors.append(f"Invalid componente_fijo: {cf!r}")

    cv = overrides.get("componente_variable")
    if cv is not None and cv not in _ALLOWED_COMPONENTE_VARIABLE and cv not in ("",):
        errors.append(f"Invalid componente_variable: {cv!r}")

    pct_fijo = overrides.get("proporcion_componente_fijo")
    if pct_fijo is not None:
        if not isinstance(pct_fijo, (int, float)) or pct_fijo < 0 or pct_fijo > 1:
            errors.append(f"proporcion_componente_fijo must be between 0 and 1, got {pct_fijo!r}")

    pct_var = overrides.get("proporcion_componente_variable")
    if pct_var is not None:
        if not isinstance(pct_var, (int, float)) or pct_var < 0 or pct_var > 1:
            errors.append(f"proporcion_componente_variable must be between 0 and 1, got {pct_var!r}")

    # Check negative values
    for key, value in overrides.items():
        if isinstance(value, (int, float)) and value < 0:
            errors.append(f"{key} must not be negative, got {value}")

    if errors:
        raise OverrideValidationError("Invalid modelo_cobro override", errors)


def recalculate_preview(
    pricing_result_dict: dict,
    view_id: str,
    overrides: dict,
) -> dict:
    """Apply overrides and return updated modelo_cobro preview without persistence.

    Args:
        pricing_result_dict: Full persisted pricing result.
        view_id: Target view (escenario_1..5 or total).
        overrides: Dict with override fields.

    Returns:
        Updated modelo_cobro contract dict.

    Raises:
        OverrideValidationError: If overrides are invalid.
    """
    validate_overrides(overrides)

    # Check if override requires full engine recalculation
    if _requires_full_recalculation(overrides):
        from nexa_engine.modules.shared.responses import ApiResponse, ErrorDetail
        raise OverrideValidationError(
            "This override requires full calculator recalculation",
        )

    base = build_modelo_cobro_from_result(pricing_result_dict)

    resumen_rows = base.get("resumen_resultado_escenario") or []

    _apply_to_modelo_cobro_list(base, view_id, overrides)
    _apply_to_resumen(resumen_rows, view_id, overrides)
    _reapply_tariff_labels(base, view_id, overrides)

    return base


def _requires_full_recalculation(overrides: dict) -> bool:
    """Check if override requires full calculator recalculation.

    Currently, only label/proportion overrides are supported at preview level.
    Any override affecting base costs would require full recalculation.
    """
    cost_keys = {"costo_directo", "costo_financiacion", "payroll", "no_payroll"}
    provided_keys = set(overrides.keys())
    if provided_keys & cost_keys:
        return True
    return False


def _apply_to_modelo_cobro_list(base: dict, view_id: str, overrides: dict) -> None:
    items = base.get("modelo_cobro") or []
    if not items:
        return

    target = "Total" if view_id == "total" else str(_extract_scenario_number(view_id))

    for item in items:
        if item.get("escenario") == target:
            _apply_overrides_to_item(item, overrides)
            break


def _extract_scenario_number(view_id: str) -> int:
    digits = "".join(ch for ch in view_id if ch.isdigit())
    return int(digits) if digits else 0


def _apply_overrides_to_item(item: dict, overrides: dict) -> None:
    mc = overrides.get("modelo_cobro")
    if mc is not None and mc not in ("0", "null", ""):
        item["modelo_cobro"] = mc

    cf = overrides.get("componente_fijo")
    if cf is not None and cf not in ("0", "null", ""):
        item["componente_fijo"] = cf
    elif cf in ("0", "null"):
        item["componente_fijo"] = 0

    cv = overrides.get("componente_variable")
    if cv is not None and cv not in ("0", "null", ""):
        item["componente_variable"] = cv
    elif cv in ("0", "null"):
        item["componente_variable"] = None

    pct_fijo = overrides.get("proporcion_componente_fijo")
    if pct_fijo is not None:
        item["proporcion_componente_fijo"] = float(pct_fijo)

    pct_var = overrides.get("proporcion_componente_variable")
    if pct_var is not None:
        item["proporcion_componente_variable"] = float(pct_var)


def _apply_to_resumen(rows: list[dict], view_id: str, overrides: dict) -> None:
    target = view_id if view_id != "total" else "Total"
    for row in rows:
        if row.get("escenario") == str(target) or row.get("escenario") == target:
            mc = overrides.get("modelo_cobro")
            if mc is not None and mc not in ("0", "null", ""):
                row["modelo_cobro"] = mc

            cf = overrides.get("componente_fijo")
            if cf is not None and cf not in ("0", "null", ""):
                row["componente_fijo"] = cf
            elif cf in ("0", "null"):
                row["componente_fijo"] = 0

            cv = overrides.get("componente_variable")
            if cv is not None and cv not in ("0", "null", ""):
                row["componente_variable"] = cv
            elif cv in ("0", "null"):
                row["componente_variable"] = None

            pct_fijo = overrides.get("proporcion_componente_fijo")
            if pct_fijo is not None:
                row["proporcion_componente_fijo"] = float(pct_fijo)

            pct_var = overrides.get("proporcion_componente_variable")
            if pct_var is not None:
                row["proporcion_componente_variable"] = float(pct_var)
            break


def _reapply_tariff_labels(base: dict, view_id: str, overrides: dict) -> None:
    items = base.get("modelo_cobro") or []
    target = "Total" if view_id == "total" else str(_extract_scenario_number(view_id))
    modelo_cobro = next((item for item in items if item.get("escenario") == target), None)
    if not modelo_cobro:
        return
    tarifa_fijo = modelo_cobro.get("tarifa_componente_fijo") or {}
    tarifa_var = modelo_cobro.get("tarifa_componente_variable") or {}

    cf = overrides.get("componente_fijo")
    cv = overrides.get("componente_variable")

    if cf:
        is_fte = cf in ("FTE", "Fijo FTE")
        tarifa_fijo["tarifa_principal_label"] = "Tarifa por FTE" if is_fte else "Tarifa por minuto loggeado"
        tarifa_fijo["tarifa_secundaria_label"] = "Tarifa por minuto pagado"

    if cv:
        is_transaccion = cv in ("Transacción", "Transaccion")
        tarifa_var["titulo"] = f"Tarifa Componente Variable - {cv}"
        tarifa_var["tarifa_principal_label"] = "Tarifa por Transacción" if is_transaccion else "Comisiones M1"
        tarifa_var["volumen_label"] = "Volumen Mínimo de Transacción" if is_transaccion else "Ingreso por persona"
