"""
nexa_engine/calculators/vision_pyg.py
=====================================
Vision P&G Builder — transforms pyg_por_mes into structured frontend model.

The builder takes the raw list of PyGMensual and the KPIsDeal, and produces
a VisionPyG with:
  - resumen_ejecutivo: high-level deal summary
  - filas: ordered list of VisionPyGRow for frontend table rendering

Each row maps to a line item in the Excel "Visión P&G" sheet, with:
  - label (Spanish display name)
  - seccion (ingresos / costos_op / costos_fin / resultados)
  - tipo (linea / subtotal / total / porcentaje)
  - signo (+ / - / = / %)
  - valores (one per month of contract)
  - acumulado (sum)
  - promedio (average over active months)

The frontend renders this directly as a table — no recalculation needed.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from nexa_engine.modules.shared.models import (
    KPIsDeal,
    PerfilCadenaA,
    PyGMensual,
)
from nexa_engine.modules.vision_pyg.models import (
    ResumenEjecutivoPyG,
    VisionPyG,
    VisionPyGRow,
    VisionPyGRowDetalle,
)


# (key, label, seccion, tipo, signo, attr_name, excel_row, formula)
#
# Semántica de campos:
#   signo:
#     "+"  → componente que se SUMA al subtotal/total de su sección
#     "-"  → componente que se RESTA (descuento, imprevistos)
#     "="  → ES el subtotal/total (resultado de la suma de las líneas anteriores)
#     "%"  → porcentaje (ratio 0..1, no participa en sumas)
#     ""   → informativo (no participa en cálculos, ej: ramp-up)
#
#   tipo:
#     "linea"      → dato individual (componente sumable/restable)
#     "subtotal"   → suma parcial de líneas de la sección (ej: Ingreso Bruto = A+B+C)
#     "total"      → suma final de la sección (ej: Ingreso Neto, Costo Total)
#     "porcentaje" → ratio; acumulado = promedio de meses activos (no suma)
#
#   attr_name:
#     Nombre del campo en PyGMensual. "" → fila sin fuente (siempre 0, ej: Costo Fijo placeholder).
#     "__contribucion_por_puesto__" → calculado: contribucion / estaciones.
#
#   excel_row: fila exacta en la hoja "Visión P&G" del Excel V2-7.
#   formula: fórmula mensual del Excel (columna C). BK = SUM(C:BJ) salvo excepciones.
#
_ROW_DEFINITIONS = [
    # ── Ingresos (Excel rows 18-27) ───────────────────────────────
    # key                     label                              seccion      tipo         signo attr_name               row  formula
    ("ingreso_bruto_a",      "Ingreso Cadena A",                "ingresos",  "linea",     "+", "ingreso_bruto_a",       19, "=CostoA/(1-margen)*rampup"),
    ("ingreso_bruto_b",      "Ingreso Cadena B",                "ingresos",  "linea",     "+", "ingreso_bruto_b",       20, "=CostoB/(1-margen_b)*rampup"),
    ("ingreso_bruto_c",      "Ingreso Cadena C",                "ingresos",  "linea",     "+", "ingreso_bruto_c",       21, "=CostoC/(1-margen_c)*rampup"),
    ("ingreso_bruto",        "Ingreso Bruto",                   "ingresos",  "subtotal",  "=", "ingreso_bruto",         18, "=C19+C20+C21"),
    ("contingencia_op",      "Contingencia Operativa",          "ingresos",  "linea",     "+", "contingencia_op",       22, "=C18*Panel!C67"),
    ("contingencia_com",     "Contingencia Comercial",          "ingresos",  "linea",     "+", "contingencia_com",      23, "=C18*Panel!C68"),
    ("markup_ingreso",       "Mark-Up",                         "ingresos",  "linea",     "+", "markup_ingreso",        24, "=C18*Panel!C69"),
    ("descuento_ingreso",    "Descuento",                       "ingresos",  "linea",     "-", "descuento_ingreso",     25, "=C18*Panel!C70"),
    ("imprevistos_ingreso",  "Imprevistos",                     "ingresos",  "linea",     "-", "imprevistos_ingreso",   26, "=C18*Panel!C73"),
    ("ingreso_neto",         "Ingreso Neto",                    "ingresos",  "total",     "=", "ingreso_neto",          27, "=C18+C22+C23+C24-C25-C26"),

    # ── Costos Operativos (Excel rows 30-64) ─────────────────────
    ("payroll_a",            "Payroll",                         "costos_op", "linea",     "+", "payroll_a",             32, "='Costos Totales'!C7"),
    ("no_payroll_a",         "No Payroll",                      "costos_op", "linea",     "+", "no_payroll_a",          43, "='Costos Totales'!C15"),
    ("costo_a",              "Costos Cadena A",                 "costos_op", "subtotal",  "=", "costo_a",              31, "=C32+C43"),
    ("costo_b",              "Costos Cadena B",                 "costos_op", "linea",     "+", "costo_b",              45, "=C46+C51"),
    ("costo_c",              "Costos Cadena C",                 "costos_op", "linea",     "+", "costo_c",              55, "=SUM(C56:C64)"),
    ("costo_total",          "Costo Total",                     "costos_op", "total",     "=", "costo_total",          30, "=C31+C45+C55"),

    # ── Componente Financiero (Excel rows 65-70) ──────────────────
    ("ica",                  "ICA",                             "costos_fin","linea",     "+", "ica",                  66, "='Pólizas - Costo Financiacion'!C7"),
    ("gmf",                  "GMF",                             "costos_fin","linea",     "+", "gmf",                  67, "='Pólizas - Costo Financiacion'!C9"),
    ("comision_administracion","Comisión de Administración",    "costos_fin","linea",     "+", "comision_administracion",68,"=IF(Panel!C45,C30*Panel!G45,0)"),
    ("polizas",              "Pólizas adicionales",             "costos_fin","linea",     "+", "polizas",              69, "='Pólizas - Costo Financiacion'!C23"),
    ("financiacion",         "Costos Financieros",              "costos_fin","linea",     "+", "financiacion",         70, "='Pólizas - Costo Financiacion'!C48"),
    ("costos_financieros",   "Componente Financiero",           "costos_fin","total",     "=", "costos_financieros",   65, "=SUM(C66:C70)"),

    # ── Utilidad (Excel rows 74-80) ───────────────────────────────
    ("contribucion",         "Contribución",                    "resultados","total",     "=", "contribucion",         74, "=C27-C30"),
    ("contribucion_por_puesto","Contribución por Puesto",       "resultados","linea",     "=", "__contribucion_por_puesto__", 75, "=IFERROR(C74/C14,0)"),
    ("pct_contribucion",     "% Contribución",                  "resultados","porcentaje","%", "pct_contribucion",     76, "=IFERROR(C74/C27,0)"),
    ("costo_fijo",           "Costo Fijo",                      "resultados","linea",     "+", "",                     78, "=0 (placeholder)"),
    ("utilidad_neta",        "Utilidad Neta",                   "resultados","total",     "=", "utilidad_neta",        79, "=C27-C30-C78"),
    ("pct_utilidad_neta",    "% Utilidad Neta",                 "resultados","porcentaje","%", "pct_utilidad_neta",    80, "=IFERROR(C79/C27,0)"),

    # ── Operativo (Excel row 15) ──────────────────────────────────
    ("rampup",               "Factor Ramp-up",                  "operativo", "linea",     "",  "rampup",              15, "='Rot, Ausent y Rentabilidad'!C15"),
]


class VisionPyGBuilder:
    """
    Builds a VisionPyG from pyg_por_mes and kpis.

    Usage:
        vision_pyg = VisionPyGBuilder().construir(pyg_por_mes, kpis)
    """

    class FORMULA_ID:
        """Internal formula identifiers for traceability."""
        # Secciones principales de la hoja "Visión P&G" del Excel V2-7
        FILAS_INGRESOS           = "VISION_PYG.FILAS_INGRESOS"          # Excel rows 18-27 (Ingresos)
        FILAS_COSTOS_OP          = "VISION_PYG.FILAS_COSTOS_OP"         # Excel rows 30-64 (Costos Operativos)
        FILAS_COSTOS_FIN         = "VISION_PYG.FILAS_COSTOS_FIN"        # Excel rows 65-70 (Componente Financiero)
        FILAS_RESULTADOS         = "VISION_PYG.FILAS_RESULTADOS"        # Excel rows 74-80 (Utilidad)
        FILAS_OPERATIVO          = "VISION_PYG.FILAS_OPERATIVO"         # Excel row 15 (Ramp-up)
        RESUMEN_EJECUTIVO        = "VISION_PYG.RESUMEN_EJECUTIVO"       # ResumenEjecutivoPyG (deal header)
        ESTACIONES_TRABAJO       = "VISION_PYG.ESTACIONES_TRABAJO"      # Σ(fte × pct_presencia) para no-soporte
        FECHAS_MESES             = "VISION_PYG.FECHAS_MESES"            # Calendario por columna de mes
        DETALLE_PAYROLL_A        = "VISION_PYG.DETALLE_PAYROLL_A"       # Sub-componentes payroll Cadena A (rows 34-40)
        DETALLE_NO_PAYROLL_A     = "VISION_PYG.DETALLE_NO_PAYROLL_A"    # Sub-componentes no-payroll Cadena A (rows 42-44)
        DETALLE_CADENA_B         = "VISION_PYG.DETALLE_CADENA_B"        # Sub-componentes Cadena B (rows 46-54)
        DETALLE_CADENA_C         = "VISION_PYG.DETALLE_CADENA_C"        # Sub-componentes Cadena C (rows 56-64)
        DETALLE_FIN_POR_CADENA   = "VISION_PYG.DETALLE_FIN_POR_CADENA"  # ICA/GMF/Pólizas desglosados por cadena
        CONTRIBUCION_POR_PUESTO  = "VISION_PYG.CONTRIBUCION_POR_PUESTO" # Excel C75 = contribucion / estaciones
        PROMEDIO_ACTIVOS         = "VISION_PYG.PROMEDIO_ACTIVOS"        # promedio sobre meses con ingreso_neto > 0

    def construir(
        self,
        pyg_por_mes: List[PyGMensual],
        kpis: KPIsDeal,
        perfiles_cadena_a: Optional[List[PerfilCadenaA]] = None,
        fecha_inicio: str = "",
        panel: "Optional[object]" = None,
        filas_detalle: Optional[List[VisionPyGRowDetalle]] = None,
    ) -> VisionPyG:
        n = len(pyg_por_mes)
        if n == 0:
            return VisionPyG()

        activos = [m for m in pyg_por_mes if m.ingreso_neto > 0]
        n_activos = len(activos)

        # GAP-PYG-HIER-4: Estaciones de Trabajo (Excel C14 = Σ E19:S19).
        # Workbook E19:S19 = fte × pct_presencia per profile (validated: row17 FTE=40,
        # row19 stations=24 = 40×0.6). Same formula context_builder uses for stations.
        # Deal-level constant — computed from perfiles, not stored on PyGMensual.
        perfiles = perfiles_cadena_a or []
        estaciones = sum(
            p.fte * getattr(p, "pct_presencia", 1.0)
            for p in perfiles if not getattr(p, "es_soporte", False)
        )

        def _valores_for(attr_name: str, tipo: str):
            if attr_name == "__contribucion_por_puesto__":
                # C75 = contribucion / estaciones (IFERROR → 0 when estaciones==0)
                vals = [
                    (m.contribucion / estaciones if estaciones > 0 else 0.0)
                    for m in pyg_por_mes
                ]
            elif attr_name:
                vals = [getattr(m, attr_name) for m in pyg_por_mes]
            else:
                vals = [0.0] * n
            return vals

        filas: List[VisionPyGRow] = []
        for key, label, seccion, tipo, signo, attr_name, excel_row, formula in _ROW_DEFINITIONS:
            valores = _valores_for(attr_name, tipo)
            acum = sum(valores)

            if not attr_name or n_activos == 0:
                promedio = 0.0
            elif attr_name == "__contribucion_por_puesto__":
                idx = [i for i, m in enumerate(pyg_por_mes) if m.ingreso_neto > 0]
                promedio = sum(valores[i] for i in idx) / len(idx) if idx else 0.0
            elif tipo == "porcentaje":
                promedio = sum(getattr(m, attr_name) for m in activos) / n_activos
                acum = promedio
            else:
                promedio = sum(getattr(m, attr_name) for m in activos) / n_activos

            filas.append(VisionPyGRow(
                key       = key,
                label     = label,
                seccion   = seccion,
                tipo      = tipo,
                signo     = signo,
                valores   = valores,
                acumulado = acum,
                promedio  = promedio,
                excel_row = excel_row,
                formula   = formula,
            ))

        filas_detalle = filas_detalle or []

        # ── Cabecera del deal (Excel P&G rows 2-6) ───────────────────
        fecha_fin_calc = ""
        duracion_contrato = ""
        if panel and fecha_inicio:
            try:
                from datetime import datetime, timedelta
                import calendar as _cal
                fi = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                meses = getattr(panel, "meses_contrato", n)
                end_m = fi.month - 1 + meses
                end_y = fi.year + end_m // 12
                end_m = end_m % 12 + 1
                last = _cal.monthrange(end_y, end_m)[1]
                ff = datetime(end_y, end_m, min(fi.day, last)) - timedelta(days=1)
                fecha_fin_calc = ff.strftime("%Y-%m-%d")
                duracion_contrato = f"{fi.strftime('%d/%m/%Y')} a {ff.strftime('%d/%m/%Y')}"
            except Exception:
                pass

        resumen = ResumenEjecutivoPyG(
            meses_contrato        = n,
            meses_activos         = n_activos,
            valor_total_deal      = kpis.valor_total_deal,
            ingreso_neto_total    = kpis.ingreso_neto_total,
            costo_total_contrato  = kpis.costo_total_contrato,
            contribucion_total    = kpis.contribucion_total,
            pct_utilidad_promedio = kpis.pct_utilidad_neta_total,
            cumple_margen_minimo  = kpis.cumple_margen_minimo,
            # Cabecera del deal — fuente: PanelDeControl
            cliente               = getattr(panel, "cliente", "") if panel else "",
            tipo_cliente          = getattr(panel, "tipo_cliente", "") if panel else "",
            antiguedad_cliente    = getattr(panel, "antiguedad_cliente", "") if panel else "",
            linea_negocio         = getattr(panel, "linea_negocio", "") if panel else "",
            ciudad                = getattr(panel, "ciudad", "") if panel else "",
            sede                  = getattr(panel, "sede", "") if panel else "",
            fecha_inicio          = fecha_inicio,
            fecha_fin             = fecha_fin_calc,
            duracion_contrato     = duracion_contrato,
            periodo_pago_dias     = getattr(panel, "periodo_pago_dias", 0) if panel else 0,
            divisa                = "COP",
        )

        # Excel P&G row 13: calendar dates per month column
        fechas_meses: List[str] = []
        if fecha_inicio and n > 0:
            try:
                from datetime import datetime
                fi = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                for i in range(n):
                    m = fi.month + i
                    y = fi.year + (m - 1) // 12
                    m = (m - 1) % 12 + 1
                    fechas_meses.append(f"{y}-{m:02d}-01")
            except ValueError:
                pass

        return VisionPyG(
            resumen         = resumen,
            filas           = filas,
            meses_contrato  = n,
            meses_activos   = n_activos,
            filas_detalle   = filas_detalle,
            puestos_trabajo = estaciones,
            fechas_meses    = fechas_meses,
        )
