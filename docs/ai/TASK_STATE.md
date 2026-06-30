# Task State

## MODULE_STRUCTURE_BLOCK_09 — COMPLETED (2026-06-14)

**Status: ✅ DOCS CLEANUP AND INDEX CREATED**

| Item | Status |
|------|--------|
| docs/refactor/README.md | ✅ Created — canonical navigation index |
| BLOCK 08 naming polish | ✅ CLOSED as no-op — helpers are domain vocabulary, no renames |
| BLOCK 09 docs cleanup | ✅ COMPLETED — README.md index, TASK_STATE updated |
| Canonical docs | All preserved |
| Deleted docs | None — cleanup deferred to archive/ pass per owner approval |
| Certified gates | lineage 11/11, contracts 55/55, API 123/123, golden 99/99, verify ✅ |

**Navigation:** [`docs/refactor/README.md`](../../docs/refactor/README.md)

**Next:** BLOCK 06 (formula lineage annotations) is the highest-value next block. Needs Excel mapping. Push branch when owner approves.

---

## FINAL_NO_COSMOS_RELEASE_GATE — COMPLETED (2026-06-13)

**Status: ✅ LOCAL RELEASE GATE PASSED WITHOUT REAL COSMOS CREDENTIALS**

| Gate | Result |
|------|--------|
| API tests | 123/123 PASS ✅ |
| Golden tests | 99/99 PASS ✅ |
| make verify | PASS (baseline match, sin drift) ✅ |
| Health/readiness tests | 11/11 PASS ✅ |
| Functional changes | 0 ✅ |
| Cosmos real credentials | NOT SET (deferred) |
| Cosmos integration blocker | NO |

**Status:** `COSMOS_REAL_INTEGRATION_SMOKE` is deferred because `COSMOS_ENDPOINT`/`COSMOS_KEY` environment variables are unavailable locally. This is **not a blocker** for the local release gate. All local validations (API, golden, baseline verify, health/readiness) pass without Cosmos.

**Recommendation:** Run the real Cosmos smoke test later in staging when `COSMOS_ENDPOINT` and `COSMOS_KEY` are configured with real Azure credentials. No code changes required — the local gate is complete and production-ready for JSON persistence (`DB_PROVIDER=json`).

---

## ENGINE_RUNTIME_CONTRACT_AUDIT — COMPLETED (2026-06-12)

**Status: ✅ AUDIT COMPLETE. Read-only. No code changes.**

| Gate | Result |
|------|--------|
| Golden suite | 99/99 PASS ✅ |
| make verify | PASS ✅ |
| Functional changes | 0 ✅ |
| Audit doc | `docs/refactor/engine_runtime_contract_audit.md` ✅ |

**Top findings:**
1. HIGH — `ValidationError` NameError bug in `user_input_builders_cadena_a.py:162` (missing import)
2. HIGH — Protocol mismatch: `IParametrizationProvider.tasa_mensual_financiacion` declared as `@property`, implemented as method
3. MEDIUM — `except Exception: v27_defaults = {}` silently swallows provider failures → hardcoded fallbacks
4. MEDIUM — Hardcoded `1423000` salary in volumetria fallback path
5. MEDIUM — GAP-CADENA-A-FASE4 unresolved TODO (margen source: user input vs parametrization)

**Next step:** Open dedicated fix session for items 1-2 (HIGH). Items 3-5 require business confirmation before touching.

---

## V2-8 ARCHIVED — STABLE FOR PRODUCTION (2026-06-12)

**Status: ✅ COMPLETE. Do not reopen V2-8 unless production regression detected.**

| Status | Value |
|--------|-------|
| Golden suite | 99/99 PASS ✅ |
| Baseline | make verify PASS ✅ |
| Excel gate | validate-excel-v28 PASS 6/6 ✅ |
| CTS-001 | CLOSED_ACCEPTED_DELTA (-0.099%) ✅ |
| CTS-002 | FORMALLY_CLOSED (exact K34) ✅ |
| Active blockers | 0 ✅ |
| Functional changes | 0 (documentation only) ✅ |
| Archive docs | `v28_archive_index.md` ✅ |

**Next phase must be tracked separately. Optional items (exact-parity residuals, P&G generalization) are NOT V2-8 work.**

---

## ROLES_OP_STAFFCONFIG_STATUS_RECONCILIATION — COMPLETED (2026-06-12)

Golden: **99/99 PASS** | `make verify` ✅ | `validate-excel-v28` PASS 6/6 ✅ | `test_support_fte_v28.py` 12/12 PASS ✅ | **Functional changes: 0.**

**Result: `CLOSED` for V2-8**

| Implementation | Status | Evidence |
|---|---|---|
| `roles_excluidos_deal` DTO field | ✅ IMPLEMENTED | `PerfilCadenaAInput.roles_excluidos_deal: frozenset` (default_factory) |
| Request reading of `roles_operativos[].incluye_en_deal` | ✅ IMPLEMENTED | Builder: `frozenset(str(r.get("rol")) for r in roles_operativos if not r.get("incluye_en_deal", True))` |
| Light mixin aggregation | ✅ IMPLEMENTED | Light mixin: `frozenset().union(*(getattr(p, "roles_excluidos_deal", frozenset()) ...))` |
| Support mixin exclusion | ✅ IMPLEMENTED | Support mixin: applies to staff_excluidos_extra union → excluded roles do not participate in support FTE |
| JCR / AFAC / GTR exclusion | ✅ VERIFIED | request.json has `incluye_en_deal: false`; support FTE test confirms exclusion; CTS-001 result validates final calculation |
| Director de Performance override (legacy + per-channel) | ✅ IMPLEMENTED & VERIFIED | request.json: `{"Supervisor": 9.5}` (legacy); `{"Director de Performance": {"WhatsApp": 1.0}}` (per-channel); mixin applies both formats; CTS-001 = 6,218.424663 confirms correctness |
| No hardcoding | ✅ VERIFIED | Role names sourced from request.json; module code uses normalized names without literals |

**ROLES-OP-STAFFCONFIG is CLOSED.** All V2-8 requirements met. Optional future generalization to P&G / Tarifas deferred to next phase (not blocking).

Full reconciliation doc: `docs/refactor/roles_op_staffconfig_status_reconciliation.md`

---

## INPUT_PCT_ACUM_AUDIT_POST_V28_CLOSURE — COMPLETED (2026-06-12)

Golden: **99/99 PASS** | `make verify` ✅ | `validate-excel-v28` PASS 6/6 ✅ | **Functional changes: 0.**

**Result: `NO_IMPACT / RECOMMEND_NO_ACTION`**

| Source | Finding |
|--------|---------|
| `request/request.json` `reglas_negocio.porcentaje_acumulado.actual` | `0` — already pre-aligned with Excel |
| `Panel de Control General!C75` (Excel V2-8) | `0` — formula `=SUM(C67:C69)-C70`; all inputs = 0 for this deal |
| Downstream refs in Excel | **0** — exhaustive sheet search confirms Panel!C75 is display-only; not referenced by any other sheet |
| Engine consumption | **DEAD_FIELD_LEGACY** — removed in BUSINESS_RULES_FIX_3 (`engine_helpers.py:70`); `ValueError` guard active if re-added to politicas_comerciales |
| `PanelDeControl` / `ReglasNegocio` models | Field absent — silently dropped at DTO ingestion |
| Impact P&G / Vision Tarifas / CTS | **0 each** — field not read by any computation path |

**Note on `Vision Tarifas` C75 refs:** The `C75` references found in `Vision Tarifas_Modelo_Cobro`
(formulas `=(C75*D34)` and `=C75*D35`) are that sheet's own `C75` cell ("Facturación Total Mensual"),
**not** a cross-reference to `Panel de Control General!C75`. Confirmed by direct sheet inspection.

**Audit doc:** `docs/refactor/input_pct_acum_audit_post_v28_closure.md`

**`INPUT-PCT-ACUM` backlog item: CLOSED. No further action required.**

---

## V28_FINAL_CLOSURE_STATUS_AUDIT — COMPLETED (2026-06-12)

**V2-8 phase formally closed as stable for production use.**

| Gate | Status | Evidence |
|------|--------|----------|
| **Golden suite** | 99/99 PASS ✅ | Full deterministic run before closure |
| **make verify** | ✅ PASS | Baseline match. Sin drift. |
| **validate-excel-v28** | PASS 6/6 ✅ | All 6 checks pass (1 HME cache skipped) |
| **CTS-001** | CLOSED_ACCEPTED_DELTA | -6.150 COP/tx (-0.099%) ≤ 0.5% gate |
| **CTS-002** | FORMALLY_CLOSED | K34 = 5,278.326744 EXACT MATCH |
| **Active V2-8 blockers** | 0 | All resolved or classified |
| **Functional code changes** | 0 | Documentation audit only |
| **Runtime files modified** | 0 | Scope: docs only |
| **Contracts/storage/request** | 0 | No breaking changes |
| **Baseline regeneration** | Not run | Unnecessary (reproducibility confirmed) |

**Final closure document:** `docs/refactor/v28_final_closure_status.md`

**Remaining optional work:**
- ROLES-OP-STAFFCONFIG + Director de Performance -79.46 fix (audited, pending; not blocking V2-8)
- Exact-parity residuals (training/fixed-cost -6.6, SENA/Inclusión) if escalated by business
- INPUT-PCT-ACUM impact audit (P&G/Tarifas, low priority)

**Recommendation:** Proceed to project closure or next major initiative. V2-8 is stable and suitable for production.

---

## CTS_001_FORMAL_CLOSE_ACCEPTED_DELTA — COMPLETED (2026-06-12)

Golden suite: **99/99 PASS** ✅ | `make verify` ✅ | `validate-excel-v28` PASS 6/6 ✅

**CTS-001 formally closed as ACCEPTED_DELTA.**

| Metric | Before support FTE fix | After support FTE fix (5802a81) |
|--------|------------------------|--------------------------------|
| Excel C34 | 6,224.575126 COP/tx | 6,224.575126 COP/tx |
| Backend | 6,204.197492 COP/tx | **6,218.424663 COP/tx** |
| Delta COP/tx | -20.378 | **-6.150** |
| Delta % | -0.327% | **-0.099%** |
| Gate | 0.5% | **✅ PASS (0.099%)** |
| Status | PAUSED_KNOWN_DELTA | **✅ CLOSED_ACCEPTED_DELTA** |

**Functional changes in commit 5802a81:**
1. `fte_soporte_overrides` supports legacy `{role: fte}` format.
2. `fte_soporte_overrides` supports per-channel `{role: {channel: fte}}` format.
3. Director de Performance / WhatsApp = 1.0 wired from request.json (CCA!G78 literal).
4. `roles_operativos[].incluye_en_deal=False` excludes JCR / AFAC / GTR (CCA!C79/C80/C87=False).
5. No hardcoding in modules/. No storage/parametrization touched.

**Functional changes in this (closure) session:** 0 — docs only.

**Residual -6.150 COP/tx decomposition (ACCEPTED):**
- Training/Exam/Crucero: ~-3.85 COP/tx → KNOWN_DELTA_TRAINING
- Costos_fijos_estacion: ~-3.17 COP/tx → KNOWN_DELTA_COSTOS_FIJOS
- SENA/Inclusión ramp snapshot: minor residual → ACCEPTED_DELTA

**Validation (final):**
- golden suite: 99/99 PASS ✅
- make verify: ✅ Baseline match. Sin drift.
- validate-excel-v28: PASS 6/6 ✅
- support_fte: 12/12 PASS ✅
- PyG: 7/7 PASS ✅

**CTS-001 is no longer an active blocker.**  
**No further action required for V2-8 parity gates.**  
Next work should move to the next V2-8 formula/backlog item or final project closure.

---

## V2-8 · CTS_001_INCLUDED_ROLES_SALARY_DEFICIT_AUDIT — COMPLETED (2026-06-12)

Golden **96/96 PASS** | `make verify` | `validate-excel-v28` PASS 6/6. **Functional changes: 0 (docs only).**

**Target:** the **-79.46 COP/tx underlying deficit** in correctly-included roles (excl. JCR/AFAC/GTR).

**Root cause PROVEN (resolves prior `MAPPING_AMBIGUOUS`):**

| Driver | COP/tx | Classification |
|--------|--------|----------------|
| `Director de Performance` channel FTE: `CCA!G78` = hardcoded literal `1.0` (vs ratio formula E78/F78); backend derives ≈0.073 → FTE 1.16 vs 0.233 × 18,902,979 | **+79.26 (99.75% of −79.46)** | **EXCEL_QUIRK** (per-role channel literal, same class as `E95=9.5`) |
| SENA / Inclusión ramp snapshot (salaries + factors match) | ≈ −6.6 | ACCEPTED_DELTA |
| Agent salary | 0 (Nomina Loaded 925,853,204 = backend EXACT) | MATCH |

**Disproven:** prior session's "agent salary / SENA formula" hypothesis. The deficit is a single
literal channel override in the CCA FTE grid.

**Recommended fix (not implemented):** generalize `fte_soporte_overrides` to **per-channel** literals
(carry G78 Director Performance WhatsApp=1.0 alongside E95 Supervisor=9.5); apply **together** with
`ROLES-OP-STAFFCONFIG` (exclude JCR/AFAC/GTR) — fixing either alone regresses CTS-001.

**Full RCA:** `docs/refactor/cts_001_included_roles_salary_deficit_audit.md`

---

## V2-8 · CTS_001_SUPPORT_LOADED_SALARY_AUDIT — COMPLETED (2026-06-12)

Golden suite: **96/96 PASS** ✅ | `make verify` ✅ | `validate-excel-v28` PASS 6/6 ✅

**Investigation target:** `CTS_SUPPORT_LOADED_MAGNITUDE` = -13.37 COP/tx (nomina_loaded component)

**Root causes identified (proven):**

| Root cause | Impact | Classification |
|-----------|--------|----------------|
| `ROLES-OP-STAFFCONFIG`: JCR/AFAC/GTR included in backend (FTE > 0) but excluded in Excel (`C79/C80/C87=False`) | +66.09 COP/tx over-count | `BACKEND_NOT_CONSUMING_FIELD` |
| JCR `detalles_recursos_humanos` bypasses `costo_empresa_override` via `usa_detalle=True` → formula gives 12,172,533 vs W=7,648,436 | +7.14 COP/tx within JCR over-count | `REQUEST_VALUE_GAP` |
| Underlying deficit in correctly-included roles (agent salary / SENA / Inclusion?) | -79.46 COP/tx | `MAPPING_AMBIGUOUS` (not proven) |
| **Net** | **-13.37 COP/tx** | |

**Key insight:** The 3 excluded roles partially compensate a larger underlying deficit (+66.09 offsets -79.46). Fixing `ROLES-OP-STAFFCONFIG` alone would WORSEN the gap to ≈ -79.46 COP/tx. Both causes must be addressed simultaneously.

