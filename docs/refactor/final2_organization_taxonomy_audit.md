# FINAL-2 organization and taxonomy audit

Date: 2026-06-05
Branch context: `refactor/modular-pure`
Backend active: `json`

## Baseline

| Check | Result |
| --- | --- |
| `./venv/bin/python -m pytest tests -q --tb=short` | Blocked: current `venv` has no `pytest` |
| `venv_py312_backup_20260604_165827/bin/python -m pytest tests -q --tb=short` | 48 failed, 1655 passed, 46 skipped, 464 deselected, 1 xfailed |
| `venv_py312_backup_20260604_165827/bin/python -m pytest tests/parity -q --tb=short` | 406 passed, 11 skipped, 39 deselected |
| Collection errors | 0 |
| New node IDs | 0 observed versus expected 48-failure baseline |

The 48 failing node IDs were saved during the run at `/private/tmp/backend_nexa_baseline_tests.txt`.

## General inventory

| Module | Status | Issues | Action |
| --- | --- | --- | --- |
| `api/` | OK | Global router composes module/shared routers only. | KEEP |
| `db/` | OK with active worktree changes | Common infrastructure shape is present: config, factory, container, dependencies, exceptions, models, ports, providers. | KEEP |
| `modules/parametrizacion` | OK with documented exceptions | GN/HR/OP are owned submodules; frozen repository is certified read-only; resolver/provider_business_rules fallbacks are documented exceptions. | DOCUMENT_EXCEPTION |
| `modules/calculator` | Improved | `constants.py` and `serializer.py` had root-level implementation while semantic folders existed/are expected. | MOVE + RE-EXPORT_TEMPORARY |
| `modules/cadena_a` | Mixed but stable | `nomina.py` and `no_payroll.py` remain root domain calculators/services; moving them is formula-sensitive. | POSTPONE_ORACLE_SENSITIVE |
| `modules/cadena_b` | Mixed but stable | `reglas.py` remains a root calculator consumed by calculator, PYG and CTS flows. | POSTPONE_ORACLE_SENSITIVE |
| `modules/cadena_c` | Mixed but stable | `reglas.py` remains a root calculator consumed by calculator, PYG and CTS flows. | POSTPONE_ORACLE_SENSITIVE |
| `modules/costos_financieros` | OK | Canonical calculator is under `calculators/`; guardrails prevent root implementation reintroduction. | KEEP |
| `modules/panel` | OK | Router uses `Depends`; deleted `build_panel_parametros` is guarded. | KEEP |
| `modules/pyg` | Mixed but stable | Canonical builder/services exist; legacy `vision_pyg` module still has root files with test coverage and parity risk. | POSTPONE_ORACLE_SENSITIVE |
| `modules/vision_pyg` | Mixed but stable | Root `builder.py`, `costos_totales.py`, `kpis.py`, `reglas.py` remain legacy compatibility/runtime paths. | POSTPONE_ORACLE_SENSITIVE |
| `modules/vision_tarifas` | Mixed but stable | Root `reglas.py` is a large formula file with direct oracle coverage. | POSTPONE_ORACLE_SENSITIVE |
| `modules/vision_imprimible` | OK | Builders/helpers/models/api separation is clear. | KEEP |
| `modules/vision_cost_to_serve` | OK with large file | Service calculator is >500 LOC and formula-sensitive. | POSTPONE_ORACLE_SENSITIVE |
| `modules/shared` | OK with documented exceptions | Shared contracts, precision/profitability, audit/certification, lineage and app infrastructure remain shared or guarded. | DOCUMENT_EXCEPTION |
| `tests/` | OK | Tests are grouped by api, db, parametrizacion, parity, contract, unit, integration. | KEEP |
| `docs/` | OK | Architecture/db/refactor docs exist; this FINAL-2 audit adds traceability for taxonomy decisions. | KEEP |

## File classification and moves

| File | Real type | Previous location | Canonical location | Action |
| --- | --- | --- | --- | --- |
| `modules/calculator/constants.py` | Constants | Root of `calculator` | `modules/calculator/constants/global_constants.py` | MOVE; package `__init__` preserves import path |
| `modules/calculator/serializer.py` | Serializer | Root of `calculator` | `modules/calculator/serializers/pricing_result_serializer.py` | MOVE + shim |

## Files moved

| Origin | Destination | Reason |
| --- | --- | --- |
| `modules/calculator/constants.py` | `modules/calculator/constants/global_constants.py` | Constants belong under `constants/`; production imports now use the canonical path. |
| `modules/calculator/serializer.py` | `modules/calculator/serializers/pricing_result_serializer.py` | JSON response serialization belongs under `serializers/`; production imports now use `calculator.serializers`. |

## Files eliminated

| File | Evidence of no use |
| --- | --- |
| None | No safe orphan deletion was identified in this batch. |

## Exceptions documented

