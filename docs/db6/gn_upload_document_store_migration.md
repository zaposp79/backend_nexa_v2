# DB.6.2 migración upload GN a DocumentStore

## Baseline

Entorno:

- `DB_PROVIDER=json`
- Backend activo: `json`
- Errores de colección: `0`

Antes de modificar GN:

- GN upload characterization: `3 passed`
- Oracle/parity: `406 passed, 11 skipped, 39 deselected`
- Gate esperado heredado DB.6.1: `56 failed`, mismos node ids conocidos

Después de migrar GN:

- GN upload characterization: `3 passed`
- Uploads parametrización: `25 passed`
- DB: `36 passed, 12 skipped`
- Oracle/parity: `406 passed, 11 skipped, 39 deselected`
- Gate: `56 failed, 1301 passed, 46 skipped, 450 deselected, 1 xfailed`

Los 56 fallos son los mismos node ids de baseline. El incremento de passed viene de tests GN/codec nuevos.

## Inventario dirigido GN

| Componente | Responsabilidad actual | Acceso a filesystem | Acción |
| ---------- | ---------------------- | ------------------- | ------ |
| `GNService` | Validar workbook, mapear payload y delegar persistencia | No | Migrado a inyección de `GNRepository` |
| `GNRepository` | Persistir versiones GN y actualizar índice | No directo; usa `DocumentStore` | Migrado a `StoredDocument` |
| `GNVersionDocumentCodec` | Separar `version_id` como id técnico y payload lógico | No | Usado en escritura GN |
| `VersionIndexRepository` | Encapsular `versions.json` | No directo cuando recibe `store + collection`; legacy cuando recibe `domain_dir` | Migrado para usar codec + `DocumentStore` preservando `versions.json` |
| `GNActiveParametrizationRepository` | Lectura activa GN para consumidores existentes | Solo fallback `active.path` legacy | No migrado en esta fase de upload |
| `GN API router` | Contrato HTTP público | No | Usa `GNService` desde container o override de test |
| `ApplicationContainer` | Wiring de dependencias | Construye store de parametrización existente | Agrega `GNRepository` y `GNService` con el mismo `parametrization_store` |

## Flujo GN

| Componente | Antes | Después |
| ---------- | ----- | ------- |
| Router | `_service = GNService()` global | `Depends` obtiene `container.gn_upload_service`; `_service` queda solo como override de tests |
| Service | Construía `GNRepository()` internamente | Recibe `GNRepository` por constructor |
| Repository | Heredaba `BaseRepository(GN_DIR)` | Recibe `DocumentStore`, `VersionIndexRepository`, `GNVersionDocumentCodec` |
| Payload | `write_json(gn/{version_id}.json, data)` vía base repo | `codec.encode(data)` + `DocumentStore.upsert_record()` |
| Índice | `VersionIndexRepository(domain_dir=GN_DIR)` | `VersionIndexRepository(store, collection)` + `VersionIndexDocumentCodec(record_id="versions")` |

## Persistencia

| Recurso | Metadata técnica | Payload lógico | Esquema preservado |
| ------- | ---------------- | -------------- | ------------------ |
| `gn/{version_id}.json` | `StoredDocument.id = payload["version_id"]` | `{version_id, lv, sheets}` exacto | Si, sin `id`, `domain`, `metadata`, `partition_value` |
| `gn/versions.json` | `StoredDocument.id = "versions"` | Lista legacy de summaries | Si, sigue siendo lista |

## Consistencia

| Escenario de fallo | Resultado | Compensación |
| ------------------ | --------- | ------------ |
| Falla al guardar payload | No se actualiza índice | No requiere compensación |
| Falla al actualizar índice con versión nueva | No queda archivo huérfano | Se elimina solo `gn/{version_id}.json` recién creado |
| Falla al actualizar índice con versión duplicada | No se borra payload preexistente | Se restaura el payload previo |
| Escritura exitosa con versión duplicada | Se preserva comportamiento legacy | Archivo queda con último payload; índice mantiene entradas duplicadas y última activa |

## Legacy retirado

| Método legacy | Consumidores GN antes | Consumidores GN después |
| ------------- | --------------------- | ----------------------- |
| `BaseRepository.save_version()` | `GNRepository` heredado por upload GN | Ninguno |
| `BaseRepository.set_active()` | `GNService.activate()` vía `GNRepository` heredado | Ninguno; se usa `GNRepository.activate_version()` |
| `BaseRepository.delete_version()` | `GNService.delete()` vía `GNRepository` heredado | Ninguno; se usa `GNRepository.delete_version()` propio |

## Guardrails

Tests agregados:

- `tests/parametrizacion/uploads/test_gn_repository_document_store.py`
- `tests/parametrizacion/uploads/test_gn_guardrails.py`
- extensión de `tests/parametrizacion/uploads/test_document_codecs.py`

Validan:

- `GNRepository` usa `GNVersionDocumentCodec`.
- `GNRepository` usa `DocumentStore.upsert_record()`.
- JSON GN no recibe `id`.
- `versions.json` conserva lista legacy.
- Versión duplicada preserva comportamiento.
- Falla de índice compensa archivo nuevo.
- Falla de índice restaura payload previo si era duplicado.
- Runtime GN de upload no importa providers concretos ni factories.
- Repositorio GN no usa `BaseRepository`, `open()`, `json.dump` ni `write_text`.

## Validación

```text
GN upload characterization: 3 passed
Uploads parametrización:    25 passed
DB:                         36 passed, 12 skipped
Oracle:                     406 passed / delta 0
Collection errors:          0
Backend activo:             json
JSON GN con id nuevo:       no
BaseRepository.save_version consumers GN: 0
Accesos directos filesystem GN upload: 0
Acceso filesystem GN restante: GNActiveParametrizationRepository conserva fallback active.path legacy
```

## Siguiente fase: prompt HR

Migrar únicamente el upload HR usando el mismo patrón validado en GN:

1. No tocar GN, OP ni Business Rules.
2. Congelar expected actuales de `tests/parametrizacion/uploads/test_hr_upload_characterization.py`.
3. Definir una constante de colección HR compatible con `storage/parametrization/hr/{version_id}.json`.
4. Hacer que `HRRepository` reciba `DocumentStore`, `VersionIndexRepository` y `HRVersionDocumentCodec`.
5. Persistir payload HR con `HRVersionDocumentCodec.encode()` + `DocumentStore.upsert_record()`.
6. Persistir `hr/versions.json` con `VersionIndexRepository(store, collection)` preservando lista legacy.
7. Mantener comportamiento de versión duplicada.
8. Agregar compensación: si falla índice, eliminar archivo nuevo o restaurar payload previo.
9. Ajustar `HRService` para recibir repository por constructor.
10. Agregar `HRRepository` y `HRService` al `ApplicationContainer` usando el mismo `parametrization_store`.
11. Mantener endpoint, HTTP payload, códigos y validaciones sin cambios.
12. Agregar guardrails HR equivalentes a GN.
13. Validar uploads HR, uploads completos, DB, parity y gate completo contra los mismos node ids baseline.
