# Persistence and Traceability Audit

**Branch:** `refactor/modular-pure`
**Scope:** read-only — no runtime files were modified.
**Date:** 2026-06-12

---

## Executive summary

The persistence and traceability layer is broadly correct: `DocumentStore` abstraction is clean,
`simulation_id` is UUID-based (no collision risk), and the main result read path (`ResultsRepository`)
raises `NotFoundError` consistently. Seven risk findings were identified. None is a current production
blocker, but two (`F1`, `F2`) are actionable in the next sanitization pass.

The most material risk is `F1`: the `AuditIntegrityError` handler still exposes `type`/`module`
Python internals and may surface raw `str(exc)` from the underlying snapshot store failure — the same
pattern that was fixed for `DomainError`, `ValueError`, `ParametrizationError`, and `VisionIncompleteError`
in previous passes but was missed for this exception path.

---

## Baseline

Confirmed before this audit session:

| Suite | Count |
|---|---|
| Golden (99 tests) | **99/99 PASS** |
| `make verify` | **PASS** |

No runtime files were modified. Baseline is unchanged.

---

## Runtime flow map

```
POST /api/v1/simulation/calculate
  │
  ├─ SimulationContextBuilder.construir(user_input) → PricingRequest
  │
  ├─ NexaPricingEngine.calcular(request, with_lineage=True/False)
  │     → (PricingResult, LineageGraph | None)
  │
  ├─ simulation_id = resultado.simulation_id  OR  _results_repo.new_id()
  │                                                [uuid.uuid4() — non-deterministic]
  │
  ├─ _results_repo.save(full_result_dict)           [FATAL — AuditIntegrityError on fail]
  │     DocumentStore.upsert("simulation_results", sim_id, data)
  │
  ├─ _trace_writer.write(sim_id, raw_request=body.user_input, ...)
  │     TraceabilityRepository.save(record)          [NON-FATAL — exception swallowed]
  │       DocumentStore.upsert("simulation_traceability", sim_id, data)
  │
  ├─ _snapshot_repo.save(snapshot)                   [FATAL — AuditIntegrityError on fail]
  │     DocumentStore.upsert("simulation_snapshots", sim_id, data)
  │
  └─ if with_lineage=True:
        LineageSnapshotRepository.save(graph)
          DocumentStore.save → fallback to filesystem on failure
          [NON-FATAL at this layer — but audit endpoint will fail if graph not persisted]

GET /simulation/{sim_id}/results
  └─ ResultsRepository.get(sim_id)          → raises NotFoundError → 404

GET /simulation/{sim_id}/traceability
  └─ TraceabilityRepository.get(sim_id)     → returns None on miss (not exception)

GET /audit/simulation/{sim_id}
  └─ LineageSnapshotRepository.load(sim_id)
        DocumentStore.load → fallback to filesystem on DocumentStore failure
     AuditSimulationUseCase.execute(sim_id)
     → AuditResponseV1 (formula_set from VersionRegistry live metadata)
```

---

## simulation_id lifecycle findings

| # | Finding | Severity | File |
|---|---|---|---|
| — | `simulation_id` from `uuid.uuid4()` | OK | `results_repository.py:new_id()` |
| — | Upsert semantics: same `simulation_id` silently overwrites | BY_DESIGN | `DocumentStore.upsert()` |
| — | Engine result may carry its own `simulation_id` (lineage graph) | OK | `calculate_normal_handler.py` |

In normal operation, every request produces a fresh UUID. Upsert-on-same-ID is safe in production
(UUID collision probability is astronomically low). No write-once guard is needed.

---

## Result persistence findings

| # | Finding | Severity | Location |
|---|---|---|---|
| F1 | `AuditIntegrityError` handler exposes `type`/`module` + raw `exc.message` in HTTP response | HIGH | `calculate_normal_handler.py:388–394` |
| — | `ResultsRepository.save()` fatal path raises `AuditIntegrityError` (controlled) | OK | `calculate_normal_handler.py` |
| — | `ResultsRepository.get()` raises domain `NotFoundError` on miss | OK | `results_repository.py` |
| — | `SnapshotRepository.save()` non-fatal: swallows all exceptions but the handler wraps in `AuditIntegrityError` | OK | `snapshots_repository.py` + handler |