**Override mechanism confirmed working:** All 20 `costo_empresa_override` lookups via `get_costo_empresa_override()` return EXACT W-column values. The bypass is 100% due to `usa_detalle=True` path in `valores_recurso_humano()`.

**Functional changes:** 0. Docs only.

**Full audit:** `docs/refactor/cts_001_support_loaded_salary_audit.md`

**Decision:** `RECOMMEND_DEEPER_RCA` — characterize underlying -79.46 COP/tx before implementing any fix.

**Next action:** Audit agent salary (CCA!E/F/G columns per channel × salary per FTE) + SENA/Inclusion formula vs Excel. Requires `business-rules-agent` + opus.

---

## V2-8 · CTS_001_RESUME_FROM_CLEAN_BASELINE — COMPLETED (2026-06-12)

Golden suite: **96/96 PASS** ✅ | `make verify` ✅ | `validate-excel-v28` PASS 6/6 ✅

**Fresh measurement (post E95=9.5 + all V28 fixes):**
- Excel C34: 6,224.575126 COP/tx
- Backend: 6,204.197492 COP/tx
- Delta: **-20.378 COP/tx (-0.327%)** — improved from prior -27.53 (-0.44%)
- Gate 3%: ✅ WITHIN

**Component decomposition:**

| Component | Delta COP/tx | Classification |
|-----------|-------------|----------------|
| Salary loaded (nomina_loaded) | -13.37 | CTS_SUPPORT_LOADED_MAGNITUDE |
| Training / Exam / Crucero | -3.85 | KNOWN_DELTA_STRUCTURAL |
| Costos fijos estación | -3.17 | KNOWN_DELTA_COSTOS_FIJOS |
| OPEX fijo | 0.00 | ✅ MATCH |
| CAPEX / Inversiones C47 | +0.004 | ✅ MATCH |
| E95 Supervisor FTE | MATCH (9.5) | ✅ MATCH |
| Denominator 221,000 tx/mes | MATCH | ✅ MATCH |

**Decision:** Maintain `PAUSED_KNOWN_DELTA`. Residual at 0.33% is within gate and below practical tolerance.

**Functional changes:** 0. Docs only.

**Full RCA:** `docs/refactor/cts_001_resume_from_clean_baseline.md`

**Recommended next action:** If further CTS-001 closure is desired, audit aggregate salary loaded by role (CCA rows vs provider W overrides, per-role FTE × costo_empresa_override). Requires `business-rules-agent` + opus + Excel CCA sheet.

---

## V2-8 · V27_FIXTURE_REGEN_CONTROLLED — COMPLETED (2026-06-12)

Golden suite: **0 fail / 96 pass** ✅ (was 24 fail / 72 pass)

**Classification resolved:** 24 × `PREEXISTING_INFRA_PARAMETRIZATION` / `V27_FIXTURE_DRIFT`
- 13 × `V27_CTS_FIXTURE_DRIFT` — `test_cost_to_serve_golden_v27.py` (TestV27Aggregate + TestV27PerCanal)
- 11 × `V27_VT_FIXTURE_DRIFT` — `test_vision_tarifas_golden_v27.py` (TestV27TwoChannels)

**Root cause:** Active OP `tasa_financiacion` 0.0088→0.0153 (commit `939a36a`) raised financial costs ~2%, propagating via cost-plus to CTS and VisionTarifas metrics. V27 frozen fixture values predated the OP update.

**Fixtures updated (controlled — only failing fields):**
- `tests/golden/fixtures/cts_v27_real_request.json` — 13 fields: cts_cadena_a, cts_ponderado, desglose_a.nomina_loaded, canales_detalle Voz/WhatsApp (cts, payroll, nomina_loaded, no_payroll, salario_fijo)
- `tests/golden/fixtures/vt_v27_real_request.json` — 11 fields: per-canal tarifa_fijo_fte/ingreso_bruto/costo_atribuible/payroll_ch/no_payroll_ch (×2 canals) + costo_cadena_a_total

**Validation:**
- `tests/golden/` → **96 passed** ✅
- `validate-excel-v28` → **PASS 6/6** ✅ (no regression)
- `test_pyg_v28_ingreso_indexado.py` → **7/7 PASS** ✅
- `test_support_fte_v28.py` → **9/9 PASS** ✅
- `make verify` → **✅ Baseline match. Sin drift.**

**Scope:** modules=0, request=0, storage=0, contracts=0. Only `tests/golden/fixtures/` (2 files). No `make baseline` needed.

**Next step:** V2-8 parity resumption — CTS-001 residual (-27.53 COP/tx, PAUSED_KNOWN_DELTA), or ROLES-OP-STAFFCONFIG gap.

---

## V2-8 · E95_WIP_RESTORE_AND_COMMIT — COMPLETED (2026-06-12)

Golden suite: **24 fail / 72 pass** ✅ (was 25 fail / 71 pass → 27 fail / 69 pass cascade → 24/72 after PyG anchor update).

**Fix applied:**
- `request/request.json` — added `"fte_soporte_overrides": {"Supervisor": 9.5}` to SAC Actual profile (Excel CCA!E95 literal manual override). Supervisor FTE 7.1 → 9.5 (+2.4).
- `tests/golden/test_pyg_v28_ingreso_indexado.py` — PyG anchor update (M1/M7/M19 ingreso_a + ingreso_total); ingreso_b/c/b_total unchanged. Cadena A support cost increase propagates via cost-plus.
- WIP committed: `modules/calculator_motor/mixins/user_input_builders_cadena_a.py`, `context_builder_perfiles_soporte_mixin.py`, `context_builder_perfiles_light_mixin.py`, `modules/shared/contracts/api_v1/request/cadena_a.py`, `tests/golden/test_support_fte_v28.py`.

**Validation:**
- `test_support_fte_v28.py` → 9/9 PASS ✅
- `test_cts_001_v28.py` → 2/2 PASS ✅
- `test_cts_exam_crucero_v28.py` → 2/2 PASS ✅
- `validate-excel-v28` → PASS 6/6 ✅ (IPC ratio M7/M6 delta=0.000000000 — mechanism correct)
- `test_pyg_v28_ingreso_indexado.py` → 7/7 PASS ✅ (after anchor update)
- Remaining 24 failures = PREEXISTING_INFRA_PARAMETRIZATION (V27 frozen fixtures drifted by OP tasa_financiacion; deferred)

**Hard prohibitions respected:** No CTS-001 reopen, no CTS-002 reopen, no storage/ changes, no V27 frozen fixtures modified, no 9.5 hardcoded in modules/.

**Siguiente paso (P2):** V27 golden fixture regeneration — resolve 24 PREEXISTING_INFRA_PARAMETRIZATION failures. Controlled session: regenerate V27 fixtures with current active parametrization.

---

## V2-8 · TRIAGE_POST_CTS002 — COMPLETED (2026-06-12)

Golden suite: **25 fail / 71 pass** (stable baseline). validate-excel-v28: PASS 6/6 ✅

**Classification:**
- `PREEXISTING_INFRA_PARAMETRIZATION` (24): Active OP tasa_financiacion 0.0088→0.0153 drifted V27 frozen goldens. Not formula errors. Fix: V27 fixture regeneration (separate session, controlled).
- `REQUEST_VALUE_GAP` (1): `test_e95_supervisor_override_applied` — `fte_soporte_overrides` removed from request.json in `b8b3000`; unstaged WIP in `user_input_builders_cadena_a.py` + `test_support_fte_v28.py` pending commit.

**Recommended next step (P1):** Commit or align E95 WIP → reduces failures 25→24.
**P2:** V27 golden fixture regeneration → resolves remaining 24 `PREEXISTING_INFRA_PARAMETRIZATION`.
**P3 (after P1+P2):** Resume CTS-001 with fresh delta from clean baseline.

Full triage: `docs/refactor/v28_remaining_gaps_triage_after_cts002.md`

---

## V2-8 · CTS-002 — COMPLETED (2026-06-12) · CADENA_C_K34_MATCH

