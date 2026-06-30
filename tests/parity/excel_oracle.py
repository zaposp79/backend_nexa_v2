"""Excel V2-7 value oracle.

Reads cells from the V2-7 workbook (data_only=True) so tests can compare backend
output against the exact Excel value.

Configuration:
    Set NEXA_EXCEL_V27 to the absolute path of the V2-7 workbook:

        export NEXA_EXCEL_V27=/path/to/Nexa-Pricing-Simulador-V2-7.xlsx

    If NEXA_EXCEL_V27 is not set or the file does not exist, EXCEL_AVAILABLE
    is False and tests that require it are skipped automatically.

    No default path is used — developer-specific paths must never be committed.

Usage:
    from tests.parity.excel_oracle import read_cell, EXCEL_AVAILABLE
    if EXCEL_AVAILABLE:
        ingreso_m1 = read_cell("Visión P&G", "C18")
"""
from __future__ import annotations

import os
import warnings
from functools import lru_cache
from pathlib import Path

warnings.filterwarnings("ignore")

_raw_path = os.environ.get("NEXA_EXCEL_V27", "").strip()
EXCEL_PATH: Path | None = Path(_raw_path) if _raw_path else None
EXCEL_AVAILABLE: bool = EXCEL_PATH is not None and EXCEL_PATH.exists()


@lru_cache(maxsize=1)
def _wb():
    if not EXCEL_AVAILABLE:
        return None
    import openpyxl  # local import to avoid cost when oracle unused
    return openpyxl.load_workbook(EXCEL_PATH, data_only=True)


def read_cell(sheet: str, coord: str):
    wb = _wb()
    if wb is None:
        raise RuntimeError(
            "Excel oracle no disponible. "
            "Define NEXA_EXCEL_V27=/ruta/al/workbook.xlsx para habilitar los tests de paridad."
        )
    return wb[sheet][coord].value


# Canonical Excel cell references (Visión P&G — pre-loaded case in V2-7).
# NOTE: the V2-7 workbook's canonical case is "Captura de Datos" with
# ramp-up=0 → all P&G cells = 0. These references are kept for traceability.
PYG_CELLS = {
    "ingreso_bruto_m1":   ("Visión P&G", "C18"),
    "ingreso_cadena_a_m1": ("Visión P&G", "C19"),
    "ingreso_cadena_b_m1": ("Visión P&G", "C20"),
    "ingreso_cadena_c_m1": ("Visión P&G", "C21"),
    "ingreso_neto_m1":    ("Visión P&G", "C27"),
    "costo_total_m1":     ("Visión P&G", "C30"),
    "costo_a_m1":         ("Visión P&G", "C31"),
    "costo_b_m1":         ("Visión P&G", "C45"),
    "costo_c_m1":         ("Visión P&G", "C55"),
    "ica_m1":             ("Visión P&G", "C66"),
    "gmf_m1":             ("Visión P&G", "C67"),
    "contribucion_m1":    ("Visión P&G", "C74"),
    "pct_contribucion_m1": ("Visión P&G", "C76"),
    "utilidad_neta_m1":   ("Visión P&G", "C79"),
}

PANEL_INPUTS = {
    "servicio":         ("Panel de Control General", "C5"),
    "cliente":          ("Panel de Control General", "C6"),
    "duracion_meses":   ("Panel de Control General", "C11"),
    "ciudad":           ("Panel de Control General", "C12"),
    "sede":             ("Panel de Control General", "C13"),
    "tasa_ica":         ("Panel de Control General", "C34"),
    "tasa_gmf":         ("Panel de Control General", "C35"),
    "margen_a":         ("Panel de Control General", "C63"),
    "op_cont":          ("Panel de Control General", "C67"),
    "com_cont":         ("Panel de Control General", "C68"),
    "markup":           ("Panel de Control General", "C69"),
    "descuento":        ("Panel de Control General", "C70"),
    "imprevistos":      ("Panel de Control General", "C73"),
}


def panel_snapshot() -> dict:
    """Return the canonical Panel values from the V2-7 workbook."""
    out = {}
    for k, (sheet, coord) in PANEL_INPUTS.items():
        out[k] = read_cell(sheet, coord)
    return out


def pyg_snapshot() -> dict:
    out = {}
    for k, (sheet, coord) in PYG_CELLS.items():
        out[k] = read_cell(sheet, coord)
    return out
