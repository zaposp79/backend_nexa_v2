# HR Prestational Factor Audit — V2-8 (CTS-001 residual)

**Date:** 2026-06-11
**Deal:** SAC / METROCUADRADO COM SAS / Grupo Aval — 24m
**Provider:** V2-7 (canonical)
**Anchor:** Vision Cost To Serve!C34 = 6,224.575126 COP/tx

## Verdict

**NO PRESTATIONAL FACTOR MISMATCH EXISTS.** The premise "backend factor
1.5256 vs Excel 1.5699 (diff 0.0443)" does not correspond to the actual
loaded-salary computation. Both Excel and backend produce the SAME loaded
SAC line and the SAME per-line carga factor (1.5147 over imponible).

The numbers 1.5256 / 1.5699 are **emergent aggregate ratios**
(loaded payroll total / raw-commission-only base), inflated artifacts of
the agent mix, NOT clean prestational factors.

## Excel prestational components (Inputs de Nomina, row 36)

| Component | Excel cell | Rate | Backend (V27 provider) | Match |
|---|---|---|---|---|
| Salud | I36 | 0.085 | aps.salud 0.085 | YES |
| Fondo de pensión | J36 | 0.12 | aps.pension 0.12 | YES |
| ARL Staff | L36 | 0.00522 | aps.arl_staff 0.00522 | YES |
| Caja | N36 | 0.04 | aps.caja 0.04 | YES |
| ICBF + Sena | O36 | 0.04 | aps.icbf_sena 0.04 | YES |
| Cesantías | Q36 | 0.0833 | pre.cesantias 0.0833 | YES |
| Primas | R36 | 0.0833 | pre.primas 0.0833 | YES |
| Interés cesantías | S36 | 0.12 | pre.interes_cesantia 0.12 | YES |
| Vacaciones | T36 | 0.0417 | pre.vacaciones 0.0417 | YES |
| SMLV | C4 | 1,750,905 | salario_minimo 1,750,905 | YES |
| Aux transporte | C5 | 249,095 | auxilio_transporte 249,095 | YES |
| % Cumplimiento variable | C6 | 0.70 | pct_cumplimiento_variable 0.70 | YES |
| Factor alto salario | — | 10 SMLV | factor_alto_salario_smmlv 10 | YES |
| Factor corrector | — | 0.70 | factor_corrector_alto_salario 0.70 | YES |

All 14 prestational inputs match Excel V2-8 EXACTLY. There is no rate drift,
no missing component, no extra component, no provider-version mismatch.

## Loaded SAC line — exact reconstruction

Excel `Inputs de Nomina`!W62 (Costo Empresa) = 3,560,973.8626 reconstructed
component-by-component from row 36 rates:

- M62 (seg social = haberes+salud+pension+arl) = 2,894,380.3241
- P62 (parafiscales = caja+icbf) = 94,036.20
- U62 (prestaciones = ces+pri+int+vac) = 557,182.3385
- V62 (dotaciones) = 15,375.00
- **W62 = 3,560,973.8626**

Backend `NominaCargadaService.calcular(base=1,750,905, com_pct=600000/1,750,905)`
= **3,560,973.8626** — exact match (Δ < 0.01 COP).

True per-line carga factor over imponible (F62 = 2,350,905):
**W62 / F62 = 1.5147** (Excel == backend).

## Why 1.5699 / 1.5256 are not real factors

- 1.5699 = aggregate loaded variable / aggregate RAW commission across the
  full SAC agent mix. Dividing the loaded total by raw commission only
  (excluding the imponible base) inflates the ratio. Not a stored Excel cell;
  the literal 1.5699 appears nowhere in V2-8.
- 1.5256 = backend's analogous aggregate ratio under its current variable
  split (commission reported raw × 0.70, carga absorbed into salario_fijo).

## Root cause of CTS-001 residual (-232.07 COP/tx, -3.73%)

**Classification: FORMULA_IMPLEMENTATION_BUG** in the downstream CTS per-line
attribution (`NominaCalculator._comisiones` / `_salario_fijo`), NOT a
prestational factor or rate mismatch.

CTS Cadena A `desglose_a` (COP/tx):

| Component | Backend | Excel | Delta |
|---|---|---|---|
| salario_fijo | 4,621.64 | 4,629.49 | -7.85 |
| salario_variable | 494.15 | 775.74 | -281.60 |
| capacitacion_inicial | 9.80 | 11.59 | -1.78 |
| capacitacion_rotacion | 19.18 | 22.67 | -3.49 |
| examenes | 0.02 | 12.24 | -12.23 |
| crucero | 0.00 | 10.63 | -10.63 |
| no_payroll/opex (offset) | — | — | +85.5 |
| **TOTAL** | 5,992.50 | 6,224.58 | **-232.07** |

- salario_variable -281.60: backend reports commission RAW × 0.70 at the CTS
  variable line; Excel attributes the FULL loaded commission (with carga) to
  the variable line. The carga is absorbed into salario_fijo in the backend,
  but the 0.30 cumplimiento reduction and per-line allocation make the
  loaded-salary subtotal (sf+sv = 5,115.79) lower than Excel (5,405.23).
- examenes -12.23, crucero -10.63: components ~0 in backend (separate gaps,
  not factor-related).

## Why NO fix applied

1. There is NO factor to fix — rates and loaded line already match Excel.
2. Closing salario_variable requires rewriting `NominaCalculator._comisiones`
   (move cumplimiento downstream + apply carga to the variable line), which
   changes total payroll → PyG, Vision Tarifas, baseline snapshots.
   Explicitly OUT OF SCOPE ("NO TOCAR ... PyG, Vision Tarifas").
3. examenes/crucero zero-outs are separate component-load gaps (CTS-EXAM,
   CTS-CRUCERO), not prestational factor.

No hardcoded values introduced. No code changed.
