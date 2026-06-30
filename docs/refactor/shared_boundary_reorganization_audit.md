# Shared Boundary Reorganization Audit

**Fase:** AUDIT_ONLY  
**Worker:** architecture-agent  
**Riesgo:** HIGH  
**Estado:** AUDIT_ONLY — cero cambios productivos  
**Fecha:** 2026-06-10

---

## Problema

`modules/shared/` fue creado como contenedor de código transversal, pero ha acumulado carpetas que merecen revisión:

- `shared/audit/` — contiene `AuditTracer` matemático (correcto) pero en fases anteriores también tenía shims de trazabilidad (ya eliminados)
- `shared/lineage/` — modelos y query del grafo de lineage
- `shared/infrastructure/lineage/` — emitters e implementaciones de persistencia de lineage
- `shared/profitability/` — calculadoras de rentabilidad usadas por múltiples dominios
- `shared/precision.py` — rounding financiero compatible con Excel
- `shared/persistence/` — `SnapshotRepository`
- `shared/use_cases/` — casos de uso de audit y certificación

---

## Regla arquitectónica

`modules/shared/` **PUEDE** contener:

- Modelos de dominio compartidos (contratos Pydantic estables)
- Protocolos/interfaces (ports) usados por varios dominios
- Utilidades numéricas sin dueño de dominio claro y con múltiples consumidores cross-domain
- Infraestructura transversal (settings, middlewares, exception handlers)
- Constantes globales genuinas

`modules/shared/` **NO DEBE** contener:

- Lógica de dominio con dueño de dominio claro y único consumidor
- FastAPI routers específicos de un dominio (sí puede tener routers transversales)
- Repositories que solo sirven a un módulo

---

## Inventario completo

### Inventario de carpetas

| Carpeta | Archivos .py | Responsabilidad actual | ¿Es realmente shared? | Problema | Acción |
|---|:---:|---|:---:|---|---|
| `shared/audit/` | 3 | `AuditTracer`, `trace()`, router HTTP audit | SÍ | Correcto — transversal a 7+ módulos | KEEP_SHARED |
| `shared/lineage/` | 3 | Modelos `LineageGraph`, `LineageNode`, `LineageRef`, `LineageQuery` | SÍ | Modelos de datos compartidos por traceability + infra + tests | KEEP_SHARED |
| `shared/infrastructure/lineage/` | 4 | Emitters JSON/Null, `LineageSnapshotRepository` | MAYORMENTE | Infraestructura de lineage. Candidato a `traceability/infrastructure/` en fase posterior | DO_NOT_MOVE_NOW |
| `shared/profitability/` | 2 | `ProfitabilityCalculator` — factor_billing, ingreso_desde_costo | SÍ | 6+ consumidores en dominios distintos (calculator, pyg, vision_tarifas) | KEEP_SHARED |
| `shared/precision.py` | 1 | `cop_round`, `excel_round`, `pct_round`, `nexa_round` | SÍ | 6+ consumidores cross-domain (cadena_b/c, vision_tarifas, vision_imprimible, calculator) | KEEP_SHARED |
| `shared/models/` | 7 | `PricingRequest`, `PricingResult`, `PanelDeControl`, visions, resultados | SÍ | Contratos transversales del motor | KEEP_SHARED |
| `shared/ports/` | 3 | `IParametrizationProvider`, `ILogger`, `ITraceEmitter` | SÍ | Protocolos/interfaces estables | KEEP_SHARED |
| `shared/contracts/` | 12 | DTOs request/response de API v1 | SÍ | Contratos públicos de la API | KEEP_SHARED |
| `shared/exceptions.py` | 1 | `DomainError`, `NotFoundError`, `ValidationError`, etc. | SÍ | Jerarquía de excepciones compartida | KEEP_SHARED |
| `shared/responses.py` | 1 | `ApiResponse`, `ErrorDetail` | SÍ | Wrapper de respuesta HTTP transversal | KEEP_SHARED |
| `shared/infrastructure/` (no lineage) | 7 | App settings, middlewares, exception handlers, env_loader, lifespan | SÍ | Infraestructura de aplicación transversal | KEEP_SHARED |
| `shared/persistence/` | 2 | `SnapshotRepository` (DocumentStore) | PARCIAL | Solo 1 consumidor prod (`calculate_dependencies`). Candidato a `calculator_persistence/` | DO_NOT_MOVE_NOW |
| `shared/use_cases/` | 3 | `AuditSimulationUseCase`, `CertifiedCalculationUseCase` | SÍ | Cross-cutting: usados por `api/`, `calculator/api/`, `certification/` | KEEP_SHARED |
| `shared/certification/` | 5 | `CertificateRepository`, modelos de certificación, router HTTP | SÍ | Certificación transversal | KEEP_SHARED |
| `shared/versioning/` | 2 | `VersionRegistry`, `VersionMetadata` | SÍ | Versionado transversal (calculator, audit, lineage, certification) | KEEP_SHARED |
| `shared/config/` | 3 | `business_rules/loader.py` | SÍ | Config transversal | KEEP_SHARED |
| `shared/helpers/` | 2 | `certified_helpers.py` | SÍ | Helpers de certificación — solo 1 consumidor | DO_NOT_MOVE_NOW |
| `shared/i_parametrization_provider.py` | 1 | Alias/shim de `ports/parametrization_provider.py` | REVISAR | Posible duplicación con `ports/` | VERIFY_DUPLICATION |

