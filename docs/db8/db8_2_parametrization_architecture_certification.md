# DB.8.2 Parametrization Architecture Certification

Fecha: 2026-06-05
Branch: `refactor/modular-pure`

## Alcance

DB.8.2 certifica que GN, HR, OP y business_rules usan `DocumentStore` como
puerto de persistencia en las rutas normales de lectura y escritura.

JSON sigue siendo default. Cosmos sigue preparado por composicion y no se activa
por defecto. No se modifico logica de calculo, contratos HTTP, payloads ni
layout JSON legacy.

## Matriz dominio

| Dominio | Escritura normal | Lectura normal | Fallback legacy |
| --- | --- | --- | --- |
| GN | `GNRepository.save_version()` -> `save_version_payload_and_index()` -> `upsert_records_atomic()` o `upsert_record()` | `GNActiveParametrizationRepository.get_active_data()` -> `VersionIndexRepository.get_active()` -> `get_record("gn", version_id)` -> codec GN | `active.path` -> `read_json()` solo si falta el record |
| HR | `HRRepository.save_version()` -> `save_version_payload_and_index()` -> `upsert_records_atomic()` o `upsert_record()` | `HRActiveParametrizationRepository.get_active_data()` -> `VersionIndexRepository.get_active()` -> `get_record("hr", version_id)` -> codec HR | `active.path` -> `read_json()` solo si falta el record |
| OP | `OPRepository.save_version()` -> `save_version_payload_and_index()` -> `upsert_records_atomic()` o `upsert_record()` | `OPActiveParametrizationRepository.get_active_data()` -> `VersionIndexRepository.get_active()` -> `get_record("op", version_id)` -> codec OP | `active.path` -> `read_json()` solo si falta el record |
| business_rules | Composicion por `BusinessRulesRepository` sobre `DocumentStore`; formato dict-based heredado | `get_record("business_rules", "versions")` -> `get_record("business_rules", active_id)` | `versions.json`/`path` -> `read_json()` solo si falta el record |

## Excepciones legacy permitidas

- `db/factory.py` puede instanciar `JsonDocumentStore(PARAMETRIZATION_DIR)` para preservar el layout legacy JSON.
- `GNActiveParametrizationRepository`, `HRActiveParametrizationRepository` y `OPActiveParametrizationRepository` pueden usar `active.path` + `read_json()` solo despues de intentar `get_record()`.
- `BusinessRulesRepository` puede leer `versions.json`/`path` como fallback legacy solo si falta el record en `DocumentStore`.
- `VersionIndexRepository` conserva fallback `domain_dir` legacy fuera de la ruta normal con `store + collection`.

## Guardrails agregados

Archivo:

```text
tests/parametrizacion/uploads/test_parametrization_architecture_guardrails.py
```

Certifica:

- `JsonDocumentStore(PARAMETRIZATION_DIR)` solo aparece en `db/factory.py`.
- Repositorios activos no usan `self._store.get(`.
- Repositorios activos usan `get_record()` como ruta principal.
- Si hay `read_json()` en repositorios activos, aparece despues de `get_record()`.
- Repositorios de upload GN/HR/OP no importan provider concreto ni usan filesystem directo.
- Escritura de uploads usa `upsert_records_atomic()` o `upsert_record()`.
- `db/container.py` selecciona parametrizacion mediante `build_parametrization_document_store(db_config)`, no provider concreto.

Guardrails relacionados:

- `tests/parametrizacion/uploads/test_active_parametrization_document_store.py`
- `tests/parametrizacion/uploads/test_uploads_document_store_certification.py`
- `tests/db/unit/test_config_and_factory.py`

## Validacion focal

```text
tests/parametrizacion/uploads/test_parametrization_architecture_guardrails.py
tests/parametrizacion/uploads/test_active_parametrization_document_store.py
26 passed
```

```text
tests/db
58 passed, 20 skipped
```

```text
tests/parametrizacion/uploads
101 passed
```

```text
provider/panel/riesgo focal
33 passed, 4 deselected
```

```text
tests/parity
406 passed, 11 skipped, 39 deselected
```

```text
tests/api/test_app_factory.py
15 passed
```

## Gate vs baseline por node id

Baseline oficial ejecutado desde copia temporal de `HEAD`, con el mismo
`storage/` local:

```text
48 failed, 1623 passed, 54 skipped, 450 deselected, 1 xfailed
```

Gate actual DB.8.2:

```text
48 failed, 1654 passed, 54 skipped, 450 deselected, 1 xfailed
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

DB.8.2 queda cerrado: la parametrizacion queda certificada como agnostica en
rutas normales de lectura y escritura. No hay acoplamiento normal a JSON ni a
filesystem directo en GN/HR/OP/business_rules, y el gate no introduce fallos
nuevos frente al baseline oficial.

## Riesgos antes de activar Cosmos real

- Falta smoke real contra una cuenta Cosmos.
- Los fallos del gate completo siguen siendo deuda preexistente del baseline.
- Los fallbacks legacy deben conservarse mientras existan datos con `path`.
- business_rules mantiene contrato historico dict-based para `versions.json`.
