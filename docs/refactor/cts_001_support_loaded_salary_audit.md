# CTS-001 Support Loaded Salary Audit

**Date:** 2026-06-12  
**Session:** CTS_001_SUPPORT_LOADED_SALARY_AUDIT  
**Prior RCA:** `cts_001_resume_from_clean_baseline.md` (commit 2e20fe9)  
**Residual under investigation:** -13.37 COP/tx (salary loaded component)

> **STATUS (2026-06-12):** CTS-001 formally closed as `ACCEPTED_DELTA` via commit `5802a81`.  
> Final delta: **-6.150 COP/tx (-0.099%)** — below 0.5% gate.  
> The -13.37 COP/tx salary loaded residual was partially resolved by the support FTE fix  
> (Director de Performance WhatsApp=1.0 + JCR/AFAC/GTR exclusion).  
> Remaining residual (-6.150) attributed to training/fixed-cost known deltas.  
> **No further action required for V2-8 parity gates.**

---

## Baseline Confirmation

| Gate | Result |
|------|--------|
| `tests/golden/` 96 passed | ✅ PASS |
| `make verify` | ✅ PASS — Baseline match. Sin drift. |
| `validate-excel-v28` | ✅ PASS 6/6 (1 SKIPPED) |
| `test_cts_001_v28.py` | ✅ 2/2 PASS |

---

## Fresh CTS-001 Residual

| Metric | Value |
|--------|-------|
| Excel C34 | 6,224.575126 COP/tx |
| Backend | 6,204.197492 COP/tx |
| Delta | **-20.378 COP/tx (-0.327%)** |
| Gate (3%) | ✅ WITHIN |

**Component split (confirmed):**

| Component | Backend | Excel | Delta |
|-----------|---------|-------|-------|
| Payroll nomina | 5,445.146 | 5,462.356 | -17.210 |
| → nomina_loaded | 5,391.864 | ~5,405.230* | -13.366 |
| → training/exam/crucero | 53.282 | ~57.126* | -3.844 |
| No-payroll | 759.051 | 762.219 | -3.168 |
| **TOTAL** | **6,204.197** | **6,224.575** | **-20.378** |

*Excel nomina_loaded sub-split from prior session (`formula_first_diff.md` §P4); C35/C45 anchors are authoritative.

---

## Excel Support Loaded Extraction

### Provider overrides (Excel `Inputs de Nomina!W39:W58`)

All 20 staff roles have `costo_empresa_override` values from Excel column W. **Phase 5c confirms all 20 provider lookups return EXACT match with the expected W values.**

### Excel `roles_operativos` exclusion flags

From `request.json` `condiciones_cadena_a.perfiles[0].roles_operativos`:

| Role | `incluye_en_deal` | Excel `fte_calculado` (CCA!C79/C80/C87) | Implication |
|------|-------------------|------------------------------------------|-------------|
| `Jefe Comercial Regional` | **False** | **0** | Excel FTE = 0, cost = 0 |
| `Analista profesional AFAC` | **False** | **0** | Excel FTE = 0, cost = 0 |
| `GTR` | **False** | **0** | Excel FTE = 0, cost = 0 |
| `Validador` | **False** | **0** | Excel FTE = 0, cost = 0 |
| All others (Director, Supervisor, Jefe de Operación, etc.) | True | > 0 | Included in Excel |

---

## Backend Support Loaded Extraction

### Override lookup verification

All 20 `costo_empresa_override` lookups from `build_v28_deal_provider()` return **EXACT match** with Excel W column. The override mechanism works correctly via alias rows appended by `_ActiveRepoPatchedNomina._patch_all_staff`.

### Per-role backend loaded salary (aggregated across channels)

From diagnostic script `/tmp/cts001_support_audit.py`:

