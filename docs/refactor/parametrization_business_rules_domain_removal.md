# Parametrization Business Rules Domain Removal

## Scope

`business_rules` was removed as an active parametrization domain/source from `storage/parametrization/v2-7` and runtime parametrization registries. Runtime business rules remain served from canonical YAML under `modules/shared/config/business_rules`.

No formulas, calculations, YAML business rule values, GN/HR/OP values, frozen assets, certified baselines, or DB-backed certification assets were changed.

## Active v2-7 Inventory

- `gn.json`
- `hr.json`
- `op.json`
- `manifest.json`

`storage/parametrization/v2-7/business_rules.json` was removed from the active store.

## Runtime Guardrails

Runtime code must not reference:

- `storage/parametrization/business_rules`
- `storage/parametrization/v2-7/business_rules.json`

The active parametrization modules for v2-7 are GN/HR/OP only.

## Cadena C Excel Parity Gate

The missing active Cadena C parity snapshots were checked in git:

- `tests/refactor/snapshots_cadena_c/baseline_a_plus_b_v1.json`
- `tests/refactor/snapshots_cadena_c/baseline_a_plus_c_v1.json`
- `tests/refactor/snapshots_cadena_c/baseline_a_b_plus_c_v1.json`

They do not exist in `HEAD~1` at the active paths. Git tracks the corresponding files only under `tests/refactor/snapshots_cadena_c/invalidated/`, consistent with the known state that Cadena C Excel parity is blocked until a real Excel/V2-8 oracle exists.

Only the affected Excel parity snapshot tests are marked with `cadena_c_excel_oracle_missing` and excluded from the default gate. Cadena C backend regression/golden tests remain active. No snapshots were regenerated from backend output.

## Validation

- `PYTHONPATH=$(pwd) pytest tests/refactor/test_excel_backend_parity_cadena_c_scenarios.py -q` -> `11 passed, 3 deselected`
- `PYTHONPATH=$(pwd) pytest tests/refactor/ -q` -> `93 passed, 3 deselected`
- `PYTHONPATH=$(pwd) pytest tests/golden/ -q` -> `58 passed, 82 deselected`
- `PYTHONPATH=$(pwd) pytest tests/refactor/test_baseline_formula_snapshot_v1.py -q` -> `5 passed`
- `PYTHONPATH=$(pwd) pytest tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py -q` -> `5 passed`

Runtime reference checks found no matches for:

- `storage/parametrization/business_rules`
- `storage/parametrization/v2-7/business_rules.json`

Zero-drift status: validated for the executed golden and baseline snapshot gates.
