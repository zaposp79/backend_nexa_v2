# CTS-001 Included-Roles Salary Deficit Audit

**Date:** 2026-06-12
**Session:** CTS_001_INCLUDED_ROLES_SALARY_DEFICIT_AUDIT
**Prior RCA:** `cts_001_support_loaded_salary_audit.md` (commit 2328bec)

> **STATUS (2026-06-12):** CTS-001 formally closed as `ACCEPTED_DELTA` via commit `5802a81`.  
> Final delta: **-6.150 COP/tx (-0.099%)** — below 0.5% gate.  
> The underlying -79.46 COP/tx deficit (Director de Performance G78=1.0 literal) was resolved  
> alongside ROLES-OP-STAFFCONFIG (JCR/AFAC/GTR exclusion) in the same commit — exactly as  
> recommended in this audit (fixing either alone would regress CTS-001).  
> **No further action required for V2-8 parity gates.**
**Target:** the **-79.46 COP/tx underlying deficit** in roles CORRECTLY included in Excel
(excluding JCR / AFAC / GTR, which are the separate +66.09 over-count bucket).
**Mode:** RCA / audit only — **0 production code changes**.

---

## Baseline Confirmation

| Gate | Result |
|------|--------|
| `tests/golden/` 96 passed | PASS |
| `make verify` | PASS — Baseline match. Sin drift. |
| `make validate-excel-v28` | PASS 6/6 (1 SKIPPED) |
| `tests/golden/test_cts_001_v28.py` | 2/2 PASS |

Working tree had pre-existing `M`/`??` changes unrelated to this session; none were
introduced or staged here except the docs below.

---

## Residual reproduction (Phase 1)

| Metric | Value |
|--------|-------|
| Excel C34 | 6,224.575126 COP/tx |
| Backend `cts_cadena_a` | 6,204.197492 COP/tx |
| Delta | **-20.378 COP/tx (-0.327%)** |
| Backend `nomina_loaded` (C36) | 5,391.864105 |
| Excel C36 | 5,405.229652 |
| `nomina_loaded` delta | **-13.366 COP/tx** |

**Net decomposition (confirmed, from prior audit):**
```
nomina_loaded delta -13.366 = +66.09 (JCR/AFAC/GTR over-count)  −  79.46 (included-role deficit)
```
Removing JCR/AFAC/GTR: backend nomina_loaded → 5,391.864 − 66.09 = 5,325.77 vs Excel 5,405.23
→ **included-role deficit = −79.46 COP/tx** (confirmed).

---

## Excel per-role extraction (Phase 2)

**Excel FTE source:** `'Condiciones Cadena A'` rows 77-99, columns E/F/G = channels Voz 1 / Voz 2 / WhatsApp.
**Excel loaded salary source:** `'Inputs de Nomina'` column W (rows 39-64), already used as backend override.
**Excel payroll aggregate source:** `'Nomina Loaded'` fijo block (rows 43-66) + variable block (rows 155-178),
columns C/D/E = the three perfiles (Escenario SAC Actual / WhatsApp Actual / Crecimiento inhouse).

Cross-checks vs Vision CTS formula map:
- Variable block total / 221,000 = **775.7432 = C38 exactly** (variable side reconciles cell-for-cell).
- Agent line `Agente Básico 1`: Excel fijo+var = 769,853,204 + 156,000,000 = 925,853,204 COP/mes;
  backend 260 FTE × 3,560,973.86 = **925,853,204 — EXACT MATCH** (agent is NOT a deficit source).

---

## Backend per-role extraction (Phase 3)

`build_v28_deal_provider()` + `request.json`, 66 `perfiles_cadena_a` (3 agent scenarios + support × channels).
Roles JCR / AFAC / GTR excluded from the included-role comparison per scope.

Roles with **EXACT** Excel match (per-FTE and aggregate): agent, supervisor, director de cuentas,
jefe de operación, works force, reporting, analista 2 service desk, formadores, monitor de calidad,
lider de entrenamiento, lider de experiencia, lider de planeación, analista (inicial) ×2. (≈14 roles, delta 0.)

---

## Comparison of correctly-included roles (Phase 4)

FTE comparison `'Condiciones Cadena A'!E/F/G` (Excel) vs backend per-channel FTE:

