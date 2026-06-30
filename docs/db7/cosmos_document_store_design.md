# DB.7.0 diseño Cosmos DB para DocumentStore

## Objetivo

Preparar el adapter Cosmos DB para preservar el comportamiento certificado de
uploads GN, HR y OP sobre `DocumentStore`, sin cambiar el adapter activo, sin
pedir credenciales y sin tocar contratos HTTP, payloads JSON de negocio ni
archivos Oracle-sensitive.

## Estado de activación

| Elemento | Estado |
| -------- | ------ |
| Provider por defecto | `json` |
| Provider Cosmos | Preparado, no activo |
| Requiere credenciales en modo JSON | No |
| Conexión real a Cosmos en DB.7.0 | No |
| Cambio de contratos HTTP | No |
| Cambio de payload lógico GN/HR/OP | No |

## Configuración

| Variable | Default | Uso |
| -------- | ------- | --- |
| `DB_PROVIDER` | `json` | Selecciona `json` o `cosmos` |
| `JSON_STORAGE_PATH` | `storage` | Raíz filesystem del provider JSON |
| `COSMOS_ENDPOINT` | sin default | Requerido solo si `DB_PROVIDER=cosmos` |
| `COSMOS_KEY` | sin default | Requerido solo si `DB_PROVIDER=cosmos` |
| `COSMOS_DATABASE` | sin default | Requerido solo si `DB_PROVIDER=cosmos` |
| `COSMOS_CONTAINER` | sin default | Requerido solo si `DB_PROVIDER=cosmos` |

`db.factory.build_provider()` mantiene import diferido de `azure-cosmos`: con
`DB_PROVIDER=json` no importa el paquete ni exige configuración Cosmos.

## Modelo Cosmos propuesto

### Database

Base sugerida:

```text
nexa_pricing_db
```

El nombre final queda por entorno mediante `COSMOS_DATABASE`.

### Container

Container sugerido para parametrización:

```text
parametrization
```

El nombre final queda por entorno mediante `COSMOS_CONTAINER`.

### Partition key

Para `StoredDocument` de parametrización:

```text
/_pk
```

Valor:

```text
{collection.name}
```

Ejemplos:

| Dominio | Collection | Partition key |
| ------- | ---------- | ------------- |
| GN | `gn` | `gn` |
| HR | `hr` | `hr` |
| OP | `op` | `op` |

Esta decisión garantiza que el payload de versión y el índice `versions` del
mismo dominio compartan partición y puedan escribirse con transactional batch.

## Estructura de documentos

### Documento técnico Cosmos para payload GN

```json
{
  "id": "gn:gn-v1",
  "_collection": "gn",
  "_logical_id": "gn-v1",
  "_kind": "stored_document",
  "_pk": "gn",
  "payload": {
    "version_id": "gn-v1",
    "lv": {},
    "sheets": []
  }
}
```

### Documento técnico Cosmos para payload HR

```json
{
  "id": "hr:hr-v1",
  "_collection": "hr",
  "_logical_id": "hr-v1",
  "_kind": "stored_document",
  "_pk": "hr",
  "payload": {
    "version_id": "hr-v1",
    "niveles": {},
    "salarios": [],
    "nomina": [],
    "recargos": [],
    "seg_social": [],
    "prestaciones": [],
    "ratios": [],
    "rentabilidad": [],
    "campana": [],
    "costo_fijo": [],
    "med_seg": [],
    "extra_sheets": {}
  }
}
```

### Documento técnico Cosmos para payload OP

```json
{
  "id": "op:op-v1",
  "_collection": "op",
  "_logical_id": "op-v1",
  "_kind": "stored_document",
  "_pk": "op",
  "payload": {
    "version_id": "op-v1",
    "sheets": []
  }
}
```

### Documento técnico Cosmos para índice legacy

```json
{
  "id": "gn:versions",
  "_collection": "gn",
  "_logical_id": "versions",
  "_kind": "stored_document",
  "_pk": "gn",
  "payload": [
    {
      "version_id": "gn-v1",
      "filename": "GN.xlsx",
      "uploaded_at": "2026-06-04T00:00:00Z",
      "is_active": true,
      "sheet_count": 1,
      "total_rows": 1
    }
  ]
}
```

