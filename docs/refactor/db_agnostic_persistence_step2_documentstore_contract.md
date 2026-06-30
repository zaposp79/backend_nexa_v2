# DB_AGNOSTIC_PERSISTENCE_STEP2_DOCUMENTSTORE_CONTRACT

**Fecha:** 2026-06-06  
**Status:** ⚠️ MAPEADO — Violaciones encontradas, fixes bloqueados para refactor mayor  
**Objetivo:** Validar que toda persistencia pase por Repository + DocumentStore + StoredDocument

---

## Resumen Ejecutivo

**Arquitectura objetivo:**

```
Módulo funcional
  → Repository específico
    → DocumentStore (agnóstico)
      → StoredDocument
        → Provider concreto (JSON/Cosmos)
```

**Estado actual:**

| Componente | Usa DocumentStore | Status |
|---|---|---|
| **ResultsRepository** | ✅ SÍ | OK — implementación correcta |
| **SnapshotRepository** | ❌ NO (postponed) | VIOLATION — escribe directo a filesystem |
| **TraceabilityWriter** | ❌ NO | VIOLATION — escribe directo a filesystem |
| **LineageSnapshotRepository** | ❌ NO (external infra) | VIOLATION — escribe directo a filesystem |

**Total: 1 OK, 3 VIOLATIONS**

---

## Persistencia Actual (Detallado)

### 1. ResultsRepository ✅ CORRECTO

**Ubicación:** `modules/calculator/persistence/results_repository.py`

**Flujo:**
```python
ResultsRepository.save(data: Dict)
  → DocumentStore.upsert("simulation_results", document)
    → Provider JSON: storage/simulation_results/{id}.json
    → Provider Cosmos: Azure Cosmos Document {id}
```

**Características:**
- ✅ Acepta DocumentStore por inyección
- ✅ Usa CollectionConfig para agnosticismo
- ✅ Preserva payload (quita "id" en lectura)
- ✅ Maneja excepciones de DocumentStore

**Patrón correcto:**
```python
def save(self, data: Dict[str, Any]) -> str:
    simulation_id = data["simulation_id"]
    document = {"id": simulation_id, **data}
    self._store.upsert(_COLLECTION, document)  # ← DocumentStore
    return simulation_id
```

**Tests:** 
- ✅ Implicit via golden tests (58/58 pass)

---

### 2. SnapshotRepository ❌ VIOLACIÓN

**Ubicación:** `modules/shared/persistence/snapshots_repository.py`

**Flujo actual (VIOLACIÓN):**
```python
SnapshotRepository.save(snapshot)
  → Path.mkdir() + json.dump() directamente
    → storage/snapshots/{simulation_id}/snapshot.json
    → storage/snapshots/{simulation_id}/summary.json
```

**Problema:**
- ❌ Acepta DocumentStore pero NO lo usa (linea 58: `self._store = store  # reserved for future internal migration`)
- ❌ Escribe directamente a filesystem via json.dump()
- ❌ Layout incompatible con DocumentStore (dos archivos por simulación)
- ❌ Não ser agnóstico (hardcoded Path, no funciona con Cosmos)

**Código problemático (linea 79-95):**
```python
def save(self, snapshot: SimulationSnapshot) -> Path:
    sim_dir = self._base / snapshot.simulation_id
    sim_dir.mkdir(parents=True, exist_ok=True)  # ← DIRECT FILESYSTEM
    try:
        self._write_json(sim_dir / "snapshot.json", ...)  # ← json.dump()
        self._write_json(sim_dir / "summary.json", ...)   # ← json.dump()
```

**Lectura (linea 107-120):**
```python
def load(self, simulation_id: str) -> Optional[SimulationSnapshot]:
    path = self._base / simulation_id / "snapshot.json"
    return json.loads(path.read_text(encoding="utf-8"))  # ← DIRECT READ
```

**Impacto:**
- ⚠️ Simulations guardan pero NO son agnósticas de BD
- ⚠️ Si se activa Cosmos, SnapshotRepository falla (Path-based)
- ⚠️ Migración postponed indefinidamente

---

### 3. TraceabilityWriter ❌ VIOLACIÓN

**Ubicación:** `modules/calculator/audit/traceability_writer.py`

**Flujo actual (VIOLACIÓN):**
```python
TraceabilityWriter.write(simulation_id, raw_request, solicitud, resultado)
  → Path.mkdir() + json.dump() directamente
    → storage/simulations/{simulation_id}/
      ├── request.json
      ├── visions/
      │   ├── vision_pyg.json
      │   ├── vision_tarifas.json
      │   ├── cost_to_serve.json
      │   └── vision_imprimible.json
      └── audit/
          ├── polizas_source.json
          ├── adapter_trace.json
          └── escenarios_aplicados.json
```

