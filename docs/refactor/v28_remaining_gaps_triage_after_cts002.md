# V28 Remaining Gaps Triage After CTS-002 Closure

> **Sesión:** triage post-CTS-002 · Fecha: 2026-06-12 · Rama: `refactor/modular-pure`
> **Commit base:** `24743c0` (docs: close CTS-002 Cadena C parity)
> **Modo:** READ-ONLY + DOCS-ONLY — 0 cambios en modules/, request/, storage/, tests/, contracts/.
>
> **UPDATED 2026-06-12:** E95 + V27 fixture regen completed. Golden suite: **0 fail / 96 pass** ✅

---

## Current validation state (post-V27_FIXTURE_REGEN, 2026-06-12)

| Gate | Result |
|------|--------|
| `make validate-excel-v28` | **PASS 6/6** ✅ |
| `test_cts_001_v28.py` | 2/2 PASS — CTS-001 PAUSED_KNOWN_DELTA |
| `test_cts_exam_crucero_v28.py` | 2/2 PASS |
| `test_pyg_v28_ingreso_indexado.py` | 7/7 PASS |
| `test_support_fte_v28.py` | 9/9 PASS |
| `test_cost_to_serve_golden_v27.py` | **30/30 PASS** ✅ |
| `test_vision_tarifas_golden_v27.py` | **41/41 PASS** ✅ |
| **Full golden suite** | **0 fail / 96 pass** ✅ |
| `make verify` | ✅ Baseline match. Sin drift. |

**CTS-001:** PAUSED_KNOWN_DELTA — not reopened.
**CTS-002:** FORMALLY_CLOSED — K34 delta = 2.24e-6 (floating-point).
**VTM-001:** CLOSED.

---

## Current golden failure set

### Group A — `test_cost_to_serve_golden_v27.py` (13 failures)

| # | Test | Live | Golden | Delta | Delta% |
|---|------|------|--------|-------|--------|
| 1 | `test_cts_cadena_a` (Aggregate) | 5,912.88 | 5,798.08 | +114.80 | +1.98% |
| 2 | `test_cts_ponderado` (Aggregate) | 45,789.87 | 45,728.27 | +61.60 | +0.13% |
| 3 | `test_desglose_a_nomina_loaded` (Aggregate) | 4,709.43 | 4,612.89 | +96.54 | +2.09% |
| 4 | `test_per_canal_cts[Voz]` | 4,500,081 | 4,405,408 | +94,673 | +2.15% |
| 5 | `test_per_canal_cts[WhatsApp]` | 4,586,799 | 4,477,458 | +109,341 | +2.44% |
| 6 | `test_per_canal_payroll_breakdown[Voz-payroll]` | 3,587,414 | 3,514,742 | +72,672 | +2.07% |
| 7 | `test_per_canal_payroll_breakdown[Voz-nomina_loaded]` | 3,545,327 | 3,472,655 | +72,672 | +2.09% |
| 8 | `test_per_canal_payroll_breakdown[Voz-no_payroll]` | 912,667 | 890,666 | +22,001 | +2.47% |
| 9 | `test_per_canal_payroll_breakdown[Voz-salario_fijo]` | 3,545,327 | 3,472,655 | +72,672 | +2.09% |
| 10 | `test_per_canal_payroll_breakdown[WhatsApp-payroll]` | 3,370,237 | 3,350,092 | +20,145 | +0.60% |
| 11 | `test_per_canal_payroll_breakdown[WhatsApp-nomina_loaded]` | 3,545,327 | 3,472,655 | +72,672 | +2.09% |
| 12 | `test_per_canal_payroll_breakdown[WhatsApp-no_payroll]` | 999,385 | 962,716 | +36,669 | +3.81% |
| 13 | `test_per_canal_payroll_breakdown[WhatsApp-salario_fijo]` | 3,370,237 | 3,350,092 | +20,145 | +0.60% |

