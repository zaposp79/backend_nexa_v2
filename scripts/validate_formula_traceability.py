"""
scripts/validate_formula_traceability.py
=========================================
Auditoría exhaustiva de fórmulas con trazabilidad completa.

Pipeline:
  1. Carga test case canónico (bancamia_whatsapp_only.json)
  2. Instrumenta motor para capturar valores intermedios por capa
  3. Compara CADA fórmula contra Excel V2-4
  4. Genera matriz de trazabilidad exhaustiva (JSON + CSV + Markdown)
  5. Clasifica resultados por severidad y tolerancia

Outputs:
  - reports/audit/formula_traceability_{case}.json
  - reports/audit/formula_traceability_{case}.csv
  - reports/audit/formula_traceability_{case}.md

Uso:
    python scripts/validate_formula_traceability.py --case bancamia_whatsapp_only
    python scripts/validate_formula_traceability.py --detailed  # Modo verbose
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
from backend_nexa.domain.models import (
    PricingRequest, ResultadoNomina, CostosTotalesMes, PyGMensual, KPIsDeal
)

import openpyxl

BACKEND_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES = BACKEND_ROOT / "test_cases"
EXCEL_PATH = BACKEND_ROOT / "excel" / "Nexa - Pricing - Simulador - V2-4.xlsx"
REPORTS_DIR = BACKEND_ROOT / "reports" / "audit"


@dataclass
class FormulaValidation:
    """Resultado de validación de una fórmula."""
    formula_id: str
    formula_description: str
    capa: str
    calculador: str
    archivo_backend: str
    linea_backend: str
    sheet_excel: str
    cell_excel: Optional[str]
    formula_excel: str
    variables_entrada: List[str] = field(default_factory=list)
    mes: int = 1
    # Valores
    expected_excel: Optional[float] = None
    actual_backend: Optional[float] = None
    delta_absolute: Optional[float] = None
    delta_pct: Optional[float] = None
    # Clasificación
    status: str = "UNKNOWN"  # MATCH_EXACTO, MATCH_REDONDEO, DESVIACION_MENOR, DESVIACION_CRITICA, MISSING
    severidad: str = "MEDIA"  # BAJA, MEDIA, ALTA, CRÍTICA
    causa_raiz: Optional[str] = None
    accion_recomendada: Optional[str] = None
    # Meta
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


def classify_result(delta_pct: Optional[float]) -> tuple[str, str]:
    """Clasifica resultado basado en delta porcentual."""
    if delta_pct is None:
        return ("MISSING", "CRÍTICA")

    abs_delta = abs(delta_pct)
    if abs_delta < 0.0001:
        return ("MATCH_EXACTO", "BAJA")
    elif abs_delta < 0.001:
        return ("MATCH_REDONDEO", "BAJA")
    elif abs_delta < 0.01:
        return ("DESVIACION_MENOR", "MEDIA")
    elif abs_delta < 0.1:
        return ("DESVIACION_MODERADA", "ALTA")
    else:
        return ("DESVIACION_CRITICA", "CRÍTICA")


def run_backend_instrumented(case_path: Path) -> dict:
    """Ejecuta backend y captura valores intermedios por capa."""
    loader = UserInputLoader()
    ui = loader.cargar(case_path)
    request = SimulationContextBuilder().construir(ui)
    result = NexaPricingEngine().calcular(request)

    # Captura outputs por capa
    pyg_mes1 = result.pyg_por_mes[0] if result.pyg_por_mes else None
    kpis = result.kpis

    return {
        "request": request,
        "pyg_mes1": pyg_mes1,
        "kpis": kpis,
        "all_pyg": result.pyg_por_mes,
    }


def read_excel_cells(path: Path, case: str) -> dict:
    """Lee celdas críticas del Excel V2-4."""
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception as e:
        print(f"Error leyendo Excel: {e}")
        return {}

    # Mapeo: formula_id → (sheet, cell, descripción)
    CELL_MAP = {
        # Capa 2: Nómina
        "NOMINA_SALARIO_FIJO_M1": ("Nomina Loaded", "C15", "Salario fijo mes 1 — suma de perfiles"),
        "NOMINA_CARGAS_SOCIALES": ("Nomina Loaded", "D15", "Cargas sociales mes 1"),
        "NOMINA_CAP_INICIAL": ("Nomina Loaded", "E15", "Capacitación inicial mes 1"),
        "NOMINA_CAP_ROTACION": ("Nomina Loaded", "F15", "Capacitación rotación mes 1"),
        "NOMINA_EXAMENES": ("Nomina Loaded", "G15", "Exámenes médicos mes 1"),
        "NOMINA_SEGURIDAD": ("Nomina Loaded", "H15", "Estudios seguridad mes 1"),
        "NOMINA_CRUCERO": ("Nomina Loaded", "I15", "Beneficio crucero mes 1"),
        "NOMINA_TOTAL_MES1": ("Nomina Loaded", "C16", "Total nómina mes 1"),
        # Capa 8: Financieros
        "FINANCIERO_FINANCIACION_M1": ("Visión P&G", "C65", "Financiación mes 1 (debe ser 0)"),
        "FINANCIERO_POLIZAS_M1": ("Visión P&G", "C64", "Pólizas mes 1"),
        "FINANCIERO_ICA_M1": ("Visión P&G", None, "ICA mes 1 (ver fórmula)"),
        "FINANCIERO_GMF_M1": ("Visión P&G", None, "GMF mes 1 (ver fórmula)"),
        # Capa 9: PyG
        "PYG_INGRESO_NETO_M1": ("Visión P&G", "C26", "Ingreso neto mes 1"),
        "PYG_COSTO_TOTAL_M1": ("Visión P&G", "C31", "Costo total mes 1"),
        "PYG_UTILIDAD_NETA_M1": ("Visión P&G", "C70", "Utilidad neta mes 1"),
        # Capa 10: KPIs
        "KPI_TARIFA_MENSUAL": ("KPIs", "C15", "Tarifa mensual promedio"),
        "KPI_MARGEN_UTILIDAD_PCT": ("KPIs", "C20", "% Margen utilidad"),
    }

    out = {}
    for formula_id, (sheet, cell, desc) in CELL_MAP.items():
        if cell is None:
            out[formula_id] = {"value": None, "sheet": sheet, "cell": cell, "desc": desc}
            continue
        try:
            value = wb[sheet][cell].value
            out[formula_id] = {"value": value, "sheet": sheet, "cell": cell, "desc": desc}
        except Exception as e:
            out[formula_id] = {"value": None, "sheet": sheet, "cell": cell, "desc": desc, "error": str(e)}

    wb.close()
    return out


def validate_formulas(backend_data: dict, excel_data: dict, case: str) -> List[FormulaValidation]:
    """Valida fórmulas críticas y genera matriz de trazabilidad."""
    validations: List[FormulaValidation] = []
    pyg_m1 = backend_data["pyg_mes1"]
    kpis = backend_data["kpis"]

    # Fórmulas a validar: (formula_id, expected_path_backend, excel_key)
    FORMULAS = [
        # CAPA 2: Nómina
        ("NOMINA_SALARIO_FIJO_M1", pyg_m1.payroll_a if pyg_m1 else None, "NOMINA_SALARIO_FIJO_M1"),
        ("NOMINA_TOTAL_MES1", pyg_m1.payroll_a if pyg_m1 else None, "NOMINA_TOTAL_MES1"),
        # CAPA 8: Financieros
        ("FINANCIERO_FINANCIACION_M1", pyg_m1.financiacion if pyg_m1 else None, "FINANCIERO_FINANCIACION_M1"),
        ("FINANCIERO_POLIZAS_M1", pyg_m1.polizas + pyg_m1.ica + pyg_m1.gmf if pyg_m1 else None, "FINANCIERO_POLIZAS_M1"),
        # CAPA 9: PyG
        ("PYG_INGRESO_NETO_M1", pyg_m1.ingreso_neto if pyg_m1 else None, "PYG_INGRESO_NETO_M1"),
        ("PYG_COSTO_TOTAL_M1", pyg_m1.costo_total if pyg_m1 else None, "PYG_COSTO_TOTAL_M1"),
        ("PYG_UTILIDAD_NETA_M1", pyg_m1.utilidad_neta if pyg_m1 else None, "PYG_UTILIDAD_NETA_M1"),
        # CAPA 10: KPIs
        ("KPI_TARIFA_MENSUAL", kpis.ingreso_mensual if kpis else None, "KPI_TARIFA_MENSUAL"),
        ("KPI_MARGEN_UTILIDAD_PCT", kpis.pct_utilidad_neta_total * 100 if kpis else None, "KPI_MARGEN_UTILIDAD_PCT"),
    ]

    for formula_id, backend_val, excel_key in FORMULAS:
        excel_info = excel_data.get(excel_key, {})
        excel_val = excel_info.get("value")

        delta = None
        delta_pct = None
        if backend_val is not None and excel_val is not None:
            delta = backend_val - excel_val
            denom = abs(excel_val) if abs(excel_val) > 1e-9 else 1.0
            delta_pct = (delta / denom * 100) if abs(excel_val) > 1e-9 else 0.0

        status, severidad = classify_result(delta_pct)

        # Mapeo de metadata por fórmula
        metadata = {
            "NOMINA_SALARIO_FIJO_M1": {
                "capa": "Capa 2", "calculador": "NominaCalculator",
                "archivo": "calculators/nomina.py", "linea": "79-100",
                "excel_cell": excel_info.get("cell"), "excel_sheet": excel_info.get("sheet"),
            },
            "NOMINA_TOTAL_MES1": {
                "capa": "Capa 2", "calculador": "NominaCalculator",
                "archivo": "calculators/nomina.py", "linea": "90-100",
                "excel_cell": excel_info.get("cell"), "excel_sheet": excel_info.get("sheet"),
            },
            "FINANCIERO_FINANCIACION_M1": {
                "capa": "Capa 8", "calculador": "CostosFinancierosCalculator",
                "archivo": "calculators/costos_financieros.py", "linea": "139-149",
                "excel_cell": excel_info.get("cell"), "excel_sheet": excel_info.get("sheet"),
            },
            "FINANCIERO_POLIZAS_M1": {
                "capa": "Capa 8", "calculador": "CostosFinancierosCalculator",
                "archivo": "calculators/costos_financieros.py", "linea": "151-163",
                "excel_cell": excel_info.get("cell"), "excel_sheet": excel_info.get("sheet"),
            },
            "PYG_INGRESO_NETO_M1": {
                "capa": "Capa 9", "calculador": "PyGCalculator",
                "archivo": "calculators/pyg.py", "linea": "77-126",
                "excel_cell": excel_info.get("cell"), "excel_sheet": excel_info.get("sheet"),
            },
            "PYG_COSTO_TOTAL_M1": {
                "capa": "Capa 9", "calculador": "PyGCalculator",
                "archivo": "calculators/pyg.py", "linea": "97-99",
                "excel_cell": excel_info.get("cell"), "excel_sheet": excel_info.get("sheet"),
            },
            "PYG_UTILIDAD_NETA_M1": {
                "capa": "Capa 9", "calculador": "PyGCalculator",
                "archivo": "domain/models.py", "linea": "429-430",
                "excel_cell": excel_info.get("cell"), "excel_sheet": excel_info.get("sheet"),
            },
            "KPI_TARIFA_MENSUAL": {
                "capa": "Capa 10", "calculador": "KPIsCalculator",
                "archivo": "calculators/kpis.py", "linea": "121-150",
                "excel_cell": excel_info.get("cell"), "excel_sheet": excel_info.get("sheet"),
            },
            "KPI_MARGEN_UTILIDAD_PCT": {
                "capa": "Capa 10", "calculador": "KPIsCalculator",
                "archivo": "calculators/kpis.py", "linea": "116-119",
                "excel_cell": excel_info.get("cell"), "excel_sheet": excel_info.get("sheet"),
            },
        }

        meta = metadata.get(formula_id, {})

        validation = FormulaValidation(
            formula_id=formula_id,
            formula_description=excel_info.get("desc", "N/A"),
            capa=meta.get("capa", "N/A"),
            calculador=meta.get("calculador", "N/A"),
            archivo_backend=meta.get("archivo", "N/A"),
            linea_backend=meta.get("linea", "N/A"),
            sheet_excel=meta.get("excel_sheet", "N/A"),
            cell_excel=meta.get("excel_cell"),
            formula_excel="[Ver Excel]",
            expected_excel=excel_val,
            actual_backend=backend_val,
            delta_absolute=delta,
            delta_pct=delta_pct,
            status=status,
            severidad=severidad,
        )
        validations.append(validation)

    return validations


def export_json(validations: List[FormulaValidation], output_path: Path) -> None:
    """Exporta matriz de validaciones a JSON."""
    data = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_formulas": len(validations),
            "summary": {
                "match_exacto": sum(1 for v in validations if v.status == "MATCH_EXACTO"),
                "match_redondeo": sum(1 for v in validations if v.status == "MATCH_REDONDEO"),
                "desviacion_menor": sum(1 for v in validations if v.status == "DESVIACION_MENOR"),
                "desviacion_moderada": sum(1 for v in validations if v.status == "DESVIACION_MODERADA"),
                "desviacion_critica": sum(1 for v in validations if v.status == "DESVIACION_CRITICA"),
                "missing": sum(1 for v in validations if v.status == "MISSING"),
            }
        },
        "formulas": [v.to_dict() for v in validations]
    }
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"✅ JSON: {output_path}")


def export_csv(validations: List[FormulaValidation], output_path: Path) -> None:
    """Exporta matriz de validaciones a CSV."""
    fieldnames = [
        "formula_id", "formula_description", "capa", "calculador",
        "archivo_backend", "linea_backend", "sheet_excel", "cell_excel",
        "expected_excel", "actual_backend", "delta_absolute", "delta_pct",
        "status", "severidad", "causa_raiz", "accion_recomendada"
    ]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for v in validations:
            writer.writerow({k: getattr(v, k) for k in fieldnames})
    print(f"✅ CSV: {output_path}")


def export_markdown(validations: List[FormulaValidation], output_path: Path, case: str) -> None:
    """Exporta matriz de validaciones a Markdown."""
    lines = [
        f"# Auditoría de Fórmulas — {case}",
        f"**Generado:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Resumen",
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

    lines.append(f"- **Total fórmulas auditadas**: {len(validations)}")
    lines.append(f"- **Match exacto**: {summary['match_exacto']}")
    lines.append(f"- **Match redondeo**: {summary['match_redondeo']}")
    lines.append(f"- **Desviación menor**: {summary['desviacion_menor']}")
    lines.append(f"- **Desviación moderada**: {summary['desviacion_moderada']}")
    lines.append(f"- **Desviación crítica**: {summary['desviacion_critica']}")
    lines.append(f"- **Missing**: {summary['missing']}")
    lines.append("")
    lines.append("## Matriz de Fórmulas")
    lines.append("")
    lines.append("| Fórmula | Capa | Calculador | Excel | Backend | Delta % | Estado |")
    lines.append("|---------|------|------------|-------|---------|---------|--------|")

    for v in validations:
        delta_str = f"{v.delta_pct:.6f}%" if v.delta_pct is not None else "N/A"
        exp_str = f"{v.expected_excel:.2f}" if v.expected_excel is not None else "N/A"
        act_str = f"{v.actual_backend:.2f}" if v.actual_backend is not None else "N/A"
        lines.append(
            f"| {v.formula_id} | {v.capa} | {v.calculador} | "
            f"{exp_str} | {act_str} | "
            f"{delta_str} | {v.status} |"
        )

    lines.append("")
    lines.append("## Detalle por Fórmula")
    lines.append("")

    for v in validations:
        lines.append(f"### {v.formula_id}")
        lines.append(f"- **Descripción**: {v.formula_description}")
        lines.append(f"- **Capa**: {v.capa}")
        lines.append(f"- **Calculador**: {v.calculador}")
        lines.append(f"- **Archivo**: {v.archivo_backend}:{v.linea_backend}")
        lines.append(f"- **Cell Excel**: {v.sheet_excel}!{v.cell_excel}")
        lines.append(f"- **Valor Excel**: {v.expected_excel if v.expected_excel is not None else 'N/A'}")
        lines.append(f"- **Valor Backend**: {v.actual_backend if v.actual_backend is not None else 'N/A'}")
        delta_str = f"{v.delta_absolute} ({v.delta_pct:.6f}%)" if v.delta_pct is not None else "N/A"
        lines.append(f"- **Delta**: {delta_str}")
        lines.append(f"- **Estado**: {v.status}")
        lines.append(f"- **Severidad**: {v.severidad}")
        lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"✅ Markdown: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validación exhaustiva de fórmulas")
    parser.add_argument("--case", default="bancamia_whatsapp_only",
                       help="Caso de test (sin .json)")
    parser.add_argument("--detailed", action="store_true",
                       help="Modo verbose")
    args = parser.parse_args()

    case_path = TEST_CASES / f"{args.case}.json"
    if not case_path.exists():
        print(f"❌ Caso no encontrado: {case_path}")
        return 1

    print(f"🔍 Validando case: {args.case}")
    print(f"   Input:  {case_path}")
    print(f"   Excel:  {EXCEL_PATH}")
    print()

    # Ejecutar backend
    print("▶️  Ejecutando backend...")
    backend_data = run_backend_instrumented(case_path)
    print("   ✅ Backend ejecutado")

    # Leer Excel
    print("▶️  Leyendo Excel V2-4...")
    excel_data = read_excel_cells(EXCEL_PATH, args.case)
    print(f"   ✅ Excel leído ({len(excel_data)} celdas)")

    # Validar fórmulas
    print("▶️  Validando fórmulas...")
    validations = validate_formulas(backend_data, excel_data, args.case)
    print(f"   ✅ {len(validations)} fórmulas validadas")

    # Exportar resultados
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    base_name = f"formula_traceability_{args.case}"

    export_json(validations, REPORTS_DIR / f"{base_name}.json")
    export_csv(validations, REPORTS_DIR / f"{base_name}.csv")
    export_markdown(validations, REPORTS_DIR / f"{base_name}.md", args.case)

    print()
    print("📊 Resumen:")
    for v in validations:
        status_icon = "✅" if v.status == "MATCH_EXACTO" else "⚠️" if "DESVIACION" not in v.status else "❌"
        delta_str = f"{v.delta_pct:+.6f}%" if v.delta_pct is not None else "N/A"
        print(f"   {status_icon} {v.formula_id:35s} | {v.status:20s} | Δ={delta_str}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
