# CTS Variable Split Attribution — V2-8 (CTS-001 residual)

**Date:** 2026-06-11
**Deal:** SAC / METROCUADRADO COM SAS / Grupo Aval — 24m
**Provider:** V2-7 (canonical)
**Anchor:** Vision Cost To Serve!C34 = 6,224.575126115379 COP/tx
**Verdict:** CTS_VARIABLE_SPLIT_BLOCKED_RESIDUAL_NOT_IN_VARIABLE_SPLIT

## Summary

The hypothesis was that the CTS-001 residual (-232.07 COP/tx, 3.73%) is caused by
the per-line variable commission attribution in `NominaCalculator._comisiones`
(backend variable line = raw × pct_cumplimiento 0.70 = 494.15 COP/tx; Excel
variable line = 775.74 COP/tx).

**This hypothesis is disproven by the backend split algebra.** Changing
`_comisiones` alone CANNOT move `cts_cadena_a` because the backend defines the
fixed line as a carve-out of the loaded total:

```
salario_fijo = total_cargado − comisiones        (nomina.py:174)
=> salario_fijo + comisiones = total_cargado      (INVARIANT)
```

Whatever is added to `comisiones` is subtracted from `salario_fijo`. The CTS
payroll subtotal (fijo + variable) is invariant to the split. The residual lives
in the **payroll subtotal** itself, not in the fijo/variable reallocation.

## Excel attribution model (confirmed)

| Line | Excel source | Cell | Value (SAC) | Carga? | Cumplimiento 0.70? |
|---|---|---|---|---|---|
| Salario Fijo (C37) | Nomina Loaded!115 ← `Inputs de Nomina` col **AM** | AM62 = W62 | 3,560,973.86 | YES (full loaded) | n/a |
| Salario Variable (C38) | Nomina Loaded!205 ← `Inputs de Nomina` col **D** | D62 | 600,000 (raw) | NO | NO |

Reconstructed from Excel (all 24 months, ÷ C11=24 ÷ W31=221,000):
- Salario Fijo = 4,629.486449 COP/tx
- Salario Variable = 775.743203 COP/tx
- **Payroll Nomina Loaded subtotal (C36) = 5,405.229652 COP/tx**

Key structural fact: **Excel adds the raw commission (D62) ON TOP of the full
loaded cost (AM=W62)**. W62's prestational carga is computed over the imponible
base F62 = base + full commission (2,350,905), so the commission's *carga* is
inside the fijo line, and the *raw* commission is added again as the variable
line. The two lines are additive, NOT a partition.

Variable line decomposition (Excel `Nomina Loaded`!205 = 171,439,247.83/mes-equiv):
- raw_month = Σ(base × com_pct × FTE) = 156,009,137.31
- 171,439,247.83 / 156,009,137.31 = **1.0989** → salary indexation aging (NOT carga, NOT 0.70)
- D62 = base × com_pct = 600,000 (no cumplimiento, no carga) confirmed by
  `Nomina Loaded`!C174 (Agente Básico 1) = 78,000,000 = 600,000 × 130 headcount.

## Backend model

| Line | Backend | COP/tx | Formula |
|---|---|---|---|
| salario_fijo | nomina.py:174 | 4,621.64 | (salario_cargado × FTE × idx) − comisiones |
| salario_variable | nomina.py:208 | 494.15 | base × FTE × com_pct × **0.70** × idx |
| **subtotal (fijo+var)** | = total_cargado | **5,115.79** | salario_cargado × FTE × idx |

Backend per-perfil `salario_cargado` = 3,561,022.48 ≈ Excel W62 = 3,560,973.86
(match within 0.0014%). The carga and rates match Excel exactly (see
`hr_param_factor_prestacional_v28.md`).

## Why the residual is NOT a variable-split bug

| Quantity | Backend | Excel | Delta |
|---|---|---|---|
| Payroll subtotal (fijo+var) | 5,115.79 | 5,405.23 | **−289.44** |
| salario_fijo (individual) | 4,621.64 | 4,629.49 | −7.85 |
| salario_variable (individual) | 494.15 | 775.74 | −281.60 |

The −289.44 subtotal gap = Excel adds the raw commission on top of the full
loaded cost; the backend folds the commission INTO the loaded total (partition).
The CTS-001 total residual (−232.07) is the subtotal gap (−289.44) partially
offset by the No-Payroll over-allocation (+85.50, tracked as CTS-NO-PAYROLL) and
examenes/crucero (−12.24 / −10.63).

## Experiment performed (and reverted)

Removed `× pct_cumplimiento_variable` from `_comisiones` (variable line = raw,
matching Excel D62 attribution). Result:

| | salario_fijo | salario_variable | cts_cadena_a |
|---|---|---|---|
| Before | 4,621.64 | 494.15 | 5,992.502271 |
| After  | 4,409.86 | 705.92 | **5,992.502271 (UNCHANGED)** |

- `cts_cadena_a` did NOT move (total-invariant, as predicted).
- The variable line improved (494.15 → 705.92, residual −69.82 = 1.0989 indexation).
- The fixed line REGRESSED (−7.85 → −219.62) because it is a carve-out.

Net: the change does not reduce CTS-001, worsens the fijo attribution, and is
purely cosmetic on the split. **Reverted.** No code change retained.

## Root cause (real) and why out of scope

To match Excel, the backend must restructure `_salario_fijo` so the fixed line =
full loaded total (NO carve-out) AND the variable line = raw commission ADDED on
top (the additive AM+D model). This:
1. Increases total Cadena A payroll by ~289 COP/tx (the added raw commission).
2. Cascades into PyG, Vision Tarifas, baseline snapshots and parity goldens.
3. Touches `_salario_fijo` (line 163-198) and the payroll subtotal — explicitly
   OUT OF SCOPE for CTS_VARIABLE_SPLIT_ATTRIBUTION ("modify only _comisiones").

Additionally, the residual −69.82 on the variable line (1.0989 indexation aging)
indicates the variable line's `factor_idx` aggregation differs from the loaded
line's aging — a separate indexation-aggregation concern, not a 0.70 issue.

**Classification:** FORMULA_IMPLEMENTATION_STRUCTURE — backend partitions the
loaded total (fijo = loaded − commission); Excel adds the raw commission on top
of the loaded total. Fix requires `_salario_fijo` + payroll-subtotal change +
full re-baseline + business approval. NOT achievable within `_comisiones` alone.

## No hardcoded values introduced. No code change retained.