---

## Matriz por archivo — candidatos a revisión

### `shared/audit/trace.py` (292 LOC)

| Clase/func | Qué hace | Consumidores prod | ¿Es shared? |
|---|---|:---:|:---:|
| `AuditTracer` | Tracer matemático con `entry()`, `export()`, `to_dict()` | 7+ módulos (formulas, cadena_b/c, pyg, traceability) | **SÍ** |
| `trace()` | Decorador/función helper para emitir trazas | 5+ módulos | **SÍ** |
| `get_tracer()` | Acceso al tracer activo del hilo | 15+ test imports | **SÍ** |
| `set_active_tracer()` / `clear_active_tracer()` | Lifecycle del tracer | `traceability/audit/integration.py` | **SÍ** |

**Veredicto: KEEP_SHARED.** Correcto aquí. Moverlo a `traceability/` crearía una cascada masiva de cambios sin beneficio arquitectónico real (los dominios como `cadena_b`, `pyg` no dependen de `traceability/`).

### `shared/lineage/models.py` (288 LOC) y `query.py` (153 LOC)

| Clase/func | Qué hace | Consumidores prod | ¿Es shared? |
|---|---|:---:|:---:|
| `LineageGraph`, `LineageNode`, `LineageRef` | Modelos de datos del grafo de lineage | `traceability/lineage_builder`, `shared/infra/lineage/*`, `shared/use_cases/*`, `audit_router` | **SÍ** |
| `LineageQuery` | Query sobre el grafo (find_path, explain) | `shared/use_cases/audit_simulation`, 6 tests | **SÍ** |

**Veredicto: KEEP_SHARED.** Estos son modelos de datos puros (dataclasses sin IO). `traceability/lineage_builder.py` los importa — si se movieran a `traceability/`, `traceability/` se importaría a sí misma indirectamente. Los modelos deben vivir en `shared/` como contratos estables.

### `shared/infrastructure/lineage/` (3 archivos, ~440 LOC total)

| Archivo | Qué hace | Consumidores prod | Candidato a mover |
|---|---|:---:|:---:|
| `json_lineage_emitter.py` | Emitter JSON que escribe al filesystem | `calculator/engine.py` (lazy), 5 tests | `traceability/infrastructure/` en fase posterior |
| `null_emitter.py` | Emitter no-op | `calculator/engine.py` (lazy) | Junto con json_lineage_emitter |
| `snapshot_repository.py` | `LineageSnapshotRepository` — DocumentStore | `calculate_dependencies.py`, `use_cases/certified_calculation`, 8 tests | `traceability/infrastructure/` o `calculator_persistence/` en fase posterior |

