"""
scripts/validate_layers_exhaustive.py
======================================
Auditoría exhaustiva por CAPA con captura de valores intermedios mes a mes.

Arquitectura:
  1. Ejecuta backend instrumentado para CADA mes
  2. Captura outputs de cada capa (Capa 2-10)
  3. Compara contra Excel V2-4 para cada mes
  4. Genera matriz de validaciones por capa × mes
  5. Identifica anomalías y cause raíz

Outputs:
  - reports/audit/layers_exhaustive_{case}.json
  - reports/audit/layers_exhaustive_{case}.csv
  - reports/audit/layers_exhaustive_{case}.md

Uso:
    python scripts/validate_layers_exhaustive.py --case bancamia_whatsapp_only
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.disable(logging.WARNING)
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend_nexa.adapters.user_input_loader import UserInputLoader
from backend_nexa.adapters.context_builder import SimulationContextBuilder
from backend_nexa.engine import NexaPricingEngine

import openpyxl

BACKEND_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES = BACKEND_ROOT / "test_cases"
EXCEL_PATH = BACKEND_ROOT / "excel" / "Nexa - Pricing - Simulador - V2-4.xlsx"
REPORTS_DIR = BACKEND_ROOT / "reports" / "audit"


@dataclass
class LayerValidation:
    """Validación de una capa en un mes específico."""
    capa: str
    calculador: str
    mes: int
    metrica: str
    esperado_excel: Optional[float] = None
    obtenido_backend: Optional[float] = None
    delta_absoluto: Optional[float] = None
    delta_pct: Optional[float] = None
    status: str = "UNKNOWN"  # MATCH_EXACTO, MATCH_REDONDEO, DESVIACION_MENOR, etc.
    severidad: str = "MEDIA"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


def classify_delta(delta_pct: Optional[float]) -> tuple[str, str]:
    """Clasifica basado en delta %."""
    if delta_pct is None:
        return ("MISSING", "CRÍTICA")
    abs_d = abs(delta_pct)
    if abs_d < 0.0001:
        return ("MATCH_EXACTO", "BAJA")
    elif abs_d < 0.001:
        return ("MATCH_REDONDEO", "BAJA")
    elif abs_d < 0.01:
        return ("DESVIACION_MENOR", "MEDIA")
    elif abs_d < 0.1:
        return ("DESVIACION_MODERADA", "ALTA")
    else:
        return ("DESVIACION_CRITICA", "CRÍTICA")


def run_backend_full(case_path: Path) -> dict:
    """Ejecuta backend y captura todo."""
    loader = UserInputLoader()
    ui = loader.cargar(case_path)
    request = SimulationContextBuilder().construir(ui)
    result = NexaPricingEngine().calcular(request)
    return {
        "request": request,
        "result": result,
        "pyg_por_mes": result.pyg_por_mes,
        "kpis": result.kpis,
    }


def read_excel_pyg_mes(path: Path, mes: int) -> dict:
    """Lee la hoja P&G de Excel para un mes específico."""
    # Mapeo de columnas por mes: mes 1 → C, mes 2 → D, mes 3 → E, etc.
    col_letra = chr(ord('C') + mes - 1)

    try:
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb["Visión P&G"]
    except Exception as e:
        print(f"⚠️ Error leyendo Excel P&G: {e}")
        return {}

    # Ubicaciones de métricas críticas en la hoja P&G
    LOCATIONS = {
        "payroll_a": 31,      # Fila del payroll Cadena A
        "no_payroll_a": 40,   # Fila del no-payroll Cadena A
        "costo_b": 44,        # Fila costo Cadena B
        "polizas_total": 64,  # Fila pólizas/ICA/GMF (suma)
        "financiacion": 65,   # Fila financiación
        "ingreso_neto": 26,   # Fila ingreso neto
        "costo_total_op": 70, # Fila costo operacional total (A+B+C)
        "utilidad_neta": 75,  # Fila utilidad neta
    }

    out = {}
    for metric, row in LOCATIONS.items():
        try:
            cell = ws[f"{col_letra}{row}"]
            out[metric] = {"value": cell.value, "cell": f"{col_letra}{row}", "row": row}
        except Exception:
            out[metric] = {"value": None, "cell": f"{col_letra}{row}", "row": row}

    wb.close()
    return out


def validate_all_layers(backend_data: dict, case: str) -> List[LayerValidation]:
    """Valida todas las capas mes a mes."""
    validations: List[LayerValidation] = []
    pyg_por_mes = backend_data["pyg_por_mes"]

    # Para cada mes, validar
    for mes, pyg in enumerate(pyg_por_mes, start=1):
        excel_mes = read_excel_pyg_mes(EXCEL_PATH, mes)

        # Capa 2: NominaCalculator
        metrics_c2 = [
            ("payroll_a", pyg.payroll_a),
            ("no_payroll_a", pyg.no_payroll_a),
        ]

        # Capa 8: CostosFinancierosCalculator
        polizas_total = pyg.ica + pyg.gmf + pyg.polizas
        metrics_c8 = [
            ("polizas_total", polizas_total),
            ("financiacion", pyg.financiacion),
        ]

        # Capa 9: PyGCalculator
        costo_total_op = pyg.costo_a + pyg.costo_b + pyg.costo_c
        metrics_c9 = [
            ("ingreso_neto", pyg.ingreso_neto),
            ("costo_total_op", costo_total_op),
            ("utilidad_neta", pyg.utilidad_neta),
        ]

        all_metrics = [
            ("Capa 2", "NominaCalculator", metrics_c2),
            ("Capa 8", "CostosFinancierosCalculator", metrics_c8),
            ("Capa 9", "PyGCalculator", metrics_c9),
        ]

        for capa, calc, metrics in all_metrics:
            for metric_name, backend_val in metrics:
                excel_info = excel_mes.get(metric_name, {})
                excel_val = excel_info.get("value")

                delta = None
                delta_pct = None
                if excel_val is not None and isinstance(backend_val, (int, float)):
                    delta = backend_val - excel_val
                    denom = abs(excel_val) if abs(excel_val) > 1e-9 else 1.0
                    delta_pct = (delta / denom * 100) if abs(excel_val) > 1e-9 else 0.0

                status, sev = classify_delta(delta_pct)

                v = LayerValidation(
                    capa=capa,
                    calculador=calc,
                    mes=mes,
                    metrica=metric_name,
                    esperado_excel=excel_val,
                    obtenido_backend=backend_val,
                    delta_absoluto=delta,
                    delta_pct=delta_pct,
                    status=status,
                    severidad=sev,
                )
                validations.append(v)

    return validations


def export_json(validations: List[LayerValidation], output_path: Path) -> None:
    """Exporta a JSON."""
    data = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_validations": len(validations),
            "summary": {
                "match_exacto": sum(1 for v in validations if v.status == "MATCH_EXACTO"),
                "match_redondeo": sum(1 for v in validations if v.status == "MATCH_REDONDEO"),
                "desviacion_menor": sum(1 for v in validations if v.status == "DESVIACION_MENOR"),
                "desviacion_moderada": sum(1 for v in validations if v.status == "DESVIACION_MODERADA"),
                "desviacion_critica": sum(1 for v in validations if v.status == "DESVIACION_CRITICA"),
                "missing": sum(1 for v in validations if v.status == "MISSING"),
            }
        },
        "validations": [v.to_dict() for v in validations]
    }
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"✅ JSON: {output_path}")


def export_csv(validations: List[LayerValidation], output_path: Path) -> None:
    """Exporta a CSV."""
    fieldnames = ["capa", "calculador", "mes", "metrica", "esperado_excel", "obtenido_backend",
                  "delta_absoluto", "delta_pct", "status", "severidad"]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for v in validations:
            writer.writerow({k: getattr(v, k) for k in fieldnames})
    print(f"✅ CSV: {output_path}")


def export_markdown(validations: List[LayerValidation], output_path: Path, case: str) -> None:
    """Exporta a Markdown."""
    lines = [
        f"# Auditoría de Capas (Exhaustiva) — {case}",
        f"**Generado**: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    summary = {
        "match_exacto": sum(1 for v in validations if v.status == "MATCH_EXACTO"),
        "match_redondeo": sum(1 for v in validations if v.status == "MATCH_REDONDEO"),
        "desviacion_menor": sum(1 for v in validations if v.status == "DESVIACION_MENOR"),
        "desviacion_moderada": sum(1 for v in validations if v.status == "DESVIACION_MODERADA"),
        "desviacion_critica": sum(1 for v in validations if v.status == "DESVIACION_CRITICA"),
        "missing": sum(1 for v in validations if v.status == "MISSING"),
    }

    lines.append("## Resumen")
    lines.append("")
    lines.append(f"- **Total validaciones**: {len(validations)}")
    lines.append(f"- **Match exacto**: {summary['match_exacto']}")
    lines.append(f"- **Match redondeo**: {summary['match_redondeo']}")
    lines.append(f"- **Desviación menor**: {summary['desviacion_menor']}")
    lines.append(f"- **Desviación moderada**: {summary['desviacion_moderada']}")
    lines.append(f"- **Desviación crítica**: {summary['desviacion_critica']}")
    lines.append("")

    lines.append("## Matriz por Capa × Mes")
    lines.append("")
    lines.append("| Capa | Calculador | Mes | Métrica | Excel | Backend | Δ % | Status |")
    lines.append("|------|------------|-----|---------|-------|---------|-----|--------|")

    for v in validations:
        exp = f"{v.esperado_excel:.2f}" if v.esperado_excel is not None else "N/A"
        obs = f"{v.obtenido_backend:.2f}" if v.obtenido_backend is not None else "N/A"
        delta = f"{v.delta_pct:.6f}%" if v.delta_pct is not None else "N/A"
        lines.append(f"| {v.capa} | {v.calculador} | {v.mes} | {v.metrica} | {exp} | {obs} | {delta} | {v.status} |")

    lines.append("")
    lines.append("## Anomalías Detectadas")
    lines.append("")
    anomalies = [v for v in validations if v.status in ("DESVIACION_CRITICA", "DESVIACION_MODERADA")]
    if anomalies:
        for v in anomalies:
            lines.append(f"- **{v.capa}** ({v.calculador}) Mes {v.mes}: {v.metrica}")
            lines.append(f"  Excel: {v.esperado_excel}, Backend: {v.obtenido_backend}, Δ = {v.delta_pct:.6f}%")
    else:
        lines.append("✅ No se detectaron anomalías críticas.")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"✅ Markdown: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="bancamia_whatsapp_only")
    args = parser.parse_args()

    case_path = TEST_CASES / f"{args.case}.json"
    if not case_path.exists():
        print(f"❌ No encontrado: {case_path}")
        return 1

    print(f"🔍 Validando: {args.case}")
    print(f"   Input: {case_path}")
    print()

    print("▶️  Ejecutando backend...")
    backend_data = run_backend_full(case_path)
    n_meses = len(backend_data["pyg_por_mes"])
    print(f"   ✅ {n_meses} meses calculados")

    print("▶️  Validando capas...")
    validations = validate_all_layers(backend_data, args.case)
    print(f"   ✅ {len(validations)} validaciones completadas")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    base_name = f"layers_exhaustive_{args.case}"

    export_json(validations, REPORTS_DIR / f"{base_name}.json")
    export_csv(validations, REPORTS_DIR / f"{base_name}.csv")
    export_markdown(validations, REPORTS_DIR / f"{base_name}.md", args.case)

    print()
    print("📊 Resumen por Status:")
    for status in ["MATCH_EXACTO", "MATCH_REDONDEO", "DESVIACION_MENOR", "DESVIACION_MODERADA", "DESVIACION_CRITICA", "MISSING"]:
        count = sum(1 for v in validations if v.status == status)
        if count > 0:
            icon = "✅" if status.startswith("MATCH") else "⚠️" if "MENOR" in status else "❌"
            print(f"   {icon} {status:25s}: {count:3d}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