| Role | FTE (total) | `sal_cargado` | Monthly COP | COP/tx | Override status |
|------|------------|--------------|-------------|--------|-----------------|
| supervisor | 16.369 | 4,506,462 | 73,767,313 | 333.79 | EXACT (W57) |
| Aprendiz SENA | 15.436 | 2,496,241 | 38,532,111 | 174.35 | NO_OVERRIDE (formula) |
| analista prof. de seleccion inicial | 5.080 | 4,277,939 | 21,730,735 | 98.33 | EXACT (W51) |
| analista prof. de seleccion rotacion | 5.080 | 4,277,939 | 21,730,735 | 98.33 | EXACT (W52) |
| jefe de operacion | 1.693 | 8,065,483 | 13,656,799 | 61.80 | EXACT (W46) |
| monitor de calidad | 3.991 | 3,281,883 | 13,098,679 | 59.27 | EXACT (W56) |
| formadores | 3.991 | 3,155,445 | 12,594,038 | 56.99 | EXACT (W55) |
| director de cuentas | 0.373 | 32,816,427 | 12,224,540 | 55.31 | EXACT (W39) |
| Inclusión | 3.242 | 2,496,241 | 8,091,743 | 36.61 | NO_OVERRIDE (formula) |
| analista 1 de reclutamiento inicial | 2.540 | 2,946,260 | 7,483,087 | 33.86 | EXACT (W51) |
| analista 1 de reclutamiento rotacion | 2.540 | 2,946,260 | 7,483,087 | 33.86 | EXACT (W53) |
| **gtr** | **2.328** | 3,051,810 | **7,105,239** | **32.15** | EXACT (W49) |
| director de performance | 0.233 | 18,902,979 | 4,401,001 | 19.91 | EXACT (W40) |
| **jefe comercial regional** | **0.349** | **12,172,533** | **4,251,023** | **19.24** | **W-MISMATCH** (W41=7,648,436) |
| works force | 0.931 | 4,196,802 | 3,908,406 | 17.69 | EXACT (W48) |
| reporting | 0.931 | 4,196,802 | 3,908,406 | 17.69 | EXACT (W48) |
| **analista profesional afac** | **0.698** | 4,652,771 | **3,249,782** | **14.70** | EXACT (W42) |
| analista 2 service desk | 0.755 | 3,391,133 | 2,560,623 | 11.59 | EXACT (W54) |
| lider de planeacion operativa | 0.279 | 7,562,646 | 2,112,887 | 9.56 | EXACT (W45) |
| lider de entrenamiento | 0.279 | 6,905,404 | 1,929,264 | 8.73 | EXACT (W43) |
| lider de experiencia de cliente | 0.279 | 6,905,404 | 1,929,264 | 8.73 | EXACT (W44) |
| **TOTAL** | **67.399** | — | **265,748,763** | **1,202.48** | — |

**Bold rows** = problem roles.

---

## Role-by-Role Comparison

### Key finding: ROLES-OP-STAFFCONFIG gap