El índice conserva el contrato legacy de `versions.json`: el payload lógico es
una lista, no un objeto, y no recibe `id` técnico.

## IDs técnicos

| Campo | Propósito | Visible en payload lógico |
| ----- | --------- | ------------------------- |
| `id` | Id técnico Cosmos `{collection}:{logical_id}` | No |
| `_collection` | Colección lógica (`gn`, `hr`, `op`) | No |
| `_logical_id` | Id usado por `StoredDocument.id` | No |
| `_kind` | Tipo técnico del documento | No |
| `_pk` | Partition key técnica | No |
| `payload` | Payload lógico certificado | Si, como contenido retornado por `get_record()` |

## Interfaz atómica

Se agregó un puerto opcional:

```python
AtomicDocumentStore.upsert_records_atomic(collection, records, partition_value=None)
```

No amplía ni rompe `DocumentStore`. JSON puede seguir usando compensación best
effort; Cosmos expone esta capacidad cuando el repositorio decida usarla.

Uso esperado para uploads:

```text
records = [
  StoredDocument(id=version_id, payload=payload_logico),
  StoredDocument(id="versions", payload=versions_legacy),
]
store.upsert_records_atomic(collection, records)
```

Ambos registros resuelven `_pk = collection.name`, por lo que Cosmos puede
ejecutar `create_transactional_batch(partition_key=collection.name)`.

## Atomicidad

| Caso | JSON actual | Cosmos DB.7.0 |
| ---- | ----------- | ------------- |
| Payload nuevo + índice exitosos | Dos escrituras secuenciales | Un transactional batch |
| Falla después del payload nuevo | Compensación elimina payload nuevo | Cosmos no confirma ningún documento |
| Falla con payload previo existente | Compensación restaura payload previo | Cosmos conserva estado previo |
| Duplicado de versión | Payload reemplazado, índice lista entradas duplicadas | Mismo resultado en batch |

## Tests DB.7.0 sin cuenta real

Archivo:

- `tests/db/unit/test_cosmos_document_store_skeleton.py`

Cobertura:

- `upsert_record()`
- `get_record()`
- `delete()`
- payload lógico sin `id`
- documento técnico con `id` prefijado por colección
- transactional batch payload + índice
- duplicate version contract
- rollback completo cuando falla batch nuevo
- preservación de estado previo cuando falla batch de reemplazo

## Validación ejecutada

```text
Focal Cosmos/config/stored-doc: 24 passed
DB completo:                  42 passed, 12 skipped
Uploads parametrización:      61 passed
Oracle/parity:                406 passed, 11 skipped, 39 deselected
Gate completo:                56 failed, 1350 passed, 46 skipped, 450 deselected, 1 xfailed
```

Comparación de fallos contra baseline:

```text
expected=56 actual=56
new_failures=0
missing_baseline_failures=0
```

## Riesgos y decisiones pendientes

| Riesgo | Decisión actual | Siguiente acción |
| ------ | --------------- | ---------------- |
| Cosmos real no probado | No conectar en DB.7.0 | Agregar pruebas de integración opcionales con cuenta efímera |
| Repositorios GN/HR/OP aún usan compensación JSON | Mantener para no tocar comportamiento certificado | Fase posterior: adaptar repositorios para usar `AtomicDocumentStore` si disponible |
| Un solo container vs containers por dominio | Diseño favorece un container `parametrization` con `_pk=dominio` | Confirmar costos/RU y política de retención |
| Legacy dict API de `DocumentStore` | Se mantiene por compatibilidad | No usarla para uploads parametrización |
| Secrets Cosmos | No se loguean valores | Validar integración con secret manager en fase infra |

## Criterio de cierre DB.7.0

El diseño demuestra que Cosmos puede preservar el comportamiento certificado de
GN/HR/OP porque:

- El payload lógico sigue aislado en `payload`.
- El `id` técnico nunca entra al payload lógico.
- El índice legacy se conserva como lista.
- Payload e índice comparten partición.
- El batch transaccional evita estados intermedios.
- JSON sigue siendo el provider por defecto.
