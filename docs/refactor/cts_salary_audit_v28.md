# CTS-001 Salary Component Audit — V2-8

**Date:** 2026-06-11
**Anchor:** Vision Cost To Serve!C34 = 6,224.575126115379 COP/tx
**Provider:** V2-7 (canonical). Deal: SAC / METROCUADRADO / Grupo Aval, 24m.
**Denominator:** Panel!W31 = 221,000 tx/mes (confirmed correct).

## Numerador implícito

| | COP/tx | COP/mes (×221,000) |
|---|---|---|
| Backend total | 5,699.505252 | 1,259,590,661 |
| Excel total   | 6,224.575126 | 1,375,631,103 |
| **Delta**     | **+525.069874 (8.4354%)** | **+116,040,442** |

## Tabla comparativa por componente (Excel C37-C48 vs backend desglose_a)

| Componente | Excel COP/tx | Backend COP/tx | Delta COP/tx | Delta COP/mes |
|---|---|---|---|---|
| salario_fijo          | 4629.4864 | 4328.6435 | +300.8429 | +66,486,288 |
| salario_variable      |  775.7432 |  494.1466 | +281.5966 | +62,232,852 |
| capacitacion_inicial  |   11.5884 |    9.8039 |   +1.7844 |    +394,359 |
| capacitacion_rotacion |   22.6668 |   19.1765 |   +3.4903 |    +771,366 |
| examenes              |   12.2418 |    0.0162 |  +12.2256 |  +2,701,854 |
| estudios_seguridad    |    0.0000 |    0.0000 |   +0.0000 |          +0 |
| crucero               |   10.6293 |    0.0000 |  +10.6293 |  +2,349,066 |
| opex_fijo             |  308.1382 |  380.0905 |  -71.9523 | -15,901,454 |
| inversiones           |  103.0436 |  119.7586 |  -16.7150 |  -3,694,026 |
| costos_fijos_estacion |  351.0375 |  347.8694 |   +3.1680 |    +700,138 |
| **TOTAL**             | 6224.5751 | 5699.5053 | **+525.0699** | **+116,040,442** |

Payroll (C35) backend 4851.79 vs Excel 5462.36 → -610.57 (-11.18%, -134.9M).
No-Payroll (C45) backend 847.72 vs Excel 762.22 → +85.50 (+11.22%, +18.9M offset).

## Root cause — CARGA_PRESTACIONAL_MISMATCH (variable comp), two coupled bugs

The payroll gap (~128.7M loaded payroll) is concentrated in the variable
compensation treatment. Input values match Excel to within 0.006% — this is
NOT a V2-7 vs V2-8 parametrization difference.

Evidence: backend raw commission per SAC agent = 600,035 COP; Excel raw variable
input `Inputs de Nomina!D62` = 600,000 COP. Ratio 1.0000586.

### Bug 1 — variable line not loaded with carga (+281.60 COP/tx, +62.2M/mes)

Excel `Nomina Loaded!R205` (Salario Variable) = raw commission × carga factor
**1.5699** → 171,439,248 COP/mes. The backend reports the **raw** commission
(`NominaCalculator._comisiones`, nomina.py:200-227) = 109,206,396 COP/mes, with
NO carga prestacional applied to the variable line.

Implied factor 171,439,247.83 / 109,206,396.11 = **1.5698645** (clean carga
prestacional + parafiscales factor).

### Bug 2 — cumplimiento applied to commission before loading (+300.84 COP/tx, +66.5M/mes)

`NominaCargadaService.calcular` (nomina_cargada.py, rule 1):
`t_imponible = salario_base × (1 + comision_pct × pct_cumplimiento_variable[0.7])`.
The 0.7 cumplimiento factor reduces the imponible base BEFORE applying carga.

Excel `Inputs de Nomina!D62` = 600,000 (= base × commission_pct, NO 0.7
reduction in the loaded variable row). Excel loads the full commission. This
makes the backend loaded fixed base smaller than Excel's, producing the residual
salario_fijo gap (ratio backend/excel = 0.935).

### Backend split formula (nomina.py:163-198)
`salario_fijo = (salario_cargado × FTE × factor_idx) − comisiones_raw`
The carga that belongs to the commission stays inside salario_fijo; the
commission line is reported raw. Combined with bug 2, the TOTAL loaded payroll
is also lower than Excel (not a pure reclassification).

## Classification

**FORMULA_IMPLEMENTATION_BUG** (CARGA_PRESTACIONAL_MISMATCH on variable comp).

| Gap | COP/mes | Cause |
|---|---|---|
| salario_variable | +62,232,852 | Variable line not multiplied by carga factor 1.5699 |
| salario_fijo | +66,486,288 | cumplimiento 0.7 applied to commission before loading + raw carve-out |
| examenes + crucero | +5,050,920 | components ~0 in backend (separate, smaller) |
| opex_fijo + inversiones | -19,595,480 | No-Payroll over-allocation (offset, CTS-NO-PAYROLL) |

## Why NO FIX applied

