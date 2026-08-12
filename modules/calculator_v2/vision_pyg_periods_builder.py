"""
Builder: convierte meses + totales almacenados en CosmosDB al formato periods[].

Formato de salida compatible con 003_response_con_cadena_a-pyg.json.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _or_none(v: Optional[float]) -> Optional[float]:
    """Devuelve None si el valor es 0 o None (para campos opcionales nulos)."""
    if v is None or v == 0.0:
        return None
    return v


def _period_ingresos(v: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ingreso_bruto": v.get("ingreso_bruto"),
        "ingreso_cadena_a": v.get("ingreso_cadena_a"),
        "ingreso_cadena_b": v.get("ingreso_cadena_b"),
        "ingreso_cadena_c": v.get("ingreso_cadena_c"),
        "contingencia_op": _or_none(v.get("contingencia_operativa_valor")),
        "contingencia_com": _or_none(v.get("contingencia_comercial_valor")),
        "markup": _or_none(v.get("markup_valor")),
        "descuento": _or_none(v.get("descuento_valor")),
        "imprevistos": v.get("imprevistos_valor"),
        "ingreso_fijo": v.get("ingreso_fijo"),
        "ingreso_por_comision": None,
        "ingreso_variable": v.get("ingreso_variable"),
        "ingreso_neto": v.get("ingreso_neto"),
    }


def _period_cadena_a(v: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "payroll": v.get("nomina_total_mensual"),
        "nomina_loaded": v.get("nomina_loaded_mensual"),
        "salario_fijo": v.get("salario_fijo_mensual"),
        "salario_variable": v.get("salario_variable_mensual"),
        "capacitacion_inicial": None,
        "capacitacion_rotacion": None,
        "examenes_medicos": None,
        "estudios_seguridad": None,
        "crucero": v.get("crucero_total_mensual"),
        "no_payroll": v.get("no_payroll_total_mensual"),
        "opex_fijo": v.get("opex_fijo_mensual"),
        "inversiones": v.get("inversiones_mensual"),
        "costos_fijos": v.get("costos_fijos_mensual"),
        "total_cadena_a": v.get("costo_cadena_a"),
    }


def _period_componente_financiero(v: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ica": v.get("ica_mensual"),
        "gmf": v.get("gmf_mensual"),
        "comision_administracion": v.get("comision_admin_hm"),
        "polizas_adicionales": v.get("polizas_adicionales_hm"),
        "costos_financieros": None,
        "total_componente_financiero": v.get("componente_financiero_total"),
    }


def _period_costos(v: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "costo_total": v.get("costo_total"),
        "cadena_a": _period_cadena_a(v),
        "cadena_b": {
            "total_cadena_b":    v.get("costo_cadena_b", 0),
            "componente_fijo":   v.get("componente_fijo_b"),
            "opex_fijo":         v.get("opex_fijo_b"),
            "inversiones":       v.get("inversiones_b"),
            "s_and_m":           v.get("sm_b"),
            "componente_variable": v.get("componente_variable_b"),
            "tarifa_canal":      v.get("tarifa_canal_b"),
            "opex_variable":     v.get("opex_variable_b"),
            "tasa_escalamiento": v.get("tasa_escalamiento_b"),
            "hitl":              v.get("hitl_b"),
        },
        "cadena_c": {
            "total_cadena_c":    v.get("costo_cadena_c", 0),
            "tarifa_proveedor":  v.get("tarifa_proveedor_c"),
            "costo_integracion": v.get("costo_integracion_c"),
            "opex_fijo":         v.get("opex_fijo_integ_c"),
            "inversiones":       v.get("inversiones_integ_c"),
            "equipo_integracion": v.get("equipo_integ_c"),
            "costo_variable":    v.get("costo_variable_c"),
            "tasa_escalamiento": v.get("tasa_escalamiento_c"),
            "opex_variable":     v.get("opex_var_integ_c"),
            "hitl":              v.get("hitl_c"),
        },
        "componente_financiero": _period_componente_financiero(v),
        "costo_por_comision": None,
    }


def _period_utilidad(v: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "contribucion": v.get("contribucion"),
        "contribucion_por_puesto": v.get("contribucion_por_puesto"),
        "porcentaje_contribucion": v.get("pct_contribucion"),
        "costo_fijo": None,
        "utilidad_neta": v.get("utilidad_neta"),
        "porcentaje_utilidad_neta": v.get("pct_utilidad_neta"),
    }


def build_vision_pyg_periods(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Construye la respuesta periods[] desde el doc almacenado en CosmosDB.

    El doc debe tener: meses[], totales{}, (opcionales) cliente, servicio, duracion_meses.
    """
    meses: List[Dict[str, Any]] = doc.get("meses", [])
    totales: Dict[str, Any] = doc.get("totales", {})

    periods = []
    for m in meses:
        mes_num = m.get("mes", 0)
        v: Dict[str, Any] = m.get("valores", {})
        periods.append({
            "index": mes_num,
            "label": f"Mes {mes_num}",
            "periodo": mes_num,
            "ingresos": _period_ingresos(v),
            "costos": _period_costos(v),
            "utilidad": _period_utilidad(v),
            "operativo": {"ramp_up": v.get("ramp_up_mes")},
        })

    totales_out = {
        "ingresos": _period_ingresos(totales),
        "costos": _period_costos(totales),
        "utilidad": _period_utilidad(totales),
        "operativo": {},
    }

    # estaciones_trabajo es constante por deal → leer del primer mes (la suma en totales no sirve)
    # Excel V2-8: 'Visión P&G'!J14 = SUM('Condiciones Cadena A'!$E$11:$S$11)
    estaciones_trabajo = None
    if meses:
        et = meses[0].get("valores", {}).get("estaciones_trabajo")
        estaciones_trabajo = et if et is not None else None

    return {"periods": periods, "totales": totales_out, "estaciones_trabajo": estaciones_trabajo}
