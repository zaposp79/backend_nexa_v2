#!/usr/bin/env python3
"""
scripts/extract_frozen_v26.py
=============================
Extrae todos los parámetros del Excel V2-6 y genera storage/parametrization/frozen/v2-6.json

Uso:
    python scripts/extract_frozen_v26.py /path/to/Nexa*.xlsx
"""

import json
import sys
from pathlib import Path
from openpyxl import load_workbook

def extract_frozen_v26(excel_path: str) -> dict:
    """
    Extrae parámetros críticos del Excel V2-6.

    Retorna un dict con toda la información necesaria para FrozenParametrizationV26.
    """
    wb = load_workbook(excel_path, data_only=True)

    # ── Hoja: Inputs de Nomina ───────────────────────────────────────
    sheet_nomina = wb["Inputs de Nomina"]
    smmlv = float(sheet_nomina["C4"].value or 0)
    auxilio_transporte = float(sheet_nomina["C5"].value or 0)

    # ── Hoja: Tasas, TRM, Polizas ────────────────────────────────────
    sheet_tasas = wb["Tasas, TRM, Polizas"]

    # Factores de indexación (años 1-6, 2025-2030, columns B-G)
    # Row 8 = IPC, Row 9 = SMMLV, Row 10 = 70%SMMLV+30%IPC, Row 11 = IPC+1PUNTO,
    # Row 12 = Fixed, Row 15 = 80%SMMLV+20%IPC, Row 16 = 20%SMMLV+80%IPC
    def safe_float_list(sheet, row, cols="BCDEFG"):
        """Lee una fila y retorna lista de floats, skip si no es número."""
        values = []
        for col in cols:
            try:
                v = sheet[f"{col}{row}"].value
                values.append(float(v) if v else 1.0)
            except (TypeError, ValueError):
                values.append(1.0)
        return values

    factores_indexacion = {
        "ipc": safe_float_list(sheet_tasas, 8),
        "smmlv": safe_float_list(sheet_tasas, 9),
        "mix_70_30": safe_float_list(sheet_tasas, 10),
        "ipc_plus_1": safe_float_list(sheet_tasas, 11),
        "fixed": [1.0] * 6,
        "mix_80_20": safe_float_list(sheet_tasas, 15),
        "mix_20_80": safe_float_list(sheet_tasas, 16),
    }

    # Pólizas rates (B22:B29)
    polizas_tasas = {
        "seriedad": float(sheet_tasas["B22"].value or 0),
        "cumplimiento": float(sheet_tasas["B23"].value or 0),
        "salarios": float(sheet_tasas["B24"].value or 0),
        "calidad": float(sheet_tasas["B25"].value or 0),
        "rc_cruzada": float(sheet_tasas["B26"].value or 0),
        "irf": float(sheet_tasas["B27"].value or 0),
        "responsabilidad": float(sheet_tasas["B28"].value or 0),
        "admin_commission": float(sheet_tasas["B29"].value or 0),
    }

    # Tasas (ICA, GMF, Timbre) - rows 30-32
    ica_base = float(sheet_tasas["B30"].value or 0.01966)
    gmf = float(sheet_tasas["B31"].value or 0.004)
    timbre = float(sheet_tasas["B32"].value or 0.01)

    # ICA por ciudad - buscar en rango (puede variar)
    # Estructura: Ciudad | ICA Base | ...
    ica_por_ciudad = {}
    for row in range(30, 80):  # Escanea más filas para encontrar las ciudades
        ciudad_cell = sheet_tasas[f"A{row}"].value
        ica_cell = sheet_tasas[f"B{row}"].value
        if (ciudad_cell and isinstance(ciudad_cell, str) and
            not any(x in str(ciudad_cell).lower() for x in ["ica", "gmf", "timbre", "tasa", "aumento"])):
            try:
                ica_rate = float(ica_cell) if ica_cell else ica_base
                ica_por_ciudad[ciudad_cell.strip()] = ica_rate
            except (TypeError, ValueError):
                pass

    # ── Hoja: Panel de Control General ────────────────────────────────
    sheet_panel = wb["Panel de Control General"]

    absenteeism_default = float(sheet_panel["C19"].value or 0.065)
    rotation_default = float(sheet_panel["C20"].value or 0.085)
    target_margin = float(sheet_panel["C63"].value or 0.18)

    # ── Hoja: Rot, Ausent y Rentabilidad ─────────────────────────────
    sheet_rot = wb["Rot, Ausent y Rentabilidad"]

    # Absenteeism por servicio (rows 7-10, F = promedio)
    absenteeism_by_service = {
        "cobranzas": float(sheet_rot["F7"].value or 0.0826),
        "sac": float(sheet_rot["F8"].value or 0.0820),
        "ventas_multicanal": float(sheet_rot["F9"].value or 0.1010),
        "saco": float(sheet_rot["F10"].value or 0.0806),
    }

    # Rotation por servicio (rows 18-21, F)
    rotation_by_service = {
        "cobranzas": float(sheet_rot["F18"].value or 0.1199),
        "sac": float(sheet_rot["F19"].value or 0.0772),
        "ventas_multicanal": float(sheet_rot["F20"].value or 0.0952),
        "saco": float(sheet_rot["F21"].value or 0.0964),
    }

    # Experience ramp (9-month productivity curve)
    experience_ramp = {
        "cobranzas": [
            float(sheet_rot[f"B{i}"].value or 1.0)
            for i in range(38, 47)
        ],
        "sac": [
            float(sheet_rot[f"C{i}"].value or 1.0)
            for i in range(38, 47)
        ],
        "ventas_multicanal": [
            float(sheet_rot[f"D{i}"].value or 1.0)
            for i in range(38, 47)
        ],
    }

    # Medical exam costs (rows 67-73)
    medical_exam_cost_bogota = float(sheet_rot["B67"].value or 60800)
    medical_exam_cost_other = float(sheet_rot["B68"].value or 58000)
    security_study_preliminary = float(sheet_rot["B69"].value or 54055)
    security_study_final = float(sheet_rot["B70"].value or 144879)

    # ── Extraer salarios por rol ──────────────────────────────────────
    # Ubicados en "Inputs de Nomina" rows 11+ (Inbound 10, Supervisor, etc.)
    salarios_por_rol = {}
    for row in range(11, 50):  # Scan hasta row 50
        rol_name = sheet_nomina[f"A{row}"].value
        sal_value = sheet_nomina[f"C{row}"].value
        if rol_name and sal_value and isinstance(rol_name, str):
            try:
                salarios_por_rol[rol_name.strip()] = float(sal_value)
            except (TypeError, ValueError):
                pass

    return {
        "version": "v2-6",
        "source": "Excel Nexa Pricing Simulator V2-6",
        "smmlv": smmlv,
        "auxilio_transporte": auxilio_transporte,
        "factores_indexacion": factores_indexacion,
        "polizas_tasas": polizas_tasas,
        "ica_base": ica_base,
        "ica_por_ciudad": ica_por_ciudad,
        "gmf": gmf,
        "timbre": timbre,
        "absenteeism_default": absenteeism_default,
        "rotation_default": rotation_default,
        "target_margin": target_margin,
        "absenteeism_by_service": absenteeism_by_service,
        "rotation_by_service": rotation_by_service,
        "experience_ramp": experience_ramp,
        "medical_exam_cost_bogota": medical_exam_cost_bogota,
        "medical_exam_cost_other": medical_exam_cost_other,
        "security_study_preliminary": security_study_preliminary,
        "security_study_final": security_study_final,
        "salarios_por_rol": salarios_por_rol,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_frozen_v26.py <path_to_excel>")
        sys.exit(1)

    excel_path = sys.argv[1]
    print(f"Extrayendo parámetros de {excel_path}...")

    frozen_data = extract_frozen_v26(excel_path)

    # Guardar en storage/parametrization/frozen/v2-6.json
    storage_dir = Path("storage/parametrization/frozen")
    storage_dir.mkdir(parents=True, exist_ok=True)

    output_file = storage_dir / "v2-6.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(frozen_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Parámetros guardados en {output_file}")
    print(f"   - SMMLV: {frozen_data['smmlv']:,.0f}")
    print(f"   - Auxilio: {frozen_data['auxilio_transporte']:,.0f}")
    print(f"   - ICA base: {frozen_data['ica_base']:.4f}")
    print(f"   - GMF: {frozen_data['gmf']:.4f}")
    print(f"   - Ciudades: {len(frozen_data['ica_por_ciudad'])}")
    print(f"   - Roles: {len(frozen_data['salarios_por_rol'])}")
