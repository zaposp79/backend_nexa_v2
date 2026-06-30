"""F6 — Oracle mesh extractor.

Recorre Excel V2-7 y extrae celdas con valores numéricos calculados de las
hojas relevantes para validation mesh. Salida estructurada con stage,
categoría y coordenada — compatible con `tests/parity/oracle_mesh_mapping.py`.

USO:
    source venv/bin/activate
    python scripts/extract_oracle_mesh.py

OUTPUTS:
    tests/parity/excel_oracle_v2_7_mesh.json
"""
from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

warnings.filterwarnings("ignore")

import openpyxl

EXCEL_PATH = Path("/Users/darwin.minota.quinto/Downloads/Nexa - Pricing - Simulador - V2-7.xlsx")
OUT_PATH = Path(__file__).resolve().parents[1] / "tests" / "parity" / "excel_oracle_v2_7_mesh.json"


def _is_numeric_cell(c) -> bool:
    return c.value is not None and isinstance(c.value, (int, float)) and not isinstance(c.value, bool)


def _label_left(sheet, row, col):
    """Look left for a textual label on same row (helpful documentation)."""
    for cc in range(col - 1, 0, -1):
        v = sheet.cell(row=row, column=cc).value
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _add(buf, sheet, cell, *, stage, category, label_hint=""):
    if not _is_numeric_cell(cell):
        return
    coord = f"{sheet.title}!{cell.coordinate}"
    if coord in buf:
        return
    label = label_hint or _label_left(sheet, cell.row, cell.column)
    buf[coord] = {
        "value": float(cell.value),
        "label": label,
        "stage": stage,
        "category": category,
        "row": cell.row,
        "column": cell.column,
    }


