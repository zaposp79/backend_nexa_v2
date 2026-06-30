# Backend Production Smoke Audit

**Date:** 2026-06-13
**Branch:** `refactor/modular-pure`
**Auditor:** backend-agent (read-only; no runtime changes made)

> This audit does not reopen V2-8, engine, API, or persistence closure.
> No runtime behavior was changed.

---

## Executive Summary

The backend starts cleanly and registers all 38 expected routes. The core calculation, parametrization, audit, and certification flows are wired correctly. Two medium-priority production risks exist:

1. **`list_simulations` is filesystem-only** — `AuditSimulationUseCase.list_simulations()` iterates `repo.base_dir` on the local filesystem even when a DocumentStore is configured. In production with `DB_PROVIDER=cosmos`, the audit `/simulations` list will always return `[]`.

2. **Two module-level `get_provider()` calls at import time** — `db/dependencies.py` and `modules/calculator/api/calculate_dependencies.py` call `get_provider()` at module import time (before the lifespan mounts the container). This is by design (documented in both files), but it means the DocumentStore singleton is built from env vars at import time, not from the lifespan. If env vars are not set before the first import, the JSON fallback is silently used.

All other DI wiring, config guards, and health endpoints are in order.

---

## Baseline

```
git log --oneline -3:
  18af430  fix(api): resolve pre-existing API contract failures
  82e03d6  fix(persistence): enforce lineage store and invalidate version cache
  ef6a050  docs(persistence): decide lineage storage and version cache strategy

API suite:   114/114 PASS
golden suite: 99/99 PASS
make verify: ✅ Baseline match. Sin drift.
```

---

## Startup Status

```
Entrypoint: backend_nexa/app.py  (create_app factory)
app type:   FastAPI
routes:     38

Import result:   CLEAN (no import errors or unhandled warnings at startup)
Lifespan:        ensure_storage_dirs() → build_container() → yield → container.close()
Docs in prod:    DISABLED (docs_enabled = app_env != "production")
```

The `create_app()` factory is safe to import without side effects. The DocumentStore is built inside the lifespan, not at import time — the container owns the "real" store. The two module-level singletons (`_lineage_repo` in `db/dependencies.py` and `_store` in `calculate_dependencies.py`) are intentional composition roots for non-Depends paths; they call `get_provider()` at import time which reads from env vars at that moment.

---

## Registered Routers

| Router | Prefix | Source |
|--------|--------|--------|
| Parametrization HR | `/api/v1/parametrization/hr` | `modules/parametrizacion/hr/api/router.py` |
| Parametrization GN | `/api/v1/parametrization/gn` | `modules/parametrizacion/gn/api/router.py` |
| Parametrization OP | `/api/v1/parametrization/op` | `modules/parametrizacion/op/api/router.py` |
| Panel / Cadenas | `/api/v1/simulation/input/...` | `modules/panel/`, `modules/cadena_*/` |
| Calculate | `/api/v1/simulation/calculate` | `modules/calculator/api/calculate_router.py` |
| Results | `/api/v1/simulation/{id}/results/...` | `modules/calculator/api/results_router.py` |
| Audit | `/api/v1/audit/...` | `modules/audit/api/audit_router.py` |
| Certification | `/api/v1/certification/...` | `modules/certification/` |
| Vision Imprimible | `/api/v1/simulation/{id}/results/vision-imprimible` | `modules/vision_imprimible/api/router.py` |
| Vision P&G | `/api/v1/simulation/{id}/results/vision-pyg` | `modules/pyg/` |
| Vision Tarifas | `/api/v1/simulation/{id}/results/vision-tarifas` | `modules/vision_tarifas/` |
| Cost to Serve | `/api/v1/simulation/{id}/results/cost-to-serve` | `modules/vision_cost_to_serve/` |
| Health | `/health` | `app.py` (inline) |

All 38 routes confirmed registered (includes 4 Swagger routes active in dev, 1 health, 33 API routes).

---

## Router/DI Risks

