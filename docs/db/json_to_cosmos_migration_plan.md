# Plan de Migración JSON → Cosmos

**Versión:** 1.0 (FASE DB.6.9)
**Fecha:** 2026-06-04
**Estado:** PREPARADO — Cosmos NO activo

---

## Precondiciones

Antes de ejecutar la migración real (modo `--execute`):

| Precondición | Estado |
|---|:---:|
| GN/HR/OP usan `DocumentStore` | ✅ |
| `BaseRepository` eliminado | ✅ |
| Providers paralelos eliminados | ✅ |
| `CosmosDocumentStore` implementa contrato completo | ✅ |
| Dry-run exitoso (14 docs, all_hashes_match=True) | ✅ |
| DT-router deuda documentada | ⚠️ ver sección DT-router |
| Partition keys definidas | ✅ ver sección partition keys |
| Credenciales Cosmos en entorno AISLADO | ⏳ a configurar |
| Smoke test Cosmos pasando | ⏳ requiere credenciales |
| Validación de hashes completa | ⏳ tras smoke test |

---

## Variables de entorno requeridas para ejecución

```env
# Backend (NO cambiar en producción hasta completar smoke test)
DB_PROVIDER=cosmos

# Cosmos (solo en el entorno de migración aislado)
COSMOS_ENDPOINT=https://<account>.documents.azure.com:443/
COSMOS_KEY=<primary-or-secondary-key>
COSMOS_DATABASE=nexa_pricing
COSMOS_CONTAINER=parametrization

# Para smoke test usar base de datos aislada:
COSMOS_DATABASE=nexa_pricing_smoke_test
COSMOS_CONTAINER=parametrization_smoke
```

---

## Colecciones en alcance

| Colección | Owner | Storage JSON | Documentos actuales | Estado |
|---|---|---|:---:|:---:|
| `gn` | `parametrizacion/gn` | `storage/parametrization/gn/` | 3 | `MIGRATE_READY` |
| `hr` | `parametrizacion/hr` | `storage/parametrization/hr/` | 4 | `MIGRATE_READY` |
| `op` | `parametrizacion/op` | `storage/parametrization/op/` | 7 | `MIGRATE_READY` |
| `business_rules` | `parametrizacion/br` | `storage/parametrization/business_rules/` | 3 | `MIGRATE_READY` |
| `simulation_results` | `calculator` | `storage/simulation_results/` | 18 | `MIGRATE_READY` |

## Colecciones fuera de alcance

| Colección | Motivo | Estado |
|---|---|:---:|
| `snapshots` | Filesystem path-based; 2 archivos por simulación (snapshot.json + summary.json) | `NOT_APPLICABLE` |
| `lineage` | Filesystem path-based; 2500+ archivos por simulación | `NOT_APPLICABLE` |
| `certificates` | Filesystem path-based con index.json; requiere refactoring mayor | `NOT_APPLICABLE` |

> Estas colecciones requieren una fase de refactoring independiente antes de poder migrarse a Cosmos.

---

## Partition keys

| Colección | Partition key propuesta | Evidencia | Riesgo | Estado |
|---|---|---|---|:---:|
| `gn` | Sin partition key | Colección pequeña (≤100 docs); partition key añadiría complejidad sin beneficio | Bajo | `READY_NO_PK` |
| `hr` | Sin partition key | Idem | Bajo | `READY_NO_PK` |
| `op` | Sin partition key | Idem | Bajo | `READY_NO_PK` |
| `business_rules` | Sin partition key | Idem | Bajo | `READY_NO_PK` |
| `simulation_results` | `simulation_id` (primeros 8 chars) | Colección puede crecer; partition por prefijo de UUID es patrón estándar | Medio | `POSTPONE_DEFINE_BEFORE_EXECUTE` |

> **Nota sobre `simulation_results`**: Definir partition key antes de ejecutar migración para esta colección. Las demás pueden migrar sin partition key inicialmente.

---

