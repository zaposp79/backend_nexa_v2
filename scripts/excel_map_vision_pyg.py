"""
scripts/excel_map_vision_pyg.py
===============================
SHEET_TYPE: vista
Hoja Excel V2-8: 'Visión P&G'

Mapa de celdas ancla del P&G (mes 1) backend <-> Excel V2-8.
Semilla heredada de scripts/validate_excel.py (probada en V2-7). Las
coordenadas se re-verifican contra V2-8 en Stage 2 (el diff V2-7->V2-8 marcó
'Visión P&G' con 3 transiciones de fórmula + 495 constantes).
"""
from __future__ import annotations

SHEET_NAME = "Visión P&G"
SHEET_TYPE = "vista"

# backend metric (PyGMensual mes 1) -> (celda V2-8, descripción)
PYG_ANCHOR_CELLS: dict[str, dict] = {
    "payroll_a":    {"cell": "C31", "desc": "Payroll Inbound mes 1"},
    "no_payroll_a": {"cell": "C40", "desc": "No Payroll mes 1"},
    "costo_b":      {"cell": "C44", "desc": "Costos Cadena B mes 1"},
    "financiacion": {"cell": "C65", "desc": "Costos Financieros mes 1"},
    "ingreso_neto": {"cell": "C26", "desc": "Ingreso Neto mes 1"},
    "pct_utilidad_neta": {"cell": "C75", "desc": "% Utilidad Neta mes 1"},
}
