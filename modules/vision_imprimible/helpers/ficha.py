"""Ficha del Deal — Visión Imprimible sección 01 (Excel VI!B10:T13).

Produce el dict `ficha_deal` con todos los campos visibles en el encabezado
del deal: datos del cliente, rango de fechas contractuales, parámetros
operativos, indexación, tasas impositivas y cadenas activas.

Fórmulas propias de VI sección 01:
  fecha_fin          = fecha_inicio + meses_contrato − 1 día (último día del período)
  duracion_contrato  = "DD/MM/YYYY a DD/MM/YYYY" (rango formateado para el header)
  mes_finalizacion   = (mes_inicio − 1) + meses_contrato

Regla Superior: Excel V2-7 es canónico. No leer storage ni calculators en runtime.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from nexa_engine.modules.shared.models import PanelDeControl


def ficha_deal_to_dict(panel: PanelDeControl) -> Dict[str, Any]:
    """Extrae la ficha del deal desde PanelDeControl.

    Fuente: Sección 01 de la Visión Imprimible (Excel VI rows 10-13).

    Expone todos los campos visibles del encabezado del deal:
    - Datos del cliente (nombre, tipo, antigüedad, ciudad, sede)
    - Datos contractuales (fecha inicio/fin, duración, periodo pago, divisa)
    - Parámetros operativos (ausentismo, rotación, formación, financiación)
    - Indexación (componente humano/tecnológico, frecuencia, mes ajuste)
    - Tasas impositivas (ICA, GMF)
    - Cadenas activas
    """
    idx = panel.indexacion

    fecha_fin, duracion_contrato, mes_finalizacion = _derivar_fechas(
        panel.fecha_inicio, panel.meses_contrato
    )

    return {
        # ── Datos del cliente (Excel VI!B10:T11) ──────────────────────
        "cliente":                    panel.cliente,
        "tipo_cliente":               panel.tipo_cliente,
        "antiguedad_cliente":         panel.antiguedad_cliente,
        "ciudad":                     panel.ciudad,
        "sede":                       panel.sede,
        # ── Datos del servicio ────────────────────────────────────────
        "linea_negocio":              panel.linea_negocio,
        "divisa":                     "COP",
        # ── Datos contractuales (Excel VI!B12:T13) ────────────────────
        "fecha_inicio":               panel.fecha_inicio,
        "fecha_fin":                  fecha_fin,
        "duracion_contrato":          duracion_contrato,
        "meses_contrato":             panel.meses_contrato,
        "mes_finalizacion":           mes_finalizacion,
        "periodo_pago_dias":          panel.periodo_pago_dias,
        # ── Parámetros operativos (Panel!C16:C21) ─────────────────────
        "pct_ausentismo":             panel.pct_ausentismo,
        "horas_formacion_mensual":    panel.horas_formacion_mensual,
        "activa_financiacion":        panel.activa_financiacion,
        "tarifa_diaria_capacitacion": panel.tarifa_diaria_capacitacion,
        "tarifa_crucero":             panel.tarifa_crucero,
        "complejidad_especialista":   panel.complejidad_especialista,
        # ── Indexación (Panel!L6:L10) ─────────────────────────────────
        "ajuste_precio_tipo":         idx.componente_humano if idx else "",
        "ajuste_precio_tecnologico":  idx.componente_tecnologico if idx else "",
        "ajuste_precio_frecuencia":   idx.frecuencia if idx else "Anual",
        "mes_ajuste_indexacion":      panel.mes_ajuste_indexacion,
        # ── Tasas impositivas (Panel!B34:B35) ─────────────────────────
        "tasa_ica":                   panel.tasa_ica,
        "tasa_gmf":                   panel.tasa_gmf,
        # ── Cadenas activas ───────────────────────────────────────────
        "cadenas_activas": {
            "cadena_a": panel.cadenas_activas.cadena_a,
            "cadena_b": panel.cadenas_activas.cadena_b,
            "cadena_c": panel.cadenas_activas.cadena_c,
        },
    }


def _derivar_fechas(
    fecha_inicio: str,
    meses_contrato: int,
) -> tuple[Optional[str], Optional[str], Optional[int]]:
    """Deriva fecha_fin, duracion_contrato y mes_finalizacion.

    Excel VI!B13: muestra rango "DD/MM/YYYY a DD/MM/YYYY".
    fecha_fin = último día del mes (meses_contrato − 1) después del inicio.

    Returns:
        (fecha_fin, duracion_contrato, mes_finalizacion) — todos None si falla el parse.
    """
    try:
        fi = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        end_month = fi.month - 1 + meses_contrato
        end_year  = fi.year + end_month // 12
        end_month = end_month % 12 + 1
        last_day  = calendar.monthrange(end_year, end_month)[1]
        end_day   = min(fi.day, last_day)
        ff = datetime(end_year, end_month, end_day) - timedelta(days=1)
        return (
            ff.strftime("%Y-%m-%d"),
            f"{fi.strftime('%d/%m/%Y')} a {ff.strftime('%d/%m/%Y')}",
            (fi.month - 1) + meses_contrato,
        )
    except (ValueError, TypeError):
        return None, None, None
