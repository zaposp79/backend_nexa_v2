# LINEAGE_MODULE_BOUNDARY_CLEANUP

> ⚠️ **SUPERSEDED** by [`lineage_bounded_context_extraction.md`](lineage_bounded_context_extraction.md).
> The scatter-location structure described here no longer exists. This file is kept for historical reference only.

**Status:** ✅ COMPLETE (superseded)

**Date:** 2026-06-10

**Outcome:** NO MOVES REQUIRED — Current lineage module layout is correct and follows ownership rules.

---

## Executive Summary

Investigation into lineage module ownership revealed that the current partition is **clean, intentional, and correctly designed**:

- **modules/shared/lineage/** — Domain models (LineageGraph, LineageNode, LineageRef, LineageQuery)
- **modules/shared/infrastructure/lineage/** — Infrastructure (JsonLineageEmitter, LineageSnapshotRepository, NullLineageEmitter)
- **modules/traceability/lineage/** — Application-specific builders (seed_lineage_from_request, seed_lineage_from_result)

All three folders contain code that serves either **cross-cutting** use cases (audit, certification, engine) or **traceability-specific** application logic. No ownership conflicts, no duplicates, no split problems.

---

## 1. Final Lineage Inventory

| Path | Files | Purpose | Classification | Ownership Decision |
|---|---|---|---|---|
| `modules/shared/lineage/` | models.py, query.py, __init__.py | Domain: LineageGraph, LineageNode, LineageRef, LineageQuery | SHARED_CROSS_CUTTING | **STAY** (cross-cutting evidence) |
| `modules/shared/infrastructure/lineage/` | json_lineage_emitter.py, snapshot_repository.py, null_emitter.py, __init__.py | Infrastructure: Persistence and construction of lineage graphs | SHARED_CROSS_CUTTING | **STAY** (cross-cutting evidence) |
| `modules/traceability/lineage/` | lineage_builder.py, __init__.py | Application: seed_lineage_from_request, seed_lineage_from_result | TRACEABILITY_OWNED | **STAY** (correct ownership) |

**Total lines of code:** 1230

---

## 2. Cross-Cutting Evidence

### Consumers of `modules/shared/lineage/` (models + query)

**Non-test consumers:**
1. ✅ `modules/shared/use_cases/audit_simulation.py` — Uses LineageGraph, LineageQuery, LineageNode
2. ✅ `modules/shared/use_cases/certified_calculation.py` — Uses LineageGraph, LineageNode
3. ✅ `modules/audit/api/audit_router.py` — Uses LineageRef
4. ✅ `modules/traceability/lineage/lineage_builder.py` — Uses LineageRef, SOURCE_TYPE constants
5. ✅ `modules/calculator_motor/engine.py` — Reads/queries lineage graphs

**Justification:** ≥2 unrelated consumers (audit, certification, traceability) → **Cross-cutting.**

### Consumers of `modules/shared/infrastructure/lineage/`

**Non-test consumers:**
1. ✅ `modules/calculator_motor/engine.py` — Uses JsonLineageEmitter, LineageSnapshotRepository
2. ✅ `modules/shared/use_cases/audit_simulation.py` — Uses LineageSnapshotRepository
3. ✅ `modules/shared/use_cases/certified_calculation.py` — Uses LineageSnapshotRepository
4. ✅ `db/dependencies.py` — Builds _lineage_repo (DI container)
5. ✅ `modules/shared/helpers/certified_helpers.py` — Uses for hashing lineage

**Justification:** Used by engine, audit, certification, and DI container → **Cross-cutting.**

### Consumers of `modules/traceability/lineage/lineage_builder.py`

**Non-test consumers:**
1. ✅ `modules/calculator_motor/engine.py` — Imports seed_lineage_from_request, seed_lineage_from_result

**Justification:** Builder functions are **application-specific** to the traceability domain (seed nodes from request/result data). Correct ownership.

---

## 3. Ownership Decisions

### Decision 1: shared/lineage stays (models + query)

**Rule Applied:** "modules/shared/lineage stays ONLY if proven cross-cutting (≥2 unrelated consumers)"

**Evidence:** ✅ Consumed by audit, certification, traceability, engine → **Cross-cutting.**

**Why not move to traceability?**
- Audit and certification are independent of traceability and must be able to query lineage graphs
- Engine produces lineage graphs for multiple use cases, not just traceability
- Models are generic financial lineage abstractions, not traceability-specific

**Verdict:** **STAY in shared/lineage/** (cross-cutting rule satisfied)

---

### Decision 2: shared/infrastructure/lineage stays (persistence + emitter)

**Rule Applied:** "lineage infrastructure → traceability only if consumed by traceability; otherwise leave + document"

**Evidence:** ✅ Consumed by engine, audit_simulation, certified_calculation, DI container → **Multiple domains, not traceability-specific.**

**Why not move to traceability?**
- The emitter is instantiated by the ENGINE (calculator_motor), not by traceability
- Persistence is read by audit and certification use cases
- Infrastructure is domain-agnostic (JSON/Cosmos DocumentStore pattern)

**Verdict:** **STAY in shared/infrastructure/lineage/** (cross-cutting usage)

---

### Decision 3: traceability/lineage/lineage_builder stays

**Rule Applied:** "lineage application logic specific to traceability module"

**Evidence:** ✅ Builders are called only by engine; logic is specific to seeding nodes from request/result

**Why here?**
- seed_lineage_from_request / seed_lineage_from_result are application-specific decisions
- They define what nodes to emit for financial traceability semantics
- They belong in the traceability module conceptually

**Verdict:** **STAY in traceability/lineage/** (correct application ownership)

---

## 4. Files Moved

**NONE** — Current layout is optimal.

---

## 5. Files Intentionally Left in shared

**All lineage files in shared are justified:**

| File | Justification |
|---|---|
| `shared/lineage/models.py` | Domain models used by audit, certification, engine |
| `shared/lineage/query.py` | Read-only query logic used by audit, tests |
| `shared/infrastructure/lineage/json_lineage_emitter.py` | Infrastructure for building graphs; used by engine and tests |
| `shared/infrastructure/lineage/snapshot_repository.py` | Persistence layer used by audit, certification, engine, DI container |
| `shared/infrastructure/lineage/null_emitter.py` | Test infrastructure support |

---

## 6. Imports Updated

**NONE** — No files were moved, so no imports needed updating.

---

## 7. Route Paths Before/After

**No change.** Traceability endpoint remains:

```
GET /api/v1/simulation/{simulation_id}/traceability
  Handler: modules.traceability.api.results_router.get_traceability
  Payload: FieldTraceabilityRegistry.build() result (field classification)
```

**Note:** This endpoint returns field-level audit/compliance classification, NOT the financial lineage graph. Lineage graph is persisted separately by LineageSnapshotRepository.

---

## 8. Tests Executed & Results

### ✅ test/refactor/
```
95 passed, 3 deselected
```

### ✅ tests/golden/
```
63 passed, 82 deselected
```

### ✅ tests/refactor/test_baseline_formula_snapshot_v1.py + test_baseline_formula_snapshot_cadena_c_v1.py
```
10 passed
```

### ✅ tests/unit/test_traceability_boundary_guardrails.py (NEW LINEAGE GUARDRAILS)
```
32 passed (26 existing + 6 new lineage-specific)
```

**Total:** 200+ tests green. ✅ **Drift status: CLEAN — no numerical changes.**

---

## 9. Drift Status

✅ **NONE** — All calculations identical before/after. No breaking changes.

---

## 10. Guardrails Added

Six new assertions in `tests/unit/test_traceability_boundary_guardrails.py::TestLineageModuleOwnership`:

1. **G-LINEAGE-1:** Exact allowlist for `shared/lineage/` files
2. **G-LINEAGE-2:** Exact allowlist for `shared/infrastructure/lineage/` files
3. **G-LINEAGE-3:** Exact allowlist for `traceability/lineage/` files
4. **G-LINEAGE-4:** No duplicate symbols between shared and traceability
5. **G-LINEAGE-5:** Route `/api/v1/simulation/{simulation_id}/traceability` is registered
6. **G-LINEAGE-6:** Cross-cutting consumer snapshot (regression alarm)

**Purpose:** Lock the current layout as intentional design. Future drift (new files, moved symbols, missing consumers) will be caught immediately.

---

## 11. Remaining Decisions (Out of Scope)

### A. audit_router.py coupling to shared.lineage.LineageRef

**Finding:** `modules/audit/api/audit_router.py` imports LineageRef directly from shared/lineage/models.

**Consideration:** Evaluate whether audit should consume lineage through an explicit read-model contract instead (dependency inversion). Currently acceptable but may benefit from abstraction layer in future.

**Recommendation:** Out of scope for this task. Document for WAVE 15+ architectural review.

---

### B. Audit & Certification use cases may belong to bounded contexts

**Finding:** `modules/shared/use_cases/audit_simulation.py` and `modules/shared/use_cases/certified_calculation.py` are currently in shared/ as cross-cutting use cases.

**Consideration:** If audit and certification become their own modules, these use cases should move to their respective owners. Currently they're in shared because they're consumed by multiple routes.

**Recommendation:** Out of scope for this task. Revisit during PHASE 12+ when modules stabilize.

---

## 12. Dependency Graph (Verified Acyclic)

```
traceability/lineage_builder.py
  ↓ imports
shared/lineage/models.py
  ↓ (no circular imports back)

engine.py
  ↓ imports
shared/infrastructure/lineage/json_lineage_emitter.py (instantiates)
shared/infrastructure/lineage/snapshot_repository.py (uses)
traceability/lineage_builder.py (imports functions)
  ↓ (no circular imports back)

audit_simulation.py, certified_calculation.py
  ↓ imports
shared/lineage/models.py
shared/lineage/query.py
shared/infrastructure/lineage/snapshot_repository.py
  ↓ (no circular imports back)
```

✅ **Acyclic. No circular dependencies detected.**

---

## Summary

| Aspect | Status |
|---|---|
| **Files moved** | ✅ NONE (optimal) |
| **Files deleted** | ✅ NONE |
| **Imports updated** | ✅ NONE |
| **Route paths changed** | ✅ NO |
| **Tests passing** | ✅ 200+ (refactor + golden + baseline + guardrails) |
| **Numerical drift** | ✅ CLEAN |
| **Guardrails added** | ✅ 6 new assertions |
| **Ownership locked** | ✅ YES (regression alarm in place) |

**Conclusion:** Lineage module ownership is **clean, intentional, and production-ready.** No refactoring required. Guardrails in place to prevent future drift.

