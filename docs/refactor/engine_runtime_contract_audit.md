# Engine Runtime Contract Audit

**Date:** 2026-06-12  
**Auditor:** backend-agent (claude-sonnet-4-6)  
**Branch:** refactor/modular-pure  
**Scope:** Read-only inspection. No code changes, no storage/request/test modifications.

---

> This audit does not reopen V2-8, CTS-001, or CTS-002. V2-8 remains CLOSED / STABLE_FOR_PRODUCTION.

---

## Executive Summary

The NEXA pricing engine is architecturally sound. The Composition Root pattern is correctly applied, IParametrizationProvider is consistently injected, and the HTTP layer has comprehensive error handling for all expected exception types. The engine correctly validates that at least one chain (A/B/C) is active, handles zero-denominator cases, and enforces required fields.

**Key findings (in priority order):**

1. **HIGH — BUG:** `ValidationError` used without import in `user_input_builders_cadena_a.py` line 162. Raises `NameError` at runtime when a critical financial field is malformed. Currently masked by a broad `except` that catches `(KeyError, ValueError)` but the `raise ValidationError(...)` line is inside the `except` block — it will raise `NameError` instead of `ValidationError`.
2. **HIGH — PROTOCOL MISMATCH:** `IParametrizationProvider` declares `tasa_mensual_financiacion` as `@property`, but the implementation defines it as a regular method. All callers use `()` syntax (method calls). The Protocol is incorrect; this silently passes `runtime_checkable` isinstance checks because the attribute is callable in both cases, but the Protocol contract is misleading.
3. **MEDIUM — SILENT DEFAULT CHAIN:** When `get_v27_defaults()` fails or returns `{}`, `margen_b_default`, `margen_c_default`, and `tasa_interes_mensual` silently fall back to hardcoded values (0.30, 0.20, 0.0153). The `except Exception: v27_defaults = {}` swallows provider errors that should surface.
4. **MEDIUM — HARDCODED SALARY FALLBACK:** Volumetria-derived perfiles fallback path uses `ops.get("salario_base_default", 1423000)` — a hardcoded SMMLV-era value. If `salario_base_default` is absent from entry_data and parametrization is not reached, the engine silently uses 1_423_000 COP as salary.
5. **MEDIUM — UNDOCUMENTED TODO (GAP-CADENA-A-FASE4):** `panel.margen` vs `get_margen_minimo(linea)` discrepancy logged as WARNING only. The engine uses `panel.margen` (user input), while Excel derives margen from storage. The divergence is silently tolerated without a guardrail or explicit business decision documented outside of a code comment.
6. **LOW — BROAD SILENT CATCHES:** Several `except Exception: ...` blocks in context builder mixins swallow errors from provider calls (`get_clasificacion_cargos`, `get_complejidad_especialista`, `get_costo_empresa_override`) with empty dict/None fallback. If these provider methods fail due to malformed parametrization, the engine continues with degraded output rather than raising an explicit error.
7. **LOW — ENGINE INVARIANTS NOT COVERED AT ENGINE LEVEL:** Determinism (same input → same output) is tested only at `NominaCargadaService` level (Layer 1). No test exercises `NexaPricingEngine.calcular()` twice with the same input and asserts identical results. Channel isolation, totals-equals-sum-of-components, and zero-volume handling are not tested at engine level.
8. **LOW — MISSING PARAMETRIZATION RAISES CORRECTLY IN PROVIDER:** `ParametrizationError` is correctly raised by all provider/repository methods. The HTTP handler catches it and returns 422. However, no test verifies that a missing/corrupt parametrization causes a 422 (vs silent fallback or 500).

---

## Baseline

| Gate | Result |
|------|--------|
| Golden suite (`tests/golden/`) | 99/99 PASS |
| `make verify` | PASS — no drift |
| `git status` | 26 modified files (pre-existing, all in contracts/docs/tests; no engine regression) |

---

## Phase 1 — Runtime Flow Map

