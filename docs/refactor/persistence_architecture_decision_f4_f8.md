# Architecture Decision: Persistence Risks F4 and F8

**Branch:** `refactor/modular-pure`
**Date:** 2026-06-12
**Status:** DECIDED — pending implementation
**Author:** NEXA backend team

---

## Executive Summary

Two structural risks remain open after the persistence fix wave (F1–F3, F5–F7):

| ID | Risk class | Impact | Urgency |
|----|-----------|--------|---------|
| F4 | `LineageSnapshotRepository` filesystem fallback → split-brain in multi-pod | Silent audit data loss in Cosmos/multi-pod deployments | High on `DB_PROVIDER=cosmos`; none on `json` |
| F8 | `VersionRegistry` process-lifetime cache not invalidated on parametrization activation | Stale `formula_set` / `parametrization_hashes` in audit responses after hot-swap | Medium — functional correctness issue |

Neither risk affects calculation output or financial values (the engine is stateless). They affect only the **audit trail** and **version metadata** recorded after calculation.

---

## Baseline at Decision Point

```
golden tests: 99/99 PASS
make verify:  ✅ Baseline match. Sin drift.
last commit:  2309f94  fix(persistence): clean low-risk audit contracts
```

---

## F4 — LineageSnapshotRepository Split-Brain

### Current behavior

**File:** `modules/lineage/infrastructure/snapshot_repository.py`

```
save():
  1. Try DocumentStore.upsert(_COLLECTION, document)
  2. On ANY exception → logger.error() + _save_filesystem() fallback

load():
  1. Try DocumentStore.get(_COLLECTION, simulation_id)
  2. On DbNotFoundError / any exception → _load_filesystem() fallback

exists():
  Same dual-path as load().
```

`_save_filesystem()` writes to `self._base_dir / <sim_id> / lineage.json`
where `_base_dir` defaults to `Path(os.getcwd()) / "storage" / "lineage"`.

### Production risk analysis

| Scenario | `DB_PROVIDER` | Result |
|----------|--------------|--------|
| Cosmos transient error during save | `cosmos` | Lineage written to **Pod A** local ephemeral storage. Pod A restart → lineage gone. Audit returns `AuditNotAvailableError`. |
| Load routed to different pod (Pod B) | `cosmos` | Pod B has no local lineage file → `_load_filesystem()` raises `FileNotFoundError` → caller sees `AuditNotAvailableError`. |
| Normal operation (Cosmos healthy) | `cosmos` | No split-brain; DocumentStore is single source of truth. |
| Normal operation | `json` | Filesystem IS the DocumentStore backing (`storage/` dir). The fallback writes to the same location. No split-brain. |
| Unit/CI tests | any | No Cosmos; `json` provider. No split-brain risk. |

### Risk classification

```
PROD_SPLIT_BRAIN_RISK
Probability: LOW (Cosmos is reliable; triggers only on transient error)
Impact: MEDIUM (silent audit loss; calculation result unaffected)
Blast radius: lineage/audit only — not simulation_results, not snapshots
```

### RCA

The fallback was designed for `DB_PROVIDER=json` offline use (scripts, testing). It predates the multi-pod deployment target. The assumption "filesystem is always accessible" holds for local dev but not for Azure Container Apps ephemeral containers.

### Design options

| Option | Description | Pro | Con |
|--------|-------------|-----|-----|
| **A (Recommended)** | On DocumentStore failure, raise immediately (no filesystem fallback at runtime). Log error. Caller records `AuditNotAvailableError`. | Fail-fast; no silent data loss; single source of truth | Audit unavailable on Cosmos transient error |
| B | Retain fallback but emit structured metric/alert; skip on non-`json` provider | Preserves fallback for local | Alert infra needed; still split-brain risk if metric dropped |
| C | Write to both DocumentStore AND filesystem always | Redundancy | Double writes; filesystem as secondary index; wasted I/O |
| D | Circuit breaker: after N Cosmos failures in a window, switch to filesystem mode for the pod lifetime | Graceful degradation | Complexity; still pod-local; overkill for audit data |

**Chosen option: A**

Guard at the top of `save()`: if `self._store is not None`, disable the filesystem fallback path entirely. Filesystem fallback remains only when `store=None` (legacy offline scripts). This makes the split-brain scenario structurally impossible.

