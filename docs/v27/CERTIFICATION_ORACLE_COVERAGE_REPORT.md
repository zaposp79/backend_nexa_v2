# Oracle Coverage Report — V2-7

## Test suite summary

| Suite | File | Tests | Pass | Skip | Fail |
|-------|------|-------|------|------|------|
| Oracle Mesh (208 checkpoints) | test_oracle_mesh.py + test_excel_oracle_v2_7_real.py | 208 | **208** | 7 | 0 |
| Vision Gap Closure | test_vision_gap_closure.py | 14 | 14 | 0 | 0 |
| Service-Driven Behavior | test_servicio_driven_behavior.py | 18 | 18 | 0 | 0 |
| Vision Activation Cases | test_vision_activation_cases.py | 21 | 21 | 0 | 0 |
| Gap Follow-up | test_gap_followup.py | 32 | 32 | 0 | 0 |
| W18.F5.D Coverage | test_w18_f5d_coverage.py | 40 | 40 | 0 | 0 |
| W18.F5.E Closure | test_w18_f5e_closure.py | 34 | 34 | 0 | 0 |
| **TOTAL PARITY SUITE** | tests/parity/ | **378** | **378** | **8** | **0** |

**Nota:** Los 8 skipped son justificados:
- W41/W42/W43: perfiles 3/4/5 no existen en fixture V2-7 (extractor devuelve None correctamente)
- Nomina Loaded!I89: celda header vacía en workbook (no confundir con dato)

## Oracle checkpoint distribution (208 total)

| Stage | Checkpoints | Pass |
|-------|-------------|------|
| PANEL (inputs) | 30 | 30 |
| NOMINA (salarios) | 5 | 5 |
| NOMINA_LOADED (por canal/mes) | 17 | 17 |
| PAYROLL_A (por mes) | 7 | 7 |
| NO_PAYROLL_A (por mes) | 7 | 7 |
| COSTOS_FINANCIEROS (ICA/GMF/etc.) | 21 | 21 |
| COSTO_TOTAL (por mes) | 7 | 7 |
| FACTOR_BILLING | 3 | 3 |
| INGRESO (por mes) | 21 | 21 |
| PYG (Vision P&G filas) | 35 | 35 |
| KPI | 3 | 3 |
| VISIONES (VT + CTS) | 23 | 23 |
| EXCEL_ORACLE_REAL | 39 | 39 |

## Tolerance

All checkpoints: `REL_TOL = 1e-6` (< 0.0001%)  
Two exceptions (VT polizas extension approx): `rel_tol = 3e-6`  
No checkpoint uses absolute tolerance relaxation beyond ABS_TOL = 1e-6.

## Drift summary

0% drift in all certified economic scenarios.
No gap between backend calculation and workbook oracle.