**F1 detail:**

```python
# calculate_normal_handler.py  lines 383–394  (unfixed path)
except AuditIntegrityError as exc:
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            success=False,
            error=ErrorDetail(
                code="AUDIT_INTEGRITY_ERROR",
                message=exc.message,          # ← may contain str(_snap_exc) with file paths / system errors
                details={
                    "module": type(exc).__module__,  # ← leaks internal module path
                    "type":   type(exc).__name__,    # ← leaks exception class name
                }
            ),
        ).model_dump(),
    )
```

`exc.message` is constructed at line ~207 as:
```python
f"SimulationSnapshot obligatorio no pudo persistirse: {_snap_exc}"
```
This includes `str(_snap_exc)` which in a Cosmos/filesystem error may contain:
- OS-level error strings (`No such file or directory`)
- Cosmos SDK messages with endpoint/key fragments
- Internal DocumentStore implementation details

Same sanitization applied to `DomainError`/`ValueError`/`VisionIncompleteError` must be applied here.

---

## Traceability and lineage findings

| # | Finding | Severity | Location |
|---|---|---|---|
| F2 | `SnapshotRepository.get()` raises `FileNotFoundError` (Python builtin) not domain `NotFoundError` | MEDIUM | `snapshots_repository.py:get()` |
| F3 | `TraceabilityWriter.write()` stores full `raw_request` (complete user input) in traceability record | MEDIUM | `audit/writer.py` |
| F4 | `LineageSnapshotRepository` dual-storage path (DocumentStore → filesystem fallback) creates split-brain risk | MEDIUM | `lineage/infrastructure/snapshot_repository.py` |
| F5 | `AuditResponseV1.formula_set` default is stale (`"formula-set-v2-7"`) — WAVE 14 comment outdated | LOW | `shared/contracts/api_v1/response/audit.py` |

**F2 detail:**

All other repositories raise `NotFoundError` (domain) on miss:
- `ResultsRepository.get()` → `NotFoundError` ✓
- `TraceabilityRepository.get()` → returns `None` (inconsistent, see F7)
- `SnapshotRepository.get()` → raises `FileNotFoundError` ← breaks any handler with `except NotFoundError`

Currently `SnapshotRepository.get()` is not called from any HTTP handler path, so this is latent.
Any future endpoint that retrieves a snapshot will encounter an uncontrolled 500 if the handler
catches `NotFoundError` but not `FileNotFoundError`.

**F3 detail:**

`TraceabilityWriter.write()` builds the traceability record with:
```python
"raw_request": raw_request   # body.user_input — full client business payload
```
This includes client names, pricing margins, service types, FTE counts, CAPEX figures, etc.
In `DB_PROVIDER=cosmos` production mode, this data lands in the `simulation_traceability` container
without any redaction or sanitization. Access controls are entirely external (Cosmos RBAC).
This is technically correct for audit purposes, but must be treated as sensitive data at rest.
No sanitization layer exists in the application.

**F4 detail:**

`LineageSnapshotRepository` saves to DocumentStore primary and falls back to filesystem on failure.
In a multi-pod deployment (e.g., Azure Container Apps) with ephemeral filesystem:

1. Pod A saves lineage → DocumentStore fails → filesystem fallback on Pod A
2. Pod B receives `GET /audit/simulation/{id}` → DocumentStore fails → filesystem fallback on Pod B
3. Pod B filesystem is empty → `AuditNotAvailableError` (silent lineage loss)

The fallback is logged at `logger.error()` level, but no alerting, metrics, or circuit-breaker exists.
In single-pod or local `DB_PROVIDER=json` deployments, this path is safe.

---

## Repository / DB error handling findings

| # | Finding | Severity | Location |
|---|---|---|---|
| F6 | `SnapshotRepository.list_summaries()` is a TODO stub — always returns `[]` | LOW | `snapshots_repository.py` |
| F7 | `TraceabilityRepository.get()` returns `None` on miss (not `NotFoundError`) | LOW | `traceability_repository.py` |
| F8 | `VersionRegistry` singleton cache never invalidated after parametrization upload/activation | LOW | `shared/versioning/version_registry.py` + `calculate_dependencies.py` |

