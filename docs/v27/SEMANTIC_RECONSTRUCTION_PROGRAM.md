# SEMANTIC EXCEL RECONSTRUCTION PROGRAM

> **Status (2026-05-28)**: Active. Replaces all prior parity certification
> claims (see `_DEPRECATED_CERTIFICACION_PARIDAD_V2_7.md`,
> `_DEPRECATED_CERTIFICACION_INDUSTRIALIZACION_COMPLETA.md`).

---

## 0. Charter

The objective is no longer approximation, structural equivalence, or
"acceptable financial tolerance". The objective is:

```
∀x: f_backend(x) = f_excel(x)
```

with drift = **0.00%**, cell-by-cell, deterministic.

Excel V2-7 (`Nexa - Pricing - Simulador - V2-7.xlsx`) is the **sole**
source of truth for both formulas and parameter values. If backend ≠
Excel, **backend is wrong**. No exceptions, no business overrides, no
normalization tricks, no rounding bands.

The branch `refactor/engine-v2` is FROZEN against merge into `main` until
this program completes.

---

## 1. Audit Findings (W16-W19)

### 1.1 Eight confirmed hacks (W16)

| # | Hack | Severity | Status |
|---|------|---|---|
| H1 | `comision_pct` invented for Director (5%) and GTR (10%) — Excel cells are empty | CRITICAL | open |
| H2 | Bancamia "golden master" uses fake aggregate `salario_base=85065268.0` | HIGH | open |
| H3 | Parity tests circular — compute expected via same backend formula | CRITICAL | mitigated W17 (39 tests marked `legacy_circular`) |
| H4 | Two different SHA-256 hash algorithms for parametrization | HIGH | open |
| H5 | "WAVE 4 business override" markers — admit non-Excel values | MEDIUM | open |
| H6 | Excel oracle test only verifies inputs / asserts P&G is zero | CRITICAL | mitigated W17 (real oracle suite added) |
| H7 | WAVE 15 "923 passed" not reproducible under Python 3.7 | HIGH | environmental — defer |
| H8 | "Agente Básico 1 backport" — value OK, sourcing manual | LOW | acceptable |

### 1.2 Oracle status (W17 → W19)

- 531 Excel V2-7 cells extracted, **333 non-zero**
- 41 cells mapped to a backend path
- **W17**: 6 pass / 33 fail (drift 73% – 302%)
- **W19**: 6 pass / 33 fail (after duplicate-staff fix: Cadena A H31
  113% → 2.08%, H32 158% → 14.39% — structural drift collapsed but
  total fail count unchanged because remaining failures are dominated
  by Cadena C unmodeled, financial layer missing, GMF base mismatch)

### 1.3 Five structural root causes

1. **Request reconstruction incomplete** — Excel V2-7 carries 28 implicit
   staff profiles (Director 1:750, GTR 1:200, Supervisor 1:70, ...);
   the engine request only supplies front-line agents.
2. **Ramp-up table not propagated** — `linea_negocio="Captura de Datos"`
   yields backend ramp=0 for every month; Excel uses 0.9/0.95/1.0 from
   M6 onward.
3. **Cadena C semantic gap** — HITL costs, escalation rates, OPEX
   variable structure are not modeled. Excel Cadena C costo total
   $29.1B; backend ≈ 0.
4. **Financial layer incomplete** — GMF base divergence (Excel: cost+
   income; backend: cost only), admin commission 1.18% missing, ICA on
   different base, financial cost of working capital absent.
5. **Dual execution paths** — W9 "Clean Architecture" extracted formulas
   into `domain/` but `calculators/` still owns the runtime path.
   Mutation tests confirm `domain/` functions are not exercised.

---

## 2. The Six Phases

### F1 — Freeze & Reality Alignment **(in progress)**

**Purpose.** Stop the false certification narrative. Block the PR.
Re-baseline docs against measured reality. Zero engine code modified.

**Deliverables.**
- `PR_DESCRIPTION.md` (repo root) replacing previous triumphant body
- Two `CERTIFICACION_*.md` renamed `_DEPRECATED_*.md` with banner
- Post-W17 disclaimers on `WAVE{3,4,5,6,7,8,9,10,13,14,15}_REPORT.md`
- `docs/v27/SEMANTIC_RECONSTRUCTION_PROGRAM.md` (this file)
- `tests/parity/CURRENT_ORACLE_STATUS.md` with current pass/fail/drift
- No regression: suite stays at 892 passed / 33 failed / 25 skipped

**Exit criteria.** No document in `docs/v27/` claims certified parity
without a disclaimer. Status page exists. PR body honest.

---

### F2 — Request Model Reconstruction

**Purpose.** Materialize the 28 implicit staff profiles that Excel V2-7
auto-derives via `Condiciones Cadena A!E25:F48` ratios. Make the engine
request reproduce Excel's pre-loaded case verbatim.

