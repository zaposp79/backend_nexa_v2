# DB.7.1 escritura atómica opcional para uploads GN/HR/OP

## Objetivo

Hacer que los uploads GN, HR y OP guarden payload de versión e índice legacy en
una sola operación cuando el `DocumentStore` soporte atomicidad, conservando la
compensación JSON existente para stores no atómicos.

## Implementación

| Pieza | Cambio |
| ----- | ------ |
| `AtomicDocumentStore` | Se marcó como `runtime_checkable` para detectar capacidad por puerto, no por clase concreta |
| `VersionIndexRepository` | Puede construir el registro `versions` sin persistirlo mediante `build_append_record()` |
| `VersionIndexRepository` | Puede persistir un registro preparado mediante `save_record()` |
| `version_payload_persistence.py` | Operación común `save_version_payload_and_index()` |
| `GNRepository` | Delega payload + índice en operación común |
| `HRRepository` | Delega payload + índice en operación común |
| `OPRepository` | Delega payload + índice en operación común |

## Flujo

### Store atómico

```text
payload_record = codec.encode(data)
index_record = version_index_repository.build_append_record(summary)
store.upsert_records_atomic(collection, [payload_record, index_record])
```

No hay compensación manual. Si el batch falla, el provider atómico debe no dejar
cambios parciales.

### Store no atómico

```text
previous_record = store.get_record(collection, payload_record.id)
store.upsert_record(collection, payload_record)
try:
    version_index_repository.save_record(index_record)
except Exception:
    eliminar payload nuevo o restaurar payload previo
```

La ruta JSON conserva la compensación certificada en DB.6.

## Contratos preservados

| Contrato | Estado |
| -------- | ------ |
| HTTP upload GN/HR/OP | Sin cambios |
| Payload lógico `{version_id}.json` | Sin `id` técnico |
| `versions.json` | Lista legacy preservada |
| Duplicados | Entradas duplicadas y última activa |
| Orden del índice | Append al final preservado |
| Provider default | `json` |
| Import directo de Cosmos en repositories | No existe |

## Diferencias GN/HR/OP

No hay diferencias en persistencia. Los tres repositorios usan:

```text
save_version_payload_and_index()
```

Las diferencias restantes son de dominio y ya existían:

- HR mantiene logging y validación permisiva histórica.
- GN/HR/OP tienen payloads lógicos distintos.
- Routers conservan `_service` temporal como override de tests.

## Tests agregados/extendidos

Archivo principal:

- `tests/parametrizacion/uploads/test_uploads_document_store_certification.py`

Cobertura nueva:

- Store atómico recibe payload + índice en un único batch.
- La ruta atómica no llama `upsert_record()` manual.
- Falla del batch atómico no deja payload ni índice parcial.
- Duplicado con store atómico mantiene orden y flags legacy.
- Store JSON conserva compensación actual.
- Payload no incluye `id`.
- Índice conserva lista y orden.
- Certificación transversal GN/HR/OP.

## Validación ejecutada

```text
Certificación transversal: 30 passed
Uploads parametrización:   70 passed
DB:                        42 passed, 12 skipped
Cosmos skeleton:           6 passed
Oracle/parity:             406 passed, 11 skipped, 39 deselected
Gate completo:             56 failed, 1359 passed, 46 skipped, 450 deselected, 1 xfailed
```

Comparación de fallos contra baseline:

```text
expected=56 actual=56
new_failures=0
missing_baseline_failures=0
```

## Riesgos pendientes para Cosmos real

| Riesgo | Estado | Siguiente paso |
| ------ | ------ | -------------- |
| Cuenta Cosmos no configurada | No probada por diseño | Crear prueba integración opcional con cuenta efímera |
| RU/latencia de batch | No medido | Medir con `parametrization` container real |
| Concurrencia sobre `versions` | Batch es atómico, pero no hay control de etag en DB.7.1 | Evaluar optimistic concurrency en DB.7.2 |
| `_service` temporal | Sigue en routers | Retirar cuando tests usen overrides FastAPI/container |
| `active.path` | Sigue en repositorios de lectura activa | Auditar índices productivos antes de eliminar |

## Criterio de cierre

DB.7.1 queda cerrado porque GN/HR/OP:

- usan atomicidad cuando el store implementa `AtomicDocumentStore`;
- mantienen fallback con compensación para JSON;
- preservan contratos HTTP y JSON legacy;
- no introducen fallos nuevos por node id.
