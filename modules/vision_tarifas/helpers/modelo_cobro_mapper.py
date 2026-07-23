"""Public screen mapper for Vision Tarifas modelo_cobro.

Translates persisted ResultadoVisionTarifas into the simplified
screen-ready contract defined in VISION_TARIFAS_MODELO_COBRO_GET_POST_SCREEN_CONTRACT.
"""
from __future__ import annotations

import math
import re
from typing import Any, Optional


_INVALID_STRINGS = {"#VALOR!", "#DIV/0!", "#N/D", "NaN", "Infinity", "-Infinity"}


def build_modelo_cobro_from_result(pricing_result_dict: Optional[dict]) -> dict:
    """Build the public modelo_cobro screen contract from persisted data only.

    Returns the simplified contract:
        cliente, servicio, ciudad, selected_view_id,
        resumen_resultado_escenario[], modelo_cobro[], desglose_producto_opex[]
    """
    result = pricing_result_dict or {}
    vt_data = result.get("vision_tarifas") or {}
    missing_fields: list[str] = []

    header = _build_header(result, vt_data, missing_fields)
    canales = vt_data.get("canales") or []
    raw_scenarios = vt_data.get("escenarios_detalle") or []
    opex_raw = vt_data.get("desglose_producto_opex") or []

    scenario_map, scenario_sources = _index_scenarios(raw_scenarios, canales, vt_data)

    selected_view_id, _ = _pick_selected_scenario(result, scenario_map)

    resumen = _build_resumen_resultado_escenario(
        scenario_map, scenario_sources, vt_data, canales, missing_fields
    )

    modelo_cobro = _build_modelo_cobro_list(
        scenario_map, scenario_sources, vt_data, result, missing_fields
    )

    desglose_producto_opex = _build_desglose_producto_opex(opex_raw, missing_fields)

    for key in ("cliente", "servicio", "ciudad"):
        if header.get(key) in (None, ""):
            missing_fields.append(f"header.{key}")

    payload = {
        "cliente": header.get("cliente"),
        "servicio": header.get("servicio"),
        "ciudad": header.get("ciudad"),
        "selected_view_id": selected_view_id,
        "resumen_resultado_escenario": resumen,
        "modelo_cobro": modelo_cobro,
        "desglose_producto_opex": desglose_producto_opex,
    }

    omitted_invalid: list[str] = []
    sanitized = _sanitize_invalid(payload, omitted_invalid)

    sanitized.setdefault("resumen_resultado_escenario", _empty_resumen_rows())
    sanitized.setdefault("modelo_cobro", [])
    sanitized.setdefault("desglose_producto_opex", [])

    return sanitized


# ---------------------------------------------------------------------------
# Header helpers
# ---------------------------------------------------------------------------


def _build_header(result: dict, vt_data: dict, missing_fields: list[str]) -> dict:
    ficha = result.get("ficha_deal") or {}
    resumen = result.get("resumen") or {}
    panel = result.get("panel") or {}

    return {
        "cliente": ficha.get("cliente") or resumen.get("cliente") or panel.get("cliente"),
        "servicio": (
            ficha.get("linea_negocio")
            or ficha.get("servicio")
            or resumen.get("linea_negocio")
            or resumen.get("servicio")
            or panel.get("linea_negocio")
            or panel.get("servicio")
        ),
        "ciudad": ficha.get("ciudad") or resumen.get("ciudad") or panel.get("ciudad"),
    }


# ---------------------------------------------------------------------------
# Scenario indexing
# ---------------------------------------------------------------------------


def _index_scenarios(
    raw_scenarios: list[Any],
    canales: list[Any],
    vt_data: dict,
) -> tuple[dict[str, dict], dict[str, dict]]:
    scenario_map: dict[str, dict] = {}
    sources: dict[str, dict] = {}

    for index, raw in enumerate(raw_scenarios, start=1):
        if not isinstance(raw, dict):
            continue
        meta = raw.get("meta") or {}
        scenario_number = _scenario_number(meta, index)
        scenario_id = f"escenario_{scenario_number}"
        channel = _find_channel(meta, canales, index - 1)

        scenario_map[scenario_id] = _build_scenario_entry(meta, raw, channel, vt_data)
        sources[scenario_id] = {
            "meta": meta,
            "channel": channel,
            "reglas": raw.get("reglas_business") or {},
            "tarifas": raw.get("tarifas") or {},
            "fixed_component": raw.get("componente_fijo") or {},
            "variable_component": raw.get("componente_variable") or {},
            "cadena_a": raw.get("cadena_a") or {},
            "cadena_b": raw.get("cadena_b") or {},
            "cadena_c": raw.get("cadena_c") or {},
            "tarifas_venta": raw.get("tarifas_venta") or [],
        }

    return scenario_map, sources


