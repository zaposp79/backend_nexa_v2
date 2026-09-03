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
    "imprevistos_valor": ("ingresos", "imprevistos"),
    "ingreso_neto": ("ingresos", "ingreso_neto"),
}

_COSTOS_MAP = {
    "payroll_a": ("costos", "cadena_a", "payroll"),
    "no_payroll_a": ("costos", "cadena_a", "no_payroll"),
    "costo_a": ("costos", "cadena_a", "total_cadena_a"),
    "costo_b": ("costos", "cadena_b", "total_cadena_b"),
    "componente_fijo_b": ("costos", "cadena_b", "componente_fijo"),
    "opex_fijo_cadena_b": ("costos", "cadena_b", "opex_fijo"),
    "capex_cadena_b": ("costos", "cadena_b", "inversiones"),
    "sm_cadena_b": ("costos", "cadena_b", "s_and_m"),
    "componente_variable_b": ("costos", "cadena_b", "componente_variable"),
    "tarifa_canal_cadena_b": ("costos", "cadena_b", "tarifa_canal"),
    "opex_variable_cadena_b": ("costos", "cadena_b", "opex_variable"),
    "tasa_escalamiento_cadena_b": ("costos", "cadena_b", "tasa_escalamiento"),
    "hitl_cadena_b": ("costos", "cadena_b", "hitl"),
    "costo_c": ("costos", "cadena_c", "total_cadena_c"),
    "costo_cadena_c": ("costos", "cadena_c", "total_cadena_c"),
    # Claves v2 (Motor de Reglas): tarifa_canal_cadena_c, opex_fijo_cadena_c, etc.
    "tarifa_canal_cadena_c": ("costos", "cadena_c", "tarifa_proveedor"),
    "opex_fijo_cadena_c": ("costos", "cadena_c", "opex_fijo"),
    "capex_cadena_c": ("costos", "cadena_c", "inversiones"),
    "equipo_transversal_cadena_c": ("costos", "cadena_c", "equipo_integracion"),
    "tasa_escalamiento_cadena_c": ("costos", "cadena_c", "tasa_escalamiento"),
    "opex_variable_cadena_c": ("costos", "cadena_c", "opex_variable"),
    "hitl_cadena_c": ("costos", "cadena_c", "hitl"),
    # Claves legacy v1 (PricingEngine): por compatibilidad con resultados antiguos
    "tarifa_proveedor_c": ("costos", "cadena_c", "tarifa_proveedor"),
    "costo_integracion_c": ("costos", "cadena_c", "costo_integracion"),
    "opex_fijo_integ_c": ("costos", "cadena_c", "opex_fijo"),
    "inversiones_integ_c": ("costos", "cadena_c", "inversiones"),
    "equipo_integ_c": ("costos", "cadena_c", "equipo_integracion"),
    "costo_variable_c": ("costos", "cadena_c", "costo_variable"),
    "tasa_escalamiento_c": ("costos", "cadena_c", "tasa_escalamiento"),
    "opex_var_integ_c": ("costos", "cadena_c", "opex_variable"),
    "hitl_c": ("costos", "cadena_c", "hitl"),
    "ica": ("costos", "componente_financiero", "ica"),
    "gmf": ("costos", "componente_financiero", "gmf"),
    "comision_administracion": ("costos", "componente_financiero", "comision_administracion"),
    "polizas": ("costos", "componente_financiero", "polizas"),
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


def _ingresos_mes(vals: Dict[str, Any], comision_ventas: float) -> Dict[str, Any]:
    ingreso_bruto    = vals.get("ingreso_bruto") or 0.0
    pct_imprevistos  = vals.get("pct_imprevistos") or 0.0
    cont_op          = vals.get("contingencia_op") or 0.0
    cont_com         = vals.get("contingencia_com") or 0.0
    markup           = vals.get("markup_ingreso") or 0.0
    descuento        = vals.get("descuento_ingreso") or 0.0

    imprevistos = vals.get("imprevistos_valor")
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
        "ingreso_por_comision": comision_ventas,
        "ingreso_variable":    vals.get("ingreso_variable"),
        "ingreso_neto":        vals.get("ingreso_neto"),
    }


