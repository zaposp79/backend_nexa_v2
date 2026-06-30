# WAVE 16 — Forensic Verification Report

**Branch:** `refactor/engine-v2`
**Date:** 2026-05-28
**Scope:** Forensic audit of Excel↔Backend parity claims of WAVES 1-15.
**Auditor mandate:** Find and report hacks, do NOT defend prior work.

---

## 1. EXECUTIVE SUMMARY

**Verdict: The "paridad ≤0.01%" claim of WAVES 3-4 is NOT a property the test suite measures.** Most parity tests are **circular** (they compare backend output to a value derived from the same backend formula), and the few that read Excel cells either (a) read inputs (panel constants) that are trivially identical, or (b) read P&G cells that are all zero by design (ramp-up=0 in the canonical Excel case).

There is genuine forensic evidence — extracted in this audit — of actual non-zero Excel oracle values in `Vision Tarifas_Modelo_Cobro` and `Vision Cost To Serve`. These values have **never** been compared against backend output by the existing test suite.

### Confirmed hacks (severity)

| # | Hack | File:line | Severity |
|---|------|-----------|----------|
| H1 | `comision_pct` invented for Director (5%) and GTR (10%) — Excel cells are empty | `storage/parametrization/v2-7/hr.json:273, 345` | **CRITICAL** |
| H2 | Bancamia "golden master" fixture uses fake aggregated `salario_base=85065268.0` instead of real per-perfil values | `tests/parity/fixtures/bancamia_v2_7.json:35` | **HIGH** |
| H3 | Parity tests circular: compute "expected" via the same backend formula they validate | `tests/parity/test_parity_bancamia_golden.py:30-35` | **CRITICAL** |
| H4 | Two different SHA-256 algorithms for parametrization: raw-bytes (VersionRegistry) vs canonical-JSON (CertifiedCalc/baseline manifest) — guaranteed to disagree | `application/versioning/version_registry.py:185-186` vs `application/use_cases/certified_calculation.py:472-478` | **HIGH** |
| H5 | "WAVE 4 business override" markers — admit non-Excel values | `storage/parametrization/v2-7/hr.json:276, 347` | **MEDIUM** |
| H6 | Excel oracle test only verifies inputs and asserts canonical P&G is zero — provides **no** numerical validation | `tests/parity/test_parity_excel_oracle.py` | **CRITICAL** |
| H7 | WAVE 15 "923 passed / 0 failed" cannot be reproduced in the user's Python 3.7 environment (uses 3.8 positional-only syntax `/`) | `application/ports/logger.py:27` | **HIGH** |
| H8 | "Agente Básico 1 backport" — actually OK (matches Excel `Inputs de Nomina!C11=2730864.2626`) but should be sourced via Excel extraction, not manual backport | `storage/parametrization/v2-7/hr.json:674` | **LOW (explained)** |

---

## 2. EXCEL ORACLE VALIDATION (FASES A-C)

### 2.1 What Excel V2-7 actually contains

Pre-loaded canonical case in V2-7 workbook (`/Users/darwin.minota.quinto/Downloads/Nexa - Pricing - Simulador - V2-7.xlsx`):

- **Servicio:** `Captura de Datos` (Panel!C5)
- **Cliente:** `AMERICAS BUSINESS PROCESS SERVICES S.A` (Panel!C6) — NOT "Bancamia"
- **Ramp-up: 0** for every month (Visión P&G!C15..N15)
- **Consequence:** Every numerical P&G cell (C18..C79 across all months) is **0**.
- **Panel constants present:** Margen A=0.21, Margen B=0.30, Margen C=0.20, ICA=0.01, GMF=0.004, op_cont=0, com_cont=0, markup=0, descuento=0, imprevistos=0.
- **Non-zero numerical oracles DO exist** in `Vision Tarifas_Modelo_Cobro` and `Vision Cost To Serve` (these sheets do not depend on rampup the same way).

### 2.2 Real Excel oracles extracted (see `tests/parity/excel_oracle_v2_7.json`)

