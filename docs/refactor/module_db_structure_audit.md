# Module & DB Structure Audit

**Date:** 2026-06-13  
**Branch:** `refactor/modular-pure`  
**Auditor:** backend-agent (read-only)  
**Status:** READ-ONLY — no code changed, no files moved, no files deleted

---

## 1. Executive Verdict

The architecture is **structurally sound at the domain level**. Vertical slices for `parametrizacion/{hr,gn,op}`, `cadena_{a,b,c}`, `vision_*`, and `lineage` follow clean module boundaries. The `db/` infrastructure layer is well-separated.

**Primary debts identified:**

| Category | Count | Risk |
|----------|-------|------|
| Empty placeholder packages (no `.py` files) | 11 | LOW — footprint noise |
| Deprecated shims (backward-compat re-exports still in place) | 6 | MEDIUM — confusion about canonical paths |
| Wildcard re-export surface (`shared/models/__init__.py`) | 1 | MEDIUM — hides canonical owners, used by certified core |
| Misnamed files (`reglas.py` for calculator classes) | 3 | LOW — naming only; functional |
| Dual config (`config.py` + `app_settings.py` in shared/config) | 1 | LOW — some overlap |
| `db/factory.py` module-level cache | 1 | LOW — only risk under hot-reload |

**Certified core is fully protected.** No formula or engine file is proposed to move in the first blocks.

---

## 2. CERTIFIED_CORE_FREEZE