def _build_scenario_entry(meta: dict, raw: dict, channel: dict, vt_data: Optional[dict] = None) -> dict:
    reglas = raw.get("reglas_business") or {}
    tarifas = raw.get("tarifas") or {}
    fixed_component = raw.get("componente_fijo") or {}
    variable_component = raw.get("componente_variable") or {}

    entry = {
        "escenario": str(_scenario_number(meta, 0)),
        "modalidad": _coalesce(meta.get("modalidad"), channel.get("modalidad")),
        "canal": _coalesce(meta.get("canal"), channel.get("producto"), channel.get("nombre_canal")),
        "modelo_cobro": _coalesce(meta.get("modelo_cobro"), channel.get("modelo_cobro"), ""),
        "componente_fijo": _resolve_componente_label(meta, channel),
        "proporcion_componente_fijo": _safe_float(meta.get("pct_fijo")),
        "componente_variable": _coalesce(meta.get("componente_variable_label"), channel.get("componente_variable"), ""),
        "proporcion_componente_variable": _safe_float(meta.get("pct_variable")),
        "facturacion": _safe_float(_coalesce(
            meta.get("facturacion_directo"),
            tarifas.get("facturacion_total"),
        )),
        "tarifa_componente_fijo": _safe_float(_coalesce(
            meta.get("tarifa_componente_fijo"),
            tarifas.get("tarifa_por_fte"),
        )),
        "tarifa_componente_variable": _safe_float(_coalesce(
            meta.get("tarifa_componente_variable"),
            tarifas.get("tarifa_por_transaccion"),
        )),
        "fte": _safe_float(meta.get("fte")),
        "reglas_negocio": _build_reglas_negocio(reglas, {}),
        "cadenas": _build_cadenas(raw),
        "totales": _build_totales(tarifas, vt_data.get("costo_total") if vt_data else None),
        "tarifa_componente_fijo_detail": _build_tarifa_fijo(
            meta, tarifas, fixed_component, channel
        ),
        "tarifa_componente_variable_detail": _build_tarifa_variable(
            meta, tarifas, variable_component
        ),
    }
    return entry


# ---------------------------------------------------------------------------
# Resumen resultado escenario
# ---------------------------------------------------------------------------


def _build_resumen_resultado_escenario(
    scenario_map: dict,
    scenario_sources: dict,
    vt_data: dict,
    canales: list,
    missing_fields: list,
) -> list[dict]:
    rows: list[dict] = []

    for i in range(1, 6):
        scenario_id = f"escenario_{i}"
        if scenario_id in scenario_map:
            entry = scenario_map[scenario_id]
            rows.append({
                "escenario": str(i),
                "modalidad": entry.get("modalidad"),
                "canal": entry.get("canal"),
                "modelo_cobro": entry.get("modelo_cobro"),
                "componente_fijo": entry.get("componente_fijo"),
                "proporcion_componente_fijo": entry.get("proporcion_componente_fijo", 0),
                "componente_variable": entry.get("componente_variable"),
                "proporcion_componente_variable": entry.get("proporcion_componente_variable", 0),
                "facturacion": entry.get("facturacion", 0),
                "tarifa_componente_fijo": entry.get("tarifa_componente_fijo", 0),
                "tarifa_componente_variable": entry.get("tarifa_componente_variable", 0),
            })
        else:
            rows.append(_empty_scenario_row(str(i)))

    total_row = _build_total_resumen_row(vt_data, scenario_map)
    rows.append(total_row)

    return rows


def _empty_scenario_row(scenario_number: str) -> dict:
    return {
        "escenario": scenario_number,
        "modalidad": None,
        "canal": None,
        "modelo_cobro": None,
        "componente_fijo": None,
        "proporcion_componente_fijo": 0,
        "componente_variable": None,
        "proporcion_componente_variable": 0,
        "facturacion": 0,
        "tarifa_componente_fijo": 0,
        "tarifa_componente_variable": 0,
    }