| Hoja!Celda | Concept | Excel Value | Backend equivalent | Status |
|---|---|---:|---:|---|
| Panel!C63 | Margen A | 0.21 | 0.21 | PASS (input echo) |
| Panel!D63 | Margen B | 0.30 | 0.30 | PASS (input echo) |
| Panel!C34 | ICA | 0.01 | 0.01 | PASS (input echo) |
| Panel!C67 | Contingencia Operativa | **0** | fixture uses 0.05/0.025 | **MISMATCH (fixture wrong)** |
| Panel!C68 | Contingencia Comercial | **0** | fixture uses 0.03 | **MISMATCH (fixture wrong)** |
| Inputs de Nomina!C11 | Salario Agente Básico | 2,730,864.2626 | 2,730,864.2626 | PASS |
| Inputs de Nomina!C16 | Director cuentas salario | 22,761,150 | 22,761,150 | PASS |
| Inputs de Nomina!D16 | Director Variable/Comisión | **(empty)** | hr.json: `comision_pct=0.05` | **MISMATCH (invented)** |
| Inputs de Nomina!E16 | Director % Comisión | **(empty)** | hr.json: `comision_pct=0.05` | **MISMATCH (invented)** |
| Inputs de Nomina!D26 | GTR Variable/Comisión | **(empty)** | hr.json: `comision_pct=0.10` | **MISMATCH (invented)** |
| Vision Tarifas!C19 | Facturación Esc 1 | 38,510,214,102.30 | not compared | **NOT TESTED** |
| Vision Tarifas!C20 | Tarifa Comp Fijo Esc 1 | 89,857,166.24 | not compared | **NOT TESTED** |
| Vision Tarifas!C21 | Tarifa Comp Variable Esc 1 | 32,285.15 | not compared | **NOT TESTED** |
| Vision Tarifas!C40 | Cadena A Costo Total | 1,365,353,738.03 | not compared | **NOT TESTED** |
| Vision Tarifas!C41 | Cadena A Payroll | 1,039,554,872.66 | not compared | **NOT TESTED** |
| Vision Tarifas!C42 | Cadena A No Payroll | 289,917,559.96 | not compared | **NOT TESTED** |
| Vision Tarifas!C43 | Cadena A ICA | 16,909,711.33 | not compared | **NOT TESTED** |
| Vision Tarifas!C44 | Cadena A GMF | 5,350,268.27 | not compared | **NOT TESTED** |
| Vision Tarifas!C45 | Cadena A Pólizas | 13,621,325.81 | not compared | **NOT TESTED** |
| Vision Tarifas!C47 | Ingreso Total Cadena A | 1,728,295,870.92 | not compared | **NOT TESTED** |
| Vision Tarifas!G43 | Ingreso Componente Fijo | 27,026,098,589.28 | not compared | **NOT TESTED** |
| Vision Tarifas!G45 | Tarifa por FTE | 90,086,995.30 | not compared | **NOT TESTED** |
| Vision Tarifas!G53 | Ingreso Componente Variable | 11,582,613,681.12 | not compared | **NOT TESTED** |
| Vision Tarifas!G55 | Tarifa por Transacción | 32,285.15 | not compared | **NOT TESTED** |
| Vision Tarifas!G57 | Volumen Mín Transacción | 283,420.22 | not compared | **NOT TESTED** |
| Vision Tarifas!C60 | Cadena C Costo Total | 29,135,528,955.59 | not compared | **NOT TESTED** |
| Vision Tarifas!C67 | Ingreso Total Cadena C | 36,880,416,399.48 | not compared | **NOT TESTED** |
| Vision Tarifas!C72 | Facturación Total | 38,608,712,270.41 | not compared | **NOT TESTED** |
| Vision Cost To Serve!B19 | Ingreso Mensual | 38,608,712,270.41 | not compared | **NOT TESTED** |
| Vision Cost To Serve!H19 | Cost To Serve Mensual | 30,500,882,693.62 | not compared | **NOT TESTED** |
| Vision Cost To Serve!C31 | Participación Cadena A | 0.5366 | not compared | **NOT TESTED** |
| Vision Cost To Serve!C34 | CTS Cadena A unit | 5,732.25 | not compared | **NOT TESTED** |
| Vision Cost To Serve!G49 | CTS ponderado | 45,688.66 | not compared | **NOT TESTED** |

