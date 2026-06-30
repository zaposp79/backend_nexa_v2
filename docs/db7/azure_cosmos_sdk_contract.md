# DB.7.3 contrato SDK `azure-cosmos`

## Objetivo

Validar, sin red y sin cuenta Cosmos, que `CosmosDocumentStore` construye
llamadas compatibles con el SDK real `azure-cosmos` antes de activar el provider.

## Estado del entorno

El entorno local usado en DB.7.3 no tiene instalado `azure-cosmos`:

```text
Package(s) not found: azure-cosmos
```

Por eso los tests de contrato real del SDK quedan como `skipped` explícitos
hasta instalar la dependencia. JSON sigue siendo provider default y no requiere
el paquete.

## Versión soportada

Rango fijado en `requirements.txt`:

```text
azure-cosmos>=4.5,<5
```

Motivo:

- DB.7.x está diseñado contra la familia 4.x del SDK.
- Un salto a 5.x debe fallar/revisarse antes de activar Cosmos.

## Firma SDK esperada

Cuando `azure-cosmos` está instalado, el test inspecciona:

```python
azure.cosmos.container.ContainerProxy.execute_item_batch
```

Y exige los parámetros:

```text
batch_operations
partition_key
```

`CosmosDocumentStore` envía:

```python
container.execute_item_batch(
    batch_operations=[
        ("upsert", (payload_item,), {}),
        ("upsert", (versions_item,), {"if_match_etag": expected_etag}),
    ],
    partition_key="gn",
)
```

La operación con precondición se aplica solo al documento lógico `versions`.

## ETag y match condition

La ruta DB.7.3 usa para batch:

```text
if_match_etag
```

No se inserta `_etag` en el payload lógico. `_etag` solo viaja como metadata de
`StoredDocument`.

## Mapeo de errores

| Cosmos | Condición | Error NEXA |
| ------ | --------- | ---------- |
| `CosmosHttpResponseError.status_code == 412` | ETag obsoleto / precondition failed | `DbConcurrencyError` |
| Otro `CosmosHttpResponseError` | Falla de backend | `DbConnectionError` |
| Batch response con operación `412` | Precondition failed en batch | `DbConcurrencyError` |

## Tests agregados

Archivo:

- `tests/db/unit/test_cosmos_sdk_contract.py`

Cobertura cuando el SDK está instalado:

- versión major `4`
- firma de `ContainerProxy.execute_item_batch`
- llamada con `autospec`, sin red
- operaciones `upsert`
- `if_match_etag` aplicado al índice `versions`
- error 412 traducido a `DbConcurrencyError`

Cobertura cuando el SDK no está instalado:

- tests saltan explícitamente
- JSON/fakes siguen ejecutándose
- no se requieren credenciales ni conexión

## Validación DB.7.3

```text
Contrato SDK + skeleton:     9 passed, 4 skipped
Certificación transversal:   33 passed
Uploads parametrización:     73 passed
DB:                          45 passed, 16 skipped
Oracle/parity:               406 passed, 11 skipped, 39 deselected
Gate completo:               56 failed, 1365 passed, 50 skipped, 450 deselected, 1 xfailed
```

Los `4 skipped` corresponden a ausencia local de `azure-cosmos`.

Comparación de fallos contra baseline:

```text
expected=56 actual=56
new_failures=0
missing_baseline_failures=0
```

## Riesgos pendientes

| Riesgo | Estado | Mitigación |
| ------ | ------ | ---------- |
| SDK no instalado localmente | Tests reales skipped | Instalar `azure-cosmos>=4.5,<5` en CI antes de activar Cosmos |
| Firma exacta validada solo cuando SDK está presente | Pendiente CI | Gate debe incluir `test_cosmos_sdk_contract.py` con SDK instalado |
| Cuenta Cosmos real no probada | Fuera de DB.7.3 | Fase de integración con cuenta efímera |
| Semántica real de RU/latencia | No medida | Pruebas integración/performance |

## Criterio de cierre

DB.7.3 deja el contrato listo para fallar temprano cuando el SDK esté instalado.
En este entorno no se puede afirmar compatibilidad con una versión instalada
porque el paquete no existe; sí queda protegido que:

- JSON no depende del SDK;
- el rango soportado está fijado;
- la ruta con `execute_item_batch` está cubierta por fake funcional;
- el test con `autospec` validará firma real en CI o ambiente con SDK.