| Stage | File | Responsibility | Detected Risk |
|-------|------|---------------|---------------|
| 1. HTTP input | `modules/calculator/api/calculate_router.py` → `_calculate_normal` | Receives `CalculationRequest`, dispatches to handler | NONE |
| 2. Contract validation | `modules/calculator_motor/validation/contract_validator.py` | Validates entry_data format (entry_data path only) | LOW — legacy `panel_de_control` path skips `ContractValidator` |
| 3. Input normalization | `modules/calculator_motor/input_normalizer.py` + `InputNormalizer` | Normalizes entry_data → internal format, validates required fields, logs defaults | NONE (STRICT mode enforced on entry_data) |
| 4. Input loading | `modules/calculator_motor/adapters/user_input_loader.py` (`UserInputLoader`) | Builds `UserInput` from normalized dict; applies escenarios to perfiles; injects volumes | HIGH — `ValidationError` NameError bug in `_perfil_a` |
| 5. Context building | `modules/calculator_motor/context_builder.py` (`SimulationContextBuilder`) | Combines UserInput + parametrization → `PricingRequest`; resolves salarios, tasas, perfiles | MEDIUM — silent `except Exception` swallowing provider errors |
| 6. Engine execution | `modules/calculator_motor/engine.py` (`NexaPricingEngine.calcular`) | Orchestrates 10-layer pipeline; validates at least 1 chain active | LOW — GAP-CADENA-A-FASE4 unresolved TODO |
| 7. CTS facts | `engine.py:_build_cts_facts` | Pre-computes per-month nomina/no_payroll/cadena_b for CTS | NONE (zero-denominator guard present) |
| 8. VT facts | `engine.py:_build_vt_facts` | Pre-computes per-escenario nomina/no_payroll for VisionTarifas | NONE |
| 9. Visions serialization | `modules/calculator_motor/serializers/pricing_result_serializer.py` | Validates all visions complete; serializes to dict | NONE |
| 10. Persistence | `modules/calculator/persistence/` + `db/container.py` | DocumentStore (JSON or Cosmos) | NONE |

---

## Phase 2 — Runtime Input Contract Audit

| Field | Expected source | Current source | Silent default | Status | Evidence |
|-------|----------------|---------------|---------------|--------|---------|
| `panel.tasa_ica` | User override or OP-ICA by city | Correct: `panel.tasa_ica if not None else self._prov.get_ica(ciudad)` | None — raises if city missing | OK | `context_builder_panel_mixin.py:44` |
| `panel.tasa_gmf` | User override or OP-Config | Correct: `panel.tasa_gmf if not None else self._prov.get_gmf()` | None — raises if missing | OK | `context_builder_panel_mixin.py:45` |
| `panel.tasa_mensual_financ` | User override, then `tasa_interes_mensual`, then OP-Config | Correct priority chain | Fallback to `0.0153` if `get_v27_defaults()` fails | DEFAULT_RISK | `context_builder_panel_mixin.py:50-85` |
| `panel.pct_rotacion` | User override or HR by line | Correct: `panel.pct_rotacion if not None else self._prov.get_pct_rotacion(linea)` | None — raises if missing | OK | `context_builder.py:134-137` |
| `panel.margen_b` | User override or `v27_defaults.margenes.margen_b_default` | Correct priority; fallback if `get_v27_defaults()` fails | `0.30` hardcode if provider fails | DEFAULT_RISK | `context_builder_panel_mixin.py:70` |
| `panel.margen_c` | User override or `v27_defaults.margenes.margen_c_default` | Correct priority; fallback if provider fails | `0.20` hardcode if provider fails | DEFAULT_RISK | `context_builder_panel_mixin.py:75` |
| `salario_base` (perfiles) | User override or `get_salario_rol(rol)` | Correct: `p.salario_base if not None else self._prov.get_salario_rol(p.rol)` | None — raises `ParametrizationError` if rol absent | OK | `context_builder_perfiles_light_mixin.py:104-106` |
| `salario_base` (volumetria fallback) | ops.salario_base_default or `1423000` | `ops.get("salario_base_default", 1423000)` — never reaches parametrization | `1423000` COP (hardcoded) | DEFAULT_RISK | `user_input_loader.py:374,388` |
| `perfil.cadena_b_mensual` | User input or `0.0` | `float(d["cadena_b_mensual"]) if "cadena_b_mensual" in d else 0.0` | `0.0` if absent | OK (documented) | `user_input_builders_cadena_a.py:158` |
| `perfil.vol_cadena_a_mensual` | User input or VolumeResolutionService | Correct priority | `0.0` if absent and no volumetria | OK (documented) | `user_input_loader.py:475-479` |
| `get_clasificacion_cargos` result | Provider lookup | `try: self._prov.get_clasificacion_cargos() except Exception: {}` | `{}` (silently) | SOURCE_MISMATCH | `context_builder_perfiles_light_mixin.py:79-81` |
| `get_complejidad_especialista` result | Provider lookup | `except Exception: {"BAJA": 0.20, "MEDIA": 0.50, "ALTA": 0.50}` | Hardcoded map | SOURCE_MISMATCH | `context_builder_perfiles_soporte_mixin.py:154-158` |
| `ValidationError` in `_perfil_a` | `nexa_engine.modules.shared.exceptions` | Not imported — `NameError` at runtime | — | CONTRACT_GAP (BUG) | `user_input_builders_cadena_a.py:162` |