def extract():
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    cells: dict[str, dict] = {}

    # --------------------------------------------------------------------- INPUT / PANEL
    s = wb["Panel de Control General"]
    for row in range(4, 90):
        for col in ["C", "D", "E", "F"]:
            c = s[f"{col}{row}"]
            if _is_numeric_cell(c) and 0 < abs(c.value) < 1e15:
                _add(cells, s, c, stage="INPUT", category="PANEL")

    # --------------------------------------------------------------------- INPUT NOMINA
    s = wb["Inputs de Nomina"]
    # Constants (C4-C11)
    for row in range(4, 12):
        c = s[f"C{row}"]
        _add(cells, s, c, stage="INPUT", category="NOMINA_PARAMS")
    # Per-profile aggregates: rows 16,26,39,40 etc — also W column ("C. Empresa total")
    for row in [16, 26, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48]:
        for col in ["C", "D", "E", "F", "G", "H", "I", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W"]:
            c = s[f"{col}{row}"]
            if _is_numeric_cell(c) and abs(c.value) > 0:
                stage = "INTERMEDIATE" if col in "MNOPQRSTUVW" else "INPUT"
                _add(cells, s, c, stage=stage, category="NOMINA_PERFIL")

    # --------------------------------------------------------------------- NOMINA LOADED — aggregations per canal/mes
    s = wb["Nomina Loaded"]
    # Known aggregate rows from earlier exploration: 89, 93, 97, 100, 117, 118
    for row in [89, 93, 97, 100, 103, 117, 118, 119]:
        for col_letter in "HIJKLMNOPQRSTUVW":
            c = s[f"{col_letter}{row}"]
            if _is_numeric_cell(c) and abs(c.value) > 1:
                _add(cells, s, c, stage="AGGREGATE", category="NOMINA_LOADED_AGGR")

    # --------------------------------------------------------------------- No payroll
    s = wb["No payroll"]
    for row in range(1, 60):
        for col_letter in "CDEFGHIJKLMNOP":
            c = s[f"{col_letter}{row}"]
            if _is_numeric_cell(c) and abs(c.value) > 1:
                _add(cells, s, c, stage="INTERMEDIATE", category="NO_PAYROLL")
        if len([k for k in cells if k.startswith("No payroll!")]) > 30:
            break

    # --------------------------------------------------------------------- Costo Fijo / Variable
    for sn, cat in [("Costo Fijo", "COSTO_FIJO"), ("Costo Variable", "COSTO_VAR"), ("Costo Cadena C", "CADENA_C"), ("Costos Totales", "COSTOS_TOTALES")]:
        s = wb[sn]
        added = 0
        for row in range(1, 80):
            for col_letter in "CDEFGHIJKLMNOPQ":
                c = s[f"{col_letter}{row}"]
                if _is_numeric_cell(c) and abs(c.value) > 1:
                    _add(cells, s, c, stage="AGGREGATE", category=cat)
                    added += 1
            if added > 60:
                break

    # --------------------------------------------------------------------- Tasas, TRM, Polizas
    s = wb["Tasas, TRM, Polizas"]
    for row in range(1, 60):
        for col_letter in "BCDEFGH":
            c = s[f"{col_letter}{row}"]
            if _is_numeric_cell(c) and 0 < abs(c.value):
                _add(cells, s, c, stage="INPUT", category="POLIZAS_TASAS")

    # --------------------------------------------------------------------- Polizas - Costo Financiacion
    s = wb["Pólizas - Costo Financiacion"]
    for row in range(1, 80):
        for col_letter in "CDEFGHIJ":
            c = s[f"{col_letter}{row}"]
            if _is_numeric_cell(c) and abs(c.value) > 1:
                _add(cells, s, c, stage="INTERMEDIATE", category="COSTOS_FINANCIEROS")

    # --------------------------------------------------------------------- Vision Tarifas_Modelo_Cobro — already partially extracted
    s = wb["Vision Tarifas_Modelo_Cobro"]
    for row in range(15, 80):
        for col_letter in "BCDEFGH":
            c = s[f"{col_letter}{row}"]
            if _is_numeric_cell(c) and abs(c.value) > 1e-9:
                stage = "OUTPUT" if row >= 60 else ("INTERMEDIATE" if row >= 30 else "INPUT")
                _add(cells, s, c, stage=stage, category="VISION_TARIFAS")

    # --------------------------------------------------------------------- Vision Cost To Serve
    s = wb["Vision Cost To Serve"]
    for row in range(15, 80):
        for col_letter in "BCDEFGHIJKLMN":
            c = s[f"{col_letter}{row}"]
            if _is_numeric_cell(c) and abs(c.value) > 1e-9:
                stage = "OUTPUT" if row >= 60 else "INTERMEDIATE"
                _add(cells, s, c, stage=stage, category="VISION_CTS")

    # --------------------------------------------------------------------- Visión P&G monthly grid
    s = wb["Visión P&G"]
    # Rows 15..79 with cols C..N (12 months)
    for row in range(13, 82):
        for col_letter in "CDEFGHIJKLMN":
            c = s[f"{col_letter}{row}"]
            if _is_numeric_cell(c) and abs(c.value) > 1e-9:
                _add(cells, s, c, stage="OUTPUT", category="VISION_PYG")

    # --------------------------------------------------------------------- Rot, Ausent y Rentabilidad
    s = wb["Rot, Ausent y Rentabilidad"]
    for row in range(1, 30):
        for col_letter in "BCDEFGHIJ":
            c = s[f"{col_letter}{row}"]
            if _is_numeric_cell(c) and abs(c.value) > 0:
                _add(cells, s, c, stage="INPUT", category="ROTACION_AUSENTISMO")

    return wb, cells


def main():
    wb, cells = extract()
    # Sheet coverage stats
    by_sheet = {}
    by_stage = {}
    by_category = {}
    for coord, meta in cells.items():
        sheet = coord.split("!")[0]
        by_sheet[sheet] = by_sheet.get(sheet, 0) + 1
        by_stage[meta["stage"]] = by_stage.get(meta["stage"], 0) + 1
        by_category[meta["category"]] = by_category.get(meta["category"], 0) + 1

    # workbook hash from prior oracle (don't recompute — keep consistent)
    workbook_sha = sha256(EXCEL_PATH.read_bytes()).hexdigest()
    out = {
        "_metadata": {
            "workbook_sha256": workbook_sha,
            "workbook_path": str(EXCEL_PATH),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "extractor_version": "F6",
            "total_cells": len(cells),
            "by_sheet": by_sheet,
            "by_stage": by_stage,
            "by_category": by_category,
        },
        "cells": cells,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"Wrote {OUT_PATH}")
    print(f"Total cells: {len(cells)}")
    print(f"By stage: {by_stage}")
    print(f"By sheet: {by_sheet}")


if __name__ == "__main__":
    main()