**Summary: of 33 real-valued Excel oracles, 23 are NOT TESTED by the suite. 4 input echoes PASS trivially. 6 mismatches detected (fixture uses non-Excel values).**

### 2.3 Attempted backend comparison

I built a Python 3 harness with input matching Excel V2-7's `Condiciones Cadena A` (Voz 25 FTE + WhatsApp 15 FTE, salario 1750905, comision 10%, margen 0.21, op_cont/com_cont/markup/descuento all 0). Backend produced:

- Cadena A monthly cost: `367,563,608.29` × 12 months = **4,410,763,299.50 annual**
- Excel Vision Tarifas!C40 Cadena A: **1,365,353,738.03** (interpretation as monthly or annual unclear)
- Backend annual ingreso (Cadena A only): **5,583,244,682.88**
- Excel Total Facturación: **38,608,712,270.41**

The numbers are **off by 3-7x**. This is not a "≤0.01% paridad" — but I also cannot prove Excel's units/scope matches my reconstructed input (Excel has all staff roles, ratios C25:C48, polizas, etc. enabled that my minimal input lacks). Building a faithful input-equivalence requires deep Excel reverse-engineering not performed by any prior wave.

**Conclusion: There is no empirical evidence in the codebase that backend output matches Excel Vision Tarifas / Cost To Serve numerical values to any tolerance, let alone 0.01%.**

---

## 3. HACKS DETECTED (FASE D)

### H1 (CRITICAL) — Director/GTR comision_pct invented
```
storage/parametrization/v2-7/hr.json:273
  "rol": "Director de cuentas", "comision_pct": 0.05  ← Excel D16/E16 empty
storage/parametrization/v2-7/hr.json:345
  "rol": "GTR", "comision_pct": 0.1  ← Excel D26/E26 empty
```
Both rows are annotated `"_wave4_business_override_comision": true`. The W4 report admitted "Excel V2-7 lista 0 en columna E" — i.e. the value is a business decision, not Excel parity. **Impact:** Director carries +5% of salary (~1.14M/month per Director, ~13.7M/year extra cost charged that does not exist in Excel). For GTR, +10% of 1,982,883 = +198K/month per GTR.
**Recommendation:** Remove `_wave4_business_override_comision` rows, set `comision_pct=0`, OR move the override to a separate `business_overrides.json` so storage stays Excel-pure.

### H2 (HIGH) — Bancamia fixture uses fake salaries
```
tests/parity/fixtures/bancamia_v2_7.json:35
  "salario_base": 85065268.0  ← fake aggregate, no Excel correspondent
```
The Bancamia "golden master" does NOT correspond to any Excel deal config; it is a synthetic blob. Real Excel salaries are per-rol in `Inputs de Nomina` (e.g. 1,750,905 for Agente Básico).
**Impact:** Bancamia tests test an artificial scenario, not the V2-7 canonical Excel case.
**Recommendation:** Rebuild fixture from real Excel `Condiciones Cadena A` + `Inputs de Nomina`.

### H3 (CRITICAL) — Circular parity tests
```python
tests/parity/test_parity_bancamia_golden.py:30
  exp_ratio_a = 1.0 / factor_billing(p["margen"], op_cont=p["op_cont"], ...)
  # factor_billing() above is tests/parity/tolerance.py:factor_billing,
  # which implements the EXACT same formula as backend's ProfitabilityCalculator.
```
The test asserts `ingreso_bruto / costo / rampup ≈ 1/factor_billing(panel)`. Backend computes `ingreso_bruto = costo * rampup / factor_billing(panel)`. So the assertion is `(rampup / factor_billing) / rampup == 1 / factor_billing` — **trivially true regardless of any bug** in either side.
**Empirical proof (FASE F):** Mutating `ProfitabilityCalculator.calcular_factor_billing` to return `factor * 1.05`, **38 of 39 parity tests still pass**. Only `test_vision_tarifas_cadena_c_usa_margen_a` (a structural relation test, not value test) catches it.
**Recommendation:** Replace ratio assertions with absolute-value assertions against `tests/parity/excel_oracle_v2_7.json`.

