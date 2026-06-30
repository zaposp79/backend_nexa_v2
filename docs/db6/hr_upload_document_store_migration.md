# DB.6.3 migración upload HR a DocumentStore

## Baseline

Entorno:

- `DB_PROVIDER=json`
- Backend activo: `json`
- Errores de colección: `0`

Antes de modificar HR:

- HR upload characterization: `3 passed`
- Oracle/parity: `406 passed, 11 skipped, 39 deselected`
- Gate esperado heredado DB.6.2: `56 failed`, mismos node ids conocidos

Después de migrar HR:

- HR upload characterization: `3 passed`
- Uploads parametrización: `32 passed`
- DB: `36 passed, 12 skipped`
- Oracle/parity: `406 passed, 11 skipped, 39 deselected`
- Gate: `56 failed, 1308 passed, 46 skipped, 450 deselected, 1 xfailed`

Los 56 fallos son los mismos node ids de baseline. El incremento de passed viene de tests HR nuevos.

## Inventario dirigido HR

| Componente | Responsabilidad actual | Acceso a filesystem | Acción |
| ---------- | ---------------------- | ------------------- | ------ |
| `HRService` | Validar workbook, mapear payload HR y delegar persistencia | No | Migrado a inyección de `HRRepository` |
| `HRRepository` | Persistir versiones HR y actualizar índice | No directo; usa `DocumentStore` | Migrado a `StoredDocument` |
| `HRVersionDocumentCodec` | Separar `version_id` como id técnico y payload lógico | No | Usado en escritura HR |
| `VersionIndexRepository` | Encapsular `versions.json` | No directo cuando recibe `store + collection`; legacy cuando recibe `domain_dir` | Usado con `DocumentStore` preservando `versions.json` |
| `HRActiveParametrizationRepository` | Lectura activa HR para consumidores existentes | Solo fallback `active.path` legacy | No migrado en esta fase de upload |
| `HR API router` | Contrato HTTP público | No | Usa `HRService` desde container o override de test |
| `ApplicationContainer` | Wiring de dependencias | Construye store de parametrización existente | Agrega `HRRepository` y `HRService` con el mismo `parametrization_store` |

## Flujo HR

| Componente | Antes | Después |
| ---------- | ----- | ------- |
| Router | `_service = HRService()` global | `Depends` local obtiene `container.hr_upload_service`; `_service` queda solo como override temporal de tests |
| Service | Construía `HRRepository()` internamente | Recibe `HRRepository` por constructor |
| Repository | Heredaba `BaseRepository(HR_DIR)` | Recibe `DocumentStore`, `VersionIndexRepository`, `HRVersionDocumentCodec` |
| Payload | `write_json(hr/{version_id}.json, data)` vía base repo | `codec.encode(data)` + `DocumentStore.upsert_record()` |
| Índice | `VersionIndexRepository(domain_dir=HR_DIR)` | `VersionIndexRepository(store, collection)` + `VersionIndexDocumentCodec(record_id="versions")` |

## Persistencia

| Recurso | Metadata técnica | Payload lógico | Esquema preservado |
| ------- | ---------------- | -------------- | ------------------ |
| `hr/{version_id}.json` | `StoredDocument.id = payload["version_id"]` | Payload HR exacto (`version_id`, `niveles`, `salarios`, `nomina`, etc.) | Si, sin `id`, `domain`, `metadata`, `partition_value` |
| `hr/versions.json` | `StoredDocument.id = "versions"` | Lista legacy de summaries | Si, sigue siendo lista |

## Consistencia

| Escenario de fallo | Resultado | Compensación |
| ------------------ | --------- | ------------ |
| Falla al guardar payload | No se actualiza índice | No requiere compensación |
| Falla al actualizar índice con versión nueva | No queda archivo huérfano | Se elimina solo `hr/{version_id}.json` recién creado |
| Falla al actualizar índice con versión duplicada | No se borra payload preexistente | Se restaura el payload previo |
| Escritura exitosa con versión duplicada | Se preserva comportamiento legacy | Archivo queda con último payload; índice mantiene entradas duplicadas y última activa |

La compensación es best effort para JSON. Cosmos requerirá estrategia transaccional posterior si se activa.

## Legacy retirado

| Método legacy | Consumidores HR antes | Consumidores HR después |
| ------------- | --------------------- | ----------------------- |
| `BaseRepository.save_version()` | `HRRepository` heredado por upload HR | Ninguno |
| `BaseRepository.set_active()` | `HRService.activate()` vía `HRRepository` heredado | Ninguno; se usa `HRRepository.activate_version()` |
| `BaseRepository.delete_version()` | `HRService.delete()` vía `HRRepository` heredado | Ninguno; se usa `HRRepository.delete_version()` propio |

## Guardrails

Tests agregados:

- `tests/parametrizacion/uploads/test_hr_repository_document_store.py`
- `tests/parametrizacion/uploads/test_hr_guardrails.py`

Validan:

- `HRRepository` usa `HRVersionDocumentCodec`.
- `HRRepository` usa `DocumentStore.upsert_record()`.
- JSON HR no recibe `id`.
- `versions.json` conserva lista legacy.
- Versión duplicada preserva comportamiento.
- Falla de índice compensa archivo nuevo.
- Falla de índice restaura payload previo si era duplicado.
- Runtime HR no importa providers concretos ni factories.
- Repositorio HR no usa `BaseRepository`, `open()`, `json.dump` ni `write_text`.

## Validación

```text
HR upload characterization: 3 passed
Uploads parametrización:    32 passed
DB:                         36 passed, 12 skipped
Oracle:                     406 passed / delta 0
Gate:                       56 failed, 1308 passed, 46 skipped, 450 deselected, 1 xfailed
Collection errors:          0
Backend activo:             json
JSON HR con id nuevo:       no
BaseRepository.save_version consumers HR: 0
Accesos directos filesystem HR upload: 0
Acceso filesystem HR restante: HRActiveParametrizationRepository conserva fallback active.path legacy
```

## Siguiente fase: prompt OP

Migrar únicamente el upload OP verificando primero sus diferencias funcionales frente a GN y HR:

1. No tocar GN, HR ni Business Rules.
2. Congelar expected actuales de `tests/parametrizacion/uploads/test_op_upload_characterization.py`.
3. Inventariar estructura OP real: hojas, validaciones, comportamiento de `OP-LV`, `OP-ICA`, `OP-Poliza`, extensiones inválidas y workbook inválido.
4. Definir una constante de colección OP compatible con `storage/parametrization/op/{version_id}.json`.
5. Hacer que `OPRepository` reciba `DocumentStore`, `VersionIndexRepository` y `OPVersionDocumentCodec`.
6. Persistir payload OP con `OPVersionDocumentCodec.encode()` + `DocumentStore.upsert_record()`.
7. Persistir `op/versions.json` con `VersionIndexRepository(store, collection)` preservando lista legacy.
8. Mantener comportamiento de versión duplicada.
9. Agregar compensación: si falla índice, eliminar archivo nuevo o restaurar payload previo.
10. Ajustar `OPService` para recibir repository por constructor.
11. Ajustar router OP para obtener service desde container; `_service` solo como override temporal de tests si se conserva.
12. Agregar `OPRepository` y `OPService` al `ApplicationContainer` usando el mismo `parametrization_store`.
13. Mantener endpoint, HTTP payload, códigos y validaciones sin cambios.
14. Agregar guardrails OP equivalentes a GN/HR.
15. Validar upload OP, uploads completos, DB, parity y gate completo contra los mismos node ids baseline.