def _build_total_resumen_row(vt_data: dict, scenario_map: dict) -> dict:
    first_entry = next(iter(scenario_map.values()), None)
    facturacion = _safe_float(vt_data.get("ingreso_mensual"))
    tarifa_var = 0
    if first_entry:
        tarifa_var = _safe_float(first_entry.get("tarifa_componente_variable"))

    return {
        "escenario": "Total",
        "modalidad": None,
        "canal": None,
        "modelo_cobro": "Fijo",
        "componente_fijo": "FTE",
        "proporcion_componente_fijo": 0,
        "componente_variable": "Transacción",
        "proporcion_componente_variable": 1,
        "facturacion": facturacion,
        "tarifa_componente_fijo": 0,
        "tarifa_componente_variable": tarifa_var,
    }


def _empty_resumen_rows() -> list[dict]:
    rows = [_empty_scenario_row(str(i)) for i in range(1, 6)]
    rows.append({
        "escenario": "Total",
        "modalidad": None,
        "canal": None,
        "modelo_cobro": "Fijo",
        "componente_fijo": "FTE",
        "proporcion_componente_fijo": 0,
        "componente_variable": "Transacción",
        "proporcion_componente_variable": 1,
        "facturacion": 0,
        "tarifa_componente_fijo": 0,
        "tarifa_componente_variable": 0,
    })
    return rows


# ---------------------------------------------------------------------------
# Modelo cobro list (all views Escenario 1..5 + Total)
# ---------------------------------------------------------------------------


def _build_modelo_cobro_list(
    scenario_map: dict,
    scenario_sources: dict,
    vt_data: dict,
    result: dict,
    missing_fields: list,
) -> list[dict]:
    items: list[dict] = []

    for i in range(1, 6):
        scenario_id = f"escenario_{i}"
        if scenario_id in scenario_map:
            entry = scenario_map[scenario_id]
            source = scenario_sources.get(scenario_id) or {}
            items.append({
                "escenario": str(i),
                "modalidad": entry.get("modalidad"),
                "canal": entry.get("canal"),
                "modelo_cobro": entry.get("modelo_cobro"),
                "componente_fijo": entry.get("componente_fijo"),
                "proporcion_componente_fijo": entry.get("proporcion_componente_fijo", 0),
                "componente_variable": entry.get("componente_variable"),
                "proporcion_componente_variable": entry.get("proporcion_componente_variable", 0),
                "fte": entry.get("fte", 0),
                "cadena_a": _normalize_cadena(source.get("cadena_a") or {}, "a"),
                "cadena_b": _normalize_cadena(source.get("cadena_b") or {}, "b"),
                "cadena_c": _normalize_cadena(source.get("cadena_c") or {}, "c"),
                "totales": entry.get("totales"),
                "reglas_negocio": entry.get("reglas_negocio"),
                "tarifa_componente_fijo": entry.get("tarifa_componente_fijo_detail"),
                "tarifa_componente_variable": entry.get("tarifa_componente_variable_detail"),
            })
        else:
            items.append(_empty_modelo_cobro_item(str(i)))

    total_item = _build_total_detail(
        vt_data, scenario_map, scenario_sources, result, missing_fields
    )
    items.append(total_item)

    return items


def _empty_modelo_cobro_item(scenario_number: str) -> dict:
    return {
        "escenario": scenario_number,
        "modalidad": None,
        "canal": None,
        "modelo_cobro": None,
        "componente_fijo": None,
        "proporcion_componente_fijo": 0,
        "componente_variable": None,
        "proporcion_componente_variable": 0,
        "fte": 0,
        "cadena_a": {},
        "cadena_b": {},
        "cadena_c": {},
        "totales": {
            "costo_total_mensual": 0,
            "facturacion_total_mensual": 0,
        },
        "reglas_negocio": {},
        "tarifa_componente_fijo": {},
        "tarifa_componente_variable": {},
    }