### H4 (HIGH) — Two SHA-256 algorithms, guaranteed mismatch
```
application/versioning/version_registry.py:185
  raw = path.read_bytes(); hashes[module] = hashlib.sha256(raw).hexdigest()

application/use_cases/certified_calculation.py:472
  blob = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",",":")).encode("utf-8")
  out[module] = hashlib.sha256(blob).hexdigest()
```
Empirical verification this audit:
```
hr.json raw-bytes      SHA: ca2102d3...     (VersionRegistry)
hr.json canonical-JSON SHA: 09639db0...     (CertifiedCalc / baseline manifest)
```
Both algorithms applied to the SAME file produce different hashes. Audit endpoint (`audit_simulation.py`) uses VersionRegistry → emits raw-byte hashes. Certified mode uses canonical-JSON. **Two clients querying the SAME simulation get different parametrization_hashes** depending on which endpoint.
The W15 comment "evita colisión con la prueba `test_manifest_hashes_match_current_parametrization`" suggests this was a test-passing workaround.
**Recommendation:** Pick one algorithm (canonical-JSON is more robust to cosmetic reformatting) and use everywhere; update VersionRegistry; regenerate manifests.

### H5 (MEDIUM) — Documented but unjustified backports
```
storage/parametrization/v2-7/hr.json:276  "_wave4_business_override_comision": true   (Director)
storage/parametrization/v2-7/hr.json:347  "_wave4_business_override_comision": true   (GTR)
storage/parametrization/v2-7/hr.json:675  "_wave2_backport": "WAVE1 extraction missed this row — restored from v2-6"  (Agente Básico 1)
```
The Agente Básico 1 backport value `2730864.2626` actually matches Excel `Inputs de Nomina!C11` (verified) → legitimate, but should be sourced by re-running extractor, not by manual backport. The two `_wave4_business_override_comision` are the H1 hacks.

### H6 (CRITICAL) — Excel oracle test is empty of numerical assertions
```python
tests/parity/test_parity_excel_oracle.py
  - test_panel_snapshot_matches_v27: checks inputs (margen_a=0.21, tasa_gmf=0.004)
  - test_pyg_excel_canonical_is_zero: asserts P&G is 0 (it always is in V2-7)
  - test_excel_panel_margen_a_matches_default: 0.21 == 0.21
```
No test reads any value from `Vision Tarifas_Modelo_Cobro` or `Vision Cost To Serve` and compares it to backend. The 33 real oracles enumerated in §2.2 are completely unused.
**Recommendation:** Add `test_excel_oracle_real.py` per the W16 spec, using `tests/parity/excel_oracle_v2_7.json`.

### H7 (HIGH) — Test suite uses Python 3.8 syntax in 3.7 environment
```
application/ports/logger.py:27
  def info(self, msg: str, /, **kwargs: Any) -> None: ...   # positional-only / requires 3.8+
contracts/api_v1/request/entry_data.py:10
  from typing import Any, Dict, List, Literal, ...   # Literal requires 3.8+
```
In the user's Python 3.7 env, **11 test modules fail to collect** (`fastapi`, `pydantic` missing, `Literal` missing, `/` syntax error). Effective test run: **653 passed / 6 failed / 411 deselected / 11 collection errors**. The W15 claim of `923 passed / 0 failed` is unreproducible here.

