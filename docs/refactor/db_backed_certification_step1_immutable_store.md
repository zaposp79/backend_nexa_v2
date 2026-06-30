# DB_BACKED_CERTIFICATION_STEP1_IMMUTABLE_STORE

**Fecha:** 2026-06-07  
**Status:** ✅ **COMPLETE**  
**Branch:** refactor/modular-pure  

---

## Objetivo

Añadir soporte mínimo de snapshots inmutables a `DocumentStore` como fundamento para certificación DB-backed futura, sin cambios a fórmulas, cálculos ni comportamiento de runtime.

---

## API añadida

### `DocumentStore` (abstract port)

```python
def put_immutable(
    self,
    collection: CollectionConfig,
    record: StoredDocument,
) -> StoredDocument:
    """Crea documento solo si no existe. Lanza DbConflictError si ya existe."""

def get_snapshot(
    self,
    collection: CollectionConfig,
    document_id: str,
    *,
    partition_value: str | None = None,
) -> StoredDocument | None:
    """Retorna snapshot inmutable por id, o None si no existe."""
```

**Semántica garantizada:**
- `put_immutable`: create-only — no overwrite posible a través de este método
- `get_snapshot`: read-only alias semántico de `get_record` para colecciones inmutables
- `upsert_record`: sin cambios — sigue permitiendo sobreescritura

---

## Implementaciones

### `JsonDocumentStore`

- `put_immutable`: verifica existencia del archivo antes de escribir; lanza `DbConflictError` si ya existe; escribe atómicamente con `write_json_atomic`
- `get_snapshot`: delega a `get_record`

### `CosmosDocumentStore`

- `put_immutable`: usa `create_item` (semántica nativa Cosmos: lanza 409 si ya existe → `DbConflictError`)
- `get_snapshot`: delega a `get_record`

---

## Tests

**Archivo:** `tests/db/contract/test_document_store_immutable_snapshots.py`

```
TestPutImmutableCreates:
  ✅ put_immutable creates document
  ✅ get_snapshot returns created document
  ✅ get_snapshot returns None when not found

TestPutImmutableConflict:
  ✅ second put_immutable with same id raises DbConflictError
  ✅ conflict on different payload same id
  ✅ original payload preserved after conflict

TestUpsertUnchanged:
  ✅ upsert_record can overwrite (unchanged behavior)
  ✅ put_immutable and upsert_record coexist in same collection
  ✅ upsert does not affect immutable ids
────────────────────────────────────────────────────────
Total: 9/9 PASS (JSON) + 9 SKIPPED (Cosmos, no credentials)
```

---

## Conflicto esperado: comportamiento

| Situación | Resultado |
|---|---|
| `put_immutable` en id nuevo | `StoredDocument` creado |
| `put_immutable` en id existente | `DbConflictError` |
| `get_snapshot` en id existente | `StoredDocument` |
| `get_snapshot` en id inexistente | `None` |
| `upsert_record` en id existente | Sobreescribe (unchanged) |

---

## Gates críticos de runtime

```
tests/refactor/test_baseline_formula_snapshot_v1.py       ✅ 6/6
tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py  ✅ 4/4
tests/golden/                                              ✅ 58/58
───────────────────────────────────────────────────────────
TOTAL: 68/68 PASS ✅  Zero pricing drift
```

---

## Riesgo

🟢 **ZERO** — No hay cambios a fórmulas, cálculos, parámetros activos, ni contratos existentes. Solo se añaden métodos abstractos nuevos a la interface y sus implementaciones.

---

## Siguiente Paso: DB_BACKED_CERTIFICATION_STEP2_SNAPSHOT_REPOSITORY

Crear `ParametrizationSnapshotRepository` que use `put_immutable` / `get_snapshot` para persistir snapshots en la colección `parametrization_snapshots`. Punto de integración con `CertifiedCalculationUseCase`.

Inputs mínimos para Step 2:
- Colección: `CollectionConfig(name="parametrization_snapshots")`
- Documento por módulo: `StoredDocument(id=f"{version}/{module}", payload=<parametrization_dict>)`
- Operación de certificación: `put_immutable` por módulo (falla si ya certificado)
- Operación de ejecución: `get_snapshot` por módulo (carga Layer 1 desde DB)