def _build_total_detail(
    vt_data: dict,
    scenario_map: dict,
    scenario_sources: dict,
    result: dict,
    missing_fields: list,
) -> dict:
    first_entry = next(iter(scenario_map.values()), None)
    first_source = next(iter(scenario_sources.values()), None)

    if not first_entry:
        fte_total = 0
        rules = _build_reglas_negocio({}, result.get("panel") or result.get("resumen") or {})
        cadenas = {
            "cadena_a": {},
            "cadena_b": {},
            "cadena_c": {},
        }
        totales = {}
        tarifa_fijo = {}
        tarifa_var = {}
    else:
        raw_fte = _safe_float(first_entry.get("fte"))
        fte_total = raw_fte * 2 if raw_fte else 0

        reglas_source = first_source.get("reglas") if first_source else {}
        root_rules = result.get("panel") or result.get("resumen") or {}
        rules = _build_reglas_negocio(reglas_source, root_rules)

        ca = (first_source.get("cadena_a") or {}) if first_source else {}
        cb = (first_source.get("cadena_b") or {}) if first_source else {}
        cc = (first_source.get("cadena_c") or {}) if first_source else {}
        cadenas = {
            "cadena_a": _normalize_cadena(ca, "a"),
            "cadena_b": _normalize_cadena(cb, "b"),
            "cadena_c": _normalize_cadena(cc, "c"),
        }

        totales = first_entry.get("totales") or {}
        tarifa_fijo = first_entry.get("tarifa_componente_fijo_detail") or {}
        tarifa_var = first_entry.get("tarifa_componente_variable_detail") or {}

    return {
        "escenario": "Total",
        "modalidad": None,
        "canal": None,
        "modelo_cobro": "Fijo",
        "componente_fijo": "FTE",
        "proporcion_componente_fijo": 0,
        "componente_variable": "Transacción",
        "proporcion_componente_variable": 1,
        "fte": fte_total,
        "cadena_a": cadenas["cadena_a"],
        "cadena_b": cadenas["cadena_b"],
        "cadena_c": cadenas["cadena_c"],
        "totales": totales,
        "reglas_negocio": rules,
        "tarifa_componente_fijo": tarifa_fijo,
        "tarifa_componente_variable": tarifa_var,
    }


# ---------------------------------------------------------------------------
# Component helpers
# ---------------------------------------------------------------------------


def _resolve_componente_label(meta: dict, channel: dict) -> Any:
    label = _coalesce(
        meta.get("componente_fijo_label"),
        channel.get("componente_fijo"),
    )
    pct = _safe_float(meta.get("pct_fijo", channel.get("pct_fijo", 0)))
    if not label or label in ("", "0"):
        return 0
    return label


def _build_reglas_negocio(reglas: dict, root_rules: dict) -> dict:
    return {
        "total_regla_negocio": _safe_float(_coalesce(
            root_rules.get("margen_objetivo_cadena_a"),
            root_rules.get("margen"),
            reglas.get("margen_objetivo_cadena_a"),
        )),
        "descuento_volumen": _safe_float(_coalesce(
            reglas.get("descuento_volumen"), reglas.get("descuento")
        )),
        "cont_operativa": _safe_float(reglas.get("cont_operativa")),
        "cont_comercial": _safe_float(reglas.get("cont_comercial")),
        "margen_cadena_a": _safe_float(reglas.get("margen_cadena_a")),
        "margen_cadena_b": _safe_float(reglas.get("margen_cadena_b")),
        "margen_cadena_c": _safe_float(reglas.get("margen_cadena_c")),
        "markup": _safe_float(reglas.get("markup")),
    }


def _build_cadenas(raw: dict) -> dict:
    return {
        "cadena_a": _build_cadena(raw.get("cadena_a") or {}, "a"),
        "cadena_b": _build_cadena(raw.get("cadena_b") or {}, "b"),
        "cadena_c": _build_cadena(raw.get("cadena_c") or {}, "c"),
    }


