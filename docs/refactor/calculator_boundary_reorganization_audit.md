# Calculator Boundary Reorganization Audit

**Fase:** 6A — AUDIT_ONLY  
**Worker:** architecture-agent  
**Riesgo:** HIGH  
**Estado:** AUDIT_ONLY — cero cambios productivos  
**Fecha:** 2026-06-09

---

## Problema

`modules/calculator/` mezcla responsabilidades. Contiene no solo el motor de cálculo puro (engine, formulas, context_builder) sino también:

- Routers FastAPI y handlers HTTP (`api/`)
- Repositorios de persistencia + DocumentStore (`persistence/`)
- Writers y registry de trazabilidad de auditoría (`audit/`)
- Builder de nodos de lineage (`lineage/`)
- Un reporter de consola CLI (`helpers/console_reporter.py`)

Esta mezcla viola la regla arquitectónica del proyecto: `modules/calculator` es el motor de cálculo, no un módulo vertical completo con API, persistencia e infraestructura.

---

## Regla arquitectónica objetivo

`modules/calculator/` debe contener únicamente código de **cálculo puro**:

```
engine.py
context_builder.py
input_normalizer.py
input_validator.py
formulas/
adapters/
dto/
models/
serializers/     (si serializan PricingResult internamente)
validation/
use_cases/       (solo si no tocan infra)
mixins/
constants/
helpers/engine_helpers.py   (helpers de engine sin IO externo)
shared/          (interfaz pública del módulo)
```

**Prohibido en `modules/calculator/`:**

- FastAPI routers, handlers, DTOs HTTP, dependencies
- Repositories, DocumentStore, Cosmos/JSON providers
- Audit writers, traceability writers, lineage builders
- Storage, persistencia, snapshots
- Console reporters / debug printers

---

## Estructura actual vs objetivo

### Actual

```
modules/calculator/
  engine.py                          ✅ KEEP
  context_builder.py                 ✅ KEEP
  input_normalizer.py                ✅ KEEP
  input_validator.py                 ✅ KEEP
  __init__.py                        ✅ KEEP
  adapters/                          ✅ KEEP
  dto/                               ✅ KEEP
  formulas/                          ✅ KEEP
  mixins/                            ✅ KEEP
  models/                            ✅ KEEP
  serializers/                       ✅ KEEP (serialización interna de PricingResult)
  validation/                        ✅ KEEP
  use_cases/                         ✅ KEEP (sin imports de infra)
  constants/                         ✅ KEEP
  shared/                            ✅ KEEP (interfaz pública)

  api/                               ❌ MOVER → modules/calculator_api/
  persistence/                       ❌ MOVER → modules/calculator_persistence/
  audit/                             ❌ MOVER → modules/traceability/audit/
  lineage/                           ❌ MOVER → modules/traceability/lineage/
  helpers/console_reporter.py        ❌ MOVER → modules/calculator_dev_tools/ o eliminar
  helpers/engine_helpers.py          ✅ KEEP (helpers de cálculo puro)
```

### Objetivo

```
modules/
  calculator/                        ← MOTOR PURO (cálculo, context, adapters)
  calculator_api/                    ← NUEVO: FastAPI routers + handlers
  calculator_persistence/            ← NUEVO: repositories + DocumentStore
  traceability/                      ← NUEVO: audit, lineage, registry, writers
```

---

## Matriz por carpeta

| Carpeta actual | Responsabilidad actual | ¿Es cálculo? | Problema | Destino recomendado | Acción |
|---|---|:---:|---|---|---|
| `api/` | FastAPI routers, handlers HTTP, DTOs HTTP, dependencies con DocumentStore | NO | Mezcla HTTP + cálculo en mismo módulo | `modules/calculator_api/` | MOVE_TO_CALCULATOR_API |
| `persistence/` | `ResultsRepository`, `TraceabilityRepository` usando DocumentStore | NO | Repository de infra en módulo de cálculo | `modules/calculator_persistence/` | MOVE_TO_CALCULATOR_PERSISTENCE |
| `audit/` | `TraceabilityWriter`, `FieldTraceabilityRegistry`, `trace_integration` | NO | Escritura de auditoría no es cálculo | `modules/traceability/audit/` | MOVE_TO_TRACEABILITY |
| `lineage/` | `lineage_builder` — emite nodos de lineage desde PricingResult | PARCIAL | Describe resultados, no calcula; depende de `shared.lineage.models` | `modules/traceability/lineage/` | MOVE_TO_TRACEABILITY |
| `helpers/console_reporter.py` | Imprime PricingResult en consola — CLI/debugging | NO | Reporter de presentación en módulo de cálculo | `modules/calculator_dev_tools/` o eliminar | MOVE_OR_DELETE |
| `helpers/engine_helpers.py` | `_calcular_waterfall`, `_calcular_reglas_negocio` — pura matemática | SÍ | Correcto aquí | `helpers/` (actual) | KEEP_IN_CALCULATOR |
| `use_cases/` | `BuildPricingUseCase`, `BuildVisionsUseCase` — solo orquestan cálculo, sin infra | SÍ | Sin imports de persistencia/API | `use_cases/` (actual) | KEEP_IN_CALCULATOR |
| `serializers/` | `pricing_result_to_dict` — serializa `PricingResult` internamente | SÍ | Serialización interna del resultado del motor | `serializers/` (actual) | KEEP_IN_CALCULATOR |
| `adapters/` | `UserInputLoader`, `entry_data_adapter`, `volume_resolution` | SÍ | Transformación de input para el motor | `adapters/` (actual) | KEEP_IN_CALCULATOR |
| `formulas/` | Calculadoras puras (nomina, no_payroll, pricing, risk, costos_financieros) | SÍ | Correcto | `formulas/` (actual) | KEEP_IN_CALCULATOR |
| `mixins/` | Mixins de `ContextBuilder` e `InputNormalizer` | SÍ | Correcto | `mixins/` (actual) | KEEP_IN_CALCULATOR |
| `models/` | `SimulationSnapshot`, `DataProvenance` — modelos de dominio del motor | SÍ | Correcto | `models/` (actual) | KEEP_IN_CALCULATOR |
| `dto/` | DTOs internos del motor | SÍ | Correcto | `dto/` (actual) | KEEP_IN_CALCULATOR |
| `validation/` | `ContractValidator`, `SimulationRequestValidator` | SÍ | Validación de input del motor | `validation/` (actual) | KEEP_IN_CALCULATOR |
| `constants/` | `global_constants.py` | SÍ | Correcto | `constants/` (actual) | KEEP_IN_CALCULATOR |

---

## Matriz por archivo sospechoso

| Archivo | Qué hace | Por qué no debería estar en calculator | Destino recomendado | Riesgo | Fase propuesta |
|---|---|---|---|:---:|---|
| `api/calculate_router.py` | Router FastAPI `/simulation/calculate` — endpoint POST | FastAPI es infraestructura HTTP, no cálculo | `calculator_api/calculate_router.py` | ALTO | 6D |
| `api/calculate_normal_handler.py` | Handler de la ruta normal — ejecuta engine + persistencia | Mezcla engine call + persistencia + serialización HTTP | `calculator_api/handlers/calculate_normal.py` | ALTO | 6D |
| `api/calculate_certified_handler.py` | Handler modo certificado | Ídem anterior | `calculator_api/handlers/calculate_certified.py` | ALTO | 6D |
| `api/calculate_dependencies.py` | Singletons `_results_repo`, `_trace_writer`, `_snapshot_repo`, `_lineage_repo` — instancia `get_provider()` | Composition root de infra en módulo de cálculo; importa `db.factory` | `calculator_api/dependencies.py` | ALTO | 6D |
| `api/calculate_dto.py` | `CalculationRequest` Pydantic — DTO del endpoint HTTP | DTO de la capa HTTP no debería estar en módulo de cálculo | `calculator_api/dto/calculation_request.py` | MEDIO | 6D |
| `api/calculate_validate.py` | Endpoint `POST /validate` — diagnóstico de input | Endpoint HTTP | `calculator_api/validate_router.py` | MEDIO | 6D |
| `api/results_router.py` | Router `GET /simulation/{id}/results/*` | Router FastAPI | `calculator_api/results_router.py` | ALTO | 6D |
| `persistence/results_repository.py` | `ResultsRepository` con DocumentStore — persiste `PricingResult` | Repository de infra en módulo de cálculo | `calculator_persistence/results_repository.py` | ALTO | 6C |
| `persistence/traceability_repository.py` | `TraceabilityRepository` con DocumentStore — persiste trazabilidad | Repository de infra en módulo de cálculo | `calculator_persistence/traceability_repository.py` | ALTO | 6C |
| `audit/trace_integration.py` | Context manager `audit_context` — activa `AuditTracer` en engine | Integración de auditoría; importa desde `shared.audit.trace` | `traceability/audit/trace_integration.py` | MEDIO | 6B |
| `audit/traceability_registry.py` | `FieldTraceabilityRegistry` — clasifica campos desde resultado persistido | Registry de trazabilidad no es cálculo puro | `traceability/registry/traceability_registry.py` | BAJO | 6B |
| `audit/traceability_writer.py` | `TraceabilityWriter` — serializa `PricingResult` y persiste via `TraceabilityRepository` | Writer de persistencia en módulo de cálculo | `traceability/writers/traceability_writer.py` | MEDIO | 6B |
| `lineage/lineage_builder.py` | `seed_lineage_from_request/result` — emite nodos de lineage | Describe outputs para trazabilidad; no calcula; usa `shared.lineage.models` | `traceability/lineage/lineage_builder.py` | MEDIO | 6B |
| `helpers/console_reporter.py` | Imprime `PricingResult` en consola — usa `ProfitabilityCalculator` | Reporter de presentación; no pertenece al motor de cálculo | `calculator_dev_tools/console_reporter.py` o eliminar | BAJO | 6F |
| `helpers/engine_helpers.py` | `_calcular_waterfall`, `_calcular_reglas_negocio` — matemática pura | Correcto aquí — son helpers del pipeline del motor | (actual) | — | KEEP |

