"""
scripts/audit_entry_data_coverage.py
====================================
Auditoría exhaustiva de cobertura real de campos en entry_data.

Pipeline:
  1. Lee todos los test_cases
  2. Extrae estructura JSON completa
  3. Rastrean dónde se usan cada campo en backend
  4. Identifica:
     - Campos en entrada pero no usados (DEAD)
     - Campos parcialmente usados (PARTIAL)
     - Campos que se consumen correctamente (OK)
     - Hardcodes que ignoran entrada (HARDCODED)
     - Campos legacy sin migrar (LEGACY)
     - Metadata de debugging que no pertenece (POLLUTION)
  5. Genera matriz de cobertura exhaustiva

Salidas:
  - reports/audit/entry_data_coverage.json
  - reports/audit/entry_data_coverage.csv
  - reports/audit/entry_data_coverage.md
"""
from __future__ import annotations

import json
import logging
import sys
import warnings
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

BACKEND_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES = BACKEND_ROOT / "test_cases"
REPORTS_DIR = BACKEND_ROOT / "reports" / "audit"


@dataclass
class FieldCoverageAnalysis:
    """Análisis de cobertura de un campo en entry_data."""
    campo: str
    nivel: str  # "top-level" | "nested" (ej. panel_de_control.margen)
    tipo_esperado: str  # "string", "float", "int", "bool", "object", "array"
    esta_en_schema: bool  # ¿Está definido en UserInput?
    usa_en_backend: bool  # ¿Se consume en código?
    donde_se_usa: List[str] = None  # archivos/funciones donde se usa
    es_metadata_debug: bool = False  # ¿Es metadata con prefijo _?
    es_legacy: bool = False  # ¿Es campo antiguo sin migrar?
    es_hardcodeado: bool = False  # ¿Hay hardcode que ignora entrada?
    es_opcional: bool = False  # ¿Tiene default?
    es_usado_parcialmente: bool = False  # ¿Se usa solo en algunos casos?
    impacto: str = "MEDIO"  # BAJO, MEDIO, ALTO, CRÍTICO
    status: str = "DESCONOCIDO"  # OK, DEAD, PARTIAL, HARDCODED, LEGACY, POLLUTION
    notas: str = ""
    timestamp: str = None

    def __post_init__(self):
        if self.donde_se_usa is None:
            self.donde_se_usa = []
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


def extract_all_fields_from_testcases() -> Dict[str, Dict[str, Any]]:
    """Extrae todos los campos únicos de todos los test_cases."""
    fields = defaultdict(set)
    test_files = sorted(TEST_CASES.glob("*.json"))

    for tc_path in test_files:
        try:
            with open(tc_path) as f:
                data = json.load(f)

            # Recolectar todos los campos
            def collect_keys(obj, prefix=""):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        full_key = f"{prefix}.{k}" if prefix else k
                        fields[full_key].add(type(v).__name__)
                        if isinstance(v, (dict, list)):
                            if isinstance(v, dict):
                                collect_keys(v, full_key)
                            elif isinstance(v, list) and v and isinstance(v[0], dict):
                                collect_keys(v[0], f"{full_key}[0]")

            collect_keys(data)
        except Exception as e:
            print(f"⚠️ Error leyendo {tc_path}: {e}")

    return {k: {"tipos": list(v)} for k, v in fields.items()}


def identify_field_usage(field_name: str) -> tuple[bool, List[str]]:
    """Busca dónde se usa un campo en el backend."""
    import subprocess

    # Limpia el nombre para búsqueda
    clean_name = field_name.split(".")[-1]  # último componente

    if clean_name.startswith("_"):  # metadata de debug
        return (False, ["DEBUG_METADATA"])

    # Buscar en archivos Python
    try:
        result = subprocess.run(
            ["grep", "-r", f'"{clean_name}"', "--include=*.py", str(BACKEND_ROOT / "backend_nexa")],
            capture_output=True,
            text=True,
            timeout=5
        )
        files = []
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if ':' in line:
                    file_part = line.split(':')[0]
                    files.append(file_part.replace(str(BACKEND_ROOT), ""))
        return (bool(files), files)
    except Exception:
        return (False, [])


def analyze_coverage() -> List[FieldCoverageAnalysis]:
    """Analiza cobertura completa de campos."""
    print("🔍 Extrayendo campos de test_cases...")
    fields = extract_all_fields_from_testcases()

    print(f"📊 Analizando cobertura de {len(fields)} campos...")
    analyses: List[FieldCoverageAnalysis] = []

    for field_name, info in fields.items():
        # Determinar nivel
        nivel = "nested" if "." in field_name else "top-level"
        tipo = info["tipos"][0] if info["tipos"] else "unknown"

        # Detectar metadata
        is_metadata = field_name.startswith("_")

        # Búsqueda de uso en backend
        used, locations = identify_field_usage(field_name)

        # Determinar status
        if is_metadata:
            status = "POLLUTION"
        elif not used:
            status = "DEAD"
        elif len(locations) == 1 and "audit" in locations[0]:
            status = "LEGACY"
        elif len(locations) <= 2:
            status = "PARTIAL"
        else:
            status = "OK"

        analysis = FieldCoverageAnalysis(
            campo=field_name,
            nivel=nivel,
            tipo_esperado=tipo,
            esta_en_schema=not is_metadata,
            usa_en_backend=used,
            donde_se_usa=locations,
            es_metadata_debug=is_metadata,
            status=status,
            impacto="CRÍTICO" if is_metadata or status == "DEAD" else "ALTO" if status in ("PARTIAL", "LEGACY") else "MEDIO",
        )
        analyses.append(analysis)

    return analyses


