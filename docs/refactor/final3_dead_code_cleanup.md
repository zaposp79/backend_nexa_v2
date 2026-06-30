# FINAL-3 dead code cleanup

Date: 2026-06-05
Branch context: `refactor/modular-pure`
Backend active: `json`

## Baseline

| Check | Result |
| --- | --- |
| `git status --short` | Dirty before this phase; existing DB/Cosmos, FINAL-2 calculator taxonomy, pytest and parametrizacion upload changes were already present. |
| `git diff --stat` | Recorded before cleanup; this phase avoided unrelated DB/Cosmos changes. |
| `venv_py312_backup_20260604_165827/bin/python -m pytest tests -q --tb=short` | 48 failed, 1657 passed, 46 skipped, 464 deselected, 1 xfailed |
| `venv_py312_backup_20260604_165827/bin/python -m pytest tests/parity -q --tb=short` | 406 passed, 11 skipped, 39 deselected |
| Collection errors | 0 |
| New node IDs | 0 at baseline |

`ruff`, `pyflakes`, `autoflake` and `vulture` were not available in the local backup runtime, so unused-import cleanup used compile checks plus manual/AST evidence.

## Inventory

| Category | Candidates | Executed | Postponed |
| --- | ---: | ---: | ---: |
| Empty / marker-only packages | 14 | 14 | 0 |
| Orphan Python files | 0 safe | 0 | several legacy/oracle-sensitive modules |
| Unused imports / variables | 1 safe | 1 | broad AST-only findings with annotation ambiguity |
| Constants / enums | 6 empty marker packages | 6 marker packages removed | real constants/enums kept |
| Shims | 8 reviewed | 0 deleted | 8 kept for compatibility or test consumers |
| Stale docstrings | 2 | 2 | historical docs kept |
| Guardrails | 1 candidate | 1 added | 0 |

## Eliminated

| Element | Evidence of no use |
| --- | --- |
| `modules/parametrizacion/gn/constants/__init__.py` | Only package marker; exact import search for `parametrizacion.gn.constants` returned 0 real consumers. |
| `modules/parametrizacion/gn/enums/__init__.py` | Only package marker; exact import search for `parametrizacion.gn.enums` returned 0 real consumers. |
| `modules/parametrizacion/gn/helpers/__init__.py` | Only package marker; exact import search returned only its own docstring. |
| `modules/parametrizacion/hr/constants/__init__.py` | Only package marker; exact import search for `parametrizacion.hr.constants` returned 0 real consumers. |
| `modules/parametrizacion/hr/enums/__init__.py` | Only package marker; exact import search for `parametrizacion.hr.enums` returned 0 real consumers. |
| `modules/parametrizacion/hr/helpers/__init__.py` | Only package marker; exact import search returned only its own docstring. |
| `modules/parametrizacion/op/constants/__init__.py` | Only package marker; exact import search for `parametrizacion.op.constants` returned 0 real consumers. |
| `modules/parametrizacion/op/enums/__init__.py` | Only package marker; exact import search for `parametrizacion.op.enums` returned 0 real consumers. |
| `modules/parametrizacion/op/helpers/__init__.py` | Only package marker; exact import search returned only its own docstring. |
| `modules/pyg/use_cases/__init__.py` | Only package marker; exact import search returned only its own docstring. |
| `modules/shared/services/__init__.py` | Only package marker; exact import search returned only historical docs and its own docstring; no code imports. |
| `modules/shared/validation/__init__.py` | Only package marker; exact import search returned only historical docs and its own docstring; no code imports. |
| `modules/vision_tarifas/builders/__init__.py` | Only package marker; exact import search returned only its own docstring. |
| `modules/vision_tarifas/services/__init__.py` | Only package marker; exact import search returned only its own docstring. |
| top-level `datetime, timezone` import in `modules/calculator/serializers/serializer_helpers.py` | `datetime` is imported locally where needed; top-level `timezone` had no references. |

## Moved

| Origin | Destination | Reason |
| --- | --- | --- |
| None in FINAL-3 | N/A | This phase was cleanup only; no new moves were made. |

## Conserved

| Element | Reason |
| --- | --- |
| `modules/calculator/serializer.py` | Legacy path still has test consumers and possible external consumers; kept as compatibility shim. |
| `modules/parametrizacion/api/{gn,hr,op}_router.py` | Documented re-export shims for legacy API imports. |
| `modules/shared/audit/{trace_integration,traceability_registry,traceability_writer}.py` | Backward-compatibility shims guarded as re-exports. |
| `modules/shared/ports/parametrization_provider.py` | Test and production consumers still import the public port from this path. |
| `modules/shared/contracts/api_v1/**` | Public wire contract. |
| `modules/shared/precision.py` and `modules/shared/profitability/calculators.py` | Oracle-sensitive shared files. |
| Historical docs mentioning `BaseRepository`, `shared.infrastructure.storage`, `upload/` | Kept as migration history or guardrail documentation. |

## Posponed

| Element | Reason |
| --- | --- |
| Root formula modules such as `vision_tarifas/reglas.py`, `cadena_b/reglas.py`, `cadena_c/reglas.py`, `riesgo/reglas.py` | Oracle-sensitive and actively consumed. |
| Broad AST unused-import candidates | The local analysis cannot reliably distinguish annotation-only imports, public API reexports, side effects and dynamic references. |
| Test imports that appear unused | Many test files use fixture discovery, monkeypatch paths, contract imports, or documentation intent; not safe without pyflakes/ruff and focused characterization. |
| Physical directories containing only `__pycache__` after marker deletion | `rm -rf` cleanup was blocked by local safety policy; no tracked files remain in those packages. |

## Documentation updates

| File | Change |
| --- | --- |
| `modules/calculator/serializers/serializer_helpers.py` | Updated stale module path in docstring. |
| `modules/calculator/audit/trace_integration.py` | Updated usage example to canonical calculator audit import path. |

## Guardrails

| Rule | Status |
| --- | --- |
| Empty taxonomy package markers must not return without real content | ADDED in `tests/unit/test_architecture_exceptions.py`. |
| `build_panel_parametros` must not reappear | Existing guardrail retained. |
| `BaseRepository` must not reappear in shared | Existing guardrail retained. |
| `shared.infrastructure.storage` must not be recreated/imported | Existing guardrail retained. |
| Calculator taxonomy shims must stay shims | Existing FINAL-2 guardrail retained. |

## Validation

| Check | Result |
| --- | --- |
| `tests/unit/test_architecture_exceptions.py` | 20 passed |
| `tests/unit/test_shared_guardrails.py` | 19 passed |
| `tests/db` | 59 passed, 12 skipped, 14 deselected |
| `tests/parametrizacion/uploads` | 101 passed |
| `compileall modules db api tests` | PASS |
| `tests/parity -q --tb=short` | 406 passed, 11 skipped, 39 deselected |
| `tests -q --tb=short` | 48 failed, 1658 passed, 46 skipped, 464 deselected, 1 xfailed |
| New failing node IDs | 0; final failed node list matches FINAL-3 baseline exactly |

## Recommendation

`READY_FOR_FINAL_COMMIT`: final Gate keeps the same 48 failing node IDs and Oracle remains `Delta = 0`.