---

## Mapa de consumidores

### `modules/calculator/api/`

| Path actual | Consumidores productivos | Consumidores tests | Riesgo de mover |
|---|:---:|:---:|---|
| `api/calculate_router.py` | 1 (`modules/api_v1/router.py`) | 0 | ALTO — punto de montaje principal |
| `api/results_router.py` | 1 (`modules/api_v1/router.py`) | 0 | ALTO — 4 GET endpoints de resultados |
| `api/calculate_dependencies.py` | 2 (handlers normal + certified) | 1 (`test_lineage_repository_documentstore_wiring`) | ALTO — singletons de infra |
| `api/calculate_normal_handler.py` | 1 (calculate_router) | 0 | ALTO |
| `api/calculate_certified_handler.py` | 1 (calculate_router) | 0 | ALTO |
| `api/calculate_dto.py` | 3 (router + 2 handlers) | ~5 tests | MEDIO |
| `api/calculate_validate.py` | 1 (calculate_router) | 0 | MEDIO |

**Nota crítica:** `modules/api_v1/router.py` importa directamente desde `calculator.api.calculate_router` y `calculator.api.results_router`. Este es el único punto de montaje al app — debe actualizarse en la misma fase.

### `modules/calculator/persistence/`

| Path actual | Consumidores productivos | Consumidores tests | Riesgo de mover |
|---|:---:|:---:|---|
| `persistence/results_repository.py` | `api/calculate_dependencies.py`, `api/results_router.py`, `vision_*` routers (4) | ~6 tests | ALTO |
| `persistence/traceability_repository.py` | `api/calculate_dependencies.py`, `audit/traceability_writer.py` | ~3 tests | ALTO |

**Nota:** `vision_imprimible/api/router.py`, `vision_cost_to_serve/api/router.py`, `vision_tarifas/api/router.py`, `pyg/api/vision_router.py` importan `ResultsRepository` directamente. Todos deben actualizarse.

### `modules/calculator/audit/`

| Path actual | Consumidores productivos | Consumidores tests | Riesgo de mover |
|---|:---:|:---:|---|
| `audit/trace_integration.py` | `engine.py` | 0 (indirecto) | MEDIO — engine lo importa |
| `audit/traceability_writer.py` | `api/calculate_dependencies.py` | ~2 tests | MEDIO |
| `audit/traceability_registry.py` | `api/results_router.py` | ~1 test | BAJO |

**Nota:** `modules/shared/audit/` ya contiene copias o versiones paralelas de `trace_integration.py`, `traceability_writer.py`, `traceability_registry.py`. Hay **duplicación activa** entre `calculator/audit/` y `shared/audit/`. Esto debe resolverse en la fase 6B.

### `modules/calculator/lineage/`

| Path actual | Consumidores productivos | Consumidores tests | Riesgo de mover |
|---|:---:|:---:|---|
| `lineage/lineage_builder.py` | `engine.py` (lazy import con `with_lineage=True`) | ~2 tests | MEDIO |

---

## Análisis de duplicación: `calculator/audit/` vs `shared/audit/`

Este es el hallazgo más crítico de la auditoría:

| Archivo en `calculator/audit/` | Contraparte en `shared/audit/` | Relación |
|---|---|---|
| `audit/trace_integration.py` | `shared/audit/trace_integration.py` | **DUPLICADO** — misma funcionalidad `audit_context` |
| `audit/traceability_writer.py` | `shared/audit/traceability_writer.py` | **DUPLICADO** — `TraceabilityWriter` repetido |
| `audit/traceability_registry.py` | `shared/audit/traceability_registry.py` | **DUPLICADO** — `FieldTraceabilityRegistry` repetido |

El motor (`engine.py`) importa desde `calculator/audit/`. Los tests y algunos consumers importan desde `shared/audit/`. **Existe riesgo de divergencia silenciosa entre las dos versiones.**

La fase 6B debe resolver esta duplicación eligiendo una fuente canónica (probablemente `shared/audit/`) y eliminando la otra.

---

## Análisis de riesgos de dependencias circulares

### Situación actual

```
calculator/api/calculate_dependencies.py
  → db.factory.get_provider()            ← infra directa
  → calculator/persistence/...           ← repo del mismo módulo
  → calculator/audit/traceability_writer ← audit del mismo módulo
  → shared/persistence/snapshots_repo    ← ok (shared)
  → shared/infrastructure/lineage/...   ← ok (shared)

calculator/audit/traceability_writer.py
  → calculator/persistence/traceability_repository ← mismo módulo
  → shared/models                        ← ok

calculator/engine.py
  → calculator/audit/trace_integration   ← audit dentro de calculator
  → calculator/lineage/lineage_builder   ← lineage dentro de calculator (lazy)
```

### Riesgos post-reorganización

| Riesgo | Descripción | Mitigación |
|---|---|---|
| `traceability` → `calculator.engine` | `lineage_builder` usa atributos de `PricingResult` y `PricingRequest` | Depender de `shared.models` (DTOs estables), no de `calculator.engine` — ya es el caso actualmente |
| `calculator_api` → `calculator` internals | Los handlers deben importar solo por `use_cases/` o `engine.py`, no por `formulas/` | Guardrail AST en fase 6G |
| `calculator_persistence` → `calculator.engine` | `ResultsRepository` no importa `engine.py` — solo recibe `dict` | Sin riesgo actual |
| Ciclo `traceability.writer` → `traceability.repository` → `calculator_persistence` | Posible si se colapsan módulos | Mantener separación writer / repository |

---

## Fases 6A–6G

### Fase 6A — Auditoría boundary (ACTUAL)
- **Objetivo:** inventario, matriz, consumidores, riesgos.
- **Archivos:** solo documentación.
- **Resultado:** este documento.

### Fase 6B — Mover `calculator/audit/` y `calculator/lineage/` a `modules/traceability/`
- **Archivos a mover:**
  - `calculator/audit/trace_integration.py` → `traceability/audit/trace_integration.py`
  - `calculator/audit/traceability_registry.py` → `traceability/registry/traceability_registry.py`
  - `calculator/audit/traceability_writer.py` → `traceability/writers/traceability_writer.py`
  - `calculator/lineage/lineage_builder.py` → `traceability/lineage/lineage_builder.py`
- **Prerrequisito crítico:** resolver duplicación con `shared/audit/` antes de mover.
  - Verificar cuál versión es canónica comparando imports y tests.
  - Si `shared/audit/` es canónica: actualizar `engine.py` para importar desde `shared/audit/`, luego eliminar `calculator/audit/`.
  - Si `calculator/audit/` es canónica: mover a `traceability/`, actualizar `shared/audit/` como shim temporal.
- **Imports a actualizar:** `engine.py` (2 imports), `api/calculate_dependencies.py`, `api/results_router.py`.
- **Shims temporales:** Permitidos en `calculator/audit/__init__.py` por 1 ciclo.
- **Tests mínimos:** guardrail `calculator/audit/` vacío post-migración, imports desde `traceability/` funcionan.
- **Rollback:** `git revert` de la fase.
- **Riesgos:** divergencia entre `calculator/audit/` y `shared/audit/` — investigar antes de iniciar.

### Fase 6C — Mover `calculator/persistence/` a `modules/calculator_persistence/`
- **Archivos a mover:**
  - `calculator/persistence/results_repository.py` → `calculator_persistence/results_repository.py`
  - `calculator/persistence/traceability_repository.py` → `calculator_persistence/traceability_repository.py`
- **Imports a actualizar:**
  - `api/calculate_dependencies.py`
  - `api/results_router.py`
  - `vision_imprimible/api/router.py`
  - `vision_cost_to_serve/api/router.py`
  - `vision_tarifas/api/router.py`
  - `pyg/api/vision_router.py`
  - `traceability/writers/traceability_writer.py` (post fase 6B)
  - `db/container.py` (si inyecta repos directamente)
  - ~6 tests
- **Shims temporales:** `calculator/persistence/__init__.py` re-exporta por 1 ciclo.
- **Tests mínimos:** `ResultsRepository` importable desde nuevo path, `TraceabilityRepository` ídem.
- **Rollback:** `git revert`.
- **Riesgos:** 4 routers de visions importan `ResultsRepository` directamente — riesgo ALTO de olvidar alguno.

### Fase 6D — Mover `calculator/api/` a `modules/calculator_api/`
- **Archivos a mover (todos los de `calculator/api/`):**
  - `calculate_router.py`, `results_router.py`, `calculate_dto.py`
  - `calculate_normal_handler.py`, `calculate_certified_handler.py`
  - `calculate_validate.py`, `calculate_dependencies.py`
- **Imports a actualizar:**
  - `modules/api_v1/router.py` (único punto de montaje — CRÍTICO)
  - Tests que importen desde `calculator.api.*`
