#!/usr/bin/env python3
"""
Phase 5.5: Normalize input files to official entry_data contract

This script:
1. Removes legacy field names (parametros_* → condiciones_*)
2. Removes non-contracted fields (parametros_calculo, validaciones, etc.)
3. Renames old field names to new official names
4. Generates audit trail
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES_INPUT = PROJECT_ROOT / "test_cases" / "input"

# Field renames (legacy → official)
FIELD_RENAMES = {
    "perfiles_cadena_a": "condiciones_cadena_a",
    "parametros_cadena_a": "condiciones_cadena_a",
    "parametros_cadena_b": "condiciones_cadena_b",
    "parametros_cadena_c": "condiciones_cadena_c",
}

# Fields to remove entirely (not part of official contract)
FIELDS_TO_REMOVE = {
    "parametros_calculo",
    "parametros_no_payroll",
    "parametros_nomina",  # This should be optional in panel, not root
    "validaciones",
    "audit_info",
    "debug_info",
}

# Official contract fields (root level)
OFFICIAL_ROOT_FIELDS = {
    "panel_de_control",
    "condiciones_cadena_a",
    "condiciones_cadena_b",
    "condiciones_cadena_c",
    "parametros_nomina",  # Optional
    "reglas_negocio",     # Optional
    "contingencia_operativa",  # Optional
    "escenarios_comerciales",  # Optional
}


def normalize_input_file(filepath: Path) -> Tuple[bool, str]:
    """
    Normalize a single input file.

    Returns:
        (success: bool, message: str)
    """
    try:
        with open(filepath) as f:
            data = json.load(f)
    except Exception as e:
        return False, f"Failed to read: {e}"

    original_keys = set(data.keys())
    changes = []

    # Step 1: Remove prohibited fields
    for field in FIELDS_TO_REMOVE:
        if field in data:
            del data[field]
            changes.append(f"REMOVED: {field}")

    # Step 2: Rename legacy fields
    for old_name, new_name in FIELD_RENAMES.items():
        if old_name in data:
            data[new_name] = data.pop(old_name)
            changes.append(f"RENAMED: {old_name} → {new_name}")

    # Step 3: Convert arrays to official structure
    # If condiciones_cadena_a/b/c is an array, wrap in proper structure
    if "condiciones_cadena_a" in data:
        if isinstance(data["condiciones_cadena_a"], list):
            data["condiciones_cadena_a"] = {"perfiles": data["condiciones_cadena_a"]}
            changes.append("WRAPPED: condiciones_cadena_a array → {perfiles: [...]}")

    if "condiciones_cadena_b" in data:
        cadena_b = data["condiciones_cadena_b"]
        if isinstance(cadena_b, list):
            data["condiciones_cadena_b"] = {"canales": cadena_b}
            changes.append("WRAPPED: condiciones_cadena_b array → {canales: [...]}")
        elif isinstance(cadena_b, dict):
            # Remove unknown fields from cadena_b
            cadena_b_valid = {
                "canales": cadena_b.get("canales", []),
                "opex_consumo_variable": cadena_b.get("opex_consumo_variable", []),
                "equipo_sm": cadena_b.get("equipo_sm", []),
                "dispositivos_sm": cadena_b.get("dispositivos_sm", []),
                "inversion_plataforma": cadena_b.get("inversion_plataforma", 0.0),
                "fte_equipo_sm": cadena_b.get("fte_equipo_sm", 1.0),
                "amortizar_dispositivos_sm": cadena_b.get("amortizar_dispositivos_sm", True),
            }
            # Remove empty/default values to keep file clean
            cadena_b_clean = {k: v for k, v in cadena_b_valid.items() if v}
            unknown_b = set(cadena_b.keys()) - set(cadena_b_valid.keys())
            if unknown_b:
                data["condiciones_cadena_b"] = cadena_b_clean
                changes.append(f"CLEANED: condiciones_cadena_b (removed {unknown_b})")

    if "condiciones_cadena_c" in data:
        cadena_c = data["condiciones_cadena_c"]
        if isinstance(cadena_c, list):
            data["condiciones_cadena_c"] = {"canales": cadena_c}
            changes.append("WRAPPED: condiciones_cadena_c array → {canales: [...]}")
        elif isinstance(cadena_c, dict):
            cadena_c_valid = {
                "canales": cadena_c.get("canales", []),
                "equipo_transversal": cadena_c.get("equipo_transversal", []),
                "inversion_anual": cadena_c.get("inversion_anual", 0.0),
            }
            cadena_c_clean = {k: v for k, v in cadena_c_valid.items() if v}
            unknown_c = set(cadena_c.keys()) - set(cadena_c_valid.keys())
            if unknown_c:
                data["condiciones_cadena_c"] = cadena_c_clean
                changes.append(f"CLEANED: condiciones_cadena_c (removed {unknown_c})")

    # Step 4: Validate all remaining root fields are official
    remaining_keys = set(data.keys())
    unknown_fields = remaining_keys - OFFICIAL_ROOT_FIELDS
    if unknown_fields:
        return False, f"Unknown fields remain: {unknown_fields}"

    # Step 5: Write back normalized data
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        return False, f"Failed to write: {e}"

    message = f"✓ {filepath.name} normalized"
    if changes:
        message += f" ({len(changes)} changes: {', '.join(changes[:3])}{'...' if len(changes) > 3 else ''})"

    return True, message


def main():
    print("🔧 Phase 5.5: Normalize Input Files to Official Contract")
    print(f"   Source: {TEST_CASES_INPUT}")
    print()

    if not TEST_CASES_INPUT.exists():
        print(f"❌ Input directory not found: {TEST_CASES_INPUT}")
        return 1

    input_files = list(TEST_CASES_INPUT.glob("*.json"))

    if not input_files:
        print(f"❌ No input files found")
        return 1

    print(f"📋 Processing {len(input_files)} files...")
    print()

    results = []
    successful = 0

    for input_file in sorted(input_files):
        success, message = normalize_input_file(input_file)
        results.append({"file": input_file.name, "success": success, "message": message})

        if success:
            successful += 1
            print(f"  {message}")
        else:
            print(f"  ❌ {input_file.name}: {message}")

    print()
    print(f"📊 Summary:")
    print(f"  Processed: {len(input_files)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {len(input_files) - successful}")

    if successful == len(input_files):
        print()
        print("✅ All input files normalized successfully!")
        print()
        print("📌 Next step: Verify with test_phase55_contract_enforcement.py")
        return 0
    else:
        print()
        print("❌ Some files failed normalization")
        return 1


if __name__ == "__main__":
    sys.exit(main())