| Frozen path/pattern | Reason | certified_core | golden_impact | Decision |
|---------------------|--------|---------------|--------------|----------|
| `modules/calculator_motor/**` | Engine pipeline, all 10 calculation layers | DIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/calculator_motor/formulas/**` | All formula implementations | DIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/calculator_motor/mixins/**` | Context builders and input normalizers feeding engine | DIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/calculator_motor/engine.py` | Single engine entry point; `NexaPricingEngine.calcular()` | DIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/calculator_motor/adapters/**` | Entry data adapters used by the engine pipeline | DIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/calculator_motor/serializers/**` | `PricingResult` serialization; used in baseline | DIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/pyg/services/**` | `PyGCalculator`, `CostosTotalesCalculator`, `KPIsCalculator` — imported directly by `engine.py` | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/pyg/builders/vision_pyg_builder.py` | PyG view builder called from engine pipeline | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/cadena_b/reglas.py` | `CadenaBCalculator` imported by `engine.py:65` and `costos_totales_calculator.py` | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/cadena_c/reglas.py` | `CadenaCCalculator` imported by `engine.py:66` and `costos_totales_calculator.py` | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/vision_tarifas/reglas.py` | `VisionTarifasCalculator` imported by `engine.py:78` | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/shared/models/results.py` | `PricingResult` and all result dataclasses; backward-compat adapter used by 15+ modules including certified core | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/shared/models/__init__.py` | Wildcard re-export; imported by `engine.py`, all mixins, all serializers, `cadena_b/c/reglas.py` | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/shared/ports/parametrization_provider.py` | `IParametrizationProvider` Protocol; implemented by all parametrization providers consumed by engine | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/parametrizacion/services/provider.py` | `ParametrizationProvider` — live parametrization consumed by engine | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/parametrizacion/services/certified_provider.py` | Frozen parametrization provider used in certified/reproducibility mode | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/parametrizacion/mixins/**` | Provider business rule mixins (salary, rotation, staffing, fin/op) | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/parametrizacion/repositories/**` | Domain repositories backing the active provider | INDIRECT | INDIRECT | DEFER_CERTIFIED_CORE |
| `request/request.json` | Canonical deal input; changes propagate to all golden test values | DIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `storage/parametrization/**` | Active parametrization data consumed by provider | DIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `tests/golden/fixtures/**` | Frozen golden test values | DIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `excel/**` | Excel reference files; source of truth for business rules | DIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `storage/baselines/**` | `make verify` baseline snapshots | DIRECT | DIRECT | DEFER_CERTIFIED_CORE |

**Rules enforced for all blocks:**
- Do not propose moving any `calculator_motor` file.
- Do not propose touching golden fixtures, request, storage parametrization, or Excel.
- Do not propose formula rewrites.
- Do not propose baseline regeneration.

---

## 3. Repository State

```
Branch:  refactor/modular-pure
State:   2 dirty files (excel/ and storage/ — gitignored, not tracked)
         1 untracked (artifacts/ — not committed)
         Working tree clean for all committed code
```

**Counts:**
- Python files under `modules/`: **366**
- Python files under `db/`: **20**
- Empty package directories (no `.py` files, only `__init__.py` or `__pycache__`): **11**

---

## 4. `modules/` Compact Inventory

### Top-level modules

| current_path | short_responsibility | decision |
|---|---|---|
| `modules/api_v1/router.py` | Top-level API v1 composition root — includes all subrouters | KEEP_AS_IS |
| `modules/audit/api/audit_router.py` | HTTP endpoints for audit trail | KEEP_AS_IS |
| `modules/audit/integration.py` | Hooks audit events into engine lifecycle | KEEP_AS_IS |
| `modules/audit/registry.py` | `FieldTraceabilityRegistry` — in-memory audit state | KEEP_AS_IS |
| `modules/audit/trace.py` | Audit trace domain model | KEEP_AS_IS |
| `modules/audit/use_cases/audit_simulation.py` | Records simulation audit trail | KEEP_AS_IS |
| `modules/audit/writer.py` | Writes audit records to storage | KEEP_AS_IS |
| `modules/cadena_a/api/chain_a_router.py` | HTTP endpoints for Cadena A input | KEEP_AS_IS |
| `modules/cadena_a/dto/cadena_a_dto.py` | Cadena A DTOs | KEEP_AS_IS |
| `modules/cadena_a/enums/cargo_tipo.py` | Cargo type enum — correctly owned by cadena_a | KEEP_AS_IS |
| `modules/cadena_a/payroll/__init__.py` | **Empty package** — only docstring, no `.py` files | DELETE_CANDIDATE |
| `modules/cadena_a/services/cadena_a_service.py` | Service for Cadena A input persistence | KEEP_AS_IS |
| `modules/cadena_a/services/nomina_cargada.py` | Nomina cargada service | KEEP_AS_IS |
| `modules/cadena_a/services/parameters_query_service.py` | Parametrization query for Cadena A context | KEEP_AS_IS |
| `modules/cadena_a/services/special_roles_calculator.py` | Special roles calc helper | KEEP_AS_IS |
| `modules/cadena_a/staffing/__init__.py` | **Empty package** — only docstring, no real Python files | DELETE_CANDIDATE |
| `modules/cadena_a/staffing/calculators.py` | **Only in `__pycache__`** — no source file on disk | DEFER_IMPORT_RISK |
| `modules/cadena_a/use_cases/build_payroll.py` | Builds payroll context for Cadena A | KEEP_AS_IS |
| `modules/cadena_a/use_cases/build_staffing.py` | Builds staffing context for Cadena A | KEEP_AS_IS |
| `modules/cadena_b/api/chain_b_router.py` | HTTP endpoints for Cadena B input | KEEP_AS_IS |
| `modules/cadena_b/dto/cadena_b_dto.py` | Cadena B DTOs | KEEP_AS_IS |
| `modules/cadena_b/reglas.py` | `CadenaBCalculator` — **misnamed**: name implies business rules, content is a calculator service; imported by certified core | DEFER_CERTIFIED_CORE |
| `modules/cadena_b/services/cadena_b_service.py` | Service for Cadena B input persistence | KEEP_AS_IS |
| `modules/cadena_b/services/parameters_query_service.py` | Parametrization query for Cadena B context | KEEP_AS_IS |
| `modules/cadena_c/api/chain_c_router.py` | HTTP endpoints for Cadena C input | KEEP_AS_IS |
| `modules/cadena_c/dto/cadena_c_dto.py` | Cadena C DTOs | KEEP_AS_IS |
| `modules/cadena_c/reglas.py` | `CadenaCCalculator` — **misnamed** same issue as cadena_b; certified core | DEFER_CERTIFIED_CORE |
| `modules/cadena_c/services/parameters_query_service.py` | Parametrization query for Cadena C context | KEEP_AS_IS |
| `modules/calculator/api/calculate_certified_handler.py` | Certified mode calculation handler | KEEP_AS_IS |
| `modules/calculator/api/calculate_dependencies.py` | FastAPI dependencies for calculation endpoints | KEEP_AS_IS |
| `modules/calculator/api/calculate_dto.py` | Request/response DTOs for calculate endpoint | KEEP_AS_IS |
| `modules/calculator/api/calculate_normal_handler.py` | Normal mode calculation handler | KEEP_AS_IS |
| `modules/calculator/api/calculate_router.py` | Calculate API router | KEEP_AS_IS |
| `modules/calculator/api/calculate_validate.py` | Input validation for calculate endpoint | KEEP_AS_IS |
| `modules/calculator/api/results_router.py` | Results retrieval API (public VisionImprimible) | KEEP_AS_IS |
| `modules/calculator/helpers/certified_helpers.py` | Hashing helpers for certified mode — **misplaced** in helpers, should be use_cases or services | READY_TO_MOVE |
| `modules/calculator/persistence/results_repository.py` | Results DocumentStore repository | KEEP_AS_IS |
| `modules/calculator/persistence/snapshots_repository.py` | Snapshots DocumentStore repository | KEEP_AS_IS |
| `modules/calculator/persistence/traceability_repository.py` | Traceability DocumentStore repository | KEEP_AS_IS |
| `modules/calculator/use_cases/certified_calculation.py` | Certified calculation use case orchestration | KEEP_AS_IS |
| `modules/calculator_motor/**` (all files) | Engine core — all certified | DEFER_CERTIFIED_CORE |
| `modules/certification/api/certification_router.py` | Certification API endpoint | KEEP_AS_IS |
| `modules/certification/certificate_repository.py` | Certificate persistence | KEEP_AS_IS |
| `modules/certification/models.py` | Certificate models | KEEP_AS_IS |
| `modules/lineage/application/builder.py` | Lineage trace builder | KEEP_AS_IS |
| `modules/lineage/domain/models.py` | Lineage domain models | KEEP_AS_IS |
| `modules/lineage/domain/query.py` | Lineage query model | KEEP_AS_IS |
| `modules/lineage/infrastructure/json_emitter.py` | JSON lineage emitter | KEEP_AS_IS |
| `modules/lineage/infrastructure/null_emitter.py` | Null emitter (no-op tracing) | KEEP_AS_IS |
| `modules/lineage/infrastructure/snapshot_repository.py` | Lineage snapshot repo | KEEP_AS_IS |
| `modules/panel/api/panel_router.py` | Panel HTTP endpoints | KEEP_AS_IS |
| `modules/panel/dto/panel_dto.py` | Panel DTOs | KEEP_AS_IS |
| `modules/panel/models/panel.py` | Panel domain models (`PanelDeControl`, etc.) | KEEP_AS_IS |
| `modules/panel/services/panel_service.py` | Panel input persistence service | KEEP_AS_IS |
| `modules/parametrizacion/api/gn_router.py` | **Deprecated shim** re-exporting from `parametrizacion/gn/api/router.py` | REMOVE_TEMP_ADAPTER |
| `modules/parametrizacion/api/hr_router.py` | **Deprecated shim** re-exporting from `parametrizacion/hr/api/router.py` | REMOVE_TEMP_ADAPTER |
| `modules/parametrizacion/api/op_router.py` | **Deprecated shim** re-exporting from `parametrizacion/op/api/router.py` | REMOVE_TEMP_ADAPTER |
| `modules/parametrizacion/api/router.py` | Parametrizacion aggregate router (legitimate composition) | KEEP_AS_IS |
| `modules/parametrizacion/enums/types.py` | Parametrization type enums | KEEP_AS_IS |
| `modules/parametrizacion/gn/**` | GN domain — well-structured | KEEP_AS_IS |
| `modules/parametrizacion/hr/**` | HR domain — well-structured | KEEP_AS_IS |
| `modules/parametrizacion/mixins/**` | Provider mixins — needed, owns business rule application | KEEP_AS_IS |
| `modules/parametrizacion/op/**` | OP domain — well-structured | KEEP_AS_IS |
| `modules/parametrizacion/repositories/**` | Domain repositories for HR/GN/OP data | KEEP_AS_IS |
| `modules/parametrizacion/services/certified_provider.py` | Frozen/certified provider | DEFER_CERTIFIED_CORE |
| `modules/parametrizacion/services/provider.py` | Active parametrization provider | DEFER_CERTIFIED_CORE |
| `modules/parametrizacion/services/resolver.py` | Version resolution logic | KEEP_AS_IS |
| `modules/parametrizacion/shared/**` | Parametrization cross-cutting infrastructure | KEEP_IN_SHARED |
| `modules/pyg/api/vision_router.py` | P&G vision HTTP endpoint | KEEP_AS_IS |
| `modules/pyg/builders/vision_pyg_builder.py` | Builds VisionPyG from PricingResult — **certified core** | DEFER_CERTIFIED_CORE |
| `modules/pyg/dto/models.py` | P&G DTO models | KEEP_AS_IS |
| `modules/pyg/services/costos_totales_calculator.py` | `CostosTotalesCalculator` — **certified core** (imported by engine) | DEFER_CERTIFIED_CORE |
| `modules/pyg/services/kpis_calculator.py` | `KPIsCalculator` — **certified core** | DEFER_CERTIFIED_CORE |
| `modules/pyg/services/pyg_calculator.py` | `PyGCalculator` — **certified core** | DEFER_CERTIFIED_CORE |
| `modules/pyg/use_cases/` | **Empty package** — only `__init__.py` in `__pycache__` | DELETE_CANDIDATE |
| `modules/shared/**` | See Section 5 (shared/ ownership audit) | (per file) |
| `modules/vision_cost_to_serve/api/router.py` | CTS vision HTTP endpoint | KEEP_AS_IS |
| `modules/vision_cost_to_serve/dto/models.py` | CTS DTO models | KEEP_AS_IS |
| `modules/vision_cost_to_serve/helpers/servicio_catalogo.py` | Service catalog helper — owned by vision_cost_to_serve | KEEP_AS_IS |
| `modules/vision_cost_to_serve/models/cts_facts.py` | CTS computation facts model | KEEP_AS_IS |
| `modules/vision_cost_to_serve/services/cost_to_serve_calculator.py` | CTS calculator service | KEEP_AS_IS |
| `modules/vision_imprimible/api/public_mapper.py` | Public mapper for Visión Imprimible API projection | KEEP_AS_IS |
| `modules/vision_imprimible/api/response_models.py` | Typed response models for public API | KEEP_AS_IS |
| `modules/vision_imprimible/api/router.py` | Vision Imprimible HTTP endpoint | KEEP_AS_IS |
| `modules/vision_imprimible/builders/vision_datasets_builder.py` | Internal dataset builder | KEEP_AS_IS |
| `modules/vision_imprimible/builders/vision_imprimible_builder.py` | Full vision builder | KEEP_AS_IS |
| `modules/vision_imprimible/helpers/*.py` | Vision-specific helpers — correctly owned by this module | KEEP_AS_IS |
| `modules/vision_imprimible/models/vision_datasets.py` | Dataset models | KEEP_AS_IS |
| `modules/vision_imprimible/models/visions_imprimible.py` | Vision composite model | KEEP_AS_IS |
| `modules/vision_tarifas/api/router.py` | Vision Tarifas HTTP endpoint | KEEP_AS_IS |
| `modules/vision_tarifas/dto/models.py` | Vision Tarifas DTO models | KEEP_AS_IS |
| `modules/vision_tarifas/mixins/reglas_methods*.py` | Vision Tarifas calculation mixins | KEEP_AS_IS |
| `modules/vision_tarifas/models/visions_tarifas.py` | Vision Tarifas models | KEEP_AS_IS |
| `modules/vision_tarifas/models/vt_facts.py` | VT computation facts | KEEP_AS_IS |
| `modules/vision_tarifas/reglas.py` | `VisionTarifasCalculator` — **misnamed** (should be `calculator.py` or `vision_tarifas_calculator.py`); imported by certified core | DEFER_CERTIFIED_CORE |
| `modules/vision_tarifas/builders/` | **Empty package** — only `__pycache__` | DELETE_CANDIDATE |
| `modules/vision_tarifas/services/` | **Empty package** — only `__pycache__` | DELETE_CANDIDATE |
| `modules/vision_tarifas/use_cases/build_scenarios.py` | Builds scenario comparison data | KEEP_AS_IS |

---

## 5. `modules/shared/` Ownership Audit

`shared/` is used by many modules. Detailed classification below.

```bash
# Usage scan: who imports from shared
# (grepped across modules/ and db/)
```

| current_path | used_by_modules | is_generic | domain_owner_detected | shared_validity | proposed_owner | adapter_required | decision |
|---|---|---|---|---|---|---|---|
| `shared/__init__.py` | all | YES | none | VALID | — | NO | KEEP_IN_SHARED |
| `shared/exceptions.py` | 10+ modules | YES | none | VALID — base exceptions are cross-cutting | — | NO | KEEP_IN_SHARED |
| `shared/responses.py` | all API modules | YES | none | VALID — generic `ApiResponse` envelope | — | NO | KEEP_IN_SHARED |
| `shared/precision.py` | multiple calculators | YES | none | VALID — generic math helper | — | NO | KEEP_IN_SHARED |
| `shared/config/config.py` | parametrizacion, db | YES | none | VALID — storage paths + security limits | — | NO | KEEP_IN_SHARED |
| `shared/config/app_settings.py` | app.py, db | YES | none | VALID — deployment config | — | NO | KEEP_IN_SHARED |
| `shared/config/business_rules/loader.py` | calculator_motor, cadena_a | PARTIAL | calculator_motor / shared | VALID at current location | — | NO | KEEP_IN_SHARED |
| `shared/config/business_rules_loader.py` | 0 direct imports found | YES | none | **INVALID** — DEPRECATED shim; canonical path is `config/business_rules/loader.py` | — | NO | REMOVE_TEMP_ADAPTER |
| `shared/contracts/api_v1/adapter.py` | calculator/api/calculate_dto.py | YES | none | VALID — API contract adapter bridging entry_data to engine DTO | — | NO | KEEP_IN_SHARED |
| `shared/contracts/api_v1/request/**` | calculator, parametrizacion, tests | YES | none | VALID — public API input contracts | — | NO | KEEP_IN_SHARED |
| `shared/contracts/api_v1/response/**` | calculator, certification, tests | YES | none | VALID — public API response contracts | — | NO | KEEP_IN_SHARED |
| `shared/helpers/__init__.py` | — | YES | none | **EMPTY** — no implementation | — | NO | DELETE_EMPTY_PACKAGE |
| `shared/infrastructure/env_loader.py` | config, db | YES | none | VALID — env var loader | — | NO | KEEP_IN_SHARED |
| `shared/infrastructure/exception_handlers.py` | app.py | YES | none | VALID — global FastAPI exception handlers | — | NO | KEEP_IN_SHARED |
| `shared/infrastructure/lifespan.py` | app.py | YES | none | VALID — FastAPI lifespan startup | — | NO | KEEP_IN_SHARED |
| `shared/infrastructure/logging/structured_logger.py` | multiple modules | YES | none | VALID — structured logging | — | NO | KEEP_IN_SHARED |
| `shared/infrastructure/request_utils.py` | middlewares, exception_handlers | YES | none | VALID — request ID extraction | — | NO | KEEP_IN_SHARED |
| `shared/middleware/middlewares.py` | app.py | YES | none | VALID — global CORS / correlation ID middleware | — | NO | KEEP_IN_SHARED |
| `shared/models/__init__.py` | **15+ modules including certified core** | PARTIAL | calculator_motor (canonical owner of PricingResult) | **BORDERLINE** — wildcard re-export aggregator; used by engine core, cannot be removed without import changes in certified files; documents canonical owners in its docstring | — | YES (de facto) | KEEP_TEMP_ADAPTER |
| `shared/models/results.py` | **14 modules including certified core** | NO — business-specific | `calculator_motor/models/results.py` | **BORDERLINE** — permanent backward-compat adapter; canonical classes live in `calculator_motor/models/results.py`; removing requires touching certified core imports | `calculator_motor` | YES | DEFER_IMPORT_RISK |
| `shared/ports/__init__.py` | — | YES | none | VALID — package init | — | NO | KEEP_IN_SHARED |
| `shared/ports/logger.py` | infrastructure | YES | none | VALID — `ILogger` Protocol | — | NO | KEEP_IN_SHARED |
| `shared/ports/parametrization_provider.py` | calculator_motor engine, parametrizacion | YES | none | VALID — `IParametrizationProvider` Protocol (cross-cutting) | — | NO | KEEP_IN_SHARED |
| `shared/ports/trace_emitter.py` | engine, lineage | YES | none | VALID — `ITraceEmitter` Protocol | — | NO | KEEP_IN_SHARED |
| `shared/use_cases/__init__.py` | 0 active consumers (pycache from old imports) | YES | none | **EMPTY** — only docstring, dead code | — | NO | DELETE_EMPTY_PACKAGE |
| `shared/versioning/version_registry.py` | calculator/api, parametrizacion/api | YES | none | VALID — cross-cutting version metadata | — | NO | KEEP_IN_SHARED |
| `shared/versioning/registry_provider.py` | calculator/api, parametrizacion/api | YES | none | VALID — singleton wrapper for `VersionRegistry` | — | NO | KEEP_IN_SHARED |

---

## 6. `db/` Compact Inventory

| current_path | short_responsibility | detected_issue | decision |
|---|---|---|---|
| `db/__init__.py` | Package init | None | KEEP_AS_IS |
| `db/config.py` | `DbConfig` dataclass + `load_config()` — reads env vars for provider selection | Contains `ALLOW_COSMOS_NON_PRODUCTION` default=`False` — safe default, correctly documented | KEEP_AS_IS |
| `db/constants/provider_constants.py` | Provider identifiers, env var names, reserved field names | Well-structured; no domain logic | KEEP_AS_IS |
| `db/container.py` | **Dependency injection root** — builds DocumentStore, all repositories, services on startup | Large file (builds 15+ objects); no domain logic leaked | KEEP_AS_IS |
| `db/dependencies.py` | FastAPI `Depends()` factories per repository type | Correctly delegates to `app.state.container` | KEEP_AS_IS |
| `db/exceptions.py` | `DbConfigurationError`, `DbConnectionError`, `DbOperationError` | No duplication with `shared/exceptions.py` (different concern levels) | KEEP_AS_IS |
| `db/factory.py` | `build_provider()` and `build_parametrization_document_store()` | **Module-level cache** (`_cached_provider`) — safe in prod; can serve stale state under hot-reload in tests | KEEP_AS_IS |
| `db/helpers/atomic_json_writer.py` | Atomic JSON file writer (temp + rename) | Correctly in `db/helpers/` — generic technical helper | KEEP_AS_IS |
| `db/models/atomic_write.py` | `AtomicWriteOperation` model | Fine | KEEP_AS_IS |
| `db/models/collection_config.py` | Collection configuration model | Fine | KEEP_AS_IS |
| `db/models/stored_document.py` | `StoredDocument` — document envelope for persistence | Fine | KEEP_AS_IS |
| `db/ports/atomic_document_store.py` | `IAtomicDocumentStore` Protocol | Correctly in ports | KEEP_AS_IS |
| `db/ports/document_store.py` | `DocumentStore` Protocol | Correctly in ports | KEEP_AS_IS |
| `db/providers/cosmos_document_store.py` | Cosmos SDK implementation | Deferred import pattern correct | KEEP_AS_IS |
| `db/providers/json_document_store.py` | JSON filesystem implementation | Correctly isolated | KEEP_AS_IS |

---

## 7. Detailed Table — Problematic / Candidate Files

### 7.1 — Empty packages (DELETE_CANDIDATE)

| current_path | current_responsibility | detected_issue | decision |
|---|---|---|---|
| `modules/cadena_a/payroll/` | Only `__init__.py` with docstring; no `.py` files | Reserved namespace never populated; creates import noise | DELETE_CANDIDATE |
| `modules/cadena_a/staffing/` | `__init__.py` + `calculators.py` only in `__pycache__` (no source) | Source file missing; only compiled artifact exists | DEFER_IMPORT_RISK |
| `modules/shared/helpers/` | Only `__init__.py` with docstring | Empty package; no utility functions here | DELETE_EMPTY_PACKAGE |
| `modules/shared/use_cases/` | Only `__init__.py`; `__pycache__` contains old compiled files from deleted modules | Dead package; old use cases moved to `modules/calculator/use_cases/` and `modules/audit/use_cases/` | DELETE_EMPTY_PACKAGE |
| `modules/pyg/use_cases/` | Only `__pycache__/__init__.cpython-312.pyc` | Source `__init__.py` missing; orphaned cache | DELETE_CANDIDATE |
| `modules/vision_tarifas/builders/` | Only `__pycache__` | Empty directory with no source | DELETE_CANDIDATE |
| `modules/vision_tarifas/services/` | Only `__pycache__` | Empty directory with no source | DELETE_CANDIDATE |
| `modules/parametrizacion/gn/constants/` | Only `__pycache__` | Phantom directory — never populated | DELETE_CANDIDATE |
| `modules/parametrizacion/gn/enums/` | Only `__pycache__` | Phantom directory — never populated | DELETE_CANDIDATE |
| `modules/parametrizacion/gn/helpers/` | Only `__pycache__` | Phantom directory — never populated | DELETE_CANDIDATE |
| `modules/parametrizacion/hr/constants/` | Only `__pycache__` | Phantom directory — never populated | DELETE_CANDIDATE |
| `modules/parametrizacion/hr/enums/` | Only `__pycache__` | Phantom directory — never populated | DELETE_CANDIDATE |
| `modules/parametrizacion/hr/helpers/` | Only `__pycache__` | Phantom directory — never populated | DELETE_CANDIDATE |
| `modules/parametrizacion/op/constants/` | Only `__pycache__` | Phantom directory — never populated | DELETE_CANDIDATE |
| `modules/parametrizacion/op/enums/` | Only `__pycache__` | Phantom directory — never populated | DELETE_CANDIDATE |
| `modules/parametrizacion/op/helpers/` | Only `__pycache__` | Phantom directory — never populated | DELETE_CANDIDATE |

### 7.2 — Deprecated shims / backward-compat adapters

| current_path | current_responsibility | detected_issue | proposed_owner | move_type | risk | certified_core | golden_impact | adapter_required | decision |
|---|---|---|---|---|---|---|---|---|---|
| `modules/shared/config/business_rules_loader.py` | DEPRECATED shim re-exporting from `config/business_rules/loader.py` | No active consumers found; docstring marks it DEPRECATED | none | DELETE | LOW — no active imports | NO | NONE | NO | REMOVE_TEMP_ADAPTER |
| `modules/parametrizacion/api/gn_router.py` | 1-line backward-compat re-export of `gn/api/router.router` | Consumed only by `parametrizacion/api/router.py` which already directly imports `gn/api/router` | none | DELETE | LOW — `api/router.py` already imports directly | NO | NONE | NO | REMOVE_TEMP_ADAPTER |
| `modules/parametrizacion/api/hr_router.py` | Same pattern as above for HR | Same as above | none | DELETE | LOW | NO | NONE | NO | REMOVE_TEMP_ADAPTER |
| `modules/parametrizacion/api/op_router.py` | Same pattern as above for OP | Same as above | none | DELETE | LOW | NO | NONE | NO | REMOVE_TEMP_ADAPTER |
| `modules/shared/models/results.py` | Backward-compat adapter — re-exports all result classes from `calculator_motor/models/results.py` | Classes defined in `calculator_motor` but imported via `shared`; removing requires touching certified core imports | `calculator_motor` | DEFER | HIGH — engine.py and 13+ files import from here | INDIRECT | DIRECT | YES | DEFER_IMPORT_RISK |
| `modules/calculator_motor/shared/__init__.py` | Re-exports `PricingCalculator` from `formulas/pricing` | This `shared/` sub-package inside `calculator_motor` is non-standard; `PricingCalculator` should be imported directly | `calculator_motor/formulas/pricing` | MERGE | LOW — only structural | DIRECT | DIRECT | NO | DEFER_CERTIFIED_CORE |

### 7.3 — Misplaced files (not in forbidden paths)

| current_path | current_responsibility | detected_issue | proposed_owner | proposed_path | move_type | risk | certified_core | golden_impact | adapter_required | decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `modules/calculator/helpers/certified_helpers.py` | Hashing utilities for certified mode: `_hash_request`, `_hash_result`, `_extract_kpis_from_result` | Pure hashing functions placed in `helpers/`; they belong with the certified use case that consumes them | `modules/calculator/use_cases/` | `modules/calculator/use_cases/certified_helpers.py` | RENAME + MOVE | LOW — only one consumer (`certified_calculation.py`) | NO | INDIRECT | YES (temp shim in `helpers/`) | READY_TO_MOVE |

### 7.4 — Naming convention debt

| current_path | current_responsibility | detected_issue | proposed_path | certified_core | golden_impact | decision |
|---|---|---|---|---|---|---|
| `modules/cadena_b/reglas.py` | `CadenaBCalculator` — a calculation service | Filename `reglas.py` implies business rules, not a calculator class. Canonical name should be `calculator.py` or `cadena_b_calculator.py` | `modules/cadena_b/services/cadena_b_calculator.py` | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/cadena_c/reglas.py` | `CadenaCCalculator` — same pattern | Same as above | `modules/cadena_c/services/cadena_c_calculator.py` | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |
| `modules/vision_tarifas/reglas.py` | `VisionTarifasCalculator` — same pattern | `reglas.py` implies rules, not a calculator with 630+ lines of calculation logic | `modules/vision_tarifas/calculator.py` or `services/vision_tarifas_calculator.py` | INDIRECT | DIRECT | DEFER_CERTIFIED_CORE |

### 7.5 — Dual config concern

| current_path | detected_issue | decision |
|---|---|---|
| `modules/shared/config/config.py` | Storage paths + Excel upload security limits + ICA guard | File name `config.py` is generic; content is actually storage layout + upload guardrails. Fine as-is; could eventually be split into `storage_paths.py` + `upload_limits.py` for clarity | KEEP_AS_IS |
| `modules/shared/config/app_settings.py` | Deployment config (env var constants, CORS, host/port, APP_ENV) | Slightly overlaps with `db/config.py` naming but different concern — no action needed | KEEP_AS_IS |

---

## 8. Constants / Enums / Helpers Findings

| finding | location | issue | recommendation |
|---------|----------|-------|---------------|
| Technical constants correctly placed | `db/constants/provider_constants.py`, `modules/calculator_motor/constants/global_constants.py` | None | KEEP_AS_IS |
| Business enum correctly scoped | `modules/cadena_a/enums/cargo_tipo.py` | Module-owned enum, correct placement | KEEP_AS_IS |
| Parametrization enum correctly scoped | `modules/parametrizacion/enums/types.py` | Module-owned, correct | KEEP_AS_IS |
| `shared/helpers/` is EMPTY | `modules/shared/helpers/__init__.py` | No utilities defined; phantom folder | DELETE_EMPTY_PACKAGE |
| `certified_helpers.py` in wrong layer | `modules/calculator/helpers/certified_helpers.py` | Hashing utilities belong with the use case, not a generic helpers folder | Move to `use_cases/` in BLOCK 01 |
| No global `helpers.py` or `utils.py` at module root | all modules | Correct — domain-specific helpers are scoped inside their modules | KEEP_AS_IS |
| Business rules YAML loader correctly scoped | `shared/config/business_rules/loader.py` | Fine; YAML config is shared across cadena_a, calculator_motor | KEEP_IN_SHARED |

---

## 9. Import Risk Findings

| risk | location | description |
|------|----------|-------------|
| MEDIUM | `modules/shared/models/__init__.py` | Wildcard re-export (`from ... import *`) used by 15+ modules including certified core. Removing or restructuring requires coordinated import changes across engine, mixins, serializers, helpers — all certified. Can only be addressed in a dedicated BLOCK 05 after FORMULA_MAP. |
| MEDIUM | `modules/shared/models/results.py` | Backward-compat adapter; canonical classes live in `calculator_motor/models/results.py`. 14 modules import via `shared/models`. Changing requires touching certified core. `DEFER_IMPORT_RISK`. |
| LOW | `modules/cadena_a/staffing/calculators.py` | Only in `__pycache__`, no source file on disk. Some Python process compiled this. Investigate before deleting — may be a stale artifact from a previous move. |
| LOW | `modules/calculator_motor/shared/__init__.py` | Unnecessary sub-package inside certified core; re-exports `PricingCalculator`. Not harmful but adds confusion. `DEFER_CERTIFIED_CORE`. |
| LOW | `modules/parametrizacion/api/{gn,hr,op}_router.py` | Three shims all re-exporting from their respective `*/api/router.py`. The `api/router.py` already imports directly. Shims are unreferenced except by old tests/docs. Safe to remove. |
| LOW | `modules/shared/config/business_rules_loader.py` | DEPRECATED shim with no found active consumers. Safe to remove. |

---

## 10. Delete / Empty Package Candidates

### Confirmed DELETE candidates (no active consumers, no golden impact)

| path | reason | risk |
|------|--------|------|
| `modules/cadena_a/payroll/__init__.py` + folder | Empty namespace with docstring only; no files | LOW |
| `modules/shared/helpers/__init__.py` + folder | Empty package | LOW |
| `modules/shared/use_cases/__init__.py` + folder | Dead package; use cases moved to dedicated modules | LOW |
| `modules/pyg/use_cases/` directory | No source file; only orphaned `.pyc` | LOW |
| `modules/vision_tarifas/builders/` directory | No source file; only orphaned `.pyc` | LOW |
| `modules/vision_tarifas/services/` directory | No source file; only orphaned `.pyc` | LOW |
| `modules/parametrizacion/gn/{constants,enums,helpers}/` | Phantom directories; only `__pycache__` | LOW |
| `modules/parametrizacion/hr/{constants,enums,helpers}/` | Phantom directories; only `__pycache__` | LOW |
| `modules/parametrizacion/op/{constants,enums,helpers}/` | Phantom directories; only `__pycache__` | LOW |
| `modules/shared/config/business_rules_loader.py` | DEPRECATED shim; no active consumers | LOW |
| `modules/parametrizacion/api/gn_router.py` | Unused shim; `api/router.py` imports directly | LOW |
| `modules/parametrizacion/api/hr_router.py` | Same | LOW |
| `modules/parametrizacion/api/op_router.py` | Same | LOW |

### Requires investigation before deleting

| path | reason |
|------|--------|
| `modules/cadena_a/staffing/calculators.py` | Only `.pyc` exists — source may have been moved or lost. Verify import graph before removing `__pycache__`. |

---

## 11. Proposed Implementation Blocks

### BLOCK 01 — Safe organization (low risk, no golden impact)

**Goal:** Remove empty packages, remove confirmed deprecated shims, move misplaced certified-free helper.

**Files / categories:**
- Delete: `modules/cadena_a/payroll/__init__.py` + folder
- Delete: `modules/shared/helpers/` folder
- Delete: `modules/shared/use_cases/__init__.py` + folder
- Delete: `modules/pyg/use_cases/` (no source)
- Delete: `modules/vision_tarifas/builders/` (no source)
- Delete: `modules/vision_tarifas/services/` (no source)
- Delete: phantom `parametrizacion/{gn,hr,op}/{constants,enums,helpers}/` folders (all `__pycache__`-only)
- Remove: `modules/shared/config/business_rules_loader.py` (DEPRECATED shim)
- Remove: `modules/parametrizacion/api/{gn,hr,op}_router.py` (unused shims)
- Move: `modules/calculator/helpers/certified_helpers.py` → `modules/calculator/use_cases/certified_helpers.py`
  - Add 1-line shim at old path with TODO: `REMOVE_AFTER_BLOCK_01_CLEANUP`
  - Update import in `modules/calculator/use_cases/certified_calculation.py`

**Risk:** LOW — no certified core files, no golden impact, no formula changes  
**Tests required:**
- `PYTHONPATH=$(pwd) pytest tests/api/ -q` — must remain 123 PASS
- `PYTHONPATH=$(pwd) pytest tests/golden/ -q` — must remain 99/99 PASS
- `make verify` — must remain PASS

**Must NOT touch:** `calculator_motor/**`, `shared/models/**`, `request/**`, `storage/**`, `tests/golden/fixtures/**`

**Exit criteria:** All phantom directories removed. All deprecated shims removed. `certified_helpers.py` in `use_cases/`. All tests green.

---

### BLOCK 02 — API / module boundaries (medium risk)

**Goal:** Verify and harden API layer conventions. Ensure response models are in correct location. Confirm no business logic in `api/` files.

**Files / categories:**
- Audit: all `*/api/` directories — confirm no business logic leaks
- Audit: `modules/shared/contracts/api_v1/` — confirm all contracts belong here or in module-local `contracts/`
- Review: `modules/calculator/api/calculate_dto.py` — confirm DTO vs contract boundary
- Review: `modules/vision_imprimible/api/response_models.py` — already in correct place

**Risk:** MEDIUM — API contract changes can affect consumers  
**Tests required:** Full API suite + typed contract tests  
**Must NOT touch:** `shared/models/**`, `shared/ports/**`, `calculator_motor/**`  
**Exit criteria:** No business logic in `api/` layers. All API files follow naming conventions.

---

### BLOCK 03 — Services / repositories / validators (medium risk)

**Goal:** Audit and normalize naming for services, use cases, repositories. Identify any business logic in wrong layer.

**Files / categories:**
- Audit: `modules/cadena_b/services/`, `modules/cadena_c/services/`
- Audit: `modules/parametrizacion/repositories/` — confirm repo naming consistency
- Audit: `modules/audit/use_cases/` — confirm use case pattern
- Do NOT touch: `cadena_b/reglas.py`, `cadena_c/reglas.py` (certified core)

**Risk:** MEDIUM — repository changes affect persistence behavior  
**Tests required:** API tests + golden tests  
**Exit criteria:** All services/repos follow naming conventions. No logic misplaced.

---

### BLOCK 04 — `db/` cleanup

**Goal:** Minor cleanup of `db/` layer — no structural changes needed.

**Files / categories:**
- Investigate: `db/factory.py` module-level cache — consider documenting the hot-reload caveat
- Verify: no domain logic has crept into `db/` modules
- Audit: `db/container.py` imports — confirm all are infra-only

**Risk:** LOW — `db/` is already well-structured  
**Tests required:** API health/readiness tests (`pytest tests/api/ -k "health or ready"`)  
**Must NOT touch:** `db/providers/` protocol implementations  
**Exit criteria:** No domain logic in `db/`. Cache caveat documented.

---

### BLOCK 05 — `calculator_motor` audit only (read-only)

**Goal:** Map formula ownership, golden impact, and import surface of `calculator_motor`. No moves.

**Files / categories:**
- Audit: all `modules/calculator_motor/formulas/**`
- Audit: all `modules/calculator_motor/mixins/**`
- Identify: which files are DIRECT vs INDIRECT golden impact
- Map: `shared/models/__init__.py` consumers → understand scope of wildcard import chain
- Document: `cadena_b/reglas.py`, `cadena_c/reglas.py`, `vision_tarifas/reglas.py` naming debt — confirm safe rename path

**Risk:** READ-ONLY — no code changes  
**Tests required:** None (read-only)  
**Exit criteria:** Formula ownership map written. Import graph of `shared/models` documented. Safe rename path for `reglas.py` files confirmed or ruled out.

---

### BLOCK 06 — Formula lineage / FORMULA_MAP

**Goal:** Add structured `@excel_lineage` docstrings to formula functions. Build `FORMULA_MAP` index.

**Files / categories:** `modules/calculator_motor/formulas/**` (after BLOCK 05 audit)

**Risk:** LOW if docstrings only; MEDIUM if any function signatures touched  
**Tests required:** Golden suite must remain 99/99 PASS  
**Exit criteria:** All formula functions have `@excel_lineage` docstring. `FORMULA_MAP.md` generated.

---

### BLOCK 07 — Adapter cleanup

**Goal:** Remove temporary adapters introduced in BLOCK 01. Remove old `__init__.py` redirections. Validate final import graph.

**Files / categories:**
- Remove: `modules/calculator/helpers/__init__.py` if only a shim after BLOCK 01
- Remove: `modules/calculator_motor/shared/__init__.py` if safe (BLOCK 05 must confirm)
- Remove: `modules/shared/models/__init__.py` wildcard export — only after BLOCK 05 maps all consumers and confirms a migration path
- Validate: `from nexa_engine.modules.shared.models import *` → explicit imports

**Risk:** HIGH for `shared/models/__init__.py` — touches certified core import chain; requires careful staging  
**Tests required:** All tests — API 123 PASS, golden 99/99 PASS, `make verify` PASS  
**Must NOT touch without BLOCK 05 map:** `shared/models/__init__.py`, `shared/models/results.py`  
**Exit criteria:** All temporary adapters removed. All imports explicit. No wildcard re-exports in shared. Full test suite green.

---

## 12. Summary Table

| block | scope | risk | tests required | must not touch |
|-------|-------|------|---------------|----------------|
| BLOCK 01 | Empty packages, deprecated shims, certified_helpers move | LOW | API + golden + verify | calculator_motor, shared/models, request, storage, golden fixtures |
| BLOCK 02 | API layer audit and contracts | MEDIUM | API suite + typed contracts | shared/models, shared/ports, calculator_motor |
| BLOCK 03 | Services/repos/validators naming | MEDIUM | API + golden | cadena_b/reglas, cadena_c/reglas, calculator_motor |
| BLOCK 04 | db/ minor cleanup | LOW | health/readiness | db/providers implementations |
| BLOCK 05 | calculator_motor audit (READ-ONLY) | NONE | none | everything — read only |
| BLOCK 06 | Formula docstrings and FORMULA_MAP | LOW–MEDIUM | golden 99/99 | formula logic itself |
| BLOCK 07 | Adapter cleanup + explicit imports | HIGH | full suite | shared/models until BLOCK 05 map is complete |

---

## CHECKPOINT_REQUIRED

```
No code was changed.
No files were moved.
No folders were created.
No files were deleted.
Implementation must not start until this report is reviewed and approved.
```

**Certified state preserved:**
- V2-8: CLOSED
- Engine: CLOSED
- API: CLOSED
- Persistence/traceability: CLOSED
- Backend production smoke: CLOSED
- Local release gate: READY
- Cosmos real smoke: DEFERRED_NO_CREDENTIALS, non-blocking
- All golden tests: 99/99 PASS (unmodified)
- `make verify`: PASS (baseline match, sin drift)