- **Shims temporales:** `calculator/api/__init__.py` re-exporta routers por 1 ciclo.
- **Tests mínimos:** `GET /health` funciona, `POST /simulation/calculate` devuelve 201, `GET /simulation/{id}/results/*` devuelve 200.
- **Rollback:** `git revert`.
- **Riesgos:** ALTO — es el punto de entrada HTTP. Ejecutar en horario de baja carga o en rama feature.

### Fase 6E — (Completada en 5K-C)
`user_input_loader.py` ya está en `calculator/adapters/`. No se requiere acción.

### Fase 6F — Revisar `helpers/` — mover o eliminar `console_reporter.py`
- **Archivos candidatos:** `helpers/console_reporter.py`
- **Acción:**
  - Verificar si algún código de producción importa `ConsoleReporter`.
  - Si solo scripts/CLI lo usan: mover a `calculator_dev_tools/console_reporter.py`.
  - Si nadie lo usa: eliminar.
  - `helpers/engine_helpers.py` → KEEP (matemática pura, importado por `engine.py`).
- **Shims:** si hay consumidores, shim temporal en `calculator/helpers/__init__.py`.
- **Riesgos:** BAJO.

### Fase 6G — Gate final de boundaries
- **Objetivo:** Confirmar que `modules/calculator/` ya no contiene infra.
- **Acción:** Ejecutar guardrails (ver sección siguiente) + suite completa + snapshot diff.
- **Criterio de éxito:** 0 archivos en `calculator/api/`, `calculator/persistence/`, `calculator/audit/`, `calculator/lineage/`. Suite ≥ baseline (1249 pass / 57 fail).

---

## Guardrails propuestos para `tests/unit/test_calculator_boundary_guardrails.py`

```python
"""
Phase 6G — Calculator boundary guardrails.

Validates that modules/calculator/ contains only pure computation code
after the boundary reorganization.
"""
from __future__ import annotations
import ast
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_MODULES = _BACKEND_ROOT / "modules"
_CALC = _MODULES / "calculator"
_FORMULAS = _CALC / "formulas"

_FORBIDDEN_IN_FORMULAS = frozenset([
    "fastapi", "starlette", "DocumentStore", "cosmos", "azure",
    "json_document_store", "json_provider", "requests", "httpx",
    "results_repository", "traceability_repository",
    "traceability_writer", "lineage_builder",
])

_FORBIDDEN_DIRS_POST_6G = ["api", "persistence", "audit", "lineage"]


class TestCalculatorFormulasNoPureIOImports:
    """formulas/ must not import any infrastructure."""

    def test_formulas_no_forbidden_imports(self):
        violations = []
        for py in _FORMULAS.rglob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module = getattr(node, "module", "") or ""
                    names = [alias.name for alias in getattr(node, "names", [])]
                    for fb in _FORBIDDEN_IN_FORMULAS:
                        if fb.lower() in module.lower() or any(fb.lower() in n.lower() for n in names):
                            violations.append(f"{py.relative_to(_BACKEND_ROOT)}: {module or names}")
        assert not violations, "formulas/ imports forbidden infra symbols:\n" + "\n".join(violations)


class TestCalculatorNoBannedDirs:
    """After 6G: calculator/ must not contain api/, persistence/, audit/, lineage/."""

    def test_no_api_dir(self):
        assert not (_CALC / "api").exists(), "calculator/api/ must be deleted (moved to calculator_api/)"

    def test_no_persistence_dir(self):
        assert not (_CALC / "persistence").exists(), "calculator/persistence/ must be moved to calculator_persistence/"

    def test_no_audit_dir(self):
        assert not (_CALC / "audit").exists(), "calculator/audit/ must be moved to traceability/"

    def test_no_lineage_dir(self):
        assert not (_CALC / "lineage").exists(), "calculator/lineage/ must be moved to traceability/"


class TestNewModulesImportable:
    """New target modules must be importable after their respective phases."""

    def test_calculator_api_importable(self):
        from nexa_engine.modules.calculator_api import calculate_router  # noqa: F401

    def test_calculator_persistence_importable(self):
        from nexa_engine.modules.calculator_persistence import results_repository  # noqa: F401

    def test_traceability_importable(self):
        from nexa_engine.modules import traceability  # noqa: F401


class TestNoLegacyImportsAfterMigration:
    """No production code may import from old paths after each phase completes."""

    def test_no_production_imports_to_calculator_audit(self):
        fragment = "calculator.audit"
        violations = [
            str(py.relative_to(_BACKEND_ROOT))
            for py in _MODULES.rglob("*.py")
            if fragment in py.read_text(encoding="utf-8")
        ]
        assert not violations

    def test_no_production_imports_to_calculator_persistence(self):
        fragment = "calculator.persistence"
        violations = [
            str(py.relative_to(_BACKEND_ROOT))
            for py in _MODULES.rglob("*.py")
            if fragment in py.read_text(encoding="utf-8")
        ]
        assert not violations
```

**Nota:** Los guardrails de 6G deben activarse solo DESPUÉS de que la fase correspondiente esté completa. Añadir `pytest.mark.skip(reason="activar post-fase 6X")` hasta entonces.

---

## Riesgos abiertos

| # | Riesgo | Severidad | Mitigación |
|---|---|:---:|---|
| R1 | Duplicación activa `calculator/audit/` vs `shared/audit/` — versiones pueden divergir silenciosamente | CRÍTICO | Resolver en inicio de fase 6B (auditar versiones antes de mover) |
| R2 | 4 routers de visions importan `ResultsRepository` directamente desde `calculator.persistence` — alto riesgo de olvidar uno | ALTO | Pre-grep exhaustivo antes de fase 6C |
| R3 | `api_v1/router.py` es el único punto de montaje HTTP — si falla, toda la API cae | ALTO | Test de integración smoke pre/post en fase 6D |
| R4 | `engine.py` importa `audit_context` lazy (no en startup) — puede fallar en runtime si el path cambia | MEDIO | Test de integración que ejecute `engine.calcular()` con `audit=True` |
| R5 | `calculate_dependencies.py` instancia `get_provider()` en import time — si mueve de ubicación puede cambiar working directory | MEDIO | Verificar `settings.*_root` paths post-movimiento |
| R6 | Tests de integración que importan `calculator.api.*` directamente quedarán rotos post-6D | BAJO | Pre-grep de tests antes de iniciar 6D |

---

## Decisión

**AUDIT_ONLY — cero cambios productivos en esta fase.**

El veredicto es **CONFIRMADO**: `modules/calculator/` mezcla responsabilidades significativas. Los módulos `api/`, `persistence/`, `audit/`, y `lineage/` no pertenecen al motor de cálculo y deben reorganizarse en fases controladas (6B–6G).

La reorganización no es urgente desde el punto de vista funcional — el código funciona correctamente. El beneficio es arquitectónico: separar el motor de cálculo puro de la infraestructura HTTP, persistencia y trazabilidad.

**Prerrequisito antes de iniciar cualquier fase:** resolver la duplicación `calculator/audit/` vs `shared/audit/` (riesgo R1).

---

## Phase 6B-0 — Audit Duplication Resolution

**Fecha:** 2026-06-10  
**Estado:** AUDIT_ONLY — cero cambios productivos

### Hallazgo principal: no hay duplicación funcional

Lo que parecía duplicación activa es en realidad una relación de **shim → canónico bien definida**:

```
modules/calculator/audit/       ← FUENTES CANÓNICAS (implementación real)
  trace_integration.py   (95 LOC)
  traceability_writer.py (243 LOC)
  traceability_registry.py (54 LOC)

modules/shared/audit/           ← SHIMS (11, 10, 10 LOC)
  trace_integration.py   → re-exporta desde calculator.audit.trace_integration
  traceability_writer.py → re-exporta desde calculator.audit.traceability_writer
  traceability_registry.py → re-exporta desde calculator.audit.traceability_registry
```

Cada shim en `shared/audit/` contiene solo 10-11 líneas y re-exporta explícitamente. El docstring de cada shim declara:

> `moved to modules.calculator.audit.* in FASE SHARED.2 (2026-06-04). Remove this shim once no callers remain.`

No existe duplicación funcional. Solo hay tres shims de backward-compat que apuntan al canónico.

### Inventario comparativo

