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


# ── helpers internos ───────────────────────────────────────────────────────────

def _datos_op(request_data: Dict[str, Any]) -> Dict[str, Any]:
    return request_data.get("datos_operativos", {}) or {}


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
    financiero = float(cts_p.get("financiero", 0.0)) if cts_p else 0.0
    costo_a = float(cts_p.get("costo_total", 0.0)) if cts_p else (payroll + no_payroll + financiero)

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
    }

def _build_escenario_total(data: Dict[str, Any], vals0: Dict[str, Any], fte_total: float, escenarios: List[dict]) -> dict:
    
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

    # Si hay escenarios_comerciales, mostrar solo los perfiles con escenario configurado
    esc_activos = get_escenarios_activos_keys(request_data)
    perfiles_input = list(all_perfiles)
    if esc_activos is not None:
        perfiles_input = [
            p for p in perfiles_input
            if _clave(p.get("canal"), p.get("modalidad")) in esc_activos
        ]

    # FTE total de los escenarios configurados — base para distribución proporcional de Cadena B/C.
    # Excel HME: Cadena B/C se distribuye entre los escenarios activos (no todos los perfiles del deal).
    fte_total_activos = sum(float(p.get("fte", 0) or 0) for p in perfiles_input)

    cts_map = _cts_map(cts_perfiles or [])

    escenarios = []
    for i, p_input in enumerate(perfiles_input):
        nombre = str(p_input.get("nombre", f"Escenario {i + 1}"))
        cts_p = cts_map.get(nombre)

        # Distribución FTE-proporcional de costos Cadena B y C entre escenarios activos.
        # Excel HME C27: costo_B_esc = SUMPRODUCT(CostoFijo filtrado por canal/modalidad)
        # Aproximación: proporcional a FTE del escenario sobre FTE total activos.
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
        )
        escenarios.append(escenario)

    # Siempre retornar 5 slots cuando escenarios_comerciales está configurado.
    # Slots sin datos = {"id": "Escenario N", resto: None}
    if esc_activos is not None:
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

    total = _build_total(escenarios, cts_perfiles or [])

    return {
        "escenarios": escenarios,
        "escenario_total": _build_escenario_total(request_data["escenario_total"], vals0, fte_total_activos, escenarios), 
        "total": total,
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
