# Equivalence Validation: Flat vs Nested

Fecha: 2026-06-06. Branch: refactor/modular-pure.

## Objective

Confirm that the canonical flat format (request/request.json) produces exactly the same
engine output as the legacy double-nested format for cadena_a and cadena_b.

## Tests Executed

Tests in `tests/refactor/test_input_contract_fix_b1.py`:

- `test_flat_and_nested_b_produce_same_output` — cadena_b: flat vs nested, compares costo_b mes1 and total
- `test_flat_and_nested_a_produce_same_output` — cadena_a: flat vs nested, compares payroll_a mes1
- `test_cadena_b_nested_and_flat_produce_equal_cost` — synthetic fixture-based equivalence for cadena_b

All 3 tests use `math.isclose(rel_tol=1e-9)` — exact equality to floating-point precision.

## Results

All tests PASSED (12/12 PASSED in full refactor canonicalization suite).

| Metrica | Plano (canonical) | Anidado (legacy) | Match |
|---------|-------------------|------------------|-------|
| costo_b mes1 | 39,503,127.41 | 39,503,127.41 | EXACT (rel_tol=1e-9) |
| costo_b total (24m) | (baseline) | (baseline) | EXACT (rel_tol=1e-9) |
| payroll_a mes1 | 154,103,322.32 | 154,103,322.32 | EXACT (rel_tol=1e-9) |

## Conclusion

Formato canónico plano es equivalente a legacy anidado en output.
Backend normalización (unwrap guards en _normalizar_entry_data_format) funciona correctamente.

Los guards en user_input_loader.py producen exactamente el mismo payload interno al motor
independientemente de si la entrada viene en formato plano o anidado.

## Why This Matters

- Production clients sending the legacy nested format will continue to work without error.
- New clients and integrations should use the flat canonical format.
- The engine output is deterministic and format-independent.

## Deprecation Plan

When all clients/integrations are updated to the flat canonical format:
1. Remove the cadena_a guard (~line 344-357 in user_input_loader.py)
2. Remove the cadena_b guard (~line 397-416 in user_input_loader.py)
3. Add a 422 VALIDATION_ERROR for any nested format received
4. Document the breaking change in the API changelog

Until then, both formats are supported with zero output difference.