**Veredicto: DO_NOT_MOVE_NOW.** Los emitters e implementación son candidatos legítimos para `traceability/infrastructure/`, pero tienen 8+ tests y consumidores en múltiples módulos. Mover en una fase dedicada con planificación exhaustiva.

### `shared/profitability/calculators.py` (100 LOC)

| Clase/func | Qué hace | Consumidores prod | ¿Es shared? |
|---|---|:---:|:---:|
| `ProfitabilityCalculator.calcular_factor_billing()` | Factor denominador de billing (WAVE 3 V2-7) | `calculator/formulas/pricing`, `calculator/formulas/costos_financieros`, `pyg/services/kpis_calculator`, `pyg/services/pyg_calculator`, `vision_tarifas/reglas` (+ 2 mixins) | **SÍ** |
| `ProfitabilityCalculator.calcular_ingreso_desde_costo()` | Ingreso bruto desde costo + factor | `calculator/use_cases/build_pricing` | **SÍ** |
| `ProfitabilityCalculator.calcular_factor_margenes()` | Factor combinado de márgenes | `calculator/helpers/console_reporter` | **SÍ** |

**Veredicto: KEEP_SHARED — CORRECTO AQUÍ.** `ProfitabilityCalculator` es cross-domain genuino: lo usan `calculator/`, `pyg/` y `vision_tarifas/`. Si se moviera a `calculator/formulas/profitability/`, `pyg/` y `vision_tarifas/` importarían desde `calculator/` — violación de boundaries (dominios no deben importar desde otro dominio de negocio). `shared/profitability/` es el lugar correcto.

### `shared/precision.py` (129 LOC)

**Veredicto: KEEP_SHARED — CORRECTO AQUÍ.** `cop_round`, `excel_round`, `pct_round`, `nexa_round` son usados por `cadena_b`, `cadena_c`, `vision_tarifas`, `vision_imprimible`, `calculator/formulas/costos_financieros`. Cross-domain genuino.

### `shared/persistence/snapshots_repository.py`

**Veredicto: DO_NOT_MOVE_NOW.** Solo 1 consumidor prod (`calculate_dependencies.py`). Candidato a `calculator_persistence/` en Fase 6C, junto con el resto de persistence de calculator.

### `shared/i_parametrization_provider.py`

| Archivo | LOC | Consumidores |
|---|:---:|:---:|

Pendiente verificar si es shim de `shared/ports/parametrization_provider.py` o si agrega valor.

---

## Análisis de ciclos

### Mapa de dependencias actuales

```
calculator/formulas/* → shared/audit/trace         (OK — shared no importa formulas)
calculator/formulas/* → shared/profitability        (OK)
calculator/formulas/* → shared/precision            (OK)
traceability/audit/integration → shared/audit/trace (OK)
traceability/lineage_builder → shared/lineage/models (OK — modelos puros)
shared/infrastructure/lineage/* → shared/lineage/models (OK — mismo módulo)
shared/use_cases/* → shared/lineage/*, shared/versioning, shared/infra/lineage (OK)
pyg/* → shared/profitability, shared/audit/trace    (OK)
vision_tarifas/* → shared/profitability, shared/precision (OK)
```

### Movimientos que CREARÍAN ciclos (BLOQUEADOS)

| Movimiento propuesto | Ciclo resultante | Veredicto |
|---|---|---|
| `shared/profitability/` → `calculator/formulas/profitability/` | `pyg/` y `vision_tarifas/` importarían `calculator/` | BLOQUEADO |
| `shared/lineage/models.py` → `traceability/lineage/models.py` | `traceability/lineage_builder.py` importaría `traceability/` (ciclo interno) | BLOQUEADO |
| `shared/audit/trace.py` → `traceability/audit/trace.py` | `cadena_b`, `cadena_c`, `pyg/` importarían `traceability/` (cascade) | BLOQUEADO si `traceability` no es shared |

---

## Veredicto global

**`modules/shared/` está mayormente bien organizado.** Las carpetas que parecían sospechosas son en realidad correctas:

- `shared/profitability/` — cross-domain genuino (no mover a calculator)
- `shared/precision.py` — cross-domain genuino (mantener)
- `shared/lineage/` — modelos de datos compartidos (mantener)
- `shared/audit/trace.py` — infraestructura matemática transversal (mantener)