def _cadena_c_costos_mes(vals: Dict[str, Any]) -> Dict[str, Any]:
    """Desglose Cadena C desde valores del Motor de Reglas v2.

    Excel P&G rows 59-68:
      Costos Cadena C = Tarifa Proveedor + Costo Integración + Costo Variable
      Costo Integración = OPEX Fijo + Inversiones + Equipo de integración
      Costo Variable    = Tasa Escalamiento + OPEX Variable + HITL
    """
    tarifa      = vals.get("tarifa_canal_cadena_c") or 0.0
    opex_fijo   = vals.get("opex_fijo_cadena_c") or 0.0
    inversiones = vals.get("capex_cadena_c") or 0.0
    equipo      = vals.get("equipo_transversal_cadena_c") or 0.0
    tasa        = vals.get("tasa_escalamiento_cadena_c") or 0.0
    opex_var    = vals.get("opex_variable_cadena_c") or 0.0
    hitl        = vals.get("hitl_cadena_c") or 0.0

    costo_integracion = opex_fijo + inversiones + equipo
    costo_variable    = tasa + opex_var + hitl

    return {
        "total_cadena_c":     vals.get("costo_cadena_c"),
        "tarifa_proveedor":   tarifa or None,
        "costo_integracion":  costo_integracion or None,
        "opex_fijo":          opex_fijo or None,
        "inversiones":        inversiones or None,
        "equipo_integracion": equipo or None,
        "costo_variable":     costo_variable or None,
        "tasa_escalamiento":  tasa or None,
        "opex_variable":      opex_var or None,
        "hitl":               hitl or None,
    }


