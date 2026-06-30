# INPUT_CONTRACT_FIX_B1 Summary

Fecha: 2026-06-06. Branch: refactor/modular-pure.

## Qué cambió

Un único guard de unwrap en `modules/calculator/user_input_loader.py`,
método `_normalizar_entry_data_format`, sección cadena_b (~línea 390):

```python
# Guard: detect accidental double-nesting (same pattern as cadena_a above).
if (
    isinstance(condiciones_b, dict)
    and "condiciones_cadena_b" in condiciones_b
    and "canales" not in condiciones_b
    and "opex" not in condiciones_b
):
    inner = condiciones_b["condiciones_cadena_b"]
    if isinstance(inner, dict):
        condiciones_b = inner
```

## Por qué cambió

`request.json` (Bancamia Cobranzas) envía `condiciones_cadena_b` con doble anidamiento:
```json
"condiciones_cadena_b": {
  "condiciones_cadena_b": { "opex": {...}, "hitl": {...}, ... }
}
```

El loader pasaba el nivel externo al adapter, que no reconocía ese formato y
construía cadena_b vacía → `costo_b = 0` en los 24 meses del contrato.

El mismo patrón (doble anidamiento) ya estaba corregido para `condiciones_cadena_a`
en la línea 346 del mismo método. La corrección para cadena_b es idéntica.

## Impacto en contratos públicos

**NINGUNO.**
- DTOs públicos (`CondicionesCadenaBInput`, `CanalCadenaBInput`, etc.): sin cambio
- `ApiResponse`: sin cambio
- Endpoints HTTP: sin cambio
- Calculadores y fórmulas: sin cambio
- `NewEntryDataAdapter`: sin cambio

## Tests que validan el fix

Archivo: `tests/refactor/test_input_contract_fix_b1.py` — 7/7 PASSED

1. `test_cadena_b_flat_format_works` — formato plano sigue funcionando
2. `test_cadena_b_nested_format_works` — formato doble-anidado produce costo_b > 0
3. `test_cadena_b_nested_and_flat_produce_equal_cost` — ambos formatos dan resultado idéntico
4. `test_cadena_b_produces_canales` — canales se construyen correctamente
5. `test_cadena_c_flat_format_doesnt_break` — cadena_c no se afecta
6. `test_cadena_a_not_affected` — cadena_a no se afecta
7. `test_request_json_after_fix` — request.json ya no produce costo_b=0

## Baseline actualizado

Ver `formula_refactor_baseline_1.md` para valores de referencia post-fix.

---

## Post-fix: Input Contract Canonicalization (B1-Canon)

Fecha: 2026-06-06.

### Changes

- `request/request.json` normalizado a formato canónico plano
- Cadena A: `condiciones_cadena_a` ya no está anidada bajo sí misma
- Cadena B: `condiciones_cadena_b` ya no está anidada bajo sí misma
- Cadena C: ya estaba en formato plano, sin cambios
- Backend: unwrap guards mantenidos para compatibilidad con formato legacy
- `ContractValidator._validate_escenarios`: extendido para aceptar volumetria-derived
  canales como escenarios válidos (outbound cadena_a activo en volumetria es válido)

### Impact

- Output: idéntico a Baseline 1 (`costo_b mes1 = 39,503,127.41`)
- Tests: 7 originales PASSED + 5 nuevos canonicalization tests = 12/12 PASSED
- Golden suite: 58/58 PASSED (sin regresiones)
- Baseline snapshot: 5/5 PASSED (sin drift)
- Ready for: refactor de no_payroll con contrato de entrada limpio

---

## Closeout: INPUT_CONTRACT_CANONICALIZATION_1 (2026-06-06)

### Final State

- `request/request.json`: PLANO (sin doble wrapper en A/B/C)
- Backend: acepta legacy anidado (compatibilidad temporal via unwrap guards)
- Equivalencia: plano == anidado en output (validado con rel_tol=1e-9)
- Cadena B: fluye correctamente (costo_b mes1 = 39,503,127.41)
- Baseline: v1 (`tests/refactor/baseline_formula_snapshot_v1.json`) es baseline oficial post-canonicalization

### Code Impact

- Modified: `user_input_loader.py` (normalización de entrada, NOT formulas)
  - Guard cadena_a: ~line 344 (unwrap `condiciones_cadena_a.condiciones_cadena_a`)
  - Guard cadena_b: ~line 397 (unwrap `condiciones_cadena_b.condiciones_cadena_b`)
- Modified: `request/request.json` (canonicalized to flat format)
- Modified: `validation/contract_validator.py` (accept volumetria-derived canales)
- Untouched: All calculators, formulas, frozen parametrization, CTS, DTOs, HTTP contracts

### Tests (CLOSEOUT)

- Canonicalization tests: 12/12 PASSED
- Baseline/Snapshot guardrails: 5/5 PASSED
- Golden/Parity: 58/58 PASSED
- Full refactor + golden suite: 81/81 PASSED

### Note on Entry Points

- ❌ `python -m backend_nexa.main`: **REMOVED (legacy CLI, no productive use)**
- ✅ Use tests to validate: `pytest tests/refactor/`
- ✅ For integration/production: use API endpoints `POST /api/v1/simulation/calculate`

### Artifacts Created by Closeout

- `docs/refactor/canonicalization_closeout_code_changes.md`
- `docs/refactor/baseline_state.md`
- `docs/refactor/equivalence_validation.md`
- `docs/refactor/entrypoint_notes.md`
- `docs/refactor/CLOSEOUT_REPORT.md`
- `tests/refactor/baseline_formula_snapshot_v1.json`