## DT-router — Estado antes de activación

Los siguientes routers llaman `get_provider()` a nivel de módulo (inicialización). Con JSON backend esto es benigno. Con Cosmos backend, si las credenciales cambian post-boot, el store no se re-inicializa.

| Router | Línea | Riesgo Cosmos | Acción recomendada |
|---|:---:|---|---|
| `calculator/api/results_router.py` | 49 | Medio | `MIGRATE_TO_DEPENDS` (DB.7) |
| `calculator/api/calculate_dependencies.py` | 16 | Medio | `MIGRATE_TO_DEPENDS` (DB.7) |
| `vision_cost_to_serve/api/router.py` | 15 | Medio | `MIGRATE_TO_DEPENDS` (DB.7) |
| `vision_pyg/api/router.py` | 36 | Medio | `MIGRATE_TO_DEPENDS` (DB.7) |
| `pyg/api/vision_router.py` | 36 | Medio | `MIGRATE_TO_DEPENDS` (DB.7) |
| `vision_tarifas/api/router.py` | 15 | Medio | `MIGRATE_TO_DEPENDS` (DB.7) |
| `vision_imprimible/api/router.py` | 18 | Medio | `MIGRATE_TO_DEPENDS` (DB.7) |

**Decisión para activación de Cosmos:**

Estos routers usan `get_provider()` una vez en startup, luego el store queda cacheado. Si Cosmos está configurado con credenciales válidas en el arranque, el riesgo es bajo para una instancia de larga vida. Para deploys con rolling restarts o cambios de credenciales, el riesgo es medio.

**Criterio**: No bloquean el smoke test. Sí deben resolverse antes de `DB_PROVIDER=cosmos` en producción estable.

---

## Script de migración

```text
scripts/migrations/migrate_json_to_cosmos.py
```

### Uso

```bash
# Dry-run (default) — leer y validar sin escribir
python scripts/migrations/migrate_json_to_cosmos.py --dry-run

# Dry-run de colecciones específicas
python scripts/migrations/migrate_json_to_cosmos.py --dry-run --collections gn,hr,op

# Ejecución real (requiere credenciales + confirmación explícita)
python scripts/migrations/migrate_json_to_cosmos.py --execute --collections gn,hr,op

# Con reporte personalizado
python scripts/migrations/migrate_json_to_cosmos.py --dry-run --report reports/db/cosmos_migration_report.json

# Abortar al primer error
python scripts/migrations/migrate_json_to_cosmos.py --execute --fail-fast
```

### Dry-run — resultado actual

```
mode: dry-run
total: 14 (gn + hr + op)
by_status: {'READY': 14}
all_hashes_match: True
```

### Semántica del reporte

```json
{
  "collection": "gn",
  "document_id": "v2-7",
  "source_hash": "abc123...",
  "target_payload_hash": "abc123...",
  "metadata": {"id": "v2-7", "partition_value": null, "etag": null},
  "status": "READY"
}
```

**Códigos de estado:**

| Status | Significado |
|---|---|
| `READY` | Dry-run: documento puede migrarse, hash consistente |
| `WRITTEN` | Execute: documento escrito en Cosmos, hash verificado |
| `ALREADY_EXISTS` | Execute: documento ya existe en Cosmos con hash idéntico → skip |
| `CONFLICT` | Execute: documento existe en Cosmos con hash DIFERENTE → **ABORTAR** |
| `ERROR` | Cualquier error técnico durante la migración |

---

## Procedimiento de ejecución

### Paso 1 — Dry-run completo

```bash
python scripts/migrations/migrate_json_to_cosmos.py \
  --dry-run \
  --collections gn,hr,op,business_rules,simulation_results \
  --report reports/db/cosmos_migration_report_dryrun.json
```

Verificar:
- `total` == número esperado de documentos
- `by_status` == `{'READY': N}`
- `all_hashes_match` == `true`

### Paso 2 — Smoke test Cosmos aislado