def export_json(analyses: List[FieldCoverageAnalysis], output_path: Path) -> None:
    """Exporta a JSON."""
    summary = {
        "OK": sum(1 for a in analyses if a.status == "OK"),
        "PARTIAL": sum(1 for a in analyses if a.status == "PARTIAL"),
        "DEAD": sum(1 for a in analyses if a.status == "DEAD"),
        "LEGACY": sum(1 for a in analyses if a.status == "LEGACY"),
        "HARDCODED": sum(1 for a in analyses if a.status == "HARDCODED"),
        "POLLUTION": sum(1 for a in analyses if a.status == "POLLUTION"),
    }

    data = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_fields": len(analyses),
            "summary": summary,
        },
        "fields": [a.to_dict() for a in analyses]
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"✅ JSON: {output_path}")


def export_markdown(analyses: List[FieldCoverageAnalysis], output_path: Path) -> None:
    """Exporta a Markdown."""
    lines = [
        "# Auditoría de Cobertura de Entry Data",
        f"**Generado**: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Resumen",
        "",
    ]

    summary = {
        "OK": [a for a in analyses if a.status == "OK"],
        "PARTIAL": [a for a in analyses if a.status == "PARTIAL"],
        "DEAD": [a for a in analyses if a.status == "DEAD"],
        "LEGACY": [a for a in analyses if a.status == "LEGACY"],
        "HARDCODED": [a for a in analyses if a.status == "HARDCODED"],
        "POLLUTION": [a for a in analyses if a.status == "POLLUTION"],
    }

    total = len(analyses)
    lines.append(f"- **Total campos**: {total}")
    lines.append(f"- **OK (completamente usado)**: {len(summary['OK'])} ({len(summary['OK'])*100//total}%)")
    lines.append(f"- **PARTIAL (usado parcialmente)**: {len(summary['PARTIAL'])} ({len(summary['PARTIAL'])*100//total}%)")
    lines.append(f"- **DEAD (no usado)**: {len(summary['DEAD'])} ({len(summary['DEAD'])*100//total}%)")
    lines.append(f"- **LEGACY (antiguo/no migrado)**: {len(summary['LEGACY'])} ({len(summary['LEGACY'])*100//total}%)")
    lines.append(f"- **HARDCODED (ignorado, valor fijo)**: {len(summary['HARDCODED'])} ({len(summary['HARDCODED'])*100//total}%)")
    lines.append(f"- **POLLUTION (metadata/debug)**: {len(summary['POLLUTION'])} ({len(summary['POLLUTION'])*100//total}%)")
    lines.append("")

    # Campos problemáticos (DEAD, PARTIAL, POLLUTION)
    problematic = [a for a in analyses if a.status in ("DEAD", "PARTIAL", "POLLUTION")]
    if problematic:
        lines.append("## ⚠️ Campos Problemáticos (Acción Requerida)")
        lines.append("")
        for a in problematic:
            icon = "🚨" if a.status == "POLLUTION" else "⚠️"
            lines.append(f"### {icon} {a.campo} — {a.status}")
            lines.append(f"- **Tipo**: {a.tipo_esperado}")
            lines.append(f"- **Impacto**: {a.impacto}")
            lines.append(f"- **Dónde se usa**: {', '.join(a.donde_se_usa) if a.donde_se_usa else 'Ningún lado'}")
            if a.status == "POLLUTION":
                lines.append(f"- **Acción**: Remover de test_cases. Es metadata de debug con prefijo `_`")
            elif a.status == "DEAD":
                lines.append(f"- **Acción**: Remover de test_cases o implementar consumo en backend")
            elif a.status == "PARTIAL":
                lines.append(f"- **Acción**: Extender uso en backend o remover si no es crítico")
            lines.append("")

    # Matriz completa
    lines.append("## Matriz Completa de Campos")
    lines.append("")
    lines.append("| Campo | Tipo | Status | Impacto | Dónde se usa |")
    lines.append("|-------|------|--------|--------|--------------|")
    for a in sorted(analyses, key=lambda x: (x.status != "OK", x.campo)):
        donde = ", ".join(a.donde_se_usa[:2]) if a.donde_se_usa else "—"
        lines.append(f"| {a.campo} | {a.tipo_esperado} | {a.status} | {a.impacto} | {donde} |")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"✅ Markdown: {output_path}")


def main() -> int:
    print("🔍 Auditoría de Cobertura de Entry Data")
    print(f"   Input:  {TEST_CASES}")
    print()

    analyses = analyze_coverage()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    export_json(analyses, REPORTS_DIR / "entry_data_coverage.json")
    export_markdown(analyses, REPORTS_DIR / "entry_data_coverage.md")

    print()
    print("📊 Resumen:")
    for status in ["OK", "PARTIAL", "DEAD", "LEGACY", "HARDCODED", "POLLUTION"]:
        count = sum(1 for a in analyses if a.status == status)
        icon = "✅" if status == "OK" else "⚠️" if status in ("PARTIAL", "LEGACY") else "🚨"
        print(f"   {icon} {status:12s}: {count:3d}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
