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

_OPERATIVO_MAP = {
    "rampup": ("operativo", "ramp_up"),
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
        "fecha_inicio": resumen.get("fecha_inicio"),
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


def _empty_operativo_bucket() -> Dict[str, Any]:
    return {}


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
        period["operativo"] = _empty_operativo_bucket()
        periods.append(period)
    return periods


def _build_totales() -> Dict[str, Any]:
    return {
        "ingresos": {},
        "costos": _empty_cost_buckets(),
        "utilidad": {},
        "operativo": _empty_operativo_bucket(),
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
    elif key in _OPERATIVO_MAP:
        period_path = _OPERATIVO_MAP[key]
        total_path = _OPERATIVO_MAP[key]
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


def _cts_breakdown(vision_cts: Dict[str, Any]) -> Dict[str, float]:
    """Pre-computa totales base del CTS para pro-rateo mensual."""
    perfiles = vision_cts.get("perfiles") or []
    return {
        "payroll_base":       vision_cts.get("payroll_total") or 0.0,
        "no_payroll_base":    vision_cts.get("no_payroll_total") or 0.0,
        "crucero_base":       sum(p.get("crucero", 0.0) for p in perfiles),
        "nomina_loaded_base": sum(p.get("salario_cargado", 0.0) for p in perfiles),
        "opex_fijo_base":     sum(p.get("opex_it", 0.0) for p in perfiles),
        "inversiones_base":   sum(p.get("inversiones", 0.0) for p in perfiles),
        "costos_fijos_base":  sum(p.get("costos_fijos", 0.0) for p in perfiles),
    }


def _scale(base: float, actual: float, denom: float) -> Optional[float]:
    """Pro-rateo lineal: base × (actual / denom). None si denominador es 0."""
    if not denom:
        return None
    return base * (actual / denom)


def _ingresos_mes(vals: Dict[str, Any]) -> Dict[str, Any]:
    ingreso_bruto    = vals.get("ingreso_bruto") or 0.0
    pct_imprevistos  = vals.get("pct_imprevistos") or 0.0
    cont_op          = vals.get("contingencia_op") or 0.0
    cont_com         = vals.get("contingencia_com") or 0.0
    markup           = vals.get("markup_ingreso") or 0.0
    descuento        = vals.get("descuento_ingreso") or 0.0

    imprevistos = vals.get("imprevistos_ingreso")
    if imprevistos is None and pct_imprevistos:
        imprevistos = pct_imprevistos * ingreso_bruto

    # Ingreso Fijo = ingreso_bruto + cont_op + cont_com + markup − descuento − imprevistos
    ingreso_fijo = (
        ingreso_bruto + cont_op + cont_com + markup - descuento - (imprevistos or 0.0)
    ) if ingreso_bruto else None

    return {
        "ingreso_bruto":       ingreso_bruto or None,
        "ingreso_cadena_a":    vals.get("ingreso_cadena_a"),
        "ingreso_cadena_b":    vals.get("ingreso_cadena_b"),
        "ingreso_cadena_c":    vals.get("ingreso_cadena_c"),
        "contingencia_op":     cont_op or None,
        "contingencia_com":    cont_com or None,
        "markup":              markup or None,
        "descuento":           descuento or None,
        "imprevistos":         imprevistos,
        "ingreso_fijo":        ingreso_fijo,
        "ingreso_por_comision": vals.get("ingreso_por_comision"),
        "ingreso_variable":    vals.get("ingreso_variable"),
        "ingreso_neto":        vals.get("ingreso_neto"),
    }


def _costos_mes(vals: Dict[str, Any], cts: Dict[str, float]) -> Dict[str, Any]:
    nomina   = vals.get("nomina_total_mensual") or 0.0
    nopayroll = vals.get("no_payroll_total_mensual") or 0.0

    return {
        "costo_total": vals.get("costo_total"),
        "cadena_a": {
            "payroll":              nomina or None,
            "nomina_loaded":        vals.get("nomina_loaded_mensual"),
            "salario_fijo":         vals.get("salario_fijo_mensual"),
            "salario_variable":     vals.get("salario_variable_mensual"),
            "capacitacion_inicial": vals.get("capacitacion_inicial"),
            "capacitacion_rotacion": vals.get("capacitacion_rotacion"),
            "examenes_medicos":     vals.get("examenes_medicos"),
            "estudios_seguridad":   vals.get("estudios_seguridad"),
            "crucero":              _scale(cts["crucero_base"], nomina, cts["payroll_base"]),
            "no_payroll":           nopayroll or None,
            "opex_fijo":            _scale(cts["opex_fijo_base"], nopayroll, cts["no_payroll_base"]),
            "inversiones":          _scale(cts["inversiones_base"], nopayroll, cts["no_payroll_base"]),
            "costos_fijos":         _scale(cts["costos_fijos_base"], nopayroll, cts["no_payroll_base"]),
            "total_cadena_a":       vals.get("costo_cadena_a"),
        },
        "cadena_b": {
            "total_cadena_b":   vals.get("costo_cadena_b"),
            "opex_fijo":        vals.get("opex_fijo_b"),
            "inversiones":      vals.get("inversiones_b"),
            "s_and_m":          vals.get("sm_b"),
            "tarifa_canal":     vals.get("tarifa_canal_b"),
            "tasa_escalamiento": vals.get("tasa_escalamiento_b"),
            "hitl":             vals.get("hitl_b"),
        },
        "cadena_c": {
            "total_cadena_c":    vals.get("costo_cadena_c"),
            "tarifa_proveedor":  vals.get("tarifa_proveedor_c"),
            "opex_fijo":         vals.get("opex_fijo_integ_c"),
            "inversiones":       vals.get("inversiones_integ_c"),
            "equipo_integracion": vals.get("equipo_integ_c"),
            "tasa_escalamiento": vals.get("tasa_escalamiento_c"),
            "opex_variable":     vals.get("opex_var_integ_c"),
            "hitl":              vals.get("hitl_c"),
        },
        "componente_financiero": {
            "ica":                     vals.get("ica_mensual") or vals.get("ica_hm"),
            "gmf":                     vals.get("gmf_mensual") or vals.get("gmf_hm"),
            "comision_administracion": vals.get("comision_admin_hm"),
            # R73 Excel P&G = ICA + GMF + Comisión + Pólizas_puras (no solo polizas_puras)
            "polizas_adicionales":     vals.get("polizas_adicionales_hm"),
            "costos_financieros":      vals.get("costos_financieros"),
            "total_componente_financiero": vals.get("componente_financiero_total"),
        },
        "costo_por_comision": vals.get("costo_por_comision"),
    }


def _utilidad_mes(vals: Dict[str, Any]) -> Dict[str, Any]:
    contribucion = vals.get("contribucion")
    estaciones   = vals.get("estaciones_trabajo") or 0.0
    cpp = vals.get("contribucion_por_puesto")
    if cpp is None and contribucion is not None and estaciones:
        cpp = contribucion / estaciones
    return {
        "contribucion":           contribucion,
        "contribucion_por_puesto": cpp,
        "porcentaje_contribucion": vals.get("pct_contribucion"),
        "costo_fijo":             vals.get("costo_fijo"),
        "utilidad_neta":          vals.get("utilidad_neta"),
        "porcentaje_utilidad_neta": vals.get("pct_utilidad_neta"),
    }


def _build_from_v2_result(
    result_doc: Dict[str, Any],
    simulation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Construye el contrato de pantalla desde un resultado del Motor de Reglas (v2).

    Expone todos los campos de la Visión P&G (Excel V2-8 'Visión P&G' filas 18-88),
    incluyendo campos derivados del CTS y campos nulos donde no hay datos disponibles.
    """
    meses_data   = result_doc.get("meses", [])
    totales_vals: Dict[str, Any] = result_doc.get("totales", {})
    cts = _cts_breakdown(result_doc.get("vision_cts") or {})

    periods = []
    for m in meses_data:
        mes_num = m.get("mes", len(periods) + 1)
        vals: Dict[str, Any] = m.get("valores", {})
        periods.append({
            "index":    mes_num,
            "label":    f"Mes {mes_num}",
            "periodo":  mes_num,
            "ingresos": _ingresos_mes(vals),
            "costos":   _costos_mes(vals, cts),
            "utilidad": _utilidad_mes(vals),
            "operativo": {"ramp_up": vals.get("ramp_up_mes")},
        })

    # Totales: igual que un mes pero usando totales_vals
    # Para CTS el pro-rateo usa el acumulado de nomina/no_payroll
    nomina_tot    = totales_vals.get("nomina_total_mensual") or 0.0
    nopayroll_tot = totales_vals.get("no_payroll_total_mensual") or 0.0
    cts_tot = {k: v for k, v in cts.items()}  # mismas bases

    totales = {
        "ingresos": _ingresos_mes(totales_vals),
        "costos":   _costos_mes(totales_vals, cts_tot),
        "utilidad": _utilidad_mes(totales_vals),
        "operativo": {},
    }

    # imprevistos e ingreso_fijo no pueden derivarse desde totales_vals porque
    # _calcular_totales acumula pct_imprevistos como suma de porcentajes (0.10 × N meses),
    # lo que hace que la fórmula de fallback produzca un valor N veces mayor.
    # Se suman directamente los valores ya correctos de cada período mensual.
    _imp_total = sum((p["ingresos"].get("imprevistos") or 0.0) for p in periods)
    _if_total  = sum((p["ingresos"].get("ingreso_fijo") or 0.0) for p in periods)
    totales["ingresos"]["imprevistos"]  = _imp_total or None
    totales["ingresos"]["ingreso_fijo"] = _if_total  or None

    # Sobreescribir campos CTS en totales con escala acumulada
    totales["costos"]["cadena_a"].update({
        "nomina_loaded": _scale(cts["nomina_loaded_base"], nomina_tot, cts["payroll_base"]),
        "crucero":       _scale(cts["crucero_base"],       nomina_tot, cts["payroll_base"]),
        "opex_fijo":     _scale(cts["opex_fijo_base"],   nopayroll_tot, cts["no_payroll_base"]),
        "inversiones":   _scale(cts["inversiones_base"], nopayroll_tot, cts["no_payroll_base"]),
        "costos_fijos":  _scale(cts["costos_fijos_base"],nopayroll_tot, cts["no_payroll_base"]),
    })

    # estaciones_trabajo: constante por deal — leer del primer mes
    # Excel V2-8: 'Visión P&G'!J14 = SUM('Condiciones Cadena A'!$E$11:$S$11)
    estaciones_trabajo = None
    if meses_data:
        estaciones_trabajo = meses_data[0].get("valores", {}).get("estaciones_trabajo")

    return {
        "version": "v2",
        "simulation_id": simulation_id or result_doc.get("simulation_id"),
        "header": {
            "cliente":        result_doc.get("cliente"),
            "servicio":       result_doc.get("servicio"),
            "duracion_meses": result_doc.get("duracion_meses"),
            "fecha_inicio":   result_doc.get("fecha_inicio"),
        },
        "estaciones_trabajo": estaciones_trabajo,
        "periods":  periods,
        "totales":  totales,
        "metadata": {
            "source":              "motor_de_reglas_v2",
            "omitted_empty_fields": False,
        },
    }


def build_vision_pyg_from_result(
    pricing_result_dict: Optional[Dict[str, Any]],
    simulation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the public period-centric vision_pyg contract from persisted data."""
    doc = pricing_result_dict or {}

    # Motor de Reglas v2: estructura diferente (meses + totales planos)
    if doc.get("version") == "v2":
        return _build_from_v2_result(doc, simulation_id=simulation_id)

    # V1: vision_pyg con filas/secciones/fechas_meses
    vp_data = doc.get("vision_pyg") or {}

    periods = _build_periods(vp_data)
    totales = _build_totales()

    for row in _iter_rows(vp_data):
        _apply_row_to_contract(row, periods, totales)

    response = {
        "version": "v1",
        "simulation_id": simulation_id,
        "header": _build_header(vp_data),
        "estaciones_trabajo": vp_data.get("puestos_trabajo", 0.0),
        "periods": periods,
        "totales": totales,
        "metadata": {
            "source": "persisted_pricing_result",
            "omitted_empty_fields": True,
        },
    }
    return _prune_empty(response) or {}


__all__ = ["build_vision_pyg_from_result"]