The `_load_filesystem()` path in `load()` should behave analogously: if a `DocumentStore` is present and the document is not found, raise `FileNotFoundError` (existing behavior from `_load_filesystem`) which the caller maps to `AuditNotAvailableError`. Do NOT silently succeed by returning a stale local file that belongs to a different pod's run.

### Implementation plan

| Step | File | Change |
|------|------|--------|
| 1 | `modules/lineage/infrastructure/snapshot_repository.py` | In `save()`: wrap DocumentStore path in `if self._store is not None:`; on exception, re-raise (no `_save_filesystem` fallback). In `load()`: when `self._store is not None` and document not found in DocumentStore, raise `FileNotFoundError` directly (do not fall through to filesystem). |
| 2 | Same file | Add docstring note: "filesystem fallback is only active when `store=None` (offline/legacy)." |
| 3 | `tests/unit/test_lineage_snapshot_repository_f4.py` | New unit tests: (a) Cosmos save failure raises (not silent), (b) Cosmos miss on load raises, (c) filesystem fallback active when `store=None`. |

### Tests required

```python
# Case 1: store present, DocumentStore.upsert raises → exception propagates
# Case 2: store present, DocumentStore.get raises DbNotFoundError → FileNotFoundError raised
# Case 3: store=None → filesystem fallback active (legacy path intact)
# Case 4: store=None, file missing → FileNotFoundError raised
```

---

## F8 — VersionRegistry Cache Invalidation

### Current behavior

**File:** `modules/shared/versioning/version_registry.py`

```python
class VersionRegistry:
    def __init__(self, storage_root: Optional[Path] = None) -> None:
        self._cached: Optional[VersionMetadata] = None
        self._cached_hashes: Optional[Dict[str, str]] = None

    def get_current(self, baseline_version=None) -> VersionMetadata:
        if self._cached is not None and baseline_version is None:
            return self._cached   # ← returns stale value forever
        # ... reads from storage, computes hashes, caches ...
        if baseline_version is None:
            self._cached = meta
        return meta

    def invalidate_cache(self) -> None:
        """Drop cached metadata. Useful when storage changes mid-process."""
        self._cached = None
        self._cached_hashes = None
```

**Singleton creation** in `modules/calculator/api/calculate_dependencies.py`:

```python
# (via db/dependencies.py import chain)
_version_registry = VersionRegistry(...)   # created at import time
```

**Activation flow** (`modules/parametrizacion/*/api/router.py` → service → storage):
- Writes new `versions.json` with `is_active=True`.
- Does NOT call `_version_registry.invalidate_cache()`.

### Production risk analysis

| Scenario | Result |
|----------|--------|
| Process starts, reads parametrization version `v2-8`. First calculation audit reports `formula_set="formula-set-v2-8"`. ✅ | Correct |
| Admin uploads a new OP Excel, activates it (new version ID e.g. `v2-9`). | `versions.json` updated on disk. |
| Next calculation on same process. | `_version_registry.get_current()` returns cached `formula_set="formula-set-v2-8"`. **Stale.** |
| Audit response reports `formula_set="formula-set-v2-8"` for a simulation that used `v2-9` parameters. | **Incorrect audit trail.** |
| Process restart (deploy or manual). | Cache cleared. `get_current()` reads new `v2-9`. ✅ |

### Risk classification

```
STALE_AFTER_SET_ACTIVE
Probability: MEDIUM (any parametrization hot-swap without process restart)
Impact: MEDIUM (audit reports wrong formula_set; does not affect calculation)
Blast radius: AuditResponseV1.formula_set, AuditResponseV1.parametrization_hashes only
```

### RCA

`invalidate_cache()` was designed for this exact use case but was never wired to the activation endpoint. The method exists; the call site does not. The cache is process-lifetime because `VersionRegistry` is instantiated at module import time and not re-created by the activation flow.

Note: in `audit_simulation.py:328–354`, stale `formula_set="formula-set-v2-7"` from old WAVE 13 graphs triggers a fallback via `self._version_registry.get_current()`. This fallback reads from the same cached registry — so after F5 removed the default, the fallback still calls the potentially stale singleton.

### Design options