Three roles are marked **`incluye_en_deal: False`** in `roles_operativos` (Excel `C79/C80/C87 = False`) but are **actively processed by the backend** (HR ratios include them, `staff_config` doesn't exclude them):

| Role | Backend FTE | Backend Monthly | COP/tx | Excel FTE | Excel Monthly | Over-count COP/tx |
|------|------------|-----------------|--------|-----------|---------------|-------------------|
| `jefe comercial regional` | 0.349 | 4,251,023 | 19.24 | **0** | **0** | **+19.24** |
| `analista profesional afac` | 0.698 | 3,249,782 | 14.70 | **0** | **0** | **+14.70** |
| `gtr` | 2.328 | 7,105,239 | 32.15 | **0** | **0** | **+32.15** |
| **Total over-count** | | 14,606,044 | **+66.09** | | | |

### Secondary: `jefe comercial regional` sal_cargado formula bypass

Beyond the FTE discrepancy, JCR also has a `sal_cargado` mismatch:

| | `sal_cargado` | Source |
|--|---------------|--------|
| Excel W41 | 7,648,436 | `Inputs de Nomina!W41` (no commission in deal) |
| Backend | **12,172,533** | Formula path: `calcular(5,528,260, 3,270,000/5,528,260)` |
| Delta per FTE | +4,524,097 | |

**Root cause of bypass:** `request.json` `condiciones_cadena_a.detalles_recursos_humanos` contains `Jefe Comercial Regional` with `comisiones: 3,270,000`. When the mixin calls `valores_recurso_humano("jefe comercial regional")`, `usa_detalle=True` (entry found in `detalles_por_rol`). The branch `if not usa_detalle:` is skipped → `get_costo_empresa_override` is **NEVER CALLED** (confirmed: 0 trace calls during full engine run). The formula inflates `sal_cargado` from 7,648,436 to 12,172,533.

Additional JCR impact due to formula inflation vs W: `0.349 × (12,172,533 - 7,648,436)` = 1,578,954 COP/month = **+7.14 COP/tx** within the JCR over-count.

### Roles with `sal_cargado = Excel W` (formula path coincidentally matches)

For `analista profesional afac` and `gtr`, `usa_detalle=True` is also triggered (both are in `detalles_recursos_humanos`), but their formula result happens to equal the Excel W value:
- AFAC: `calcular(3,140,052, 0)` ≈ 4,652,771 = W42 ✓
- GTR: `calcular(1,982,883, 0)` ≈ 3,051,810 = W49 ✓

These roles have **zero per-FTE sal_cargado gap** vs Excel, but a **full FTE gap** (backend FTE > 0, Excel FTE = 0).

### Structural decomposition

The -13.37 COP/tx nomina_loaded gap is the NET of two opposing forces:

| Source | COP/tx | Direction |
|--------|--------|-----------|
| JCR/AFAC/GTR over-count (roles Excel excludes) | +66.09 | reduces gap |
| Underlying deficit in correctly-included roles | -79.46 | increases gap |
| **Net** | **-13.37** | — |

The **+66.09 over-count partially compensates a larger -79.46 underlying deficit**. Simply removing JCR/AFAC/GTR (fixing ROLES-OP-STAFFCONFIG) would INCREASE the gap from -13.37 to approximately -79.46 COP/tx without simultaneously addressing the underlying deficit.

---

## Classification

### By role/group

| Role/group | Delta COP/tx | Main driver | Classification | Evidence |
|-----------|-------------|-------------|----------------|---------|
| `jefe comercial regional` | +19.24 (vs Excel=0) | FTE mismatch (included vs excluded) + sal_cargado formula bypass | `BACKEND_NOT_CONSUMING_FIELD` + `REQUEST_VALUE_GAP` | `incluye_en_deal: False`; `detalles_recursos_humanos` with comision 3.27M bypasses override |
| `analista profesional afac` | +14.70 (vs Excel=0) | FTE mismatch (included vs excluded) | `BACKEND_NOT_CONSUMING_FIELD` | `incluye_en_deal: False`; formula = W (zero per-FTE gap) |
| `gtr` | +32.15 (vs Excel=0) | FTE mismatch (included vs excluded) | `BACKEND_NOT_CONSUMING_FIELD` | `incluye_en_deal: False`; formula = W (zero per-FTE gap) |
| Underlying deficit (-79.46) | -79.46 | Unknown — agent salary / SENA / Inclusion differences vs Excel | `MAPPING_AMBIGUOUS` | Not proven in this session; requires deeper Excel CCA comparison |
| All other staff (18 roles) | 0 | Override applied correctly | MATCH | All 18 override lookups return exact W values |
| SENA / Inclusion | 0 (per FTE, not proven vs Excel) | Formula-computed, not in W column | `MAPPING_AMBIGUOUS` | No Excel anchor for SENA/Inclusion monthly cost |

### By classification type

| Classification | Roles | COP/tx |
|---------------|-------|--------|
| `BACKEND_NOT_CONSUMING_FIELD` | JCR, AFAC, GTR | +66.09 |
| `REQUEST_VALUE_GAP` | JCR (`detalles_recursos_humanos.comisiones`) | within JCR over-count |
| `MAPPING_AMBIGUOUS` | Underlying deficit (agent/SENA/Inclusion) | -79.46 (not proven) |
| MATCH / EXACT | 18 staff roles (W39-W58 exc. JCR) | ~0 |

---

## Root Cause (Proven)

**Primary confirmed root cause:** `ROLES-OP-STAFFCONFIG` gap

The engine processes roles from HR ratios directly, WITHOUT consuming `roles_operativos[].incluye_en_deal` from the request. Three roles marked `incluye_en_deal: False` in the deal (Excel `CCA!C79/C80/C87 = False`) are included in the backend calculation:

- `Jefe Comercial Regional` (ratio=800)
- `Analista profesional AFAC` (ratio=400)
- `GTR` (ratio=1300 or similar)

The `staff_config[]` mechanism exists in the mixin (`ContextBuilderPerfilesSoporteMixin._construir_perfiles_soporte`) to exclude roles via `activo=False`, but this field is NOT populated in `request.json` for these roles. The `roles_operativos` list (which carries the `incluye_en_deal` flag) is NOT consumed by the motor.

**Secondary confirmed root cause:** JCR `detalles_recursos_humanos` formula bypass

`request.json` `condiciones_cadena_a.detalles_recursos_humanos` includes `Jefe Comercial Regional` with `comisiones: 3,270,000`. When the mixin finds this entry, it sets `usa_detalle=True` → the `get_costo_empresa_override()` call is skipped → `sal_cargado = calcular(5,528,260, 0.591)` ≈ 12,172,533 instead of the correct Excel W41 = 7,648,436. This inflates JCR `sal_cargado` by +4,524,097 per FTE within the already-overflowing JCR FTE count.

**Unproven root cause:** Underlying -79.46 COP/tx deficit

Without the 3 excluded roles, backend nomina_loaded would be ~5,325.77 COP/tx vs Excel ~5,405.23 COP/tx = -79.46 COP/tx gap. This underlying deficit is NOT proven in this session. Candidate sources:
1. Agent salary differences (the engine uses HR base salary for agents; Excel uses CCA!C column per-deal)
2. SENA / Inclusión formula deviations
3. FTE ratio differences for correctly-included roles across channels

---

## Recommended Fix (Not Implementing)

**RECOMMEND_DEEPER_RCA** before any code change.

### Immediate: Wire `incluye_en_deal` → `staff_config.activo`

**File:** `modules/shared/contracts/api_v1/request/cadena_a.py` + `modules/calculator_motor/mixins/user_input_builders_cadena_a.py`  
**Before:** `CondicionesCadenaAInput` does not map `roles_operativos[].incluye_en_deal=False` to `staff_config[].activo=False`  
**After:** When building `CondicionesCadenaAInput`, for each role in `roles_operativos` with `incluye_en_deal=False`, create a `StaffRolInput(nombre=rol, activo=False)` entry in `staff_config`  
**Expected tests:** `test_cts_001_v28.py` — delta should change, need new anchor  
**Risk:** HIGH — fixing this alone increases gap from -13.37 to approximately -79.46 COP/tx. MUST address underlying deficit simultaneously.  
**Requires:** `request.json` (no change needed), `modules/` code change (builder), no production change until underlying deficit is characterized.

### JCR detalles comision fix

**File:** `request/request.json` `condiciones_cadena_a.detalles_recursos_humanos` entry for Jefe Comercial Regional  
**Before:** `comisiones: 3,270,000` (inflates formula sal_cargado, bypasses override)  
**After:** `comisiones: 0` (matches provider `_V28_STAFF_COMISION` → no commission for JCR in SAC deal per `_v28_deal_provider.py` comment: "Row 41: no commission")  
**Risk:** Medium — reduces JCR sal_cargado to formula ≈ W value (7,648,436)  
**Requires:** `request.json` change (in-scope). But because `incluye_en_deal=False`, even with correct sal_cargado the JCR FTE should be 0 in Excel.

### Prerequisite investigation before any fix

1. Characterize the -79.46 COP/tx underlying deficit by auditing agent salary + SENA/Inclusion in a dedicated session.
2. Only then implement ROLES-OP-STAFFCONFIG fix + fix the -79.46 simultaneously.
3. Expected outcome after BOTH fixes: net gap approaches 0 COP/tx.

---

## Non-goals

- Did NOT modify production code
- Did NOT modify `request/`, `storage/`, `tests/golden/`
- Did NOT update anchors
- Did NOT run `make baseline`
- Did NOT reopen CTS-002
- Temporary scripts under `/tmp/` — not committed

---

## Supporting Evidence Files

- Diagnostic script: `/tmp/cts001_support_audit.py` (NOT committed)
- Trace scripts: `/tmp/cts001_jefe_trace*.py`, `/tmp/cts001_prov_type.py` (NOT committed)
- Override lookup verified via `ParametrizationProvider.get_costo_empresa_override` trace (0 calls for JCR during engine run — confirmed via `ContextBuilderPerfilesSoporteMixin` patch)
- `detalles_recursos_humanos` discovery: `request.json` `condiciones_cadena_a.detalles_recursos_humanos[2]` = `{'cargo': 'Jefe Comercial Regional', 'salario_base': 5528260.0, 'comisiones': 3270000.0}`
- `roles_operativos` exclusion flags: SAC Actual profile — JCR/AFAC/GTR/Validador with `incluye_en_deal: False`