- **Excel K34:** 5,278.326744819592 COP/tx · **Backend:** 5,278.3267470588235 · **Delta:** 2.24e-6 (floating-point)
- **4 fixes:**
  - `2d006cc` — technology indexation: `pct_aumento_tecnologico = 0.0` (Tasas row=1.0) · delta +133.31 → -65.84
  - `ee1e7db` — fixed OPEX: `opex_fijo_integ` from `costo_variable.opex_items(tipo='Fijo')` 22,230,000/mes · delta -65.84 → +64.92
  - `cd5bb6d` — inversiones=0 (`ACCEPTED_EXCEL_QUIRK`: K38=#REF!→0, NOT in K34=SUM(K35,K36,K40)) · delta +64.92 → -11.40
  - `a146370` — equipo transversal: salario_cargado=4,284,360.05/FTE + opex_herramientas=1,159,602.60/mes · delta -11.40 → **0.00**
- **validate-excel-v28:** PASS 6/6 ✅ | **golden suite:** 25 fail / 71 pass (baseline pre-existente, sin cambio) ✅
- **CTS-001:** PAUSED_KNOWN_DELTA — no reabierto ✅ | **PyG anchors:** estables (7/7 PASS) ✅
- modules touched: `modules/calculator_motor/` (mixin + adapter + dto + user_input_builders) | request touched: `request/request.json` (salario_cargado) | baseline run: no

---

## V2-8 · VTM-001 — COMPLETED (2026-06-12)

- **`ingreso_mensual` fix**: `reglas.py:614` `ingreso_total` (24m cum) → `pyg_por_mes[2].ingreso_bruto` (M3 monthly)
- **Excel H19**: `Vision Tarifas_Modelo_Cobro`!H19 → HME!C289 = 3,018,108,469 · Backend: 3,076,257,253 (+1.9% ACCEPTED_ARCHITECTURAL_DELTA)
- **Golden anchors**: `vt_cobranzas_outbound_fte.json` 659,715,695 → 57,873,559 · `vt_v27_real_request.json` 38,631,742,871 → 2,057,008,752
- **validate-excel-v28**: PASS 6/6 ✅ (sin regresión)
- **test_vision_tarifas_golden_v27**: 17 PASS / 11 FAIL (was 16/12 — 1 test fixed) ✅
- **typed_contract**: 0 regressions ✅ (public_mapper path unaffected)
- **CTS-001**: PAUSED_KNOWN_DELTA — no reabierto ✅
- modules touched: `modules/vision_tarifas/reglas.py` (1 line) | request: 0 | motor P&G: 0
- **Siguiente**: CTS-002 (Cadena C delta 51.28 COP/tx) o seguir con mapa V2-8

---

## V2-8 · PARAM_VALUE_FIX_P5_ROTACION_SAC — COMPLETED (2026-06-12)

- **rotación SAC**: 0.09 → **0.077175** · fuente `Rot, Ausent y Rentabilidad`!F19 = AVERAGE(B19:E19)
- **Archivo modificado**: `tests/refactor/_v28_deal_provider.py:208`
- **validate-excel-v28**: PASS 6/6 ✅ (sin regresión)
- **test_pyg_v28**: 7/7 PASS ✅ — sin anchor drift
- **test_cts_001_v28**: 2/2 PASS ✅ — CTS-001 = PAUSED_KNOWN_DELTA (no reabierto)
- **test_cts_exam_crucero**: 2/2 PASS ✅ — anchors estables
- **Preexistentes**: tarifas 12 FAIL + support_fte 1 FAIL (sin cambio)
- modules touched: 0 | request touched: 0 | baseline run: no | CTS-001 reopened: no
- **Siguiente**: VTM-001 (P1) — Vision Tarifas H19 field mapping, o CTS-001 retomar residual -27.53

---

## V2-8 · ANCHOR_UPDATE_PYG — COMPLETED (2026-06-12)

- `test_pyg_v28_ingreso_indexado.py`: **7/7 PASS** (antes 4 PASS + 3 FAIL)
- 12 anchors refrescados: M1/M7/M19 × ingreso_a/b/c/total
- Causa: `tasa_ica` 0.01→0.00966 + alineación request cadena B/C (preexistente)
- Mecanismo IPC intacto: ratios M7/M6 y M19/M18 exactos (mechanism tests PASS)
- `validate-excel-v28`: PASS 6/6 (sin regresión)
- modules touched: 0 | request touched: 0 | storage touched: 0 | baseline run: no
- **Pendiente siguiente**: PARAM_VALUE_FIX P5 — rotacion SAC provider 0.09 → 0.077175

---

## V2-8 · OP_CONFIG_PROVIDER_FIX_P4 — COMPLETED (2026-06-12)

- **validate-excel-v28**: PASS 6/6 checks (1 skipped) ✅
- **Economic component 2026**: agregadas 6 filas `'20% SMMLV - 80% IPC'` al active OP-Componente (valor=0.06616). Fuente: v2-8/op.json fixture.
- **tasa_financiacion**: config sheet agregada → 0.0153 (Panel!L11 Excel). Confirmado vía `provider.tasa_mensual_financiacion()`.
- **Impacto en anchors**: `TestPYGAbsoluteAnchorsV28` 3 anchors DEFERRED (indexación ahora 6.616% vs silently 0.0 anterior).
- **modules touched**: 0. **request touched**: 0. **baseline run**: no. **CTS-001 reopened**: no.
- **Pendiente siguiente**: ANCHOR_UPDATE_PYG P4c + PARAM_VALUE_FIX P5 (rotacion SAC 0.09→0.077175).

---

## V2-8 · REQUEST_FIX_P2_P3 — COMPLETED (2026-06-12)

- **tasa_ica**: 0.01 → 0.00966 · fuente Tasas!B37 Bogota.
- **porcentaje_acumulado.actual**: ya era 0 en working copy (pre-alineado).
- Validación `validate-excel-v28`: bloqueada por `ParametrizationError: '20% SMMLV - 80% IPC' for year 2026` (error preexistente).
- Golden tests: fallos preexistentes, 0 nuevas regresiones.
- **Pendiente siguiente:** `OP_CONFIG_TASA_FINANCIACION_PROVIDER_FIX` (P4) — poblar OP-Config en storage activo.
- CTS-001: PAUSED_KNOWN_DELTA (no reabierto). CTS_SUPPORT_LOADED_MAGNITUDE: DEFERRED.

---

## V2-8 · V28_ENGINE_FORMULA_MAP_CONTINUATION — COMPLETED (2026-06-12)

- **10 hojas analizadas**: Inputs Nomina, Nomina Loaded, No payroll, Costo Fijo/Variable, Costo Cadena C, Costos Totales, Pólizas-Financiación, Vision P&G, Vision Tarifas.
- **Cambios funcionales: 0** — solo documentación.
- **Hallazgos nuevos:**
  - VTM-001 (P1): Vision Tarifas H19 = usar `pyg_por_mes[2].ingreso_bruto` — sin módulos.
  - REQUEST_FIX (P2): `porcentaje_acumulado.actual` 0.02 → 0 (Panel!C75=0).
  - REQUEST_FIX (P3): `tasa_ica` 0.01 → 0.00966 (Tasas!B37 Bogota).
  - PROVIDER_FIX (P4): OP-Config `tasa_financiacion` ausente → usa default 0.0088.
  - PARAM_VALUE_FIX (P5): rotacion SAC provider=0.09 vs Excel=0.077175.
  - BASE_INGRESO P&G: ACCEPTED_ARCHITECTURAL_DELTA (sin acción).
- **Siguiente sesión recomendada:** REQUEST_FIX P2+P3 (sin riesgo) → medir impacto P&G/Tarifas.
- **Doc:** `docs/refactor/v28_engine_formula_map_continuation.md`

---

## V2-8 · CTS-001 paused as known_delta — `CTS-001_FUNCTIONAL_PARITY_WITH_KNOWN_DELTA` (2026-06-12)

- **CTS-001**: `FUNCTIONAL_PARITY_WITH_KNOWN_DELTA`, paused. Residual -27.53 COP/tx (0.44%). FULL_MATCH=NO.
- **CTS_SUPPORT_LOADED_MAGNITUDE**: DEFERRED. Residual menor (~0.33%); retomar tras mapa general de fórmulas.
- **Next focus**: complete formula lineage/map for V2-8 engine sheets before global parity (`V28_ENGINE_FORMULA_MAP_CONTINUATION`).
  - Scope: Inputs Nomina, Nomina Loaded, No Payroll, Costo Fijo/Variable, Costo Cadena C, Costos Totales, Pólizas-Financiación, Vision P&G, Vision Tarifas.
- **Componentes CTS-001 cerrados**: cargos_adicionales ✅ · E95 override ✅ · CAPEX C47 ✅ · C38 variable ✅ · C46 OPEX ✅
- Docs: `cts_001_v28_evidence.md` §Cierre temporal · `formula_first_diff.md` §P5 · `v28_backlog.md` (CTS-001=PAUSED · CTS_SUPPORT_LOADED_MAGNITUDE=DEFERRED · V28_ENGINE_FORMULA_MAP_CONTINUATION=NEXT) · `v28_plan_status.md`

---

## V2-8 · CTS variable staff commission — `CTS_VARIABLE_COMMISSION_STAFF` (C38 EXACT) (2026-06-12)

- **Objetivo:** cerrar el residual C38 (-69.86) etiquetado `CTS_VARIABLE_INDEXATION_AGING`.
- **Diagnóstico previo REFUTADO:** la hipótesis "envejecimiento por indexación ≈1.0989" era falsa. Verificado con openpyxl: las filas de nómina de Vision CTS son PLANAS los 24 meses (sin aging). Y los **agentes ya coinciden** exactamente — Excel usa partición igual que el backend (fijo agente row 63 = 384,926,602 = 130×(W62−D62) = loaded − comisión cruda), NO aditiva.
- **Causa raíz real:** comisión variable de roles de SOPORTE. El bloque variable de Excel (`Nomina Loaded` filas 155-181) suma comisión por rol = `Inputs de Nomina`!D-col × FTE-staff (Supervisor D57×9.5=6,650,000 [usa E95], Jefe D46, Director D39). Backend tenía `comision_pct=0` para staff → variable soporte=0. Staff variable Excel = 15,439,248/mes = 69.86 COP/tx = el residual exacto.
- **Fix:** `tests/refactor/_v28_deal_provider.py` `_V28_STAFF_COMISION` — poblar `salario`(=Excel C) + `comision_pct`(=Excel D/C) para Director/Jefe/Supervisor (filas existentes + alias accent-stripped, porque `get_comision_pct_rol` usa `.lower()` sin quitar acentos y "jefe de operación" no resolvía). Particiona igual que agentes (`salario_fijo = total_cargado − comisiones`) → **total de soporte invariante**.
- **Resultado:** C38 705.88 → **775.7432 (Δ+0.0000 EXACT)**. C37 +49.35 → -20.51 (mejora). C34/C35/C36 invariantes (sin compensación falsa). Hardcodes en `modules/`: 0 (valores en test provider, trazables a Excel C/D).
- **Clasificación:** `PROVIDER_VALUE_MISMATCH`. **Residual restante `CTS_SUPPORT_LOADED_MAGNITUDE`:** C37/C36 -20.51 = cargado de soporte (override W) ~20.51 COP/tx por debajo de Excel. Frente separado, menor (~0.33%).
- **Gates:** CTS 2/2 · nomina_variable 2/2 · exam/crucero 2/2 · support FTE 6/6 · validate-excel-v28 6/6 · make all PASS (verify baseline match, sin drift). Golden suite: 0 fallos nuevos vs HEAD. Baseline NO requerido.
- **Docs:** `formula_first_diff.md` §P4, `cts_001_v28_evidence.md`, `v28_backlog.md` (CTS-SUPPORT-LOADED-MAGNITUDE nuevo).
- **Siguiente:** `CTS_SUPPORT_LOADED_MAGNITUDE` (auditar overrides W staff vs Excel W39:W58) o cerrar CTS-001 como known_delta -27.53 (0.44%).

---

## V2-8 · CTS salary split C37/C38 — `CTS_SALARY_SPLIT_ALIGNED` (2026-06-12)

- **Objetivo:** alinear el split salario_fijo/variable (Vision CTS C37/C38) contra Excel V2-8, frente restante de CTS-001.
- **Hallazgo:** la antigua hipótesis "aditiva" era una lectura errónea — **Excel usa partición** (C37 = C36 − C38), igual que el backend. La única diferencia estructural: el backend aplicaba `× pct_cumplimiento_variable (0.70)` a la línea de costo variable (`nomina.py:_comisiones`), que NO existe en Excel `Inputs de Nomina`!D62 (comisión cruda). Como `salario_fijo = total_cargado − comisiones`, el 0.70 inflaba fijo (carve-out) y reducía la variable.
- **Fix:** removido `× pct_cumplimiento_variable` de `_comisiones` (variable = `salario_base × FTE × comision_pct × idx` = comisión cruda Excel D62). Blast radius verificado: el 0.70 solo multiplicaba un costo en ese punto (`nomina_cargada.py` ya no lo aplica desde el fix Bug-2). **Total-invariante** (`fijo+variable=total_cargado`).
- **Resultado:** C37 +261.11→**+49.35** · C38 -281.63→**-69.86** (ambos mejoran ~212 individualmente). C34/C35/C36/PyG/Tarifas/baseline **sin cambio** (invariante) → sin compensación falsa, sin cascada.
- **Residual (frente separado `CTS_VARIABLE_INDEXATION_AGING`, diferido):** C38 -69.86 = envejecimiento idx de la comisión agente (≈1.0989) + comisión cruda de staff (Director/Jefe/Supervisor) que Excel suma a la variable y el backend lleva en el cargado (override) con `comision_rol=0`. Cerrar → toca provider/request/indexación (afecta total → `STOP_LARGER_NOMINA_REDESIGN`).
- **Gates:** CTS 2/2 · nomina_variable_load 2/2 · exam/crucero 2/2 · support FTE 6/6 · validate-excel-v28 6/6 · **make all PASS (verify baseline match, sin drift)**. Golden suite: **0 fallos nuevos** vs HEAD (las 3 fallas PyG son pre-existentes de E95). Hardcodes nuevos: 0.
- **Docs:** `formula_first_diff.md` §P3, `cts_001_v28_evidence.md`, `v28_backlog.md` (CTS-VARIABLE-INDEXATION-AGING nuevo).
- **Siguiente:** `CTS_VARIABLE_INDEXATION_AGING` (descomponer override staff / poblar comision_rol + envejecimiento variable; re-baseline aprobado) o cerrar CTS-001 como known_delta -27.53 (0.44%).

---

## V2-8 · E95 override + CAPEX amortization — `E95_OVERRIDE_APPLIED` + `CTS_CAPEX_AMORT_FIXED` (2026-06-12)

- **Objetivo:** cerrar el residual dominante de CTS-001 vía override Supervisor SAC E95=9.5 (Excel literal) + corregir amortización CAPEX. Opción 3 aprobada por el usuario (E95 + CAPEX juntos, sin compensación).
- **Hallazgo crítico:** el headline CTS-001 era `+1.05 COP/tx` **falso** — cancelación entre payroll -74.94 (brecha E95) y CAPEX +75.99 (sobre-amortización). No era paridad real. Esta sesión corrige **cada componente** contra Excel.
- **P1 E95 override (opt-in per-rol):** campo `fte_soporte_overrides: Dict[str,float]` en `PerfilCadenaAV1` + DTO + dominio `PerfilCadenaA` + builders. Default vacío = legacy byte-idéntico. En `context_builder_perfiles_soporte_mixin` reemplaza `fte_contable` del rol ANTES de cascada SENA/Inclusión. Request SAC `{"Supervisor": 9.5}` (Excel CCA!E95). Supervisor SAC 7.1→9.5. **0 hardcodes** (9.5 en request).
- **P2 CAPEX (C47 EXACT):** root cause = (1) backend leía `meses_amortizacion` (request usa `meses_a_diferir`) → `meses=1` → `precio_mensual=precio_total`; (2) gate `mes≤meses` con meses=1 → todo CAPEX en mes 1 (966M)/24=182.20. Excel `No payroll`!E167 amortiza plano `precio/meses_a_diferir × cantidad × (1+L11)` TODOS los meses del contrato (`meses_a_diferir` no gatea, solo deriva precio_mensual). Fix: `_build_amortizable_item` usa precio_mensual del request + `meses=meses_contrato` (cobro plano). **C47 182.20→103.0436 (Δ+0.0000 EXACT)**.
- **Resultado:** CTS-001 +1.05 (falso) → **-27.53 COP/tx (0.44%) HONESTO**. C35 payroll -74.94→-24.36 (+50.58). C47 EXACT. Sin compensación: cada componente individualmente más cerca de Excel.
- **Residual restante:** `CTS_SALARY_ADDITIVE_STRUCTURE` (C37 salario_fijo +210.53 / C38 salario_variable -281.63: Excel suma comisión cruda D62 sobre el cargado AM, backend la particiona) + costos_fijos -3.17. Frente separado (toca NominaCalculator + re-baseline).
- **Gates:** CTS golden 2/2 · exam/crucero 2/2 · support FTE 6/6 (anchors E95 actualizados, opt-in verificado) · validate-excel-v28 6/6 · **make all PASS (verify baseline match, sin drift)**. Hardcodes nuevos: 0.
- **Drift esperado (diferido):** 4 anchors `no_payroll` v27 frozen golden (`test_cost_to_serve_golden_v27.py`, `test_vision_tarifas_golden_v27.py`) drift por el fix CAPEX (solo no_payroll; payroll/salario intactos). `SNAPSHOT_REGENERATION_REQUIRED` — NO regenerado (política). Las otras 24 fallas v27 son pre-existentes (`GOLDEN-001`). `make baseline` NO ejecutado/no requerido.
- **Docs:** `formula_first_diff.md` (NEW), `v28_backlog.md` (CTS-CAPEX-AMORT + CONTRACT-OVERRIDE-PER-ROL cerrados), `cts_001_v28_evidence.md`.
- **Siguiente:** `CTS_SALARY_ADDITIVE_STRUCTURE` (C37/C38) o `SNAPSHOT_REGENERATION` (regenerar 4 v27 no_payroll anchors con aprobación).

---

## V2-8 · WORKTREE_REQUEST_NULL_FIXED — `WORKTREE-REQUEST-NULL` RESOLVED (2026-06-12)

- **Objetivo:** resolver bloqueo `cantidad: null` en WhatsApp `opex_fijo.items[3,4]` que causaba `TypeError float(None)` en `context_builder_perfiles_soporte_mixin.py:398`.
- **Fix:** `request/request.json` → `condiciones_cadena_a.perfiles[1].opex_fijo.items[3].cantidad: null → 0` y `items[4].cantidad: null → 0`.
- **Fuente:** `opex_request_alignment_v28.md` §1 tabla — WhatsApp: `Licencia Genesys Blending = 0` / `Licencia Genesys Rotación = 0` (Excel No payroll sheet). Genesys no aplica a WhatsApp; `no_payroll_mensual: 3525293.25` override cubre el total correcto.
- **Root cause del crash:** `_calcular_opex_fijo_mensual_perfil` (Vision Tarifas decomp) siempre itera `items`; `item.get('cantidad', 1.0)` retorna `None` (key presente con valor null) → `float(None)` → TypeError.
- **Gates:** CTS golden 2/2 PASS · exam/crucero 2/2 PASS · validate-excel-v28 6/6 PASS (1 SKIP esperado).
- **Hardcodes nuevos en motor:** 0.
- **Backlog:** `WORKTREE-REQUEST-NULL` → RESOLVED.
- **Siguiente:** `E95_OVERRIDE_DECISION` (≈80% residual CTS-001 = SAC Supervisor E95=9.5 literal override, ~-49 COP/tx).

---

## V2-8 · Excel Engine Lineage Fast Pass — `V28_EXCEL_ENGINE_LINEAGE_FAST_PASS_COMPLETED` + `STOP_DIRTY_WORKTREE_GATE_BLOCK` (2026-06-12)

- **Objetivo:** mapa accionable Visiones/charts → hojas intermedias → inputs Panel/Condiciones → parametrización HR/OP/GN → request.json → backend. Diagnóstico read-only (sin fixes). Output: [`docs/refactor/v28_excel_engine_lineage_fast_pass.md`](../refactor/v28_excel_engine_lineage_fast_pass.md).
- **DAG:** 4 inputs raíz (Panel + Cadena A/B/C) + 3 hojas parametrización (Tasas/Rot/Listas) + 11 intermedias (Nomina Loaded, No payroll, Costos*, Pólizas-Financ., HME) → 4 visiones (CTS, P&G, Tarifas, Imprimible) → charts (Graficos!/Riesgo!).
- **Fase 4 (nuevo) parametrización↔backend:** paridad mayormente vía provider W-override (`_v28_deal_provider.py`), no storage activo. Mismatches reales: rotación SAC (provider 0.09 vs Excel F19=0.077175, `PARAM_VALUE_MISMATCH`) + `tasa_financiacion` (OP-Config ausente, `PARAM_MISSING_EXISTING_FIELD`). 0 claves/tablas nuevas requeridas.
- **Fase 6 (nuevo) charts:** 5 gráficos, todos display de datos ya calculados; 0 cambio de backend.
- **0 `BACKEND_MISSING_COMPONENT`**, hardcodes nuevos: 0.
- **⚠️ Bloqueador operativo:** worktree `request/request.json` sin commitear (WIP `OPEX_REQUEST_ALIGNMENT`) deja `cantidad: null` en WhatsApp `opex_fijo.items[3,4]` → `TypeError float(None)` en `context_builder_perfiles_soporte_mixin.py:398`; rompe **todos** los gates de motor (CTS golden 2/2 FAIL, validate-excel-v28 2/6 FAIL). En `HEAD` `6778540` hay 0 nulos y pasan. **No es regresión de esta sesión.** Backlog: `WORKTREE-REQUEST-NULL`.
- **Gates:** no ejecutado `make all`/`make baseline`. Solo docs commiteados.
- **Siguiente:** resolver `WORKTREE-REQUEST-NULL` (poblar cantidad o revertir WIP a HEAD); luego `E95_OVERRIDE_DECISION` (≈80% residual CTS-001).

---

## V2-8 · `cargos_adicionales` IMPLEMENTED — `CONTRACT_CHANGE_CARGOS_ADICIONALES_APPLIED` + `CTS-001_PARTIAL_BEST_IMPROVED` + `E95_OVERRIDE_DEFERRED` (2026-06-12)

- **Objetivo:** implementar el campo aprobado `cargos_adicionales: float = 0.0` y usarlo en el numerador del FTE de soporte de Cadena A, sin hardcodear en el motor.
- **Contrato:** campo `cargos_adicionales: float = Field(default=0.0, ge=0.0)` en `PerfilCadenaAV1` ([cadena_a.py:31](modules/shared/contracts/api_v1/request/cadena_a.py)); espejo en DTO interno `PerfilCadenaAInput` y en el modelo de dominio `PerfilCadenaA` (panel.py). Backward compatible (default neutro).
- **Wiring:** request → `_perfil_a` builder → `PerfilCadenaAInput` → `_construir_perfil_a` → `PerfilCadenaA` → `context_builder_perfiles_soporte_mixin`. Verificado que el normalizer (`dict(perfil)`) y `{**perfil}` preservan el campo.
- **Fórmula:** nueva variable `fte_base_soporte = fte_base + perfil_base.cargos_adicionales` usada SOLO en el loop de soporte regular (Excel CCA!E95/F95/G95 `(col9+col26)/col122`). `fte_base` (reparto Especialista, salario de agentes) intacto → **sin doble conteo** (perfiles base conservan fte=130/50/80).
- **Request V2-8:** `request.json` perfiles Cadena A → SAC `cargos_adicionales=12` (E26), Crecimiento `7.384615` (G26); WhatsApp omitido (F26=0 → default). Sin otro campo tocado.
- **CTS-001:** delta **-128.4328 → -61.3335** COP/tx (move **+67.10**, 2.063%→**0.985%**). Supervisor SAC 6.5→7.1=(130+12)/20 ✓.
- **Residual -61.33 decompuesto:** E95 override (2.4 FTE Supervisor, ≈-49 COP/tx, **DIFERIDO**) + cap/crucero/exámenes no cableados (-3.84) + SENA/Inclusión estructural & CAPEX no-payroll (~-8.5). Sin el E95 diferido, estaría ~-12 (±20).
- **E95=9.5:** override manual literal → **NO implementado** (diferido por diseño). Backend SAC supervisor = 7.1 (fórmula), no 9.5.
- **Tests:** nuevo `tests/golden/test_support_fte_v28.py` (6/6). Anchors backend PyG (ingreso_a M1/M7/M19) refrescados por drift trazado (B/C sin cambio; mecanismo de indexación intacto).
- **Gates:** support FTE 6/6 · CTS golden 2/2 · exam/crucero 2/2 · nomina 2/2 · PyG 7/7 · validate-excel-v28 6/6 · make all 36 pass + **baseline match (sin drift)**. Hardcodes nuevos en motor: **0**.
- **Baseline:** NO requerido (make verify = baseline match). NO ejecutado `make baseline`.
- **Siguiente:** `E95_OVERRIDE_DECISION` (decidir si modelar el override per-rol) o cerrar CTS-001 como known_delta parcial documentado.

---

## V2-8 · Contract Design `cargos_adicionales` — `CONTRACT_CHANGE_CARGOS_ADICIONALES_DESIGN_READY` (2026-06-12)

- **Objetivo:** diseñar (sin implementar) el contract change para soportar `cargos_adicionales` en V2-8 —
  el gap dominante de CTS-001 (FTE soporte / override per-rol). Output: `docs/refactor/contract_design_cargos_adicionales_v28.md`.
- **Excel confirmado (`openpyxl`):** `Condiciones Cadena A`!E26=12 · F26=None(0) · G26=7.384615 (cargos_adicionales por escenario);
  F95/G95 fórmula `(col9+col26+col30+col34)/col122`; **E95=9.5 literal** (override manual, la fórmula daría (130+12)/20=7.1).
- **Clasificación:** E26/F26/G26 = `SCENARIO_LEVEL_INPUT`; E95=9.5 = `PROFILE_LEVEL_OVERRIDE` (literal, sin regla de negocio).
- **Decisión:** **Alternativa A** (campo `cargos_adicionales: float=0.0` por escenario/perfil-base en `PerfilCadenaAV1` +
  `PerfilCadenaAInput`, consumido en numerador FTE soporte `soporte_mixin:122/137-146`). Override per-rol (Alt C, E95) **DIFERIDO**
  (`NEEDS_REVIEW`, riesgo número mágico). Alt B (por rol) rechazada (granularidad errónea, E26 es 1 por escenario).
- **Backward compat:** default `0.0` neutro; `extra="forbid"` no afecta campos nuevos declarados; legacy idéntico. No breaking.
- **Riesgo dominante:** doble conteo → `cargos_adicionales` solo al numerador soporte/cap/crucero, nunca al salario de agentes.
- **Gates:** CTS golden 2/2 · exam/crucero 2/2 · validate-excel-v28 6/6 · make all PASS. Baseline NO ejecutado. Hardcodes nuevos: 0.
- **Siguiente:** `IMPLEMENT_CARGOS_ADICIONALES_CONTRACT` (fase de implementación, fuera de esta sesión) o `CLOSE_CTS001_PARTIAL_DOCUMENTED`.

---

## V2-8 · Vision CTS Formula Map — `V28_VISION_CTS_FORMULA_MAP_COMPLETED` (2026-06-12)

- **Objetivo:** mapa fórmula-por-fórmula de `Vision Cost To Serve` (Excel celda→fórmula→backend→delta→clasif)
  para decidir si `cargos_adicionales` sigue siendo el único gap estructural grande antes de abrir contrato.
- **Output:** `docs/refactor/v28_vision_cts_formula_map.md`. Mapa 1:1 del bloque CTS Cadena A (C34-C48, 14 celdas core).
- **Estructura confirmada:** cada línea Excel = `SUM(rango_mensual)/C11(24m)/W31(221,000 tx/mes)`; backend la replica
  en `cost_to_serve_calculator.py:329` (`avg_div`). Campos backend anotados con su celda Excel (C036-C048).
- **Comparación (Excel vs backend, post e296c77):**
  - CTS-001: 6,224.575126 vs **6,096.142357** → -128.43 (2.063%). Reconciliación exacta: payroll -141.98 + no-payroll +13.55.
  - **Payroll C35** -141.98 (~97% residual): `nomina_loaded` -138.14 = raíz `cargos_adicionales` (FTE soporte).
  - **OPEX C46** = 308.138215 EXACT (Δ=0). **CAPEX C47** +16.72 (FORMULA_GAP amortización, signo opuesto).
  - **Firma única:** cap_inicial/cap_rotación/crucero con Δ% **idéntico -6.938%** = proporción FTE soporte faltante.
- **0 MAPPING_AMBIGUOUS · 0 BACKEND_METRIC_NOT_EXPOSED.** Hardcodes nuevos: 0.
- **Decisión:** `cargos_adicionales` = único gap estructural grande; **no hay otro comparable**. Contrato debe cubrir
  (1) `cargos_adicionales` por escenario + (2) override per-rol (SAC Supervisor E95=9.5 literal). CAPEX = frente aparte.
- **Gates:** CTS golden 2/2 · exam/crucero 2/2 · validate-excel-v28 6/6 · make all PASS. Baseline NO ejecutado.
- **Siguiente:** `CONTRACT_CHANGE_CARGOS_ADICIONALES` (único P0 para cerrar CTS-001 Cadena A).

---

## V2-8 · DIAS_CAPACITACION Request Alignment — `DIAS_CAPACITACION_REQUEST_ALIGNMENT_APPLIED` (2026-06-12)

- **Objetivo:** aplicar el único quick-win request-scope con impacto medido: alinear `dias_capacitacion_perfil` 10→11.
- **Excel confirmado:** CCA!E139=F139=G139=11 (label "Días de capacitación por perfil"). Inequívoco.
- **Cambio:** `request/request.json` — 3 perfiles Cadena A: `dias_capacitacion_perfil` 10→11. Sin otro campo tocado.
- **Impacto medido (motor):**
  - **CTS-001:** 6,093.2443 → **6,096.1424** (+2.898 COP/tx). Delta vs Excel: -131.33 → **-128.43 COP/tx (2.063%)**.
  - **cap_inicial:** +0.98 COP/tx. **cap_rotacion:** +1.92 COP/tx.
  - **OPEX/crucero/pct_acumulado/comisiones:** sin cambio (todos estables).
  - **PyG ingreso_bruto_a:** anchors actualizados (propagación cost→tarifa via solver: M1 +741,800 / M7 +869,947).
- **Gates:** CTS golden 2/2 · exam/crucero golden 2/2 · nomina golden 2/2 · PyG golden 3/3 · validate-excel-v28 6/6 · make all PASS.
- **Baseline:** NO ejecutado (no requerido — cambio leve dentro de tolerancia).
- **Hardcodes nuevos en motor:** 0.
- **Siguiente:** `CONTRACT_CHANGE_CARGOS_ADICIONALES` (raíz del 97% residual) o alinear `porcentaje_acumulado` 0.02→0 (P&G/Tarifas).

---

## V2-8 · What-If Gap Simulation — `V28_WHAT_IF_GAP_SIMULATION_COMPLETED` (2026-06-11)

- **Objetivo:** medir (motor) el impacto real de cada gap CTS-001 conocido, individual y combinado, sin fixes.
- **Output:** `docs/refactor/v28_what_if_gap_simulation.md`. Baseline CTS-001 = 6,093.2443 (-131.33, 2.110%);
  payroll 5,317.48; no-payroll 775.77; OPEX 308.14 (EXACT); crucero 9.8918; exámenes 11.512.
- **Impactos medidos:**
  - **DIAS_CAPACITACION** (10→11): **+2.898 COP/tx** → `APPLY_NOW_REQUEST_SCOPE` (único request-scope que mueve CTS).
  - **PCT_ACUMULADO** (0.02→0): **0.0 en CTS** (factor billing/P&G, no CTS) → `NEEDS_FORMULA_MAP`.
  - **COMISION_ROL_STAFF** (patch request): **0.0** — `roles_operativos[].comision_rol` no consumido; comisión
    ya embebida en provider W-override → `ALREADY_APPLIED_BASELINE`.
  - **CRUCERO_FULL_PARITY**: +0.7375 solo via aproximación (escalar tarifa) → `DO_NOT_APPLY_COMPENSATING_GAP`.
  - **CARGOS_ADICIONALES**: `NOT_SIMULABLE_WITHOUT_MODULE_CHANGE` (sin campo; raíz dominante ≈ -68).
- **Conclusión:** techo request-scope = **2.051%** (-127.70 COP/tx). ~97% del residual es payroll soporte
  (cargos_adicionales + override SAC Supervisor E95): contrato/módulo, no request. No quedan quick-wins de input.
- **Gates:** CTS golden 4/4 · validate-excel-v28 6/6 · make all PASS. Hardcodes nuevos: 0.
  Sin cambios en modules/request/storage/tests/baseline (runner en /tmp).
- **Siguiente:** decidir contrato `cargos_adicionales` (+override Supervisor) — único frente que cierra el residual.

---

## V2-8 · Input Full Mapping — `V28_INPUT_FULL_MAPPING_COMPLETED` (2026-06-11)

- **Objetivo:** pausar fixes delta-por-delta; construir mapa maestro extremo-a-extremo de inputs V2-8
  (Excel input real → request.json → contrato API → loader/context/provider → valor consumido backend).
- **Output:** `docs/refactor/v28_input_full_mapping.md` (~70 inputs Panel + Cadena A/B/C).
  ~48 MATCH, 3 VALUE_MISMATCH, 3 MISSING_IN_REQUEST, 2 PRESENT_NOT_CONSUMED, 3 MAPPING_AMBIGUOUS,
  3 EXCEL_SOURCE_OPAQUE.
- **Hallazgos nuevos (no detectados por fixes previos):**
  - `dias_capacitacion_perfil` Excel A!E139=**11** vs request **10** → `INPUT-DIAS-CAP` (request-scope).
  - `porcentaje_acumulado.actual` request **0.02** vs Panel!C75=**0** → `INPUT-PCT-ACUM` (request-scope).
  - `comision_rol` staff=0.0 vs Excel F44/F51/F62 (Director/Jefe Op/Supervisor) → staff variable ausente
    del deal; provider lo simula → `STAFF-COMISION-001`.
  - `roles_operativos[]` NO consumido: el motor usa `staff_config[]` → `ROLES-OP-STAFFCONFIG`.
  - `pct_ausentismo` `PRESENT_NOT_CONSUMED`. Panel!L6 "¿Aplica indexación?"=No = gate de tarifa de venta
    (no de costo) — sin campo backend equivalente, no inventar.
- **Confirmado:** `cargos_adicionales` (A!E26/G26=12/0/7.3846) = `MISSING_BACKEND_INPUT_SOURCE` (P0,
  decisión de contrato DEFERRED). Supervisor E95=9.5 = override literal (`EXCEL_SOURCE_OPAQUE`).
- **Gates:** CTS golden 4/4, exam/crucero golden incluido, validate-excel-v28 6/6 (1 skip), make all PASS.
  Hardcoded nuevos en motor: 0. Sin cambios en modules/request/storage/tests/baseline.
- **Backlog:** +5 entradas (`INPUT-DIAS-CAP`, `INPUT-PCT-ACUM`, `STAFF-COMISION-001`,
  `ROLES-OP-STAFFCONFIG`, `AUSENTISMO-NOT-CONSUMED`).
- **Siguiente:** `V28_FIX_ROADMAP` consolidado — binomio payroll soporte (`comision_rol` staff +
  `cargos_adicionales`) domina el residual CTS (-131 COP/tx) ahora que OPEX = paridad exacta;
  quick-wins request-scope previos (dias_cap, pct_acumulado).

---

## V2-8 · OPEX Request Alignment — `OPEX_EXACT_PARITY_VIA_REQUEST` (2026-06-11)

- **Fix:** `no_payroll_mensual` per-perfil en los 3 perfiles Cadena A de `request.json`.
  SAC=39,973,918.08 / WA=3,525,293.25 / Crec=24,599,334.20307692 COP/mes (Excel No payroll!C107/C111/C108).
- **OPEX TI:** backend 380.09 → **308.138215** COP/tx = Excel 308.138215 → **delta = 0.000000 (EXACT MATCH)**.
- **CTS-001:** -59.38 → **-131.33 COP/tx (2.110%)** — empeora porque OPEX dejó de enmascarar el déficit de payroll.
- **Regression factor:** 131.33 / 59.38 = **2.21x < 5.0 → SAFE**.
- **Tests:** golden 13/13 PASS; refactor 86/94 PASS (8 pre-existentes). Sin fallos nuevos.
- **Lógica de override:** `no_payroll_mensual > 0` bypasea `opex_fijo.items` keyword filter → no doble-conteo.
- **Item-level mapping:** `OPEX_ITEM_MAPPING_AMBIGUOUS` (Excel: Worki/Speech/Genesys ≠ request: Internet/Antivirus/CCaaS).
- **Detalle:** `docs/refactor/opex_request_alignment_v28.md`.
- **Siguiente:** `CONTRACT_CHANGE_CARGOS_ADICIONALES` (campo nuevo para Support FTE y Crucero residual) o `CTS-002`.

---

## V2-8 · Crucero Request Alignment — `CTS_CRUCERO_PARTIAL` (2026-06-11)

- **Fix:** `incluye_crucero=true` en los 3 perfiles Cadena A de `request.json`. Sin cambios en modules/.
- **Crucero:** backend 0 → **9.892** COP/tx (Excel 10.629, residual -0.737 = cargos_adicionales).
- **CTS-001:** -69.27 → **-59.38 COP/tx (0.954%)**. Estado: `PARTIAL_BEST_IMPROVED`.
- **Baseline:** sin drift (baseline es `bancamia_whatsapp_only`, no afecta SAC deal).
- **Gates:** golden 4/4, validate-excel-v28 6/6, make all PASS.
- **Siguiente:** `OPEX_REQUEST_ALIGNMENT` (reconciliar opex_fijo.items vs Excel) → luego `CONTRACT_CHANGE_CARGOS_ADICIONALES`.

---

## V2-8 · CTS-001 Decision Checkpoint — `CTS_INPUT_DECISION_CHECKPOINT_COMPLETED` (2026-06-11)

- **CTS-001:** -69.27 COP/tx (1.113%), `PARTIAL_BEST` / `FULL_MATCH=BLOCKED`. Gates: golden 4/4,
  validate-excel-v28 6/6, make all PASS (baseline match, sin drift).
- **Crucero** → `CTS_CRUCERO_FIXABLE_WITH_REQUEST`: campo `incluye_crucero` **ya en contrato**
  (`cadena_a.py:36`), tarifa `crucero=8408` ya en request.json. Falta activar el flag en perfiles.
  +10.63 COP/tx, mejora directa. (Corrige doc previo "tarifa ausente" — era falso.)
- **OPEX no-payroll** → `OPEX_NO_PAYROLL_FIXABLE_WITH_REQUEST`: data desde `opex_fijo.items` (existe).
  Backend **+71.95 SOBRE** Excel → corregir en aislamiento **empeora** CTS-001 (enmascara déficit FTE).
- **Support FTE / cargos_adicionales** → `CONTRACT_CHANGE_CARGOS_ADICIONALES_DEFERRED`: único frente que
  exige campo nuevo. Decidir contrato solo tras agotar request-scope y aislar el residual FTE real.
- **Decisión:** agotar request-scope primero (sí), abrir contrato ahora (no).
- **Detalle:** `docs/refactor/cts_001_decision_checkpoint_v28.md`.
- **Siguiente:** `CRUCERO_REQUEST_ALIGNMENT` → `OPEX_REQUEST_ALIGNMENT` → reevaluar contrato.

---

## V2-8 · Support FTE — `SUPPORT_FTE_BLOCKED_MISSING_SOURCE` (2026-06-11)

- **Frente:** gap dominante CTS-001 (~-68 COP/tx vía Supervisor soporte).
- **Causa confirmada:** Excel calcula soporte como `(fte_agentes + cargos_adicionales)/ratio`,
  `cargos_adicionales` = `Condiciones Cadena A`!E26/E30/E34 = **12 / 0 / 7.3846** (insumo separado).
  SAC Supervisor E95=**9.5** es un **override manual literal**, no la fórmula.
- **Bloqueo:** `cargos_adicionales` **no existe** en request / context / provider
  (`PerfilCadenaAInput` solo tiene `fte`). Prohibido crear campo público nuevo o hardcodear → **BLOCKED**.
- **Reclasificación:** `SUPPORT_FTE_REQUIRES_MODULE_SCOPE` → **`SUPPORT_FTE_BLOCKED_MISSING_SOURCE`** +
  `REQUIRES_CONTRACT_DECISION`.
- **Motor:** sin cambios. Baseline: sin regenerar. Hardcoded nuevos en motor: 0.
- **Detalle:** `docs/refactor/support_fte_input_decision_v28.md` §8-§10.
- **Siguiente:** decisión de contrato (añadir dotación adicional por escenario) o avanzar a
  `CTS_CRUCERO_INPUT_DECISION` / `OPEX_NO_PAYROLL_INPUT_DECISION`.

---

**LECTURA RÁPIDA PARA NUEVA SESIÓN:**
- Revisar cambios sin commit: `git status` y `git diff`
- Verificar baseline: `PYTHONPATH=$(pwd) pytest backend_nexa/tests/ -m "parity or baseline" -q`
- Flujo completo: leer `docs/ai/CODE_REVIEW_WORKFLOW.md` o `docs/ai/QUICK_START.md`
- Dudas de design: leer `docs/ai/ROUTING_MATRIX.md` para elegir worker

---

## Estado actual
Branch activo: `refactor/modular-pure`

### ✅ SUPPORT FTE — AUDITORÍA DE DECISIÓN (READ-ONLY): SUPPORT_FTE_REQUIRES_MODULE_SCOPE — 2026-06-11

**Status: `SUPPORT_FTE_REQUIRES_MODULE_SCOPE`. Diagnóstico, NO fix. 0 hardcodes nuevos. Gates PASS.**

- **REFUTA la auditoría previa "Excel soporte ~71 FTE vs backend 61.4 (gap -138)".** Extracción limpia
  del bloque FTE de Excel (`Condiciones Cadena A`!E77:G100): **Excel soporte = 59.55 FTE vs backend 61.44
  → backend +1.89 FTE (MÁS, no menos).** El gap NO es dotación.
- **Causa raíz dominante (`SUPPORT_FTE_FORMULA_BUG`, ~-68 COP/tx)**: numerador FTE soporte backend =
  `fte_agentes/ratio`; Excel = `(fte_agentes + cargos_adicionales CCA!E26)/ratio`. Supervisor backend
  13.0 vs Excel 16.37 (-3.37 FTE caro). Ratios COINCIDEN (no es ratio/input mismatch).
- Secundarios: `SUPPORT_FTE_PROFILE_MAPPING_MISMATCH` (Excel desactiva GTR/JCR/AFAC, backend activa →
  request/staff_config); `SUPPORT_FTE_RAMP_MISMATCH` (rotación analistas, a confirmar).
- **Crucero CORREGIDO**: `request.json crucero=8408` (tarifa SÍ existe → `tarifa_crucero`); backend=0
  porque falta flag `incluye_crucero` en perfiles. `CTS_CRUCERO_INPUT_DECISION_REQUIRED` (no BLOCKED).
- **OPEX**: +71.95 COP/tx (`no_payroll_mensual` request.json) → `OPEX_NO_PAYROLL_INPUT_DECISION_REQUIRED`.
- CTS-001 sin cambio: 6,155.30 vs 6,224.58 = -69.27 (1.113%). Golden 4/4, validate-excel-v28, make all: PASS.
- Doc: `docs/refactor/support_fte_input_decision_v28.md` (matriz completa + trazabilidad por rol).

### ✅ CTS-001 V2-8 — CTS-EXAM PROVIDER PATCH APPLIED: PARTIAL_BEST_IMPROVED (1.113%) — 2026-06-11

**Status: `CTS_EXAM_APPLIED` / `CTS-001_PARTIAL_BEST_IMPROVED`. Backend examenes: 0.016 → 11.512 (+11.496 COP/tx).**
**CTS: 6,143.81 → 6,155.30 COP/tx (1.298% → 1.113%). NO módulos. NO re-baseline.**

- Patch A: `med_seg[Bogota].valor = 60,800` (from Excel `Nomina Loaded!C329/C330/C331 = 60,800`).
  Active HR had 60.8 (wrong scale). Patched in `_v28_deal_provider.py`.
- Patch B: `rotacion_ausentismo[SAC].pct_examen_anual = 0.28` (from Excel `Condiciones Cadena A!E135`).
  Active HR fallback was 1.0 (HR-AutRot missing). `pct_rotacion_mensual=0.09, pct_ausentismo=0.07` unchanged.
- Residual examenes -0.73 COP/tx = `fte_examenes` gap (soporte FTE mismatch, requires modules/).
- **CTS-CRUCERO = BLOCKED**: `tarifa_crucero` comes from `datos_operativos.crucero` in request.json — NO provider.
  Excel `Condiciones Cadena A!E152 = 1,193,936/month`. Business decision required.
- Gate < 2%: PASS (1.113%). Golden: 4/4 PASS. validate-excel-v28: PASS. make all: PASS.
- Docs: `docs/refactor/cts_exam_crucero_audit_v28.md` (full trace, crucero classification).

### ✅ CTS-001 V2-8 — SENA/INCL PROVIDER PATCH APPLIED: PARTIAL_BEST_IMPROVED (1.298%) — 2026-06-11

**Status: `CTS_SENA_INCLUSION_PROVIDER_PATCH_APPLIED` / `CTS-001_PARTIAL_BEST_IMPROVED`.**
**Best: 6,143.809068 COP/tx (delta = -80.77, 1.298%). Provider-only fix. NO módulos. NO re-baseline.**

- Patch: `_V28_SENA_INCLUSION_SALARY` en `tests/refactor/_v28_deal_provider.py`.
  `aprendiz sena`=1,750,905 / `inclusion`=1,750,905 (fuente: Excel `Inputs de Nomina`!C59/C60).
- Mejora: 6,109.62 → 6,143.81 COP/tx (+34.18 cerrados, 1.847% → 1.298%).
- Gate: < 2% (tightened from < 3%). CTS golden 2/2 PASS, validate-excel-v28 PASS, make all PASS.
- Residual -80.77 restante: soporte FTE ~-138 + examenes -12.22 + crucero -10.63 + cap -5.28
  + no-payroll OPEX +71.95 + CAPEX +16.72 + costos_fijos -3.17. Todo fuera de scope provider.
- Siguiente: `CTS-EXAM` (-12.22), `CTS-CRUCERO` (-10.63), o `SUPPORT_FTE_INPUT_DECISION`.

### 🔬 CTS-001 V2-8 — AUDITORÍA ESTRUCTURAL DEL RESIDUAL COMPLETADA — 2026-06-11

**Status: `CTS_RESIDUAL_STRUCTURAL_AUDIT_COMPLETED`. Residual descompuesto y clasificado.
Solo +34.18 COP/tx fixable sin tocar modules/storage/request (APLICADO en commit siguiente).**

- Descomposición verificada: **Payroll -200.45** + **No-payroll +85.50** = -114.95.
- **CORRIGE doc INPUT_DEAL_MATCH**: el "CAPEX month-1 +119.72" era falso. No-payroll real =
  OPEX Fijo **+71.95** (backend>Excel, dominante) + CAPEX **+16.72** (Excel también amortiza
  C47=103.04) + CostosFijos -3.17. Fuente: `Vision Cost To Serve`!C46-C48.
- **SENA/Incl base**: Excel `Inputs de Nomina`!C59/C60 = 1,750,905 vs backend 1,423,500.
  `SENA_INPUT_MISMATCH` = FIXABLE_WITH_PROVIDER → APLICADO.
- **Soporte FTE (gap dominante ~-138)**: backend 61.44 FTE vs Excel ≈71.29.
  `STAFFING_FTE_MISMATCH` = requiere modules/ o staffing input.
- examenes -12.22 (CTS-EXAM), crucero -10.63 (CTS-CRUCERO).
- Doc: `docs/refactor/cts_residual_structural_audit_v28.md`.

### ✅ CTS-001 V2-8 — INPUT_DEAL_MATCH APPLIED: PARTIAL_BEST (1.847%) — 2026-06-11

**Status: CTS-001_PARTIAL_BEST. Best: 6,109.62 COP/tx (delta = -114.95, 1.847%). CLOSED.**

- Provider: `tests/refactor/_v28_deal_provider.py` — active HR + `costo_empresa_override`
  for ALL 20 regular staff roles (W39-W58, 'Inputs de Nomina' column W, METROCUADRADO SAC).
- Before: 5,992.50 COP/tx (V27, 3.73%). After: 6,109.62 (1.847%). +117 COP/tx closed.
- Golden test `tests/golden/test_cts_001_v28.py`: uses `build_v28_deal_provider()` for both
  SCB and engine (previously inconsistent V27/active). 2/2 PASS, < 3% gate.
- Residual gap: see `docs/refactor/cts_input_deal_match_v28.md` for full breakdown.
  Payroll -200.45 (SENA/Inclusión salary mismatch) + no-payroll steady-state -34.26 +
  CAPEX month-1 average artifact +119.72 = -114.95 COP/tx net. All require modules/ → STOP.
- Next gap to address: CTS-EXAM (-12.24 COP/tx), CTS-CRUCERO (-10.63 COP/tx), CTS-002.

---

### 🔒 CTS-001 V2-8 — RESIDUAL AISLADO: staff-variable faltante (superseded) — 2026-06-11

**Status: CTS_FTE_AUDIT_BLOCKED. El residual −289.44 COP/tx del nomina_loaded vive 100% en
el COSTO CARGADO de SOPORTE, no en agentes/FTE/headcount/ramp.**

- Agentes: cargado backend 4,189.44 vs Excel 4,189.38 COP/tx → MATCH (260 HC, AM 3.56M).
- Soporte: cargado backend 926.35 vs Excel 1,215.85 → +289.50 = el delta completo.
- Causa: Excel embebe comisión variable de staff en AM (`Inputs de Nomina`!D39=3,868,125
  Director, D46=1,500,000 Jefe Op, D57=700,000 Supervisor). El `request.json` lleva
  `comision_rol=0.0` en los 72 roles → staff variable ausente del cargado backend.
- El 0.70 `pct_cumplimiento_variable` NO mueve el total (nomina_loaded = total_cargado,
  invariante); solo reclasifica fijo↔variable.
- Clasificación: **BLOCKED_MISSING_PARAMETRIZATION_SOURCE** (STAFF_VARIABLE_NOT_IN_LOADED_COST
  + INPUT_DEAL_MISMATCH). Sin fix de motor: el dato no existe en la entrada y NO se toca
  request.json ni se hardcodea.
- Hardcoded nuevos: 0. Golden `test_cts_001_v28.py`: 2/2 PASS. Sin cambio de motor → sin regresión.
- Evidencia: `docs/refactor/cts_fte_headcount_audit_v28.md`, `docs/refactor/cts_001_v28_evidence.md`.
- Siguiente paso: recalcular V2-8 con el deal real de `Condiciones Cadena A` (con comisiones de
  staff) antes de cualquier veredicto numérico CTS-001 — patrón INPUT_DEAL_MISMATCH.

### ✅ CTS-001 V2-8 — VEREDICTO FORENSE: Excel usa PARTICIÓN, NO aditivo — 2026-06-11

**Status: ADDITIVE_HYPOTHESIS_REFUTED. Excel V2-8 NO suma comisión encima del cargado.**

- Veredicto: NO_ADITIVO / NO_DOBLE_CONTEO. El Excel usa modelo de PARTICIÓN, idéntico al backend.
- Evidencia de celdas:
  - `'Inputs de Nomina'!F62 = SUM(C62:D62)` → imponible YA incluye comisión D62=600,000.
  - `'Inputs de Nomina'!W62` (cargado) sobre F62 → factor limpio 1.5147; W62/C62=2.0338 es artefacto.
  - `'Inputs de Nomina'!AM62 = W62` ("Costo Empresa + Comisiones").
  - `'Nomina Loaded'!C43` (línea FIJA, fila 115) = `INDEX(AM...)*conteo − INDEX($C$155:$Q$178...)`
    → usa cargado total y RESTA el bloque variable. NO lo suma encima.
  - `'Nomina Loaded'!C155` (línea VARIABLE, fila 205) = `INDEX('Inputs de Nomina'!D...)*conteo` = comisión raw.
  - Prueba: fija (AM−D=2,960,973.86) + variable (D=600,000) = 3,560,973.86 = AM62 exacto → PARTICIÓN.
- CORRECCIÓN al audit previo (líneas abajo): la afirmación "Excel ADDS raw commission ON TOP of
  the full loaded cost (col AM → row 115)" es FALSA. La fila 115 (fijo) RESTA el bloque variable;
  no lo suma. fija+variable reconstruye el cargado, no lo excede.
- Implicación: NO reescribir nómina a modelo aditivo (introduciría doble-conteo de 600,000/perfil
  inexistente en Excel). El delta CTS-001 residual (−289.44 COP/tx) NO viene de aditivo vs partición;
  esa hipótesis queda DESCARTADA. Re-aislar causa: factor de carga base, conteo FTE/ramp-up,
  denominador, o rubros HR de cargado.
- Documento: `docs/refactor/cts_additive_commission_model_v28.md`.

---

### ✅ CTS-001 V2-8 PARITY — PARTIAL (Bug 2 FIXED + BASELINE REGENERATED) — 2026-06-11

**Status: VARIABLE_COMP_LOAD_APPLIED=DONE. BASELINE_REGENERATED=DONE. CTS-001 delta 8.44% → 3.73%.**

- Decision adopted: variable commission loaded COMPLETE with prestational factor
  (like Excel V2-8); `pct_cumplimiento_variable` (0.70) applied downstream in
  `NominaCalculator._comisiones`, NOT before loading.
- Fix (Bug 2): `NominaCargadaService.calcular` (nomina_cargada.py:117) imponible base
  now `salario_base × (1 + comision_pct)`, matching Excel `Inputs de Nomina!F62=2,350,905`.
- Impact: CTS Cadena A 5,699.51 → 5,992.50 (delta -525.07 → -232.07 COP/tx).
- Residual 3.73% = Bug 1 (per-line variable carga split) + examenes/crucero.
  CORRECTION: NO prestational factor mismatch exists. Loaded SAC line matches Excel
  W62=3,560,973.86 exactly; true per-line factor 1.5147 == Excel. 1.5256/1.5699 are
  aggregate artifacts (loaded total / raw-commission base), not real factors. All 14
  prestational rates match Excel V2-8 row 36 exactly. Root cause = FORMULA_IMPLEMENTATION_BUG
  in CTS variable per-line attribution. Audit: docs/refactor/hr_param_factor_prestacional_v28.md.
- Baseline regenerated 2026-06-11: reports/baseline_oficial.json, tests/refactor/ snapshots
  (v0, v1, cadena_c_v1) + anchor values updated. 9/9 baseline snapshot tests PASS.
- make all: PASS. make validate-excel-v28: PASS (6/6, 1 skip).
- Evidence: `docs/refactor/cts_salary_audit_v28.md`, `docs/refactor/cts_001_v28_evidence.md`
- Regeneration doc: `docs/refactor/baseline_regeneration_variable_comp_v28.md`
- Golden gates: test_cts_001_v28.py 2/2 PASS; test_nomina_variable_load_v28.py 2/2 PASS.
- CTS_VARIABLE_SPLIT_AUDIT (2026-06-11) = BLOCKED. The residual is NOT a fixable
  variable-split bug. Backend `salario_fijo = total_cargado − comisiones`
  (nomina.py:174) makes `fijo + variable` INVARIANT to `_comisiones`. Removing the
  0.70 from the variable line reallocates fijo↔variable (494.15→705.92,
  4621.64→4409.86) but leaves `cts_cadena_a` UNCHANGED at 5,992.502271 (verified,
  reverted). The residual lives in the payroll SUBTOTAL: Excel `Nomina Loaded` ADDS
  the raw commission (`Inputs de Nomina`!D62=600,000, col D → row 205) ON TOP of the
  full loaded cost (col AM=W62 → row 115); the backend folds it INTO the loaded total.
  Evidence: `docs/refactor/cts_variable_split_attribution_v28.md`.
- Next: HR_PARAM_FACTOR_PRESTACIONAL = CLOSED. CTS_VARIABLE_SPLIT = BLOCKED (out of
  scope). To close CTS-001 fully → restructure `_salario_fijo` (full loaded, no
  carve-out) + add raw commission on top (Excel AM+D additive model); touches PyG /
  Vision Tarifas / baseline; requires business decision + re-baseline. Or pursue
  CTS-002 / CTS-EXAM / CTS-CRUCERO (smaller secondary gaps).

---

### ⚠️ CTS-001 V2-8 PARITY — prior fallback audit (superseded) — 2026-06-11

**Status: CTS-001_PARTIAL_FALLBACKS_NOT_BLOCKING**

- Commit ed07c42: denominator fixed from 260 FTE → 221,000 tx/mes (Panel!W31). Unit now correct.
- Commit 22df2dd: HR infra scale whitelist normalization. No impact on CTS-001 delta.
- Current delta: backend=5,699.505252, excel=6,224.575126, delta=-525.07 COP/tx (8.44%)
- Golden gate: `tests/golden/test_cts_001_v28.py` — 2/2 PASS (50% tolerance, unit verified)
- Full formula runner: FORMULA_PARITY_FAIL delta=525.07 (strict MAX_DELTA=0.000001)
- **Fallback audit (2026-06-11):** HR-AutRot fallback (0.09/0.07) and OP-Config fallback (0.0088)
  are NOT the delta cause. request.json provides explicit overrides (0.0815/0.065) that match
  Excel Panel!B18-19. `cons_costo_de_financiacion=False` disables financing component in both.
  Evidence: `docs/refactor/cts_001_fallbacks_v28_evidence.md`
- Actual cause: unknown — likely HR salary parametrization values (V2-7 vs V2-8 active provider)
- make all: PASS — no regression
- Next: Compare `costo_fijo_mensual_cadena_a` backend vs Excel `Nomina Loaded` to identify salary gap

---

### ⚠️ FULL_FORMULA_PARITY_GATE_V28 — NOT_ACHIEVED (2026-06-11)

**Status: FULL_FORMULA_PARITY_V28_NOT_ACHIEVED — 4 FORMULA_PARITY_FAIL in comparable checkpoints**

Full coverage gate added: `scripts/v28_full_formula_coverage_runner.py` — inventories all 3030 formulas in output scope sheets, evaluates 14 checkpoints, classifies each.

**Results:**
- Total Excel formulas in scope sheets: 3,030
- Checkpoints evaluated: 14 / Comparable: 8
- MATCH (delta ≤ 0.000001): 1 — IPC ratio mechanism
- BLOCKED_BY_ARCHITECTURE_DELTA: 6 — HME single-base vs backend month-by-month
- FORMULA_PARITY_FAIL: 4:
  - CTS-001: CTS Cadena A — unit mismatch (Excel COP/FTE/month, backend total). After normalization ÷260 FTE still shows 2.8× gap (unresolved)
  - CTS-002: CTS Cadena C — 51.28 COP/tx delta (~1%)
  - CTS ponderado: driven by CTS-001
  - VTM-001: Vision Tarifas total revenue — wrong backend field (cumulative vs monthly base)
- MISSING_BACKEND_MAPPING: 0

**Open items added to backlog:** CTS-001, CTS-002, VTM-001 (see `docs/refactor/v28_backlog.md`)

**Artefactos generados:**
- `docs/refactor/v28_full_formula_inventory.md` — full formula classification (3030 formulas)
- `docs/refactor/v28_full_formula_backend_mapping.md` — comparable checkpoints with delta analysis
- `scripts/v28_full_formula_coverage_runner.py` — executable coverage gate
- `reports/v28_full_formula_coverage_report.json` — machine-readable output (exit 1 on fail)

**Siguiente paso:** CTS-001 investigation (unit normalization), CTS-002 minor fix, VTM-001 field mapping fix. Each requires separate session.

---

### ✅ V28_EXCEL_VALIDATION_GATE_ADDED (2026-06-11)

`make validate-excel-v28` → `scripts/validate_excel_v28.py` — gate real para V2-8.
`make validate-excel` (legado V2-7/bancamia) intacto, NO tocar.
Gate V2-8: PASS (6/6 checks, 1 skip). Checks: input alignment, engine resolve,
OP componente, IPC ratio m7/m6 (V2-7 provider, delta=0.0), CAPEX activo, Cadena C activo.
HME: SKIP (SKIPPED_OLD_EXCEL_CACHE_NOT_COMPARABLE).

### ✅ EXCEL_V28_PARITY — BASE_INGRESO_MISMATCH FORMULA FIX APPLIED (2026-06-11)

**Status: FORMULA_STRUCTURE_ALIGNED — absolute parity pending INPUT_DEAL_MISMATCH (ACCEPTED_ARCHITECTURAL_DELTA)**

- **Option B-revisada implemented:** `PyGCalculator` now computes `ingreso_cadena = costo_total_cadena / factor_billing` where `costo_total = costo_opex + ICA + GMF + pólizas + ComAdm + fin`. Matches HME!C258→C296 chain structure.
- **IPC mechanism:** MATCH — ratio M7/M3 = 1.05547729 (delta=0.0000000000)
- **Residual delta ~18%:** INPUT_DEAL_MISMATCH — Excel HME cached with different deal. ACCEPTED_ARCHITECTURAL_DELTA.
- **Tests:** 168 passed (1 skipped). All golden/refactor suites green.
- **KPI updated:** `utilidad_neta_total` = 16,523,925,793.77, `pct_utilidad_neta_total` = 0.24558
- **New golden test:** `tests/golden/test_hme_two_pass_revenue_base_v28.py` — 5/5 PASS
- **Artefactos:** `docs/refactor/hme_two_pass_solver_evidence.md`, `docs/refactor/v28_backlog.md` (BASE_INGRESO_MISMATCH → CLOSED)
- **Commits pending:** pyg_calculator.py, costos_financieros/calculator.py, models/results.py, snapshots, golden tests
- **Siguiente paso:** Commit changes (see below)

---

### ✅ EXCEL_V28_PARITY — APPLICABLE PLAN COMPLETE (2026-06-11)

**Status: CLOSED — V2-8 applicable work complete. Last commit: `60b69a2`**

- **Paso B:** COMPLETED — 15 commits aplicados (14 VALUE_UPDATE/STRUCTURE_EXTENSION + 1 polizas flags).
  - Panel de Control: 11 VALUE_UPDATE + 4 STRUCTURE_EXTENSION → todos aplicados.
  - Pólizas pct (EXCEL_LIKELY_BUG): Cumplimiento/Salarios/Calidad → corregidos (Panel canónico).
  - Pólizas activa flags (PASO-B-POLIZAS-FLAGS): 6 flags True→False → aplicados (campo CONSUMED verificado).
  - 63/63 goldens estables durante todo Paso B.
- **Stage 2 T3 (Vision Tarifas):** NO_DELTA para deal referencia (contingencias=0).
- **Stage 2 T2 (Cadena C CAPEX factor):** DEFERRED — kill-switch: rompe 8 goldens V2-7; requiere goldens V2-8 numéricos.
- **Stage 2 T1 (P&G indexación IPC):** DEFERRED — kill-switch: INPUT_DEAL_MISMATCH + wiring tabla Tasas requerido.
- **INPUT_DEAL_MISMATCH:** DEFERRED — decisión de negocio (servicio/cliente/tipo_cliente/fecha_inicio). → Resuelto en commit `66e9ae8` (Option B).
- **Snapshot debt / GOLDEN-001:** ACCEPTED_DEBT (2 failures preexistentes en tests/refactor/; 42 goldens v27 bajo productiva 2026).
- **Pendientes activos:** 0
- **Artefactos:** `docs/refactor/v28_plan_status.md`, `docs/refactor/v28_backlog.md`, `docs/refactor/audit_polizas_activa_flag.md`, `docs/refactor/golden_drift_v28_paso_b.md`
- **Siguiente paso:** iniciar fase separada solo cuando haya decisión de negocio (INPUT_DEAL_MISMATCH) o goldens V2-8 numéricos disponibles (Stage 2 T1/T2).

---

### ✅ SHARED_RESIDUAL_SHIMS_REMOVED + EXCEL_PARITY_CONFIRMED (2026-06-10)

**Status: CLOSED**

- **Objetivo:** Eliminar 12 shims/adapters residuales de `modules/shared/` y confirmar paridad Excel.
- **Eliminados:** `shared/models/{panel,visions_tarifas,visions}.py`, `shared/use_cases/{audit_simulation,certified_calculation}.py`, `shared/helpers/certified_helpers.py`, `shared/infrastructure/{app_settings,business_rules_loader,config,middlewares}.py`, `shared/certification/`, `shared/persistence/`
- **Diferido permanente:** `shared/models/results.py` (serialización, persistencia, contratos API — adapter mantenido intencionalmente)
- **Permitido:** `shared/models/__init__.py` como surface aggregator único
- **Imports actualizados:** 33 archivos en modules/ y tests/ apuntan a rutas canónicas
- **Guardrails:** 58/58 passing — `TestResidualShimsDeleted` (12 ratchets), `_ALLOWED_ADAPTER_FILES` reducido a `{"models/__init__.py"}`
- **Tests:** 2186 pass / 92 fail pre-existentes / 0 regresiones nuevas
- **Excel parity:** `make validate-excel` bloqueado por script legado (`backend_nexa.adapters` pre-FASE 8B); no es regresión del cleanup. Proxy: 158/158 golden+refactor PASSED; 21/21 baseline PASSED; golden cadena_c PASSED.
- **Commits:** `c31dcda` (ownership inversion), `0ae175e` (remove residual shims)
- **Riesgo:** BAJO — solo cambios de import paths, sin lógica productiva ni contratos

---

### ✅ FORMULA_REFACTOR_PHASE10_VISION_IMPRIMIBLE: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Objetivo:** Auditar y mejorar trazabilidad mínima de Vision Imprimible (composición final) sin cambiar fórmulas, composición ni contratos
- **Archivo auditado:** 1 (VisionImprimibleBuilder en modules/vision_imprimible/builders/vision_imprimible_builder.py)
- **Bloques identificados:** 10 (ficha_deal, economics, config_comercial, evolucion, comparativo, vision_servicio, vision_canal, detalle_canal, estructura_equipo, resultado)
- **Cambios:** Agregadas constantes internas `FORMULA_ID` (10 constantes: FICHA_DEL_DEAL, ECONOMICS_DEAL, CONFIGURACION_COMERCIAL, EVOLUCION_MENSUAL, COMPARATIVO_ESCENARIOS, VISION_SERVICIO, VISION_POR_CANAL, DETALLE_POR_CANAL, ESTRUCTURA_EQUIPO, VISION_IMPRIMIBLE_RESULTADO)
- **Refactor:** Decisión conservadora — composición pura perfecta; solo constantes internas
- **Validación:** 162/162 tests PASSED (80 obligatorios + 82 vision_imprimible-specific)
  - ✅ 12 contract/fix tests
  - ✅ 5 baseline v1 tests
  - ✅ 5 baseline cadena_c tests
  - ✅ 58 golden parity tests
  - ✅ 31 test_vision_imprimible_ownership tests
  - ✅ 27 test_vision_imprimible_aprobaciones tests
  - ✅ 9 test_vision_imprimible_db_provider tests
  - ✅ 15 test_vision_imprimible_persisted_contract tests
- **Paridad:** 100% (sin drift contra baselines v1 y cadena_c_v1)
- **Riesgo:** CERO (cambio aditivo-only: constantes internas, sin uso en runtime, no alteran output)
- **Confirmación:** VisionImprimibleBuilder importado desde engine.py; cero impacto en métodos de construcción, composición ni DTOs
- **Artefactos:** docs/refactor/formula_refactor_phase10_vision_imprimible.md
- **Next:** Crear PR para main o PHASE11+

---

### ✅ FORMULA_REFACTOR_PHASE9_COST_TO_SERVE: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Objetivo:** Auditar y mejorar trazabilidad mínima de Cost To Serve (Capa 9) sin cambiar fórmulas, cálculos ni contratos
- **Archivo auditado:** 1 (CostToServeCalculator en modules/vision_cost_to_serve/services/cost_to_serve_calculator.py)
- **Bloques identificados:** 13 (denominador_cadena_a/b/c, costo_cadena_a/b/c, costo_ponderado, desglose_a/b, canales_detalle, participacion_a/b/c)
- **Cambios:** Agregadas constantes internas `FORMULA_ID` (13 constantes: DENOMINADOR_CADENA_A, DENOMINADOR_CADENA_B, DENOMINADOR_CADENA_C, COSTO_CADENA_A, COSTO_CADENA_B, COSTO_CADENA_C, COSTO_PONDERADO, DESGLOSE_CADENA_A, DESGLOSE_CADENA_B, CANALES_DETALLE, PARTICIPACION_A, PARTICIPACION_B, PARTICIPACION_C)
- **Refactor:** Decisión conservadora — código excepcional bien estructurado; solo constantes internas
- **Validación:** 110/110 tests PASSED (80 obligatorios + 30 cts-specific)
  - ✅ 12 contract/fix tests
  - ✅ 5 baseline v1 tests
  - ✅ 5 baseline cadena_c tests
  - ✅ 58 golden parity tests
  - ✅ 30 test_cost_to_serve_golden_v27 tests
- **Paridad:** 100% (sin drift contra baselines v1 y cadena_c_v1)
- **Riesgo:** CERO (cambio aditivo-only: constantes internas, sin uso en runtime, no alteran output)
- **Confirmación:** CostToServeCalculator importado desde engine.py; cero impacto en denominadores, costos, desglose ni canales_detalle
- **Artefactos:** docs/refactor/formula_refactor_phase9_cost_to_serve.md
- **Next:** PHASE10+ o crear PR para main

---

### ✅ CLEANUP_VISION_PYG_DEAD_CODE: COMPLETADO (2026-06-06)

**Status: CLOSED — ELIMINACIÓN EXITOSA**

- **Objetivo:** Eliminar `modules/vision_pyg/` (legacy dead code confirmado en auditoría anterior)
- **Eliminación:** 8 archivos, 1,197 líneas removidas completamente
- **Archivos eliminados:** __init__.py, builder.py, costos_totales.py, kpis.py, reglas.py, vision_pyg_60m.py, api/__init__.py, api/router.py
- **Validación post-cleanup:** 101/101 tests PASSED
  - ✅ 12 contract/fix tests
  - ✅ 5 baseline v1 tests
  - ✅ 5 baseline cadena_c tests
  - ✅ 58 golden parity tests
  - ✅ 21 pyg-specific tests
- **Paridad:** 100% (sin drift contra baselines v1 y cadena_c_v1)
- **Confirmación:** Cero impacto en runtime, tests, API, outputs
- **Riesgo:** CERO (auditoría previa confirmó zero dependencias)
- **Artefactos:** docs/refactor/vision_pyg_dead_code_cleanup.md
- **Next:** Crear commit cuando esté listo para PR

---

### ✅ CLEANUP_VISION_PYG_DEAD_CODE_AUDIT: AUDITADO (2026-06-06)

**Status: AUDIT COMPLETO — PROCEDER CON CLEANUP**

- **Objetivo:** Validar si `modules/vision_pyg/` puede eliminarse sin romper runtime, tests ni API
- **Búsqueda:** Imports runtime, imports en tests, registración de router, referencias en docs
- **Hallazgo principal:** `modules/vision_pyg/` es **COMPLETAMENTE HUÉRFANO** (zero dependencias)
  - ❌ NO hay imports runtime directo
  - ❌ NO hay imports en tests
  - ❌ Router NO está registrado en FastAPI
  - ✅ Doc references son al modelo `vision_pyg` (DTO), no al módulo
- **Contenido:** 8 archivos, 1,197 líneas (duplicados desactualizados de modules/pyg/)
- **Estado de archivos:** DEAD_CODE (todos 8 archivos marcados para DELETE)
- **Riesgo:** CERO (sin dependencias activas)
- **Plan:** Crear branch cleanup/remove-vision_pyg-legacy, eliminar carpeta, ejecutar 101 tests
- **Tests esperados post-cleanup:** 101/101 PASSED (mismo baseline que PHASE6)
- **Artefactos:** docs/refactor/vision_pyg_dead_code_cleanup_audit.md
- **Next:** Crear branch cleanup cuando PHASE6 sea merged (opcional, no bloqueante)

---

### ✅ FORMULA_REFACTOR_PHASE6_PYG: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Objetivo:** Auditar y mejorar trazabilidad mínima de PyG/KPIs/VisionPyG sin cambiar fórmulas, cálculos ni contratos
- **Archivos auditados:** 3 (PyGCalculator, KPIsCalculator, VisionPyGBuilder)
- **Bloques identificados:** 8 (PyG: ingresos×3, costos, contribución, margen, acumuladores) + 5 (KPIs: tarifa, facturación, margen_mínimo) + 7 (VisionPyG: estaciones, filas×25, detalle×4, fechas)
- **Cambios:** Agregadas constantes internas `FORMULA_ID` (49 constantes totales: 19 PyG + 15 KPIs + 15 VisionPyG)
- **Refactor:** Decisión conservadora — código limpio; solo constantes internas
- **Validación:** 101/101 tests PASSED (12 contract + 5 baseline_v1 + 5 cadena_c + 58 golden + 21 pyg_specific)
- **Paridad:** 100% (sin drift contra baselines v1 y cadena_c_v1)
- **Riesgo:** CERO (cambio aditivo-only: constantes internas, sin uso en runtime, no alteran output)
- **Confirmación:** modules/vision_pyg/ NO fue tocado (legacy dead code preservado para cleanup posterior)
- **Artefactos:** docs/refactor/formula_refactor_phase6_pyg.md
- **Next:** CLEANUP FASE (eliminar modules/vision_pyg/) o siguiente fase de auditoría

---

### ✅ FORMULA_REFACTOR_PHASE7_NOMINA: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Objetivo:** Auditar y mejorar trazabilidad mínima de Nómina/Payroll Cadena A (Capa 2) sin cambiar fórmulas, cálculos ni contratos
- **Archivo auditado:** 1 (NominaCalculator en modules/cadena_a/nomina.py)
- **Bloques identificados:** 8 (salario_fijo, comisiones, factor_indexacion, cap_inicial, cap_rotacion, examenes_medicos, seguridad, crucero)
- **Cambios:** Agregadas constantes internas `FORMULA_ID` (13 constantes: SALARIO_CARGADO, SALARIO_FIJO, FACTOR_INDEXACION, COMISIONES, CAPACITACION_INICIAL, CAPACITACION_ROTACION, EXAMENES_MEDICOS, EXAMENES_NUEVOS, EXAMENES_ROTACION, EXAMENES_ANUAL, SEGURIDAD, CRUCERO, TOTAL_MENSUAL)
- **Refactor:** Decisión conservadora — código limpio; solo constantes internas
- **Validación:** 109/109 tests PASSED (80 obligatorios + 29 payroll-specific)
  - ✅ 12 contract/fix tests
  - ✅ 5 baseline v1 tests
  - ✅ 5 baseline cadena_c tests
  - ✅ 58 golden parity tests
  - ✅ 13 test_nomina_cargada tests
  - ✅ 16 test_calculators_nomina tests
- **Paridad:** 100% (sin drift contra baselines v1 y cadena_c_v1)
- **Riesgo:** CERO (cambio aditivo-only: constantes internas, sin uso en runtime, no alteran output)
- **Confirmación:** NominaCalculator importado desde costos_totales_calculator.py y engine.py; cero impacto
- **Artefactos:** docs/refactor/formula_refactor_phase7_nomina.md
- **Next:** PHASE8+ o crear PR para main

---

### ✅ FORMULA_REFACTOR_PHASE8_VISION_TARIFAS: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Objetivo:** Auditar y mejorar trazabilidad mínima de Vision Tarifas/Tarificación (Capa 10) sin cambiar fórmulas, cálculos ni contratos
- **Archivo auditado:** 1 (VisionTarifasCalculator en modules/vision_tarifas/reglas.py)
- **Bloques identificados:** 12 (factor_billing, l50, costos_financieros, tarifa_canal, desglose_cadena, escenarios, tarifa_fte, hora_loggeada, hora_pagada, transaccion, componente_fijo, componente_variable)
- **Cambios:** Agregadas constantes internas `FORMULA_ID` (13 constantes: TARIFA_FTE, TARIFA_HORA_PAGADA, TARIFA_HORA_LOGGEADA, TARIFA_TRANSACCION, COMPONENTE_FIJO, COMPONENTE_VARIABLE, COSTO_CANAL, DESGLOSE_OPEX, DESGLOSE_CAPEX, FACTOR_BILLING, FACTOR_MARGENES, COSTOS_FINANCIEROS, ESCENARIO_COMERCIAL)
- **Refactor:** Decisión conservadora — código bien estructurado con mixins; solo constantes internas
- **Validación:** 108/108 tests PASSED (80 obligatorios + 28 tarifa-specific)
  - ✅ 12 contract/fix tests
  - ✅ 5 baseline v1 tests
  - ✅ 5 baseline cadena_c tests
  - ✅ 58 golden parity tests
  - ✅ 28 test_vision_tarifas_golden_v27 tests
- **Paridad:** 100% (sin drift contra baselines v1 y cadena_c_v1)
- **Riesgo:** CERO (cambio aditivo-only: constantes internas, sin uso en runtime, no alteran output)
- **Confirmación:** VisionTarifasCalculator importado desde engine.py; cero impacto en mixins
- **Artefactos:** docs/refactor/formula_refactor_phase8_vision_tarifas.md
- **Next:** PHASE9+ o crear PR para main

---

### ✅ PYG_ACTIVE_OWNERSHIP_CONFIRMATION: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Objetivo:** Determinar qué archivos PyG son runtime activo antes de FORMULA_REFACTOR_PHASE6_PYG
- **Búsqueda:** Imports en engine.py, app, routers; cero referencias de modules/vision_pyg en runtime
- **Hallazgo principal:** modules/vision_pyg/ es **DEAD CODE CONFIRMADO** (8 archivos legacy, 0 consumidores)
- **Activo identificado:** modules/pyg/ con 4 servicios + 2 builders (7 archivos, todos consumidos en runtime)
- **PHASE6 scope:** PyGCalculator + KPIsCalculator + VisionPyGBuilder (3 archivos principales)
- **Artefactos:** docs/refactor/pyg_active_ownership_confirmation.md
- **Riesgo:** BAJO (patrón FORMULA_ID probado en PHASE1-5)
- **Next:** FORMULA_REFACTOR_PHASE6_PYG (cuando se requiera) ✅ EJECUTADO

---

### ✅ FORMULA_REFACTOR_PHASE5_COSTOS_TOTALES: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Objetivo:** Auditar y mejorar trazabilidad mínima de CostosTotalesCalculator (Capa 7) sin cambiar lógica
- **Auditoría:** Patrón orquestador puro — coordina 4 calculadores (Nomina, NoPayroll, CadenaBCalculator, CadenaCCalculator)
- **Cambios:** Agregadas constantes internas `FORMULA_ID` (5 constantes: PAYROLL_A, NO_PAYROLL_A, COSTO_B, COSTO_C, TOTAL_MENSUAL)
- **Refactor:** Decisión conservadora — código limpio; solo constantes internas
- **Validación:** 80/80 tests PASSED (12 contract + 5 baseline_v1 + 5 cadena_c + 58 golden)
- **Paridad:** 100% (sin drift contra baselines v1 y cadena_c_v1)
- **Riesgo:** BAJO (cambio mínimo: constantes internas, sin uso en runtime, no alteran output)
- **Artefactos:** docs/refactor/formula_refactor_phase5_costos_totales.md
- **Next:** FORMULA_REFACTOR_PHASE6_PyG o CLEANUP FASE

---

### ✅ FORMULA_REFACTOR_PHASE4_CADENA_C: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Objetivo:** Auditar y mejorar trazabilidad mínima de CadenaCCalculator (Capa 6) sin cambiar fórmulas
- **Auditoría:** 7 bloques bien estructurados (canales, opex_fijo, opex_var, inversiones, equipo, escalamiento, HITL)
- **Cambios:** Agregadas constantes internas `FORMULA_ID` (8 constantes: CANALES, EQUIPO_TRANSVERSAL, INVERSION_ANUAL, OPEX_FIJO_INTEGRACION, OPEX_VARIABLE_INTEGRACION, ESCALAMIENTO, HITL, TOTAL_MENSUAL)
- **Refactor:** Decisión conservadora — código limpio; solo constantes internas
- **Validación:** 80/80 tests PASSED (12 contract + 5 baseline_v1 + 5 cadena_c + 58 golden)
- **Paridad:** 100% (snapshot cadena_c_v1 bit-by-bit match + costo_c mes1 = 101.2M)
- **Riesgo:** BAJO (cambio mínimo: constantes internas, sin uso en runtime, no alteran audit_trace)
- **H-05/H-08 FIX:** cop_round per-channel y total intacto
- **Artefactos:** docs/refactor/formula_refactor_phase4_cadena_c.md
- **Next:** FORMULA_REFACTOR_PHASE5_COSTOS_TOTALES o CLEANUP FASE

---

### ✅ CADENA_C_ACTIVE_BASELINE_PREP: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Objetivo:** Preparar baseline oficial para Cadena C activa (IA/Automation)
- **Problema:** request.json canónico tiene Cadena C desactivada (costo_c=0)
- **Solución:** Creado request_cadena_c_active.json con Cadena C configurada
- **Canales:** 2 canales IA (Chatbot Inbound 15k vol + RPA Outbound 8k vol)
- **Equipo:** IA Engineer (100%) + Data Scientist (50%) + OPEX infraestructura
- **Costo_c mes1:** 101,200,000.0 (activo, no cero)
- **Costo_c total:** 2,491,534,080.0 (24 meses)
- **Artefactos:**
  - ✅ request_cadena_c_active.json (fixture)
  - ✅ baseline_formula_snapshot_cadena_c_v1.json (snapshot)
  - ✅ test_baseline_formula_snapshot_cadena_c_v1.py (test fixture con 5 tests)
- **Validación:** 80/80 tests PASSED (12 contract + 5 v1 + 5 cadena_c + 58 golden)
- **Paridad:** 100% (snapshot parity + anchor values + costo_c > 0)
- **Riesgo:** BAJO (fixture adicional, no modifica request.json canónico)
- **Next:** FORMULA_REFACTOR_PHASE4_CADENA_C (cuando esté listo)

---

### ✅ FORMULA_REFACTOR_PHASE3_COSTOS_FINANCIEROS: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Auditoría:** CostosFinancierosCalculator contiene 8 componentes (financiación, pólizas, ICA, GMF, comisión adm, per-cadena distribution)
- **Cambios:** Agregadas constantes internas `FORMULA_ID` para trazabilidad (8 constantes: FINANCIACION, POLIZAS, ICA, GMF, COMISION_ADMINISTRACION, POLIZAS_PER_CADENA, ICA_PER_CADENA, GMF_PER_CADENA)
- **Refactor:** Decisión conservadora — código bien estructurado; solo constantes internas
- **Validación:** 90/90 tests PASSED (12 contract + 5 baseline_v1 + 58 golden + 13 costos_financieros + 2 polizas)
- **Baseline v1:** Creado test_baseline_formula_snapshot_v1.py (oficial post-canonicalization); regenerado baseline_formula_snapshot_v1.json
- **Paridad:** 100% (snapshot v1 bit-by-bit match + KPI anchors rel_tol=1e-9)
- **Riesgo:** BAJO (cambio mínimo: constantes internas, sin uso en runtime, no alteran audit_trace)
- **Gross-up:** ICA intacto (base = costo/fm + polizas + fin); GMF intacto (base = costo + polizas + fin)
- **ComAdm:** Aplica solo Cadena A; H-07 cop_round intacto
- **Next:** Aplicar patrón análogo a Cadena C o continuar con otras fases

---

### ✅ FORMULA_REFACTOR_PHASE2_CADENA_B: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Auditoría:** CadenaBCalculator contiene 8 componentes bien estructurados (factor, volúmenes, 6 costos)
- **Cambios:** Agregadas constantes internas `FORMULA_ID` para trazabilidad (7 constantes: OPEX_FIJO, INVERSIONES, SOPORTE_MANTENIMIENTO, COSTO_VARIABLE, ESCALAMIENTO, HITL, FACTOR_PERSONAL)
- **Refactor:** Decisión conservadora — código ya está limpio; solo constantes internas
- **Validación:** 75/75 tests PASSED (12 contract + 5 baseline + 58 golden)
- **Paridad:** 100% (costo_b mes1, payroll_a mes1, utilidad_neta_total sin cambios)
- **Riesgo:** BAJO (cambio mínimo: constantes internas, sin uso en runtime, no alteran rounding H-05/H-08)
- **Rounding:** H-05 (variable/escalamiento por canal) y H-08 (SM/HITL total) intactos
- **Cadena B:** Fluye (costo_b mes1 = 39,503,127.41)
- **Next:** Aplicar patrón análogo a Cadena C o continuar con otras fases

---

### ✅ FORMULA_REFACTOR_PHASE1_NOPAYROLL: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Auditoría:** NoPayrollCalculator contiene 8 bloques bien estructurados (overrides, estaciones, costos)
- **Cambios:** Agregadas constantes internas `FORMULA_ID` para trazabilidad (cero impacto en output)
- **Refactor:** Decisión conservadora — no refactorizar código ya limpio; solo mejorar trazabilidad
- **Validación:** 81/81 tests PASSED (12 contract + 5 baseline + 58 golden + 6 other)
- **Paridad:** 100% (costo_b mes1, payroll_a mes1, utilidad_neta_total, pct_utilidad sin cambios)
- **Riesgo:** BAJO (cambio mínimo: constantes internas, sin uso en runtime, no alteran audit_trace)
- **Cadena B:** Fluye (costo_b mes1 = 39,503,127.41)
- **Next:** Aplicar patrón análogo a Cadena B o continuar con otras fases

---

### ✅ INPUT_CONTRACT_CANONICALIZATION_1_CLOSEOUT: COMPLETADO (2026-06-06)

**Status: CLOSED**

- **Contrato canónico:** `request/request.json` en formato plano (A/B/C sin wrapper redundante)
- **Backend:** `user_input_loader.py` normaliza ambos formatos (plano + legacy anidado)
- **Equivalencia:** tests validaron que plano == anidado en output (rel_tol=1e-9)
- **Baseline v1:** `tests/refactor/baseline_formula_snapshot_v1.json` es baseline oficial post-fix
- **Code changes:** SOLO normalización de entrada, NO fórmulas/cálculos/CTS/frozen
- **Tests cierre:** 81/81 PASSED (refactor + golden suites)
- **Cadena B:** fluye (costo_b mes1 = 39,503,127.41)
- **Next:** Proceder a FORMULA_REFACTOR_PHASE1_NOPAYROLL con baseline v1 oficial

### Code Impact Summary

- Modified: `user_input_loader.py` (`_normalizar_entry_data_format` guards cadena_a ~344, cadena_b ~397)
- Modified: `request/request.json` (canonicalized flat format)
- Modified: `validation/contract_validator.py` (volumetria-derived canales accepted)
- Untouched: All formulas, calculators, DTOs, frozen, CTS, contracts

### Artifacts

- `docs/refactor/canonicalization_closeout_code_changes.md`
- `docs/refactor/baseline_state.md`
- `docs/refactor/equivalence_validation.md`
- `docs/refactor/entrypoint_notes.md`
- `docs/refactor/CLOSEOUT_REPORT.md`
- `tests/refactor/baseline_formula_snapshot_v1.json`

---

### ✅ INPUT_CONTRACT_FIX_B1: COMPLETADO (2026-06-06)

- **D-1 bug:** Cadena B no fluía por doble anidamiento `condiciones_cadena_b.condiciones_cadena_b`.
  Confirmado y corregido.
- **Fix:** `user_input_loader.py` `_normalizar_entry_data_format` — unwrap guard añadido
  (análogo al guard existente para `condiciones_cadena_a` en línea 346).
- **Adapter:** `NewEntryDataAdapter` sin cambios (correcto para datos planos).
- **Baseline 1:** Regenerado. `costo_b mes1 = 39.503.127,41` (era 0).
- **Tests:** 7/7 PASSED (`tests/refactor/test_input_contract_fix_b1.py`).
- **Golden:** 58/58 PASSED (sin regresiones).
- **Contratos públicos:** sin cambios.
- **Snapshot:** `tests/refactor/baseline_formula_snapshot_v0.json` actualizado a Baseline 1.
- **Next:** Proceder a refactor de no_payroll con Baseline 1 como base.

---

### ✅ FORMULA_REFACTOR_BASELINE_0: COMPLETADO (2026-06-06)

Línea base confiable del motor establecida ANTES de reorganizar fórmulas.

- Motor ejecuta `request/request.json` (Bancamia Cobranzas, 24m) sin errores.
  PricingResult válido (22 claves, pyg 24 meses, todas las visiones completas).
- Parametrización activa: v2-7 (HR/GN/OP/business_rules).
- Guardrails: `tests/refactor/test_baseline_formula_snapshot_v0.py` → 5/5 PASSED.
- Golden/parity: `tests/golden/` → 58/58 PASSED.
- Snapshot congelado: `tests/refactor/baseline_formula_snapshot_v0.json`.
- Comparación Excel V2-7: constantes deal-independientes en paridad exacta;
  agregados NO_COMPARABLE (Excel cacheado para otro deal: Americas/Captura
  de Datos/12m).
- **Divergencia D-1 (BUG TÉCNICO, no corregido):** Cadena B no fluye (costo_b=0)
  por doble anidamiento `condiciones_cadena_b.condiciones_cadena_b` no detectado
  por NewEntryDataAdapter. Requiere decisión de negocio sobre el contrato.
- Primera fase recomendada: **no_payroll** (más aislada, riesgo bajo, no
  bloqueada por D-1).
- Código productivo, contratos y Excel runtime: intactos. Sin commit.

Artefactos: `docs/refactor/formula_refactor_baseline_0*.{md,json}`.
Próximo paso: proceder con Fase 1 (no_payroll) corriendo guardrails antes/después;
escalar D-1 a backend-agent en paralelo.

---

### ✅ WORKER CONFIGURATION VALIDATION PHASE: COMPLETED AND VALIDATED

**Phase scope: Worker system validation only**

**Worker configuration: ✅ VALIDATED (2026-06-06)**
- **12 specialized agents** configured and verified (coordinator, scanner, cleanup, backend, qa, architecture, security, infra, business-rules, frontend, docs, reviewer)
- Each has: unique name, clear description, correct model (haiku/sonnet/opus), minimal tools
- **3 generic agents** present (design, explore, implement) as documented fallback
- Frontmatter structure: consistent YAML format with `name`, `description`, `tools`, `model`
- Priority documented in CLAUDE.md: specialized agents before fallback

**Functional code changed by this phase: NO** — only configuration and AI context files modified
**Tests executed during this phase: NO** — validation was file-based only
**Command `/agents`: Unavailable** — file-based validation required and completed

**Cambios introducidos en esta fase (worker validation):**
- `CLAUDE.md` — nuevos (Workers section added)
- `docs/ai/TASK_STATE.md` — actualizado (worker config status)
- `docs/ai/VALIDATION.md` — actualizado (worker validation commands and results)

---

**⚠️ GLOBAL WORKING TREE STATUS: UNCLEAN (PRE-EXISTING CHANGES)**

Cambios funcionales pre-existentes pendientes de clasificación y commit:
- `api/v1/router.py` — modificado (pre-existing, not from worker-validation phase)
- `app.py` — modificado (pre-existing, not from worker-validation phase)
- `modules/cadena_a/api/chain_a_router.py` — modificado (pre-existing)
- `modules/cadena_b/api/chain_b_router.py` — modificado (pre-existing)
- `modules/cadena_c/api/chain_c_router.py` — modificado (pre-existing)
- `modules/panel/api/panel_router.py` — modificado (pre-existing)

Nuevos archivos de contexto/tests pre-existentes:
- `tests/db/`, `tests/golden/`, `tests/refactor/`, `docs/refactor/` — cambios previos a esta fase

**NOTA:** Worker validation phase NO introduced these changes. They are pre-existing on branch `refactor/modular-pure`.

## Última tarea completada
1. Lectura de CLAUDE.md, PROJECT_CONTEXT.md, VALIDATION.md, ROUTING_MATRIX.md
2. Validación exhaustiva de todos los archivos .claude/agents/*.md
3. Confirmación: sistema de workers correctamente configurado

---

### ✅ TARGETED VALIDATION COMPLETED (2026-06-06)

**Validación dirigida por categoría: ALL PASSED** 🎯

- ✅ API contract/runtime fix: 12/12 PASSED
- ✅ Vision DB provider: 9/9 PASSED  
- ✅ Vision persisted contract: 15/15 PASSED
- ✅ Golden/Parity tests: 58/58 PASSED (30 CTS + 28 VT)
- ✅ Parametrization source policy: 6/6 PASSED

**Total: 100/100 tests PASSED** (1 deselected = cosmos_integration)

**Status:** Repository ready for commit separation by category. No regressions detected.

---

## Pendientes
- Ejecutar full suite solo después de commits separados (para auditar por categoría)
- Scanner-agent clasificó 21 archivos únicos en 6 categorías
- 7 commits propuestos, listos para separación

## Cambios sin commit por categoría

| Categoría | Archivos | Tests | Status |
|-----------|----------|-------|--------|
| AI/Claude config | CLAUDE.md, docs/ai/ | N/A | VALIDATED (config) |
| API contract fix | 6 routers + 1 test | 12 | **100% PASSED** ✅ |
| Vision DB provider | 2 tests | 24 | **100% PASSED** ✅ |
| Golden/Parity | 2 tests + fixtures | 58 | **100% PASSED** ✅ |
| Parametrization policy | 1 test + doc | 6 | **100% PASSED** ✅ |
| Documentation | 3 .md files | N/A | AUDIT DOCS |

## Fallos conocidos
- `tests/test_parametrization_phase_1_2.py` — excluido permanentemente (ImportError de módulo legacy desaparecido).
- Tests `cosmos_integration` requieren `azure-cosmos` instalado y credenciales; excluidos del default run (1 deselected).

---

### ✅ CLAUDE WORKERS SYSTEM VALIDATION (2026-06-06)

Worker system validation: PASSED
Validation scope: Claude workers/config only
/agents availability: unavailable; file-based validation used
Functional repo files reviewed: NO
Backend tests executed: NO
Working tree classified: NO
Routing simulation: PASSED

## Próxima acción recomendada
Proceder con separación de commits por categoría en orden propuesto. Claude Code workers y routing están validated y ready.
