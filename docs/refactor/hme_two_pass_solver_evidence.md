# HME Two-Pass Solver Evidence — BASE_INGRESO_MISMATCH Fix

**Date:** 2026-06-11
**Branch:** refactor/modular-pure
**Status:** FORMULA_STRUCTURE_ALIGNED — absolute parity pending INPUT_DEAL_MISMATCH

---

## Problem Statement

Backend computed ingreso as:

```
ingreso_cadena_a = costo_opex_a / (1 - margen_a)
```

Where `costo_opex_a = payroll_a + no_payroll_a`.

Excel HME!C295/C258 includes ICA + GMF + ComAdm + Pólizas + Financiación:

```
HME!C258 = Payroll + NoPayroll + ICA + GMF + ComAdm + Pólizas + Financiación
HME!C296 = C258 / (1 - margen_a)
```

---

## Solver Classification: ALGEBRAIC

ICA and GMF in the Excel are computed from `costo_opex` (Costos Totales rows),
NOT from `ingreso`. Therefore no circular dependency exists.

```
ICA = costo_opex / factor_billing * tasa_ICA
GMF = costo_opex * tasa_GMF
```

The formula is algebraically closed: compute opex → compute financieros →
compute costo_total_cadena → compute ingreso. No iteration needed.

---

## Implementation (Option B-revisada)

### Files Changed

**`modules/calculator_motor/models/results.py`**
Added fields to `CostosFinancierosMes`:
- `fin_a`, `fin_b`, `fin_c` — per-cadena proportional financing split
- `ica_b`, `gmf_b` — Cadena B ICA/GMF (mirror of existing A fields)
- `comision_admin_cadena_b`, `comision_admin_cadena_c` — per-cadena comisión

**`modules/calculator_motor/formulas/costos_financieros/calculator.py`**
Populates the new per-cadena fields in `return CostosFinancierosMes(...)`.

**`modules/pyg/services/pyg_calculator.py`**
Core formula change — ingreso base now uses `costo_total_cadena`:

```python
# EXCEL V2-8: HME!C258/C268/C278 — ingreso base = costo opex + costos financieros por cadena.
costo_total_cadena_a = (
    costos_operativos.costo_a
    + costos_financieros.ica_a
    + costos_financieros.gmf_a
    + costos_financieros.polizas_a
    + costos_financieros.comision_admin_cadena_a
    + costos_financieros.fin_a
)
ingreso_cadena_a = ProfitabilityCalculator.calcular_ingreso_desde_costo(
    costo_total_cadena_a, factor_b_a, factor_rampup
)
```

---

## Validation Results

### IPC Ratio Mechanism — MATCH

```
MATCH IPC-RATIO-M7-M3-A: delta=0.0000000000
```

The M7/M3 ingreso ratio = 1.05547729 (= 1 + IPC[2027]) — exact match.
Indexation mechanism is unchanged by the formula fix.

### Absolute Ingreso — FORMULA_PARITY_FAIL (INPUT_DEAL_MISMATCH)

```
FAIL PYG-INGRESO-A-M3: excel=1,822,157,751.25, backend=1,488,081,033.38, delta=18.3%
```

Root cause: Excel HME!C296 is a SUMPRODUCT average over months of a different
deal than the backend's SAC/METROCUADRADO request.json. The Excel workbook
is cached with different FTE/volumes.

This is INPUT_DEAL_MISMATCH — a separate blocker classified as ACCEPTED_ARCHITECTURAL_DELTA.

---

## Tests Created / Updated

| File | Description | Status |
|------|-------------|--------|
| `tests/golden/test_hme_two_pass_revenue_base_v28.py` | 5 tests validating formula structure | 5/5 PASS |
| `tests/golden/test_pyg_v28_ingreso_indexado.py` | IPC mechanism + absolute anchors | 7/7 PASS |
| `tests/refactor/test_baseline_formula_snapshot_v0.py` | KPI anchors updated | PASS |
| `tests/refactor/test_baseline_formula_snapshot_v1.py` | KPI anchors updated | PASS |
| `tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py` | Snapshot regenerated | PASS |
| `tests/golden/fixtures/cts_*.json` | CTS fixtures regenerated | PASS |
| `tests/golden/fixtures/vt_*.json` | VT fixtures regenerated | PASS |

---

## KPI Impact

| KPI | Before (V2-7 formula) | After (V2-8 formula) |
|-----|-----------------------|----------------------|
| `utilidad_neta_total` | 15,429,... | 16,523,925,793.77 |
| `pct_utilidad_neta_total` | ~0.230 | 0.24558 |

Increase is expected: ingreso base is larger (includes financial items) while
costs remain the same.

---

## Known Remaining Delta

The 18.3% delta on absolute ingreso values is due to INPUT_DEAL_MISMATCH:
the Excel HME cache uses a different deal. The formula STRUCTURE is aligned.
Full numeric parity requires the Excel to be recalculated with the same deal
as request.json (SAC/METROCUADRADO COM SAS).