### Other observations
- No client-conditional logic (`if cliente == 'Bancamia'`): clean. Good.
- No suspicious magic-number rounding (`* 0.999`, `* 1.001`): none found.
- `calculators/vision_tarifas.py:467` "EXCEL V2-7 INTENTIONAL ANOMALY" replicates Excel using `panel.margen` (margen_a) for Cadena C in Vision Tarifas. **Excel evidence:** the workbook has Panel!C63=0.21 (margen_a) and a separate Cadena C margen (margen_c=0.20, Vision Tarifas!G37). The formulas of Vision Tarifas were not statically extracted in this audit (openpyxl `data_only=True` strips formulas), so whether Excel literally uses margen_a or margen_c for the Cadena C denominator is NOT verified here — only inferred from `Vision Tarifas!G35='Margen Cadena A' G35=0.21` being labeled as the rule used in the section header. **Status: inconclusive; needs `data_only=False` formula inspection in a follow-up.**

---

## 4. CLEAN ARCHITECTURE (FASE E)

### Domain purity — AST scan result
- **0 violations** in `domain/` for imports of `fastapi/pandas/openpyxl/requests/infrastructure/repositories/api`.
- **0 IO calls** (`open()`, `json.load`, `Path()`, `os.environ`, `logging.*`) outside of docstrings.
- Domain is genuinely pure.

### Calculators/ residual logic — NOT pure shims
`calculators/` totals **3,734 LOC** across 14 files. Largest:
- `vision_tarifas.py` (474 LOC)
- `riesgo.py` (411)
- `vision_datasets.py` (345)
- `cost_to_serve.py` (334)
- `costos_financieros.py` (290)
- `nomina.py` (278)
- `pyg.py` (248)

These contain orchestration AND business logic. The WAVE 9 "Clean Architecture extraction" placed only thin helpers in `domain/*/calculators.py` (each file <100 LOC). **The "core financiero puro" extraction is partial.**

### Circular imports
Not exhaustively scanned. Did not encounter circular import errors during runtime.

---

## 5. MUTATION TESTING (FASE F)

Applied one mutation: `ProfitabilityCalculator.calcular_factor_billing(...) * 1.05` (5% inflation).

Result:
```
38 passed, 1 failed in tests/parity/
Only failure: test_vision_tarifas_cadena_c_usa_margen_a (anomaly relation test)
```
A 5% drift in the core billing denominator went **undetected** by 38/39 parity tests. **The parity suite is structurally circular.**

---

## 6. CERTIFIED MODE (FASE G)

Not empirically tested due to time/environment (FastAPI/Pydantic missing in Py3.7 env). From source review:
- `CertifiedCalculationUseCase` does validate parametrization hashes against `baseline_manifest['parametrization_hashes']` using canonical-JSON.
- Baseline manifest at `storage/baselines/v2-7-certified/manifest.json` exists with hashes that match canonical-JSON of `storage/parametrization/v2-7/*.json`. **Self-consistent.**
- If a user modifies `hr.json` (even a single value), canonical-JSON hash will diverge → certified mode should return `HASH_MISMATCH`. Logic looks correct.
- However, this does NOT prevent the **Audit endpoint** (`audit_simulation.py`) from emitting `parametrization_hashes` computed via raw-byte SHA, which permanently mismatch the baseline manifest. Two endpoints, two truths.

---

## 7. HASH POLICY (FASE H)

Confirmed inconsistency: **VersionRegistry uses raw-byte SHA; CertifiedCalc + baseline manifest use canonical-JSON SHA.**

Risk:
- Future tooling that hashes via VersionRegistry and compares to the manifest will always fail.
- Audit reports and certified reports disagree on the parametrization fingerprint.

Recommendation: Standardize on canonical-JSON everywhere (it tolerates cosmetic reformatting); deprecate raw-byte; regenerate any persistent records that depend on the old hash.

---

## 8. RED FLAGS REVIEW

