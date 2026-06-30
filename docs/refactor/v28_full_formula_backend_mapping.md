# V2-8 Full Formula Backend Mapping

> Generated: 2026-06-11 | MAX_DELTA = 0.000001

## Comparable Checkpoints

| ID | Sheet | Cell | Formula Excel | Value Excel | Value Backend | Delta | Status | Backend File | Note |
|----|-------|------|---------------|-------------|---------------|-------|--------|--------------|------|
| IPC_RATIO | Tasas, TRM, Polizas | L8/M8 | IPC ratio | 0.05548/0.05840 | 0.05548/0.05840 | 0.0 | MATCH | calculator_motor/formulas/ | IPC indexation mechanism exact match |
| VCT_C34 | Vision Cost To Serve | C34 | =C35+C45 | 6,224.58 | 4,549,186.15 | ~4.5M | FORMULA_PARITY_FAIL | modules/vision_cost_to_serve/ | Unit mismatch: Excel = COP/FTE/month, backend = total COP for all FTE |
| VCT_K34 | Vision Cost To Serve | K34 | =SUM(K35,K36,K40) | 5,278.33 | 5,329.61 | 51.28 | FORMULA_PARITY_FAIL | modules/vision_cost_to_serve/ | CTS Cadena C per-transaction delta ~1% |
| VCT_G49 | Vision Cost To Serve | G49 | =(C34*C31)+(G34*G31)+(K34*K31) | 4,660.08 | 7,936.40 | 3,276.33 | FORMULA_PARITY_FAIL | modules/vision_cost_to_serve/ | Weighted CTS delta driven by C34 unit mismatch |
| VTM_H19 | Vision Tarifas_Modelo_Cobro | H19 | =SUM(C19:G19) | 3,018,108,469.26 | 64,529,525,326.10 | ~61B | FORMULA_PARITY_FAIL | modules/vision_tarifas/ | Scale mismatch: Excel = single monthly base, backend = cumulative 24 months |
| VPG_I15 | Visión P&G | I15 | =INDEX(Rot_Ausent...,MATCH) | 0.9 | 0.9 | 0.0 | MATCH (after fix) | calculator_motor/engine.py | Rampup month 1 = 0.9 correct |

## Architecture Delta Analysis

### CTS Cadena A (VCT_C34)

**Root cause**: Scale difference, not formula error.

- **Excel**: `C34 = C35 + C45` where C37 (Salario Fijo) = **4,629.49 COP/FTE/month** and the entire CTS breakdown is in thousands of COP per-FTE.
- **Backend**: `cts_cadena_a = 4,549,186.15` = total COP for all 260 FTE per month (not normalized by FTE count yet in the exported field).

**Normalization check**: `4,549,186.15 / 260 FTE = 17,497 COP/FTE` — this still differs from Excel's 6,224.58, indicating a real calculation gap beyond units, likely related to:
- Backend includes rampup in monthly computation
- Different treatment of capacitation costs
- Volume/period normalization differs

**Status**: FORMULA_PARITY_FAIL — requires investigation of CTS Cadena A formula chain.

### CTS Cadena C (VCT_K34)

**Root cause**: Small delta (~1%).

- Excel K34 = 5,278.33 COP/transaction
- Backend `cts_cadena_c` = 5,329.61 COP/transaction
- Delta = 51.28 (0.97%)

This is likely a rounding or normalization difference in the Cadena C cost chain.

**Status**: FORMULA_PARITY_FAIL — minor but exceeds MAX_DELTA = 0.000001.

### Vision Tarifas Total Revenue (VTM_H19)

**Root cause**: Backend `ingreso_mensual` is cumulative over contract period, not the monthly base.

- Excel H19 = `3,018,108,469.26` = single monthly base revenue (all escenarios combined, no rampup, no IPC)
- Backend `ingreso_mensual` = `64,529,525,326.10` = sum over 24 months × rampup × IPC indexation

The correct backend equivalent is `kpis.facturacion_mensual_proyectada` or the first full month's total.

**Status**: FORMULA_PARITY_FAIL — backend field mapping incorrect. Need to use month-9+ average or HME base.

## Missing Backend Mappings

None. All scope formulas have either:
- A backend field mapped (with delta)
- A documented architectural reason for incompatibility

## Verdict by Category

| Category | Status | Action |
|----------|--------|--------|
| IPC ratio mechanism | MATCH | None needed |
| HME monthly bases (C258/C268/C278) | BLOCKED_BY_ARCHITECTURE_DELTA | Document accepted delta |
| P&G monthly series | BLOCKED_BY_ARCHITECTURE_DELTA | Document accepted delta |
| CTS Cadena A | FORMULA_PARITY_FAIL | Investigate unit normalization |
| CTS Cadena C | FORMULA_PARITY_FAIL | Investigate ~1% gap |
| CTS Ponderado | FORMULA_PARITY_FAIL | Driven by C34 unit mismatch |
| Tarifas total revenue | FORMULA_PARITY_FAIL | Fix backend field mapping |
| Rampup values | MATCH (after correction) | None needed |