| Component | File | Responsibility | Import/DI status | Risk |
|-----------|------|----------------|------------------|------|
| `create_app` factory | `app.py` | FastAPI app + middleware + routers | CLEAN — lazy; no side effects at import | OK |
| `make_lifespan` | `modules/shared/infrastructure/lifespan.py` | startup storage dirs + container build | CLEAN — runs at ASGI startup, not import | OK |
| `build_container` | `db/container.py` | owns the real DocumentStore for DI tree | CLEAN — built inside lifespan | OK |
| `get_provider()` in `db/dependencies.py:19` | `db/dependencies.py` | module-level `_lineage_repo` singleton | Built at import time from env vars; intentional design; if env changes after import the singleton is stale | LOW |
| `get_provider()` in `calculate_dependencies.py:19` | `modules/calculator/api/calculate_dependencies.py` | module-level `_store`, `_results_repo`, etc. | Same as above — intentional; documented in module docstring | LOW |
| `_version_registry` singleton | `modules/shared/versioning/registry_provider.py` | shared VersionRegistry for normal calculate + activation invalidation | Reads storage at first `get_current()` call; invalidated on parametrization activation | OK |
| HR/GN/OP activation routers | `modules/parametrizacion/*/api/router.py` | call `_version_registry.invalidate_cache()` after success | Correctly wired; no cycles; import chain is `shared/versioning/registry_provider → version_registry (stdlib only)` | OK |
| `get_audit_use_case` | `db/dependencies.py` + `audit_router.py` | Depends-injected `AuditSimulationUseCase` | CLEAN — resolved per request via `get_lineage_repository → container.lineage_repository` | OK |
| `AuditSimulationUseCase.list_simulations()` | `modules/audit/use_cases/audit_simulation.py:155` | Lists all lineage simulations | Always iterates `repo.base_dir` (filesystem); returns `[]` in Cosmos/multi-pod deployments | MEDIUM |
| `LineageSnapshotRepository` (post-F4) | `modules/lineage/infrastructure/snapshot_repository.py` | save/load/exists | DocumentStore path exclusive when store configured; filesystem for `store=None` | OK |
| `NexaPricingEngine` | `modules/calculator_motor/engine.py` | core calculation pipeline | Created per request in normal handler with singleton `_version_registry`; certified handler creates fresh registry per request | OK |
| Audit `/simulations` endpoint | `modules/audit/api/audit_router.py:161` | `list_audit_simulations` | Delegates to `list_simulations()` which has filesystem gap (see above) | MEDIUM |

---

## Config/Env Risks

| Variable | File | Current behavior | Production risk | Classification |
|----------|------|-----------------|-----------------|----------------|
| `APP_ENV` | `app_settings.py` | defaults to `"development"`; validation fails if not in `{development, test, production}` | If not set in prod, Swagger docs and reload are enabled | PROD_CONFIG_REQUIRED |
| `CORS_ALLOWED_ORIGINS` | `app_settings.py` | required (no wildcard) when `APP_ENV=production`; raises `DbConfigurationError` at startup if missing | Hard fail at startup prevents silent misconfiguration | OK |
| `DB_PROVIDER` | `db/config.py` | defaults to `"json"`; falls back to local `storage/` | In Cosmos environments, must be explicitly set to `"cosmos"` or JSON is silently used | SILENT_FALLBACK_RISK |
| `COSMOS_ENDPOINT` | `db/config.py` | optional; if set with `DB_PROVIDER != cosmos`, triggers `ALLOW_COSMOS_NON_PRODUCTION` guard | Guard raises `DbConfigurationError` unless opted-in | OK |
| `COSMOS_KEY` | `db/config.py` | required when `DB_PROVIDER=cosmos`; raises at startup if missing | Fails fast — no silent missing key | OK |
| `COSMOS_DATABASE` | `db/config.py` | required when `DB_PROVIDER=cosmos` | Fails fast | OK |
| `COSMOS_CONTAINER` | `db/config.py` | required when `DB_PROVIDER=cosmos` | Fails fast | OK |
| `JSON_STORAGE_PATH` | `db/config.py` | defaults to `<project_root>/storage`; detects production-like env (APP_ENV=production + no explicit path) and warns | Safe default for dev; production should set explicitly | MISSING_ENV_DEFAULT |
| `ALLOW_COSMOS_NON_PRODUCTION` | `app_settings.py` | defaults to `false`; allows Cosmos+Swagger in non-prod when `true` | Risky if set to `true` in a prod-facing deployment | LOCAL_ONLY |
| `HEALTH_PATH` | `app_settings.py` | defaults to `/health`; configurable | No risk — inline handler, no external deps | OK |
| Redis / cache | — | Not present | No Redis/cache dependencies in any module | OK |
| Auth / JWT / bearer | — | Not present | No authentication layer wired | MISSING_ENV_DEFAULT (gap, not risk) |

---

## Health Endpoint Status

| Endpoint/test | Exists | Behavior | Gap/Risk |
|---------------|--------|----------|----------|
| `GET /health` | YES | Returns `{"status": "ok", "service": "nexa-simulator-api"}` | No deep-health check (DocumentStore/Cosmos connectivity not probed) |
| Health CORS test (`test_sec_p0_1_production_hardening`) | YES — 2 tests PASS | Validates origin allow/reject + correlation-id | OK |
| Health contract test (`test_health_endpoint_contract_unchanged`) | YES — PASS | Checks `status == "ok"` | OK |
| Readiness/liveness probe (`/ready`, `/live`) | NO | Only `/health` exists | HEALTH_ENDPOINT_GAP — no Cosmos connectivity check; no readiness distinction from liveness |
| Deep health (DocumentStore ping) | NO | `/health` does not query the store | In Cosmos deployments a pod may report healthy while Cosmos is unreachable |

---

## Production Smoke Findings

