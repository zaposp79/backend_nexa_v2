# DB.6.4 migración upload OP a DocumentStore

## Baseline

Entorno:

- `DB_PROVIDER=json`
- Backend activo: `json`
- Errores de colección: `0`

Antes de modificar OP:

- OP upload characterization: `3 passed`
- Oracle/parity: `406 passed, 11 skipped, 39 deselected`
- Gate esperado heredado SEC.P0.1: `56 failed`, mismos node ids conocidos

Después de migrar OP:

- OP upload characterization: `3 passed`
- Uploads parametrización: `40 passed`
- Oracle/parity: `406 passed, 11 skipped, 39 deselected`
- Gate: `56 failed, 1323 passed, 46 skipped, 450 deselected, 1 xfailed`

## Inventario dirigido OP

| Componente | Responsabilidad actual | Acceso a filesystem | Acción |
| ---------- | ---------------------- | ------------------- | ------ |
| `OPService` | Validar workbook, mapear payload OP y delegar persistencia | No | Migrado a inyección de `OPRepository` |
| `OPRepository` | Persistir versiones OP y actualizar índice | No directo; usa `DocumentStore` | Migrado a `StoredDocument` |
| `OPVersionDocumentCodec` | Separar `version_id` como id técnico y payload lógico | No | Usado en escritura OP |
| `VersionIndexRepository` | Encapsular `versions.json` | No directo cuando recibe `store + collection`; legacy cuando recibe `domain_dir` | Usado con `DocumentStore` preservando `versions.json` |
| `OPActiveParametrizationRepository` | Lectura activa OP para consumidores existentes | Solo fallback `active.path` legacy | No migrado en esta fase de upload |
| `OP API router` | Contrato HTTP público | No | Usa `OPService` desde container o override de test |
| `ApplicationContainer` | Wiring de dependencias | Construye store de parametrización existente | Agrega `OPRepository` y `OPService` con el mismo `parametrization_store` |

## Flujo OP

| Componente | Antes | Después |
| ---------- | ----- | ------- |
| Router | `_service = OPService()` global | `Depends` obtiene `container.op_upload_service`; `_service` queda solo como override de tests |
| Service | Construía `OPRepository()` internamente | Recibe `OPRepository` por constructor |
| Repository | Heredaba `BaseRepository(OP_DIR)` | Recibe `DocumentStore`, `VersionIndexRepository`, `OPVersionDocumentCodec` |
| Payload | `write_json(op/{version_id}.json, data)` vía base repo | `codec.encode(data)` + `DocumentStore.upsert_record()` |
| Índice | `VersionIndexRepository(domain_dir=OP_DIR)` | `VersionIndexRepository(store, collection)` + `VersionIndexDocumentCodec(record_id="versions")` |

## Persistencia

| Recurso | Metadata técnica | Payload lógico | Esquema preservado |
| ------- | ---------------- | -------------- | ------------------ |
| `op/{version_id}.json` | `StoredDocument.id = payload["version_id"]` | Payload OP exacto (`version_id`, `sheets`) | Si, sin `id`, `domain`, `metadata`, `partition_value` |
| `op/versions.json` | `StoredDocument.id = "versions"` | Lista legacy de summaries | Si, sigue siendo lista |

## Consistencia

| Escenario de fallo | Resultado | Compensación |
| ------------------ | --------- | ------------ |
| Falla al guardar payload | No se actualiza índice | No requiere compensación |
| Falla al actualizar índice con versión nueva | No queda archivo huérfano | Se elimina solo `op/{version_id}.json` recién creado |
| Falla al actualizar índice con versión duplicada | No se borra payload preexistente | Se restaura el payload previo |
| Escritura exitosa con versión duplicada | Se preserva comportamiento legacy | Archivo queda con último payload; índice mantiene entradas duplicadas y última activa |

La compensación es best effort para JSON. Cosmos requerirá estrategia transaccional posterior si se activa.

## Contrato OP preservado

| Comportamiento | Estado |
| -------------- | ------ |
| `POST /parametrization/op/upload` retorna el mismo envelope HTTP | Preservado |
| `OP-ICA` se serializa como `key="ica"` con `rows` | Preservado |
| `OP-Poliza` se serializa como `key="poliza"` con `rows` | Preservado |
| `OP-LV` se serializa como catálogos únicos | Preservado |
| Extensión inválida retorna `400` con el mismo `detail` | Preservado |
| Workbook inválido retorna `success=false` con `UPLOAD_ERROR` | Preservado |
| Warnings por tasas sospechosas de ICA y póliza | Preservado |
| Versión duplicada mantiene entradas duplicadas en `versions.json` | Preservado |

## Legacy retirado

| Método legacy | Consumidores OP antes | Consumidores OP después |
| ------------- | --------------------- | ----------------------- |
| `BaseRepository.save_version()` | `OPRepository` heredado por upload OP | Ninguno |
| `BaseRepository.set_active()` | `OPService.activate()` vía `OPRepository` heredado | Ninguno; se usa `OPRepository.activate_version()` |
| `BaseRepository.delete_version()` | `OPService.delete()` vía `OPRepository` heredado | Ninguno; se usa `OPRepository.delete_version()` propio |

## Guardrails

Tests agregados:

- `tests/parametrizacion/uploads/test_op_repository_document_store.py`
- `tests/parametrizacion/uploads/test_op_guardrails.py`

Validan:

- `OPRepository` usa `OPVersionDocumentCodec`.
- `OPRepository` usa `DocumentStore.upsert_record()`.
- JSON OP no recibe `id`.
- `versions.json` conserva lista legacy.
- Versión duplicada preserva comportamiento.
- Falla de índice compensa archivo nuevo.
- Falla de índice restaura payload previo si era duplicado.
- Runtime OP no importa providers concretos ni factories.
- Repositorio OP no usa `BaseRepository`, `open()`, `json.dump` ni `write_text`.
- Warnings funcionales OP para `OP-ICA` y `OP-Poliza` siguen activos.

## Validación

```text
OP upload characterization: 3 passed
Uploads parametrización:    40 passed
DB:                         36 passed, 12 skipped
Oracle:                     406 passed / delta 0
Gate:                       56 failed, 1323 passed, 46 skipped, 450 deselected, 1 xfailed
JSON OP con id nuevo:       no
BaseRepository.save_version consumers OP: 0
Accesos directos filesystem OP upload: 0
Acceso filesystem OP restante: OPActiveParametrizationRepository conserva fallback active.path legacy
```

## Siguiente fase: prompt de cierre DB.6

Auditar y cerrar la convergencia de uploads GN/HR/OP ya migrados a `DocumentStore`:

1. No modificar Business Rules ni lógica financiera.
2. Verificar que GN, HR y OP usen exclusivamente repositorios inyectados para escritura de upload.
3. Confirmar que `versions.json` conserva forma legacy en los tres dominios.
4. Confirmar que los payloads `{version_id}.json` no incluyen metadata técnica.
5. Revisar si los fallbacks `active.path` de lectura activa siguen teniendo consumidores reales.
6. Proponer una fase separada para retirar fallbacks legacy si ya no son necesarios.
7. Ejecutar uploads completos, DB, Oracle/parity y gate completo contra baseline.
8. Documentar delta de passed/failures y riesgos pendientes para Cosmos.
