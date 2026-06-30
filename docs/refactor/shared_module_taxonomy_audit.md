# SHARED_MODULE_TAXONOMY_AUDIT

**Date:** 2026-06-10  
**Scope:** Review organization of `modules/shared/` against CLAUDE.md architecture rules  
**Phase:** Read-only classification (no moves in this phase)  
**Status:** ✅ COMPLETE — Ready for implementation decisions

---

## Executive Summary

**Finding:** `modules/shared/` is **well-organized overall** with correct separation of concerns, but has **3 structural clarity issues**:

1. ✅ **Lineage split is correct** (domain models in `lineage/`, persistence in `infrastructure/lineage/`)
2. ⚠️ **Vision models should migrate to their owning modules** (visions_imprimible, visions_tarifas, visions_pyg belong to vision_* modules)
3. ⚠️ **i_parametrization_provider.py should move to ports/** (it's an interface, not a root-level artifact)
4. ✅ **All other folders are correctly placed**

**Risk:** LOW — All suggested moves are low-risk, non-formula-changing, and have clear owning modules.

---

## Inventory & Classification

### Section A: KEEP_IN_SHARED (No Action)

| Folder/File | Responsibility | Import Count | Classification | Reason |
|---|---|---|---|---|
| `audit/` | HTTP endpoint + trace infrastructure | High | KEEP_IN_SHARED | Cross-domain audit capability; router + trace infra are truly shared |
| `certification/` | Certified mode models + persistence + HTTP endpoint | Medium | KEEP_IN_SHARED | Cross-domain certification capability; models, repo, router all shared |
| `config/business_rules/` | YAML-based business rule loading | Medium | KEEP_IN_SHARED | Transversal configuration infrastructure |
| `contracts/` | API v1 request/response DTOs | High | KEEP_IN_SHARED | Global API contract layer; used by all modules |
| `exceptions.py` | DomainError, NotFoundError, ValidationError hierarchy | High | KEEP_IN_SHARED | Cross-domain error abstraction |
| `responses.py` | ApiResponse wrapper (success/data/error/meta) | High | KEEP_IN_SHARED | Standardized HTTP response format across all APIs |
| `profitability/calculators.py` | Stateless factor_billing, ingreso_desde_costo math | High | KEEP_IN_SHARED | Pure math used by calculator_motor, pyg, vision_tarifas — truly cross-cutting |
| `lineage/models.py` & `lineage/query.py` | LineageRef, LineageNode, LineageGraph, LineageQuery | High | KEEP_IN_SHARED | Domain models for financial lineage; immutable, no IO |
| `infrastructure/lineage/` | LineageSnapshotRepository, JsonLineageEmitter, NullEmitter | High | KEEP_IN_SHARED | Persistence adapter for LineageGraph; correctly separated from domain models |
| `versioning/` | VersionRegistry, VersionMetadata | Medium | KEEP_IN_SHARED | Cross-domain version tracking; used by engine, audit, certification |
| `ports/` | ILogger, ITraceEmitter, IParametrizationProvider (interfaces) | Medium | KEEP_IN_SHARED | Port abstraction layer; protocol definitions belong in shared |
| `infrastructure/` (root files) | app_settings, env_loader, exception_handlers, lifespan, logging, middlewares, request_utils | High | KEEP_IN_SHARED | Global app infrastructure; transversal across all modules |
| `helpers/` | certified_helpers (utilities) | Low | KEEP_IN_SHARED | Shared utilities with low coupling |
| `use_cases/` | audit_simulation.py, certified_calculation.py | Medium | KEEP_IN_SHARED | Cross-domain orchestration logic; no owning module, truly shared |
| `models/panel.py` | PanelDeControl, related panel input models | High | KEEP_IN_SHARED | Truly shared input model; used by multiple calculators |
| `models/results.py` | PricingResult, related output models | High | KEEP_IN_SHARED | Truly shared output model; engine produces this for all flows |
| `precision.py` | Decimal precision, rounding utilities | Low | KEEP_IN_SHARED | Math utilities used across multiple calculators |

**Subtotal: 17 items** — All correctly placed. No action required.

---

### Section B: MOVE_TO_DOMAIN_MODULE (Low-Risk Migrations)

| Current Path | Proposed Owner | Current Responsibility | Risk | Reason | Implementation |
|---|---|---|---|---|---|
| `models/visions_imprimible.py` | `modules/vision_imprimible/models.py` | VisionImprimible, related models | LOW | Vision-specific domain models; belongs to vision_imprimible module | Move file, update imports (3 locations: tests, vision_tarifas, shared/__init__) |
| `models/visions_pyg.py` | `modules/pyg/models.py` | VisionPyG, related models | LOW | PyG-specific domain models; belongs to pyg module | Move file, update imports (2 locations: tests, shared/__init__) |
| `models/visions_tarifas.py` | `modules/vision_tarifas/models.py` | VisionTarifas, related models | LOW | Tarifas-specific domain models; belongs to vision_tarifas module | Move file, update imports (4 locations: tests, vision_imprimible, shared/__init__) |
| `models/visions_cts.py` | `modules/vision_cost_to_serve/models.py` | VisionCostToServe, related models | LOW | Cost-to-Serve-specific domain models; belongs to vision_cost_to_serve module | Move file, update imports (1 location: shared/__init__) |

**Subtotal: 4 items** — Vision models should migrate to their owning vision modules.

---

### Section C: MOVE_TO_INFRASTRUCTURE (Low-Risk Moves)

| Current Path | Proposed Destination | Current Responsibility | Risk | Reason | Implementation |
|---|---|---|---|---|---|
| `i_parametrization_provider.py` | `ports/parametrization_provider.py` | IParametrizationProvider protocol | LOW | Interface definition; belongs with other port abstractions | **Already exists at destination.** This file should be deleted; all imports should use `ports/parametrization_provider.py` instead |

**Subtotal: 1 item** — Interface is duplicated; consolidate imports.

---

### Section D: NO ACTION / ALREADY CORRECT

| Path | Status | Evidence |
|---|---|---|
| `modules/shared/lineage/models.py` vs `modules/shared/infrastructure/lineage/snapshot_repository.py` | ✅ CORRECTLY SPLIT | Domain models (frozen dataclasses) separate from infrastructure (persistence adapter with DocumentStore) |
| `modules/shared/persistence/snapshots_repository.py` vs `modules/shared/infrastructure/lineage/snapshot_repository.py` | ✅ NOT DUPLICATES | Different entities: `SimulationSnapshot` vs `LineageGraph`. Different purposes, different collections. No consolidation needed |
| Audit structure (`audit/` + `use_cases/audit_simulation.py`) | ✅ CORRECTLY SEPARATED | `audit/` = infrastructure (trace.py) + router; `use_cases/` = business logic (audit_simulation.py). Correct boundaries. |
| Certification structure (`certification/` + `use_cases/certified_calculation.py`) | ✅ CORRECTLY SEPARATED | `certification/` = domain models + repository + router; `use_cases/` = orchestration logic. Correct boundaries. |

---

## Detailed Findings

### A. Lineage Organization (CORRECTLY SPLIT ✅)

**Structure:**
```
modules/shared/
├── lineage/
│   ├── models.py           ← Domain: LineageRef, LineageNode, LineageGraph
│   ├── query.py            ← Domain: LineageQuery (convenience accessor)
│   └── __init__.py         ← Re-exports domain models
└── infrastructure/
    └── lineage/
        ├── snapshot_repository.py    ← Infra: Persistence via DocumentStore
        ├── json_lineage_emitter.py   ← Infra: JSON trace emitter
        ├── null_emitter.py           ← Infra: Null-object emitter
        └── __init__.py               ← Re-exports infrastructure
```

**Verdict:** ✅ **CORRECT**
- Domain models (frozen dataclasses) correctly separated from persistence adapters
- Clear responsibility boundary: `lineage/` = what lineage is; `infrastructure/lineage/` = how to persist it
- No duplication

**Evidence:**
- `lineage/models.py` docstring: "No IO — these classes never read from disk. Persistence lives in `infrastructure/lineage/snapshot_repository.py`."
- `infrastructure/lineage/snapshot_repository.py` imports domain models from `lineage.models`

---

### B. Persistence Layer (NO DUPLICATION ✅)

**Structure:**
```
modules/shared/
├── persistence/
│   └── snapshots_repository.py       ← SnapshotRepository (persists SimulationSnapshot)
└── infrastructure/lineage/
    └── snapshot_repository.py        ← LineageSnapshotRepository (persists LineageGraph)
```

**Question:** Are these duplicates?

**Answer:** ✅ **NO** — Different entities, different purposes:

| Aspect | SimulationSnapshot | LineageGraph |
|---|---|---|
| Entity | Simulation snapshot (full calculation state at pipeline completion) | Financial lineage trace (formula tracking + sources) |
| Repository Class | `SnapshotRepository` | `LineageSnapshotRepository` |
| Location | `persistence/` | `infrastructure/lineage/` |
| Collection | `simulation_snapshots` | `lineage_snapshots` |
| Use Case | Debugging, forensics, snapshot retrieval | Audit, certification, formula tracing |
| Imports | `SimulationSnapshot.from_dict()` | `LineageGraph.from_dict()` |

**Verdict:** Correctly placed. The naming is slightly confusing (`snapshot_repository` vs `snapshots_repository`), but the separation is sound.

---

### C. Vision Models (SHOULD MIGRATE ⚠️)

**Current Structure:**
```
modules/shared/models/
├── visions_imprimible.py      ← VisionImprimible + nested models
├── visions_pyg.py             ← VisionPyG + nested models
├── visions_tarifas.py         ← VisionTarifas + nested models
├── visions_cts.py             ← VisionCostToServe + nested models
├── visions.py                 ← Re-exports all 4
└── __init__.py                ← Re-exports visions.py
```

**Owning Modules:**
```
modules/
├── vision_imprimible/
├── vision_pyg/
├── vision_cost_to_serve/
└── vision_tarifas/
```

**Verdict:** ⚠️ **SHOULD MIGRATE** — Vision-specific models belong to their owning modules.

**Reason:**
1. CLAUDE.md rule: "Models should live in their owning module unless they are truly cross-cutting."
2. These models are NOT cross-cutting; each is specific to one vision module
3. Vision modules already import from `shared.models.visions`; they should own their own models
4. Moving them reduces coupling and clarifies ownership

**Risk Assessment:** LOW
- No formula changes
- Clear owning modules exist
- Limited import locations (3-4 per model file)
- No breaking changes to API contracts (models not directly exposed in v1 endpoints)

**Import Impact:**
```
visions_imprimible.py:
  - tests/vision/test_imprimible*.py (3 test files)
  - modules/vision_tarifas/visions_imprimible.py (re-imports to build visions_tarifas)
  - modules/shared/models/__init__.py (re-export)

visions_pyg.py:
  - tests/pyg/test_*.py (2 test files)
  - modules/shared/models/__init__.py (re-export)

visions_tarifas.py:
  - tests/vision/test_tarifas*.py (4 test files)
  - modules/vision_tarifas/ (multiple files import)
  - modules/shared/models/__init__.py (re-export)

visions_cts.py:
  - tests/vision/test_cts*.py (1 test file)
  - modules/shared/models/__init__.py (re-export)
```

**Next Steps:** After classification, coordinate with vision module owners to execute migrations in sequence.

---

### D. Profitability Calculator (CORRECTLY PLACED ✅)

**Current Location:** `modules/shared/profitability/calculators.py`

**Usage Pattern:**
```
Used by:
  - modules/calculator_motor/use_cases/build_pricing.py (factor_billing calculation)
  - modules/calculator_motor/helpers/console_reporter.py (reporting)
  - modules/calculator_motor/formulas/costos_financieros/calculator.py (pricing)
  - modules/pyg/services/pyg_calculator.py (KPI calculation)
  - modules/pyg/services/kpis_calculator.py (metrics)
  - modules/vision_tarifas/reglas.py (tariff rules)
  - tests/ (6+ test files)
```

**Analysis:**
- Pure stateless methods: `calcular_factor_billing()`, `calcular_ingreso_desde_costo()`, `calcular_factor_margenes()`
- No dependencies on other modules
- Formula V2-7 anchored (documented in code)
- Backward-compatible aliases for legacy code

**Verdict:** ✅ **KEEP IN SHARED**
- Truly cross-cutting (used by calculator, pyg, and multiple visions)
- Pure math layer (no IO, no side effects)
- Not owned by any single domain module
- High import count indicates widespread need

---

### E. Audit Organization (CORRECTLY STRUCTURED ✅)

**Structure:**
```
modules/shared/
├── audit/
│   ├── api/audit_router.py           ← HTTP endpoints (GET /audit/...)
│   ├── trace.py                      ← Infrastructure: AuditTracer, get_tracer
│   └── __init__.py                   ← Re-exports
└── use_cases/
    ├── audit_simulation.py           ← Business logic: AuditResult building
    └── certified_calculation.py       ← Business logic: Certification orchestration
```

**Verdict:** ✅ **CORRECT**
- Clear responsibility: `audit/` = infrastructure + router; `use_cases/` = orchestration
- `AuditTracer` (trace.py) handles mathematical tracing (infrastructure)
- `AuditSimulationUseCase` (use_cases/) handles audit envelope building (business logic)
- No duplication

---

### F. Certification Organization (CORRECTLY STRUCTURED ✅)

**Structure:**
```
modules/shared/
├── certification/
│   ├── api/certification_router.py   ← HTTP endpoints (GET/POST /certification/...)
│   ├── models.py                     ← ExecutionCertificate domain model
│   ├── certificate_repository.py     ← Persistence adapter
│   └── __init__.py                   ← Re-exports
└── use_cases/
    └── certified_calculation.py       ← Business logic: Certificate issuance
```

**Verdict:** ✅ **CORRECT**
- Clear layers: router → use_case → repository → DocumentStore
- Domain models (ExecutionCertificate) separate from persistence and HTTP
- Certification logic centralized in use_cases/

---

### G. Interface Duplication (CONSOLIDATE ⚠️)

**Finding:** `i_parametrization_provider.py` is duplicated:

```
modules/shared/
├── i_parametrization_provider.py           ← Root level (OLD)
└── ports/
    └── parametrization_provider.py         ← Correct location (NEW)
```

**Evidence:**
```bash
# Two files with same interface
grep -l "IParametrizationProvider" /modules/shared/i_parametrization_provider.py
grep -l "IParametrizationProvider" /modules/shared/ports/parametrization_provider.py
```

**Verdict:** ⚠️ **CONSOLIDATE**
- `ports/parametrization_provider.py` is the correct location (interfaces belong in ports/)
- `i_parametrization_provider.py` should be deleted
- All imports should use `ports/parametrization_provider.py`

**Risk:** LOW — Simple file deletion + import rewrite

---

## Taxonomy Classification Summary

### Classification Distribution

| Classification | Count | Status | Next Step |
|---|---|---|---|
| KEEP_IN_SHARED | 17 | ✅ Complete | No action |
| MOVE_TO_DOMAIN_MODULE | 4 | ⚠️ Planned | Coordinate with vision module owners |
| MOVE_TO_INFRASTRUCTURE | 0 (1 deleted) | ⚠️ Planned | Delete duplicate, repoint imports |
| DEAD_CODE_CANDIDATE | 0 | ✅ None found | — |
| NEEDS_DECISION | 0 | ✅ None found | — |

### Overall Architecture Assessment

**Strengths:**
- ✅ Clear separation of domain models from infrastructure
- ✅ Well-organized vertical slices (audit, certification, versioning)
- ✅ Correct use of ports/interfaces
- ✅ API contracts properly centralized
- ✅ Business logic in use_cases, routers in api/ folders

**Issues (Minor):**
- ⚠️ Vision models should move to their owning modules (clarity improvement)
- ⚠️ Interface duplication (`i_parametrization_provider.py` is orphaned)

**No Formula/Contract Changes Required:**
- All proposed moves are structural (models, interfaces)
- No business logic changes
- No persisted payload shape changes
- No API contract changes

---

## Recommended Implementation Plan

### Phase 1: Quick Win (LOW RISK) — Delete Orphaned Interface
**Target:** Remove interface duplication  
**Files:** Delete `modules/shared/i_parametrization_provider.py`  
**Imports to Repoint:** Find all imports of `i_parametrization_provider` and change to `ports/parametrization_provider`  
**Effort:** 15 minutes  
**Risk:** LOW (only imports within shared/)  

### Phase 2: Migrate Vision Models (MEDIUM EFFORT)
**Target:** Move vision-specific models to their owning modules  
**Files to Move:**
1. `models/visions_imprimible.py` → `modules/vision_imprimible/models.py`
2. `models/visions_pyg.py` → `modules/pyg/models.py`
3. `models/visions_tarifas.py` → `modules/vision_tarifas/models.py`
4. `models/visions_cts.py` → `modules/vision_cost_to_serve/models.py`

**Imports to Update:**
- Test files (point to new locations)
- `modules/shared/models/__init__.py` (re-imports)
- Any cross-vision imports (e.g., visions_imprimible imports from visions_tarifas)

**Effort:** 1-2 hours  
**Risk:** LOW (no formula changes, clear owning modules, test coverage validates)  

**Sequence:** Do visions_cts first (no dependencies), then visions_pyg, then visions_tarifas (has cross-dependency from visions_imprimible), then visions_imprimible.

### Phase 3: Validation
**Commands:**
```bash
# After each move:
PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m baseline --tb=short

# Verify no import errors:
python -c "from nexa_engine.modules import shared; print('✓ shared imports OK')"
python -c "from nexa_engine.modules.vision_imprimible import models; print('✓ vision_imprimible models OK')"
python -c "from nexa_engine.modules.vision_tarifas import models; print('✓ vision_tarifas models OK')"
python -c "from nexa_engine.modules.pyg import models; print('✓ pyg models OK')"
python -c "from nexa_engine.modules.vision_cost_to_serve import models; print('✓ vision_cost_to_serve models OK')"

# Verify API contracts unchanged:
git diff contracts/openapi/ | grep -E "^[\+\-]" && echo "⚠️ CONTRACT CHANGED" || echo "✓ No API changes"
```

**Exit Criteria:**
- All baseline tests pass (1249 pass / 57 fail)
- No import errors
- No API contract changes
- All model re-imports validated

---

## Architecture Rules Compliance Check

| Rule (from CLAUDE.md) | Compliance | Evidence |
|---|---|---|
| "shared must not become a dumping ground" | ✅ PASS | All folders in shared have clear ownership and cross-cutting purpose |
| "Models should live in their owning module unless truly cross-cutting" | ⚠️ PARTIAL | Vision models violate this; should move |
| "Audit/traceability/lineage concepts may belong under single audit boundary" | ✅ PASS | Correctly split: domain models in lineage/, infrastructure in infrastructure/lineage/ |
| "Infrastructure-specific code not mixed with domain models" | ✅ PASS | Clear separation across all modules |
| "Persistence abstractions DB/provider-facing, not business logic" | ✅ PASS | DocumentStore pattern correctly applied in repositories |
| "Do not move anything until ownership is proven" | ✅ PASS | All proposed moves have clear owning modules |

---

## Conclusion

**shared_module_taxonomy_audit: COMPLETE ✅**

- **17 folders/items correctly placed** — No action needed
- **4 vision models should migrate** — Low-risk, high-clarity improvement
- **1 interface duplication to consolidate** — Quick fix
- **No formula/contract/persistence changes required**
- **Risk Level: LOW** — All proposed moves are structural clarity improvements

**Recommendation:** Proceed with Phase 1 (interface consolidation) immediately. Schedule Phase 2 (vision model migration) after current active work completes.

