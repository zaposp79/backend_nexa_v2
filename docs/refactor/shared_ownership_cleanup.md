# FASE SHARED.1 — Shared Ownership Cleanup

**Fecha de ejecución:** 2026-06-04
**Branch:** refactor/modular-pure
**Estado:** Completada con deuda técnica documentada

---

## Baseline pre-fase

| Métrica | Valor |
|---------|-------|
| Gate (fallos) | 56 |
| Oracle (parity) | 406 passed / Δ = 0 |
| Collection errors | 0 |
| Archivos en `shared/` | 68 (excl. `__init__.py`) |

---

## FASE 1 — Análisis REVIEW_REQUIRED (sin código)

### Decisiones tomadas

| Archivo | Decisión | Justificación |
|---------|----------|---------------|
| `audit/api/audit_router.py` | `MOUNT_ENDPOINT` → ejecutado | Router existente con tests, no estaba en `api/v1/router.py`. 3 baseline failures. |
| `certification/api/certification_router.py` | `MOUNT_ENDPOINT` → ejecutado | Idem. 27 certification baseline failures (preexistentes). |
| `infrastructure/logging/structured_logger.py` | `KEEP_SHARED` | Re-exportado por `__init__`, validado en tests domain purity. |
| `lineage/query.py` | `KEEP_SHARED` | Re-exportado desde `shared/lineage/__init__`, usado por `use_cases/audit_simulation.py`. |
| `models/panel.py` | `KEEP_SHARED` | Re-exportado por `models/__init__` → 56 módulos producción (star import). |
| `models/results.py` | `KEEP_SHARED` | Idem. `PyGMensual` con tests de contrato P0. |
| `models/visions_cts.py` | `KEEP_SHARED` | Cadena re-export: `visions_cts.py` → `visions.py` → `models/__init__`. Modelos de dominio compartido. |
| `models/visions_imprimible.py` | `KEEP_SHARED` | Idem. |
| `models/visions_pyg.py` | `KEEP_SHARED` | Idem. Tests de contrato. |
| `models/visions_tarifas.py` | `KEEP_SHARED` | Idem. |
| `use_cases/audit_simulation.py` | `KEEP_SHARED` | Implementa `AuditSimulationUseCase`. Necesario para `audit_router.py`. |
| `helpers/certified_helpers.py` | `KEEP_SHARED` | Helper de `certified_calculation.py` (extracción intencional >500 LOC). |

**Corrección al audit previo:** `models/visions.py` fue reclasificada de `MODULE_OWNED` a
`SHARED_CONFIRMED`. Tiene cero imports directos pero es el hub de re-export de todos los modelos
de visiones (`visions_cts`, `visions_pyg`, `visions_imprimible`, `visions_tarifas`), consumidos
transitivamente por 56 módulos a través de `models/__init__`.

---

## FASE 2 — Huérfanos eliminados

| Archivo | Evidencia de no uso |
|---------|---------------------|
| `shared/profitability/entities.py` | 0 imports producción, 0 tests, 0 dynamic refs. `WaterfallStep` dataclass sin consumidor. |
| `shared/profitability/value_objects.py` | 0 imports producción, 0 tests, 0 dynamic refs. `MargenDeal` dataclass sin consumidor. |

**Gate tras eliminación:** 56 → 56 (sin cambio). Oracle 406/Δ=0.

---

## FASE 3 — Movidas de bajo riesgo ejecutadas

### Ejecutado: `lineage/lineage_builder.py` → `calculator/lineage/lineage_builder.py`

| Campo | Valor |
|-------|-------|
| Origen | `modules/shared/lineage/lineage_builder.py` |
| Destino | `modules/calculator/lineage/lineage_builder.py` |
| Imports actualizados | `modules/calculator/engine.py:200` |
| Re-export shim | `modules/shared/lineage/lineage_builder.py` (compatibilidad) |
| Gate tras movida | 53 (sin regresión) |
| Oracle | 406/Δ=0 |

### Cancelado: `config/business_rules/loader.py`

**Motivo:** `loader.py` usa `_RULES_DIR = os.path.dirname(__file__)` para resolver rutas a YAML
(`operaciones.yaml`, `margenes.yaml`). Mover el archivo sin mover los YAMLs rompe el resolver.
El movimiento no es trivial — requiere también mover los archivos YAML de datos, actualizar 16
sitios de import (3 prod + 13 tests) y asegurar que el path resolver funcione en el nuevo módulo.

**Decisión:** `POSTPONE_WITH_REASON` — reubicación de `loader.py` junto con sus YAMLs es una
tarea independiente que requiere más análisis. El archivo permanece en `shared/config/business_rules/`.

### Cancelado: `use_cases/certified_calculation.py` + `helpers/certified_helpers.py`

**Motivo:** 27 tests de certification ya fallan en el baseline. Mover el use case durante una fase
de inestabilidad añade riesgo sin valor claro. Los tests usan imports directos de la ruta `shared`.

**Decisión:** `POSTPONE_WITH_REASON` — mover solo después de que los 27 certification failures
sean resueltos en una fase dedicada.