def _build_cadena(chain: dict, label: str) -> dict:
    if label == "a":
        return {
            "total": _safe_float(_coalesce(chain.get("total"), chain.get("total_costo"))),
            "payroll": _safe_float(chain.get("payroll")),
            "no_payroll": _safe_float(chain.get("no_payroll")),
            "ica": _safe_float(chain.get("ica")),
            "gmf": _safe_float(chain.get("gmf")),
            "comision_administracion": _safe_float(chain.get("comision_administracion")),
            "polizas": _safe_float(chain.get("polizas")),
            "costos_financiacion": _safe_float(chain.get("costos_financiacion")),
            "ingreso_mensual": _safe_float(_coalesce(chain.get("ingreso_mensual"), chain.get("ingreso_bruto"))),
        }
    return {
        "total": _safe_float(_coalesce(chain.get("total"), chain.get("total_costo"))),
        "componente_fijo": _safe_float(chain.get("componente_fijo")),
        "componente_variable": _safe_float(chain.get("componente_variable")),
        "ica": _safe_float(chain.get("ica")),
        "gmf": _safe_float(chain.get("gmf")),
        "comision_administracion": _safe_float(chain.get("comision_administracion")),
        "polizas": _safe_float(chain.get("polizas")),
        "costos_financiacion": _safe_float(chain.get("costos_financiacion")),
        "ingreso_mensual": _safe_float(_coalesce(chain.get("ingreso_mensual"), chain.get("ingreso_bruto"))),
    }


def _normalize_cadena(chain: dict, label: str) -> dict:
    return _build_cadena(chain, label)


def _build_totales(tarifas: dict, costo_total: Optional[float]) -> dict:
    return {
        "costo_total_mensual": _safe_float(costo_total),
        "facturacion_total_mensual": _safe_float(tarifas.get("facturacion_total")),
    }


# ---------------------------------------------------------------------------
# Tariff detail builders
# ---------------------------------------------------------------------------


def _build_tarifa_fijo(meta: dict, tarifas: dict, fixed_component: dict, channel: dict) -> dict:
    fijo_label = _coalesce(
        meta.get("componente_fijo_label"),
        channel.get("componente_fijo"),
    )
    is_fte = fijo_label and fijo_label in ("FTE", "fte", "Fijo FTE")

    return {
        "ingreso_componente_fijo": _safe_float(tarifas.get("ingreso_componente_fijo")),
        "tarifa_principal_label": "Tarifa por FTE" if is_fte else "Tarifa por minuto loggeado",
        "tarifa_principal": _safe_float(tarifas.get("tarifa_por_fte")),
        "tarifa_secundaria_label": "Tarifa por minuto pagado" if is_fte else "Tarifa por minuto pagado",
        "tarifa_secundaria": _safe_float(tarifas.get("tarifa_hora_pagada")),
        "tarifa_por_fte": _safe_float(tarifas.get("tarifa_por_fte")),
        "tarifa_por_minuto_loggeado": _safe_float(_coalesce(
            tarifas.get("tarifa_hora_loggeada"), tarifas.get("tarifa_por_minuto_loggeado")
        )),
        "tarifa_por_minuto_pagado": _safe_float(tarifas.get("tarifa_hora_pagada")),
    }


def _build_tarifa_variable(meta: dict, tarifas: dict, variable_component: dict) -> dict:
    var_label = _coalesce(
        meta.get("componente_variable_label"),
        variable_component.get("tipo"),
    )
    is_transaccion = var_label and var_label in ("Transacción", "Transaccion")

    payload = {
        "titulo": f"Tarifa Componente Variable - {var_label}" if var_label else "Tarifa Componente Variable",
        "ingreso_componente_variable": _safe_float(tarifas.get("ingreso_componente_variable")),
        "tarifa_principal_label": "Tarifa por Transacción" if is_transaccion else "Comisiones M1",
        "tarifa_principal": _safe_float(tarifas.get("tarifa_por_transaccion")),
        "volumen_label": "Volumen Mínimo de Transacción" if is_transaccion else "Ingreso por persona",
        "volumen": _safe_float(tarifas.get("volumen_minimo_transaccion")),
        "volumetria_label": "Volumetría de 1 FTE" if is_transaccion else "",
        "volumetria_de_1_fte": _safe_float(tarifas.get("volumetria_de_1_fte")),
        "tarifa_por_transaccion": _safe_float(tarifas.get("tarifa_por_transaccion")),
        "comisiones_m1": _safe_float(_first_comision(variable_component)),
        "ingreso_por_persona": _safe_float(tarifas.get("ingreso_por_persona")),
    }
    return payload


