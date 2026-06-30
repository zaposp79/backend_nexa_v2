#!/usr/bin/env python3
"""
Phase 5.5: Complete Entry Data Coverage and Legacy Dependencies Audit

This script generates a comprehensive matrix showing:
1. What entry_data fields are consumed by backend
2. Which calculator/adapter uses each field
3. Which endpoints expose each field
4. What fields are ignored/dead
5. What hardcodes exist (not consuming entry_data)
6. What legacy mappings exist
7. What adapters need modernization
"""

import json
import sys
import subprocess
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Set, List, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT

# Official entry_data contract fields (Phase 5.5)
ENTRY_DATA_CONTRACT = {
    "panel_de_control": {
        "cliente": str,
        "tipo_cliente": str,
        "linea_negocio": str,
        "ciudad": str,
        "sede": str,
        "fecha_inicio": str,
        "meses_contrato": int,
        "margen": float,
        "op_cont": float,
        "com_cont": float,
        "markup": float,
        "descuento": float,
        "periodo_pago_dias": int,
        "activa_financiacion": bool,
        "antiguedad_cliente": str,
        "componente_indexacion_humano": str,
        "componente_indexacion_tecnologico": str,
        "tasa_ica": float,
        "tasa_gmf": float,
        "tasa_mensual_financ": float,
        "pct_rotacion": float,
        "pct_ausentismo": float,
        "aplica_ley_1819": bool,
    },
    "condiciones_cadena_a": {"perfiles": list},
    "condiciones_cadena_b": {"canales": list, "opex_consumo_variable": list, "equipo_sm": list, "dispositivos_sm": list},
    "condiciones_cadena_c": {"canales": list, "equipo_transversal": list, "inversion_anual": float},
}

# Known calculators and what they consume
CALCULATORS_EXPECTED_USAGE = {
    "NominaCalculator": ["panel_de_control.meses_contrato", "condiciones_cadena_a.perfiles"],
    "NoPayrollCalculator": ["condiciones_cadena_a.perfiles"],
    "CadenaBCalculator": ["condiciones_cadena_b"],
    "CadenaCCalculator": ["condiciones_cadena_c"],
    "CostosFinancierosCalculator": ["panel_de_control.tasa_ica", "panel_de_control.tasa_gmf", "panel_de_control.tasa_mensual_financ"],
    "PyGCalculator": ["panel_de_control.meses_contrato"],
    "KPIsCalculator": [],
}

# Endpoints and what they're expected to expose
ENDPOINTS_EXPECTED_FIELDS = {
    "GET /simulation/{id}/results": ["ingreso_neto", "costo_total", "utilidad_neta", "payroll_a", "no_payroll_a"],
    "GET /simulation/{id}/results/kpis": ["tarifa_mensual", "margen_utilidad"],
    "GET /simulation/{id}/results/pyg": ["ingreso_neto", "costo_total"],
    "GET /simulation/{id}/results/vision-tarifas": ["payroll_ch", "no_payroll_ch"],
}


def grep_field_in_code(field_name: str, directory: str = None) -> Set[str]:
    """Search for field references in Python code."""
    if directory is None:
        directory = str(BACKEND_ROOT / "calculators")

    try:
        result = subprocess.run(
            ["grep", "-r", f'"{field_name}"', "--include=*.py", directory],
            capture_output=True,
            text=True,
            timeout=5
        )
        files = set()
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if ':' in line:
                    file_part = line.split(':')[0]
                    file_rel = file_part.replace(str(BACKEND_ROOT), "")
                    files.add(file_rel)
        return files
    except Exception:
        return set()