| Archivo | `calculator/audit/` | `shared/audit/` | LOC calc | LOC shared | Relación |
|---|:---:|:---:|:---:|:---:|---|
| `trace_integration.py` | ✅ implementación | ✅ shim | 95 | 11 | CALC_CANONICAL — shared es shim |
| `traceability_writer.py` | ✅ implementación | ✅ shim | 243 | 10 | CALC_CANONICAL — shared es shim |
| `traceability_registry.py` | ✅ implementación | ✅ shim | 54 | 10 | CALC_CANONICAL — shared es shim |
| `trace.py` | ❌ no existe | ✅ implementación | — | 292 | SHARED_CANONICAL — `AuditTracer`, `trace()` |
| `api/audit_router.py` | ❌ no existe | ✅ implementación | — | ~130 | SHARED_CANONICAL — endpoints GET /audit/* |

**`shared/audit/trace.py` es completamente distinto** — define `AuditTracer`, `TraceEntry`, `get_tracer()`, `trace()`. Es la clase matemática de tracing usada por las fórmulas (payroll, no_payroll, costos_financieros, pyg). **No está duplicado.**

### Mapa completo de consumidores

#### `modules/calculator/audit/` (fuentes canónicas)

| Símbolo | Consumidores productivos | Consumidores tests |
|---|---|---|
| `audit_context`, `export_audit_trace` | `calculator/engine.py` (directo), `shared/audit/trace_integration.py` (shim) | `tests/refactor/test_formula_trace_runtime_query.py` |
| `TraceabilityWriter` | `calculator/api/calculate_dependencies.py`, `shared/audit/traceability_writer.py` (shim) | `tests/integration/test_traceability_polizas_source.py` |
| `FieldTraceabilityRegistry` | `calculator/api/results_router.py`, `shared/audit/traceability_registry.py` (shim) | `tests/unit/test_shared_guardrails.py` (guardrail) |

#### `modules/shared/audit/` (mezcla de implementaciones y shims)

| Archivo | Tipo | Símbolo | Consumidores productivos | Consumidores tests |
|---|---|---|---|---|
| `trace.py` | IMPLEMENTACIÓN | `AuditTracer`, `trace()`, `get_tracer()` | `calculator/audit/trace_integration.py`, `cadena_b/reglas.py`, `cadena_c/reglas.py`, `formulas/costos_financieros`, `formulas/no_payroll`, `formulas/payroll`, `pyg/services/*` | ~15 tests (audit, certificacion, formula_trace) |
| `api/audit_router.py` | IMPLEMENTACIÓN | router GET /audit/* | `api_v1/router.py` | `tests/security/test_path_traversal_prevention.py` |
| `trace_integration.py` | SHIM | `audit_context`, `export_audit_trace` | 0 consumidores directos productivos | 0 tests directos |
| `traceability_writer.py` | SHIM | `TraceabilityWriter` | 0 consumidores directos productivos | 0 tests directos |
| `traceability_registry.py` | SHIM | `FieldTraceabilityRegistry` | 0 consumidores directos productivos | 0 tests directos |

**Conclusión:** Los 3 shims en `shared/audit/` tienen **cero consumidores directos** — todos los consumidores reales ya usan `calculator.audit.*` directamente. Los shims son eliminables de forma segura.

### Decisión por archivo

| Archivo | Decisión | Justificación |
|---|---|---|
| `calculator/audit/trace_integration.py` | `CALCULATOR_AUDIT_CANONICAL` → mover a `traceability/` en 6B-1 | Implementación real, 2 consumidores productivos |
| `calculator/audit/traceability_writer.py` | `CALCULATOR_AUDIT_CANONICAL` → mover a `traceability/` en 6B-1 | Implementación real, 2 consumidores productivos |
| `calculator/audit/traceability_registry.py` | `CALCULATOR_AUDIT_CANONICAL` → mover a `traceability/` en 6B-1 | Implementación real, 2 consumidores productivos |
| `shared/audit/trace_integration.py` | `DELETE_SAFE` | Shim con 0 consumidores directos — eliminar en 6B-1 |
| `shared/audit/traceability_writer.py` | `DELETE_SAFE` | Shim con 0 consumidores directos — eliminar en 6B-1 |
| `shared/audit/traceability_registry.py` | `DELETE_SAFE` | Shim con 0 consumidores directos — eliminar en 6B-1 |
| `shared/audit/trace.py` | `SHARED_CANONICAL — KEEP` | `AuditTracer` matemático; usado por 7+ módulos productivos. No mover. |
| `shared/audit/api/audit_router.py` | `SHARED_CANONICAL — KEEP` | Router HTTP de auditoría; correcto en `shared/audit/api/`. No mover. |

### Estructura objetivo post-6B-1

```text
modules/traceability/
  __init__.py
  audit/
    __init__.py
    trace_integration.py     ← movido desde calculator/audit/
    traceability_writer.py   ← movido desde calculator/audit/
    traceability_registry.py ← movido desde calculator/audit/
  lineage/
    __init__.py
    lineage_builder.py       ← movido desde calculator/lineage/

modules/shared/audit/
  __init__.py                ← conserva: expone AuditTracer, trace(), get_tracer()
  trace.py                   ← KEEP: AuditTracer matemático (no mover)
  api/                       ← KEEP: audit HTTP router (no mover)
    __init__.py
    audit_router.py
  trace_integration.py       ← ELIMINAR (shim con 0 consumidores)
  traceability_writer.py     ← ELIMINAR (shim con 0 consumidores)
  traceability_registry.py   ← ELIMINAR (shim con 0 consumidores)
```

**Justificación de carpetas vs archivos planos:** Se prefieren subcarpetas `audit/` y `lineage/` dentro de `traceability/` para mantener cohesión semántica y facilitar expansión futura (ej. agregar `registry/` sin mezclar archivos de distintas capas).

**`shared/audit/trace.py` y `shared/audit/api/` no se mueven:** `trace.py` es infraestructura matemática transversal usada por 7 módulos productivos (cadena_b, cadena_c, formulas, pyg). Moverla generaría una cascada de updates innecesaria. `api/audit_router.py` pertenece correctamente en `shared/` ya que expone endpoints transversales.

### Plan Phase 6B-1 (implementación)

| Paso | Acción | Origen | Destino | Consumidores a actualizar | Shim | Riesgo |
|---|---|---|---|---|:---:|:---:|
| 1 | Crear `modules/traceability/__init__.py` + subdirs | — | `traceability/audit/`, `traceability/lineage/` | — | — | BAJO |
| 2 | Mover `trace_integration.py` | `calculator/audit/` | `traceability/audit/` | `calculator/engine.py` (1 import) | Sí en `calculator/audit/` por 1 ciclo | MEDIO |
| 3 | Mover `traceability_writer.py` | `calculator/audit/` | `traceability/audit/` | `calculator/api/calculate_dependencies.py` | Sí en `calculator/audit/` por 1 ciclo | MEDIO |
| 4 | Mover `traceability_registry.py` | `calculator/audit/` | `traceability/audit/` | `calculator/api/results_router.py`, `tests/unit/test_shared_guardrails.py` | Sí en `calculator/audit/` por 1 ciclo | BAJO |
| 5 | Mover `lineage_builder.py` | `calculator/lineage/` | `traceability/lineage/` | `calculator/engine.py` (lazy import) | Sí en `calculator/lineage/` por 1 ciclo | MEDIO |
| 6 | Eliminar shims `shared/audit/{trace_integration,traceability_writer,traceability_registry}.py` | `shared/audit/` | — | Verificar 0 consumidores directos (ya confirmado) | — | BAJO |
| 7 | Actualizar `shared/audit/__init__.py` | `shared/audit/` | — | Sin cambio de símbolos públicos — `AuditTracer`, `trace`, `get_tracer` permanecen | — | BAJO |
| 8 | Verificar guardrail `test_shared_guardrails.py:260` | — | — | Actualizar referencia si apunta a `calculator.audit` | — | BAJO |
| 9 | Crear guardrails en `tests/unit/test_calculator_boundary_guardrails.py` | — | — | Activar tests de 6G para `calculator/audit/` vacío | — | BAJO |

**Rollback:** `git revert` de la fase completa. Los shims temporales en `calculator/audit/` garantizan que consumidores no migrados sigan funcionando durante la transición.

### Riesgos de la fase 6B-1

| # | Riesgo | Severidad | Mitigación |
|---|---|:---:|---|
| RB1 | `engine.py` importa `audit_context` en top-level — si el shim no re-exporta correctamente, el startup del motor falla | ALTO | Verificar shim con `python -c "from nexa_engine.modules.calculator.audit.trace_integration import audit_context"` antes de commitear |
| RB2 | `test_shared_guardrails.py:260` tiene un guardrail que verifica `"calculator.audit" in src` — se vuelve falso post-migración | MEDIO | Actualizar el test en la misma fase |
| RB3 | `traceability_writer.py` importa `TraceabilityRepository` desde `calculator.persistence` — si 6C no está completa, el path sigue siendo válido | BAJO | No hay dependencia de orden; los imports de persistence no cambian en 6B-1 |
| RB4 | Si se eliminan shims `shared/audit/` antes de confirmar 0 consumidores con `grep`, un consumidor oculto puede romper | MEDIO | Ejecutar grep exhaustivo justo antes de eliminar (incluyendo `scripts/`) |

### Orden de ejecución recomendado

```
6B-1 (audit + lineage → traceability/)
  ↓
6C (persistence → calculator_persistence/)
  ↓
6D (api → calculator_api/)
```

6B-1 es independiente de 6C y 6D — puede ejecutarse primero sin riesgo de interdependencias circulares. Los shims permiten que 6C y 6D procedan a su propio ritmo.


---

## Phase 6B-1 — Traceability Move

**Fecha:** 2026-06-10  
**Estado:** COMPLETA ✅ — cero cambios funcionales

### Archivos movidos

| Origen | Destino | Método |
|---|---|---|
| `calculator/audit/trace_integration.py` | `traceability/audit/integration.py` | `git mv` |
| `calculator/audit/traceability_writer.py` | `traceability/audit/writer.py` | `git mv` |
| `calculator/audit/traceability_registry.py` | `traceability/audit/registry.py` | `git mv` |
| `calculator/lineage/lineage_builder.py` | `traceability/lineage/lineage_builder.py` | `git mv` |

### Shims eliminados

| Archivo | LOC | Consumidores directos | Acción |
|---|:---:|:---:|---|
| `shared/audit/trace_integration.py` | 11 | 0 | `git rm` |
| `shared/audit/traceability_writer.py` | 10 | 0 | `git rm` |
| `shared/audit/traceability_registry.py` | 10 | 0 | `git rm` |

### Imports productivos actualizados

| Archivo | Cambio |
|---|---|
| `calculator/engine.py` | `calculator.audit.trace_integration` → `traceability.audit.integration` |
| `calculator/engine.py` | `calculator.lineage.lineage_builder` → `traceability.lineage.lineage_builder` |
| `calculator/api/calculate_dependencies.py` | `calculator.audit.traceability_writer` → `traceability.audit.writer` |
| `calculator/api/results_router.py` | `calculator.audit.traceability_registry` → `traceability.audit.registry` |
| `tests/refactor/test_formula_trace_runtime_query.py` | `calculator.audit.trace_integration` → `traceability.audit.integration` |
| `tests/integration/test_traceability_polizas_source.py` | `calculator.audit.traceability_writer` → `traceability.audit.writer` |

### Shims temporales dejados

| Archivo | LOC | Motivo |
|---|:---:|---|
| `calculator/audit/__init__.py` | 10 | Re-exporta 3 símbolos — eliminar en 6G una vez confirmado sin consumers |
| `calculator/lineage/__init__.py` | 10 | Re-exporta 2 símbolos — eliminar en 6G |

### `shared/audit/trace.py` — preservado

No movido. Razón: define `AuditTracer` y `trace()` (infraestructura matemática transversal), usados por 7+ módulos productivos (`cadena_b`, `cadena_c`, `formulas/payroll`, `formulas/no_payroll`, `formulas/costos_financieros`, `pyg/services`). Mover generaría una cascada de updates innecesaria sin beneficio arquitectónico.

`shared/audit/api/audit_router.py` tampoco movido — correctamente ubicado en `shared/`.

### Paths canónicos post-6B-1

```
nexa_engine.modules.traceability.audit.integration   → audit_context, export_audit_trace
nexa_engine.modules.traceability.audit.writer        → TraceabilityWriter
nexa_engine.modules.traceability.audit.registry      → FieldTraceabilityRegistry
nexa_engine.modules.traceability.lineage.lineage_builder → seed_lineage_from_request/result
```

### Validaciones ejecutadas

| Suite | Resultado |
|---|---|
| `test_traceability_boundary_guardrails.py` (15 guardrails) | 15/15 ✅ |
| `test_wave9_domain_purity.py` | ✅ pass |
| `test_shared_guardrails.py` (excl. preexistente cosmos_repo) | ✅ pass |
| `test_traceability_polizas_source.py` | ✅ pass |
| `test_formula_trace_runtime_query.py` | ✅ pass |
| `tests/golden/test_vision_tarifas_golden_v27.py` | 58/58 ✅ |
| `tests/golden/test_cost_to_serve_golden_v27.py` | ✅ pass |
| `tests/ -m "parity or baseline"` | 21/21 ✅ (3 errors preexistentes cadena_c fixtures) |

Fallo preexistente: `test_parallel_parametrization_repos_do_not_exist` — cosmos_parametrization_repository.py, no relacionado con 6B-1 (confirmado via ejecución sin cambios).

### Estado boundary post-6B-1

```
modules/calculator/
  ❌ audit/    → vacía (shim __init__.py temporal, eliminar en 6G)
  ❌ lineage/  → vacía (shim __init__.py temporal, eliminar en 6G)
  ✅ api/
  ✅ persistence/
  [resto del motor — sin cambios]

modules/traceability/  ← NUEVO
  audit/
    integration.py   ← canónico
    writer.py        ← canónico
    registry.py      ← canónico
  lineage/
    lineage_builder.py ← canónico

modules/shared/audit/
  trace.py           ← PRESERVADO (AuditTracer)
  api/               ← PRESERVADO (audit HTTP endpoints)
  [shims eliminados]
```

**Pendiente:** `calculator/api/` y `calculator/persistence/` — fases 6C y 6D.

---

## Phase 6B-2 — Traceability Shim Cleanup

**Fecha:** 2026-06-10  
**Estado:** COMPLETA ✅ — cero cambios funcionales

### Matriz de consumidores

| Shim | Consumidores prod | Consumidores tests | Acción |
|---|:---:|:---:|---|
| `calculator/audit/__init__.py` | 0 | 0 (solo strings en guardrails) | DELETE_SAFE |
| `calculator/lineage/__init__.py` | 0 | 0 (solo strings en guardrails) | DELETE_SAFE |

### Shims eliminados

```
git rm modules/calculator/audit/__init__.py
git rm modules/calculator/lineage/__init__.py
```

### Estado post-6B-2

`modules/calculator/audit/` — sin archivos `.py` (solo `__pycache__`)  
`modules/calculator/lineage/` — sin archivos `.py` (solo `__pycache__`)

`modules/calculator/` ya no contiene implementaciones de auditoría ni lineage.

### Guardrails actualizados

`test_traceability_boundary_guardrails.py`: 17/17 ✅ (+2 nuevos: `test_g_6b2_calculator_audit_dir_has_no_py_files`, `test_g_6b2_calculator_lineage_dir_has_no_py_files`)

### Validaciones

| Suite | Resultado |
|---|---|
| `test_traceability_boundary_guardrails.py` (17) | 17/17 ✅ |
| `test_wave9_domain_purity.py` | ✅ |
| `test_shared_guardrails.py` (excl. preexistente) | ✅ |
| `test_vision_tarifas_golden_v27.py` | ✅ |
| `test_cost_to_serve_golden_v27.py` | ✅ |

Fallo preexistente: `test_parallel_parametrization_repos_do_not_exist` — no relacionado.

**Pendiente:** `calculator/api/` y `calculator/persistence/` — fases 6C y 6D.

---

## Phase 6C — Calculator Persistence Move

**Fecha:** 2026-06-10  
**Estado:** COMPLETA ✅ — cero cambios funcionales

### Archivos movidos

| Origen | Destino | Método |
|---|---|---|
| `calculator/persistence/results_repository.py` | `calculator_persistence/results_repository.py` | `git mv` |
| `calculator/persistence/traceability_repository.py` | `calculator_persistence/traceability_repository.py` | `git mv` |

### Imports productivos actualizados

| Archivo | Cambio |
|---|---|
| `calculator/api/calculate_dependencies.py` | `calculator.persistence.*` → `calculator_persistence.*` |
| `calculator/api/results_router.py` | `calculator.persistence.results_repository` → `calculator_persistence.*` |
| `pyg/api/vision_router.py` | ResultsRepository |
| `vision_cost_to_serve/api/router.py` | ResultsRepository |
| `vision_imprimible/api/router.py` | ResultsRepository |
| `vision_tarifas/api/router.py` | ResultsRepository |
| `traceability/audit/writer.py` | TraceabilityRepository |
| `db/container.py` | ResultsRepository |
| `db/dependencies.py` | ResultsRepository |

### Tests actualizados

| Test | Cambio |
|---|---|
| `tests/db/test_vision_imprimible_db_provider.py` | ResultsRepository + módulo |
| `tests/db/test_vision_imprimible_persisted_contract.py` | ResultsRepository |
| `tests/integration/test_traceability_polizas_source.py` | TraceabilityRepository |

### Path antiguo eliminado — clean break

```
git rm modules/calculator/persistence/__init__.py
```

`modules/calculator/persistence/` no contiene archivos `.py`.

### Paths canónicos post-6C

```
nexa_engine.modules.calculator_persistence.results_repository    → ResultsRepository
nexa_engine.modules.calculator_persistence.traceability_repository → TraceabilityRepository
```

### Validaciones

| Suite | Resultado |
|---|---|
| `test_traceability_boundary_guardrails.py` (25 tests) | 25/25 ✅ |
| `test_wave9_domain_purity.py` | ✅ |
| `test_shared_guardrails.py` | ✅ (excl. preexistente) |
| `test_vision_tarifas_golden_v27.py` | ✅ |
| `test_cost_to_serve_golden_v27.py` | ✅ |
| `test_traceability_polizas_source.py` | ✅ |
| `tests/db/` (17 fallos) | preexistentes — `_FakeDocumentStore` abstract methods, confirmado via stash |

### Estado boundary post-6C

```
modules/calculator/
  ❌ persistence/ → vacía (clean break)
  ❌ audit/       → vacía (6B-2)
  ❌ lineage/     → vacía (6B-2)
  ✅ api/         → pendiente Fase 6D

modules/calculator_persistence/  ← NUEVO
  results_repository.py
  traceability_repository.py

modules/traceability/             ← 6B-1/6B-2 completados
```

**Pendiente:** `calculator/api/` — Fase 6D.

---

## Phase 6D-A — Calculator API Move Audit

**Fecha:** 2026-06-10
**Estado:** AUDIT_ONLY — cero cambios productivos
**Worker:** architecture-agent / refactor-agent
**Riesgo:** HIGH

### Contexto

`modules/calculator/api/` es el último directorio que viola el boundary del motor de cálculo. Contiene capa HTTP, routers FastAPI, handlers, DTOs y singletons de dependencias — ninguno pertenece al motor puro. La fase 6D-B moverá estos archivos a `modules/calculator_api/`.

---

### TAREA 1 — Inventario

| Archivo | LOC | Responsabilidad | Tipo | Acción |
|---|---|---|---|---|
| `calculate_router.py` | 60 | Router POST /simulate/calculate + routing normal/certified | Router FastAPI | MOVE |
| `results_router.py` | 109 | Routers GET /results, /traceability | Router FastAPI | MOVE |
| `calculate_dependencies.py` | 27 | Singletons de repos (composition root del flujo calculate) | Dependency factory | MOVE |
| `calculate_dto.py` | 48 | `CalculationRequest` Pydantic model | DTO HTTP | MOVE |
| `calculate_validate.py` | 169 | `validate_input()` — diagnóstico sin correr engine | Utility interna | MOVE |
| `calculate_normal_handler.py` | 480 | `_calculate_normal()` — flujo principal de cálculo | Handler | MOVE |
| `calculate_certified_handler.py` | 156 | `_calculate_certified()` — flujo WAVE 15 con baseline | Handler | MOVE |
| `__init__.py` | 1 | Docstring de paquete | Package init | MOVE + actualizar docstring |

**Ningún archivo debe quedar en `modules/calculator/api/` al final de 6D-B.**

---

### TAREA 2 — Matriz de consumidores

#### Consumidores productivos

| Consumidor | Símbolo importado | Tipo import | Nuevo destino | Acción en 6D-B |
|---|---|---|---|---|
| `modules/api_v1/router.py:12` | `calculate_router` | `calculator.api.calculate_router` | `calculator_api.calculate_router` | Actualizar import |
| `modules/api_v1/router.py:15` | `results_router` | `calculator.api.results_router` | `calculator_api.results_router` | Actualizar import |
| `modules/shared/certification/api/certification_router.py:112` | `_lineage_repo` | `calculator.api.calculate_dependencies` (lazy, dentro de función) | `calculator_api.calculate_dependencies` | Actualizar import lazy |

#### Consumidores internos (dentro de `calculator/api/` — se resuelven al mover)

| Consumidor | Símbolo importado | Nota |
|---|---|---|
| `calculate_router.py` | `calculate_dto`, `calculate_normal_handler`, `calculate_certified_handler` | auto-resolución al mover todo |
| `calculate_normal_handler.py` | `calculate_dto`, `calculate_dependencies` | auto-resolución al mover todo |
| `calculate_certified_handler.py` | `calculate_dto`, `calculate_dependencies` | auto-resolución al mover todo |
| `calculate_validate.py` | `calculate_dto` | auto-resolución al mover todo |

#### Consumidores tests

| Test | Símbolo importado | Tipo | Acción en 6D-B |
|---|---|---|---|
| `tests/db/contract/test_lineage_repository_documentstore_wiring.py:25` | `_lineage_repo` | `calculator.api.calculate_dependencies` | Actualizar import |

#### Referencias docs/strings (no ejecutables — no requieren acción código)

| Archivo | Tipo | Acción |
|---|---|---|
| `docs/refactor/api_v1_router_modularization.md:77-78` | Referencia doc | Actualizar docs en 6D-B |
| `docs/refactor/calculator_boundary_reorganization_audit.md` | Referencia doc | Actualizar este doc en 6D-B |
| `docs/refactor/calculator_structure_redesign_audit.md:558` | Referencia doc | Actualizar docs en 6D-B |

#### Consumidores en guardrails

| Archivo | Referencia | Acción |
|---|---|---|
| `tests/unit/test_shared_guardrails.py:275,294` | Referencia a `calculate_dependencies.py` como nombre de archivo allowlist | Verificar: referencia es al filename, no al path — debe funcionar sin cambio |

---

### TAREA 3 — Mapa de montaje HTTP

| Router | Archivo actual | Prefix | Tags | Montado por | Endpoint principal | Debe permanecer igual |
|---|---|---|---|---|---|---|
| `calculate_router` | `calculator/api/calculate_router.py` | `/simulation` | `simulation-calculate` | `api_v1/router.py` include_router | `POST /api/v1/simulation/calculate` | ✅ |
| `results_router` | `calculator/api/results_router.py` | `/simulation` | `simulation-results` | `api_v1/router.py` include_router | `GET /api/v1/simulation/{id}/results` | ✅ |
| `results_router` | mismo | mismo | mismo | mismo | `GET /api/v1/simulation/{id}/traceability` | ✅ |

**Regla:** Phase 6D-B es import-only + file move. `APIRouter(prefix=..., tags=...)` no cambia. `api_v1/router.py` sigue montando con `include_router()` — solo cambia el import path.

---

### TAREA 4 — Dependencias externas de `calculator/api/`

```
calculator_api
  ├── calculator.engine          (NexaPricingEngine)
  ├── calculator.context_builder (SimulationContextBuilder)
  ├── calculator.serializers     (build_simulation_snapshot, etc.)
  ├── calculator.adapters.user_input_loader (UserInputLoader)
  ├── calculator.validation.contract_validator (ContractValidator)
  ├── calculator_persistence     (ResultsRepository, TraceabilityRepository)
  ├── shared.infrastructure.lineage.snapshot_repository (LineageSnapshotRepository)
  ├── shared.persistence.snapshots_repository (SnapshotRepository)
  ├── shared.exceptions          (DomainError, ParametrizationError, NotFoundError)
  ├── shared.responses           (ApiResponse, ErrorDetail)
  ├── shared.certification.*     (lazy imports en certified handler)
  ├── shared.use_cases.*         (lazy imports)
  ├── shared.versioning.*        (lazy imports)
  └── db.factory                 (get_provider)
  └── db.dependencies            (get_results_repository)
```

**Análisis de ciclos post-movimiento:**

| Dependencia | Riesgo de ciclo post-6D-B | Justificación |
|---|---|---|
| `calculator.engine` | NINGUNO | `calculator_api` → `calculator.engine` es dirección correcta (HTTP → motor) |
| `calculator_persistence` | NINGUNO | `calculator_api` → `calculator_persistence` es dirección correcta |
| `shared.*` | NINGUNO | `shared/` no importa desde `calculator_api` |
| `traceability` | NINGUNO | `calculator_api` no importa directamente traceability (usa `calculate_dependencies` que usa `traceability.audit.writer`) |
| `api_v1` | NINGUNO | `api_v1` importa `calculator_api`, no al revés |
| `shared.certification.api.certification_router` | CUIDADO | Hace lazy import de `calculator_api.calculate_dependencies._lineage_repo` — importar `calculator_api` desde `shared` es import cruzado entre módulos no relacionados. El singleton `_lineage_repo` debería migrar a `db/dependencies.py` en fase futura. Por ahora: actualizar el path lazy. |

**Único riesgo real:** `certification_router` hace lazy import de `_lineage_repo` desde `calculate_dependencies`. Esto es un acoplamiento no ideal (`shared` dependiendo de `calculator_api`), pero es un lazy import dentro de función — no crea ciclo de importación Python, solo acoplamiento semántico. Migrarlo está fuera del alcance de 6D.

---

### TAREA 5 — Estructura objetivo

```
modules/calculator_api/
  __init__.py                    ← actualizar docstring: modules.calculator_api
  calculate_router.py            ← sin cambios de contenido
  results_router.py              ← sin cambios de contenido
  calculate_dependencies.py      ← sin cambios de contenido
  calculate_dto.py               ← sin cambios de contenido
  calculate_validate.py          ← sin cambios de contenido
  calculate_normal_handler.py    ← sin cambios de contenido
  calculate_certified_handler.py ← sin cambios de contenido
```

No se crean subcarpetas. Move mecánico 1:1.

---

### TAREA 6 — Plan de implementación Phase 6D-B

#### Paso 1 — Pre-gate
```bash
git status --short
grep -R "modules\.calculator\.api\." modules/ tests/ db/ --include="*.py" | grep -v "__pycache__" | sort
```
Confirmar que Phase 6C está commiteada y cero cambios fuera de scope.

#### Paso 2 — Crear módulo y mover archivos
```bash
mkdir modules/calculator_api
touch modules/calculator_api/__init__.py
git mv modules/calculator/api/calculate_router.py modules/calculator_api/calculate_router.py
git mv modules/calculator/api/results_router.py modules/calculator_api/results_router.py
git mv modules/calculator/api/calculate_dependencies.py modules/calculator_api/calculate_dependencies.py
git mv modules/calculator/api/calculate_dto.py modules/calculator_api/calculate_dto.py
git mv modules/calculator/api/calculate_validate.py modules/calculator_api/calculate_validate.py
git mv modules/calculator/api/calculate_normal_handler.py modules/calculator_api/calculate_normal_handler.py
git mv modules/calculator/api/calculate_certified_handler.py modules/calculator_api/calculate_certified_handler.py
```

Actualizar `__init__.py` docstring: `modules.calculator.api` → `modules.calculator_api`.

#### Paso 3 — Actualizar imports externos (4 archivos)

| Archivo | Línea actual | Línea nueva |
|---|---|---|
| `modules/api_v1/router.py:12` | `calculator.api.calculate_router` | `calculator_api.calculate_router` |
| `modules/api_v1/router.py:15` | `calculator.api.results_router` | `calculator_api.results_router` |
| `modules/shared/certification/api/certification_router.py:112` | `calculator.api.calculate_dependencies` | `calculator_api.calculate_dependencies` |
| `tests/db/contract/test_lineage_repository_documentstore_wiring.py:25` | `calculator.api.calculate_dependencies` | `calculator_api.calculate_dependencies` |

#### Paso 4 — Actualizar imports internos (dentro de los 7 archivos movidos)
Todos los imports `from nexa_engine.modules.calculator.api.X import Y` deben cambiar a `from nexa_engine.modules.calculator_api.X import Y`.

Archivos afectados internamente:
- `calculate_router.py` (2 imports internos)
- `calculate_normal_handler.py` (2 imports internos)
- `calculate_certified_handler.py` (2 imports internos)
- `calculate_validate.py` (1 import interno)

Comando bulk:
```bash
sed -i '' 's|nexa_engine\.modules\.calculator\.api\.|nexa_engine.modules.calculator_api.|g' \
  modules/calculator_api/calculate_router.py \
  modules/calculator_api/calculate_normal_handler.py \
  modules/calculator_api/calculate_certified_handler.py \
  modules/calculator_api/calculate_validate.py \
  modules/api_v1/router.py \
  modules/shared/certification/api/certification_router.py \
  tests/db/contract/test_lineage_repository_documentstore_wiring.py
```

#### Paso 5 — Eliminar path antiguo
```bash
git rm modules/calculator/api/__init__.py
# Verificar que calculator/api/ queda vacío
ls modules/calculator/api/
```

**Clean break. Sin shim.**

#### Paso 6 — Verificar
```bash
grep -R "modules\.calculator\.api\." modules/ tests/ db/ --include="*.py" | grep -v "__pycache__" | grep -v "test_shared_guardrails\|guardrail"
# → 0 resultados ejecutables
py_compile modules/calculator_api/*.py
python -c "from nexa_engine.modules.calculator_api.calculate_router import router; print('ok')"
python -c "from nexa_engine.modules.calculator_api.results_router import router; print('ok')"
```

#### Rollback
```bash
git stash  # antes de commitear — reversión completa
```

---

### TAREA 7 — Guardrails propuestos (para crear en 6D-B)

Archivo: `tests/unit/test_calculator_api_boundary_guardrails.py`

| ID | Descripción | Tipo |
|---|---|---|
| G-6D1 | `modules/calculator_api/calculate_router.py` existe | path check |
| G-6D2 | `modules/calculator_api/results_router.py` existe | path check |
| G-6D3 | `modules/calculator_api/calculate_dependencies.py` existe | path check |
| G-6D4 | `calculate_router` importable desde `calculator_api.calculate_router` | import check |
| G-6D5 | `results_router` importable desde `calculator_api.results_router` | import check |
| G-6D6 | `modules/calculator/api/` no contiene `.py` | path check (dir vacío) |
| G-6D7 | Ningún módulo productivo importa desde `modules.calculator.api.` | grep check |
| G-6D8 | `modules/calculator/formulas/` no importa `calculator_api` | grep check |
| G-6D9 | `modules/calculator/engine.py` no importa `calculator_api` | content check |
| G-6D10 | `modules/api_v1/router.py` importa desde `calculator_api.calculate_router` | content check |

---

### TAREA 8 — Tests requeridos para 6D-B

```bash
# Suite mínima obligatoria
PYTHONPATH=$(pwd) pytest tests/unit/test_wave9_domain_purity.py -q
PYTHONPATH=$(pwd) pytest tests/golden/test_vision_tarifas_golden_v27.py tests/golden/test_cost_to_serve_golden_v27.py -q
PYTHONPATH=$(pwd) pytest tests/ -m "parity or baseline" -q

# Guardrails de boundaries
PYTHONPATH=$(pwd) pytest tests/unit/test_traceability_boundary_guardrails.py -q
PYTHONPATH=$(pwd) pytest tests/unit/test_calculator_api_boundary_guardrails.py -q

# Tests de routers y handlers
PYTHONPATH=$(pwd) pytest tests/db/contract/test_lineage_repository_documentstore_wiring.py -q

# Smoke de importabilidad
PYTHONPATH=$(pwd) python -c "from nexa_engine.modules.calculator_api.calculate_router import router; print('calculate_router ok')"
PYTHONPATH=$(pwd) python -c "from nexa_engine.modules.calculator_api.results_router import router; print('results_router ok')"
PYTHONPATH=$(pwd) python -c "from nexa_engine.modules.calculator_api.calculate_dependencies import _results_repo; print('dependencies ok')"
PYTHONPATH=$(pwd) python -c "from nexa_engine.modules.api_v1.router import router; print('api_v1 router ok')"

# py_compile de todos los archivos movidos
PYTHONPATH=$(pwd) python -m py_compile modules/calculator_api/calculate_router.py modules/calculator_api/results_router.py modules/calculator_api/calculate_dependencies.py modules/calculator_api/calculate_dto.py modules/calculator_api/calculate_validate.py modules/calculator_api/calculate_normal_handler.py modules/calculator_api/calculate_certified_handler.py
```

---

### Riesgos abiertos

| ID | Riesgo | Severidad | Mitigación |
|---|---|---|---|
| R1 | `certification_router.py` lazy-importa `_lineage_repo` desde `calculator_api` — acoplamiento `shared` → `calculator_api` | BAJO | Lazy import inside function — no crea ciclo Python. Actualizar path en 6D-B. Migrar a `db/dependencies.py` en fase futura. |
| R2 | `test_shared_guardrails.py:294` tiene allowlist `calculate_dependencies.py` — es filename, no path | MÍNIMO | El test verifica filename, no módulo — no requiere cambio. Verificar post-move. |
| R3 | Docs (`api_v1_router_modularization.md`, `calculator_structure_redesign_audit.md`) tienen paths viejos | MÍNIMO | Actualizar docs en 6D-B para consistencia. |
| R4 | Si hay tests adicionales de integración E2E que instancian `TestClient(create_app())` | BAJO | Los tests E2E importan la app via `create_app()` — no dependen de paths internos. Verificar con grep post-move. |

---

### Confirmación AUDIT_ONLY

- Cero archivos modificados en esta fase (6D-A).
- Cero imports cambiados.
- Cero código productivo tocado.
- Solo documentación agregada.
- Todos los consumidores identificados: 3 productivos externos, 1 test, 3 referencias docs.
- Plan 6D-B diseñado y listo para ejecutar.

---

## Phase 6D-B — Calculator API Move

**Fecha:** 2026-06-10
**Estado:** COMPLETA ✅ — cero cambios funcionales
**Worker:** refactor-agent
**Riesgo:** HIGH

### Archivos movidos

| Origen | Destino | Método |
|---|---|---|
| `calculator/api/__init__.py` | `calculator_api/__init__.py` | `git mv` |
| `calculator/api/calculate_router.py` | `calculator_api/calculate_router.py` | `git mv` |
| `calculator/api/results_router.py` | `calculator_api/results_router.py` | `git mv` |
| `calculator/api/calculate_dependencies.py` | `calculator_api/calculate_dependencies.py` | `git mv` |
| `calculator/api/calculate_dto.py` | `calculator_api/calculate_dto.py` | `git mv` |
| `calculator/api/calculate_validate.py` | `calculator_api/calculate_validate.py` | `git mv` |
| `calculator/api/calculate_normal_handler.py` | `calculator_api/calculate_normal_handler.py` | `git mv` |
| `calculator/api/calculate_certified_handler.py` | `calculator_api/calculate_certified_handler.py` | `git mv` |

### Imports actualizados

| Archivo | Cambio |
|---|---|
| `calculator_api/__init__.py` | docstring: `modules.calculator.api` → `modules.calculator_api` |
| `calculator_api/calculate_router.py` | 3 imports internos actualizados |
| `calculator_api/calculate_normal_handler.py` | 2 imports internos actualizados |
| `calculator_api/calculate_certified_handler.py` | 2 imports internos actualizados |
| `calculator_api/calculate_validate.py` | 1 import interno actualizado |
| `modules/api_v1/router.py` | `calculator.api.calculate_router` → `calculator_api.calculate_router`; `calculator.api.results_router` → `calculator_api.results_router` |
| `modules/shared/certification/api/certification_router.py` | lazy import `calculator.api.calculate_dependencies` → `calculator_api.calculate_dependencies` |
| `tests/db/contract/test_lineage_repository_documentstore_wiring.py` | `calculator.api.calculate_dependencies` → `calculator_api.calculate_dependencies` |

### Path antiguo eliminado — clean break

`modules/calculator/api/` eliminado. Sin shims.

### Rutas HTTP preservadas

| Router | Prefix | Tag | Montado por |
|---|---|---|---|
| `calculate_router` | `/simulation` | `simulation-calculate` | `api_v1/router.py` |
| `results_router` | `/simulation` | `simulation-results` | `api_v1/router.py` |

Smoke verificado: `api_v1.router` monta 33 rutas idénticas post-move.

### Paths canónicos post-6D-B

```
nexa_engine.modules.calculator_api.calculate_router      → router (POST /simulation/calculate)
nexa_engine.modules.calculator_api.results_router        → router (GET /simulation/{id}/results/*)
nexa_engine.modules.calculator_api.calculate_dependencies → _results_repo, _lineage_repo, etc.
nexa_engine.modules.calculator_api.calculate_dto         → CalculationRequest
nexa_engine.modules.calculator_api.calculate_validate    → validate_input
nexa_engine.modules.calculator_api.calculate_normal_handler     → _calculate_normal
nexa_engine.modules.calculator_api.calculate_certified_handler  → _calculate_certified
```

### Validaciones

| Suite | Resultado |
|---|---|
| `test_calculator_api_boundary_guardrails.py` (14 tests) | 14/14 ✅ |
| `test_traceability_boundary_guardrails.py` (25 tests) | 25/25 ✅ |
| `test_wave9_domain_purity.py` | ✅ |
| `test_vision_tarifas_golden_v27.py` | ✅ |
| `test_cost_to_serve_golden_v27.py` | ✅ |
| `tests/ -m parity or baseline` | 21/21 ✅ |
| `test_lineage_repository_documentstore_wiring.py` | 7/7 ✅ |
| Cadena C parity ERRORs | preexistentes — fixture snapshot faltante, confirmado preexistente |

### Estado boundary post-6D-B

```
modules/calculator/
  ✅ api/         → eliminada (6D-B)
  ✅ persistence/ → vacía (6C)
  ✅ audit/       → vacía (6B-2)
  ✅ lineage/     → vacía (6B-2)

modules/calculator_api/        ← NUEVO (6D-B)
modules/calculator_persistence/ ← 6C
modules/traceability/           ← 6B-1/6B-2

modules/calculator/ ahora contiene SOLO el motor puro:
  engine.py, formulas/, mixins/, adapters/, context_builder.py,
  serializers.py, validation/, models/, dto/, risk/, use_cases/, helpers/
```

**`modules/calculator/` es ahora un motor puro de cálculo sin capas HTTP ni persistence.**

---

## Phase 6E — Final Calculator Boundary Gate

**Fecha:** 2026-06-10
**Estado:** GATE PASSED ✅
**Worker:** architecture/qa-agent
**Riesgo:** MEDIUM (audit only)

### Confirmación — carpetas prohibidas

| Carpeta | Archivos .py | Estado |
|---|---|---|
| `calculator/api/` | 0 | ✅ vacía (6D-B) |
| `calculator/persistence/` | 0 | ✅ vacía (6C) |
| `calculator/audit/` | 0 | ✅ vacía (6B-2) |
| `calculator/lineage/` | 0 | ✅ vacía (6B-2) |

### Confirmación — imports legacy ejecutables

| Categoría | Imports ejecutables | Estado |
|---|---|---|
| `modules.calculator.api.*` | 0 | ✅ |
| `modules.calculator.persistence.*` | 0 | ✅ |
| `modules.calculator.audit.*` | 0 | ✅ |
| `modules.calculator.lineage.*` | 0 | ✅ |

### Estructura final de `modules/calculator/` — clasificación

| Carpeta/Archivo | Responsabilidad | Pertenece al motor | Acción |
|---|---|---|---|
| `engine.py` | Orquestador del pipeline de 10 capas | ✅ SÍ | KEEP_IN_CALCULATOR |
| `context_builder.py` | Construye SimulationContext desde inputs | ✅ SÍ | KEEP_IN_CALCULATOR |
| `input_normalizer.py` | Normaliza user_input antes de calcular | ✅ SÍ | KEEP_IN_CALCULATOR |
| `input_validator.py` | Valida input antes del motor | ✅ SÍ | KEEP_IN_CALCULATOR |
| `formulas/` | Cálculos puros: payroll, no_payroll, pricing, risk, costos_financieros | ✅ SÍ | KEEP_IN_CALCULATOR |
| `adapters/` | `entry_data_adapter.py`, `user_input_loader.py`, `volume_resolution.py` — adaptan input al dominio | ✅ SÍ | KEEP_IN_CALCULATOR |
| `constants/` | Constantes del motor financiero (SMMLV, días laborales, tasas legales) | ✅ SÍ — motor-domain | KEEP_IN_CALCULATOR |
| `dto/` | `NormalizedInput`, `RequestDTO`, `UserInputs` — contratos internos del motor | ✅ SÍ | KEEP_IN_CALCULATOR |
| `mixins/` | Context builder mixins, input normalizer mixins, user input builders | ✅ SÍ — internos del engine | KEEP_IN_CALCULATOR |
| `models/` | `DataProvenance`, `Snapshot` — modelos internos del resultado | ✅ SÍ | KEEP_IN_CALCULATOR |
| `serializers/` | `PricingResultSerializer`, helpers de serialización — serializa `PricingResult` interno | ✅ SÍ — no HTTP, no API | KEEP_IN_CALCULATOR |
| `validation/` | `ContractValidator`, `SimulationRequestValidator` — validación de dominio | ✅ SÍ | KEEP_IN_CALCULATOR |
| `use_cases/` | `BuildPricingUseCase`, `BuildVisionsUseCase` — orquestación sin infra pesada | ✅ SÍ — application layer sin HTTP/DB | KEEP_WITH_JUSTIFICATION |
| `helpers/engine_helpers.py` | Helpers matemáticos extraídos del engine (>500 LOC split, FASE Z4b) | ✅ SÍ — exclusivamente del engine | KEEP_IN_CALCULATOR |
| `helpers/console_reporter.py` | Presentador de `PricingResult` en consola — dev tool | ⚠️ BORDERLINE — no es motor, es presentador | MOVE_CANDIDATE_FUTURE_PHASE |
| `shared/__init__.py` | Re-exporta `PricingCalculator` desde `formulas.pricing` | ⚠️ Solo 1 línea — namespace convenience | KEEP_WITH_JUSTIFICATION (trivial) |
| `risk/` | Solo `__pycache__`, sin `.py` actualmente | ✅ vacío | DELETE_CANDIDATE (directorio vacío) |

### Análisis de carpetas borderline

**`helpers/console_reporter.py`** (MOVE_CANDIDATE_FUTURE_PHASE):
- Depende de `shared.profitability.calculators` y `shared.models.PricingResult`
- No tiene consumidores en producción (no importado por routers ni por engine)
- Es un dev/debug tool — candidato a `modules/shared/dev_tools/` o eliminar
- **No bloquea el gate** — no es capa HTTP ni persistence

**`calculator/shared/__init__.py`** (KEEP_WITH_JUSTIFICATION):
- 3 líneas: re-exporta `PricingCalculator`
- Consumidores pueden importar directamente desde `formulas.pricing`
- **No bloquea el gate** — es namespace convenience interno

**`calculator/risk/`** (DELETE_CANDIDATE):
- Solo contiene `__pycache__`, sin `.py`
- Remnant de refactoring previo
- **No bloquea el gate**

### Dependencias del motor — análisis de pureza

```
modules/calculator/engine.py imports:
  ✅ modules.calculator.formulas.*        (motor puro)
  ✅ modules.calculator.context_builder   (motor puro)
  ✅ modules.calculator.serializers.*     (serialización interna)
  ✅ modules.shared.models               (contratos compartidos)
  ✅ modules.shared.audit.trace          (AuditTracer — cross-domain)
  ✅ modules.traceability.*              (lazy imports — correcto)
  ✅ modules.shared.infrastructure.lineage.* (lazy import — correcto)
  ❌ calculator_api                       → NO (confirmado)
  ❌ calculator_persistence               → NO (confirmado)
  ❌ FastAPI / DocumentStore              → NO (confirmado)
```

### Nuevos módulos canónicos post-Fase 6

| Módulo | Path | Responsabilidad |
|---|---|---|
| Motor puro | `modules.calculator` | Engine pipeline, formulas, context, adapters |
| HTTP layer | `modules.calculator_api` | Routers, handlers, DTOs, dependencies |
| Persistence | `modules.calculator_persistence` | ResultsRepository, TraceabilityRepository |
| Trazabilidad | `modules.traceability` | Audit integration, writer, registry, lineage builder |

### Validaciones del gate

| Suite | Resultado |
|---|---|
| `test_calculator_api_boundary_guardrails.py` (14) | 14/14 ✅ |
| `test_traceability_boundary_guardrails.py` (25) | 25/25 ✅ |
| `test_wave9_domain_purity.py` (13) | 13/13 ✅ |
| `test_vision_tarifas_golden_v27.py` | ✅ |
| `test_cost_to_serve_golden_v27.py` | ✅ |
| `tests/ -m parity or baseline` | 21/21 ✅ |
| `py_compile` — todos los módulos boundary | ✅ |
| 3 ERRORs cadena_c parity | preexistentes — fixture snapshot faltante |

### Veredicto final

**GATE PASSED — READY ✅**

`modules/calculator/` es un motor de cálculo puro. Las 4 capas de infraestructura fueron extraídas limpiamente:

```
6B-1/6B-2: calculator/audit + lineage  → modules/traceability/
6C:         calculator/persistence      → modules/calculator_persistence/
6D-B:       calculator/api              → modules/calculator_api/
```

### Riesgos abiertos (no bloquean)

| ID | Descripción | Prioridad |
|---|---|---|
| R1 | `helpers/console_reporter.py` — dev tool mezclado con motor | BAJA — candidato fase futura |
| R2 | `calculator/risk/` directorio vacío (sin .py) | MÍNIMA — limpiar en próxima fase |
| R3 | `certification_router.py` lazy-importa `_lineage_repo` desde `calculator_api` — acoplamiento `shared` → `calculator_api` | BAJA — migrar a `db/dependencies.py` en fase futura |

### Próxima fase recomendada

**Phase 6F (opcional):** Limpiar directorios vacíos residuales (`calculator/risk/`, `calculator/audit/`, `calculator/persistence/`, `calculator/lineage/`) — son solo `__pycache__`, sin impacto funcional.

**Phase 7 (si aplica):** Migrar `_lineage_repo` de `calculator_api/calculate_dependencies.py` a `db/dependencies.py` para eliminar acoplamiento `shared.certification` → `calculator_api`.