def _first_comision(variable_component: dict) -> Optional[float]:
    meses = variable_component.get("meses_comisiones") or []
    first = next((m for m in meses if isinstance(m, dict)), None)
    if first is not None:
        return first.get("comision")
    return None


# ---------------------------------------------------------------------------
# Desglose producto opex
# ---------------------------------------------------------------------------


def _build_desglose_producto_opex(opex_rows: list[Any], missing_fields: list) -> list[dict]:
    if not opex_rows:
        missing_fields.append("desglose_producto_opex")
        return []

    result = []
    for row in opex_rows:
        if not isinstance(row, dict):
            continue
        result.append({
            "producto": row.get("producto") or "",
            "costo_directo": _safe_float(row.get("costo_directo")),
            "costo_financiacion": _safe_float(row.get("costo_financiacion")),
            "polizas": _safe_float(row.get("polizas")),
            "ingreso_por_producto": _safe_float(_coalesce(
                row.get("ingreso_por_producto"), row.get("ingreso_producto")
            )),
        })

    return result


# ---------------------------------------------------------------------------
# Scenario / channel helpers
# ---------------------------------------------------------------------------


def _pick_selected_scenario(result: dict, scenario_map: dict) -> tuple[Optional[str], str]:
    candidates = [
        result.get("selected_view_id"),
        result.get("selected_scenario_id"),
        (result.get("vision_tarifas") or {}).get("selected_scenario_id"),
        (result.get("vision_tarifas") or {}).get("escenario_seleccionado"),
        (result.get("panel") or {}).get("escenario_seleccionado"),
        (result.get("resumen") or {}).get("escenario_seleccionado"),
    ]
    sources = [
        "persisted_selected_view_id",
        "persisted_selected_scenario_id",
        "persisted_selected_scenario_id",
        "persisted_escenario_seleccionado",
        "panel_escenario_seleccionado",
        "resumen_escenario_seleccionado",
    ]
    for candidate, source_label in zip(candidates, sources):
        scenario_id = _normalize_scenario_id(candidate)
        if scenario_id in scenario_map:
            return scenario_id, source_label

    if scenario_map:
        return next(iter(scenario_map)), "first_available_scenario"
    return "escenario_1", "fallback"


def _normalize_scenario_id(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    if isinstance(value, str) and value.startswith("escenario_"):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low == "total":
            return "total"
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits:
            return f"escenario_{int(digits)}"
    if isinstance(value, (int, float)):
        return f"escenario_{int(value)}"
    return None


def _scenario_number(meta: dict, index: int) -> int:
    scenario = meta.get("escenario")
    if isinstance(scenario, (int, float)) and int(scenario) > 0:
        return int(scenario)
    if isinstance(scenario, str):
        digits = "".join(ch for ch in scenario if ch.isdigit())
        if digits:
            return int(digits)
    return index


def _find_channel(meta: dict, canales: list[Any], fallback_index: int) -> dict:
    if not isinstance(canales, list):
        return {}
    target_name = str(meta.get("canal") or "").strip().lower()
    target_mode = str(meta.get("modalidad") or "").strip().lower()
    for channel in canales:
        if not isinstance(channel, dict):
            continue
        name = str(channel.get("nombre_canal") or "").strip().lower()
        mode = str(channel.get("modalidad") or "").strip().lower()
        product = str(channel.get("producto") or "").strip().lower()
        if target_name and target_name in {name, product} and (not target_mode or target_mode == mode):
            return channel
    if 0 <= fallback_index < len(canales) and isinstance(canales[fallback_index], dict):
        return canales[fallback_index]
    return {}


# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------


def _sanitize_invalid(value: Any, omitted_paths: list[str], path: str = "") -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else key
            cleaned[key] = _sanitize_invalid(item, omitted_paths, child_path)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_invalid(item, omitted_paths, f"{path}.{i}") for i, item in enumerate(value)]
    if _is_invalid_value(value):
        omitted_paths.append(path)
        return 0
    return value


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return 0.0
        return float(value)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0.0
        if value in _INVALID_STRINGS:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def _is_invalid_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip() in _INVALID_STRINGS
    if isinstance(value, float):
        return math.isnan(value) or math.isinf(value)
    return False


def _coalesce(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


__all__ = ["build_modelo_cobro_from_result"]