| Role | Excel FTE (E+F+G) | Backend FTE | sal_cargado | Deficit COP/tx = (ex−bk)·salc/221000 | Driver |
|------|-------------------|-------------|-------------|--------------------------------------|--------|
| **Director de Performance** | **1.1600** (G78 = literal `1`) | **0.2333** (ratio-derived) | 18,902,979 | **+79.264** | channel literal override G78=1 |
| Analista Prof. Sel. (Inicial) | 5.0797 | 5.0797 | 4,277,939 | 0.000 | match |
| Analista 1 Recl. (Inicial) | 2.5399 | 2.5399 | 2,946,260 | 0.000 | match |
| Analista Prof. Sel. (Rotación) | 0.4140 | 5.0797* | 4,277,939 | −90.315* | backend uses Inicial FTE (offsetting over-count) |
| Analista 1 Recl. (Rotación) | 0.2070 | 2.5399* | 2,946,260 | −31.101* | backend uses Inicial FTE (offsetting over-count) |
| Aprendiz SENA | 15.933 | 15.436 | ~2.49M | ~ −5.5 (snapshot) | ramp/SENA formula (see Phase 5) |
| Inclusión | 3.346 | 3.242 | ~2.49M | ~ −1.1 (snapshot) | ramp/Inclusión formula |

\* The Rotación rows carry an **opposite-sign** delta: backend assigns the (large) Inicial FTE to the
Rotación analista roles. This is an over-count that *masks*, not deepens, the deficit. It is a snapshot
artifact of steady-state CCA FTE and does not net into the 24-month-averaged CTS the same way; see note below.

### Dominant driver — `Director de Performance` channel literal `G78 = 1`

```
'Condiciones Cadena A'!G78 = 1          ← HARDCODED literal (not a formula)
'Condiciones Cadena A'!E78/F78          ← formulas: =IF($C78=TRUE, ((E$9+E$26+E$30+E$34)/E105)…)
```
Backend computes G78 via the ratio formula (≈0.073) → backend FTE 0.2333 vs Excel 1.1600.
This single override explains:

```
Director de Performance deficit = (1.1600 − 0.2333) × 18,902,979 / 221,000 = +79.264 COP/tx
79.264 / 79.46 = 99.75% of the included-role deficit
```

**This is the SAME class of literal per-role/channel override as the already-documented
`Supervisor E95 = 9.5` (DEFERRED).** `E95` and `G78` are both manual literals in the CCA FTE grid.

---

## SENA / Inclusión / payroll treatment (Phase 5)

- **SENA / Inclusión**: backend uses `calcular_aprendiz(get_salario_rol(rol))` with base 1,750,905
  (`'Inputs de Nomina'!C59/C60`, patched in provider). The residual ~−5.5 / −1.1 COP/tx is a
  ramp/headcount snapshot difference (Excel CCA steady FTE 15.93/3.35 vs backend 24-month average
  15.44/3.24), not a salary or factor error. SENA/Inclusión salaries reconcile.
- **Transport / benefit factors**: agent loaded salary (3,560,973.86) matches `'Inputs de Nomina'!W62`
  exactly, so the SENA/transport/benefit loading factor is correct.
- **No salary-magnitude error** found in any correctly-included role; every W-override lookup returns
  the exact Excel value. The deficit is driven by **FTE (headcount), not by loaded salary per FTE**.

---

## Classification (Phase 6)

| Driver | COP/tx | Classification | Evidence |
|--------|--------|----------------|----------|
| Director de Performance G78=1 literal | **+79.26** (99.75% of deficit) | **EXCEL_QUIRK** (per-role channel literal override) | `CCA!G78` is a hardcoded `1`, not the ratio formula in E78/F78; identical class to `E95=9.5` |
| SENA / Inclusión ramp snapshot | ≈ −5.5 / −1.1 | **ACCEPTED_DELTA** | salaries + factors match; difference is 24-month-avg vs steady FTE |
| Analista Rotación FTE = Inicial FTE | offsetting (snapshot) | **MODULE_FORMULA_GAP** (candidate) | backend reuses Inicial channel ratios for Rotación rows; opposite sign, masks deficit; not validated against the 24-month numerator |
| All loaded salaries / W overrides | 0 | **MATCH** | 20/20 W lookups exact; agent exact |