---

## FASE 5 — Endpoints montados

| Router | Prefijo | Donde montado | Fallos corregidos |
|--------|---------|---------------|-------------------|
| `shared/audit/api/audit_router.py` | `/audit` | `api/v1/router.py` | 3 (`test_http_audit_*`) |
| `shared/certification/api/certification_router.py` | `/certification` | `api/v1/router.py` | 0 (27 cert failures son preexistentes, no del montaje) |

**Gate tras montaje:** 56 → **53** fallos. Oracle 406/Δ=0.

---

## Estado final del inventario `shared/`

### Mantenidos en shared (permanentes)

| Archivo | Motivo |
|---------|--------|
| `contracts/api_v1/**` (15 archivos) | Wire contract versionado — NUNCA mover |
| `exceptions.py` | 56 importers, 7 dominios prod |
| `i_parametrization_provider.py` | Interfaz DIP central, 6 dominios |
| `responses.py` | 11 dominios prod |
| `audit/trace.py` | 8 dominios prod |
| `ports/logger.py` | Port transversal, 3 dominios |
| `ports/trace_emitter.py` | Port transversal, 3 dominios |
| `infrastructure/config.py` | 3 dominios + infra |
| `infrastructure/app_settings.py` | Arranque de app |
| `models/panel.py` / `results.py` | Hub de dominio central vía `__init__` star |
| `models/visions.py` + submódulos | Hub re-export, consumido transitivamente |
| `lineage/models.py` | Exportado desde `lineage/__init__`, usado en tests |
| `lineage/query.py` | Parte del contrato `shared.lineage` |
| `use_cases/audit_simulation.py` | Necesario para `audit_router.py` |
| `helpers/certified_helpers.py` | Helper interno de `certified_calculation.py` |
| `certification/models.py` | Modelos de certificación compartidos |
| `certification/certificate_repository.py` | DIP: infra cablea, calculator usa |

### Bloqueados (Oracle / contrato público)

| Archivo | Motivo |
|---------|--------|
| `precision.py` | Oracle-sensitive. Funciones de redondeo Excel-compatible. NO TOCAR. |
| `profitability/calculators.py` | Oracle-sensitive. Tests de mutation detection. NO TOCAR. |
| `contracts/api_v1/**` | Wire contract público. NO MOVER bajo ninguna circunstancia. |

### Movidos

| Origen | Destino | Shim en origen |
|--------|---------|:--------------:|
| `lineage/lineage_builder.py` | `calculator/lineage/lineage_builder.py` | ✓ |

### Eliminados

| Archivo | Motivo |
|---------|--------|
| `profitability/entities.py` | Huérfano confirmado (0 consumidores) |
| `profitability/value_objects.py` | Huérfano confirmado (0 consumidores) |

---

## Deuda técnica pendiente

| ID | Tarea | Complejidad | Motivo de postergación |
|----|-------|:-----------:|------------------------|
| DT-1 | Mover `config/business_rules/loader.py` a `vision_tarifas/` junto con sus YAMLs | Media | Requiere mover archivos de datos + 16 sitios de import |
| DT-2 | Mover `use_cases/certified_calculation.py` + `helpers/certified_helpers.py` a `calculator/` | Media | 27 certification tests ya inestables en el baseline |
| DT-3 | Resolver 27 certification test failures (baseline preexistente) | Alta | Requiere análisis independiente de la causa raíz |
| DT-4 | Eliminar shim `shared/lineage/lineage_builder.py` | Baja | Solo al confirmar que no hay otros callers |
| DT-5 | Mover `audit/trace_integration.py`, `traceability_registry.py`, `traceability_writer.py` → `calculator/audit/` | Media | Fase 4 (riesgo medio, DIP wiring) |
| DT-6 | Mover `certification/models.py` → `calculator/certification/` | Media | Fase 4 |
| DT-7 | Mover `infrastructure/storage/base_repository.py` + `json_store.py` → `parametrizacion/shared/infra/` | Media | Fase 4 |
| DT-8 | Mover `lineage/models.py` → `calculator/lineage/` (junto con tests) | Media | Fase 4 |
| DT-9 | Mover `versioning/version_registry.py` → `calculator/` | Baja | Solo 2 prod consumers (calculator) |

---

## Validación final

| Métrica | Baseline | Post-fase | Δ |
|---------|:--------:|:---------:|:---:|
| Gate (fallos) | 56 | **53** | −3 |
| Oracle | 406/Δ=0 | **406/Δ=0** | 0 |
| Collection errors | 0 | **0** | 0 |
| Routers no montados | 2 | **0** | −2 |
| Huérfanos confirmados | 2 | **0** | −2 |
| MODULE_OWNED pendientes | 5 | **4** (1 movido) | −1 |

---

## Guardrails activos post-fase

Ver `tests/unit/test_shared_guardrails.py` para:
1. `precision.py` y `profitability/calculators.py` no se movieron.
2. `contracts/api_v1/**` no se movió.
3. Ningún router en `shared/**/api/` queda sin montar.
4. `shared/helpers/` no contiene helpers con 0 consumidores.
