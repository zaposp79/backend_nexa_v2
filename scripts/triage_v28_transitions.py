"""
scripts/triage_v28_transitions.py
=================================
Triage de las transiciones de fórmula V2-7 -> V2-8 (Stage 2 prep, read-only).

Lee docs/refactor/excel_v27_v28_diff.json (logic_transitions por hoja) y
clasifica cada transición distinta para separar lógica de negocio real de
reorganización de layout, y rankear por impacto (celdas afectadas).

Heurística de clasificación (señal -> etiqueta):
  - NEW_FUNCTION       : V2-8 introduce funciones ausentes en V2-7
                         (IFERROR, INDEX, MATCH, IF, EDATE, SUMIFS, ...)
  - DROPPED_FUNCTION   : V2-8 elimina funciones que V2-7 tenía
  - CONSTANT_IN_FORMULA: cambió un literal numérico embebido en la fórmula
  - OPERATOR_SHIFT     : cambió la mezcla de operadores (+,-,*,/) sin cambiar funciones
  - LIKELY_LAYOUT_REORG: skeletons sin relación estructural (bloque reubicado:
                         p.ej. SUMIFS(...) -> @*@); requiere validación numérica
  - TRIVIAL_REWRITE    : mismo set de funciones y operadores; reescritura menor

Salida:
  - docs/refactor/excel_v28_triage.md
  - docs/refactor/excel_v28_triage.json

Uso:
    PYTHONPATH=$(pwd) python scripts/triage_v28_transitions.py
"""
from __future__ import annotations

import json
import re
from collections import Counter

from scripts.excel_map_common import BACKEND_ROOT

DIFF_JSON = BACKEND_ROOT / "docs" / "refactor" / "excel_v27_v28_diff.json"
OUT_MD = BACKEND_ROOT / "docs" / "refactor" / "excel_v28_triage.md"
OUT_JSON = BACKEND_ROOT / "docs" / "refactor" / "excel_v28_triage.json"

_FUNC_RE = re.compile(r"([A-Z][A-Z0-9.]+)\(")
_NUM_RE = re.compile(r"(?<![A-Za-z0-9_.\[])\d+(?:\.\d+)?(?![A-Za-z0-9_.])")
_OP_RE = re.compile(r"[+\-*/]")

# Hint de hoja -> módulo backend probable (poblado por inspección de la
# arquitectura; se afina al mapear cada transición real en Stage 2).
SHEET_BACKEND_HINT: dict[str, str] = {
    "Visión P&G": "modules/pyg/ (builders/vision_pyg_builder.py) + motor pyg/services",
    "Vision Tarifas_Modelo_Cobro": "modules/vision_tarifas/reglas.py + dto",
    "Vision Cost To Serve": "modules/vision_cost_to_serve/services/cost_to_serve_calculator.py",
    "Visión Imprimible": "modules/vision_imprimible/builders/",
    "Costos Totales": "modules/pyg/services/costos_totales_calculator.py",
    "Costo Cadena C": "modules/cadena_c/reglas.py + calculator_motor formulas",
    "Costo Fijo": "modules/calculator_motor/formulas/no_payroll/",
    "Costo Variable": "modules/cadena_b/reglas.py",
    "Pólizas - Costo Financiacion": "modules/calculator_motor/formulas/costos_financieros/",
    "Nomina Loaded": "modules/calculator_motor/formulas/payroll/ + cadena_a",
    "Inputs de Nomina": "modules/cadena_a/ (staffing/payroll) + parametrización",
    "Condiciones Cadena A": "modules/cadena_a/",
    "Condiciones Cadena B": "modules/cadena_b/",
    "Condiciones Cadena C": "modules/cadena_c/",
    "Riesgo": "modules/calculator_motor/formulas/risk/ + config/business_rules/riesgo.yaml",
    "Hoja Maestra Escenarios": "modules/panel/ escenarios_comerciales + config operaciones.yaml",
    "Tasas, TRM, Polizas": "parametrización + costos_financieros",
    "Listas Desplegables": "parametrización / catálogos",
    "Graficos": "modules/<vision>/ (datos de gráfico embebidos en domain models)",
}


def _funcs(skeleton: str) -> set[str]:
    return set(_FUNC_RE.findall(skeleton))


def _nums(skeleton: str) -> list[str]:
    return _NUM_RE.findall(skeleton)


