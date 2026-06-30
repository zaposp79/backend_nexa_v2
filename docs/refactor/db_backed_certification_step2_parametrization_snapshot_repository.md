# DB_BACKED_CERTIFICATION_STEP2_PARAMETRIZATION_SNAPSHOT_REPOSITORY

**Fecha:** 2026-06-07  
**Status:** ✅ **COMPLETE**  
**Branch:** refactor/modular-pure  

---

## Objetivo

Crear `ParametrizationSnapshotRepository` sobre `DocumentStore.put_immutable()` y `get_snapshot()` como capa de persistencia para snapshots certificados de parametrización.

---

## Archivo creado

[modules/parametrizacion/repositories/parametrization_snapshot_repository.py](../../modules/parametrizacion/repositories/parametrization_snapshot_repository.py)

---

## Formato de documento

```json
{
  "id": "v2-7__business_rules",
  "version": "v2-7",
  "module": "business_rules",
  "schema_version": "parametrization_snapshot_v1",
  "hash": "<sha256 hex>",
  "payload": { ... },
  "created_at": "2026-06-07T12:00:00+00:00"
}
```

**Colección:** `parametrization_snapshots`

---

## Estrategia de ID seguro

```
id = "{version}__{module}"
```

- Doble guión bajo como separador — sin barras `/` ni `\`
- Seguro para filesystem (nombre de archivo JSON) y Cosmos (document id)
- Ejemplos: `v2-7__business_rules`, `v2-7__hr`, `v2-8__op`
- Versión validada contra caracteres inseguros antes de construcción del id

---

## API pública

```python
class ParametrizationSnapshotRepository:

    def put_snapshot(
        self,
        version: str,
        module: str,
        payload: dict,
        *,
        content_hash: str = "",
    ) -> dict:
        """Crea snapshot inmutable. Lanza ParametrizationSnapshotConflictError si ya existe."""

    def get_snapshot(self, version: str, module: str) -> dict | None:
        """Retorna snapshot o None si no existe."""
```

**Módulos válidos:** `business_rules`, `gn`, `hr`, `op` (frozenset — extensible)

**Excepciones de dominio:**
- `ParametrizationSnapshotConflictError(version, module)` — snapshot ya certificado
- `ParametrizationSnapshotValidationError` — módulo o versión inválida

---

## Tests

**Archivo:** `tests/db/contract/test_parametrization_snapshot_repository.py`

```
TestPutSnapshotCreates:
  ✅ put_snapshot creates document
  ✅ id present in returned document
  ✅ created_at timestamp present
  ✅ content_hash stored correctly
  ✅ get_snapshot returns created document
  ✅ get_snapshot returns None when absent

TestPutSnapshotConflict:
  ✅ duplicate put raises ParametrizationSnapshotConflictError
  ✅ original payload preserved after conflict

TestSafeIdFormat:
  ✅ id does not contain '/' or '\\'
  ✅ id uses double-underscore separator
  ✅ all 4 modules produce safe ids

TestModuleValidation:
  ✅ invalid module raises before write
  ✅ empty module raises
  ✅ invalid module in get raises
  ✅ unsafe version raises
─────────────────────────────────────────────────
Total: 15/15 PASS (JSON) + 15 SKIP (Cosmos, no credentials)
```

---

## Gates críticos de runtime

```
test_document_store_immutable_snapshots.py   9/9 PASS ✅
test_baseline_formula_snapshot_v1.py         6/6 PASS ✅
test_baseline_formula_snapshot_cadena_c_v1.py 4/4 PASS ✅
tests/golden/                               58/58 PASS ✅
──────────────────────────────────────────────────────
TOTAL: 77/77 PASS ✅  Zero pricing drift
```

---

## Riesgo

🟢 **ZERO** — Nuevo archivo, sin tocar fórmulas, cálculos, ni runtime.

---

## Siguiente Paso: DB_BACKED_CERTIFICATION_STEP3_WIRING

Cablear `ParametrizationSnapshotRepository` en `CertifiedCalculationUseCase`:

1. Inyectar `ParametrizationSnapshotRepository` en `CertifiedCalculationUseCase.__init__`
2. En `execute()`, antes de calcular: cargar snapshots Layer 1 desde DB via `get_snapshot(version, module)`
3. Si snapshots presentes → usar como parametrización Layer 1 en el engine certificado
4. Si snapshots ausentes → degradar a Layer 2 con advertencia (backward compat)
5. Crear `SnapshotLoader` o adapter que convierta `payload` → `IParametrizationProvider`

**Dependencia crítica:** Para que Step 3 sea útil en producción, se necesita un flujo de certificación que llame `put_snapshot()` para cada módulo al momento de certificar.