- **REQUEST_VALUE_GAP:** none in the included-role deficit (the JCR comisiones gap is in the excluded bucket).
- **PARAM_VALUE_GAP:** none — HR/GN/OP factors validated.
- **PROVIDER_VALUE_GAP / PROVIDER_SELECTION_GAP:** none — provider returns exact W values.
- **MODULE_FORMULA_GAP:** only the Rotación-FTE candidate (offsetting, not the deficit cause).
- **MAPPING_AMBIGUOUS:** resolved — prior session's "agent/SENA" hypothesis is **disproven**;
  the deficit is the Director de Performance channel literal.

> Per scope rule, no MODULE_FORMULA_GAP is asserted as the deficit cause: request, provider and
> parametrization were validated first, and the deficit traces to an Excel literal (EXCEL_QUIRK).

---

## Root cause (proven)

**The −79.46 COP/tx included-role deficit is ~99.75% the `Director de Performance` channel FTE:
`'Condiciones Cadena A'!G78` is a hardcoded literal `1.0`, while the backend derives it from the
channel ratio formula (≈0.073). Excel total FTE 1.16 vs backend 0.233 × loaded salary 18,902,979
= +79.26 COP/tx.** This is the same per-role literal-override pattern as `Supervisor E95 = 9.5`.

The previously "unproven" `MAPPING_AMBIGUOUS` deficit is now **resolved**: it is NOT agent salary
(agent matches exactly) and NOT SENA/Inclusión salary (factors match); it is a single per-role
channel literal in the Excel CCA FTE grid.

---

## Recommended fix (NOT implemented)

**Add `Director de Performance` channel override `WhatsApp = 1.0` to the same per-role FTE-override
mechanism that carries `Supervisor E95 = 9.5`.**

- **File:** `request/request.json` (`condiciones_cadena_a.perfiles[0].fte_soporte_overrides`) +
  consumption already wired in `modules/calculator_motor/mixins/context_builder_perfiles_soporte_mixin.py`
  (the `fte_soporte_overrides` channel-level path), as done for Supervisor.
- **Field/function:** extend `fte_soporte_overrides` to support per-channel literal (currently total-FTE
  override for Supervisor). Director de Performance needs **channel-specific** override (WhatsApp=1.0),
  so the override contract must carry `{rol: {canal: fte}}` granularity, not just `{rol: fte}`.
- **Before:** Director de Performance WhatsApp FTE = ratio-derived ≈0.073 (total 0.233).
- **After:** Director de Performance WhatsApp FTE = 1.0 (total 1.16), matching `CCA!G78`.
- **Risk:** MEDIUM. Closing this alone moves the included-role deficit from −79.46 to ≈ −0.2, i.e. it
  would shift net `nomina_loaded` from −13.37 to ≈ +66.09 (the JCR/AFAC/GTR over-count becomes dominant).
  **Director de Performance G78 and the `ROLES-OP-STAFFCONFIG` exclusion of JCR/AFAC/GTR must be fixed
  together**, or CTS-001 will regress. Requires a new golden anchor.
- **Tests expected:** `test_cts_001_v28.py` (new anchor), `test_support_fte_v28.py` (Director de
  Performance override applied), `test_e95_supervisor_override_applied` (pattern parity).

**Prerequisite ordering for full closure:**
1. Generalize `fte_soporte_overrides` to per-channel literals (E95 Supervisor + G78 Director Performance).
2. Wire `roles_operativos[].incluye_en_deal=False` → exclude JCR/AFAC/GTR (`ROLES-OP-STAFFCONFIG`).
3. Apply both simultaneously; expected net `nomina_loaded` → ≈ 0; re-anchor goldens.

---

## Non-goals / scope

- No production code changed. No `request/`, `storage/`, `tests/golden/` modified.
- JCR / AFAC / GTR NOT touched and NOT included in the included-role deficit calculation.
- No anchors updated. `make baseline` NOT run.
- Temporary scripts under `/tmp/` (`cts001_included_deficit.py`) NOT committed.

---

## Supporting evidence

- `'Condiciones Cadena A'!G78` formula-mode read = literal `1` (vs `E78`/`F78` IF-formulas) — `data_only=False`.
- `'Condiciones Cadena A'!E95` = `9.5` literal (Supervisor, documented DEFERRED) — same class.
- Agent reconciliation: `Nomina Loaded` rows 63/174 sum 925,853,204 = backend 260 × 3,560,973.86 (exact).
- Variable block (`Nomina Loaded` 155-178) / 221,000 = 775.7432 = Vision CTS C38 (exact).
- Director de Performance deficit: (1.16 − 0.2333) × 18,902,979 / 221,000 = +79.264 COP/tx = 99.75% of −79.46.
