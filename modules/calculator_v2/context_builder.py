"""
Construye el contexto de evaluación desde el request JSON de la simulación.

El contexto es un dict plano con todos los escalares que necesitan las fórmulas.
Se actualiza progresivamente durante el loop de evaluación de rubros.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _extract_valor(field: Any) -> float:
    """Extrae el valor escalar de un campo que puede ser float o dict {valor: ...}."""
    if isinstance(field, dict):
        return float(field.get("valor", 0))
    return float(field) if field is not None else 0.0


def build_base_context(
    request_data: Dict[str, Any],
    mes_numero: int,
    ramp_up_override: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Construye el contexto base para un mes dado.

    Incluye todas las variables escalares extraídas del request que las fórmulas
    de los rubros necesitan. Los rubros `computed` se añaden en el engine.
    """
    datos_op: Dict = request_data.get("datos_operativos", {})
    reglas: Dict = request_data.get("reglas_negocio", {})
    polizas: List[Dict] = request_data.get("polizas", [])
    cadena_a: Dict = request_data.get("condiciones_cadena_a", {})

    # Estructura nueva: reglas_negocio.margen_objetivo.{cadena_a, cadena_b, cadena_c}
    margen_obj: Dict = reglas.get("margen_objetivo", {})

    # Estructura nueva: reglas_negocio.descuento_volumen.{valor, minimo, maximo}
    descuento_obj = reglas.get("descuento_volumen", {})
    descuento_val = float(descuento_obj.get("valor", 0)) if isinstance(descuento_obj, dict) else float(descuento_obj or 0)

    # FTE total Cadena A
    perfiles: List[Dict] = cadena_a.get("perfiles", [])
    fte_total_cadena_a = sum(float(p.get("fte", 0)) for p in perfiles)

    # Estaciones de trabajo presencial en sede
    # Excel V2-8: 'Condiciones Cadena A'!E11:S11 → 'Visión P&G'!J14 = SUM($E$11:$S$11)
    estaciones_trabajo_presencial = sum(float(p.get("estaciones_presenciales", 0)) for p in perfiles)

    # Polizas activas (lista de dicts para generadores en fórmulas)
    polizas_activas = [p for p in polizas if p.get("activa", False)]

    # Factor ramp-up para el mes actual.
    # Prioridad: 1) HR-Campaña de CosmosDB (ramp_up_override), 2) request.datos_operativos.ramp_up
    ramp_up_lista: List[float] = ramp_up_override or datos_op.get("ramp_up", [])
    if ramp_up_lista and mes_numero <= len(ramp_up_lista):
        ramp_up_mes = float(ramp_up_lista[mes_numero - 1])
    else:
        ramp_up_mes = 1.0  # sin ramp_up definido → 100%

    # Tasas base para el cálculo de ingreso
    tasa_ica_val = float(datos_op.get("tasa_ica", 0.01))
    tasa_gmf_val = float(datos_op.get("tasa_gmf", 0.004))
    pct_imprevistos_val = float(reglas.get("imprevistos", 0.10))

    # Tasa polizas efectiva (suma de activas: pct_poliza × pct_atribuible)
    tasa_polizas = sum(
        p.get("pct_poliza", 0) * p.get("pct_atribuible", 0)
        for p in polizas_activas
    )

    # Pre-estimación para despejar ingreso_cadena_a sin circularidad.
    # ICA y GMF: aplican sobre ingreso_bruto (ley colombiana — tributo sobre facturación bruta).
    # Pólizas: aplican sobre ingreso_neto = ingreso_bruto × (1 - imprevistos).
    tasa_financiero_efectiva = tasa_ica_val + tasa_gmf_val + tasa_polizas * (1 - pct_imprevistos_val)

    # paso_cobro_variable: fila 16 de Visión P&G (distinto del ramp-up)
    # Es 0 para SAC (modelo fijo). El ramp-up afecta el ingreso en cadena, no aquí.
    paso_cobro_variable = float(reglas.get("paso_cobro_variable", 0.0))

    return {
        # ── Mes ────────────────────────────────────────────────────────────
        "mes_numero": mes_numero,
        "ramp_up_mes": ramp_up_mes,

        # ── Datos operativos ───────────────────────────────────────────────
        "meses_proyecto": int(datos_op.get("duracion_meses", 10)),
        "tipo_servicio": datos_op.get("servicio", "SAC"),
        "tasa_ica": float(datos_op.get("tasa_ica", 0.01)),
        "tasa_gmf": float(datos_op.get("tasa_gmf", 0.004)),
        "crucero_valor": float(datos_op.get("crucero", 8600)),
        "costos_financiacion_mensual": float(datos_op.get("cons_costo_de_financiacion", 0)),

        # ── Reglas de negocio ──────────────────────────────────────────────
        "margen_a": float(margen_obj.get("cadena_a", 0.18)),
        "margen_b": float(margen_obj.get("cadena_b", 0.30)),
        "margen_c": float(margen_obj.get("cadena_c", 0.18)),
        "cont_op": _extract_valor(reglas.get("contingencia_operativa", 0)),
        "cont_com": _extract_valor(reglas.get("contingencia_comercial", 0)),
        "markup": _extract_valor(reglas.get("markup", 0)),
        "descuento": descuento_val,
        "pct_imprevistos": float(reglas.get("imprevistos", 0.10)),

        # ── Cadenas activas ────────────────────────────────────────────────
        "cadena_b_activa": request_data.get("condiciones_cadena_b") is not None,
        "cadena_c_activa": request_data.get("condiciones_cadena_c") is not None,

        # ── FTE ────────────────────────────────────────────────────────────
        "fte_total_cadena_a": fte_total_cadena_a,
        # Excel V2-8: 'Visión P&G'!J14 = SUM('Condiciones Cadena A'!$E$11:$S$11)
        "estaciones_trabajo": estaciones_trabajo_presencial,

        # ── Pólizas ────────────────────────────────────────────────────────
        "polizas_activas": polizas_activas,  # lista de dicts para sum() en fórmulas

        # ── Financiero pre-estimado (para despejar ingreso sin circularidad) ──
        "tasa_polizas": tasa_polizas,
        "tasa_financiero_efectiva": tasa_financiero_efectiva,

        # ── Paso cobro variable (fila 16 P&G, ≠ ramp_up, = 0 para SAC) ──────
        "paso_cobro_variable": paso_cobro_variable,

        # ── Datos operativos globales (Panel de Control General) ───────────
        # Excel V2-8: Panel!C19 = pct_ausentismo, Panel!C20 = pct_rotacion
        # Panel!C16 = tarifa_diaria_capacitacion, Panel!C18 = horas_formacion_mes
        "pct_ausentismo": float(datos_op.get("pct_ausentismo", 0.0)),
        "pct_rotacion": float(datos_op.get("pct_rotacion", 0.0)),
        "horas_formacion_mes": float(datos_op.get("horas_formacion_mes", 8.0)),
        "tarifa_diaria_capacitacion": float(datos_op.get("tarifa_diaria_capacitacion", 20_000.0)),
    }
