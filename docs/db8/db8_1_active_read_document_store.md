# DB.8.1 Active Parametrization Read Closure

Fecha: 2026-06-05
Branch: `refactor/modular-pure`

## Alcance

DB.8.1 alinea la lectura activa de parametrizacion con
`DocumentStore.get_record()` como ruta principal.

No se modifico logica de calculo, contratos HTTP, payloads, layout JSON legacy,
`versions.json`, ni defaults de provider. JSON sigue siendo default y Cosmos no
queda activado por defecto.

## Matriz de lectura

| Dominio | Lectura anterior | Lectura nueva |
| --- | --- | --- |
| GN | `active.path` -> `read_json()`, si no `store.get()` | `VersionIndexRepository.get_active()` -> `store.get_record("gn", version_id)` -> codec GN; fallback `active.path` solo si falta el record |
| HR | `active.path` -> `read_json()`, si no `store.get()` | `VersionIndexRepository.get_active()` -> `store.get_record("hr", version_id)` -> codec HR; fallback `active.path` solo si falta el record |
| OP | `active.path` -> `read_json()`, si no `store.get()` | `VersionIndexRepository.get_active()` -> `store.get_record("op", version_id)` -> codec OP; fallback `active.path` solo si falta el record |
| business_rules | `versions.json` por `read_json()`, luego `active.path` o `store.get()` | `store.get_record("business_rules", "versions")`, luego `store.get_record("business_rules", active_id)`; fallback legacy a `versions.json`/`path` solo si falta el record |

## Fallbacks legacy conservados

Se conserva `active.path` para GN/HR/OP y `path` en business_rules porque el
storage legacy puede referenciar documentos en rutas como `../v2-7/*.json`.
El fallback queda despues de `get_record()` y esta cubierto por tests.

## Guardrails

`tests/parametrizacion/uploads/test_active_parametrization_document_store.py`
verifica:

- lectura normal desde `DocumentStore.get_record()`;
- lectura de documentos tipo Cosmos mediante `StoredDocument.payload`;
- fallback legacy controlado cuando falta el record;
- ausencia de `self._store.get()` en repositorios activos;
- orden `get_record()` antes de `read_json()` cuando existe fallback.

## Validacion

Comandos focales ejecutados:

```bash
PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA \
  venv_py312_backup_20260604_165827/bin/python \
  -m pytest tests/parametrizacion/uploads/test_active_parametrization_document_store.py -q --tb=short
```

Resultado: `12 passed`.

```bash
PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA \
  venv_py312_backup_20260604_165827/bin/python -m pytest tests/db -q --tb=short
```

Resultado: `58 passed, 20 skipped`.

```bash
PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA \
  venv_py312_backup_20260604_165827/bin/python \
  -m pytest tests/parametrizacion/uploads -q --tb=short
```

Resultado: `87 passed`.

```bash
PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA \
  venv_py312_backup_20260604_165827/bin/python \
  -m pytest tests/unit/test_business_rules_config.py tests/unit/test_riesgo_calculator.py \
  tests/parity/test_parity_panel_propagation.py tests/diagnostics/test_provider_singleton_state.py \
  -q --tb=short
```

Resultado: `33 passed, 4 deselected`.

```bash
PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA \
  venv_py312_backup_20260604_165827/bin/python -m pytest tests/parity -q --tb=short
```

Resultado: `406 passed, 11 skipped, 39 deselected`.

```bash
PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA \
  venv_py312_backup_20260604_165827/bin/python -m pytest tests/api/test_app_factory.py -q --tb=short
```

Resultado: `15 passed`.

`tests/unit/test_phase9_business_rules_migration.py` conserva 3 fallos conocidos
del baseline oficial.

## Gate vs baseline por node id

Baseline oficial ejecutado desde copia temporal de `HEAD`, con el mismo
`storage/` local:

```text
48 failed, 1623 passed, 54 skipped, 450 deselected, 1 xfailed
```

Gate actual DB.8.1:

```text
48 failed, 1640 passed, 54 skipped, 450 deselected, 1 xfailed
```

Comparacion:

```text
baseline_count=48
current_count=48
new_failures=0
missing_baseline_failures=0
```

`new_failures`:

```text
[]
```

`missing_baseline_failures`:

```text
[]
```

## Veredicto

DB.8.1 queda cerrado frente al baseline oficial por node id. La lectura activa
usa `DocumentStore.get_record()` como ruta principal y no introduce fallos
nuevos.

## Riesgos antes de Cosmos real

- Falta ejecutar smoke real contra cuenta Cosmos.
- Los fallbacks `active.path` siguen siendo necesarios para datos legacy.
- business_rules conserva su contrato historico de `versions.json` dict-based.
- La suite completa sigue roja por deuda preexistente del baseline, no por DB.8.1.
