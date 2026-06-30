# DB.6.1 contrato StoredDocument

## Baseline

Entorno:

- `DB_PROVIDER=json`
- Errores de colección: `0`
- Backend activo: `json`

Antes de cambios DB.6.1:

- Gate: `56 failed, 1276 passed, 46 skipped, 450 deselected, 1 xfailed`
- Oracle/parity: `406 passed, 11 skipped, 39 deselected`
- Tests de carga: `9 passed`

Despues de cambios DB.6.1:

- Gate: `56 failed, 1293 passed, 46 skipped, 450 deselected, 1 xfailed`
- Oracle/parity: `406 passed, 11 skipped, 39 deselected`
- DB + cargas focales: `53 passed, 12 skipped`
- StoredDocument/codecs focal: `26 passed`

## Inventario DocumentStore

| Consumidor | Metodo usado | Documento actual | Incluye id | Riesgo |
| ---------- | ------------ | ---------------- | ---------- | ------ |
| `ResultsRepository` | `upsert`, `get` | Resultado simulacion dict | Si | Bajo, legacy API intacta |
| `BusinessRulesRepository` | `get` | Business rules dict | Si en documento regular | Bajo, no migrado |
| `HRActiveParametrizationRepository` | `get` | Payload HR versionado | No en JSON logico historico | Medio, requiere codec antes de write |
| `GNActiveParametrizationRepository` | `get` | Payload GN versionado | No en JSON logico historico | Medio, requiere codec antes de write |
| `OPActiveParametrizationRepository` | `get` | Payload OP versionado | No en JSON logico historico | Medio, requiere codec antes de write |
| Tests `JsonDocumentStore` | `get/list/query/upsert` | Dict legacy con `id` | Si | Bajo, contrato legacy preservado |
| Tests/config `CosmosDocumentStore` | construccion diferida | Dict legacy con `id` | Si | Bajo, no activo con JSON |

## Contrato tecnico

| Componente | Responsabilidad |
| ---------- | --------------- |
| `StoredDocument` | Separar metadata tecnica (`id`, `partition_value`) del payload logico |
| `DocumentStore.get_record` | Leer payload logico y reconstruir metadata tecnica desde ubicacion/backend |
| `DocumentStore.list_records` | Listar records sin inyectar metadata en payload |
| `DocumentStore.query_records` | Filtrar contra payload logico de primer nivel |
| `DocumentStore.upsert_record` | Persistir payload usando `record.id` como metadata de ubicacion |
| API legacy `get/list/query/upsert` | Compatibilidad temporal con documentos dict que contienen `id` |

## Proveedores

| Proveedor | Metadata tecnica | Payload logico | Estado |
| -------- | ---------------- | -------------- | ------ |
| `JsonDocumentStore` | `record.id` define `{collection}/{id}.json`; `partition_value` no se escribe | Se escribe exactamente como JSON del archivo | Implementado |
| `CosmosDocumentStore` | `id` y partition se guardan en envelope tecnico | Payload se guarda bajo `payload` | Preparado, no activo |

## Codecs

| Dominio | Codec | ID tecnico | Payload preservado |
| ------- | ----- | ---------- | ------------------ |
| GN | `GNVersionDocumentCodec` | `payload["version_id"]` | Si |
| HR | `HRVersionDocumentCodec` | `payload["version_id"]` | Si |
| OP | `OPVersionDocumentCodec` | `payload["version_id"]` | Si |
| Índice de versiones | `VersionIndexDocumentCodec` | `{domain}-versions-index` | Si, conserva lista legacy |

## Tests

| Suite | Casos | Resultado |
| ----- | ----- | --------- |
| `tests/db/contract/test_stored_document_contract.py` | API de registros JSON, ida y vuelta, sin metadata, config Cosmos | Pasó |
| `tests/db/contract/test_stored_document_guardrails.py` | Codecs sin providers, JSON store sin metadata tecnica en payload | Pasó |
| `tests/parametrizacion/uploads/test_document_codecs.py` | Codecs GN/HR/OP/índice de versiones | Pasó |
| `tests/parametrizacion/uploads` | Caracterización de carga GN/HR/OP | Pasó |
| `tests/parity` | Oracle/parity | `406 passed` |

## Validacion

```text
Gate:                         56 failed, mismos node ids baseline
Oracle:                       406 passed / delta 0
Errores de colección:         0
Backend activo:               json
Tests de carga:               9 passed
JSON con campos tecnicos nuevos: no
```

## Siguiente fase: prompt GN

Migrar unicamente upload GN a `DocumentStore` usando `StoredDocument`:

1. No tocar HR/OP.
2. No cambiar endpoints ni HTTP.
3. No agregar `id` al JSON `gn/{version_id}.json`.
4. Usar `GNVersionDocumentCodec` para version payload.
5. Mantener `VersionIndexRepository` encapsulando `versions.json` sin cambiar lista legacy.
6. Reemplazar en flujo GN la escritura de payload por `DocumentStore.upsert_record`.
7. Ejecutar:
   - `tests/parametrizacion/uploads/test_gn_upload_characterization.py`
   - `tests/parametrizacion/uploads`
   - `tests/db`
   - `tests/parity`
   - gate completo
8. Comparar node ids contra baseline de 56 failures.
