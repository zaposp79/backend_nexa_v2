# V2-8 Formula Parity Matrix

**MAX_DELTA_ALLOWED:** 0.000001 (absolute)  
**Deal:** SAC / METROCUADRADO COM SAS / Grupo Aval — 24m, start 2026-07-01  
**Provider:** V2-7 (canonical, commit 66e9ae8)  
**Generated:** 2026-06-11  

---

## Summary

| Verdict | Formulas Checked | MATCH | FORMULA_PARITY_FAIL | OUT_OF_SCOPE |
|---------|-----------------|-------|---------------------|--------------|
| **V28_FORMULA_PARITY_NOT_ACHIEVED** | 14 | 1 | 10 | 3 |

---

## Item Table

| ID | Sheet | Cell | Excel Value | Backend Value | Delta | Delta% | Status |
|----|-------|------|-------------|---------------|-------|--------|--------|
| BASE-INGRESO-A | Hoja Maestra Escenarios | C296 | 1,822,157,751.25 | N/A | N/A | N/A | OUT_OF_SCOPE_FOR_PARITY |
| BASE-INGRESO-B | Hoja Maestra Escenarios | C304 | 22,767,959.96 | N/A | N/A | N/A | OUT_OF_SCOPE_FOR_PARITY |
| BASE-INGRESO-C | Hoja Maestra Escenarios | C312 | 1,173,182,758.05 | N/A | N/A | N/A | OUT_OF_SCOPE_FOR_PARITY |
| PYG-INGRESO-A-M1 | Visión P&G | I19 | 1,639,941,976.12 | 2,040,973,807.04 | 401,031,830.92 | 24.5% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-B-M1 | Visión P&G | I20 | 20,491,163.97 | 17,326,600.71 | 3,164,563.25 | 15.4% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-C-M1 | Visión P&G | I21 | 1,055,864,482.24 | 981,238,725.00 | 74,625,757.24 | 7.1% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-TOTAL-M1 | Visión P&G | I18 | 2,716,297,622.33 | 3,039,539,132.76 | 323,241,510.43 | 11.9% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-A-M3 | Visión P&G | K19 | 1,822,157,751.25 | 1,463,698,411.73 | 358,459,339.51 | 19.7% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-B-M3 | Visión P&G | K20 | 22,767,959.96 | 19,251,778.57 | 3,516,181.39 | 15.4% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-C-M3 | Visión P&G | K21 | 1,173,182,758.05 | 1,090,265,250.00 | 82,917,508.05 | 7.1% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-A-M7 | Visión P&G | O19 | 1,923,246,125.24 | 1,544,900,432.99 | 378,345,692.24 | 19.7% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-B-M7 | Visión P&G | O20 | 24,274,288.19 | 20,319,815.07 | 3,954,473.12 | 16.3% | FORMULA_PARITY_FAIL |
| PYG-INGRESO-A-M19 | Visión P&G | AA19 | 1,928,573,482.55 | 1,549,179,774.86 | 379,393,707.69 | 19.7% | FORMULA_PARITY_FAIL |
| IPC-RATIO-M7-M3-A | Visión P&G | O19/K19 | 1.05547729 | 1.05547729 | 0.0000000000 | 0.0% | MATCH |

---

## Root Cause Analysis

### All FORMULA_PARITY_FAIL items share one root cause: BASE_INGRESO_MISMATCH

**Excel V2-8 approach:**
- Pre-computes a fixed margen base (`HME!C296 = 1,822,157,751.25`, `HME!C304 = 22,767,959.96`, `HME!C312 = 1,173,182,758.05`)
- P&G ingreso = `HME_base * rampup * (1 + IPC_rate_year)`
- The base is a static cached aggregate in the workbook

**Backend approach:**
- Computes ingreso dynamically from deal structure (canales, tarifas, volúmenes, margen objetivo, reglas)
- Ingreso is emergent from the full model pipeline (10 calculators)
- Fully traceable and auditable per deal

**Delta per cadena:**
| Cadena | Excel M3 Base | Backend M3 | Delta% |
|--------|--------------|------------|--------|
| A | 1,822,157,751.25 | 1,463,698,411.73 | -19.7% |
| B | 22,767,959.96 | 19,251,778.57 | -15.4% |
| C | 1,173,182,758.05 | 1,090,265,250.00 | -7.1% |

### IPC Mechanism: MATCH

The indexation mechanism is correct. The ratio `backend_M7 / backend_M3 = 1.05547729` exactly equals `1 + IPC_2027`, confirming:
- Annual rate lookup by calendar year works correctly
- Jan 2027 boundary transition is applied correctly
- V2-7 op.json IPC rates are loaded and used correctly

---

## Scope Decision: BASE_INGRESO_MISMATCH

Under strict `MAX_DELTA = 0.000001`, all P&G ingreso values are `FORMULA_PARITY_FAIL`.

The HME base values are marked `OUT_OF_SCOPE_FOR_PARITY` because:
1. They are Excel workbook internal aggregates (not deal inputs)
2. Backend does not expose a direct equivalent cell
3. The architectural decision (ACCEPTED_ARCHITECTURAL_DELTA) was previously accepted

To achieve full P&G numeric parity, the business would need to either:
- **Option A:** Feed `HME!C296/C304/C312` as frozen inputs to the backend (changes contract)
- **Option B:** Align the dynamic backend computation to match Excel's intermediate aggregation (changes formula logic — requires Excel forensics for HME!C295, C296 chain)

This is a product/business decision, not a technical bug.

---

## Related Closed Items

| ID | Status | Evidence |
|----|--------|----------|
| CAPEX-001 | COMPLETED | commit fde7657, SUM J62:J65 = 12,778,653.116 exact match |
| CADENA_C_NULL | RESOLVED | commit 69b77a9 |
| INPUT-001 | RESOLVED | commit 66e9ae8 |
| IPC mechanism ratio | MATCH | IPC-RATIO-M7-M3-A delta = 0.0000000000 |
