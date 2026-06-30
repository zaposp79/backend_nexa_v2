# Lineage Bounded Context Extraction

**Status:** COMPLETE  
**Branch:** HEAD (refactor/modular-pure)  
**Supersedes:** `docs/refactor/lineage_module_boundary_cleanup.md` (old scatter-location doc)

---

## 1. Trigger

Lineage code was scattered across three locations with no clear ownership:

| Location | Content |
|---|---|
| `modules/shared/lineage/` | Domain models (`LineageRef`, `LineageNode`, `LineageGraph`) and `LineageQuery` |
| `modules/shared/infrastructure/lineage/` | `JsonLineageEmitter`, `NullLineageEmitter`, `LineageSnapshotRepository` |
| `modules/traceability/lineage/` | `seed_lineage_from_request`, `seed_lineage_from_result` builder |

No single owner. Any module needing lineage had to span two or three import paths.

---

## 2. Inventory (Phase 0)

Files moved (6 total):

| Old path | New path |
|---|---|
| `modules/shared/lineage/models.py` | `modules/lineage/domain/models.py` |
| `modules/shared/lineage/query.py` | `modules/lineage/domain/query.py` |
| `modules/shared/infrastructure/lineage/json_lineage_emitter.py` | `modules/lineage/infrastructure/json_emitter.py` |
| `modules/shared/infrastructure/lineage/null_emitter.py` | `modules/lineage/infrastructure/null_emitter.py` |
| `modules/shared/infrastructure/lineage/snapshot_repository.py` | `modules/lineage/infrastructure/snapshot_repository.py` |
| `modules/traceability/lineage/lineage_builder.py` | `modules/lineage/application/builder.py` |

Files kept in place (not moved — out of scope per PHASE 0 decisions):
- `modules/shared/models/` — VisionImprimible, DesgloseCTSCadenaA/B, CostosTotalesMes, PolizaConfiguracion
- `modules/shared/contracts/api_v1/response/audit.py` — `LineageRefV1` is a **decoupled API DTO** (no domain imports)

Files deleted (shim `__init__.py` at old locations):
- `modules/shared/lineage/__init__.py`
- `modules/shared/infrastructure/lineage/__init__.py`
- `modules/traceability/lineage/__init__.py`

---

## 3. New Package Structure

```
modules/lineage/
  __init__.py            ← public API doc; no re-exports (consumers must use explicit layer paths)
  domain/
    __init__.py
    models.py            ← LineageRef, LineageNode, LineageGraph, SOURCE_TYPE_* constants
    query.py             ← LineageQuery
  infrastructure/
    __init__.py
    json_emitter.py      ← JsonLineageEmitter
    null_emitter.py      ← NullLineageEmitter (depends on shared/ports/trace_emitter — intentional)
    snapshot_repository.py ← LineageSnapshotRepository
  application/
    __init__.py
    builder.py           ← seed_lineage_from_request, seed_lineage_from_result
```

**No re-exports at `modules/lineage/__init__.py`** (per user decision). Consumers must import from
explicit layer paths.

---

## 4. Imports Updated

Production files (9):

| File | Change |
|---|---|
| `modules/audit/api/audit_router.py` | `shared.lineage.models` → `lineage.domain.models` |
| `modules/calculator_motor/engine.py` | `shared.infrastructure.lineage.*` + `traceability.lineage.*` → `lineage.infrastructure.*` + `lineage.application.builder` |
| `modules/shared/use_cases/audit_simulation.py` | `shared.lineage.*` + `shared.infrastructure.lineage.*` → `lineage.domain.*` + `lineage.infrastructure.*` |
| `modules/shared/use_cases/certified_calculation.py` | `shared.infrastructure.lineage.snapshot_repository` → `lineage.infrastructure.snapshot_repository` |
| `db/container.py` | `shared.infrastructure.lineage.snapshot_repository` → `lineage.infrastructure.snapshot_repository` |
| `db/dependencies.py` | same as above |
| `modules/lineage/infrastructure/null_emitter.py` (self) | internal self-references fixed |
| `modules/lineage/infrastructure/json_emitter.py` (self) | internal self-references fixed |
| `modules/lineage/application/builder.py` (self) | internal self-references fixed |