| File | Reason |
| --- | --- |
| `modules/calculator/constants/__init__.py` | Compatibility export for `calculator.constants`; guarded to prevent root `constants.py` returning. |
| `modules/calculator/serializer.py` | Temporary compatibility shim with retirement note; guarded to prevent implementation code returning. |
| `modules/shared/precision.py` | Oracle-blocked; existing guardrail requires it to stay in shared. |
| `modules/shared/profitability/calculators.py` | Oracle-blocked; existing guardrail requires it to stay in shared. |
| `modules/shared/contracts/api_v1/**` | Public wire contract; existing guardrail requires it to stay in shared. |
| `modules/parametrizacion/repositories/frozen_parametrization_repository.py` | Certified frozen snapshots; moving requires a dedicated hash-validation phase. |
| `modules/vision_tarifas/reglas.py` | Large formula/oracle-sensitive file; postpone until dedicated characterization. |
| `modules/cadena_b/reglas.py` | Root calculator with active runtime consumers; postpone until dedicated formula-safe move. |
| `modules/cadena_c/reglas.py` | Root calculator with active runtime consumers; postpone until dedicated formula-safe move. |
| `modules/riesgo/reglas.py` | Root calculator with active runtime/test consumers; postpone until dedicated characterization. |

## Shared ownership check

| Shared file/group | Consumers | Shared legitimate? | Action |
| --- | ---: | --- | --- |
| `shared/contracts/api_v1/**` | API contract tests and response/request adapters | Yes, public contract. | KEEP |
| `shared/precision.py` | Calculation/parity layers | Yes, oracle-sensitive precision primitive. | KEEP |
| `shared/profitability/calculators.py` | Calculator and parity-sensitive flows | Yes, oracle-sensitive shared calculator. | KEEP |
| `shared/audit/*` shims | Legacy import compatibility to `calculator/audit` | Temporary documented shims. | RE-EXPORT_TEMPORARY |
| `shared/helpers/certified_helpers.py` | `shared/use_cases/certified_calculation.py` | Yes, shared certified-mode helper. | KEEP |
| `shared/infrastructure/storage` | 0 allowed runtime consumers; directory absent | No longer legitimate. | DELETE_IF_ORPHAN already complete |

## `db/` review

| Element | Status |
| --- | --- |
| No business logic in `db/` | PASS by inspection; contents are config/container/factory/dependencies/exceptions/models/ports/providers/helpers. |
| No domain repositories in `db/` | PASS; repositories remain under owning modules. |
| Providers not imported from parametrizacion domain | PASS via `test_no_db_providers_import_from_domain_parametrizacion`. |
| `DocumentStore` remains the technical contract | PASS by db ports/factory and parametrizacion guardrails. |
| Cosmos not active by default | PASS by documented `DB_PROVIDER=json` baseline and config tests. |

## Router review

| Rule | Status |
| --- | --- |
| Global root composes routers | PASS: `api/v1/router.py` composes module/shared routers. |
| Routers use `Depends` for repositories/services | PASS for active parametrizacion/panel/results routers inspected. |
| Routers do not call `get_provider()` at module scope | PASS via shared guardrail. |
| Routers do not call `get_parametrization_store()` directly | PASS for inspected active routers and existing architecture tests. |

## Large files

| File | LOC | Risk | Action |
| --- | ---: | --- | --- |
| `tests/parametrizacion/security/test_excel_contracts.py` | 807 | Test-only | KEEP |
| `tests/certification/test_layer3_oracle.py` | 798 | Oracle certification | KEEP |
| `tests/unit/test_certificacion_final_v25.py` | 777 | Oracle/unit certification | KEEP |
| `tests/unit/test_gap_closure_v25.py` | 765 | Oracle/unit certification | KEEP |
| `modules/vision_tarifas/reglas.py` | 596 | HIGH_ORACLE_SENSITIVE | POSTPONE_ORACLE_SENSITIVE |
| `modules/vision_cost_to_serve/services/cost_to_serve_calculator.py` | 533 | HIGH_ORACLE_SENSITIVE | POSTPONE_ORACLE_SENSITIVE |
| `modules/calculator/adapters/entry_data_adapter.py` | 496 | Public input contract | DOCUMENT_EXCEPTION |
| `modules/calculator/serializers/pricing_result_serializer.py` | 493 | Public output contract | DOCUMENT_EXCEPTION |

## Guardrails

| Rule | Status |
| --- | --- |
| `db.providers` not imported directly from parametrizacion domain | PASS |
| Router API files do not call `get_provider()` at module scope | PASS |
| `shared.infrastructure.storage` not recreated/imported | PASS |
| Shared oracle-blocked files not moved | PASS |
| Calculator root taxonomy shims stay shims only | ADDED |
| Upload repositories avoid direct filesystem/json provider | PASS |

## Validation after safe batch

| Check | Result |
| --- | --- |
| `tests/unit/test_architecture_exceptions.py` | 19 passed |
| `tests/unit/test_shared_guardrails.py` | 19 passed |
| `tests/db` | 59 passed, 12 skipped, 14 deselected |
| `tests/parametrizacion/uploads` | 101 passed |
| `tests/unit/test_phase8_contract_enforcement.py tests/integration/test_snapshot_persistence.py` | 36 passed, 1 deselected |
| `tests/parity -q --tb=short` | 406 passed, 11 skipped, 39 deselected |
| `tests -q --tb=short` | 48 failed, 1657 passed, 46 skipped, 464 deselected, 1 xfailed |
| New failing node IDs | 0; final failed node list matches baseline exactly |
