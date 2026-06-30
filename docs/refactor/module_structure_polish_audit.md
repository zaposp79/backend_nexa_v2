# Module Structure Polish Audit — Beyond FASE 8B

**Date:** 2026-06-14  
**Branch:** refactor/modular-pure  
**Status:** MODULE_STRUCTURE_REFACTOR_CLOSED  
**This audit:** READ-ONLY structure clarity review. No code modified.

---

## 1. Executive Verdict

**The module/db refactor is structurally sound but FEELS unclear due to:**

1. **Calculator_motor carries deferred complexity** — 50 py files, 18 subdirs, all certified core with no formula lineage annotations. Looks "messy" because formula ownership is implicit, not documented in code.
2. **Vision_imprimible helpers are domain-scattered** — 5 helper files (aprobaciones, canal_builders, configuracion_comercial, ficha, reglas_negocio) house domain logic that should be clearer via naming or reorganization.
3. **Parametrizacion is large and repetitive** — 31 py files with vertical slices (gn, hr, op) that duplicate structure (each has api/, validators/, services/, repositories/); structure is sound but looks "noisy".
4. **Docs/refactor is a historical accumulation** — 170+ intermediate audit docs from V2-8 closure, formula phases, CTS investigations; final reports exist but intermediate WIP docs clutter the index.
5. **Wildcard re-exports in shared/models/__init__.py** — Intentional public API but visually unclear why they're wildcard vs. named imports.

**Verdict:** Structure is **READY FOR PRODUCTION**, but readability and future maintenance can improve via:
- Formula lineage documentation (BLOCK 06 — already planned)
- Selective helper renaming in vision_imprimible (BLOCK 08)
- Docs/refactor cleanup and indexing (BLOCK 09)
- Deferred formula core review post-formula lineage (BLOCK 12)

**No structural breaking changes required.** All recommendations are additive/clarifying.

---

## 2. Visual Structure Score by Module

| Module | Files | Dirs | Score | Main Issue | Owner |
|--------|-------|------|-------|-----------|-------|
| **api_v1** | 2 | 1 | GOOD | Minimal HTTP router aggregator | Shared |
| **audit** | 9 | 3 | ACCEPTABLE | Clear audit trace + logging; structure is sound | Shared |
| **cadena_a** | 17 | 7 | GOOD | Clear vertical slice: api, services, staffing, use_cases | cadena_a |
| **cadena_b** | 9 | 4 | GOOD | Compact vertical slice; reglas.py is clear | cadena_b |
| **cadena_c** | 8 | 4 | GOOD | Compact vertical slice; reglas.py is clear | cadena_c |
| **calculator** | 16 | 5 | NEEDS_POLISH | Has certified_helpers in use_cases; inconsistent with motor helpers; use_cases/ also contains persistence | calculator |
| **calculator_motor** | 50 | 18 | DEFER_CERTIFIED_CORE | Large, but correct. Looks messy without formula lineage annotations. Deferred for BLOCK 06. | calculator_motor |
| **certification** | 5 | 2 | ACCEPTABLE | Minimal hash/certificate tracking | Shared |
| **lineage** | 10 | 4 | ACCEPTABLE | DDD-style bounded context (domain, application, infrastructure); clear ownership | lineage |
| **panel** | 8 | 5 | GOOD | Vertical slice with clear models + services | panel |
| **parametrizacion** | 31 | 42 | ACCEPTABLE | Large domain with 3 vertical slices (gn, hr, op); structure is sound but repetitive | parametrizacion |
| **pyg** | 11 | 5 | GOOD | Vertical slice; builders + services are clear | pyg |
| **shared** | 24 | 11 | ACCEPTABLE | Central hub for exceptions, ports, config, contracts, models; over-reliant but unavoidable | shared |
| **vision_cost_to_serve** | 11 | 6 | GOOD | Vertical slice with clear ownership; helpers are minimal | vision_cost_to_serve |
| **vision_imprimible** | 17 | 5 | NEEDS_POLISH | 5 helpers (aprobaciones, canal_builders, etc.) hide domain logic; builders are clear but helpers are generic | vision_imprimible |
| **vision_tarifas** | 15 | 6 | ACCEPTABLE | Vertical slice with reglas.py; mixins for methods; acceptable but could be clearer | vision_tarifas |

