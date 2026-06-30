# INPUT-PCT-ACUM Audit After V2-8 Closure

**Date:** 2026-06-12  
**Session:** INPUT_PCT_ACUM_AUDIT_POST_V28_CLOSURE  
**Worker:** backend-agent  
**Status:** ✅ COMPLETED — `NO_IMPACT / RECOMMEND_NO_ACTION`

---

## Baseline Confirmation

| Gate | Result |
|------|--------|
| `tests/golden/` 99/99 | ✅ PASS |
| `make verify` | ✅ PASS — Baseline match. Sin drift. |
| `make validate-excel-v28` | ✅ PASS 6/6 (1 skipped) |
| `CTS-001` | CLOSED_ACCEPTED_DELTA — not touched |
| `CTS-002` | FORMALLY_CLOSED — not touched |
| Functional changes | 0 — read-only audit |

Pre-existing `tests/unit/` failures (61 failed, `storage/`-dependent, `FileNotFoundError` on missing
`storage/parametrization/business_rules/v2-7.json`) are confirmed pre-existing and unrelated to this audit.

---

## Runtime Source Trace

| Concept | Runtime source | Path/field | Current value | Excel expected | Status |
|---------|----------------|------------|---------------|----------------|--------|
| `porcentaje_acumulado.actual` | `request/request.json` | `reglas_negocio.porcentaje_acumulado.actual` | `0` | `Panel!C75 = 0` | `REQUEST_MATCH` |
| `porcentaje_acumulado` in engine | None — DEAD_FIELD | `engine_helpers.py` BUSINESS_RULES_FIX_3 | not consumed | n/a | `NOT_USED` |
| `politicas_comerciales` | `IParametrizationProvider` | provider returns 5 entries | 5 policies, no `porcentaje_acumulado` | n/a | `PROVIDER_MATCH` |

**Key facts:**
- `PanelDeControl` model does not have a `porcentaje_acumulado` field.
- `ReglasNegocio` DTO does not have a `porcentaje_acumulado` field.
- `_calcular_reglas_negocio()` in `engine_helpers.py` explicitly documents: *"porcentaje_acumulado fue eliminado: sin fuente Panel, nunca activo."*
- Active guard: if any provider returns `porcentaje_acumulado` in `politicas_comerciales`, a `ValueError` is raised immediately.
- `request/request.json` field value = 0, matching Excel Panel!C75 = 0.

---

## Excel Source Trace

| Excel cell | Value | Formula | Feeds | Expected runtime source |
|------------|-------|---------|-------|-------------------------|
| `'Panel de Control General'!C75` | `0` | `=SUM(C67:C69)-C70` | **NOTHING** — 0 cross-sheet refs | None (display-only) |
| `C67` (Contingencia Operativa) | `0` | `0` (literal) | Panel display | `panel.op_cont` (consumed individually) |
| `C68` (Contingencia Comercial) | `0` | `0` (literal) | Panel display | `panel.com_cont` (consumed individually) |
| `C69` (Mark up) | `0` | `0` (literal) | Panel display | `panel.markup` (consumed individually) |
| `C70` (Descuento volumen) | `0` | `0` (literal) | Panel display | `panel.descuento` (consumed individually) |

**Verification method:** Exhaustive regex scan of all 20 Excel sheets for any formula containing
`"Panel de Control General"` + `C75`. Result: **0 cross-sheet references** to `Panel!C75`.

`Panel!C75` is a **display-only derived cell**: it summarizes C67+C68+C69−C70 for the user's
visual reference only. It is not used as input by any calculation sheet.

The individual component cells (C67–C70) are consumed individually by the backend via
`PanelDeControl.op_cont`, `com_cont`, `markup`, `descuento` — each is already wired correctly.

**Note on Vision Tarifas C75:** The references to `C75` found in `Vision Tarifas_Modelo_Cobro` sheet
(formulas `=(C75*D34)` and `=C75*D35`) refer to that **sheet's own** C75 cell
(`'Facturación Total Mensual' = 2,098,599,983`), NOT to `Panel de Control General!C75`. Confirmed
by reading the Vision Tarifas sheet directly — no cross-sheet reference.

---

## In-Memory What-If Impact

**Measurement not required** — confirmed `NOT_USED` before measurement.