Test files (11):

- `tests/lineage/test_lineage_emitter.py`
- `tests/lineage/test_lineage_integration.py`
- `tests/lineage/test_lineage_query.py`
- `tests/api/test_audit_endpoint.py`
- `tests/certification/mode_w15/test_certified_lineage_includes_certificate.py`
- `tests/certification/mode_w15/test_certified_mode_basic.py`
- `tests/versioning/test_audit_response_includes_versions.py`
- `tests/versioning/test_backward_compat_legacy_lineage.py`
- `tests/versioning/test_lineage_includes_real_versions.py`
- `tests/versioning/test_simulation_id_mapping.py`
- `tests/db/contract/test_lineage_repository_documentstore_wiring.py`

---

## 5. Route Before / After

Unchanged. `GET /api/v1/audit/simulation/{simulation_id}` and related audit routes are in
`modules/audit/api/audit_router.py` — this file was an importer update only, no route changes.

---

## 6. Guardrails Before / After

`tests/unit/test_traceability_boundary_guardrails.py` — `TestLineageModuleOwnership` class replaced:

| Before | After |
|---|---|
| G-LINEAGE-1: assert `shared/lineage/` has exactly `{__init__, models, query}` | G-LINEAGE-1: assert `shared/lineage/models.py` and `query.py` do NOT exist |
| G-LINEAGE-2: assert `shared/infrastructure/lineage/` has exact allowlist | G-LINEAGE-2: assert both stale files do NOT exist |
| G-LINEAGE-3: assert `traceability/lineage/` has `{__init__, lineage_builder.py}` | G-LINEAGE-3: assert `lineage_builder.py` does NOT exist there |
| G-LINEAGE-4: import symbols from old paths + assert `__module__` strings | G-LINEAGE-4: 6 tests importing from new `lineage.{domain,infrastructure,application}` paths |
| G-LINEAGE-5: route unchanged | G-LINEAGE-5: route unchanged |
| G-LINEAGE-6: assert ≥3 consumers import from `shared.lineage` | G-LINEAGE-6: assert 0 consumers import from stale paths; ≥2 import from `modules.lineage` |
| (none) | Anti-regression: stale `shared.lineage.models`, `traceability.lineage.lineage_builder` raise `ModuleNotFoundError` |
| (none) | Structural: assert `lineage/{domain,infrastructure,application}/*.py` exist |

Also fixed in same file:
- `test_g_6b2_traceability_lineage_builder_exists` → `_removed` (asserts NOT exists)
- `test_g_6b3_lineage_builder_importable` → now imports from `lineage.application.builder`
- `test_g_6b8_formulas_do_not_import_traceability` → `formulas_root` fixed to `_CALC_MOTOR / "formulas"`

---

## 7. Test Results (Phase 4)

| Suite | Result |
|---|---|
| `tests/unit/test_traceability_boundary_guardrails.py` | **42/42 passed** |
| `tests/refactor/` | **95 passed** |
| `tests/golden/` | **63 passed** |
| `tests/refactor/test_baseline_formula_snapshot_v1.py` | **10 passed** |

---

## 8. Drift Status

- Formula drift: **none** — zero formula/calculation files modified.
- API contract drift: **none** — routes, response shapes, DTOs unchanged.
- Parametrization drift: **none** — no parametrization files touched.
- `LineageRefV1` in `shared/contracts/api_v1/response/audit.py` remains a standalone Pydantic model with no imports from `modules/lineage` — correct and intentional (API/domain separation).

---

## 9. Remaining Decisions

| Item | Status |
|---|---|
| `PolizaConfiguracion` flagged DEAD_CODE in Phase 0 | Deferred — out of scope for this extraction |
| `modules/lineage/__init__.py` has no re-exports | Final — per explicit user decision |
| `NullLineageEmitter` depends on `shared/ports/trace_emitter` | Final — lineage infra consumes shared/ports; direction is correct |

---

## 10. Supersedes

This document supersedes `docs/refactor/lineage_module_boundary_cleanup.md`, which described the
pre-extraction scatter-location structure. That file should be treated as historical.
