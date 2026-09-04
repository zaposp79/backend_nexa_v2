"""
Construye la Visión Tarifas / Modelo de Cobro para el Motor de Reglas v2.

Pure function: no IO, no DB, no Excel en tiempo de ejecución.
Fuente: Excel 'Vision Tarifas_Modelo_Cobro'!A1:I77

Estructura:
  - Resumen por escenario (cada perfil Cadena A = un escenario)
  - Detalle por escenario: costos Cadena A/B/C + tarifas calculadas
  - Total consolidado
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .escenarios_enricher import get_escenarios_activos_keys, _clave

from nexa_engine.modules.parametrizacion.services.resolver import (
    ParametrizationResolver,
)

_resolver = ParametrizationResolver()



# ── helpers internos ───────────────────────────────────────────────────────────

def _datos_op(request_data: Dict[str, Any]) -> Dict[str, Any]:
    return request_data.get("datos_operativos", {}) or {}

def _get_cobranzas() -> Dict[str, Any]:
    return _resolver.get_active_op().get("cobranzarango", []) or []

def _get_cost_parametrization() -> Dict[str, Any]:
    return _resolver.get_active_op().get("costo", {}) or {}

def _primer_mes_ramp1(meses: List[Dict]) -> Optional[Dict]:
    """Primer mes con ramp_up_mes >= 1.0 (régimen permanente pre-IPC)."""
    for m in meses:
        if float(m.get("valores", {}).get("ramp_up_mes", 0.0)) >= 1.0:
            return m
    return meses[-1] if meses else None


def _denominador_ingreso(
    margen: float,
    cont_op: float,
    cont_com: float,
    markup: float,
    descuento: float,
) -> float:
    """
    Denominador de la fórmula de ingreso desde costo.
    Excel 'Vision Tarifas_Modelo_Cobro'!C48:
      ingreso = costo / ((1-margen)*(1-cont_op)*(1-cont_com)*(1-markup)*(1+descuento))
    """
    denom = (1 - margen) * (1 - cont_op) * (1 - cont_com) * (1 - markup) * (1 + descuento)
    return denom if denom > 0 else 1.0


# ── Mapa perfil CTS por nombre ─────────────────────────────────────────────────

def _cts_map(cts_perfiles: List[Dict]) -> Dict[str, Dict]:
    return {p.get("nombre", ""): p for p in cts_perfiles}


def _empty_escenario(numero: int) -> dict:
    """Slot de escenario vacío (número configurado pero sin datos calculados)."""
    return {
        "id": f"Escenario {numero}",
        "nombre": None,
        "modalidad": None,
        "canal": None,
        "modelo_cobro": None,
        "componente_fijo": None,
        "pct_fijo": None,
        "componente_variable": None,
        "pct_variable": None,
        "fte": None,
        "desglose_costos_mensual": None,
        "facturacion_mensual": None,
        "ingreso_fijo_mensual": None,
        "ingreso_variable_mensual": None,
        "tarifa_componente_fijo": None,
        "tarifa_componente_variable": None,
    }


# ── Detalle de un escenario (perfil) ──────────────────────────────────────────

def _build_escenario(
    idx: int,
    perfil_input: Dict[str, Any],
    cts_p: Optional[Dict[str, Any]],
    margen_a: float,
    margen_b: float,
    margen_c: float,
    cont_op: float,
    cont_com: float,
    markup: float,
    descuento: float,
    costo_b_mensual: float,
    costo_c_mensual: float,
    request_data: Dict[str, Any]
) -> dict:
    """
    Construye el objeto de un escenario (= un perfil de Cadena A).

    Tarifas:
      - tarifa_fija = ingreso_total * pct_fijo / fte  (cuando componente_fijo = 'FTE')
      - tarifa_por_minuto = ingreso_total * pct_fijo / minutos_loggeados  (componente 'Tiempo')
      - tarifa_variable:
          * Transacción → ingreso_variable / volumen_transacciones
          * Resultados / Honorarios → porcentaje de ingreso (commission_rate)
          * default → None
    Excel 'Vision Tarifas_Modelo_Cobro'!G45, G55 — tarifas por escenario activo.
    """
    nombre = str(perfil_input.get("nombre", f"Escenario {idx + 1}"))
    canal = str(perfil_input.get("canal", ""))
    modalidad = str(perfil_input.get("modalidad", ""))
    fte = int(float(perfil_input.get("fte", 0)))
    fte_safe = max(fte, 1)

    modelo_cobro = str(perfil_input.get("modelo_cobro", "Fijo"))
    pct_var = float(perfil_input.get("pct_variable", 0.0))
    pct_fijo = round(1.0 - pct_var, 6)
    componente_fijo = str(perfil_input.get("componente_fijo", "FTE")) if pct_fijo > 0 else None
    componente_variable = str(perfil_input.get("componente_variable", "")) if pct_var > 0 else None

    # Costos Cadena A (del CTS)
    payroll = float(cts_p.get("payroll", 0.0)) if cts_p else 0.0
    no_payroll = float(cts_p.get("no_payroll", 0.0)) if cts_p else 0.0
    financiero = float(cts_p.get("costo_financiacion", 0.0)) if cts_p else 0.0
    ica = float(cts_p.get("ica", 0.0)) if cts_p else 0.0
    gmf = float(cts_p.get("gmf", 0.0)) if cts_p else 0.0
    comision_por_administracion = float(cts_p.get("comision_administracion", 0.0)) if cts_p else 0.0
    polizas = float(cts_p.get("polizas", 0.0)) if cts_p else 0.0
    costo_a = float(cts_p.get("costo_total", 0.0)) if cts_p else (payroll + no_payroll + financiero)
    
    # Costos Cadena B (del CTS) TODO Fix these values
    componente_fijo_b = float(cts_p.get("componente_fijo_b", 0.0)) if cts_p else 0.0
    componente_variable_b = float(cts_p.get("componente_variable_b", 0.0)) if cts_p else 0.0
    financiero_b = float(cts_p.get("financiero_b", 0.0)) if cts_p else 0.0
    ica_b = float(cts_p.get("ica_b", 0.0)) if cts_p else 0.0
    gmf_b = float(cts_p.get("gmf_b", 0.0)) if cts_p else 0.0
    comision_por_administracion_b = float(cts_p.get("comision_administracion_b", 0.0)) if cts_p else 0.0
    polizas_b = float(cts_p.get("polizas_b", 0.0)) if cts_p else 0.0
    costo_b = float(cts_p.get("costo_total_b", 0.0)) if cts_p else (componente_fijo_b + componente_variable_b + financiero_b)

    # Costos Cadena C (del CTS) TODO Fix these values
    componente_fijo_c = float(cts_p.get("componente_fijo_c", 0.0)) if cts_p else 0.0
    componente_variable_c = float(cts_p.get("componente_variable_c", 0.0)) if cts_p else 0.0
    financiero_c = float(cts_p.get("financiero_c", 0.0)) if cts_p else 0.0
    ica_c = float(cts_p.get("ica_c", 0.0)) if cts_p else 0.0
    gmf_c = float(cts_p.get("gmf_c", 0.0)) if cts_p else 0.0
    comision_por_administracion_c = float(cts_p.get("comision_administracion_c", 0.0)) if cts_p else 0.0
    polizas_c = float(cts_p.get("polizas_c", 0.0)) if cts_p else 0.0
    costo_c = float(cts_p.get("costo_total_c", 0.0)) if cts_p else (componente_fijo_c + componente_variable_c + financiero_c)

    # Ingreso Cadena A: desde CTS (ya resuelve circularidad HM)
    # Excel 'Vision Tarifas_Modelo_Cobro'!C48: ingreso_a = costo_a / denominador
    ingreso_a = float(cts_p.get("ingreso", 0.0)) if cts_p else 0.0
    if ingreso_a == 0.0 and costo_a > 0:
        denom_a = _denominador_ingreso(margen_a, cont_op, cont_com, markup, descuento)
        ingreso_a = costo_a / denom_a

    # Cadena B y C (para este perfil se asume 0 — los costos B/C son deal-level, no por perfil)
    # Excel 'Vision Tarifas_Modelo_Cobro'!C59: ingreso_b = costo_b / denominador_b
    ingreso_b = 0.0
    if costo_b_mensual > 0:
        denom_b = _denominador_ingreso(margen_b, cont_op, cont_com, markup, descuento)
        ingreso_b = costo_b_mensual / denom_b

    ingreso_c = 0.0
    if costo_c_mensual > 0:
        denom_c = _denominador_ingreso(margen_c, cont_op, cont_com, markup, descuento)
        ingreso_c = costo_c_mensual / denom_c

    facturacion_total = ingreso_a + ingreso_b + ingreso_c

    # Ingreso por componente (Excel fila 43/53: Ingreso Componente Fijo = Facturación × pct_fijo)
    ingreso_fijo = facturacion_total * pct_fijo
    ingreso_variable = facturacion_total * pct_var

    # Tarifa Componente Fijo (Excel G45)
    tarifa_fija: Optional[float] = None
    tipo_tarifa_fija: Optional[str] = None
    if pct_fijo > 0 and ingreso_fijo > 0:
        if componente_fijo == "FTE":
            tarifa_fija = round(ingreso_fijo / fte_safe, 2)
            tipo_tarifa_fija = "por FTE"
        elif componente_fijo == "Tiempo":
            minutos = float(perfil_input.get("minutos_loggeados_mes", 0) or 0)
            if minutos > 0:
                tarifa_fija = round(ingreso_fijo / minutos, 4)
                tipo_tarifa_fija = "por minuto loggeado"
            else:
                tarifa_fija = round(ingreso_fijo / fte_safe, 2)
                tipo_tarifa_fija = "por FTE (sin minutos)"

    # Tarifa Componente Variable (Excel G55)
    tarifa_variable: Optional[float] = None
    tipo_tarifa_variable: Optional[str] = None
    volumen_minimo: Optional[float] = None
    if pct_var > 0 and ingreso_variable > 0:
        if componente_variable == "Transacción":
            volumen = float(perfil_input.get("volumen_transacciones_mes", 0) or 0)
            if volumen > 0:
                tarifa_variable = round(ingreso_variable / volumen, 4)
                tipo_tarifa_variable = "por Transacción"
                volumen_minimo = volumen
        elif componente_variable in ("Resultados", "Honorarios"):
            commission_rate = float(perfil_input.get("commission_rate", 0) or 0)
            if commission_rate > 0:
                tarifa_variable = round(commission_rate, 4)
                tipo_tarifa_variable = "comisión por resultado"
            else:
                tarifa_variable = round(ingreso_variable / fte_safe, 2)
                tipo_tarifa_variable = "por persona (Resultados)"
                
    
    honorariosCobranza = []
    honorariosTotales = []
    ventas_multicanal = []
    desglose_componente_fijo = {}
    pct_variable = perfil_input.get("pct_variable", 0.0)
    servicio = request_data.get("datos_operativos", {}).get("servicio", "").lower()
    if(servicio == "cobranzas"):
        honorariosCobranza = _build_honorarios_cobranza(request_data, ingreso_variable)
        honorariosTotales = _build_honorarios_totales(honorariosCobranza, request_data)
        
    if(servicio == "saco" or servicio == "ventas multicanal"):
        ventas_multicanal = _build_ventas_multicanal(request_data, facturacion_total, pct_variable)
    
    desglose_componente_fijo = _build_desglose_componente_fijo(request_data, fte)
    return {
        "id": str(perfil_input.get("escenario_nombre") or f"Escenario {idx + 1}"),
        "nombre": nombre,
        "modalidad": modalidad,
        "canal": canal,
        "modelo_cobro": modelo_cobro,
        "componente_fijo": componente_fijo,
        "pct_fijo": round(pct_fijo, 4),
        "componente_variable": componente_variable,
        "pct_variable": round(pct_var, 4),
        "fte": fte,
        "desglose_costos_mensual": {
            "payroll": round(payroll, 2),
            "no_payroll": round(no_payroll, 2),
            "financiero": round(financiero, 2),
            "costo_total": round(costo_a, 2),
            "ica": round(ica, 2),
            "gmf": round(gmf, 2),
            "comision_por_administracion": round(comision_por_administracion, 2),
            "polizas": round(polizas, 2),
        },
        "desglose_costos_mensual_b": {
            "componente_fijo": round(componente_fijo_b, 2),
            "componente_variable": round(componente_variable_b, 2),
            "financiero": round(financiero_b, 2),
            "costo_total": round(costo_b, 2),
            "ica": round(ica_b, 2),
            "gmf": round(gmf_b, 2),
            "comision_por_administracion": round(comision_por_administracion_b, 2),
            "polizas": round(polizas_b, 2),
        },
        "desglose_costos_mensual_c": {
            "componente_fijo": round(componente_fijo_c, 2),
            "componente_variable": round(componente_variable_c, 2),
            "financiero": round(financiero_c, 2),
            "costo_total": round(costo_c, 2),
            "ica": round(ica_c, 2),
            "gmf": round(gmf_c, 2),
            "comision_por_administracion": round(comision_por_administracion_c, 2),
            "polizas": round(polizas_c, 2),
        },
        "facturacion_mensual": round(facturacion_total, 2),
        "ingreso_fijo_mensual": round(ingreso_fijo, 2),
        "ingreso_variable_mensual": round(ingreso_variable, 2),
        "tarifa_componente_fijo": {
            "tipo": tipo_tarifa_fija,
            "valor": tarifa_fija,
        } if tarifa_fija is not None else None,
        "tarifa_componente_variable": {
            "tipo": tipo_tarifa_variable,
            "valor": tarifa_variable,
            "volumen_minimo": volumen_minimo,
        } if tarifa_variable is not None else None,
        "honorarios_cobranza": honorariosCobranza,
        "honorarios_totales": honorariosTotales,
        "ventas_multicanal": ventas_multicanal,
        "desglose_componente_fijo": desglose_componente_fijo
    }

def _build_escenario_total(data: Dict[str, Any],request_data: Dict[str, Any], fte_total: float, escenarios: List[dict], facturacion_total: float) -> dict:
    
    servicio = request_data.get("datos_operativos", {}).get("servicio", "").lower()
    componente_fijo = str(data.get("componente_fijo", "FTE")) if data.get("proporcion_componente_fijo", 0.0) > 0 else None
    pct_var = float(data.get("proporcion_componente_variable", 0.0))
    pct_fijo = float(data.get("proporcion_componente_fijo", 0.0))
    facturacion_directa = sum(
        float(escenario.get("facturacion_mensual", 0.0) or 0.0)
        for escenario in escenarios
        if escenario.get("facturacion_mensual")
    )
    if componente_fijo == "FTE":
        tarifa_fija = facturacion_directa / fte_total if fte_total > 0 else 0.0
    else:
        tarifa_fija = facturacion_directa
    
    ingreso_variable = facturacion_total * pct_var
    honorariosCobranza = []
    honorariosTotales = []
    ventas_multicanal = []
    desglose_componente_fijo = {}
    if(servicio == "cobranzas"):
        honorariosCobranza = _build_honorarios_cobranza(request_data, ingreso_variable)
        honorariosTotales = _build_honorarios_totales(honorariosCobranza, request_data)
            
    if(servicio == "saco" or servicio == "ventas multicanal"):
        ventas_multicanal = _build_ventas_multicanal(request_data, facturacion_total, pct_var)
        
    desglose_componente_fijo = _build_desglose_componente_fijo(request_data, fte_total)
        
    return {
        "escenario": "Total",
        "modalidad": None,
        "canal": None,
        "modelo_cobro": str(data.get("modelo_cobro", "")),
        "componente_fijo": componente_fijo,
        "proporcion_componente_fijo_pct": pct_fijo,
        "componente_variable": str(data.get("componente_variable", "")),
        "proporcion_componente_variable_pct": pct_var,
        "facturacion_directa": round(facturacion_directa, 2),
        "tarifa_componente_fijo": tarifa_fija,
        "tarifa_componente_variable": 0,
        "honorarios_cobranza": honorariosCobranza,
        "honorarios_totales": honorariosTotales,
        "ventas_multicanal": ventas_multicanal,
        "desglose_componente_fijo": desglose_componente_fijo
    }

# ── Totales consolidados ──────────────────────────────────────────────────────

def _build_total(escenarios: List[dict], cts_perfiles: List[Dict]) -> dict:
    """
    Total del deal.
    Excel 'Vision Tarifas_Modelo_Cobro'!H19-H21 — columna 'Total'.
    """
    # Ignorar slots vacíos (facturacion_mensual=None) en los totales
    active = [e for e in escenarios if e.get("facturacion_mensual") is not None]
    fte_total = sum(e.get("fte", 0) or 0 for e in active)
    facturacion_total = sum(e.get("facturacion_mensual", 0.0) or 0.0 for e in active)
    ingreso_fijo_total = sum(e.get("ingreso_fijo_mensual", 0.0) or 0.0 for e in active)
    ingreso_var_total = sum(e.get("ingreso_variable_mensual", 0.0) or 0.0 for e in active)

    fte_safe = max(fte_total, 1)
    tarifa_fija_total = round(ingreso_fijo_total / fte_safe, 2) if ingreso_fijo_total else None

    return {
        "fte_total": fte_total,
        "facturacion_mensual": round(facturacion_total, 2),
        "ingreso_fijo_mensual": round(ingreso_fijo_total, 2),
        "ingreso_variable_mensual": round(ingreso_var_total, 2),
        "tarifa_fija": tarifa_fija_total,
    }

def add_month_value(concepts, concepto, mes, valor):
    concepts[concepto]["meses"].append({
        "mes": mes,
        "valor": valor
    })
    
def get_value_by_month(list, month):
    return next(x["valor"] for x in list if x["mes"] == month)
    
def _build_ventas_multicanal(request_data: Dict[str, Any], total_income: float, pct_variable: float) -> List[dict]:
    """Construye los honorarios por antigüedad desde la lista de cobranzas."""

    nPersons = request_data.get("saco_multicanal", {}).get("numero_de_asesores")
    configurations = (request_data.get("saco_multicanal", {}) or {}).get("configuraciones", []) or []
    incomes_by_agent = next((x for x in configurations if x["concepto"] == "Ingreso Variable x Asesor"),{})
    benefits_charges = next((x for x in configurations if x["concepto"] == "Carga Prestacional"),{})
    aius = next((x for x in configurations if x["concepto"] == "AIU"),{})
    quantityList = next((x for x in configurations if x["concepto"] == "Cantidad Total de Ventas"),{})
   
    concept_config = {
        "Crecimiento del cobro a riesgo": {"format": "percent", "type": "Bold"},
        "Valor Variable": {"format": "currency", "type": "Bold"},
        "Valor fijo": {"format": "currency", "type": "Bold"},
        "Total a cubrir": {"format": "currency", "type": "Bold"},
        "AIU": {"format": "percent", "type": "Normal"},
        "Valor Carga Prestacional": {"format": "currency", "type": "Normal"},
        "Valor Total (Comisión por asesor)": {"format": "currency", "type": "Normal"},
        "Comisión": {"format": "currency", "type": "Bold"},
        "Costo Variable": {"format": "currency", "type": "Bold"},
        "Costo Total": {"format": "currency", "type": "Bold"},
        "Ingreso por persona": {"format": "currency", "type": "Bold"},
        "Costo por Millon Desembolsado": {"format": "currency", "type": "Bold"},
        "Mínimo de Ventas": {"format": "currency", "type": "Bold"},
    }

    concepts = {
        concept: {
            "concepto": concept,
            "formato": config["format"],
            "tipo": config["type"],
            "meses": []
        }
        for concept, config in concept_config.items()
    }
   
    details = benefits_charges.get("detalle",[])
    previous_growth_risk = 0
    for index, item in enumerate(details):
        
        if not isinstance(item, dict):
            continue
    

        growthRisk = fixed_value = variable_value = total_to_cover = 0
        aiu_value = commision_by_agent = commision = 0

        # Growth Risk
        if index + 1 == len(details):
            growthRisk = pct_variable
        elif index > 0:
            growthRisk = previous_growth_risk + (
                pct_variable / (len(details) - 1)
            )

        previous_growth_risk = growthRisk

        # Valores base
        fixed_value = total_income * growthRisk

        total_quantity_sales = get_value_by_month(
            quantityList.get("detalle", []),
            item["mes"]
        )

        income_agent = get_value_by_month(
            incomes_by_agent.get("detalle", []),
            item["mes"]
        )

        benefit_charge_pct = get_value_by_month(
            benefits_charges.get("detalle", []),
            item["mes"]
        )

        benefit_charge_value = income_agent * benefit_charge_pct

        commision_by_agent = income_agent + benefit_charge_value

        # Variable value depende de commission by agent
        variable_value = commision_by_agent * nPersons

        # Total a cubrir depende de fixed y variable
        total_to_cover = fixed_value + variable_value

        # AIU depende de total_to_cover y variable_value
        if growthRisk == 0:
            aiu_value = get_value_by_month(
                aius.get("detalle", []),
                item["mes"]
            )
        else:
            aiu_value = (
                (total_to_cover / variable_value) - 1
                if variable_value > 1
                else 0
            )

        # Commission depende de AIU
        commision = (
            commision_by_agent *
            (1 + aiu_value) *
            nPersons
        )

        # Total depende de commission
        total = (
            commision + (total_income * (1 - growthRisk))
            if commision > 0
            else 0
        )

        income_by_person = (
            commision / nPersons
            if nPersons
            else 0
        )

        cost_by_million = (
            total / (total_quantity_sales * nPersons)
            if total_quantity_sales and nPersons
            else 0
        )
        
        minimum_sales = (
            variable_value / cost_by_million
            if cost_by_million > 0
            else 0
        )
            
        add_month_value(concepts, "Crecimiento del cobro a riesgo", item["mes"], growthRisk)
        add_month_value(concepts, "Valor fijo", item["mes"], fixed_value)
        add_month_value(concepts, "Valor Variable", item["mes"], variable_value)
        add_month_value(concepts, "Total a cubrir", item["mes"], total_to_cover)
        add_month_value(concepts, "AIU", item["mes"], aiu_value)
        add_month_value(concepts, "Valor Carga Prestacional", item["mes"], benefit_charge_value)
        add_month_value(concepts, "Valor Total (Comisión por asesor)", item["mes"], commision_by_agent)
        add_month_value(concepts, "Comisión", item["mes"], commision)
        add_month_value(concepts, "Costo Variable", item["mes"], variable_value)
        add_month_value(concepts, "Costo Total", item["mes"], total)
        add_month_value(concepts, "Ingreso por persona", item["mes"], income_by_person)
        add_month_value(concepts, "Costo por Millon Desembolsado", item["mes"], cost_by_million)
        add_month_value(concepts, "Mínimo de Ventas", item["mes"], minimum_sales)
        
    return list(concepts.values())

def _build_desglose_componente_fijo(request_data: Dict[str, Any], fteEscenario: float) -> Dict[str, Any]:
    desglose = {}
    parametrization = _get_cost_parametrization()
    datos_op = _datos_op(request_data)
    pct_ausentismo = datos_op.get("pct_ausentismo", 0) or 0
    fte = fteEscenario

    # Configuración base
    horas_semanales = next((x["valor"] for x in parametrization if x["costooperativo"] == "Horas semanales"), 0)
    horas_formacion_mensuales = datos_op.get("horas_formacion_mes", 0) or 0
    semanas_mes = next((x["valor"] for x in parametrization if x["costooperativo"] == "Semanas al mes"), 0)
    initial_break = 30

    desglose["configuracion"] = {
        "horas_semanales": horas_semanales,
        "horas_formacion_mensuales": horas_formacion_mensuales,
        "semanas_mes": semanas_mes
    }

    # Minutos improductivos
    minutos_improductivos = []

    total_minutos_improductivos = 0
    total_pct_improductivos = 0
    initial_average = (((horas_formacion_mensuales/4)/6)*60)
    hours_calculated = ((horas_semanales / 6) * 60)
    initial_coaching = 5
    initial_active_pause = 5
    initial_logout = 5
    payed_hours_percent = 0.00
    
    break_pct = initial_break / hours_calculated
    average_pct = initial_average / hours_calculated
    logout_pct = initial_logout / hours_calculated
    couching_pct = initial_coaching / hours_calculated
    active_pause_pct = initial_active_pause / hours_calculated
    
    items = [
        ("2 break al día, cada uno de 15 minutos", initial_break, break_pct),
        ("Promedio de capacitaciones al día", initial_average, average_pct),
        ("Deslogueos", initial_logout, logout_pct),
        ("Coaching al día", initial_coaching, couching_pct),
        ("Pausa activa al día", initial_active_pause, active_pause_pct),
    ]

    for concepto, minutos, porcentaje in items:
        minutos_improductivos.append({
            "concepto": concepto,
            "tiempo_minutos": minutos,
            "porcentaje": porcentaje
        })

        total_minutos_improductivos += minutos
        total_pct_improductivos += porcentaje

    desglose["minutos_improductivos"] = {
        "detalle": minutos_improductivos,
        "total_minutos": total_minutos_improductivos,
        "total_porcentaje": total_pct_improductivos
    }

    # Tiempo Programado
    tiempo_programado_horas = horas_semanales * semanas_mes * fte
    tiempo_programado_minutos = tiempo_programado_horas * 60

    desglose["tiempo_programado"] = {
        "horas": tiempo_programado_horas,
        "minutos": tiempo_programado_minutos
    }

    # Resumen
    resumen = []
    
    
    payed_hours = tiempo_programado_horas * (1-payed_hours_percent)
    logged_hours_pct = break_pct + average_pct + logout_pct
    
    ausentismo_hours = payed_hours * (1-pct_ausentismo)
    logged_hours = ausentismo_hours * (1-logged_hours_pct)
    
    productive_hours_pct = couching_pct + active_pause_pct
    productive_hours = logged_hours * (1-productive_hours_pct)

    rows = [
        {
            "concepto": "Horas pagadas",
            "porcentaje": payed_hours_percent,
            "horas": payed_hours,
            "minutos": payed_hours * 60
        },
        {
            "concepto": "Horas de Ausentismo",
            "porcentaje": pct_ausentismo,
            "horas": ausentismo_hours,
            "minutos": ausentismo_hours * 60
        },
        {
            "concepto": "Horas logueadas",
            "porcentaje": logged_hours_pct,
            "horas": logged_hours,
            "minutos": logged_hours * 60
        },
        {
            "concepto": "Horas productivas",
            "porcentaje": productive_hours_pct,
            "horas": productive_hours,
            "minutos": productive_hours * 60
        }
    ]

    for row in rows:
        resumen.append(row)

    desglose["resumen"] = resumen

    return desglose
    

def _build_honorarios_cobranza(request_data: Dict[str, Any], componente_variable: float) -> List[dict]:
    """Construye los honorarios por antigüedad desde la lista de cobranzas."""
    bechmarkList = _get_cobranzas()
    cobranzas = request_data.get("cobranzas", {}) or {}
    rangos_cartera = cobranzas.get("rangos_de_cartera", []) if isinstance(cobranzas, dict) else []
    porcentaje_cartera = cobranzas.get("porcentaje_considerando_caidas", 0.0) if isinstance(cobranzas, dict) else 0.0
    firstMonth = next((x["valor"] for x in porcentaje_cartera if x["mes"] == "1"),0)
    
    result = []
    sum_product = 0
    componente_variable_escenario = componente_variable

    for index, item in enumerate(rangos_cartera):
        if not isinstance(item, dict):
            continue

        denominator = (
            float(item.get("contactabilidad", 0) or 0)
            * float(item.get("efectividad", 0) or 0)
        )
        dificultad = 0 if denominator == 0 else 1 / denominator
        
        valueFirstMonth = float(item.get("cantidad_calculada", 0)) * firstMonth
        arpu = float(item.get("arpu", 0))
        sum_product += dificultad * arpu * valueFirstMonth
        
        benchmark_value = (
            float(bechmarkList[index].get("honorarios", 0) or 0)
            if index < len(bechmarkList)
            else 0.0
        )


        result.append({
            "antiguedadCartera": item.get("rango_de_cartera"),
            "driver_dificultad": dificultad,
            "calculado": 0.0,
            "benchmark": benchmark_value,
            "arpu": arpu, #Cals total
            "cantidad_calculada": item.get("cantidad_calculada", 0),  #Cals total
        })
        
    for item in result:
        item["calculado"] = (
            (item["driver_dificultad"] * componente_variable_escenario)
            / sum_product
            if sum_product > 0 else 0.0
        )

    return result

def _get_value_business(data: Dict[str, Any]) -> float:
    return data.get("valor",0.0)

def _build_desglose_producto_opex(
    request_data: list[Any]
) -> list[dict]:
   
    business_rules = request_data.get("reglas_negocio",{})
    objetive_margin = business_rules.get("margen_objetivo",{})
    operative_contingency = business_rules.get("contingencia_operativa",{})
    commercial_contingency = business_rules.get("contingencia_comercial",{})
    markup = business_rules.get("markup",{})
    volumen_discount = business_rules.get("descuento_volumen",{})
    monthly_interes = request_data.get("volumetria", {}).get("indexacion", {}).get("tasa_interes_mensual", [])
    datos_op = _datos_op(request_data)
    ica = datos_op.get("tasa_ica",0)
    gmf = datos_op.get("tasa_gmf",0)
    payment_period = datos_op.get("periodo_pago")
    margin_chain_b = objetive_margin.get("cadena_b",0) 
    margin_chain_a = objetive_margin.get("cadena_a",0)
    policies = request_data.get("polizas",[])
    sumproductPolicies = sum(
        (item.get("pct_poliza", 0) or 0) *
        (item.get("pct_atribuible", 0) or 0)
        for item in policies
        if item.get("activa")
    )
    
    factor_increase = {
        30: 1.0,
        45: 1.5,
        60: 2.0,
        90: 3.0,
    }.get(payment_period, 4.0)
    
    business_rules_chain_a =  ((1-margin_chain_a)*
                              (1-_get_value_business(operative_contingency))
                              *(1-_get_value_business(commercial_contingency))
                              *(1-_get_value_business(markup))
                              *(1-_get_value_business(volumen_discount)))
    
    products =request_data.get("condiciones_cadena_b",{}).get("opex",{}).get("items",[])
    result = [
        {
            "concepto": "Costo Directo",
            "products": [],
        },
        {
            "concepto": "Costo de financiación",
            "products": [],
        },
        {
            "concepto": "Polizas",
            "products": [],
        },
        {
            "concepto": "Ingreso por producto",
            "products": [],
        },
    ]

    for row in products:
        if not isinstance(row, dict):
            continue
        
        producto = row.get("producto") or ""
        total_value = row.get("valor_total") or 0.0
        financiation = total_value * factor_increase * float(monthly_interes) if monthly_interes else 0.0
       
        
        policies_product = ((total_value + financiation) / 
                business_rules_chain_a)*sumproductPolicies 
        
        ica_product = ((total_value + financiation + policies_product) /
                 business_rules_chain_a)*ica 
        
        gmf_product = ((total_value + financiation + policies_product) * gmf)
               

        policies = policies_product + ica_product + gmf_product
        
        result[0]["products"].append({
            "name": producto,
            "valor": total_value, 
        })

        result[1]["products"].append({
            "name": producto,
            "valor": financiation, 
        })

        result[2]["products"].append({
            "name": producto,
            "valor": policies,
        })

        result[3]["products"].append({
            "name": producto,
            "valor": (total_value + financiation + policies) / (1 - margin_chain_b),
        })

    return result

def _build_honorarios_totales(honorarios: Dict[str, Any], request_data: Dict[str, Any]) -> List[dict]:
    cobranzas = request_data.get("cobranzas", {}) or {}
    porcentaje_cartera = cobranzas.get("porcentaje_considerando_caidas", 0.0) if isinstance(cobranzas, dict) else 0.0
    resultado = {
        "Ingresos - Comisiones": {
            "concepto": "Ingresos - Comisiones",
            "meses": []
        },
        "Ingreso por persona": {
            "concepto": "Ingreso por persona",
            "meses": []
        }
    }
    personas = cobranzas.get("numero_de_asesores", 0) if isinstance(cobranzas, dict) else 0

    for month in porcentaje_cartera:
        mes = month["mes"]

        sum_product_benchmark = 0
        sum_product_calculated = 0

        for item in honorarios:
            arpu = float(item.get("arpu", 0))
            cantidad_mes = float(item.get("cantidad_calculada", 0)) * float(month.get("valor", 0))

            sum_product_benchmark += (
                arpu * cantidad_mes * float(item.get("benchmark", 0))
            )

            sum_product_calculated += (
                arpu * cantidad_mes * float(item.get("calculado", 0))
            )

        # Concepto 1
        resultado["Ingresos - Comisiones"]["meses"].append({
            "mes": mes,
            "benchmark": sum_product_benchmark,
            "calculado": sum_product_calculated
        })

        # Concepto 2
        resultado["Ingreso por persona"]["meses"].append({
            "mes": mes,
            "benchmark": sum_product_benchmark / personas if personas else 0,
            "calculado": sum_product_calculated / personas if personas else 0
        })
   
    return list(resultado.values())
    
# ── Entry point ───────────────────────────────────────────────────────────────

def build_vision_tarifas(
    request_data: Dict[str, Any],
    meses: List[Dict],
    totales: Dict[str, float],
    duracion_meses: int,
    cts_perfiles: Optional[List[Dict]] = None,
) -> dict:
    """Construye el dict completo de Visión Tarifas / Modelo de Cobro.

    Args:
        request_data: Dict original de la petición.
        meses: Lista de dicts {mes: int, valores: Dict[str, float]} del motor.
        totales: Acumulado del motor.
        duracion_meses: Número de meses del contrato.
        cts_perfiles: Perfiles de VisionCostToServe (costos + ingresos ya calculados).
    """
    vals0 = meses[0].get("valores", {}) if meses else {}

    # Parámetros de ajuste desde el contexto del motor
    margen_a = float(vals0.get("margen_a", 0.18))
    margen_b = float(vals0.get("margen_b", 0.30))
    margen_c = float(vals0.get("margen_c", 0.0))
    cont_op = float(vals0.get("cont_op", 0.0))
    cont_com = float(vals0.get("cont_com", 0.0))
    markup = float(vals0.get("markup", 0.0))
    descuento = float(vals0.get("descuento", 0.0))

    # Costos Cadena B y C mensuales a 100% ramp (agregar al total deal-level)
    mes_ramp1 = _primer_mes_ramp1(meses)
    vals_ramp1 = mes_ramp1.get("valores", {}) if mes_ramp1 else {}
    costo_b_mensual = float(vals_ramp1.get("costo_cadena_b", 0.0))
    costo_c_mensual = float(vals_ramp1.get("costo_cadena_c", 0.0))

    cadena_a = request_data.get("condiciones_cadena_a", {}) or {}
    all_perfiles = cadena_a.get("perfiles", []) or []

    esc_activos = get_escenarios_activos_keys(request_data)
    perfiles_input = list(all_perfiles)
    if esc_activos is not None:
        perfiles_input = [
            p for p in perfiles_input
            if _clave(p.get("canal"), p.get("modalidad")) in esc_activos
        ]

    fte_total_activos = sum(float(p.get("fte", 0) or 0) for p in perfiles_input)

    # Pesos por canal para distribuir costos B/C entre escenarios.
    # Primario: cadena_b/c.valor de volumetría.
    # Fallback: canales en condiciones sin cadena_c.valor usan cadena_a.valor como proxy
    # (replica el Excel: distribución 2 niveles Inbound/Outbound por volumen efectivo).
    def _vol_por_canal(cadena_key: str) -> Dict:
        vol_data = request_data.get("volumetria") or {}
        vol_primary: Dict = {}   # cadena_b/c.valor por canal
        vol_proxy: Dict = {}     # cadena_a.valor por canal (proxy para outbound sin cadena_c)

        for direction in ["inbound", "outbound"]:
            modalidad = direction.capitalize()
            for c in vol_data.get(direction, {}).get("canales", []):
                cn = str(c.get("canal") or "").strip()
                if not cn:
                    continue
                k = _clave(cn, modalidad)
                vol_primary[k] = vol_primary.get(k, 0.0) + float(
                    (c.get(cadena_key) or {}).get("valor", 0) or 0
                )
                vol_proxy[k] = vol_proxy.get(k, 0.0) + float(
                    (c.get("cadena_a") or {}).get("valor", 0) or 0
                )

        # Canales con datos en condiciones pero sin volumen primario:
        # usan cadena_a.valor como proxy de participación (misma lógica que el Excel).
        cond = request_data.get(f"condiciones_{cadena_key}") or {}
        if cadena_key == "cadena_c":
            items_lists = [
                cond.get("tarifa_proveedor_canal") or [],
                cond.get("opex") or [],
                cond.get("inversiones_capex") or [],
            ]
        else:  # cadena_b
            items_lists = [
                (cond.get("opex") or {}).get("items") or [],
                cond.get("inversiones_capex") or [],
            ]
        cond_keys: set = set()
        for items in items_lists:
            for item in (items if isinstance(items, list) else []):
                cn = str(item.get("canal") or "").strip()
                md = str(item.get("modalidad") or "").strip()
                if cn and md:
                    cond_keys.add(_clave(cn, md))

        result: Dict = {}
        all_keys = set(vol_primary.keys()) | cond_keys
        for k in all_keys:
            prim = vol_primary.get(k, 0.0)
            if prim > 0:
                result[k] = prim
            elif k in cond_keys:
                # proxy: cadena_a.valor si existe, sino 1.0 para garantizar participación
                result[k] = vol_proxy.get(k, 0.0) or 1.0
        return result

    vol_b_by_canal = _vol_por_canal("cadena_b")
    vol_c_by_canal = _vol_por_canal("cadena_c")
    total_vol_b = max(sum(vol_b_by_canal.values()), 1.0)
    total_vol_c = max(sum(vol_c_by_canal.values()), 1.0)

    cts_map = _cts_map(cts_perfiles or [])

    # Índice canal → perfil Cadena A (detecta si un escenario es Cadena A o B/C)
    perfil_por_canal: Dict = {
        _clave(p.get("canal"), p.get("modalidad")): p for p in perfiles_input
    }

    escenarios = []

    if esc_activos is not None:
        # Construir índice de escenarios_comerciales por slot
        esc_cfg_por_slot: Dict[int, Dict] = {}
        for _cfg in (request_data.get("escenarios_comerciales") or []):
            _n = int(_cfg.get("escenario") or 0)
            if 1 <= _n <= 5 and str(_cfg.get("canal") or "").strip():
                esc_cfg_por_slot[_n] = _cfg

        for n in sorted(esc_cfg_por_slot.keys()):
            cfg = esc_cfg_por_slot[n]
            canal_cfg = str(cfg.get("canal") or "").strip()
            modalidad_cfg = str(cfg.get("modalidad") or "").strip()
            canal_key = _clave(canal_cfg, modalidad_cfg)

            # Distribución volumen-proporcional de Cadena B/C para este canal
            weight_b = vol_b_by_canal.get(canal_key, 0.0) / total_vol_b
            weight_c = vol_c_by_canal.get(canal_key, 0.0) / total_vol_c
            b_for_esc = round(costo_b_mensual * weight_b, 2)
            c_for_esc = round(costo_c_mensual * weight_c, 2)

            p_input = perfil_por_canal.get(canal_key)
            if p_input is not None:
                # Canal con perfil Cadena A: cálculo completo con CTS
                nombre = str(p_input.get("nombre", f"Escenario {n}"))
                cts_p = cts_map.get(nombre)
            else:
                # Canal solo en Cadena B/C: perfil sintético con datos del escenario comercial
                prop_var = float(cfg.get("proporcion_componente_variable") or 0.0)
                prop_fijo = 1.0 - prop_var
                # Volumen para cálculo de tarifa variable (Transacción)
                vol_transacciones = vol_b_by_canal.get(canal_key, 0.0) or vol_c_by_canal.get(canal_key, 0.0)
                p_input = {
                    "nombre": f"Escenario {n}",
                    "canal": canal_cfg,
                    "modalidad": modalidad_cfg,
                    "modelo_cobro": cfg.get("modelo_cobro"),
                    "pct_variable": prop_var,
                    "componente_fijo": cfg.get("componente_fijo") if prop_fijo > 0 else None,
                    "componente_variable": cfg.get("componente_variable") if prop_var > 0 else None,
                    "escenario_nombre": f"Escenario {n}",
                    "fte": 0,
                    "volumen_transacciones_mes": vol_transacciones,
                    "commission_rate": float(cfg.get("commission_rate") or 0),
                }
                cts_p = None

            escenario = _build_escenario(
                idx=n - 1,
                perfil_input=p_input,
                cts_p=cts_p,
                margen_a=margen_a,
                margen_b=margen_b,
                margen_c=margen_c,
                cont_op=cont_op,
                cont_com=cont_com,
                markup=markup,
                descuento=descuento,
                costo_b_mensual=b_for_esc,
                costo_c_mensual=c_for_esc,
                request_data=request_data,
            )
            escenarios.append(escenario)

        # Colocar en 5 slots fijos (slots sin escenario configurado → vacíos)
        all_5 = [_empty_escenario(n) for n in range(1, 6)]
        for esc in escenarios:
            esc_id = esc.get("id", "")
            try:
                slot = int(esc_id.split()[-1]) - 1
                if 0 <= slot < 5:
                    all_5[slot] = esc
            except (ValueError, IndexError):
                pass
        escenarios = all_5

    else:
        # Modo legacy (sin escenarios_comerciales): distribución FTE-proporcional sobre Cadena A
        for i, p_input in enumerate(perfiles_input):
            nombre = str(p_input.get("nombre", f"Escenario {i + 1}"))
            cts_p = cts_map.get(nombre)
            fte_esc = float(p_input.get("fte", 0) or 0)
            fte_weight = fte_esc / max(fte_total_activos, 1)
            b_for_perfil = round(costo_b_mensual * fte_weight, 2)
            c_for_perfil = round(costo_c_mensual * fte_weight, 2)
            escenario = _build_escenario(
                idx=i,
                perfil_input=p_input,
                cts_p=cts_p,
                margen_a=margen_a,
                margen_b=margen_b,
                margen_c=margen_c,
                cont_op=cont_op,
                cont_com=cont_com,
                markup=markup,
                descuento=descuento,
                costo_b_mensual=b_for_perfil,
                costo_c_mensual=c_for_perfil,
                request_data=request_data,
            )
            escenarios.append(escenario)

    total = _build_total(escenarios, cts_perfiles or [])
    desglose_producto_opex = _build_desglose_producto_opex(request_data)
    return {
        "escenarios": escenarios,
        "escenario_total": _build_escenario_total(request_data["escenario_total"],request_data, fte_total_activos, escenarios, total.get("facturacion_mensual", 0.0)), 
        "total": total,
        "desglose_producto_opex": desglose_producto_opex,
        "ajustes_aplicados": {
            "margen_cadena_a": margen_a,
            "margen_cadena_b": margen_b,
            "margen_cadena_c": margen_c,
            "cont_op": cont_op,
            "cont_com": cont_com,
            "markup": markup,
            "descuento": descuento,
        },
        "cadenas_incluidas": {
            "cadena_a": True,
            "cadena_b": costo_b_mensual > 0,
            "cadena_c": costo_c_mensual > 0,
        },
    }