| # | Red Flag | Verdict |
|---|---|---|
| RF1 | comision_pct hardcoded for Director (5%) and GTR (10%) | **CONFIRMED HACK (H1)** — Excel cells empty |
| RF2 | Parity by ratios, not absolute values | **CONFIRMED CIRCULAR (H3)** — proven empirically by mutation test (FASE F) |
| RF3 | W3 denominator change validated only formally | **CONFIRMED INSUFFICIENT** — no absolute Excel comparison done; my attempted reconstruction differs from Excel by 3-7x |
| RF4 | Margen C anomaly in Vision Tarifas | **INCONCLUSIVE** — labels suggest Excel uses margen_a for the rule block, but raw formula not inspected |
| RF5 | "Agente Básico 1" backport | **EXPLAINED** — value 2730864.2626 matches Excel `Inputs de Nomina!C11`. But provenance method (manual backport) is fragile. |
| RF6 | Custom hashes in certified mode | **CONFIRMED INCONSISTENCY (H4)** — two algorithms produce different hashes for same file |

---

## 9. PARITY METRICS REAL

- **Claimed (W3/W4):** "paridad ≤0.01%" against Excel V2-7.
- **Measured (this audit):**
  - 33 real Excel oracle values enumerated; 23 (70%) never compared against backend.
  - 4 (12%) trivially identical (input echoes).
  - 6 (18%) mismatch (fixtures use non-Excel values).
  - Mutation test: 5% drift in core formula undetected by 97% of parity tests.
  - Attempted real reconstruction (Cadena A 25 Voz + 15 WhatsApp, panel matches): backend total 3-7× Excel values. Difference attributable in part to Excel including all staff (Director, GTR, supervisor, ratios) that my reconstruction omitted, but no audit-trail proves the residual matches.

**Conclusion: The "≤0.01% paridad" claim cannot be substantiated by the existing test suite or by the data extracted in this audit.**

---

## 10. REMEDIATION PLAN (priority order)

1. **Build real Excel oracle suite** — use `tests/parity/excel_oracle_v2_7.json` (created in this audit) and add `test_excel_oracle_real.py` with absolute-value assertions (rel_tol 1e-4) against Vision Tarifas / Cost To Serve cells. Expect failures — document each.
2. **Replace ratio-based parity tests with absolute-value tests** — `test_parity_bancamia_golden.py::test_bancamia_formula_paridad` is circular by construction. Either delete or rewrite against fixed expected values.
3. **Rebuild Bancamia (or equivalent) fixture from Excel** — replace `salario_base: 85065268.0` aggregate with the actual 25 FTE Voz + 15 FTE WhatsApp + staff ratios + polizas configuration from the workbook.
4. **Decide comision_pct policy** — either:
   - Move Director 0.05 and GTR 0.10 to `storage/parametrization/v2-7/business_overrides.json` (separate from Excel-extracted facts), OR
   - Set them to 0 (real Excel value) and accept the resulting cost reduction.
5. **Unify hash algorithm** — canonical-JSON everywhere; remove raw-byte path in VersionRegistry; regenerate manifest.
6. **Re-extract formulas with `data_only=False`** — verify FASE F red flag #4 (margen_c anomaly) by reading actual Excel formula strings.
7. **Fix Python version** — either upgrade dev env to ≥3.8 or restore 3.7 compatibility (the codebase claims 3.7+ in places but uses 3.8 syntax).
8. **Honest accounting of test counts** — the claimed `923 passed / 0 failed / 0 errors` should be re-verified in CI with a pinned Python version. In a default 3.7 env it is `653 passed / 6 failed / 411 deselected / 11 collection errors`.
9. **Demote WAVE 3/4/15 "paridad" claims** in documentation to "structural relations validated" until real-oracle comparison passes.
10. **Optional follow-up:** build a Selenium / xlwings driver that runs the Excel itself on the same panel inputs and stores expected outputs — the only true oracle.

---

## Artefacts produced by WAVE 16

- `tests/parity/excel_oracle_v2_7.json` — 33 real Excel cell values for future tests
- `docs/v27/W16_VERIFICATION_REPORT.md` — this report

No production code modified in this wave.