The field is dropped at DTO ingestion:
1. `UserInputLoader` loads `request.json` → builds `UserInput`
2. `reglas_negocio.porcentaje_acumulado` is not a field of `ReglasNegocio` DTO — field is silently discarded
3. `PanelDeControl` has no `porcentaje_acumulado` attribute
4. `_calcular_reglas_negocio()` iterates `provider.get_politicas_comerciales()` (5 entries, none named `porcentaje_acumulado`)
5. Engine output is identical regardless of the request field value

| Output | Current value | What-if value | Delta | Impact |
|--------|---------------|---------------|-------|--------|
| P&G M3 ingreso_bruto | unchanged | unchanged | 0.0 | **NONE** |
| P&G M3 costo_total | unchanged | unchanged | 0.0 | **NONE** |
| Vision Tarifas ingreso_mensual | unchanged | unchanged | 0.0 | **NONE** |
| CTS cadena_a | 6,218.424663 | 6,218.424663 | 0.0 | **NONE** |

Any value in `porcentaje_acumulado.actual` (0, 0.02, or any other float) produces identical
engine output because the field is not read by the computation pipeline.

---

## Classification

| Area | Classification | Evidence | Future action |
|------|----------------|----------|---------------|
| `porcentaje_acumulado.actual` in request | `NO_IMPACT` | Field not consumed by engine; ReglasNegocio DTO excludes it; BUSINESS_RULES_FIX_3 | No action needed |
| `Panel!C75` in Excel | `NO_IMPACT` | 0 cross-sheet references; display-only derived cell | No action needed |
| Value gap (request=0, Excel=0) | `REQUEST_MATCH` | Both = 0 for this deal (prior session already aligned) | Closed |
| Engine guard | `CORRECTLY_EXCLUDED` | ValueError if it re-enters politicas_comerciales | Guard is protective — keep |
| Orphaned request field | `COSMETIC_ONLY` | `reglas_negocio.porcentaje_acumulado` in request.json is never read | Optional cleanup only |

---

## Recommendation

**`RECOMMEND_NO_ACTION`**

`porcentaje_acumulado` is a dead field that was correctly removed from the backend engine in
`BUSINESS_RULES_FIX_3`. The Excel cell `Panel!C75` is display-only with 0 downstream consumers.
No computation in P&G, Vision Tarifas, or CTS depends on this value.

**What already happened (prior sessions):**
- `BUSINESS_RULES_FIX_3` removed the field from `politicas_comerciales` + `panel_dto.py`
- `engine_helpers.py` has a `ValueError` guard preventing its re-entry
- `test_business_rules_fix3.py` explicitly validates the field is absent
- The request value was aligned to 0 in a prior session (`REQUEST-PCT-ACUM` row in backlog, marked `✅ PRE-ALIGNED`)

**Optional cleanup (non-blocking):** Remove `porcentaje_acumulado` from `request/request.json`'s
`reglas_negocio` block. Impact = cosmetic only (field is already ignored). Low priority. Not
required for V2-8 closure or production stability.

---

## Non-Goals

- This audit does not reopen CTS-001 or CTS-002.
- This audit does not touch V27 fixtures, anchors, or baseline.
- No production code changed (0 functional changes).
- No modules, request, storage, tests/golden, or contracts modified.

---

## Supporting Evidence

- `modules/calculator_motor/helpers/engine_helpers.py:70` — explicit comment: *"porcentaje_acumulado fue eliminado: sin fuente Panel, nunca activo."*
- `modules/panel/dto/panel_dto.py:39` — *"porcentaje_acumulado eliminado: era DEAD_FIELD_LEGACY sin fuente Panel."*
- `tests/unit/test_business_rules_fix3.py` — 3 tests assert `porcentaje_acumulado` is absent from politicas; `test_porcentaje_acumulado_en_provider_lanza_valueerror` verifies the guard
- Excel `'Panel de Control General'!C75` formula: `=SUM(C67:C69)-C70` = 0 (all inputs = 0 for this deal)
- Global Excel sheet search: 0 formulas in any sheet reference `'Panel de Control General'!C75`
- Provider confirmed: `get_politicas_comerciales()` returns 5 entries, none named `porcentaje_acumulado`