def _costos_mes(vals: Dict[str, Any], cts: Dict[str, float], costo_variable: float) -> Dict[str, Any]:
    nomina   = vals.get("nomina_total_mensual") or 0.0
    nopayroll = vals.get("no_payroll_total_mensual") or 0.0

    return {
        "costo_total": vals.get("costo_total"),
        "cadena_a": {
            "payroll":              nomina or None,
            "nomina_loaded":        vals.get("nomina_loaded_mensual"),
            "salario_fijo":         vals.get("salario_fijo_mensual"),
            "salario_variable":     vals.get("salario_variable_mensual"),
            "capacitacion_inicial": vals.get("capacitacion_inicial_mensual") or None,
            "capacitacion_rotacion": vals.get("capacitacion_rotacion_mensual") or None,
            "examenes_medicos":     vals.get("examenes_medicos_mensual") or None,
            "estudios_seguridad":   vals.get("estudios_seguridad_mensual") or None,
            "crucero":              _scale(cts["crucero_base"], nomina, cts["payroll_base"]),
            "no_payroll":           nopayroll or None,
            "opex_fijo":            _scale(cts["opex_fijo_base"], nopayroll, cts["no_payroll_base"]),
            "inversiones":          _scale(cts["inversiones_base"], nopayroll, cts["no_payroll_base"]),
            "costos_fijos":         _scale(cts["costos_fijos_base"], nopayroll, cts["no_payroll_base"]),
            "total_cadena_a":       vals.get("costo_cadena_a"),
            "recargos_horas_extra": vals.get("recargos_horas_extra_mensual") or None,
        },
        "cadena_b": {
            "total_cadena_b":      vals.get("costo_cadena_b"),
            "componente_fijo":     vals.get("componente_fijo_b"),
            "opex_fijo":           vals.get("opex_fijo_cadena_b"),
            "inversiones":         vals.get("capex_cadena_b"),
            "s_and_m":             vals.get("sm_cadena_b"),
            "componente_variable": vals.get("componente_variable_b"),
            "tarifa_canal":        vals.get("tarifa_canal_cadena_b"),
            "opex_variable":       vals.get("opex_variable_cadena_b"),
            "tasa_escalamiento":   vals.get("tasa_escalamiento_cadena_b"),
            "hitl":                vals.get("hitl_cadena_b"),
        },
        "cadena_c": _cadena_c_costos_mes(vals),
        "componente_financiero": {
            "ica":                     vals.get("ica_mensual") or vals.get("ica_hm"),
            "gmf":                     vals.get("gmf_mensual") or vals.get("gmf_hm"),
            "comision_administracion": vals.get("comision_admin_hm"),
            "polizas":                 vals.get("polizas_puras_hm"),
            "costos_financieros":      vals.get("costos_financiacion_mensual"),
            "total_componente_financiero": vals.get("componente_financiero_total"),
        },
        "costo_por_comision": costo_variable,
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
    
    servicio = result_doc.get("servicio", "").lower()
    meses_data   = result_doc.get("meses", [])
    totales_vals: Dict[str, Any] = result_doc.get("totales", {})
    cts = _cts_breakdown(result_doc.get("vision_cts") or {})
    vision_tarifas = result_doc.get("vision_tarifas")
    
    cobranzas = None  
    ventas_multicanal = None
    if(servicio == "saco" or servicio == "ventas multicanal"):
        ventas_multicanal = next((x["ventas_multicanal"] for x in vision_tarifas.get("escenarios", []) if x.get("ventas_multicanal") != [] and x.get("ventas_multicanal") != None), None)
        if(ventas_multicanal == None):
            ventas_multicanal = vision_tarifas.get("escenario_total").get("ventas_multicanal")
    
    if(servicio == "cobranzas"):
        cobranzas = next((x["honorarios_totales"] for x in vision_tarifas.get("escenarios", []) if x.get("honorarios_totales") != [] and x.get("honorarios_totales") != None), None)
        if(cobranzas == None):
            cobranzas = vision_tarifas.get("escenario_total").get("honorarios_totales")
        
    comisiones_por_mes = []
    costos_variables_por_mes = []
    if(servicio == "cobranzas"):
        comisiones_por_mes = next(x for x in cobranzas if x.get("concepto") == "Ingresos - Comisiones").get("meses") or []
    if(servicio == "saco" or servicio == "ventas multicanal"):
        comisiones_por_mes = next(x for x in ventas_multicanal if x.get("concepto") == "Comisión").get("meses") or []
        costos_variables_por_mes = next(x for x in ventas_multicanal if x.get("concepto") == "Costo Variable").get("meses") or []
    
    periods = []
    for m in meses_data:
        mes_num = m.get("mes", len(periods) + 1)
        vals: Dict[str, Any] = m.get("valores", {})
        comision_ventas = 0
        costo_variable = 0
        if(servicio == "saco" or servicio == "ventas multicanal"):
            comision_ventas = next((x["valor"] for x in comisiones_por_mes if x.get("mes") == str(mes_num)), 0)
            costo_variable = next((x["valor"] for x in costos_variables_por_mes if x.get("mes") == str(mes_num)), 0)
        if(servicio == "cobranzas"):
            comision_ventas = next((x["benchmark"] for x in comisiones_por_mes if x.get("mes") == str(mes_num)), 0)
        
        periods.append({
            "index":    mes_num,
            "label":    f"Mes {mes_num}",
            "periodo":  mes_num,
            "ingresos": _ingresos_mes(vals, comision_ventas),
            "costos":   _costos_mes(vals, cts, costo_variable),
            "utilidad": _utilidad_mes(vals),
            "operativo": {"ramp_up": vals.get("ramp_up_mes")},
        })

    # Totales: igual que un mes pero usando totales_vals
    # Para CTS el pro-rateo usa el acumulado de nomina/no_payroll
    nomina_tot    = totales_vals.get("nomina_total_mensual") or 0.0
    nopayroll_tot = totales_vals.get("no_payroll_total_mensual") or 0.0
    cts_tot = {k: v for k, v in cts.items()}  # mismas bases
    total_comision = 0
    total_costo_variable = 0
    
    if(servicio == "saco" or servicio == "ventas multicanal"):
        total_comision = sum(item.get("valor", 0) for item in comisiones_por_mes)
        total_costo_variable = sum(item.get("valor", 0) for item in costos_variables_por_mes)
    if(servicio == "cobranzas"):
        total_comision = sum(item.get("benchmark", 0) for item in comisiones_por_mes)
    
    
    totales = {
        "ingresos": _ingresos_mes(totales_vals, total_comision),
        "costos":   _costos_mes(totales_vals, cts_tot, total_costo_variable),
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

    # CTS scaling para campos derivados de los perfiles (crucero, opex, inversiones, costos_fijos).
    # nomina_loaded NO se escala con CTS porque el valor correcto ya está en totales_vals
    # como suma directa de los meses (nomina_loaded_mensual); escalarlo con nomina_tot
    # incluiría crucero y capacitación en el numerador → total ~N× incorrecto.
    totales["costos"]["cadena_a"].update({
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

    # Recomputar ratios: _calcular_totales los suma como números acumulados (incorrecto).
    # Excel V2-8: BJ83=BJ82/BJ14; BJ87=BJ31-BJ34-BJ86; BJ88=BJ87/BJ31
    _contribucion_total  = totales["utilidad"].get("contribucion") or 0.0
    _utilidad_neta_total = totales["utilidad"].get("utilidad_neta") or 0.0
    _ingreso_neto_total  = totales["ingresos"].get("ingreso_neto") or 0.0
    if estaciones_trabajo:
        totales["utilidad"]["contribucion_por_puesto"] = _contribucion_total / estaciones_trabajo
    if _ingreso_neto_total:
        totales["utilidad"]["porcentaje_contribucion"]  = _contribucion_total / _ingreso_neto_total
        totales["utilidad"]["porcentaje_utilidad_neta"] = _utilidad_neta_total / _ingreso_neto_total

    return {
        "version": "v2",
        "simulation_id": simulation_id or result_doc.get("simulation_id"),
        "header": {
            "cliente":             result_doc.get("cliente"),
            "servicio":            result_doc.get("servicio"),
            "tipo_cliente":        result_doc.get("tipo_cliente"),
            "antiguedad_cliente":  result_doc.get("antiguedad_cliente"),
            "periodo_pago":        result_doc.get("periodo_pago"),
            "fecha_inicio":        result_doc.get("fecha_inicio"),
            "duracion_meses":      result_doc.get("duracion_meses"),
            "ciudad":              result_doc.get("ciudad"),
            "sede":                result_doc.get("sede"),
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