**F6 detail:**

```python
def list_summaries(self, ...):
    logger.warning("list_summaries is not yet implemented")
    return []
```

Any audit/monitoring UI that enumerates calculator snapshots gets an empty list.
No exception is raised, so callers cannot distinguish "no snapshots" from "stub not implemented".

**F7 detail:**

`TraceabilityRepository.get(sim_id)` returns `None` on miss. This is inconsistent with
`ResultsRepository.get()` (raises `NotFoundError`). The traceability router handles `None`
with an explicit check, so no current breakage. But any future code doing `trac.field` on the
return value without a `None` check gets `AttributeError` → uncontrolled 500.

**F8 detail:**

`VersionRegistry` instances are created once at import time in `calculate_dependencies.py`:
```python
_version_registry = VersionRegistry(...)  # singleton, created at import
```

After a parametrization upload and activation (`POST /parametrization/op/upload`), the registry
`_cached` value still reflects the pre-upload state. `formula_set` in the audit response (and
`parametrization_hashes`) will continue to report the old version until process restart.
`invalidate_cache()` exists on `VersionRegistry` but is never called by the activation flow.

---

## Test coverage gaps

| Gap | Risk | Suggested test |
|---|---|---|
| `AuditIntegrityError` response does NOT expose `type`/`module` | HIGH | `test_calculate_endpoint_error_sanitization.py` — add audit-integrity-error case |
| `AuditIntegrityError` message does not contain `str(exc)` from underlying failure | HIGH | same file |
| `SnapshotRepository.get()` raises `FileNotFoundError` (document inconsistency) | MEDIUM | `tests/db/` unit test |
| `TraceabilityRepository.get()` returns `None` on miss (document inconsistency) | LOW | `tests/db/` unit test |
| `VersionRegistry` cache survives simulated parametrization update without invalidation | LOW | `tests/parametrizacion/` |
| `LineageSnapshotRepository` filesystem fallback is triggered on DocumentStore failure | LOW | unit test with mock DocumentStore |
| Raw `raw_request` is stored in traceability record (content audit) | MEDIUM | `tests/db/test_traceability_writer.py` |

---

## Top recommended fixes

| Priority | Fix | File | Scope |
|---|---|---|---|
| **1** | Sanitize `AuditIntegrityError` handler: remove `type`/`module`; replace `message=exc.message` with `"Error de integridad de auditoría."` | `calculate_normal_handler.py:383–394` | 4-line change |
| **2** | `SnapshotRepository.get()`: raise `NotFoundError` instead of `FileNotFoundError` to align with domain contract | `calculator/persistence/snapshots_repository.py:get()` | 1-line change |
| **3** | `VersionRegistry.invalidate_cache()`: call after parametrization version activation to keep `formula_set` and `parametrization_hashes` current | `parametrizacion/*/services/activate.py` + `calculate_dependencies.py` | medium scope |
| **4** | `TraceabilityRepository.get()`: raise `NotFoundError` on miss (consistent with `ResultsRepository`) and update results router | `calculator/persistence/traceability_repository.py` + router | medium scope |
| **5** | Add `AuditIntegrityError` sanitization tests to `test_calculate_endpoint_error_sanitization.py` (2 tests) | `tests/api/test_calculate_endpoint_error_sanitization.py` | test-only |

---

## What not to touch

The following are correct by design and must not be changed based on this audit:

- `NexaPricingEngine.calcular()` — engine logic, no persistence responsibilities.
- `DocumentStore.upsert()` semantics — correct; same-ID overwrite is intentional.
- `TraceabilityRepository.save()` non-fatal pattern — intentional: traceability write failure
  must not block the primary result response.
- `simulation_id = uuid.uuid4()` — adequate entropy, no collision risk.
- Golden fixtures, V2-8 baselines, parity test suite.

---

## Scope

| Category | Files touched |
|---|---|
| Runtime files modified | **0** |
| Test files modified | **0** |
| New docs | `docs/refactor/persistence_traceability_audit.md` (this file) |

This audit does not reopen V2-8, the engine audit, or the API error-sanitization audit.
No runtime behavior was changed.