**Candidatos reales para mover (en fases futuras):**

1. `shared/infrastructure/lineage/` → `traceability/infrastructure/` (emitters + snapshot_repo)
2. `shared/persistence/snapshots_repository.py` → `calculator_persistence/` (junto con Fase 6C)
3. `shared/i_parametrization_provider.py` → verificar si es shim eliminable

**No candidatos (KEEP_SHARED confirmado):**

- `shared/audit/trace.py` — cross-domain con 7+ consumidores activos
- `shared/lineage/models.py` + `query.py` — modelos de datos puros compartidos
- `shared/profitability/calculators.py` — cross-domain (calculator + pyg + vision_tarifas)
- `shared/precision.py` — cross-domain (cadena_b/c + vision_tarifas + calculator)
- `shared/models/`, `shared/ports/`, `shared/contracts/` — contratos y protocolos
- `shared/exceptions.py`, `shared/responses.py` — transversales
- `shared/use_cases/`, `shared/versioning/`, `shared/certification/` — cross-cutting

---

## Mapa de consumidores — candidatos a mover

### `shared/infrastructure/lineage/` (candidato futuro a `traceability/infrastructure/`)

| Símbolo | Consumidores prod | Consumidores tests | Riesgo |
|---|:---:|:---:|:---:|
| `JsonLineageEmitter` | `calculator/engine.py` (lazy), `shared/infra/__init__` | 5 tests (lineage, versioning) | MEDIO |
| `NullLineageEmitter` | `calculator/engine.py` (lazy) | 1 test | BAJO |
| `LineageSnapshotRepository` | `calculate_dependencies.py`, `use_cases/certified_calculation` | 8 tests (lineage, versioning, api, cert) | ALTO |

### `shared/persistence/snapshots_repository.py` (candidato a `calculator_persistence/`)

| Símbolo | Consumidores prod | Consumidores tests |
|---|:---:|:---:|
| `SnapshotRepository` | `calculate_dependencies.py` | 1 test (`test_snapshot_persistence`) |

---

## Estructura objetivo (fases futuras)

```
modules/shared/              ← ESTADO FINAL OBJETIVO
  audit/
    trace.py                 ← KEEP (AuditTracer — cross-domain)
    api/                     ← KEEP (router HTTP de auditoría)
  lineage/
    models.py                ← KEEP (modelos de datos lineage — shared)
    query.py                 ← KEEP (LineageQuery — shared)
  infrastructure/
    [sin lineage/]           ← lineage/ se moverá a traceability/ en fase posterior
  profitability/             ← KEEP (cross-domain: calculator + pyg + vision_tarifas)
  precision.py               ← KEEP (cross-domain: cadena_b/c + vision_tarifas + calc)
  models/                    ← KEEP
  ports/                     ← KEEP
  contracts/                 ← KEEP
  exceptions.py              ← KEEP
  responses.py               ← KEEP
  use_cases/                 ← KEEP
  versioning/                ← KEEP
  certification/             ← KEEP
  helpers/                   ← KEEP (certified_helpers)
  persistence/               ← MOVER a calculator_persistence/ (junto con Fase 6C)
    [snapshots_repository.py solo]

modules/traceability/        ← ESTADO OBJETIVO FINAL
  audit/
    integration.py           ← YA MOVIDO (6B-1)
    writer.py                ← YA MOVIDO (6B-1)
    registry.py              ← YA MOVIDO (6B-1)
  lineage/
    lineage_builder.py       ← YA MOVIDO (6B-1)
  infrastructure/            ← FASE FUTURA (6D-A/B)
    json_lineage_emitter.py
    null_emitter.py
    snapshot_repository.py   ← o en calculator_persistence/
```

---

## Plan por fases

### Fase 6D-A — Mover `shared/infrastructure/lineage/` a `traceability/infrastructure/`

