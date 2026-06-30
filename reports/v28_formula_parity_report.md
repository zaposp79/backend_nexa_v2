# V2-8 Formula Parity Report

**Run:** 2026-06-11T19:06:24.719606+00:00
**MAX_DELTA_ALLOWED:** 1e-06
**Verdict:** `V28_FORMULA_PARITY_NOT_ACHIEVED`

- Formulas checked: 14
- Matches: 1
- Failures (FORMULA_PARITY_FAIL): 10
- Out of scope: 3

## Items

| ID | Sheet | Cell | Excel Value | Backend Value | Delta | Delta% | Status |
|----|-------|------|-------------|---------------|-------|--------|--------|
| BASE-INGRESO-A | Hoja Maestra Escenarios | C296 | 1,822,157,751.2461 | N/A | N/A | N/A | OUT_OF_SCOPE_FOR_PARITY |
| BASE-INGRESO-B | Hoja Maestra Escenarios | C304 | 22,767,959.9619 | N/A | N/A | N/A | OUT_OF_SCOPE_FOR_PARITY |
| BASE-INGRESO-C | Hoja Maestra Escenarios | C312 | 1,173,182,758.0472 | N/A | N/A | N/A | OUT_OF_SCOPE_FOR_PARITY |
| PYG-INGRESO-A-M1 | Visión P&G | I19 | 1,639,941,976.1215 | 2,238,923,935.1008 | 598,981,958.9793 | 36.52% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-B-M1 | Visión P&G | I20 | 20,491,163.9657 | 73,409,814.3967 | 52,918,650.4310 | 258.25% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-C-M1 | Visión P&G | I21 | 1,055,864,482.2424 | 997,429,163.9625 | 58,435,318.2799 | 5.53% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-TOTAL-M1 | Visión P&G | I18 | 2,716,297,622.3296 | 3,309,762,913.4600 | 593,465,291.1303 | 21.85% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-A-M3 | Visión P&G | K19 | 1,822,157,751.2461 | 1,670,248,945.9854 | 151,908,805.2607 | 8.34% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-B-M3 | Visión P&G | K20 | 22,767,959.9619 | 81,566,460.4408 | 58,798,500.4789 | 258.25% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-C-M3 | Visión P&G | K21 | 1,173,182,758.0472 | 1,108,254,626.6250 | 64,928,131.4222 | 5.53% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-A-M7 | Visión P&G | O19 | 1,923,246,125.2377 | 1,762,909,831.1340 | 160,336,294.1037 | 8.34% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-B-M7 | Visión P&G | O20 | 24,274,288.1930 | 86,962,897.4636 | 62,688,609.2706 | 258.25% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-A-M19 | Visión P&G | AA19 | 1,928,573,482.5470 | 1,767,793,054.4649 | 160,780,428.0821 | 8.34% | FORMULA_PARITY_FAIL |
| IPC-RATIO-M7-M3-A | Visión P&G | O19/K19 | 1.0555 | 1.0555 | 0.0000 | 0.00% | MATCH |

## Analysis: BASE_INGRESO_MISMATCH

All FORMULA_PARITY_FAIL items stem from BASE_INGRESO_MISMATCH:

- **Excel V2-8:** Uses HME!C296/C304/C312 (fixed pre-computed bases: A=1,822,157,751.25, B=22,767,959.96, C=1,173,182,758.05)
- **Backend:** Computes ingreso dynamically from deal structure (canales, tarifas, volúmenes, reglas)
- **Root cause:** Architectural divergence — not a bug in either system

Under MAX_DELTA=0.000001, these items are classified as FORMULA_PARITY_FAIL.
Under the prior policy (ACCEPTED_ARCHITECTURAL_DELTA), they were accepted.

## IPC Mechanism Verification

The indexation MECHANISM (ratio verification) is MATCH:
- Backend M7/M3 ratio (Cadena A) = 1.05547729 (exact match vs 1 + IPC_2027)
- IPC rates stored correctly in storage/parametrization/v2-7/op.json
- Annual boundary transitions (Jan 2027, Jan 2028) applied correctly

## Verdict Breakdown

| Component | Status | Notes |
|-----------|--------|-------|
| BASE_INGRESO_MISMATCH | FORMULA_PARITY_FAIL | Excel fixed base vs backend dynamic — architectural delta |
| IPC mechanism ratio | MATCH (mechanism) | Exact ratio 1.05547729 verified |
| CAPEX Cadena C | MATCH (CAPEX-001 closed) | SUM J62:J65 = 12,778,653.116, committed fde7657 |
| CADENA_C_NULL | RESOLVED | commit 69b77a9 |