**Root cause:** Active OP parametrization was updated in commit `939a36a` (`tasa_financiacion`: 0.0088→0.0153; economic component '20% SMMLV - 80% IPC' added). Both tests use `NexaPricingEngine()` with no explicit param → reads current active storage. Golden values were frozen before the OP update. The cost increase (~2%) propagates from the financial component through to CTS metrics.

### Group B — `test_support_fte_v28.py` (1 failure)

| # | Test | Live | Expected | Delta |
|---|------|------|----------|-------|
| 14 | `test_e95_supervisor_override_applied` | 7.1 FTE | 9.5 FTE | -2.4 FTE |

**Root cause:** `fte_soporte_overrides: {"Supervisor": 9.5}` was removed from `request/request.json` in commit `b8b3000` ("align request values with Excel formula map"). The test expects the override to be present and applied. The formula computes 7.1 = (130+12)/20 (formula with cargos_adicionales). The manual Excel E95 override of 9.5 is no longer in the request. Related uncommitted WIP in `modules/calculator_motor/mixins/user_input_builders_cadena_a.py` and `tests/golden/test_support_fte_v28.py`.

### Group C — `test_vision_tarifas_golden_v27.py` (11 failures)

| # | Test | Live | Golden | Delta | Delta% |
|---|------|------|--------|-------|--------|
| 15 | `test_per_canal_field[Inbound 25-tarifa_fijo_fte]` | 6,424,704 | 6,344,546 | +80,158 | +1.26% |
| 16 | `test_per_canal_field[Inbound 25-ingreso_bruto]` | 229,453,730 | 226,590,943 | +2,862,787 | +1.26% |
| 17 | `test_per_canal_field[Inbound 25-costo_atribuible]` | 181,268,447 | 179,006,845 | +2,261,602 | +1.26% |
| 18 | `test_per_canal_field[Inbound 25-payroll_ch]` | 89,685,349 | 87,868,545 | +1,816,804 | +2.07% |
| 19 | `test_per_canal_field[Inbound 25-no_payroll_ch]` | 24,503,563 | 24,159,791 | +343,772 | +1.42% |
| 20 | `test_per_canal_field[inboun Whatsapp-tarifa_fijo_fte]` | 8,786,854 | 8,668,250 | +118,604 | +1.37% |
| 21 | `test_per_canal_field[inboun Whatsapp-ingreso_bruto]` | 131,802,807 | 130,023,755 | +1,779,052 | +1.37% |
| 22 | `test_per_canal_field[inboun Whatsapp-costo_atribuible]` | 104,124,218 | 102,718,767 | +1,405,451 | +1.37% |
| 23 | `test_per_canal_field[inboun Whatsapp-payroll_ch]` | 53,811,209 | 52,721,127 | +1,090,082 | +2.07% |
| 24 | `test_per_canal_field[inboun Whatsapp-no_payroll_ch]` | 10,051,988 | 9,845,724 | +206,264 | +2.09% |
| 25 | `test_costo_cadena_a_total` | — | — | ~+1.3% | ~+1.3% |

**Root cause:** Same as Group A — active OP parametrization change (tasa_financiacion) increases costs, which propagates through cost-plus to ingreso/tarifa fields. These 11 failures were already documented in `docs/refactor/v28_plan_status.md` after VTM-001: `test_vision_tarifas_golden_v27`: 17 PASS / 11 FAIL. Not new; not blocking validate-excel-v28.

---

## Failure classification