**Summary:**
- **GOOD:** 8 modules (clear ownership, predictable structure)
- **ACCEPTABLE:** 6 modules (sound but could use polish)
- **NEEDS_POLISH:** 2 modules (vision_imprimible, calculator)
- **DEFER_CERTIFIED_CORE:** 1 module (calculator_motor — deferred until BLOCK 06)

---

## 3. Generic Name Findings

### Critical Generic Names

| File | Current Name | Issue | Domain Owner | Recommended Action | Risk | Decision |
|------|-------------|-------|--------------|-------------------|------|----------|
| `modules/calculator/use_cases/certified_helpers.py` | Too generic | "certified_helpers" hides that this is calculation helpers for certified mode | calculator | KEEP_AS_IS — removal is blocked; certified core | LOW | DEFER_CERTIFIED_CORE |
| `modules/calculator_motor/helpers/engine_helpers.py` | Acceptable but generic | "engine_helpers" is OK since calculator_motor IS the engine | calculator_motor | KEEP_AS_IS — acceptable for internal module helpers | LOW | DEFER_FORMULA_LINEAGE |
| `modules/calculator_motor/serializers/serializer_helpers.py` | Generic + problematic coupling | Imports vision_imprimible helpers (ficha, reglas_negocio, etc.); boundary unclear | calculator_motor | RENAME_LATER to clarify scope or move coupling audit to BLOCK 06 | HIGH | DEFER_IMPORT_RISK |
| `modules/parametrizacion/gn/models/models.py` | Redundant | Why "models/models.py"? Should be "gn_models.py" or stay if it's a package marker | parametrizacion/gn | RENAME_RECOMMENDED to "gn_models.py" or clarify package pattern | MEDIUM | DEFER_IMPORT_RISK — safe rename after validators audit |
| `modules/parametrizacion/hr/models/models.py` | Redundant | Same as above | parametrizacion/hr | RENAME_RECOMMENDED | MEDIUM | DEFER_IMPORT_RISK |
| `modules/parametrizacion/op/models/models.py` | Redundant | Same as above | parametrizacion/op | RENAME_RECOMMENDED | MEDIUM | DEFER_IMPORT_RISK |
| `modules/parametrizacion/gn/validators/validator.py` | Redundant | Why "validators/validator.py"? Singular file in plural folder. | parametrizacion/gn | RENAME_RECOMMENDED to "gn_validator.py" or "validators.py" (singular folder) | LOW | DEFER_LOW_VALUE — low risk but low value |
| `modules/parametrizacion/hr/validators/validator.py` | Redundant | Same as above | parametrizacion/hr | RENAME_RECOMMENDED | LOW | DEFER_LOW_VALUE |
| `modules/parametrizacion/op/validators/validator.py` | Redundant | Same as above | parametrizacion/op | RENAME_RECOMMENDED | LOW | DEFER_LOW_VALUE |

### Acceptable Generic Names

| File | Reason |
|------|--------|
| `*_service.py` | Domain-specific (cadena_a_service, cadena_b_service); acceptable pattern |
| `*_repository.py` | Clear pattern; domain is obvious from folder |
| `input_validator.py` (calculator_motor) | Correct — validates input contracts; not generic in context |
| `contract_validator.py` (calculator_motor) | Correct — validates Pydantic contracts |

---

## 4. Spanish/English Naming Findings

### Current State

