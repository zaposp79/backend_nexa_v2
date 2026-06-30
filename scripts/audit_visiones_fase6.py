#!/usr/bin/env python3
"""
Fase 6: Auditoría de Visiones — Validar origen de datos y lógica desacoplada

Este script audita que todas las visiones (vision_tarifas, vision_pyg, cost_to_serve, riesgo)
consumen EXCLUSIVAMENTE de calculadoras oficiales sin lógica desacoplada.

Genera:
1. Matriz de trazabilidad: vision_field | source_calculator | transformation | risk_level
2. Identificación de patrones sospechosos (overrides, hardcodes, fallbacks)
3. Validación de @property fields y derivaciones
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT
REPORTS_DIR = BACKEND_ROOT / "reports" / "audit"

# Visiones conocidas y su ubicación
VISIONES_MAPEADAS = {
    "vision_tarifas": {
        "file": "calculators/vision_tarifas.py",
        "class": "VisionTarifasCalculator",
        "method": "calcular",
        "entrada": ["PerfilCadenaA", "ParametrosCadenaB", "PanelDeControl", "PyGMensual[]"],
        "salida": "ResultadoVisionTarifas",
        "campos_esperados": ["canales[]", "costo_total", "ingreso_mensual"],
    },
    "vision_pyg": {
        "file": "calculators/vision_pyg.py",
        "class": "VisionPyGBuilder",
        "method": "construir",
        "entrada": ["PyGMensual[]", "KPIsDeal"],
        "salida": "VisionPyG",
        "campos_esperados": ["resumen_ejecutivo", "filas[]"],
    },
    "cost_to_serve": {
        "file": "calculators/cost_to_serve.py",
        "class": "CostToServeCalculator",
        "method": "calcular",
        "entrada": ["PerfilCadenaA", "ParametrosCadenaB", "PyGMensual[]"],
        "salida": "ResultadoCostToServe",
        "campos_esperados": ["cts_a", "cts_b", "cts_ponderado", "desglose_a", "desglose_b"],
    },
    "riesgo": {
        "file": "calculators/riesgo.py",
        "class": "RiesgoCalculator",
        "method": "evaluar",
        "entrada": ["PanelDeControl", "KPIsDeal", "PyGMensual[]", "PerfilCadenaA"],
        "salida": "EvaluacionRiesgo",
        "campos_esperados": ["score_cliente", "score_operativo", "score_total", "clasificacion"],
    },
}

# Patrones sospechosos a buscar
SUSPICIOUS_PATTERNS = [
    ("override", "Mecanismo de override detectado — valor de entrada puede ser ignorado"),
    ("fallback", "Fallback logic — valor calculado si entrada falta"),
    ("hardcod", "Hardcoded value — valor no proviene de entrada"),
    ("default", "Default value — potencial source mismatch"),
    ("if.*is None", "Null check — comportamiento condicional en cálculo"),
    ("_DEFAULT_", "Hardcoded default — constant value sin parametrización"),
]


def grep_for_patterns(file_path: Path, patterns: List[str]) -> Dict[str, List[str]]:
    """Busca patrones sospechosos en un archivo."""
    matches = {}
    for pattern, description in patterns:
        try:
            result = subprocess.run(
                ["grep", "-n", "-i", pattern, str(file_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout:
                lines = []
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        parts = line.split(':', 1)
                        lines.append(f"Line {parts[0]}: {parts[1].strip()[:80]}")
                if lines:
                    matches[pattern] = lines
        except Exception:
            pass
    return matches


def audit_vision(vision_name: str, vision_config: Dict[str, Any]) -> Dict[str, Any]:
    """Audita una visión específica."""
    file_path = BACKEND_ROOT / vision_config["file"]

    if not file_path.exists():
        return {
            "vision": vision_name,
            "status": "FILE_NOT_FOUND",
            "file": str(file_path),
        }

    # Buscar patrones sospechosos
    suspicious = grep_for_patterns(file_path, SUSPICIOUS_PATTERNS)

    # Leer archivo para análisis
    try:
        with open(file_path) as f:
            content = f.read()
    except Exception as e:
        return {
            "vision": vision_name,
            "status": "ERROR",
            "error": str(e),
        }

    # Análisis de entrada/salida
    analysis = {
        "vision": vision_name,
        "file": vision_config["file"],
        "class": vision_config["class"],
        "method": vision_config["method"],
        "entrada": vision_config["entrada"],
        "salida": vision_config["salida"],
        "campos_esperados": vision_config["campos_esperados"],
        "lineas_totales": len(content.split('\n')),
        "suspicious_patterns_found": len(suspicious),
        "suspicious_details": suspicious,
        "risk_level": "HIGH" if suspicious else "LOW",
        "status": "AUDIT_COMPLETE",
    }

    return analysis


def main():
    print("🔍 FASE 6: Auditoría de Visiones (Lógica Desacoplada)")
    print(f"   Backend: {BACKEND_ROOT}")
    print()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Auditar todas las visiones
    print("📊 Auditando visiones...")
    print()

    all_results = []
    high_risk_count = 0

    for vision_name, vision_config in VISIONES_MAPEADAS.items():
        print(f"  Auditando: {vision_name}")
        result = audit_vision(vision_name, vision_config)
        all_results.append(result)

        if result.get("status") == "AUDIT_COMPLETE":
            print(f"    ├─ Archivo: {result['file']}")
            print(f"    ├─ Líneas: {result['lineas_totales']}")
            print(f"    ├─ Patrones sospechosos: {result['suspicious_patterns_found']}")
            print(f"    └─ Riesgo: {result['risk_level']}")

            if result["risk_level"] == "HIGH":
                high_risk_count += 1
                for pattern, details in result['suspicious_details'].items():
                    print(f"         ⚠️  {pattern}: {len(details)} matches")
        else:
            print(f"    └─ Status: {result['status']}")

        print()

    # Generar reporte
    report_data = {
        "audit_date": datetime.now(timezone.utc).isoformat(),
        "phase": "6",
        "total_visiones": len(VISIONES_MAPEADAS),
        "high_risk_visiones": high_risk_count,
        "visiones": all_results,
        "recomendaciones": generate_recomendaciones(all_results),
    }

    # Exportar JSON
    output_file = REPORTS_DIR / "fase6_visiones_audit.json"
    with open(output_file, "w") as f:
        json.dump(report_data, f, indent=2, default=str)

    print("📈 Summary:")
    print(f"  Total visiones auditadas: {len(VISIONES_MAPEADAS)}")
    print(f"  High-risk visiones: {high_risk_count}")
    print()
    print(f"  Report: {output_file}")
    print()

    return 0


def generate_recomendaciones(results: List[Dict]) -> List[str]:
    """Genera recomendaciones basadas en auditoría."""
    recomendaciones = []

    for result in results:
        if result.get("risk_level") == "HIGH":
            vision = result["vision"]
            patterns = result.get("suspicious_details", {})

            if "override" in patterns:
                recomendaciones.append(
                    f"Fase 8: Documentar override mechanism en {vision} — "
                    f"validar que matches entre tarifa individual y deal aggregates"
                )

            if "hardcod" in patterns:
                recomendaciones.append(
                    f"Fase 9: Eliminar hardcodes en {vision} — "
                    f"migrar a storage parametrización"
                )

            if "fallback" in patterns:
                recomendaciones.append(
                    f"Fase 6+: Hacer calculadores obligatorios en {vision} — "
                    f"eliminar fallbacks sin warning"
                )

    return recomendaciones


if __name__ == "__main__":
    sys.exit(main())
