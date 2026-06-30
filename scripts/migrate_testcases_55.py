#!/usr/bin/env python3
"""
Migrate test_cases from contaminated structure to clean structure (Phase 5.5)

This script:
1. Reads existing test_cases/*.json files
2. Extracts POLLUTION fields (starting with _) → expected/*.expected.json
3. Extracts clean data → input/*.json
4. Creates audit/*.audit.json with migration metadata
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES_DIR = PROJECT_ROOT / "test_cases"

# Original test case files (flat structure)
TEST_CASE_FILES = [
    "bancamia_whatsapp_only.json",
    "bancamia_excel_match.json",
    "bancamia_canonical_k50.json",
    "bancamia_cobranzas.json",
    "bancamia_correo_only.json",
    "bancamia_webchat_only.json",
    "seguros_adl_cobranzas.json",
    "excel_v24_canonical_bancamia.json",
]

# List of known POLLUTION fields (metadata with _ prefix)
KNOWN_POLLUTION_FIELDS = {
    "_comment",
    "_scenario",
    "_k50_expected",
    "_l50_expected",
    "_part_a_expected",
    "_part_b_expected",
    "_cts_a_expected",
    "_cts_b_expected",
    "_cts_ponderado_expected",
    "_source",
    "_note",
    "_excel_smmlv",
    "_backend_smmlv",
    "_expected_discrepancy",
    "_excel_facturacion_esperada",
    "_excel_payroll_mes1",
    "_excel_polizas_mes1",
    "_excel_ica_mes1",
    "_excel_pct_utilidad_steady",
}

# Legitimate entry_data contract fields
LEGITIMATE_TOP_LEVEL_FIELDS = {
    "panel_de_control",
    "condiciones_cadena_a",
    "condiciones_cadena_b",
    "condiciones_cadena_c",
    "parametros_nomina",
    "reglas_negocio",
    "contingencia_operativa",
    "escenarios_comerciales",
}


def separate_metadata_and_data(data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Separate POLLUTION fields from legitimate entry_data.

    Returns:
        (metadata_dict, clean_data_dict)
    """
    metadata = {}
    clean_data = {}

    for key, value in data.items():
        if key.startswith("_"):
            metadata[key] = value
        else:
            clean_data[key] = value

    return metadata, clean_data


def migrate_test_case(filename: str) -> Dict[str, Any]:
    """
    Migrate a single test case file.

    Returns:
        {
            "file": filename,
            "status": "SUCCESS" | "ERROR",
            "pollution_fields": [...],
            "clean_fields": [...],
            "message": "...",
            "input_file": "...",
            "expected_file": "...",
            "audit_file": "..."
        }
    """
    original_path = TEST_CASES_DIR / filename

    if not original_path.exists():
        return {
            "file": filename,
            "status": "ERROR",
            "message": f"File not found: {original_path}",
        }

    try:
        with open(original_path) as f:
            data = json.load(f)
    except Exception as e:
        return {
            "file": filename,
            "status": "ERROR",
            "message": f"Failed to parse JSON: {e}",
        }

    # Separate metadata and clean data
    metadata, clean_data = separate_metadata_and_data(data)

    # Determine base name (without .json)
    base_name = filename.replace(".json", "")

    # Write clean data to input/
    input_file = TEST_CASES_DIR / "input" / f"{base_name}.json"
    try:
        with open(input_file, "w") as f:
            json.dump(clean_data, f, indent=2, default=str)
    except Exception as e:
        return {
            "file": filename,
            "status": "ERROR",
            "message": f"Failed to write input file: {e}",
        }

    # Write metadata + validation values to expected/
    expected_file = TEST_CASES_DIR / "expected" / f"{base_name}.expected.json"
    expected_data = {
        "metadata": metadata,
        "expected_values": {
            "description": "Expected output values for validation against Excel",
            "note": "These values are extracted from Excel V2-4 for comparison"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    try:
        with open(expected_file, "w") as f:
            json.dump(expected_data, f, indent=2, default=str)
    except Exception as e:
        return {
            "file": filename,
            "status": "ERROR",
            "message": f"Failed to write expected file: {e}",
        }

    # Write audit metadata to audit/
    audit_file = TEST_CASES_DIR / "audit" / f"{base_name}.audit.json"
    audit_data = {
        "original_file": str(original_path),
        "migration_date": datetime.now(timezone.utc).isoformat(),
        "pollution_fields_removed": list(metadata.keys()),
        "pollution_fields_count": len(metadata),
        "clean_fields": list(clean_data.keys()),
        "clean_fields_count": len(clean_data),
        "input_file": str(input_file),
        "expected_file": str(expected_file),
        "audit_file": str(audit_file),
        "status": "MIGRATED_PHASE_55",
    }
    try:
        with open(audit_file, "w") as f:
            json.dump(audit_data, f, indent=2, default=str)
    except Exception as e:
        return {
            "file": filename,
            "status": "ERROR",
            "message": f"Failed to write audit file: {e}",
        }

    return {
        "file": filename,
        "status": "SUCCESS",
        "pollution_fields": list(metadata.keys()),
        "pollution_fields_count": len(metadata),
        "clean_fields": list(clean_data.keys()),
        "clean_fields_count": len(clean_data),
        "input_file": str(input_file),
        "expected_file": str(expected_file),
        "audit_file": str(audit_file),
    }


def main():
    print("🔄 Phase 5.5 Migration: Separating Contaminated Test Cases")
    print(f"   Source: {TEST_CASES_DIR}")
    print()

    results = []
    total_pollution_fields = 0
    successful = 0

    for filename in TEST_CASE_FILES:
        result = migrate_test_case(filename)
        results.append(result)

        if result["status"] == "SUCCESS":
            successful += 1
            total_pollution_fields += result.get("pollution_fields_count", 0)
            print(f"✅ {filename}")
            print(f"   → input/{filename}")
            print(f"   → expected/{filename.replace('.json', '.expected.json')}")
            print(f"   Removed {result['pollution_fields_count']} pollution fields")
        else:
            print(f"❌ {filename}: {result['message']}")

    print()
    print(f"📊 Summary:")
    print(f"   Total files processed: {len(TEST_CASE_FILES)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {len(TEST_CASE_FILES) - successful}")
    print(f"   Total POLLUTION fields removed: {total_pollution_fields}")

    # Write summary report
    summary_file = TEST_CASES_DIR / "audit" / "migration_summary.json"
    summary_data = {
        "phase": "5.5",
        "migration_date": datetime.now(timezone.utc).isoformat(),
        "total_files": len(TEST_CASE_FILES),
        "successful": successful,
        "failed": len(TEST_CASE_FILES) - successful,
        "total_pollution_fields_removed": total_pollution_fields,
        "results": results,
    }
    with open(summary_file, "w") as f:
        json.dump(summary_data, f, indent=2, default=str)

    print(f"   → Summary: audit/migration_summary.json")
    print()

    return 0 if successful == len(TEST_CASE_FILES) else 1


if __name__ == "__main__":
    sys.exit(main())