def _classify(s7: str, s8: str) -> str:
    f7, f8 = _funcs(s7), _funcs(s8)
    added = f8 - f7
    dropped = f7 - f8
    if added:
        return "NEW_FUNCTION"
    if dropped:
        return "DROPPED_FUNCTION"
    if _nums(s7) != _nums(s8):
        return "CONSTANT_IN_FORMULA"
    # Mismo set de funciones; ¿estructura totalmente distinta?
    if f7 == f8 and f7:
        return "TRIVIAL_REWRITE"
    # Sin funciones en ambos lados: pura aritmética
    ops7 = Counter(_OP_RE.findall(s7))
    ops8 = Counter(_OP_RE.findall(s8))
    if ops7 != ops8:
        # Estructura aritmética muy distinta sugiere reubicación de bloque
        return "LIKELY_LAYOUT_REORG"
    return "TRIVIAL_REWRITE"


def main() -> int:
    diff = json.loads(DIFF_JSON.read_text())
    out_sheets: dict[str, list[dict]] = {}
    grand = Counter()
    for name in diff["sheets_both"]:
        ps = diff["per_sheet"][name]
        trans = ps.get("logic_transitions", [])
        if not trans:
            continue
        triaged = []
        for t in trans:
            label = _classify(t["skeleton_v27"], t["skeleton_v28"])
            grand[label] += 1
            triaged.append({
                "label": label,
                "count": t["count"],
                "example_coord": t["example_coord"],
                "funcs_added": sorted(_funcs(t["skeleton_v28"]) - _funcs(t["skeleton_v27"])),
                "funcs_dropped": sorted(_funcs(t["skeleton_v27"]) - _funcs(t["skeleton_v28"])),
                "v27": t["example_v27"],
                "v28": t["example_v28"],
            })
        triaged.sort(key=lambda x: x["count"], reverse=True)
        out_sheets[name] = triaged

    result = {"by_label": dict(grand), "per_sheet": out_sheets}
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    OUT_MD.write_text(_render(diff, out_sheets, grand))

    print("Triage por etiqueta:", dict(grand))
    print(f"→ {OUT_MD.relative_to(BACKEND_ROOT)}")
    print(f"→ {OUT_JSON.relative_to(BACKEND_ROOT)}")
    return 0


def _render(diff: dict, out_sheets: dict, grand: Counter) -> str:
    lines = [
        "# Triage de transiciones de fórmula V2-8 (Stage 2 prep)",
        "",
        "Clasificación heurística de las transiciones distintas para separar",
        "lógica de negocio real de reubicación de layout, ordenadas por celdas",
        "afectadas. La columna *Backend probable* es un hint a afinar al mapear.",
        "",
        "## Distribución por etiqueta",
        "",
        "| Etiqueta | Transiciones | Lectura |",
        "|----------|-------------:|---------|",
        f"| NEW_FUNCTION | {grand.get('NEW_FUNCTION', 0)} | V2-8 agrega lógica (guard/lookup/indexación) — **revisar** |",
        f"| DROPPED_FUNCTION | {grand.get('DROPPED_FUNCTION', 0)} | V2-8 quita lógica — **revisar** |",
        f"| CONSTANT_IN_FORMULA | {grand.get('CONSTANT_IN_FORMULA', 0)} | cambió literal embebido — **revisar (posible parámetro)** |",
        f"| LIKELY_LAYOUT_REORG | {grand.get('LIKELY_LAYOUT_REORG', 0)} | bloque reubicado — validar numéricamente, no por fórmula |",
        f"| TRIVIAL_REWRITE | {grand.get('TRIVIAL_REWRITE', 0)} | mismas funciones/operadores — bajo riesgo |",
        "",
        "## Por hoja (top transiciones)",
        "",
    ]
    for name, triaged in out_sheets.items():
        stype = diff["per_sheet"][name]["sheet_type"]
        hint = SHEET_BACKEND_HINT.get(name, "—")
        lines.append(f"### {name} ({stype})")
        lines.append(f"_Backend probable:_ {hint}")
        lines.append("")
        lines.append("| Etiqueta | Celdas | Ejemplo | Funcs +/− |")
        lines.append("|----------|-------:|---------|-----------|")
        for t in triaged[:12]:
            fa = "+" + ",".join(t["funcs_added"]) if t["funcs_added"] else ""
            fd = "−" + ",".join(t["funcs_dropped"]) if t["funcs_dropped"] else ""
            lines.append(
                f"| {t['label']} | {t['count']} | `{t['example_coord']}` | {fa} {fd} |"
            )
        if len(triaged) > 12:
            lines.append(f"| … | | _{len(triaged) - 12} transiciones más_ | |")
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys
    sys.exit(main())