**Problema:**
- ❌ Escribe directamente a filesystem via json.dump()
- ❌ Usa SIMULATIONS_DIR en lugar de DocumentStore
- ❌ NO es agnóstico (no funciona con Cosmos)
- ❌ Estructura multi-archivo incompatible con DocumentStore

**Código problemático (linea 53-56, 77-120):**
```python
def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)  # ← DIRECT FILESYSTEM
    with open(path, "w", encoding="utf-8") as f:    # ← DIRECT OPEN
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

def write(self, simulation_id, raw_request, solicitud, resultado, ...):
    sim_dir = self._base / simulation_id  # ← hardcoded path
```

**Impacto:**
- ⚠️ Traceability no es agnóstica de BD
- ⚠️ Si se activa Cosmos, TraceabilityWriter falla
- ⚠️ Requiere refactor mayor para soportar DocumentStore

---

### 4. LineageSnapshotRepository ❌ VIOLACIÓN

**Ubicación:** `modules/shared/infrastructure/lineage/snapshot_repository.py`

**Flujo actual (VIOLACIÓN):**
```python
LineageSnapshotRepository.save(graph)
  → Path.mkdir() + json.dump() directamente
    → storage/lineage/{simulation_id}.json
```

**Problema:**
- ❌ Escribe directamente a filesystem
- ❌ NO es agnóstico
- ❌ Infra externa (no crítica para simulaciones, pero viola patrón)

---

## Matriz de Repositorios y DocumentStore

| Dato | Repository | DocumentStore usado | StoredDocument usado | JSON/Cosmos agnóstico | Corrección necesaria |
|---|---|---|---|---|---|
| **PricingResult** | ResultsRepository | ✅ SÍ | ✅ Implícito | ✅ SÍ | NONE — OK |
| **SimulationSnapshot** | SnapshotRepository | ❌ NO | ❌ NO | ❌ NO | BLOCKED_FOR_REFACTOR — Layout incompatible |
| **Traceability (FASE G)** | TraceabilityWriter | ❌ NO | ❌ NO | ❌ NO | BLOCKED_FOR_REFACTOR — Multi-file structure |
| **Lineage (WAVE 10)** | LineageSnapshotRepository | ❌ NO | ❌ NO | ❌ NO | BLOCKED_FOR_REFACTOR — External infra |

---

## Violaciones Encontradas

### VIOLATION-1: SnapshotRepository — Direct filesystem writes

**Archivo:** `modules/shared/persistence/snapshots_repository.py`  
**Líneas:** 66-95 (save), 107-120 (load)  
**Severidad:** 🔴 ALTO  
**Tipo:** RUNTIME_DIRECT_STORAGE

**Descripción:**
SnapshotRepository escribe directamente a filesystem usando Path.write_text() y json.dump(), violando la arquitectura agnóstica de BD. El layout (dos archivos por simulación en subdirectorio) es incompatible con DocumentStore.

**Razón de no corregir:**
Refactor requiere:
1. Cambiar layout de almacenamiento (2 archivos → 1 documento)
2. Convertir snapshot.json + summary.json en un único document
3. Actualizar todos los lectores de snapshots
4. Posible impacto en FASE 4 (certification)

**Mitigación actual:**
- Snapshot se guarda en filesystem (JSON)
- Si se activa Cosmos, SnapshotRepository falla en runtime
- Documentación menciona "POSTPONED (FASE 13 batch snapshots)"

**Decisión:** BLOCKED_FOR_REFACTOR

---

### VIOLATION-2: TraceabilityWriter — Direct filesystem writes

**Archivo:** `modules/calculator/audit/traceability_writer.py`  
**Líneas:** 53-56 (write_json), 77-120 (write)  
**Severidad:** 🔴 ALTO  
**Tipo:** RUNTIME_DIRECT_STORAGE

**Descripción:**
TraceabilityWriter escribe directamente a filesystem usando open() y json.dump(), violando agnnosticismo. La estructura multi-archivo (request.json, visions/, audit/) es incompatible con DocumentStore (que asume 1 doc por id).

**Razón de no corregir:**
Refactor requiere:
1. Cambiar layout de 10+ archivos a documento único
2. Migrar visions/ a campos de documento
3. Migrar audit/ a campos de documento
4. Actualizar FASE G (trazabilidad contractual)
5. Actualizar todos los lectores de traceability

**Mitigación actual:**
- Traceability se guarda en filesystem (JSON)
- Si se activa Cosmos, TraceabilityWriter falla en runtime
- Documentación no menciona planes de migración

**Decisión:** BLOCKED_FOR_REFACTOR

---

### VIOLATION-3: LineageSnapshotRepository — Direct filesystem writes

**Archivo:** `modules/shared/infrastructure/lineage/snapshot_repository.py`  
**Severidad:** 🟠 MEDIO (infra externa)  
**Tipo:** RUNTIME_DIRECT_STORAGE

