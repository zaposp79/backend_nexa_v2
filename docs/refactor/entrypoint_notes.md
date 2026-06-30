# Entry Points

Fecha: 2026-06-06. Branch: refactor/modular-pure. **Updated: 2026-06-07 — CLI legacy removed.**

## CLI Legacy — Deprecated ❌ REMOVED

`backend_nexa/main.py` y `run_main.sh` were removed (2026-06-07) after audit confirmed NO productive use.
Reason: Single entrypoint principle — use API endpoint instead.

**Formats previously supported by CLI (for reference only):**
- Legacy: UserInput with `panel_de_control` + `cadena_a_perfiles`, etc.
- NOT supported: Entry data format (`request/request.json` with `datos_operativos`)

**Migration:** Use API endpoint or tests instead (see below).

## API Endpoints (Recommended for Integration)

- `POST /api/v1/simulation/calculate` — accepts CalculationRequest (includes entry_data payload)
- Returns simulation_id for subsequent result queries
- Handles full engine pipeline, persistence, and error normalization

## Tests (Recommended for Validation)

```bash
# Validates request/request.json correctness
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_input_contract_fix_b1.py -v

# Validates baseline stability
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_v0.py -v

# Full refactor suite
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/ -q

# Golden/parity tests
PYTHONPATH=$(pwd) pytest backend_nexa/tests/golden/ -q
```

All commands from `/Users/darwin.minota.quinto/Projects/NEXA` (parent directory).

## Summary

| Entry Point | Format | Use Case |
|-------------|--------|----------|
| ❌ `python -m backend_nexa.main` (REMOVED) | — | — |
| ✅ `POST /api/v1/simulation/calculate` | Entry data (datos_operativos) | **Official** — integration, production, validation |
| ✅ `pytest tests/refactor/` | Entry data via test fixtures | Validation, regression testing, baseline/parity |

**Flujo recomendado:**
1. Para validar `request/request.json` → `pytest tests/refactor/test_input_contract_*.py`
2. Para simular en producción → `POST /api/v1/simulation/calculate` con Postman/curl
3. Para garantizar reproducibilidad → `pytest tests/golden/ -m parity` (golden values)