---

## Phase 3 — Parametrization/Provider Audit

| Parameter | Current provider | Active parametrization | Default fallback | Risk | Evidence |
|-----------|-----------------|----------------------|-----------------|------|---------|
| `tasa_financiacion_mensual` | `ProviderFinOpMixin.tasa_mensual_financiacion()` → `FinancialParametrizationRepository` | OP-Config → raises `ParametrizationError` if missing | None — explicit raise | NONE | `provider_fin_op.py:22-40` |
| `tasa_gmf` | `get_gmf()` → OP-Config | Correct | None — explicit raise | NONE | `provider_fin_op.py` |
| `tasa_ica` | `get_ica(ciudad)` → OP-ICA | Correct | None — explicit raise | NONE | provider |
| `pct_rotacion` | `get_pct_rotacion(linea)` → HR | Correct | None — explicit raise | NONE | provider |
| `pct_ausentismo` | `get_pct_ausentismo(linea)` → HR | Correct | None — explicit raise | NONE | provider |
| `smmlv` | `get_smmlv()` → HR-Salarios | Correct — single source enforced (BUSINESS_RULES_FIX_2) | None — explicit raise | NONE | `engine.py:664-665` |
| `ramp_up` | `get_rampup(linea, mes)` → HR-Campana | Returns `1.0` + WARNING if linea/mes absent | `1.0` WARNING | LOW | `provider_fin_op.py:43-55` |
| `margen_minimo` | `get_margen_minimo(linea)` → HR-Rentabilidad | Used only for WARNING comparison; `panel.margen` (user) is the actual value | Logged, not enforced | MEDIUM (GAP-CADENA-A-FASE4) | `engine.py:535-555` |
| `get_v27_defaults()` | OP-Config `v2_7_defaults` key | Returns `{}` if key absent (backwards compat) + DEBUG log | `{}` → triggers hardcoded fallbacks for margen_b, margen_c, tasa_interes | MEDIUM | `provider_fin_op.py:474-477`, `context_builder_panel_mixin.py:62-85` |
| `polizas` | User override or `get_tasa_polizas_efectiva()` | Correct three-state: None → storage, [] → empty, [...] → user | None — explicit chain | NONE | `context_builder.py:141-156` |
| **Protocol mismatch** | `IParametrizationProvider.tasa_mensual_financiacion` declared as `@property` | Implementation is a regular method | All callers use `()` (method syntax) | HIGH (protocol integrity) | `shared/ports/parametrization_provider.py:68`, `provider_fin_op.py:22` |

---

## Phase 4 — Engine Invariants

| Invariant | Existing test | Risk | Recommended action |
|-----------|--------------|------|-------------------|
| Deterministic output (same input → same output at engine level) | PARTIALLY_COVERED — Layer 1 (NominaCargadaService) tested; NexaPricingEngine not tested end-to-end | UNCOVERED_MEDIUM | Add `test_engine_deterministic_two_runs` in `tests/unit/` |
| No mutation of request (PricingRequest immutable post-construction) | COVERED for NominaCargadaService; not tested for PricingRequest | UNCOVERED_LOW | Inspect PricingRequest model for frozen=True; add mutation guard test |
| Totals = sum of components (PyG: costo_total = payroll_a + no_payroll_a + costo_b + costo_c + financiero) | PARTIALLY_COVERED — `test_layer2_consistency.py` covers nomina components; P&G totals not asserted end-to-end | UNCOVERED_MEDIUM | Add PyG totals consistency test |
| Channel costs sum to total cost | UNCOVERED_LOW | UNCOVERED_LOW | Add assertion in existing golden tests |
| Negative values controlled | COVERED — `models/results.py:200-204` raises `ValidationError` on negative ingreso_bruto, costo_operativo, costos_financieros | COVERED | — |
| Chains A/B/C isolation (engine respects `cadenas_activas`) | COVERED — `test_task3_optional_chains.py`, `test_vision_activation_cases.py` | COVERED | — |
| Missing parametrization raises explicit error | COVERED in provider — raises `ParametrizationError` | PARTIALLY_COVERED — no HTTP integration test asserting 422 for corrupt parametrization | Add integration test |
| Zero transaction volume handling | COVERED — `_denominador_cadena_a_para_facts` guard + CTS `denominador > 0 else 0.0` | COVERED | — |