```bash
export COSMOS_DATABASE=nexa_pricing_smoke_test
export COSMOS_CONTAINER=parametrization_smoke
pytest tests/db/smoke/ -v
```

Verificar que 8 tests pasan.

### Paso 3 — Ejecución parcial (gn first)

```bash
python scripts/migrations/migrate_json_to_cosmos.py \
  --execute \
  --collections gn \
  --fail-fast \
  --report reports/db/cosmos_migration_gn.json
```

Verificar reporte: `all_hashes_match == true`, `status == WRITTEN`.

### Paso 4 — Ejecución completa

```bash
python scripts/migrations/migrate_json_to_cosmos.py \
  --execute \
  --collections gn,hr,op,business_rules,simulation_results \
  --report reports/db/cosmos_migration_full.json
```

### Paso 5 — Validación final

```bash
# Verificar hashes del reporte
python -c "
import json
r = json.load(open('reports/db/cosmos_migration_full.json'))
print('all_hashes_match:', r['summary']['all_hashes_match'])
print('conflicts:', r['summary']['by_status'].get('CONFLICT', 0))
print('errors:', r['summary']['by_status'].get('ERROR', 0))
"

# Ejecutar tests contractuales Cosmos
pytest tests/db/contract/ -v
```

### Paso 6 — Activar Cosmos (solo tras validación exitosa)

```bash
# En el servidor de producción:
export DB_PROVIDER=cosmos
export COSMOS_ENDPOINT=https://...
export COSMOS_KEY=...
# Reiniciar la aplicación
```

---

## Rollback

Como los datos JSON NO se eliminan, el rollback es inmediato:

```bash
# 1. Cambiar variable de entorno (o revertir en entorno de configuración)
export DB_PROVIDER=json

# 2. Reiniciar la aplicación
# El backend JSON retoma desde storage/ sin pérdida de datos.
```

### Limpiar migración parcial en Cosmos

Si la migración fue parcial y se quiere repetir:
- Si `status == ALREADY_EXISTS` con hash coincidente: idempotente, no requiere acción
- Si `status == CONFLICT`: verificar causa raíz antes de reintentar
- Para borrar documentos en Cosmos: usar Azure Portal o SDK con `delete_item`

### Repetir `--execute` de forma idempotente

El script maneja idempotencia:
- Si el documento ya existe con el mismo hash: `ALREADY_EXISTS` (skip)
- Si existe con hash diferente: `CONFLICT` (abort — requiere intervención manual)

### Verificar que JSON sigue intacto

```bash
# El dry-run nunca modifica JSON
python scripts/migrations/migrate_json_to_cosmos.py --dry-run --collections gn
# Verificar que los archivos de storage/ no cambiaron:
ls -la storage/parametrization/gn/
```

---

## Riesgos conocidos

| Riesgo | Severidad | Mitigación |
|---|:---:|---|
| DT-router con credenciales Cosmos post-boot | Medio | Resolver en DB.7 antes de producción estable |
| `simulation_results` sin partition key | Medio | Definir antes de ejecutar; colección puede crecer |
| `snapshots`/`lineage`/`certificates` no migrados | Alto (futuro) | Requieren refactoring separado; JSON sigue siendo fallback |
| Cosmos no disponible durante deploy | Bajo | Rollback a `DB_PROVIDER=json` en segundos |
| Hash collision (SHA-256) | Mínimo | Negligible para volúmenes de datos de esta aplicación |

---

## Criterio de activación de Cosmos en producción

```text
✓ Dry-run exitoso: all_hashes_match=True, 0 errores
✓ Smoke test Cosmos pasando (8/8 tests)
✓ Execute exitoso en entorno aislado (0 CONFLICT, 0 ERROR)
✓ Tests contractuales Cosmos pasando
✓ DT-router resuelto (DB.7) O documentado como riesgo aceptado
✓ Plan de rollback probado
✓ Monitoreo configurado para errores Cosmos post-activación
```