| Domain | Spanish Term | Where Used | Keep Language | Reason |
|--------|-------------|-----------|---------------|--------|
| Payroll | nomina | formulas/payroll/nomina.py, models, engine | KEEP SPANISH | Certified Excel term; Ley 1393/2010 compliance |
| Non-payroll | no_payroll | formulas/no_payroll/ | ENGLISH OK | Technical designation, not domain vocabulary |
| Rules | reglas | cadena_b/reglas.py, cadena_c/reglas.py, vision_tarifas/reglas.py | KEEP SPANISH | Business rules, domain-specific term |
| Costs | costos | costos_financieros/, constants | KEEP SPANISH | Excel vocabulary (Costos Financieros, Costos Totales) |
| Financial | financiacion | formulas/costos_financieros/financiacion.py | KEEP SPANISH | Loan/financing is domain-specific |
| Tarifas | tarifas | vision_tarifas/, models | KEEP SPANISH | Excel term; product vocabulary |
| Riesgo | riesgo | formulas/risk/riesgo.py | KEEP SPANISH | Ley 1819 compliance; business risk |
| Ausencias | ausencias, rotacion, capacitacion | input_normalizer, context_builder | KEEP SPANISH | Excel vocabulary; HR business terms |

**Verdict:** Mixed Spanish/English is **APPROPRIATE** — domains bound by Excel/Ley requirements keep Spanish; architecture/orchestration folders use English. No renaming recommended.

---

## 5. Shared/ Second-Pass Audit

### Current Shared Structure