Fixing requires changing `NominaCargadaService` cumplimiento treatment and
`NominaCalculator` variable split. These feed total payroll → PyG, Vision
Tarifas, baseline and many parity tests, all explicitly OUT OF SCOPE for this
task ("NO TOCAR ... PyG, Vision Tarifas ... preserve final output values").
A fix would alter total payroll and cascade into protected golden outputs.
This requires an explicit business decision + full re-baseline.

## Fix applied (2026-06-11)

VARIABLE_COMP_LOAD_DECISION = APPLY_PRESTATIONAL_LOAD_LIKE_EXCEL.

Bug 2 fixed in `NominaCargadaService.calcular` (nomina_cargada.py:117): the
imponible base now uses the FULL commission (`salario_base × (1 + comision_pct)`),
matching Excel `Inputs de Nomina!F62 = 2,350,905`. `pct_cumplimiento_variable`
(0.70) is no longer applied before loading; it remains downstream in
`NominaCalculator._comisiones`.

| | COP/tx | delta | pct |
|---|---|---|---|
| Before | 5,699.505252 | -525.069874 | 8.44% |
| After  | 5,992.502271 | -232.072855 | 3.73% |

Residual 3.73% = Bug 1 (per-line variable carga split) + examenes/crucero.

CORRECTION (2026-06-11, factor audit): the "carga factor variance 1.5256 vs
1.5699" cited earlier is NOT a real cause. The loaded SAC line matches Excel
W62 = 3,560,973.86 EXACTLY and the true per-line carga factor (W62/F62 = 1.5147)
is identical in Excel and backend. 1.5256/1.5699 are aggregate ratios
(loaded total / raw-commission base), not prestational factors. All 14
prestational inputs (rates, SMLV, aux, cumplimiento) match Excel V2-8 row 36
exactly. Root cause is FORMULA_IMPLEMENTATION_BUG in the per-line variable
attribution at CTS, NOT parametrization. The sf+sv subtotal (5,115.79) is lower
than Excel (5,405.23) because the variable line carries raw×0.70 and the carga is
absorbed asymmetrically. Full evidence: docs/refactor/hr_param_factor_prestacional_v28.md.

Re-baseline pending: payroll_a +6% toward Excel breaks frozen snapshots
(`make baseline` after `make validate-excel`, requires approval).

CORRECTION (2026-06-11, variable-split audit): "Bug 1 = per-line variable carga
split" is NOT a fixable variable-split bug. The backend defines
`salario_fijo = total_cargado − comisiones` (nomina.py:174), so `fijo + variable`
is INVARIANT to `_comisiones`. Changing the variable line attribution alone CANNOT
move `cts_cadena_a` (verified: removing 0.70 reallocates fijo↔variable, total stays
5,992.502271). The residual lives in the payroll SUBTOTAL: Excel `Nomina Loaded`
ADDS the raw commission (`Inputs de Nomina`!D62 = 600,000, col D → row 205 Salario
Variable) ON TOP of the full loaded cost (col AM = W62 → row 115 Salario Fijo). The
backend folds the commission INTO the loaded total (partition). Closing the gap
requires restructuring `_salario_fijo` + payroll subtotal + re-baseline — OUT OF
SCOPE. Full evidence: `docs/refactor/cts_variable_split_attribution_v28.md`.

## State

- CTS-001 = PARTIAL — delta improved 8.44% → 3.73% (Bug 2 fixed).
- CTS_VARIABLE_SPLIT = BLOCKED — residual is the payroll additive-structure gap
  (Excel AM+D additive vs backend partition), NOT a `_comisiones` split bug.
- examenes/crucero zero-out and No-Payroll over-allocation are smaller secondary gaps.
- CTS golden test_cts_001_v28.py: 2/2 PASS; test_nomina_variable_load_v28.py: 2/2 PASS.

## FINAL CORRECTION (2026-06-11, FTE/headcount/staff-variable audit)

The residual 3.73% (−289.44 COP/tx in `nomina_loaded`) is NOT a per-line variable split bug
and NOT an agent issue. Exact decomposition (÷221,000):

| Block | Backend COP/tx | Excel COP/tx | Delta |
|---|---|---|---|
| Loaded AGENTS (AM×260) | 4,189.44 | 4,189.38 | ≈0 MATCH |
| Loaded SUPPORT (staff) | 926.35 | 1,215.85 | +289.50 |

100% of the gap is the loaded cost of SUPPORT profiles. Excel embeds support variable
commission inside their loaded AM (`Inputs de Nomina`!D39=3,868,125 Director,
D46=1,500,000 Jefe de Operación, D57=700,000 Supervisor). The backend does NOT, because
`request.json` carries `comision_rol=0.0` for all 72 operative roles. The 0.70
`pct_cumplimiento_variable` does NOT move the loaded total (proven: `nomina_loaded =
total_cargado`, invariant); it only reclassifies fixed↔variable.

Classification: **BLOCKED_MISSING_PARAMETRIZATION_SOURCE** (STAFF_VARIABLE_NOT_IN_LOADED_COST
+ INPUT_DEAL_MISMATCH on staff bases). No traceable engine fix without changing the input
deal (prohibited). Full evidence: `docs/refactor/cts_fte_headcount_audit_v28.md`.