| Test | Failure | Component | Expected | Actual | Delta | Category | Recommended action |
|------|---------|-----------|----------|--------|-------|----------|--------------------|
| CTS_v27 `test_cts_cadena_a` | CTS aggregate drift | NexaPricingEngine default param | 5,798.08 | 5,912.88 | +1.98% | `PREEXISTING_INFRA_PARAMETRIZATION` | Regenerate V27 golden fixtures (separate session) |
| CTS_v27 `test_cts_ponderado` | Weighted CTS drift | NexaPricingEngine default param | 45,728.27 | 45,789.87 | +0.13% | `PREEXISTING_INFRA_PARAMETRIZATION` | Same |
| CTS_v27 `test_desglose_a_nomina_loaded` | Nomina loaded drift | NominaCalculator via active OP | 4,612.89 | 4,709.43 | +2.09% | `PREEXISTING_INFRA_PARAMETRIZATION` | Same |
| CTS_v27 per_canal_cts[Voz] | Per-canal CTS drift | CostToServeCalculator | 4,405,408 | 4,500,081 | +2.15% | `PREEXISTING_INFRA_PARAMETRIZATION` | Same |
| CTS_v27 per_canal_cts[WhatsApp] | Per-canal CTS drift | CostToServeCalculator | 4,477,458 | 4,586,799 | +2.44% | `PREEXISTING_INFRA_PARAMETRIZATION` | Same |
| CTS_v27 payroll_breakdown × 8 | Payroll/nomina/no_payroll/salario | NominaCalculator + NoPayrollCalculator | various | various | ~1-4% | `PREEXISTING_INFRA_PARAMETRIZATION` | Same |
| support_fte `test_e95_supervisor_override_applied` | E95 override not applied | `user_input_builders_cadena_a` | 9.5 FTE | 7.1 FTE | -2.4 | `REQUEST_VALUE_GAP` | Restore `fte_soporte_overrides` to request.json OR commit WIP changes implementing new mechanism |
| VT_v27 per_canal_field × 10 | Tarifa/ingreso/costo drift | VisionTarifasCalculator | various | various | ~1.3-2.1% | `PREEXISTING_INFRA_PARAMETRIZATION` | Regenerate V27 golden fixtures |
| VT_v27 `test_costo_cadena_a_total` | Costo cadena A drift | CostosTotalesCalculator | — | — | ~1.3% | `PREEXISTING_INFRA_PARAMETRIZATION` | Same |

---

## Actionability buckets

| Bucket | Count | Failures | Rationale |
|--------|-------|----------|-----------|
| 1. Do not touch now | 24 | All `PREEXISTING_INFRA_PARAMETRIZATION` (Groups A + C) | V27 frozen goldens; delta from intentional OP parametrization update; not blocking V2-8 goals; test files themselves say "Legitimate causes: parametrization update (regenerate fixtures)." |
| 2. Anchor update only | 0 | — | No anchor-only failures with Excel-backed evidence |
| 3. Requires request fix | 1 | `test_e95_supervisor_override_applied` | `fte_soporte_overrides` removed from request.json in b8b3000; requires restoration OR new mechanism from WIP |
| 4. Requires param/provider fix | 0 | — | None |
| 5. Requires backend formula fix | 0 | — | None (Groups A+C are param-driven, not formula errors) |
| 6. Requires business decision | 0 | — | None |
| 7. Needs deeper RCA | 0 | — | E95 WIP is clear enough once committed |

---

## Top 5 recommended next fronts

| Priority | Front | Type | Reason | Risk | Recommendation |
|----------|-------|------|--------|------|----------------|
| P1 | **E95 Supervisor override — commit WIP** | REQUEST_VALUE_GAP | `test_e95_supervisor_override_applied` failing; unstaged changes in `user_input_builders_cadena_a.py` + `test_support_fte_v28.py` exist but not committed; likely new mechanism replacing `fte_soporte_overrides` | Low — isolated to Cadena A soporte FTE; 0 V2-8 parity gates blocked | Inspect and commit the unstaged WIP in `user_input_builders_cadena_a.py` + `test_support_fte_v28.py`; verify E95=9.5 is re-applied via the new mechanism |
| P2 | **V27 golden fixture regeneration** | PREEXISTING_INFRA_PARAMETRIZATION | 24 of 25 failures resolve by regenerating `tests/golden/fixtures/cts_v27_real_request.json` and `vt_v27_real_request.json` against current active parametrization | Medium — changes 24 golden JSON files; no functional code; must be done in controlled session with current active param frozen | Separate session: `make baseline` equivalent on V27 golden fixture JSONs only; confirm new values are stable |
| P3 | **CTS-001 resumption** | KNOWN_DELTA_CTS001 | Residual -27.53 COP/tx (0.44%) = `CTS_SUPPORT_LOADED_MAGNITUDE`; gap is in loaded salary for support roles; E95 fix (P1) is a prerequisite | High — requires formula analysis + possible provider changes | After P1: re-run CTS-001 tests with E95 applied; measure residual; open dedicated CTS-001 session |
| P4 | **ROLES-OP-STAFFCONFIG gap** | REQUEST_VALUE_GAP | Motor consumes `staff_config[]`, not `roles_operativos[]` from deal; activación JCR/AFAC/GTR divergente vs Excel C79/C80/C87=False | Medium — affects soporte FTE calculation paths | After P1+P2: map which roles engine must consume; reconcile `staff_config` vs `roles_operativos` |
| P5 | **`porcentaje_acumulado.actual` (INPUT-PCT-ACUM)** | REQUEST_VALUE_GAP | request=0.02 vs Panel!C75=0; impact confirmed 0 on CTS; impact on P&G/Tarifas unknown | Low — zero CTS impact already measured; correct value is likely 0 | Map the formula path Panel!C75 → PyG/Tarifas; if impact also 0, close as ACCEPTED |

