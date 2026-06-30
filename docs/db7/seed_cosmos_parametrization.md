# Seed de parametrización en Cosmos DB

Cómo cargar los datos maestros de `storage/parametrization/` en Azure Cosmos DB,
y cuál es la estructura de datos resultante.

## 1. Qué datos se cargan

La carpeta `storage/parametrization/` contiene 4 **dominios** de parametrización
del simulador de pricing:

| Dominio          | Contenido                                                        | Payload activo (v2-7)                  |
|------------------|------------------------------------------------------------------|----------------------------------------|
| `gn`             | Catálogos generales (ciudades, clientes, servicios, pólizas, …)  | `v2-7/gn.json` (~5 KB)                  |
| `hr`             | Nómina, roles, niveles, reglas de staff                          | `v2-7/hr.json` (~75 KB)                |
| `op`             | OPEX fijo, hardware/software, dispositivos                       | `v2-7/op.json` (~16 KB)                |
| `business_rules` | Config de riesgo + reglas comerciales (márgenes, contingencias)  | `v2-7/business_rules.json` (~2.4 KB)   |

Cada dominio tiene además un índice `'{dominio}/versions.json'`:

- `gn`, `hr`, `op` → **lista**: `[{version_id, filename, uploaded_at, is_active, sheet_count, total_rows}, ...]`
- `business_rules` → **dict**: `{active_version, versions:[{id, status, ...}]}`

> El script solo siembra la versión **activa** de cada dominio (la única cuyo
> payload existe localmente como archivo). Las versiones históricas del índice
> solo tienen metadatos; se informan como "omitidas".

## 2. Estructura de datos en Cosmos

Se usa el esquema canónico de
[`CosmosParametrizationRepository`](../../modules/parametrizacion/shared/repositories/cosmos_parametrization_repository.py).

```
Database:      nexa_pricing_db     (COSMOS_DATABASE)
Container:     parametrization     (COSMOS_CONTAINER)
Partition key: /domain
```

Un solo container guarda todos los dominios, particionado por `/domain`. Hay
**dos tipos de documento**:

### 2.1 `parametrization_version` — una versión completa

```jsonc
{
  "id":          "v2-7",                 // = version_id; único dentro de la partición
  "pk":          "gn",                   // valor de partición (espejo de domain)
  "domain":      "gn",                   // partition key (/domain)
  "version_id":  "v2-7",
  "type":        "parametrization_version",
  "status":      "active",              // "active" | "inactive"
  "created_at":  "2026-05-27T18:33:00Z",
  "created_by":  "seed_script",
  "source":      "excel_upload",
  "file_name":   "Nexa - Pricing - Simulador - V2-7.xlsx",
  "hash":        "8edbab73f00e4d37...", // sha256 del payload
  "sheet_count": 23,
  "total_rows":  0,
  "payload":     { /* JSON completo del dominio: v2-7/gn.json */ }
}
```

### 2.2 `active_version` — puntero a la versión activa

```jsonc
{
  "id":             "active_gn",
  "pk":             "gn",
  "domain":         "gn",
  "type":           "active_version",
  "active_version": "v2-7",
  "updated_at":     "2026-06-04T..."
}
```

### Documentos resultantes (estado actual)

Con los 4 dominios sembrados se crean **8 documentos**: 4 de tipo
`parametrization_version` (uno activo por dominio) + 4 punteros `active_version`.

### Consultas típicas

```sql
-- Versión activa de un dominio (vía puntero, lectura por id + partición)
--   read_item(id="active_gn", partition_key="gn")  ->  active_version
--   read_item(id=<active_version>, partition_key="gn")  ->  payload

-- Listar todas las versiones de un dominio (intra-partición, eficiente)
SELECT * FROM c
WHERE c.domain = "gn" AND c.type = "parametrization_version"
ORDER BY c.created_at DESC
```

Todas las lecturas son **intra-partición** (filtran por `domain`), por lo que no
requieren cross-partition query.

## 3. Cómo ejecutar el seed

Script: [`scripts/migrations/seed_cosmos_parametrization.py`](../../scripts/migrations/seed_cosmos_parametrization.py)

### Requisitos

```bash
pip install azure-cosmos          # ya está en requirements.txt (>=4.5,<5)
```

Variables de entorno (en el entorno o en `backend_nexa/.env`):

```env
COSMOS_ENDPOINT=https://<cuenta>.documents.azure.com:443/
COSMOS_KEY=<primary-or-secondary-key>
COSMOS_DATABASE=nexa_pricing_db
COSMOS_CONTAINER=parametrization
```

### Comandos

```bash
# Previsualizar sin conexión (qué se escribiría)
python scripts/migrations/seed_cosmos_parametrization.py --dry-run

# Provisionar DB + container (idempotente) y sembrar todo
python scripts/migrations/seed_cosmos_parametrization.py --provision --execute

# Sembrar (DB/container ya existen)
python scripts/migrations/seed_cosmos_parametrization.py --execute

# Verificar lo que quedó en Cosmos
python scripts/migrations/seed_cosmos_parametrization.py --verify

# Acotar a dominios concretos
python scripts/migrations/seed_cosmos_parametrization.py --execute --domains gn hr
```

`save_version()` es idempotente respecto del estado activo: al sembrar de nuevo
una versión, desactiva las demás del dominio y reactiva la sembrada.

## 4. Activar Cosmos como backend de lectura (nota importante)

Sembrar los datos **no** cambia de dónde lee la aplicación. Hoy el runtime de
parametrización está cableado a JSON en
[`db/factory.py` → `get_parametrization_store()`](../../db/factory.py), que
construye siempre un `JsonDocumentStore` independientemente de `DB_PROVIDER`.

Existe además un segundo camino Cosmos genérico vía `DocumentStore`
([`CosmosDocumentStore`](../../db/providers/cosmos_document_store.py)), marcado
"PREPARADO, NO ACTIVO". Ese camino usa un encoding de `id` distinto
(`'{collection}:{id}'` en `upsert_record` vs. `id` directo en `get`) que aún no
es consistente para leer la versión activa, por lo que **no** es el objetivo de
este seed.

Para que la app lea desde el esquema canónico sembrado por este script habría
que conectar el `ParametrizationResolver`/repos "active" a
`CosmosParametrizationRepository` (o alinear `get_parametrization_store()` con el
provider Cosmos). Eso es un cambio de wiring aparte de la carga de datos.
