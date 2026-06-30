# Cosmos Readiness — NEXA Pricing Engine

**Última actualización:** 2026-06-04 (FASE DB.6.8)
**Estado arquitectónico:** JSON activo · Cosmos preparado · DocumentStore contrato único

---

## Estado actual

| Componente | Estado | Notas |
|---|:---:|---|
| Backend activo | JSON | `DB_PROVIDER=json` (default) |
| `DocumentStore` como contrato único | ✅ | Abstracción técnica única de persistencia |
| GN upload → DocumentStore | ✅ | Migrado en DB.6.x |
| HR upload → DocumentStore | ✅ | Migrado en DB.6.x |
| OP upload → DocumentStore | ✅ | Migrado en DB.6.x |
| `CosmosDocumentStore` contrato completo | ✅ | Todos los 9 métodos implementados |
| `BaseRepository` como clase | ❌ eliminado | Retirado en DB.6.5 |
| P.8 port (`ParametrizationRepositoryPort`) | ❌ eliminado | Retirado en DB.6.7 |
| Providers paralelos (`JsonParametrizationRepository`, `CosmosParametrizationRepository`) | ❌ eliminados | Retirados en DB.6.7 |
| Cosmos auto-inicialización con `DB_PROVIDER=json` | ❌ NO ocurre | Lazy import verificado |
| Credenciales hardcodeadas | ❌ ninguna | Solo variables de entorno |

---

## Variables de entorno requeridas

### Backend JSON (default, development/test)

```env
DB_PROVIDER=json
# Opcional en development (default: <repo_root>/storage)
# Obligatorio en production:
JSON_STORAGE_PATH=/data/nexa/storage
```

### Backend Cosmos (production future)

```env
DB_PROVIDER=cosmos
COSMOS_ENDPOINT=https://<account>.documents.azure.com:443/
COSMOS_KEY=<primary-or-secondary-key>
COSMOS_DATABASE=nexa_pricing          # default
COSMOS_CONTAINER=parametrization      # default
```

> **Seguridad**: Nunca commitear `COSMOS_KEY`. Usar Azure Key Vault o equivalente en producción.

Si `DB_PROVIDER=cosmos` pero faltan `COSMOS_ENDPOINT` o `COSMOS_KEY`, el sistema falla en el arranque con `DbConfigurationError` — comportamiento intencional (fail-fast).

---

## Colecciones de dominio

| Colección | Owner | `CollectionConfig` | Partition key | Estado Cosmos |
|---|---|:---:|:---:|:---:|
| `simulation_results` | `calculator/persistence/results_repository.py` | ✅ | ninguna | READY |
| `gn` | `parametrizacion/gn/repositories/collections.py` | ✅ | ninguna | READY |
| `hr` | `parametrizacion/hr/repositories/collections.py` | ✅ | ninguna | READY |
| `op` | `parametrizacion/op/repositories/collections.py` | ✅ | ninguna | READY |
| `business_rules` | `parametrizacion/business_rules/repositories/` | ✅ | ninguna | READY |
| `versions` (índice) | `parametrizacion/shared/repositories/version_index_repository.py` | implícita | ninguna | READY |

> **Nota sobre partition keys**: Ninguna colección de producción usa `partition_key_field` actualmente. El `CosmosDocumentStore` soporta particiones, pero no se han definido partition keys para ningún dominio. Definir partition keys para Cosmos es parte del plan de migración (DB.6.9).

---

## `DocumentStore` — Contrato y providers

### Métodos del contrato (`db/ports/document_store.py`)

| Método | JSON | Cosmos | Notas |
|---|:---:|:---:|---|
| `get_record` | ✅ | ✅ | API principal — no inyecta `id` en payload |
| `list_records` | ✅ | ✅ | Con paginación |
| `query_records` | ✅ | ✅ | Filtros AND de igualdad |
| `upsert_record` | ✅ | ✅ | Crea o reemplaza |
| `delete` | ✅ | ✅ | Lanza `DbNotFoundError` si no existe |
| `get` | ✅ | ✅ | API legacy (payload con `id`) |
| `list` | ✅ | ✅ | API legacy |
| `query` | ✅ | ✅ | API legacy |
| `upsert` | ✅ | ✅ | API legacy |
| `upsert_records_atomic` | ❌ N/A | ✅ | Cosmos-only (batch transaccional) |

### `StoredDocument` — Separación metadata / payload