| Priority | Area | Risk | Evidence | Recommended action |
|----------|------|------|----------|--------------------|
| 1 | `list_simulations` filesystem-only | MEDIUM | `audit_simulation.py:156` — `base = self._repo.base_dir`; always reads filesystem regardless of DocumentStore | Add a DocumentStore-backed enumeration path to `list_simulations` (or expose `LineageSnapshotRepository.list()`) |
| 2 | `DB_PROVIDER` silently defaults to `json` | MEDIUM | `db/config.py:DEFAULT_PROVIDER = "json"`; no startup warning if `DB_PROVIDER` is unset in a Cosmos environment | Add a startup log warning if `COSMOS_ENDPOINT` is set but `DB_PROVIDER != cosmos` (already partially handled by guard, but only on the `ALLOW_COSMOS_NON_PRODUCTION` path) |
| 3 | Module-level `get_provider()` called at import time | LOW | `db/dependencies.py:19`, `calculate_dependencies.py:19` — singletons built before lifespan; config must be in env before first import | Acceptable for the current deployment model; document that env vars must be set before gunicorn/uvicorn workers fork |
| 4 | `APP_ENV` defaults to `"development"` | LOW | `app_settings.py:86` — if `APP_ENV` unset in production, Swagger + reload are exposed | Deployment infra must set `APP_ENV=production`; currently no startup warning when docs are enabled |
| 5 | No deep-health / readiness probe | LOW | `/health` always returns 200 even if Cosmos is unreachable; k8s/Azure Container Apps would route traffic to an unhealthy pod | Add `GET /health/ready` that pings DocumentStore.ping() (or similar) |
| 6 | `AuditSimulationUseCase` creates its own `VersionRegistry` per request | LOW | `audit_simulation.py:123` — `self._version_registry = version_registry or VersionRegistry()`; not the shared singleton | Not a correctness bug (registry reads from disk per-instance), but misses the benefit of F8 cache invalidation for audit responses. Pass the singleton at construction time. |
| 7 | No authentication layer | INFO | No JWT/bearer/API-key middleware wired | Acceptable if deployed behind an API gateway; document assumption |

---

## Top Recommended Fixes

In priority order (not implemented in this session):

1. **`list_simulations` DocumentStore support** — add `DocumentStore.list(lineage_snapshots)` enumeration to `LineageSnapshotRepository` and update `list_simulations()` to use it when store is configured.

2. **Startup warning for implicit JSON fallback in Cosmos env** — if `COSMOS_ENDPOINT` is set but `DB_PROVIDER` is not `"cosmos"`, log a `WARNING` at startup.

3. **Deep-health / readiness endpoint** — add `GET /health/ready` that returns 503 if the DocumentStore is unreachable (probe with a lightweight `.list()` or `.get()` on a sentinel collection).

4. **Pass `_version_registry` singleton to `AuditSimulationUseCase`** — in `db/dependencies.py`'s `get_audit_use_case`, pass `_version_registry` so F8 invalidation benefits audit responses.

---

## What Not to Touch

- `modules/calculator_motor/**` — calculation engine, formulas, pipeline
- `request/request.json` — canonical test request
- `storage/parametrization/**` — parametrization data
- `tests/golden/fixtures/**` — golden test fixtures
- baseline snapshots — `storage/baselines/`
- Excel reference files
- V2-8 docs, engine audit docs, API audit docs, persistence audit docs

---

## Appendix: Route List (38 total)

```
/openapi.json               GET, HEAD  (dev only)
/docs                       GET, HEAD  (dev only)
/docs/oauth2-redirect       GET, HEAD  (dev only)
/redoc                      GET, HEAD  (dev only)
/api/v1/parametrization/hr/upload                    POST
/api/v1/parametrization/hr/versions                  GET
/api/v1/parametrization/hr/active                    GET
/api/v1/parametrization/hr/{version_id}/activate     GET
/api/v1/parametrization/hr/{version_id}              DELETE
/api/v1/parametrization/gn/upload                    POST
/api/v1/parametrization/gn/versions                  GET
/api/v1/parametrization/gn/active                    GET
/api/v1/parametrization/gn/{version_id}/activate     GET
/api/v1/parametrization/gn/{version_id}              DELETE
/api/v1/parametrization/op/upload                    POST
/api/v1/parametrization/op/versions                  GET
/api/v1/parametrization/op/active                    GET
/api/v1/parametrization/op/{version_id}/activate     GET
/api/v1/parametrization/op/{version_id}              DELETE
/api/v1/simulation/input/panel/parametros            GET
/api/v1/simulation/input/chain-a/parametros          GET
/api/v1/simulation/input/chain-b/parametros          GET
/api/v1/simulation/input/chain-c/parametros          GET
/api/v1/simulation/calculate                         POST
/api/v1/simulation/{id}/results                      GET
/api/v1/simulation/{id}/traceability                 GET
/api/v1/simulation/{id}/results/vision-imprimible    GET
/api/v1/simulation/{id}/results/vision-pyg           GET
/api/v1/audit/simulations                            GET
/api/v1/audit/simulation/{id}                        GET
/api/v1/audit/simulation/{id}/explain                GET
/api/v1/audit/simulation/{id}/baseline-diff          GET
/api/v1/certification/certificates                   GET
/api/v1/certification/certificate/{id}               GET
/api/v1/certification/verify/{id}                    POST
/api/v1/simulation/{id}/results/vision-tarifas       GET
/api/v1/simulation/{id}/results/cost-to-serve        GET
/health                                              GET
```
