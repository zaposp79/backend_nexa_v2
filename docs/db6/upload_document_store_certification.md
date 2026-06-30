# DB.6.5 certificación transversal uploads GN/HR/OP

## Objetivo

Certificar que los uploads de parametrización GN, HR y OP usan el mismo límite de
persistencia sobre `DocumentStore`, sin cambiar contratos HTTP, JSON legacy,
lógica de negocio ni archivos Oracle-sensitive.

## Matriz GN/HR/OP

| Dominio | Router | Service | Repository upload | Codec | Collection | Índice |
| ------- | ------ | ------- | ----------------- | ----- | ---------- | ------ |
| GN | `modules/parametrizacion/gn/api/router.py` resuelve `container.gn_upload_service` | `GNService(repository=...)` | `GNRepository(store, version_index_repository, codec)` | `GNVersionDocumentCodec` | `GN_PARAMETRIZATION_COLLECTION` | `VersionIndexRepository(store, collection)` |
| HR | `modules/parametrizacion/hr/api/router.py` resuelve `container.hr_upload_service` | `HRService(repository=...)` | `HRRepository(store, version_index_repository, codec)` | `HRVersionDocumentCodec` | `HR_PARAMETRIZATION_COLLECTION` | `VersionIndexRepository(store, collection)` |
| OP | `modules/parametrizacion/op/api/router.py` resuelve `container.op_upload_service` | `OPService(repository=...)` | `OPRepository(store, version_index_repository, codec)` | `OPVersionDocumentCodec` | `OP_PARAMETRIZATION_COLLECTION` | `VersionIndexRepository(store, collection)` |

## Persistencia observable

| Dominio | `{module}/{version_id}.json` | `{module}/versions.json` | Duplicados | Compensación si falla índice |
| ------- | ---------------------------- | ------------------------- | ---------- | ----------------------------- |
| GN | Payload lógico GN exacto, sin `id` técnico | Lista legacy de summaries | Conserva entradas duplicadas; última queda activa | Elimina payload nuevo o restaura payload previo |
| HR | Payload lógico HR exacto, sin `id` técnico | Lista legacy de summaries | Conserva entradas duplicadas; última queda activa | Elimina payload nuevo o restaura payload previo |
| OP | Payload lógico OP exacto, sin `id` técnico | Lista legacy de summaries | Conserva entradas duplicadas; última queda activa | Elimina payload nuevo o restaura payload previo |

## Guardrails certificados

Prueba transversal agregada:

- `tests/parametrizacion/uploads/test_uploads_document_store_certification.py`

Valida para GN, HR y OP:

- El repository de upload no hereda `BaseRepository`.
- El repository recibe `store`, `version_index_repository` y `codec` por constructor.
- El repository usa `upsert_record()` y `get_record()`.
- El repository no usa `open()`, `json.dump` ni `write_text`.
- El service recibe `repository` por constructor.
- El router usa `Depends(_get_service)` y resuelve service desde `app.state.container`.
- El payload `{version_id}.json` queda sin `id` técnico.
- `versions.json` conserva formato legacy de lista.
- Duplicados preservan el comportamiento histórico.
- La compensación elimina payload nuevo si falla el índice.
- La compensación restaura payload previo si ya existía.

## Dependencias residuales a filesystem

No hay filesystem directo en repositories de upload GN/HR/OP.

Residuo legacy intencional en repositories de lectura activa:

| Dominio | Archivo | Uso residual |
| ------- | ------- | ------------ |
| GN | `modules/parametrizacion/gn/repositories/gn_active_parametrization_repository.py` | `active.path` + `GN_DIR` + `read_json()` |
| HR | `modules/parametrizacion/hr/repositories/hr_active_parametrization_repository.py` | `active.path` + `HR_DIR` + `read_json()` |
| OP | `modules/parametrizacion/op/repositories/op_active_parametrization_repository.py` | `active.path` + `OP_DIR` + `read_json()` |

Este residuo no pertenece al límite de escritura de upload. Se conserva para
compatibilidad con índices antiguos que todavía puedan tener `path`.

## Diferencias detectadas

| Diferencia | Evaluación | Acción |
| ---------- | ---------- | ------ |
| HR mantiene logging operativo más detallado que GN/OP | Diferencia funcional histórica del service HR, no del límite de persistencia | No cambiar en DB.6.5 |
| HR trata validación estructural como warnings en algunos casos | Diferencia de contrato HR ya existente | No cambiar en DB.6.5 |
| Payloads GN/HR/OP tienen formas distintas | Diferencia de dominio esperada | Certificar por comportamiento observable, no abstraer |
| `_service` temporal existe en routers GN/HR/OP | Override legacy de tests y compatibilidad local | Mantener por ahora; retirar en fase separada |

No se creó una abstracción común porque aumentaría el riesgo sobre Oracle sin
aportar cambio observable en esta fase. Las implementaciones ya son equivalentes
en el límite certificado.

## Validación ejecutada

```text
Transversal DB.6.5:       21 passed
Uploads parametrización:  61 passed
DB:                       36 passed, 12 skipped
Oracle/parity:            406 passed, 11 skipped, 39 deselected
Gate completo:            56 failed, 1344 passed, 46 skipped, 450 deselected, 1 xfailed
```

## Fallos nuevos vs baseline

Baseline exacto esperado:

```text
56 failed
```

Comparación por node id:

```text
expected=56 actual=56
new_failures=0
missing_baseline_failures=0
```

Node ids nuevos:

```text
[]
```

## Archivos SEC.P0.1 presentes en worktree

DB.6.5 no modifica ni depende de estos cambios. Se reportan separados porque ya
estaban presentes en el worktree:

- `README.md`
- `app.py`
- `env.example`
- `run_api.sh`
- `modules/shared/infrastructure/app_settings.py`
- `tests/api/test_sec_p0_1_production_hardening.py`

## Riesgos legacy pendientes

| Riesgo | Estado | Recomendación |
| ------ | ------ | ------------- |
| `active.path` | Permanece en lectura activa GN/HR/OP | Auditar índices productivos antes de remover |
| `_service` temporal | Permanece en routers GN/HR/OP | Retirar cuando tests usen overrides FastAPI/container |
| Compensación JSON best effort | Suficiente para JSON local | Diseñar transacción o rollback explícito antes de Cosmos |

## Recomendación de siguiente fase

Siguiente paso recomendado: preparar adapter Cosmos, no corregir inconsistencias
de negocio en esta línea.

Justificación:

- GN, HR y OP quedaron equivalentes en comportamiento observable de upload.
- No hay fallos nuevos por node id.
- Las diferencias restantes son legacy o propias del dominio, no bloqueos del
  límite `DocumentStore`.
- Cosmos requiere validar atomicidad y compensación con semántica distinta a JSON.

Prompt sugerido:

```text
Implementa DB.7.0: preparación del adapter Cosmos para parametrización GN/HR/OP.

Objetivo:
Validar que el contrato StoredDocument + VersionIndexRepository usado por los
uploads GN/HR/OP pueda ejecutarse sobre Cosmos sin cambiar JSON legacy, contratos
HTTP ni lógica de negocio.

Alcance:
- DocumentStore Cosmos adapter
- StoredDocument serialization
- VersionIndexDocumentCodec
- Tests contractuales equivalentes JSON/Cosmos fake
- Sin migrar datos productivos
- Sin tocar calculators, visiones ni Oracle-sensitive files

Validar:
- upsert_record/get_record/delete por collection
- payload lógico sin metadata técnica
- versions index como lista legacy
- duplicados preservados
- estrategia de compensación o rollback para falla parcial
- gate completo contra baseline exacto de node ids
```