```python
StoredDocument(
    id="version-uuid",          # ← metadata técnica: nombre del documento
    payload={...},              # ← payload lógico puro: GN/HR/OP JSON
    partition_value=None,       # ← metadata técnica: partition para Cosmos
    etag=None,                  # ← metadata técnica: optimistic concurrency
)
```

El `id` **nunca se escribe dentro del `payload`**. El JSON lógico persiste limpio.

---

## Factories y composition root

| Función | Retorna | Consumers legítimos | Acción si se encuentra en routers/services |
|---|---|---|---|
| `db/factory.get_provider()` | `DocumentStore` (raíz `storage/`) | `db/container.py`, `db/dependencies.py`, módulos legacy de resultados | Deuda DT-router — migrar a `db/dependencies.py` |
| `db/factory.get_parametrization_store()` | `DocumentStore` (raíz `storage/parametrization/`) | `db/container.py`, `parametrizacion/services/resolver.py` (fallback), `parametrizacion/mixins/provider_business_rules.py` (fallback), `modules/panel/services/panel_service.py` (legacy) | Aceptado como composition root helper; no crear nuevos consumidores fuera del container |

### Deuda conocida (DT-router)

Los siguientes módulos llaman `get_provider()` al nivel de módulo (inicialización), no dentro del container:
- `modules/calculator/api/results_router.py`
- `modules/calculator/api/calculate_dependencies.py`
- `modules/vision_*/api/router.py` (5 routers)
- `modules/pyg/api/vision_router.py`
- `modules/vision_imprimible/api/router.py`

Estos son patrones legacy pre-DI aceptados temporalmente. Se deben migrar a `db/dependencies.py` en la fase DT-router.

---

## Tests contractuales

| Suite | Archivo | Cosmos cubierto |
|---|---|:---:|
| Contract (JSON + Cosmos) | `tests/db/contract/test_document_store_contract.py` | ✅ (skip si sin credenciales) |
| Cosmos batch/atomic | `tests/db/unit/test_cosmos_document_store_skeleton.py` | ✅ (mock SDK) |
| Cosmos SDK compat | `tests/db/unit/test_cosmos_sdk_contract.py` | ✅ (autospec) |
| Factory isolation | `tests/db/unit/test_config_and_factory.py` | ✅ incl. lazy import, DbConnectionError |
| StoredDocument guardrails | `tests/db/contract/test_stored_document_guardrails.py` | ✅ |

---

## Limitaciones actuales

1. **Sin dual-write** — no existe ruta de escritura simultánea JSON+Cosmos.
2. **Sin activación automática** — cambiar `DB_PROVIDER=cosmos` requiere que los datos ya estén en Cosmos.
3. **Sin migración de datos** — el plan de migración JSON→Cosmos aún no está implementado.
4. **Partition keys no definidas** — ninguna colección tiene `partition_key_field`. Definirlas es prerrequisito de migración.
5. **Routers legacy** — 15 routers usan `get_provider()` directamente en lugar de `db/dependencies.py` (deuda DT-router).

---

## Procedimiento futuro de activación (DB.6.9)

1. **Definir partition keys** para cada colección de dominio.
2. **Migrar datos** de JSON a Cosmos con un script de migración atómica.
3. **Ejecutar tests contractuales** con credenciales reales en entorno aislado.
4. **Verificar hashes** de payloads JSON vs Cosmos para confirmar integridad.
5. **Smoke test** con subset de simulaciones productivas.
6. **Cambiar variable** `DB_PROVIDER=cosmos` con rollback plan.
7. **Monitorear** errores en las primeras 24h.
8. **Retirar fallback JSON** después de confirmación estable.

---

## Guardrails activos

Los siguientes tests fallan si se violan las invariantes de persistencia:

| Guardrail | Archivo |
|---|---|
| `precision.py` y `calculators.py` intactos | `tests/unit/test_shared_guardrails.py` |
| `shared/infrastructure/storage/` no existe | Idem |
| `BaseRepository` no reaparece | Idem |
| `JsonParametrizationRepository` y `CosmosParametrizationRepository` no existen | Idem |
| Repos paralelos no existen | Idem |
| Cero imports runtime a `shared.infrastructure.storage` | Idem |
| `parametrizacion` no importa `db.providers` directamente | Idem |
| Cosmos no importado con `DB_PROVIDER=json` | `tests/db/unit/test_config_and_factory.py` |
| `CosmosDocumentStore(None)` lanza `DbConnectionError` | Idem |
| `get_parametrization_store()` retorna `DocumentStore` | Idem |
