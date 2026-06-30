# DB.7.2 concurrencia optimista para `versions`

## Objetivo

Evitar lost updates concurrentes sobre el índice legacy `versions` en la ruta
Cosmos, sin alterar el comportamiento certificado de JSON ni los contratos HTTP
de uploads GN, HR y OP.

## Contrato agregado

### Metadata técnica en `StoredDocument`

```python
StoredDocument(
    id="versions",
    payload=[...],
    partition_value="gn",
    etag="etag-actual",
)
```

`etag` es metadata del provider. No se serializa dentro del payload lógico.

### Precondición atómica

```python
AtomicWritePrecondition(
    logical_id="versions",
    expected_etag="etag-actual",
)
```

`AtomicDocumentStore.upsert_records_atomic()` acepta una precondición opcional
que aplica al registro lógico protegido, normalmente `versions`.

## Flujo Cosmos

1. `VersionIndexRepository` lee `versions` con `get_record()`.
2. El adapter Cosmos devuelve `_etag` como `StoredDocument.etag`.
3. `VersionIndexRepository.build_append_record()` construye el nuevo índice y
   conserva el ETag leído como metadata técnica.
4. `save_version_payload_and_index()` crea `AtomicWritePrecondition` si el
   registro del índice trae ETag.
5. `CosmosDocumentStore.upsert_records_atomic()` escribe payload + índice en un
   transactional batch.
6. La operación del índice usa `if-match` con el ETag esperado.
7. Si el ETag cambió, Cosmos rechaza el batch y se lanza `DbConcurrencyError`.

## Política de conflicto

| Decisión | Estado |
| -------- | ------ |
| Reintento silencioso dentro del repository | No permitido |
| Excepción propia | `DbConcurrencyError` |
| Cambios parciales ante conflicto | No permitidos |
| Reintento permitido | Solo capa superior, repitiendo la operación completa |

La capa superior puede decidir reintentar leyendo de nuevo el índice, regenerando
el payload y ejecutando el upload completo otra vez.

## JSON

JSON no expone ETag y mantiene el comportamiento actual:

- `StoredDocument.etag = None`
- No se crea precondición.
- Si el store no implementa `AtomicDocumentStore`, se conserva compensación
  best effort.
- `versions.json` sigue siendo una lista legacy.

## Tests DB.7.2

Cobertura Cosmos fake:

- batch exitoso con ETag vigente
- batch rechazado con ETag obsoleto
- ningún cambio parcial cuando falla la precondición
- payload lógico no contiene `_etag`, `_pk` ni `id`

Cobertura transversal GN/HR/OP:

- ruta atómica recibe payload + índice en un batch
- JSON conserva compensación actual
- duplicados mantienen orden legacy
- dos cargas concurrentes con índice obsoleto no pierden entradas
- payload lógico sigue sin metadata técnica

## Validación ejecutada

```text
Cosmos skeleton:           8 passed
Certificación transversal: 33 passed
Uploads parametrización:   73 passed
DB:                        44 passed, 12 skipped
Oracle/parity:             406 passed, 11 skipped, 39 deselected
Gate completo:             56 failed, 1364 passed, 46 skipped, 450 deselected, 1 xfailed
```

Comparación de fallos contra baseline:

```text
expected=56 actual=56
new_failures=0
missing_baseline_failures=0
```

## Riesgos pendientes

| Riesgo | Estado | Siguiente paso |
| ------ | ------ | -------------- |
| Cosmos real no probado | Sin cuenta configurada | Prueba integración opcional con cuenta efímera |
| Sintaxis exacta SDK para `match_condition` | Cubierta por fake, no por SDK real | Validar contra `azure-cosmos` real antes de activar provider |
| Política de retry HTTP | Fuera de DB.7.2 | Definir en capa API/servicio una fase posterior |
| `_service` temporal | Sigue en routers | Retirar con overrides FastAPI/container |
| `active.path` | Sigue como fallback legacy | Auditar índices productivos antes de eliminar |

## Criterio de cierre

DB.7.2 queda cerrado porque la ruta Cosmos preparada detecta y rechaza lost
updates sobre `versions` mediante ETag, mientras JSON conserva exactamente su
comportamiento certificado.
