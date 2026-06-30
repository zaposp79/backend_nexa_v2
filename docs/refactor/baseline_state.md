# Baseline State After Canonicalization

Fecha: 2026-06-06. Branch: refactor/modular-pure.

## Files

- `tests/refactor/baseline_formula_snapshot_v0.json`: Estado post D-1 fix (Bancamia Cobranzas, Baseline 1).
  Equivalente a v1 en contenido. Renombrado conservado para continuidad histórica.
- `tests/refactor/baseline_formula_snapshot_v1.json`: Estado OFICIAL post-canonicalization.
  Copia directa de v0, representa el contrato de entrada en formato plano canónico.

## Relationship Between v0 and v1

v0 ya contenía costo_b > 0 (era el Baseline 1 post D-1 fix). La canonicalization
no cambió ningún valor de output (plano == anidado producen output idéntico).
Por tanto v0 y v1 son numéricamente idénticos.

- v0: referencia histórica, corresponde a Baseline 1 del D-1 fix.
- v1: baseline oficial para futuros refactors, vinculado explícitamente a la
  canonicalization como punto de partida limpio.

## Usage

- Tests de refactor: usar v1 como baseline oficial para futuros cambios.
- v0: mantener como referencia histórica. No eliminar.
- Ambos tienen los mismos valores numéricos.

## Validation KPIs (v1 = baseline oficial)

| KPI | Valor |
|-----|-------|
| `costo_b mes1` | 39,503,127.41 |
| `payroll_a mes1` | 154,103,322.32 |
| `costo_total_contrato` | 5,411,620,868.43 |
| `pct_utilidad_neta_total` | 0.2935 (29.35%) |

## Deal Context

- Cliente: Bancamia Cobranzas
- Duración: 24 meses
- Parametrización activa: v2-7 (HR/GN/OP/business_rules)
- Cadenas activas: A (FTE 170+), B (vol. 8000), C (inactiva)
- Formato entrada: canónico plano (A/B/C sin wrapper redundante)

## How to Use in Tests

```python
import json
from pathlib import Path

SNAPSHOT_V1 = Path(__file__).resolve().parents[2] / "tests/refactor/baseline_formula_snapshot_v1.json"

with open(SNAPSHOT_V1) as f:
    baseline = json.load(f)

kpis = baseline["kpis"]
pyg  = baseline["pyg_por_mes"]
```

## Status

v1 is the official baseline for FORMULA_REFACTOR_PHASE1_NOPAYROLL and all future refactors.
Do not update without executing the full test suite and documenting the change.