| Option | Description | Pro | Con |
|--------|-------------|-----|-----|
| **A (Recommended)** | Parametrization activation service calls `_version_registry.invalidate_cache()` after writing `versions.json` | Minimal change; uses existing method; O(1) | Couples activation service to versioning module |
| B | VersionRegistry reads from disk on every call (no cache) | Always fresh | I/O per calculation; hashing on every request |
| C | TTL-based cache (e.g. 60 seconds) | Bounded staleness | Complexity; staleness still possible within window |
| D | Inject VersionRegistry into parametrization service; invalidate on activate | Clean DI | Requires wiring to parametrization service factory |
| E | Event bus: activation event → registry listener | Fully decoupled | Overkill for single-process; no event bus exists |

**Chosen option: A**

Wire `_version_registry.invalidate_cache()` into the activation endpoint handler (or the activation service layer). The `_version_registry` singleton is accessible via `calculate_dependencies.py`; a direct import into the parametrization activation handler is acceptable. This is a one-line call at the right place.

### Implementation plan

| Step | File | Change |
|------|------|--------|
| 1 | `modules/parametrizacion/hr/api/router.py` (and `gn`, `op` equivalents) | After the activation service call succeeds, call `_version_registry.invalidate_cache()`. Import from `calculate_dependencies`. |
| 2 | `modules/calculator/api/calculate_dependencies.py` | Export `_version_registry` in `__all__`. |
| 3 | `tests/unit/test_version_registry_invalidation_f8.py` | Tests: (a) after invalidation, next `get_current()` re-reads from disk; (b) activation endpoint calls invalidate. |

**Alternative if coupling to calculate_dependencies is undesirable:** Create a `VersionRegistryProvider` singleton at `db/dependencies.py` level (alongside `_lineage_repo`) so it has a neutral owner visible to both the parametrization routers and the calculate handler.

### Tests required

```python
# Case 1: VersionRegistry.get_current() returns cached value after first call
# Case 2: after invalidate_cache(), get_current() re-reads storage
# Case 3: parametrization activation endpoint calls invalidate_cache() (mock)
# Case 4: two sequential calculations after activation report new formula_set
```

---

## Recommended Strategy

### Immediate next phase (one PR, isolated)

Implement **F4-Option-A** and **F8-Option-A** together. Both are minimal surgical changes:

- F4: 3–5 lines changed in `snapshot_repository.py` + 1 new test file.
- F8: 1 line per activation router (3 routers) + export + 1 new test file.

Total surface: ≤ 15 lines of production code changed.

### What NOT to touch

- `modules/calculator_motor/**` — engine is stateless; no changes needed.
- `modules/calculator/persistence/**` — F2/F7 already fixed.
- `modules/audit/use_cases/audit_simulation.py` — fallback logic at line 344 reads from the same `_version_registry`; once F8 is fixed (cache invalidated on activation), the fallback will naturally return the correct live value.
- `storage/parametrization/**`, golden fixtures, baseline snapshots, Excel files.
- `make baseline` — not needed; no calculation logic changes.

### Risk of implementation

Both fixes are **additive guards**, not logic changes. F4 removes a fallback path (makes errors visible instead of silent). F8 adds a cache bust call (makes metadata fresher). Neither can introduce financial drift.

---

## Implementation Summary Table

| Fix | File | Lines | New tests | Risk |
|-----|------|-------|-----------|------|
| F4 | `modules/lineage/infrastructure/snapshot_repository.py` | ~5 | `tests/unit/test_lineage_snapshot_repository_f4.py` (4 cases) | LOW |
| F8 | `modules/parametrizacion/hr/api/router.py` + `gn` + `op` | 1 per router | `tests/unit/test_version_registry_invalidation_f8.py` (4 cases) | LOW |
| F8 export | `modules/calculator/api/calculate_dependencies.py` | 1 | — | LOW |

---

## Appendix — What Each Risk Does NOT Affect

| Concern | F4 | F8 |
|---------|----|----|
| Calculation output (financial values) | No impact | No impact |
| `simulation_results/` DocumentStore | No impact | No impact |
| `simulation_snapshots/` DocumentStore | No impact | No impact |
| `PricingResult` / `PricingRequest` | No impact | No impact |
| API contract (endpoints, schemas) | No impact | No impact |
| Test suite / baseline | No impact | No impact |
| Excel parity | No impact | No impact |