**Deliverables.**
- Real-ratio expander: `ratios + frontline_count → 28 staff perfiles`
- `tests/parity/fixtures/excel_v2_7_real_request.json` regenerated with
  full perfil list, sourced from Excel cells (no hardcodes)
- Ramp-up table parametrized from `linea_negocio` taxonomy
- Oracle pass count target: ≥18 / 41 (Cadena A H31/H32/H41/H67/C40-C47
  all green)

**Exit criteria.** All Cadena A oracle cells pass with drift = 0.00%.
Ramp-up M6-M12 matches Excel cell-for-cell.

---

### F3 — Runtime Unification

**Purpose.** Eliminate the dual execution path. The runtime must call
`domain/` functions; `calculators/` legacy must be decommissioned or
become a thin shim that delegates.

**Deliverables.**
- Mutation tests on `domain/finance/*` and `domain/payroll/*` detect
  ≥90% of seeded mutations
- `calculators/cost_to_serve.py`, `calculators/nomina.py`,
  `calculators/vision_tarifas.py` either deleted or fully delegating
- Single source-of-truth function per formula (no duplicates)

**Exit criteria.** Mutation tests prove the runtime exercises `domain/`.
No formula has two implementations.

---

### F4 — Financial Layer Reconstruction

**Purpose.** Restore the financial layer Excel applies that backend
omits or computes on a different base.

**Deliverables.**
- GMF computed over `cost + income` (Excel `Visión P&G!H67`)
- Comisión Administrativa 1.18% line item (Excel Panel!Cxx)
- ICA base aligned with Excel
- Financial cost of working capital (cadena financing)
- Pólizas as separate explicit line

**Exit criteria.** Oracle cells `Visión P&G!H67` (GMF), `C43-C45`
(ICA/GMF/Pólizas), `C72` (Facturación Total) pass with drift = 0.00%.

---

### F5 — Cadena C Semantic Reconstruction

**Purpose.** Implement the HITL cost model Excel uses for Cadena C.
Today backend Cadena C produces ≈ 0 vs Excel's $29.1B.

**Deliverables.**
- HITL volume × tarifa engine
- Escalation rate parametrization from Excel
- OPEX variable structure for human-in-the-loop providers
- Cadena C oracle cells: `C60` (Costo Total), `C67` (Ingreso), CTS
  ponderado, P&G H55 (Costos Cadena C)

**Exit criteria.** Cadena C oracle cells pass with drift = 0.00%.

---

### F6 — Oracle Expansion (Validation Mesh)

**Purpose.** Lift coverage from 41 mapped cells to ≥100 spanning
every sheet (Vision Tarifas, Vision Cost To Serve, Visión P&G, Vision
Sensibilidad, Vision Decisión).

**Deliverables.**
- 100+ cells in `tests/parity/excel_oracle_v2_7_full.json` with
  `backend_path` resolved
- Sheet-level coverage report
- Continuous parity gate in CI (`pytest -m oracle` must be green)

**Exit criteria.** ≥100 oracle assertions, **all green at 0.00% drift**.

---

## 3. Definition of Done (Program Level)

The program is complete only when ALL of the following hold:

1. All oracle tests (≥100 cells in F6) pass with drift = **0.00%**
2. No hardcoded values, no `business_overrides.json` entries, no
   normalization tricks remain
3. Single execution path: `calculators/` legacy decommissioned
4. Full traceability from `request → backend value → Excel cell →
   formula` is exposed via the lineage endpoint
5. Mutation testing detects ≥90% of seeded mutations across all
   `domain/` modules
6. The two `_DEPRECATED_CERTIFICACION_*.md` files can be re-instated
   as `CERTIFICACION_*.md` — but only by the program lead, only
   after CI proves all six criteria above

Until that day, **no PR merges to `main`** from `refactor/engine-v2`.

---

## 4. Working Rules

- Excel V2-7 is the only source of truth.
- Never modify oracle expected values to match backend.
- Never mark oracle failures as `xfail`/`skip` to hide drift.
- Never claim parity in a doc without a passing oracle test as proof.
- Each phase commits independently. Each phase produces a `Wxx_REPORT.md`
  with honest pass/fail numbers.
- `legacy_circular` tests stay deselected by default and may NOT be
  used to substantiate parity claims.

---

## 5. References

- `W16_VERIFICATION_REPORT.md` — forensic audit (eight hacks)
- `WAVE17_REPORT.md` — first honest oracle measurement
- `WAVE18_REPORT.md` — structural diagnoses
- `WAVE19_REPORT.md` — duplicate staff fix, Cadena A drift collapse
- `tests/parity/excel_oracle_v2_7_full.json` — 333 oracle cells
- `tests/parity/CURRENT_ORACLE_STATUS.md` — live status
- `PR_DESCRIPTION.md` (repo root) — merge-block notice