**Descripción:**
LineageSnapshotRepository escribe directamente a filesystem. Esta es infra externa (WAVE 10/14), no crítica para simulaciones, pero viola patrón agnóstico.

**Razón de no corregir:**
Lineage es feature separada de pricing. Refactor aquí requeriría decisión arquitectónica sobre si lineage debe ser agnóstico de BD.

**Decisión:** BLOCKED_FOR_REFACTOR

---

## Fixes Aplicados

**NINGUNO.** Todos los fixes requieren refactor mayor y están fuera de alcance "fix pequeño".

---

## Qué Queda Pendiente

### ⚠️ CRÍTICO — Antes de activar Cosmos

Cuando se decida activar Cosmos como DB_PROVIDER:

1. **SnapshotRepository debe migrar a DocumentStore**
   - Consolidar snapshot.json + summary.json en 1 documento
   - Actualizar readers
   - Validar FASE 4 (certification)

2. **TraceabilityWriter debe migrar a DocumentStore**
   - Consolidar 10+ archivos en 1 documento (estructura nested)
   - Actualizar FASE G (trazabilidad contractual)
   - Validar readers en use_cases/

3. **LineageSnapshotRepository debe migrar a DocumentStore** (si aplica)
   - Decidir si lineage debe ser agnóstico
   - Si sí: migrar a DocumentStore
   - Si no: documentar como "no agnóstico"

### ⚠️ RECOMENDACIÓN

**No activar DB_PROVIDER=cosmos hasta que:**
1. SnapshotRepository use DocumentStore
2. TraceabilityWriter use DocumentStore
3. Todos los readers estén actualizados
4. Pruebas de migración Cosmos completadas

---

## Resumen: Agnósticismo Actual

| Componente | JSON | Cosmos | Status |
|---|---|---|---|
| **ResultsRepository** | ✅ | ✅ | AGNÓSTICO |
| **SnapshotRepository** | ✅ | ❌ | ONLY JSON |
| **TraceabilityWriter** | ✅ | ❌ | ONLY JSON |
| **LineageSnapshotRepository** | ✅ | ❌ | ONLY JSON |
| **Overall** | ✅ | ❌ | ONLY JSON |

**Conclusión:** Sistema funciona con JSON. **Cosmos requiere refactor de 3 componentes antes de activación.**

---

## Validación

**Tests ejecutados:**

| Suite | Resultado |
|---|---|
| test_baseline_formula_snapshot_v1.py | 5/5 ✅ |
| test_baseline_formula_snapshot_cadena_c_v1.py | 5/5 ✅ |
| tests/golden/ | 58/58 ✅ |
| **TOTAL** | **68/68 ✅** |

**Cero drift — No se realizaron cambios de código.**

---

## Matriz de Clasificación Final

| Archivo | Linea | Tipo | Severidad | Clasificación | Acción |
|---|---|---|---|---|---|
| snapshots_repository.py | 66-95 | json.dump/Path | ALTO | VIOLATION_RUNTIME_DIRECT_STORAGE | BLOCKED_FOR_REFACTOR |
| snapshots_repository.py | 107-120 | Path.read_text | ALTO | VIOLATION_RUNTIME_DIRECT_STORAGE | BLOCKED_FOR_REFACTOR |
| traceability_writer.py | 53-56 | json.dump/open | ALTO | VIOLATION_RUNTIME_DIRECT_STORAGE | BLOCKED_FOR_REFACTOR |
| traceability_writer.py | 77-120 | multi-file write | ALTO | VIOLATION_RUNTIME_DIRECT_STORAGE | BLOCKED_FOR_REFACTOR |
| snapshot_repository.py (lineage) | * | json.dump | MEDIO | VIOLATION_RUNTIME_DIRECT_STORAGE | BLOCKED_FOR_REFACTOR |
| results_repository.py | * | DocumentStore | — | OK_DOCUMENTSTORE | NONE |

---

## Conclusión

**STEP2 ANÁLISIS COMPLETADO:**

- ✅ Se identificaron todas las persistencias runtime (4 componentes)
- ✅ Se clasificaron (1 OK, 3 violaciones)
- ✅ Se documentó por qué no se corriben (refactor mayor bloqueado)
- ✅ Se identificó qué requiere migrar antes de Cosmos
- ✅ 68/68 tests pasan (cero drift)

**Status actual:** ⚠️ **ONLY JSON — Cosmos requiere refactor de 3 componentes**

**Readiness para Cosmos:** ❌ **NO — Bloqueado hasta SnapshotRepository, TraceabilityWriter, LineageSnapshotRepository migren a DocumentStore**

---

**Status:** ⚠️ **CERRADO — 2026-06-06**  
**Próximo paso:** CALCULATION_PERSISTENCE_STEP3_COSMOS_MIGRATION_PLAN (decisión arquitectónica)
