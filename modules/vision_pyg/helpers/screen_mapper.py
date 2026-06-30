"""Mapper: persisted vision_pyg -> period-centric screen contract."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, Optional


_INGRESOS_MAP = {
    "ingreso_bruto_a": ("ingresos", "ingreso_cadena_a"),
    "ingreso_bruto_b": ("ingresos", "ingreso_cadena_b"),
    "ingreso_bruto_c": ("ingresos", "ingreso_cadena_c"),
    "ingreso_bruto": ("ingresos", "ingreso_bruto"),
    "contingencia_op": ("ingresos", "contingencia_op"),
    "contingencia_com": ("ingresos", "contingencia_com"),
    "markup_ingreso": ("ingresos", "markup"),
    "descuento_ingreso": ("ingresos", "descuento"),
    "imprevistos_ingreso": ("ingresos", "imprevistos"),
    "ingreso_neto": ("ingresos", "ingreso_neto"),
}

_COSTOS_MAP = {
    "payroll_a": ("costos", "cadena_a", "payroll"),
    "no_payroll_a": ("costos", "cadena_a", "no_payroll"),
    "costo_a": ("costos", "cadena_a", "total_cadena_a"),
    "costo_b": ("costos", "cadena_b", "total_cadena_b"),
    "opex_fijo_b": ("costos", "cadena_b", "opex_fijo"),
    "inversiones_b": ("costos", "cadena_b", "inversiones"),
    "sm_b": ("costos", "cadena_b", "s_and_m"),
    "tarifa_canal_b": ("costos", "cadena_b", "tarifa_canal"),
    "tasa_escalamiento_b": ("costos", "cadena_b", "tasa_escalamiento"),
    "hitl_b": ("costos", "cadena_b", "hitl"),
    "costo_c": ("costos", "cadena_c", "total_cadena_c"),
    "tarifa_proveedor_c": ("costos", "cadena_c", "tarifa_proveedor"),
    "opex_fijo_integ_c": ("costos", "cadena_c", "opex_fijo"),
    "inversiones_integ_c": ("costos", "cadena_c", "inversiones"),
    "equipo_integ_c": ("costos", "cadena_c", "equipo_integracion"),
    "tasa_escalamiento_c": ("costos", "cadena_c", "tasa_escalamiento"),
    "opex_var_integ_c": ("costos", "cadena_c", "opex_variable"),
    "hitl_c": ("costos", "cadena_c", "hitl"),
    "ica": ("costos", "componente_financiero", "ica"),
    "gmf": ("costos", "componente_financiero", "gmf"),
    "comision_administracion": ("costos", "componente_financiero", "comision_administracion"),
    "polizas": ("costos", "componente_financiero", "polizas_adicionales"),
    "financiacion": ("costos", "componente_financiero", "costos_financieros"),
    "costos_financieros": ("costos", "componente_financiero", "total_componente_financiero"),
}

_UTILIDAD_MAP = {
    "contribucion": ("utilidad", "contribucion"),
    "contribucion_por_puesto": ("utilidad", "contribucion_por_puesto"),
    "pct_contribucion": ("utilidad", "porcentaje_contribucion"),
    "costo_fijo": ("utilidad", "costo_fijo"),
    "utilidad_neta": ("utilidad", "utilidad_neta"),
    "pct_utilidad_neta": ("utilidad", "porcentaje_utilidad_neta"),
}


def _prune_empty(obj: Any) -> Any:
    """Recursively remove null/empty values while keeping 0, 0.0, and False."""
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            pruned = _prune_empty(value)
            if pruned is not None and pruned != "" and pruned != [] and pruned != {}:
                result[key] = pruned
        return result if result else None
    if isinstance(obj, list):
        result = [_prune_empty(item) for item in obj]
        result = [item for item in result if item is not None and item != "" and item != [] and item != {}]
        return result if result else None
    return obj


def _iter_rows(vp_data: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    filas = vp_data.get("filas")
    if isinstance(filas, list):
        for row in filas:
            if isinstance(row, dict):
                yield row
        return

    secciones = vp_data.get("secciones")
    if not isinstance(secciones, list):
        return

    for section_block in secciones:
        if not isinstance(section_block, dict):
            continue
        section_name = (
            section_block.get("key")
            or section_block.get("seccion")
            or section_block.get("section")
            or section_block.get("id")
        )
        rows = section_block.get("filas") or section_block.get("rows") or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            normalized = dict(row)
            normalized.setdefault("seccion", section_name)
            yield normalized


def _build_header(vp_data: Dict[str, Any]) -> Dict[str, Any]:
    resumen = vp_data.get("resumen") or {}
    return {
        "cliente": resumen.get("cliente"),
        "tipo_cliente": resumen.get("tipo_cliente"),
        "linea_negocio": resumen.get("linea_negocio"),
        "periodo_pago": resumen.get("periodo_pago_dias"),
        "duracion_contrato": resumen.get("duracion_contrato"),
        "duracion_meses": resumen.get("meses_contrato"),
        "servicio": resumen.get("servicio"),
        "divisa": resumen.get("divisa"),
    }


def _parse_period_fields(label: Any, index: int) -> Dict[str, Any]:
    period = {
        "index": index,
        "label": label,
        "periodo": index,
    }
    if isinstance(label, str):
        try:
            parsed = datetime.strptime(label, "%Y-%m-%d")
            period["mes"] = parsed.month
            period["anio"] = parsed.year
        except ValueError:
            pass
    return period


def _empty_cost_buckets() -> Dict[str, Any]:
    return {
        "cadena_a": {},
        "cadena_b": {},
        "cadena_c": {},
        "componente_financiero": {},
    }


def _assign_nested(target: Dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    current = target
    for key in path[:-1]:
        current = current.setdefault(key, {})
    current[path[-1]] = value


def _build_periods(vp_data: Dict[str, Any]) -> list[Dict[str, Any]]:
    fechas = vp_data.get("fechas_meses") or []
    periods = []
    for idx, label in enumerate(fechas, start=1):
        period = _parse_period_fields(label, idx)
        period["ingresos"] = {}
        period["costos"] = _empty_cost_buckets()
        period["utilidad"] = {}
        periods.append(period)
    return periods


def _build_totales() -> Dict[str, Any]:
    return {
        "ingresos": {},
        "costos": _empty_cost_buckets(),
        "utilidad": {},
    }


def _apply_row_to_contract(row: Dict[str, Any], periods: list[Dict[str, Any]], totales: Dict[str, Any]) -> None:
    key = row.get("key")
    if key in _INGRESOS_MAP:
        period_path = _INGRESOS_MAP[key]
        total_path = _INGRESOS_MAP[key]
    elif key in _COSTOS_MAP:
        period_path = _COSTOS_MAP[key]
        total_path = _COSTOS_MAP[key]
    elif key in _UTILIDAD_MAP:
        period_path = _UTILIDAD_MAP[key]
        total_path = _UTILIDAD_MAP[key]
    else:
        return

    valores = row.get("valores") or []
    for idx, period in enumerate(periods):
        if idx >= len(valores):
            continue
        value = valores[idx]
        if value is None or value == "":
            continue
        _assign_nested(period, period_path, value)

    acumulado = row.get("acumulado")
    if acumulado is None or acumulado == "":
        return
    _assign_nested(totales, total_path, acumulado)


def build_vision_pyg_from_result(
    pricing_result_dict: Optional[Dict[str, Any]],
    simulation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the public period-centric vision_pyg contract from persisted data."""
    vp_data = (pricing_result_dict or {}).get("vision_pyg") or {}

    periods = _build_periods(vp_data)
    totales = _build_totales()

    for row in _iter_rows(vp_data):
        _apply_row_to_contract(row, periods, totales)

    response = {
        "version": "v1",
        "simulation_id": simulation_id,
        "header": _build_header(vp_data),
        "periods": periods,
        "totales": totales,
        "metadata": {
            "source": "persisted_pricing_result",
            "omitted_empty_fields": True,
        },
    }
    return _prune_empty(response) or {}


__all__ = ["build_vision_pyg_from_result"]