---

## Known failures not to touch now

**24 failures — `PREEXISTING_INFRA_PARAMETRIZATION`** (Groups A + C):

Root cause shared by all 24: `storage/parametrization/op/` active OP was updated in commit `939a36a`:
- `tasa_financiacion_mensual`: 0.0088 → 0.0153 (+65bp, +74%)
- `'20% SMMLV - 80% IPC'` economic component: added (was missing)

These changes increased the financial cost component for any deal using the active OP, causing ~1.3-2.5% upward drift in nomina/CTS/tarifa metrics. The V27 golden fixtures were frozen before this change and now read stale values.

**Why not fix them now:**
1. Fixing requires regenerating 2 golden fixture JSON files (`cts_v27_real_request.json`, `vt_v27_real_request.json`) — equivalent to partial `make baseline`
2. Not blocking `validate-excel-v28` (PASS 6/6 ✅)
3. Not blocking any V2-8 parity goal
4. Test documentation explicitly says: *"Legitimate causes: parametrization update (regenerate fixtures)."*

---

## Anchor updates required, if any

**None** — no failure can be classified as `ANCHOR_UPDATE_REQUIRED` without Excel V2-8 evidence. All 24 `PREEXISTING_INFRA_PARAMETRIZATION` failures require fixture regeneration (not just anchor updates), which is a separate controlled operation.

---

## Real V2-8 gaps requiring future RCA/fix

None identified from the 25 failures. All failures are either:
1. Frozen V27 goldens drifted by legitimate parametrization update (24 failures)
2. Work-in-progress request gap (1 failure)

The next real V2-8 gap candidates from backlog (not reflected in golden failures):
- `CTS-001` residual -27.53 COP/tx (PAUSED_KNOWN_DELTA) — `CTS_SUPPORT_LOADED_MAGNITUDE`
- `ROLES-OP-STAFFCONFIG` — `staff_config` vs `roles_operativos` consumption mismatch
- `INPUT-PCT-ACUM` — `porcentaje_acumulado.actual` = 0.02 vs Panel!C75=0 (P&G impact unmapped)

---

## Recommended next action

**Immediate (P1):** Inspect unstaged changes in `modules/calculator_motor/mixins/user_input_builders_cadena_a.py` and `tests/golden/test_support_fte_v28.py`. These are pre-existing WIP from the CARGOS_ADICIONALES/DETALLES_RECURSOS_HUMANOS alignment. Commit or revert them to restore deterministic baseline. Goal: `test_e95_supervisor_override_applied` passes → 24 fail / 72 pass.

**Short-term (P2):** After active param is stable, regenerate V27 golden fixtures in a controlled session. Goal: 0 fail / 96 pass (or close to it, depending on any remaining real gaps).

**After P2 (P3):** Resume CTS-001 with E95 override restored. Fresh delta measurement from clean baseline.
