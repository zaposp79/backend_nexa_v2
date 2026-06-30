# DB.9.0 Cosmos Controlled Integration

Fecha: 2026-06-05
Branch: `refactor/modular-pure`

## Alcance

DB.9.0 prepara una integracion controlada de `CosmosDocumentStore` con el SDK
real de Azure Cosmos. JSON sigue siendo el provider default y Cosmos no se
activa por defecto.

No se modifico logica de calculo, contratos HTTP, payloads JSON legacy ni
fallback JSON. No se declara certificacion Cosmos real sin endpoint/credenciales
o emulador disponible.

## Configuracion Cosmos

Para ejecutar la integracion real se requieren variables explicitas:

```bash
export DB_PROVIDER=cosmos
export COSMOS_ENDPOINT="https://<account>.documents.azure.com:443/"
export COSMOS_KEY="<primary-or-secondary-key>"
export COSMOS_DATABASE="nexa_pricing_smoke"
export COSMOS_CONTAINER="parametrization_smoke"
```

Ejecutar solo contra base/container aislados. No usar contenedores productivos.

Comando de integracion real:

```bash
PYTHONPATH=/Users/darwin.minota.quinto/Projects/NEXA \
  venv_py312_backup_20260604_165827/bin/python \
  -m pytest tests/db/smoke/test_cosmos_parametrization_smoke.py \
  -m cosmos_integration -q --tb=short
```

El marker `cosmos_integration` queda excluido del default en `pytest.ini`.

## Cambios

- `pytest.ini` registra `cosmos_integration` y lo excluye del gate default.
- `tests/db/smoke/test_cosmos_parametrization_smoke.py` agrega pruebas reales
  marcadas para:
  - `upsert_record`;
  - `get_record`;
  - `delete`;
  - `upsert_records_atomic`;
  - payload + `versions` en transactional batch;
  - conflicto ETag mediante `AtomicWritePrecondition`;
  - particiones por dominio: `gn`, `hr`, `op`, `business_rules`;
  - ausencia de metadata tecnica (`id`, `_pk`, `_etag`) dentro del payload.
- `db/providers/cosmos_document_store.py` mapea `CosmosBatchOperationError`
  del SDK real a `DbConcurrencyError` cuando el batch falla por ETag.
- `tests/db/unit/test_cosmos_sdk_contract.py` cubre la firma real del SDK y el
  mapeo de `CosmosBatchOperationError`.

## SDK real

SDK instalado:

```text
azure-cosmos==4.16.1
azure-core==1.41.0
```

Contrato SDK ejecutado con 0 skipped:

```text
tests/db/unit/test_cosmos_sdk_contract.py
5 passed
```

El contrato confirma:

- major version SDK `4`;
- `ContainerProxy.execute_item_batch(batch_operations, partition_key, ...)`;
- operaciones `upsert` con `if_match_etag`;
- mapeo de `CosmosHttpResponseError(412)` a `DbConcurrencyError`;
- mapeo de `CosmosBatchOperationError(412)` a `DbConcurrencyError`.

## Integracion real

Estado local:

```text
COSMOS_ENDPOINT/COSMOS_KEY no configurados
```

Resultado:

```text
tests/db/smoke/test_cosmos_parametrization_smoke.py -m cosmos_integration
14 skipped
```

Por falta de credenciales/emulador, no se ejecutaron operaciones reales contra
Cosmos. Por tanto, transactional batch real y ETag real quedan pendientes.

## JSON default

Validaciones default:

```text
tests/db
59 passed, 12 skipped, 14 deselected
```

Los 14 `deselected` corresponden a `cosmos_integration`; JSON sigue siendo
default y no requiere credenciales Cosmos.

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

Baseline oficial:

```text
48 failed, 1623 passed, 54 skipped, 450 deselected, 1 xfailed
```

Gate actual DB.9.0:

```text
48 failed, 1655 passed, 46 skipped, 464 deselected, 1 xfailed
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

DB.9.0 queda en estado **Cosmos preparado, certificacion real bloqueada**.

El SDK real esta instalado y validado con contrato local. Los tests de
integracion real existen, estan marcados, quedan fuera del default y cubren
CRUD, transactional batch, ETag, particiones y no filtrado de metadata tecnica
al payload.

No se puede declarar Cosmos certificado porque no hay `COSMOS_ENDPOINT` ni
`COSMOS_KEY` configurados para ejecutar contra Cosmos real o emulador.

JSON permanece como default y el gate no introduce fallos nuevos frente al
baseline oficial.