- **Archivos:** `json_lineage_emitter.py`, `null_emitter.py`, `snapshot_repository.py`
- **Consumidores a actualizar:** `calculator/engine.py` (lazy), `calculate_dependencies.py`, `use_cases/certified_calculation.py`, `shared/use_cases/audit_simulation.py`, 8+ tests
- **Riesgo:** ALTO — 8+ consumidores en tests, lazy imports en engine
- **Shims:** Sí, en `shared/infrastructure/lineage/__init__.py` por 1 ciclo
- **Prerrequisito:** Fase 6C (persistence) no es necesaria para esta fase
- **Decisión:** Requiere planificación dedicada

### Fase 6D-B — Mover `shared/persistence/snapshots_repository.py` a `calculator_persistence/`

- **Candidato:** Absorber en Fase 6C junto con `calculator/persistence/results_repository.py` y `traceability_repository.py`
- **Consumidores:** `calculate_dependencies.py` (ya migrará en 6C), 1 test
- **Riesgo:** BAJO

### Fase 6D-C — Verificar `shared/i_parametrization_provider.py`

- **Acción:** Verificar si es shim de `shared/ports/parametrization_provider.py`
- **Si es shim con 0 consumers:** DELETE_SAFE
- **Riesgo:** BAJO

### Fase 6D-D — Guardrails finales de shared boundaries

- Tests que validan que `shared/` no contiene infraestructura de un solo dominio
- Tests que `shared/profitability` no importa `calculator/` (solo shared interno)
- Tests que `shared/lineage/models` no importa `traceability/`

---

## Candidatos de implementación inmediata

### `shared/i_parametrization_provider.py` — verificar si es shim eliminable

```bash
grep -Rn "i_parametrization_provider\|IParametrizationProvider" modules tests --include="*.py"
```

Si tiene 0 consumidores directos, es DELETE_SAFE.

---

## Guardrails propuestos

```python
"""tests/unit/test_shared_boundary_guardrails.py"""

class TestSharedBoundaryIntegrity:
    def test_shared_profitability_no_imports_from_calculator(self):
        """shared/profitability must not import from calculator (would violate cross-domain)."""
        ...

    def test_shared_lineage_models_no_imports_from_traceability(self):
        """shared/lineage/models must not import from traceability (would create cycle)."""
        ...

    def test_shared_audit_trace_no_imports_from_calculator(self):
        """shared/audit/trace.py must not import from calculator."""
        ...

    def test_precision_no_io_imports(self):
        """shared/precision.py must not import fastapi/documentstore/etc."""
        ...
```

---

## Decisión

**AUDIT_ONLY** — La auditoría revela que `modules/shared/` está **mayormente bien organizado**. Las piezas que parecían candidatas a mover son en realidad correctas en `shared/` por ser cross-domain genuinas.

**Movimientos no implementados en esta corrida:**
- `shared/infrastructure/lineage/` → requiere planificación dedicada (Fase 6D-A)
- `shared/persistence/` → absorber en Fase 6C

**No se recomienda mover en fases futuras:**
- `shared/profitability/calculators.py` — BLOQUEADO por ciclos
- `shared/lineage/models.py` — BLOQUEADO por ciclos
- `shared/audit/trace.py` — BLOQUEADO (cascade masiva sin beneficio)
- `shared/precision.py` — KEEP (cross-domain genuino)

---

## Hallazgo adicional: `shared/i_parametrization_provider.py` vs `shared/ports/parametrization_provider.py`

| Archivo | Tipo | LOC | Consumidores prod |
|---|---|:---:|:---:|
| `shared/i_parametrization_provider.py` | **IMPLEMENTACIÓN** (Protocol real, 20+ métodos) | ~200 | 8+ (context_builder, engine, mixins, formulas, cadena_c) |
| `shared/ports/parametrization_provider.py` | **SHIM** — re-exporta desde `i_parametrization_provider` con nota "WAVE 9 strangler" | ~15 | Consumidores que importan desde `ports/` |

**Resolución:** `i_parametrization_provider.py` es la fuente canónica correcta. `ports/parametrization_provider.py` es un shim. La separación actual funciona y no requiere cambios inmediatos. En fase futura se puede consolidad en `ports/` como canónico.

**Acción:** DO_NOT_MOVE_NOW.