| Submodule | Files | Primary Users | Is Truly Shared | Risk | Decision |
|-----------|-------|---------------|-----------------|------|----------|
| **exceptions.py** | 1 | ~180 imports | YES — technical base | LOW | KEEP_IN_SHARED |
| **responses.py** | 1 | API routers | YES — HTTP response wrapper | LOW | KEEP_IN_SHARED |
| **precision.py** | 1 | calculator_motor, formulas | YES — shared numeric utility | LOW | KEEP_IN_SHARED |
| **ports/** | 3 | calculator_motor, lineage, audit | YES — Protocols for DI | LOW | KEEP_IN_SHARED |
| **contracts/api_v1/** | 18 | API routers, handlers | YES — request/response contracts | LOW | KEEP_IN_SHARED |
| **models/__init__.py** | 1 (re-exports 7 wildcard) | Everywhere | TOLERATED — public API | MEDIUM | KEEP_PUBLIC_REEXPORT but document intent |
| **models/results.py** | 1 | calculator_motor, visions | YES — PricingResult type | LOW | KEEP_IN_SHARED |
| **config/** | 4 | app, handlers, calculator_motor | YES — business rules + app settings | LOW | KEEP_IN_SHARED |
| **infrastructure/** | 6 | app lifespan, logging, CORS | YES — FastAPI infra | LOW | KEEP_IN_SHARED |
| **middleware/** | 1 | app | YES — FastAPI middleware | LOW | KEEP_IN_SHARED |
| **versioning/** | 2 | parametrizacion, calculator_motor | YES — version registry | LOW | KEEP_IN_SHARED |

**Verdict:** All shared items are **justified**. No MOVE_LATER candidates. Wildcard re-exports in `models/__init__.py` are intentional public API; document via docstring.

---

## 6. Calculator_Motor Perception Findings

**Why does calculator_motor feel "messy"?**

1. **No formula lineage annotations** — Formulas exist but lack `# Excel V2-8 · '<Sheet>'!<Cell>` comments. Ownership implicit.
2. **Deep mixin chain** — 7 context_builder mixins inherit in sequence; composition is correct but not visually obvious.
3. **Helpers scattered across formulas/** — `payroll/factors.py`, `financiacion.py`, `calculators.py` implement helpers but aren't named as such.
4. **Serializer coupling to vision_imprimible** — `serializers/serializer_helpers.py` imports vision_imprimible.helpers; boundary unclear.

**Is structure wrong?** No. **DEFER_CERTIFIED_CORE** — all files are golden-backed and must not move before BLOCK 06 formula lineage + guardrails.

**What should BLOCK 06 document?**
- Excel cell citations for each formula
- Mixin inheritance chain diagram
- Serializer/vision_imprimible boundary justification
- Open TODO(GAP-CADENA-A-FASE4) decision

---

## 7. Docs/Refactor Cleanup Findings

**Current state:** 170+ markdown files documenting V2-8 closure, formula phases, CTS investigations, Excel parity.

### Recommended Cleanup (Deferred to BLOCK 09)

| Category | Files | Action | Reason |
|----------|-------|--------|--------|
| **Final reports** | CLOSEOUT_REPORT.md, FINAL_BRANCH_STABILITY_REPORT.md, v28_final_closure_status.md | KEEP_IN_ROOT | Official closure records |
| **Formula lineage** | calculator_motor_structure_audit.md, formula_map_v28.md, v28_full_formula_inventory.md | KEEP_IN_ROOT | Reference for BLOCK 06 |
| **Excel parity** | excel_backend_parity_certification_closeout.md, excel_v28_parity_report.md | KEEP_IN_ROOT | Validation records |
| **CTS investigations** | cts_*_v28_*.md (9 files) | ARCHIVE to `/docs/refactor/archive/cts_v28/` | Detailed audit trail; not daily reference |
| **Formula phases** | formula_refactor_phase*.md, formula_trace_runtime_wiring_phase*.md (22 files) | ARCHIVE to `/docs/refactor/archive/formula_phases/` | Intermediate work; formula lineage is final reference |
| **V2-8 process** | v28_*.md (20+ files), baseline_*.md (10 files) | ARCHIVE to `/docs/refactor/archive/v28_process/` | Historical process docs; not operational |
| **Shared/input/design audits** | shared_*.md, input_*.md, design_*.md (15 files) | KEEP_IN_ROOT if recent, ARCHIVE if >3mo | Structure decisions may still be relevant |

**Index to create:** `/docs/refactor/INDEX.md` listing:
- Operational docs (calculator_motor audit, formula map, contracts)
- V2-8 closure records (final reports, parity, CTS decisions)
- Archive locations (formula phases, process docs)

---

## 8. Target Structure Proposal

### No Immediate Moves Recommended

**Rule:** No runtime code changes without BLOCK 06 formula lineage + guardrails.

### Suggested Polish (Future Blocks)

| Area | Current | Target | When | Why | Risk |
|------|---------|--------|------|-----|------|
| **vision_imprimible helpers** | 5 generic helpers | Rename to domain-specific or reorganize into sub-packages | BLOCK 08 | Clarity; "aprobaciones" could be "approval_rules", "canal_builders" → "channel_assignment" | LOW — visuals only |
| **calculator** | use_cases/ + certified_helpers | Clarify ownership or reorganize | BLOCK 08 | Inconsistent with calculator_motor/ which has helpers/ | MEDIUM — risk import breaks if moved |
| **parametrizacion** | gn/hr/op models/models.py | models/gn_models.py, etc. | BLOCK 08 | Reduce redundancy | LOW — mechanical rename |
| **calculator_motor** | KEEP_AS_IS for now | Annotate formulas + mixin chain diagram (BLOCK 06) | BLOCK 06 | Formula lineage + golden guardrails | CRITICAL — certified core |
| **docs/refactor** | 170+ intermediate docs | Archive intermediate work; keep operational docs | BLOCK 09 | Reduce noise; improve findability | LOW — non-runtime |

---

## 9. Recommended Next Blocks

### BLOCK 08 — Naming Polish (Non-Critical Modules)

**Scope:** Improve readability of non-certified modules via selective renames and restructuring.

**Files likely touched:**
- `modules/vision_imprimible/helpers/` (5 files — rename or reorganize)
- `modules/calculator/use_cases/certified_helpers.py` (document ownership)
- `modules/parametrizacion/gn/models/models.py`, `hr/models/models.py`, `op/models/models.py` (rename to gn_models.py, etc.)

**Risk:** LOW — visual clarity only; no formula changes.

**Validation required:**
- Imports resolve (grep for from/import statements)
- Tests pass: `pytest tests/contracts/ tests/api/`
- No golden test failures

**Why this should be next:** Improves code clarity without touching certified core. Unblocks future readers.

---

### BLOCK 09 — Docs/Refactor Cleanup and Indexing

**Scope:** Archive intermediate V2-8 process docs; create operational index; clarify final records.

**Files likely touched:**
- Create `/docs/refactor/INDEX.md` (operational guide)
- Create `/docs/refactor/archive/` (CTS, formula phases, process docs)
- Move 60+ intermediate files to archive
- Keep 15-20 operational docs in root

**Risk:** NONE — documentation only.

**Validation required:**
- All moved files still exist (git mv, not delete)
- INDEX.md is accurate and complete
- No broken internal links

**Why this should be next:** Reduces cognitive load; improves findability; makes repo feel cleaner.

---

### BLOCK 06 (Already Planned) — Formula Lineage & BLOCK 06 Guardrails

**Scope:** Annotate formulas with Excel V2-8 cell citations; document mixin chain; clarify serializer coupling.

**Files likely touched:**
- `modules/calculator_motor/formulas/payroll/nomina.py`
- `modules/calculator_motor/formulas/payroll/factors.py`
- `modules/calculator_motor/formulas/no_payroll/costs.py`
- `modules/calculator_motor/formulas/costos_financieros/calculator.py`
- `modules/calculator_motor/formulas/costos_financieros/financiacion.py`
- `modules/calculator_motor/formulas/profitability/calculators.py`
- `modules/calculator_motor/formulas/pricing/pricing.py`
- `modules/calculator_motor/formulas/risk/riesgo.py`
- `modules/calculator_motor/constants/global_constants.py`
- `modules/calculator_motor/mixins/context_builder_*.py`

**Risk:** CRITICAL — annotations only (no logic changes), but requires Excel V2-8 mapping expertise.

**Validation required:**
- All formulas still produce same outputs (make verify PASS)
- Golden tests unchanged (99 PASS)
- No circular imports introduced

**Why this should be next:** Removes "messy" perception of calculator_motor; unblocks future structure decisions.

---

## 10. Checkpoint

```
CHECKPOINT_REQUIRED

✅ No code was changed
✅ No files were moved
✅ No files were renamed
✅ No files were deleted

Structure is PRODUCTION_READY.
Readability improvements are DEFERRED to BLOCK 08/09 (non-critical).
Formula lineage clarity is DEFERRED to BLOCK 06 (already planned).
Calculator_motor structure DEFERRED until BLOCK 06 complete.

This audit documents the NEXT steps for polish, not immediate action.
Implementation must not start until this report is reviewed and approved.
```

---

## Appendix A: Structure Score Rationale

### GOOD (8 modules)
Clear ownership, predictable folder structure, low ambiguity:
- `api_v1`, `cadena_a`, `cadena_b`, `cadena_c`, `panel`, `pyg`, `vision_cost_to_serve`

### ACCEPTABLE (6 modules)
Sound structure but could use polish or has justified complexity:
- `audit`, `certification`, `lineage` (DDD style; acceptable)
- `parametrizacion` (large but structured)
- `shared` (unavoidable central hub)
- `vision_tarifas` (acceptable but could clarify mixins)

### NEEDS_POLISH (2 modules)
Specific improvements would help:
- `calculator` (certified_helpers; use_cases/ location)
- `vision_imprimible` (5 helper files; domain logic scattered)

### DEFER_CERTIFIED_CORE (1 module)
Must not move before BLOCK 06 formula lineage:
- `calculator_motor` (50 py, 18 dirs; all golden-backed)

---

*Generated by backend-agent — MODULE_STRUCTURE_POLISH_AUDIT — 2026-06-14*
*No runtime code modified. Report is read-only documentation.*