---

## Phase 5 — Production Error Handling Audit

| Case | Current behavior | Expected behavior | Risk | Recommended action |
|------|-----------------|-------------------|------|-------------------|
| Missing required field (ciudad, fecha_inicio, duracion_meses) | `UserInputLoader._requerir()` raises `KeyError`; handler returns 422 `INPUT_ERROR` | Correct — 422 with field context | NONE | — |
| Invalid type (e.g. non-numeric fte) | Raises `ValueError`; handler returns 422 `INPUT_ERROR` | Correct | NONE | — |
| Malformed critical financial field in perfil (e.g. `cadena_b_mensual: "bad"`) | `except (KeyError, ValueError)` catches → `raise ValidationError(...)` → **NameError** (bug) | Should return 422 `VALIDATION_ERROR` | HIGH | Import `ValidationError` in `user_input_builders_cadena_a.py` |
| Missing/corrupt parametrization (ParametrizationError) | Provider raises `ParametrizationError`; handler returns 422 `PARAMETRIZATION_ERROR` | Correct — explicit 422 with module context | NONE | Add test coverage |
| Zero meses_contrato | `simulation_request_validator.py:77` raises `ValueError` → 422 | Correct | NONE | — |
| No cadenas activas | `engine.py:533` raises `ValueError("TASK_3: Al menos una cadena...")` → 422 | Correct | NONE | — |
| get_v27_defaults() fails (provider exception) | `except Exception: v27_defaults = {}` → silently applies hardcoded fallbacks for margen_b, margen_c, tasa_interes_mensual | Should log ERROR and surface the failure, or raise `ParametrizationError` | MEDIUM | Replace `except Exception: {}` with explicit logging + re-raise or `ParametrizationError` |
| get_clasificacion_cargos() fails (provider exception) | `except Exception: clasificacion_cargos = {}` → CargoClassifier uses empty map → all roles classify as UNKNOWN | Should raise or warn with actionable message | MEDIUM | Log WARNING with role list; do not silently degrade cargo classification |
| Datasets vision build fails (AuditIntegrityError) | `engine.py:707-710` re-raises as `AuditIntegrityError` → handler returns 500 | Correct — mandatory invariant | NONE | — |
| Audit trace export fails (AuditIntegrityError) | `engine.py:716-719` re-raises → 500 | Correct | NONE | — |
| Lineage persistence fails | `engine.py:513` swallows with WARNING log | Correct — best-effort, non-blocking | NONE | — |

---

## Phase 6 — Top 10 Recommended Fixes