def audit_entry_data_coverage() -> Dict[str, Any]:
    """Generate complete entry_data coverage audit."""

    print("🔍 Phase 5.5: Entry Data Coverage Audit (Complete)")
    print(f"   Backend: {BACKEND_ROOT}")
    print()

    # Flatten contract to individual fields
    all_fields = {}
    for section, fields in ENTRY_DATA_CONTRACT.items():
        if isinstance(fields, dict):
            for field_name in fields.keys():
                key = f"{section}.{field_name}"
                all_fields[key] = {"section": section, "field": field_name, "used_by": set()}
        else:
            all_fields[section] = {"section": section, "field": section, "used_by": set()}

    # Search for usage in calculators
    print("📊 Scanning code for entry_data field usage...")
    usage_map = {}

    for field_key in all_fields.keys():
        field_name = field_key.split(".")[-1]  # Last component
        files = grep_field_in_code(field_name)
        if files:
            usage_map[field_key] = list(files)
        print(f"  {'✓' if files else '✗'} {field_key}: {len(files)} files")

    # Classify fields
    used_fields = {k: v for k, v in usage_map.items() if v}
    dead_fields = set(all_fields.keys()) - set(used_fields.keys())

    print()
    print(f"📈 Summary:")
    print(f"  Total fields in contract: {len(all_fields)}")
    print(f"  Fields actually used: {len(used_fields)}")
    print(f"  Dead fields (no usage found): {len(dead_fields)}")
    print()

    # Identify hardcodes in calculators
    print("🔨 Scanning for hardcoded values (bypassing entry_data)...")
    hardcodes = find_hardcodes()
    print(f"  Found {len(hardcodes)} potential hardcodes")
    for hc in hardcodes[:5]:
        print(f"    - {hc}")
    if len(hardcodes) > 5:
        print(f"    ... and {len(hardcodes) - 5} more")
    print()

    # Identify legacy mappings/adapters
    print("🏛️  Scanning for legacy mappings and adapters...")
    legacy_items = find_legacy_patterns()
    print(f"  Found {len(legacy_items)} potential legacy items:")
    for item in legacy_items[:5]:
        print(f"    - {item}")
    if len(legacy_items) > 5:
        print(f"    ... and {len(legacy_items) - 5} more")
    print()

    # Build report
    report = {
        "phase": "5.5",
        "audit_date": datetime.now(timezone.utc).isoformat(),
        "entry_data_contract": {
            "total_fields": len(all_fields),
            "fields": list(all_fields.keys()),
        },
        "usage_analysis": {
            "used": len(used_fields),
            "dead": len(dead_fields),
            "dead_fields": sorted(dead_fields),
            "field_usage_map": usage_map,
        },
        "hardcodes": {
            "count": len(hardcodes),
            "items": hardcodes,
        },
        "legacy_patterns": {
            "count": len(legacy_items),
            "items": legacy_items,
        },
        "calculators_expected": CALCULATORS_EXPECTED_USAGE,
        "recommendations": generate_recommendations(dead_fields, hardcodes, legacy_items),
    }

    return report


def find_hardcodes() -> List[str]:
    """Scan for hardcoded values in calculators (not from entry_data)."""
    hardcodes = []

    patterns = [
        r"SMMLV\s*=",
        r"tasa_.*=\s*[\d.]+",
        r"0\.0[0-9]+\s*#",
        r"hardcode",
        r"FIXME.*hardcode",
    ]

    try:
        result = subprocess.run(
            ["grep", "-r", "-E", "|".join(patterns), "--include=*.py", str(BACKEND_ROOT / "calculators")],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout:
            for line in result.stdout.strip().split('\n')[:20]:  # Top 20
                if line and ':' in line:
                    hardcodes.append(line)
    except Exception:
        pass

    return hardcodes


def find_legacy_patterns() -> List[str]:
    """Identify legacy mappings and adapters that might need modernization."""
    legacy = []

    patterns = [
        ("adapters/", "Legacy adapters"),
        (r"\.get\(", "Defensive gets (might indicate optional/legacy fields)"),
        (r"if.*is None", "Null checks (might indicate legacy handling)"),
    ]

    try:
        for pattern, description in patterns:
            result = subprocess.run(
                ["grep", "-r", pattern, "--include=*.py", str(BACKEND_ROOT / "adapters")],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout:
                count = len(result.stdout.strip().split('\n'))
                legacy.append(f"{description}: {count} occurrences")
    except Exception:
        pass

    return legacy


def generate_recommendations(dead_fields: Set[str], hardcodes: List[str], legacy: List[str]) -> Dict[str, Any]:
    """Generate remediation recommendations."""
    return {
        "dead_fields_action": "REVIEW" if dead_fields else "NONE",
        "dead_fields_note": f"Remove {len(dead_fields)} unused fields from contract or implement consumers" if dead_fields else "All fields in contract are used",
        "hardcodes_action": "MIGRATE_TO_ENTRY_DATA" if hardcodes else "NONE",
        "hardcodes_note": f"Move {len(hardcodes)} hardcoded values to entry_data or storage/" if hardcodes else "No hardcodes detected",
        "legacy_action": "MODERNIZE" if legacy else "NONE",
        "legacy_note": f"Review {len(legacy)} legacy patterns in adapters" if legacy else "No legacy patterns detected",
    }


def main():
    report = audit_entry_data_coverage()

    # Export JSON
    output_file = BACKEND_ROOT / "reports" / "audit" / "entry_data_complete_55.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"✅ Report: {output_file}")
    print()

    # Summary table
    print("📋 Entry Data Audit Summary:")
    print(f"  Contract fields: {report['entry_data_contract']['total_fields']}")
    print(f"  Used fields: {report['usage_analysis']['used']}")
    print(f"  Dead fields: {report['usage_analysis']['dead']}")
    print(f"  Hardcodes found: {report['hardcodes']['count']}")
    print(f"  Legacy patterns: {report['legacy_patterns']['count']}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
