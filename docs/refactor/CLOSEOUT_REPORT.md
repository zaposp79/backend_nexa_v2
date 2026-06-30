# INPUT_CONTRACT_CANONICALIZATION_1 — CLOSEOUT REPORT

**Date:** 2026-06-06
**Branch:** refactor/modular-pure
**Status:** CLOSED AND APPROVED

## Summary

Contrato de entrada (`request/request.json`) canonicalizado a formato plano.
Backend mantiene compatibilidad temporal con legacy anidado via unwrap guards.
Todas las validaciones y tests completados exitosamente.

## Changes

| File | Change | Type |
|------|--------|------|
| `request/request.json` | Plano (A/B sin wrapper redundante) | Test fixture |
| `modules/calculator/user_input_loader.py` | Guards para normalización (NO fórmulas) | Input normalization |
| `modules/calculator/validation/contract_validator.py` | Accept volumetria-derived canales | Validation |

Formulas, CTS, frozen parametrization: INTACTAS.

## Code Change Detail

`user_input_loader.py` — `_normalizar_entry_data_format()`:

- Guard cadena_a (~line 344): unwrap `condiciones_cadena_a.condiciones_cadena_a` → plano
  Condition: `"condiciones_cadena_a" in condiciones_a and "perfiles" not in condiciones_a`
- Guard cadena_b (~line 397): unwrap `condiciones_cadena_b.condiciones_cadena_b` → plano
  Condition: `"condiciones_cadena_b" in condiciones_b and "canales" not in condiciones_b and "opex" not in condiciones_b`

Both guards emit a WARNING log when triggered (for audit traceability).

## Validation Results (Final Closeout Run)

```
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/ backend_nexa/tests/golden/ -q
Result: 81 passed, 82 deselected, 1 warning in 0.83s
```

Breakdown:

| Suite | Tests | Result |
|-------|-------|--------|
| Canonicalization (`test_input_contract_fix_b1.py`) | 12 | PASSED |
| Baseline snapshot (`test_baseline_formula_snapshot_v0.py`) | 5 | PASSED |
| Parametrization policy (`test_parametrization_source_policy.py`) | 6 | PASSED |
| Golden CTS (`test_cost_to_serve_golden_v27.py`) | 30 | PASSED |
| Golden Vision Tarifas (`test_vision_tarifas_golden_v27.py`) | 28 | PASSED |
| **TOTAL** | **81** | **PASSED** |

## Baselines

| File | Status | costo_b mes1 | costo_total_contrato |
|------|--------|--------------|----------------------|
| `tests/refactor/baseline_formula_snapshot_v0.json` | Reference (historical, Baseline 1) | 39,503,127.41 | 5,411,620,868.43 |
| `tests/refactor/baseline_formula_snapshot_v1.json` | OFFICIAL for future refactors | 39,503,127.41 | 5,411,620,868.43 |

Note: v0 and v1 are numerically identical. The canonical flat format produces the same output
as the legacy nested format (validated with rel_tol=1e-9 across all KPIs).

## Code Quality

- No regressions detected (81/81 PASSED, 0 failures, 0 errors)
- Equivalence (plano == anidado) validated at rel_tol=1e-9 for costo_b and payroll_a
- Cadena B flowing correctly (costo_b mes1 = 39,503,127.41, was 0 before D-1 fix)
- Cadena A unaffected (payroll_a mes1 = 154,103,322.32)
- CTS, frozen, DTOs, HTTP contracts: UNTOUCHED

## KPI Anchors (v1 baseline)

| KPI | Value |
|-----|-------|
| costo_b mes1 | 39,503,127.41 |
| payroll_a mes1 | 154,103,322.32 |
| costo_total_contrato | 5,411,620,868.43 |
| pct_utilidad_neta_total | 0.2935 (29.35%) |

## Next Phase

Ready for: **FORMULA_REFACTOR_PHASE1_NOPAYROLL**

- Base: `tests/refactor/baseline_formula_snapshot_v1.json` (official)
- Guardrails: snapshot tests (5 tests) + 81/81 PASSED baseline
- Entry contract: stable (canonical flat format)
- No blocking issues

## Approved For

- Formula refactoring (with snapshot guardrails)
- Architecture improvements (input contract stable)
- Production deployment (no breaking changes)

## Artifacts Created by This Closeout

- `docs/refactor/canonicalization_closeout_code_changes.md`
- `docs/refactor/baseline_state.md`
- `docs/refactor/equivalence_validation.md`
- `docs/refactor/entrypoint_notes.md`
- `docs/refactor/CLOSEOUT_REPORT.md` (this file)
- `tests/refactor/baseline_formula_snapshot_v1.json`