| Priority | Area | Risk | Recommended fix | Suggested test | Notes |
|---------|------|------|----------------|---------------|-------|
| 1 | `user_input_builders_cadena_a.py:162` — missing `ValidationError` import | HIGH | Add `from nexa_engine.modules.shared.exceptions import ValidationError` at top of file | `test_perfil_a_malformed_financial_field_returns_validation_error` | Confirmed bug: `NameError` raised instead of `ValidationError`. Minimal fix. |
| 2 | `IParametrizationProvider.tasa_mensual_financiacion` — Protocol declares `@property`, implementation is method | HIGH | Remove `@property` from Protocol interface (or add `@property` to implementation + all callers adapt) | Update contract test to verify `isinstance(provider, IParametrizationProvider)` still passes | All callers use `()` syntax — removing `@property` from the Protocol is the minimal fix. |
| 3 | `context_builder_panel_mixin.py:62-64` — `except Exception: v27_defaults = {}` | MEDIUM | Replace with `except ParametrizationError as e: logger.error(...); raise` or at minimum `logger.error(...)` before `v27_defaults = {}` | `test_engine_surfaces_v27_defaults_error` | Silently swallowing this allows engine to run with wrong margen_b/margen_c/tasa_interes without operator awareness. |
| 4 | `user_input_loader.py:374,388` — hardcoded `1423000` salary in volumetria-derived perfiles fallback | MEDIUM | Replace with `self._prov.get_salario_rol("Agente Basico")` or require `salario_base_default` in `datos_operativos` | `test_volumetria_fallback_salary_requires_parametrization` | Only affects the backward-compat volumetria path (no `condiciones_cadena_a` in payload). |
| 5 | `context_builder_perfiles_soporte_mixin.py:153-158` — `except Exception: complejidad_map = hardcoded` | MEDIUM | Log ERROR + re-raise `ParametrizationError` when `get_complejidad_especialista()` fails | `test_missing_complejidad_especialista_raises_not_silences` | Silently using hardcoded complexity map defeats the parametrization-first architecture. |
| 6 | Missing engine-level determinism test | MEDIUM | Add `test_engine_deterministic_two_runs`: call `engine.calcular(solicitud)` twice with same `PricingRequest`; assert `result1 == result2` | New test in `tests/unit/test_engine_invariants.py` | Guards against mutable state bugs in calculators or context. |
| 7 | Missing HTTP integration test for `ParametrizationError` → 422 | LOW | Add test that injects a broken provider and POSTs to `/api/v1/simulation/calculate`; asserts 422 + `PARAMETRIZATION_ERROR` code | New test in `tests/api/` | Validates the full error chain from provider to response. |
| 8 | GAP-CADENA-A-FASE4 — `panel.margen` vs `get_margen_minimo(linea)` unresolved | LOW | Escalate to business-rules-agent for decision: should `margen` come from user input or parametrization? Document decision in `DECISIONS.md`. | Parity test if decision changes source | Currently logged as WARNING only. No production risk unless the deal's margin input is systematically wrong. |
| 9 | `context_builder_perfiles_light_mixin.py:79-81` — `except Exception: clasificacion_cargos = {}` | LOW | Log WARNING with affected role list; continue with empty map (current behavior acceptable) but make it visible | Add assertion in any golden test that `cargo_tipo` is never empty string | Cargo classification failure silently produces `UNKNOWN` cargo_tipo; not a financial calculation issue. |
| 10 | PyG totals consistency test (sum of components) | LOW | Add test asserting `pyg_mes.costo_total == payroll_a + no_payroll_a + costo_b + costo_c + costos_financieros` for each month | New test in `tests/unit/test_engine_invariants.py` | Guards against future calculation refactoring that silently breaks totals. |

---

## What Not to Touch

- **CTS-001, CTS-002, V2-8** — CLOSED / STABLE. Do not reopen.
- **Golden fixtures** (`tests/golden/`) — All 99/99 PASS. No changes needed.
- **Baseline** (`storage/baselines/official.json`) — No functional changes; do not run `make baseline`.
- **request/request.json** — Pre-aligned with V2-8 closure. No changes needed.
- **Business rules / parity formulas** — Outside scope of this audit.
- **`modules/vision_imprimible/`, `modules/vision_tarifas/`, `modules/pyg/`** — Calculation correct per V2-8. No changes needed.

---

## Contract Risks Summary

| Risk | Count | Severity |
|------|-------|---------|
| BUG (NameError masking ValidationError) | 1 | HIGH |
| Protocol mismatch (property vs method) | 1 | HIGH |
| Silent provider error swallowing | 3 | MEDIUM |
| Hardcoded salary fallback in volumetria path | 1 | MEDIUM |
| Unresolved TODO with business impact | 1 | MEDIUM |
| Missing engine-level invariant tests | 4 | LOW |
| Missing HTTP integration error tests | 1 | LOW |

---

## Provider/Parametrization Risks Summary

- All provider methods raise `ParametrizationError` explicitly when data is missing — no silent defaults in the provider layer itself.
- The `tasa_mensual_financiacion` Protocol/implementation mismatch does not cause runtime failures (all callers use `()`) but creates a misleading Protocol contract.
- `get_v27_defaults()` returns `{}` (not `ParametrizationError`) for backwards compat with pre-V2-7 parametrizations. This is intentional but creates a risk window where callers silently use hardcoded fallbacks.

