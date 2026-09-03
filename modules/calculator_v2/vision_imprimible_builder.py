"""
Construye la Visión Imprimible para el Motor de Reglas v2.

Pure function: no IO, no DB, no Excel en tiempo de ejecución.
Datos de estructura: extraídos de la pestaña 'Riesgo' y 'Graficos' de ElTiempo.xlsx.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .escenarios_enricher import get_escenarios_activos_keys, _clave

from nexa_engine.modules.parametrizacion.services.resolver import (
    ParametrizationResolver,
)

_resolver = ParametrizationResolver()

# SMLV 2026 Colombia (COP) — actualizar anualmente si cambia el decreto
_SMLV_2026 = 1_423_500.0

_RANGOS_CONTINGENCIAS = [						

    {"nombre": "Margen objetivo Cadena A", "campo": "margen_a", "min": 0.0, "max": 1.0},
    {"nombre": "Margen objetivo Cadena B", "campo": "margen_b", "min": 0.0, "max": 1.0},
    {"nombre": "Margen objetivo cadena C", "campo": "margen_c", "min": 0.0, "max": 1.0},					
    {"nombre": "Contingencia Operativa", "campo": "cont_op",  "min": 0.01, "max": 0.04},
    {"nombre": "Contingencia Comercial", "campo": "cont_com", "min": 0.04, "max": 0.07},
    {"nombre": "Mark-Up",               "campo": "markup",   "min": 0.02, "max": 0.08},
    {"nombre": "Descuento",             "campo": "descuento","min": 0.00, "max": 0.08},
]


# ── helpers internos ───────────────────────────────────────────────────────────

def _datos_op(request_data: Dict[str, Any]) -> Dict[str, Any]:
    return request_data.get("datos_operativos", {}) or {}


def _primer_mes_ramp1(meses: List[Dict]) -> Optional[Dict]:
    """Primer mes con ramp_up_mes >= 1.0 (régimen permanente pre-IPC)."""
    for m in meses:
        if float(m.get("valores", {}).get("ramp_up_mes", 0.0)) >= 1.0:
            return m
    return meses[-1] if meses else None


# ── Sección 01 — Ficha del Deal ───────────────────────────────────────────────

def _build_ficha(request_data: Dict[str, Any], duracion_meses: int) -> dict:
    op = _datos_op(request_data)
    cadena_a = request_data.get("condiciones_cadena_a", {}) or {}
    perfiles = cadena_a.get("perfiles", []) or []
    fte_total = sum(float(p.get("fte", 0)) for p in perfiles)

    return {
        "cliente": op.get("cliente"),
        "servicio": op.get("servicio"),
        "ciudad": op.get("ciudad"),
        "sede": op.get("sede"),
        "tipo_cliente": op.get("tipo_cliente"),
        "fecha_inicio": op.get("fecha_inicio"),
        "fecha_fin": op.get("fecha_fin"),
        "duracion_meses": duracion_meses,
        "periodo_pago_dias": op.get("periodo_pago_dias"),
        "ajuste_precio": op.get("ajuste_precio") or op.get("tipo_ajuste_precio"),
        "volumen_base": round(fte_total, 0),
        "descuento": round(float(op.get("descuento", 0.0) or 0.0), 4),
    }


# ── Sección 02 — Economics ────────────────────────────────────────────────────

def _build_economics(
    meses: List[Dict],
    totales: Dict[str, float],
    cts_mensual: Optional[float] = None,
) -> dict:
    """
    ingreso_mensual = ingreso_neto del primer mes con ramp=1.0 (tarifa de régimen permanente).
    costo_mensual   = costo_cadena_a del mismo mes (payroll + no_payroll + financiero).
    margen          = margen_a objetivo configurado en Panel de Control.
    valor_total     = ingreso_neto acumulado del contrato (con IPC y ramp).

    Excel 'Visión Imprimible'!B21 → Ingreso Mensual = 375,959,430.39 (Mes 3, ramp=1.0)
    Excel 'Visión Imprimible'!B22 → Costo Mensual   = 342,540,814.35 (Mes 3)
    Excel 'Visión Imprimible'!B23 → Margen = 18% (parámetro Panel)
    Excel 'Visión Imprimible'!B24 → Valor Total = 3,807,486,441.05 (ingreso_neto total)
    """
    mes = _primer_mes_ramp1(meses)
    vals = mes.get("valores", {}) if mes else {}
    ingreso_mensual = float(vals.get("ingreso_neto", 0.0))

    costo_mensual = float(
        cts_mensual if cts_mensual is not None else vals.get("cts_mensual", 0.0)
    )
    margen = float(vals.get("margen_a", 0.0))
    valor_total = float(totales.get("ingreso_neto", 0.0))

    return {
        "ingreso_mensual": round(ingreso_mensual, 2),
        "costo_mensual": round(costo_mensual, 2),
        "margen": margen,
        "valor_total_contrato": round(valor_total, 2),
    }


# ── Sección 03 — Análisis Gráfico ────────────────────────────────────────────

def _build_waterfall(meses: List[Dict], totales: Dict[str, float]) -> List[dict]:
    """
    Descomposición waterfall del ingreso neto → costos → utilidad.

    Cada valor se obtiene de los rubros calculados por el motor y se acumula
    sobre los meses disponibles. Los costos se devuelven negativos para que el
    consumidor pueda representarlos como disminuciones en la cascada.
    """
    def total(key: str) -> float:
        if key in totales:
            return float(totales[key])
        return sum(float(m.get("valores", {}).get(key, 0.0)) for m in meses)

    ingreso_neto = total("ingreso_neto")
    conceptos = [
        ("Ingreso Neto", ingreso_neto, False),
        ("Payroll", total("nomina_total_mensual"), True),
        ("No Payroll", total("no_payroll_total_mensual"), True),
        ("Componente Fijo", total("componente_fijo_b"), True),
        ("Componente Variable", total("componente_variable_b"), True),
        ("Tarifa Proveedor", total("tarifa_proveedor_c"), True),
        ("Costo Integración", total("costo_integracion_c"), True),
        ("Costo Variable", total("costo_variable_c"), True),
        ("Costos Financieros", total("costos_financiacion_mensual"), True),
        ("Utilidad Neta", total("utilidad_neta"), False),
    ]

    def pct(value: float) -> float:
        return round(value / ingreso_neto, 4) if ingreso_neto else 0.0

    return [
        {
            "concepto": concepto,
            "valor": round(-value if es_costo else value, 2),
            "pct": pct(-value if es_costo else value),
            **({"subtotal": True} if concepto in ("Ingreso Neto", "Utilidad Neta") else {}),
        }
        for concepto, value, es_costo in conceptos
    ]


def _build_evolucion(meses: List[Dict]) -> List[dict]:
    """Serie mensual de ingreso_neto para el gráfico de Evolución Mensual."""
    return [
        {
            "mes_numero": m.get("mes", i + 1),
            "ingreso_neto": round(float(m["valores"].get("ingreso_neto", 0.0)), 2),
        }
        for i, m in enumerate(meses)
    ]


def _build_margen_historico() -> dict:
    """Construye el margen histórico temporal del servicio SAC."""
    return {
        "servicio": "SAC",
        "margen_servicio": 0.17,
        "items": {
            "q1": 0.13,
            "q2": 0.17,
            "q3": 0.27,
            "q4": 0.96,
        },
    }


# ── Sección 04 — Comparativo de Escenarios ───────────────────────────────────

def _build_escenarios(request_data: Dict[str, Any], cts_perfiles: List[Dict]) -> List[dict]:
    """
    Un escenario por perfil de Cadena A.
    tarifa_fte proviene del CTS (ingreso_teorico / fte).
    Excel 'Hoja Maestra Escenarios' — Escenario 1: tarifa = 5,021,494.42 / FTE.
    Cuando escenarios_comerciales está configurado, siempre retorna 5 slots (vacíos con None).
    """
    cadena_a = request_data.get("condiciones_cadena_a", {}) or {}
    perfiles_input = cadena_a.get("perfiles", []) or []

    # Si hay escenarios_comerciales, mostrar solo los perfiles con escenario configurado
    esc_activos = get_escenarios_activos_keys(request_data)
    if esc_activos is not None:
        perfiles_input = [
            p for p in perfiles_input
            if _clave(p.get("canal"), p.get("modalidad")) in esc_activos
        ]

    tarifa_por_nombre: Dict[str, float] = {
        p.get("nombre", "").replace(" ", ""): float(p.get("tarifa_fte", 0.0))
        for p in cts_perfiles
    }

    escenarios = []
    for i, p in enumerate(perfiles_input):
        nombre = str(p.get("nombre", f"Perfil {i + 1}"))
        escenario_nombre = str(p.get("escenario_nombre") or nombre)
        modelo = str(p.get("modelo_cobro", "Fijo"))
        pct_var = float(p.get("pct_variable", 0.0))
        pct_fijo = round(1.0 - pct_var, 4)
        comp_fijo = p.get("componente_fijo")
        comp_var = p.get("componente_variable")
        fte = int(float(p.get("fte", 0)))
        ingreso = tarifa_por_nombre.get(nombre, 0.0)
        tarifa = (ingreso * pct_fijo)
        tarifa_variable = (ingreso * pct_var)


        escenarios.append({
            "id": escenario_nombre,
            "nombre": escenario_nombre,
            "perfil": nombre,
            "modalidad": p.get("modalidad"),
            "canal": p.get("canal"),
            "modelo_cobro": modelo,
            "componente_fijo": comp_fijo,
            "componente_variable": comp_var,
            "pct_fijo": pct_fijo,
            "pct_variable": round(pct_var, 4),
            "fte": fte,
            "tarifa_fija": round(tarifa, 2) if tarifa is not None else None,
            "tarifa_variable": round(tarifa_variable, 2) if tarifa_variable else None,
        })

    # Siempre retornar 5 slots cuando escenarios_comerciales está configurado.
    # Slots sin perfil Cadena A muestran metadatos del escenario comercial (canal, modelo, etc.)
    # pero con datos financieros en None (pueden ser canales de Cadena B o C únicamente).
    if esc_activos is not None:
        _esc_cfg_por_slot: Dict[int, Dict] = {}
        for _cfg in (request_data.get("escenarios_comerciales") or []):
            _n = int(_cfg.get("escenario") or 0)
            if 1 <= _n <= 5 and str(_cfg.get("canal") or "").strip():
                _esc_cfg_por_slot[_n] = _cfg

        all_5: List[dict] = []
        for n in range(1, 6):
            cfg = _esc_cfg_por_slot.get(n)
            if cfg:
                prop_var = float(cfg.get("proporcion_componente_variable") or 0.0)
                prop_fijo = round(1.0 - prop_var, 4)
                all_5.append({
                    "id": f"Escenario {n}",
                    "nombre": f"Escenario {n}",
                    "perfil": None,
                    "modalidad": cfg.get("modalidad"),
                    "canal": cfg.get("canal"),
                    "modelo_cobro": cfg.get("modelo_cobro"),
                    "componente_fijo": cfg.get("componente_fijo") if prop_fijo > 0 else None,
                    "componente_variable": cfg.get("componente_variable") if prop_var > 0 else None,
                    "pct_fijo": prop_fijo,
                    "pct_variable": round(prop_var, 4),
                    "fte": None,
                    "tarifa_fija": None,
                    "tarifa_variable": None,
                })
            else:
                all_5.append({
                    "id": f"Escenario {n}", "nombre": None, "perfil": None, "modalidad": None,
                    "canal": None, "modelo_cobro": None, "componente_fijo": None,
                    "componente_variable": None, "pct_fijo": None, "pct_variable": None,
                    "fte": None, "tarifa_fija": None, "tarifa_variable": None,
                })

        for esc in escenarios:
            esc_id = esc.get("id", "")
            try:
                slot = int(esc_id.split()[-1]) - 1
                if 0 <= slot < 5:
                    all_5[slot] = esc
            except (ValueError, IndexError):
                pass
        return all_5

    return escenarios


# ── Sección 05 — Control y Aprobación (Risk Scoring) ─────────────────────────
# Fuente: Excel 'Riesgo'!B2:N18
# Categoría Cliente (peso 0.4): Q1-Q5 con pesos 0.30/0.25/0.25/0.10/0.10
# Categoría Operativo (peso 0.6): Q6-Q10 con pesos 0.30/0.20/0.20/0.20/0.10
# Score_deal = score_op×0.60 + score_cliente×0.40

def _nivel(puntaje: int) -> str:
    return {1: "Bajo", 2: "Medio", 3: "Alto"}.get(puntaje, "Bajo")


def _q1_clasificacion(valor_total_contrato: float) -> tuple[int, str]:
    # Excel Riesgo!M3 = IFERROR(IFS(L3>=1000000000,"Alto",(L3/12)>=200000000,"Alto"),"Bajo")
    # L3 = 'Visión Cost To Serve'!C203 = valor_total_contrato
    if valor_total_contrato >= 1_000_000_000 or (valor_total_contrato / 12) >= 200_000_000:
        return 3, f"{valor_total_contrato:,.0f} COP total"
    return 1, f"{valor_total_contrato:,.0f} COP total"


def _q2_tipo_cliente(request_data: Dict[str, Any]) -> tuple[int, str]:
    grupo_aval = bool(_datos_op(request_data).get("grupo_aval", False))
    return (1, "Grupo Aval") if grupo_aval else (3, "No Grupo Aval")


def _q3_periodo_pago(request_data: Dict[str, Any]) -> tuple[int, str]:
    dias = int(_datos_op(request_data).get("periodo_pago_dias", 30) or 30)
    if dias > 60:
        return 3, f"{dias} días"
    if dias > 30:  # 31-60 días → Medio; ≤30 días → Bajo (El Tiempo=30 → Bajo, score=1)
        return 2, f"{dias} días"
    return 1, f"{dias} días"


def _q4_experiencia(request_data: Dict[str, Any]) -> tuple[int, str]:
    nuevo = bool(_datos_op(request_data).get("cliente_nuevo", False))
    return (3, "Sin historial") if nuevo else (1, "Cliente antiguo")


def _q5_imprevistos(vals_mes0: Dict[str, float]) -> tuple[int, str]:
    tiene = float(vals_mes0.get("pct_imprevistos", 0.0)) > 0.0
    return (3, "Sí") if tiene else (1, "No")


def _q6_alertas(valor_total_contrato: float, periodo_pago: int) -> tuple[int, str]:
    # Excel Riesgo!L8 = IF(CTS>=1B,1,0) + IF((CTS/Panel_C9)>=100M,1,0) + IF((CTS/Panel_C9)>=200M,1,0)
    # M8 = IF(L8=3,"Alto", IF(AND(L8>=1,L8<=2),"Medio","Bajo"))
    # CTS = valor_total_contrato; Panel_C9 = periodo_pago (días)
    periodo = max(periodo_pago, 1)
    ratio = valor_total_contrato / periodo
    n = int(valor_total_contrato >= 1_000_000_000) + int(ratio >= 100_000_000) + int(ratio >= 200_000_000)
    if n == 3:
        return 3, "3 alertas"
    if n >= 1:
        return 2, f"{n} alertas"
    return 1, "0 alertas"


def _q7_complejidad(request_data: Dict[str, Any]) -> tuple[int, str]:
    perfiles = (request_data.get("condiciones_cadena_a", {}) or {}).get("perfiles", []) or []
    canales = {p.get("canal") for p in perfiles if p.get("canal")}
    n = len(canales)
    if n >= 10:
        return 3, f"{n} canales"
    if n >= 5:
        return 2, f"{n} canales"
    return 1, f"{n} canales"


def _q8_capacitacion(request_data: Dict[str, Any]) -> tuple[int, str]:
    perfiles = (request_data.get("condiciones_cadena_a", {}) or {}).get("perfiles", []) or []
    total_fte = sum(float(p.get("fte", 0)) for p in perfiles)
    total_dias = sum(
        float(p.get("capacitacion", {}).get("dias_capacitacion", 0)) * float(p.get("fte", 0))
        for p in perfiles
    )
    dias_prom = total_dias / max(total_fte, 1)
    if dias_prom > 20:
        return 3, f"{dias_prom:.1f} días"
    if dias_prom >= 10:
        return 2, f"{dias_prom:.1f} días"
    return 1, f"{dias_prom:.1f} días"


#todo changes percents to config
def _q9_rotacion(request_data: Dict[str, Any], vals_mes0: Dict[str, float]) -> tuple[int, str]:
    operativeData = request_data.get("datos_operativos", {}) or {}
    tasa = float(
        operativeData.get("pct_rotacion", 0.0)
        or 0.0
    )
    if tasa > 0.10:
        return 3, f"{tasa*100:.1f}%"
    if tasa >= 0.05:
        return 2, f"{tasa*100:.1f}%"
    return 1, f"{tasa*100:.1f}%"


def _q10_terceros(request_data: Dict[str, Any]) -> tuple[int, str]:
    volumetria = request_data.get("volumetria", {})
    inbound = volumetria.get("inbound")
    outbound = volumetria.get("outbound")
    fte = _datos_op(request_data).get("interacciones_gestionadas_por_fte_promedio")
    total = ( get_total(inbound, fte) + get_total(outbound, fte))
    total_cadena_c = (get_total(inbound, fte, "cadena_c") + get_total(outbound, fte, "cadena_c"))
    pct = (total_cadena_c / total) if total_cadena_c > 0 else 0
    if pct >= 0.50:
        return 3, f"{pct*100:.1f}%"
    if pct >= 0.10:
        return 2, f"{pct*100:.1f}%"
    return 1, f"{pct*100:.1f}%"

def get_total(data, fte, only_chain=None):
    total = 0

    active = data.get("cadenas_activas", {})
    channels = data.get("canales", [])

    for channel in channels:
        for chain_name, is_active in active.items():

            if not is_active:
                continue

            if only_chain and chain_name != only_chain:
                continue

            chain = channel.get(chain_name)

            if not chain:
                continue

            value = float(chain.get("valor", 0))
            unit = chain.get("unidad")

            total += value * fte if unit == "FTE" else value

    return total

def _build_control(
    request_data: Dict[str, Any],
    meses: List[Dict],
    totales: Dict[str, float],
) -> dict:
    
    risk_list = _resolver.get_active_op()["riesgo"]

    def search_in_risk(factor: str) -> str:
        criterios = risk_list.get("criterios", []) if isinstance(risk_list, dict) else risk_list
        criterio = next((item for item in criterios if item.get("factor") == factor), {})
        return criterio.get("pregunta", factor)
    
    vals0 = meses[0].get("valores", {}) if meses else {}
    
    ingreso_neto_total = float(totales.get("ingreso_neto", 0.0))
    periodo_pago = int(_datos_op(request_data).get("periodo_pago", 30) or 30)
    mes_ramp = _primer_mes_ramp1(meses)
    ingreso_mensual = float((mes_ramp.get("valores", {}) if mes_ramp else {}).get("ingreso_neto", 0.0))

    # Preguntas con puntaje, peso y calificación ponderada
    preguntas_raw = [
        # id, factor, categoria, peso, (puntaje, respuesta)
        (1,  search_in_risk("Clasificación de oportunidad"), "cliente",  0.30, _q1_clasificacion(ingreso_neto_total)),
        (2,  search_in_risk("Tipo de cliente"),              "cliente",  0.25, _q2_tipo_cliente(request_data)),
        (3,  search_in_risk("Período de pago"),              "cliente",  0.25, _q3_periodo_pago(request_data)),
        (4,  search_in_risk("Experiencia con el cliente"),   "cliente",  0.10, _q4_experiencia(request_data)),
        (5,  search_in_risk("Presupuesto de imprevistos"),   "cliente",  0.10, _q5_imprevistos(vals0)),
        (6,  search_in_risk("Alertas activadas"),            "operativo",0.30, _q6_alertas(ingreso_neto_total, periodo_pago)),
        (7,  search_in_risk("Complejidad"),                  "operativo",0.20, _q7_complejidad(request_data)),
        (8,  search_in_risk("Capacitaciones"),               "operativo",0.20, _q8_capacitacion(request_data)),
        (9,  search_in_risk("Rotación"),                     "operativo",0.20, _q9_rotacion(request_data, vals0)),
        (10, search_in_risk("Dependencia de terceros"),      "operativo",0.10, _q10_terceros(request_data)),
    ]

    preguntas = []
    score_cliente = 0.0
    score_operativo = 0.0

    for pid, factor, categoria, peso, (puntaje, respuesta) in preguntas_raw:
        cal = round(puntaje * peso, 4)
        preguntas.append({
            "id": pid,
            "factor": factor,
            "categoria": categoria,
            "respuesta": respuesta,
            "nivel": _nivel(puntaje),
            "puntaje": puntaje,
            "peso_factor": peso,
            "calificacion_ponderada": cal,
        })
        if categoria == "cliente":
            score_cliente += cal
        else:
            score_operativo += cal

    score_deal = round(score_operativo * 0.60 + score_cliente * 0.40, 4)

    def clasificacion(score: float) -> str:
        if score >= 2.5:
            return "Alto"
        if score >= 1.5:
            return "Medio"
        return "Bajo"

    # Alertas de aprobación
    alertas_config = [
        (
            "Gerencia Financiera",
            "> COP 100M/mes",
            ingreso_mensual,
            ingreso_mensual >= 100_000_000,
        ),
        (
            "Gerencia General",
            "> COP 200M/mes",
            ingreso_mensual,
            ingreso_mensual >= 200_000_000,
        ),
        (
            "Alta Dirección",
            f"> 1,000 SMLV (total contrato >= {_SMLV_2026 * 1_000:,.0f} COP)",
            ingreso_neto_total,
            ingreso_neto_total >= _SMLV_2026 * 1_000,
        ),
    ]
    alertas = [
        {
            "nivel": nivel,
            "umbral_descripcion": umbral,
            "valor_deal": round(valor, 2),
            "requerida": requerida,
        }
        for nivel, umbral, valor, requerida in alertas_config
    ]
    

    return {
        "score_cliente": round(score_cliente, 4),
        "score_operativo": round(score_operativo, 4),
        "score_deal": score_deal,
        "clasificacion_deal": clasificacion(score_deal),
        "alertas_aprobacion": alertas,
        "preguntas": preguntas,
    }


# ── Sección 06 — Contingencias y Ajustes ─────────────────────────────────────

def _build_contingencias(meses: List[Dict]) -> List[dict]:
    """
    Estado de cada ajuste vs su rango permitido.
    Excel 'Visión Imprimible' Sección 06:
      Cont. Op  0% ⚠ (mín 1-4%)
      Cont. Com 0% ⚠ (mín 4-7%)
      Markup    0% ⚠ (mín 2-8%)
      Descuento 0% ✓ (0-8%)
    """
    vals0 = meses[0].get("valores", {}) if meses else {}
    items = []
    for r in _RANGOS_CONTINGENCIAS:
        val = float(vals0.get(r["campo"], 0.0))
        if val < r["min"]:
            estado = "bajo_minimo"
            alerta = True
        elif val > r["max"]:
            estado = "sobre_maximo"
            alerta = True
        else:
            estado = "ok"
            alerta = False
        items.append({
            "nombre": r["nombre"],
            "valor_actual": round(val, 4),
            "rango_min": r["min"],
            "rango_max": r["max"],
            "estado": estado,
            "alerta": alerta,
        })
    return items


# ── Entry point ───────────────────────────────────────────────────────────────

def build_vision_imprimible(
    request_data: Dict[str, Any],
    meses: List[Dict],
    totales: Dict[str, float],
    duracion_meses: int,
    cts_perfiles: Optional[List[Dict]] = None,
    cts_mensual: Optional[float] = None,
) -> dict:
    """Construye el dict completo de Visión Imprimible desde los resultados del motor v2.

    Args:
        request_data: Dict original de la petición (datos_operativos + condiciones_cadena_*).
        meses: Lista de dicts {mes: int, valores: Dict[str, float]} del motor.
        totales: Acumulado del motor (ingreso_bruto, ingreso_neto, costo_cadena_a, ...).
        duracion_meses: Número de meses del contrato.
        cts_perfiles: Perfiles de VisionCostToServe (para tarifas en Sección 04).
        cts_mensual: CTS mensual de VisionCostToServe para la Sección 02.
    """
    return {
        "seccion_01_ficha": _build_ficha(request_data, duracion_meses),
        "seccion_02_economics": _build_economics(meses, totales, cts_mensual),
        "seccion_03_grafico": {
            "waterfall": _build_waterfall(meses, totales),
            "evolucion_mensual": _build_evolucion(meses),
            "margen_historico": _build_margen_historico(),
        },
        "seccion_04_escenarios": {
            "escenarios": _build_escenarios(request_data, cts_perfiles or []),
        },
        "seccion_05_control": _build_control(request_data, meses, totales),
        "seccion_06_contingencias": {
            "items": _build_contingencias(meses),
        },
    }
