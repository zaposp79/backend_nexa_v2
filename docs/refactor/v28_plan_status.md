# Estado del Plan V2-8 Parity

## INPUT_PCT_ACUM_AUDIT_POST_V28_CLOSURE — COMPLETED (2026-06-12)

**Classification: `NO_IMPACT / RECOMMEND_NO_ACTION`**

`porcentaje_acumulado` is a dead field. Full RCA: `docs/refactor/input_pct_acum_audit_post_v28_closure.md`

| Finding | Evidence |
|---------|----------|
| `Panel!C75` value | 0 (formula `=SUM(C67:C69)-C70`, all inputs=0 for this deal) |
| `Panel!C75` downstream refs | **0** — no cross-sheet references; display-only cell |
| Engine consumption | `DEAD_FIELD_LEGACY` — removed in BUSINESS_RULES_FIX_3; `ValueError` guard if re-added |
| Request value | `actual: 0` — already pre-aligned with Excel |
| Impact on P&G | **0** |
| Impact on Vision Tarifas | **0** |
| Impact on CTS | **0** |
| Classification | `NO_IMPACT` |
| Recommendation | `RECOMMEND_NO_ACTION` |
| Functional changes | 0 — read-only audit |

`INPUT-PCT-ACUM` backlog item closed. No further action required.

---

## V28_FINAL_CLOSURE_STATUS — COMPLETED (2026-06-12)

**V2-8 phase formally closed as stable.** All active blockers resolved or classified as accepted deltas. No functional changes required.

| Category | Status | Evidence |
|----------|--------|----------|
| Golden suite | 99/99 PASS ✅ | Full test run before closure |
| Baseline validation | ✅ PASS | make verify: Baseline match. Sin drift. |
| Excel gate | PASS 6/6 ✅ | validate-excel-v28: all checks pass (1 skipped HME cache) |
| CTS-001 | CLOSED_ACCEPTED_DELTA | -6.150 COP/tx (-0.099%), below 0.5% gate |
| CTS-002 | FORMALLY_CLOSED | K34 exact match (2.24e-6) |
| Active blockers | 0 | All resolved or deferred to next phase |
| Functional changes this session | 0 | Documentation only |

**Full closure document:** `docs/refactor/v28_final_closure_status.md`

**Recommendation:** Close V2-8 and move exact-parity residuals (training/fixed-cost) to optional backlog if escalated by business.

---

## CTS_001_FORMAL_CLOSE_ACCEPTED_DELTA — COMPLETED (2026-06-12)

**Commit:** `5802a81` — `fix(v28): align CTS-001 support FTE overrides with Excel`

CTS-001 formally closed as `ACCEPTED_DELTA`.

| Metric | Before support FTE fix | After support FTE fix (5802a81) |
|--------|------------------------|--------------------------------|
| Excel C34 | 6,224.575126 COP/tx | 6,224.575126 COP/tx |
| Backend | 6,204.197492 COP/tx | **6,218.424663 COP/tx** |
| Delta COP/tx | -20.378 | **-6.150** |
| Delta % | -0.327% | **-0.099%** |
| Gate (0.5%) | ✅ within | **✅ within** |
| Status | PAUSED_KNOWN_DELTA | **✅ CLOSED_ACCEPTED_DELTA** |

**Validation (final):**
- golden suite: 99/99 PASS ✅
- make verify: ✅ Baseline match. Sin drift.
- validate-excel-v28: PASS 6/6 ✅
- support_fte: 12/12 PASS ✅
- PyG: 7/7 PASS ✅

**Residual -6.150 COP/tx explanation:**
- Training/Exam/Crucero: ~-3.85 COP/tx → KNOWN_DELTA_TRAINING
- Costos_fijos_estacion: ~-3.17 COP/tx → KNOWN_DELTA_COSTOS_FIJOS
- SENA/Inclusión ramp snapshot: minor residual → ACCEPTED_DELTA

**Functional changes in this session:** 0 (docs only).
**CTS-001 is no longer an active blocker.**

---

## CTS_001_INCLUDED_ROLES_SALARY_DEFICIT_AUDIT — COMPLETED (2026-06-12)

Golden: **96/96 PASS** | verify | validate-excel-v28 PASS 6/6. **Functional changes: 0.**

Target: the **-79.46 COP/tx underlying deficit** in correctly-included roles (excl. JCR/AFAC/GTR).

**Root cause PROVEN — resolves the prior `MAPPING_AMBIGUOUS`:**
The deficit is ~99.75% the `Director de Performance` channel FTE. `'Condiciones Cadena A'!G78`
is a **hardcoded literal `1.0`** (vs the ratio formula in E78/F78); backend derives ≈0.073.
Excel FTE 1.16 vs backend 0.233 × loaded 18,902,979 = **+79.264 COP/tx (99.75% of −79.46)**.
Same per-role channel-literal class as `Supervisor E95 = 9.5` (DEFERRED).

Disproven hypotheses: agent salary (Nomina Loaded 925,853,204 = backend EXACT) and SENA/Inclusión
salary (factors match; residual ≈−6.6 is ramp snapshot = ACCEPTED_DELTA).

**Recommended fix (not implemented):** generalize `fte_soporte_overrides` to **per-channel** literals
(carry G78 Director Performance WhatsApp=1.0 alongside E95 Supervisor=9.5), and apply it
**together** with `ROLES-OP-STAFFCONFIG` (exclude JCR/AFAC/GTR) — fixing either alone regresses CTS-001.

**Full RCA:** `docs/refactor/cts_001_included_roles_salary_deficit_audit.md`

---

## CTS_001_RESUME_FROM_CLEAN_BASELINE — COMPLETED (2026-06-12)

Golden: **96/96 PASS** ✅ | verify ✅ | validate-excel-v28 PASS 6/6 ✅

| Metric | Value |
|--------|-------|
| Excel C34 | 6,224.575126 COP/tx |
| Backend | 6,204.197492 COP/tx |
| Delta | **-20.378 COP/tx (-0.327%)** |
| Prior state | -27.53 COP/tx (-0.44%) |
| Improvement | **+7.15 COP/tx** |
| Gate (3%) | ✅ WITHIN |

**Decision:** `PAUSED_KNOWN_DELTA` maintained. Residual dominated by `CTS_SUPPORT_LOADED_MAGNITUDE` (-13.37 salary loaded) + `KNOWN_DELTA_TRAINING` (-3.85) + `KNOWN_DELTA_COSTOS_FIJOS` (-3.17). OPEX fijo + CAPEX = EXACT MATCH. E95=9.5 = MATCH. Denominator = MATCH.

**Functional changes:** 0. Docs only.  
**Full RCA:** `docs/refactor/cts_001_resume_from_clean_baseline.md`

---

## V27_FIXTURE_REGEN_CONTROLLED — COMPLETED (2026-06-12)

Golden suite: **0 fail / 96 pass** ✅

| Category | Before | After |
|----------|--------|-------|
| `V27_CTS_FIXTURE_DRIFT` | 13 | 0 |
| `V27_VT_FIXTURE_DRIFT` | 11 | 0 |
| Total failures | 24 | **0** |

- **Fixtures updated:** `cts_v27_real_request.json` (13 fields) + `vt_v27_real_request.json` (11 fields)
- **Root cause:** OP `tasa_financiacion` 0.0088→0.0153 (`939a36a`) — financial costs propagated via cost-plus; frozen fixtures predated change
- **validate-excel-v28:** PASS 6/6 ✅ | **make verify:** ✅ Baseline match
- **Scope:** 0 modules touched, 0 request, 0 storage, 0 contracts, no `make baseline`

---

## E95_WIP_RESTORE_AND_COMMIT — COMPLETED (2026-06-12)

Golden suite: **24 fail / 72 pass** ✅

- **Fix:** `request/request.json` — `"fte_soporte_overrides": {"Supervisor": 9.5}` restaurado en perfil SAC Actual (Excel CCA!E95 literal). Supervisor FTE 7.1 → 9.5.
- **WIP committed:** `cadena_a.py` contract (CargoAdicionalV1, DetalleRecursoHumanoV1, Union type) + mixins (detalles_recursos_humanos support) + `test_support_fte_v28.py` (9 tests).
- **PyG anchor update:** `test_pyg_v28_ingreso_indexado.py` — M1/M7/M19 ingreso_a + ingreso_total refreshed. B/C anchors unchanged.
- **validate-excel-v28:** PASS 6/6 ✅ — IPC ratio M7/M6 = delta 0.000000000 (mechanism exact).
- **Remaining 24 failures:** PREEXISTING_INFRA_PARAMETRIZATION — V27 frozen fixtures drifted by OP parametrization. Deferred to V27-FIXTURE-REGEN session.

**Next (P2):** V27 golden fixture regeneration session → expected 0 fail / 96 pass.

---

## TRIAGE POST-CTS-002 — COMPLETED (2026-06-12)

Golden suite: **25 fail / 71 pass** (stable baseline, post CTS-002).

| Category | Count | Blocking V2-8? |
|----------|-------|----------------|
| `PREEXISTING_INFRA_PARAMETRIZATION` | 24 | No |
| `REQUEST_VALUE_GAP` (E95 override WIP) | 1 | No |

- **Root of 24 failures:** Active OP `tasa_financiacion` 0.0088→0.0153 (commit `939a36a`) drifted V27 frozen golden fixtures. No formula error — fixture regeneration needed.
- **Root of 1 failure:** `fte_soporte_overrides.Supervisor=9.5` removed from request.json in `b8b3000`; WIP in unstaged `user_input_builders_cadena_a.py` + `test_support_fte_v28.py`.
- **Next recommended:** Commit E95 WIP → 24 fail / 72 pass; then V27 fixture regeneration session.
- **validate-excel-v28:** PASS 6/6 ✅ — unaffected by any of the 25 failures.

See full triage: `docs/refactor/v28_remaining_gaps_triage_after_cts002.md`

---

## CTS-002 — COMPLETED (2026-06-12)

`FORMULA_PARITY_FAIL` resuelto: `cts_cadena_c` alineado con Excel `Costo Cadena C`!K34.

- **Excel K34:** `Costo Cadena C`!K34 = 5,278.326744819592 COP/tx = SUM(K35, K36, K40)
- **Backend antes:** 5,329.61 COP/tx (delta +51.28 — múltiples gaps: indexación + OPEX + inversiones + equipo)
- **Backend después:** 5,278.3267470588235 COP/tx — delta = 2.24e-6 (floating-point puro, 170,000 tx)

| Fix | Commit | Excel fuente | Cambio backend | Delta antes → después |
|-----|--------|--------------|----------------|----------------------|
| Technology indexation | `2d006cc` | Tasas!C15:G15 = 1.0 (0% efectivo) | `pct_aumento_tecnologico = 0.0` | +133.31 → -65.84 |
| Fixed OPEX | `ee1e7db` | Costo Cadena C!D136 22,230,000/mes → K37=130.76 | `opex_fijo_integ` desde `opex_items(tipo='Fijo')` | -65.84 → +64.92 |
| Inversiones (`ACCEPTED_EXCEL_QUIRK`) | `cd5bb6d` | K34=SUM(K35,K36,K40); K38=#REF!→0 excluido | `inversion_anual = 0` | +64.92 → -11.40 |
| Equipo transversal | `a146370` | salario_cargado=4,284,360.05 + herramientas=1,159,602.60/mes | pass-through adapter+mixin | -11.40 → **0.00** |

**Validación post-fix:**
- `validate-excel-v28`: PASS 6/6 (1 skipped) ✅ — sin regresión
- `test_cost_to_serve_golden_v27.py`: 25 pre-existing failures intactos ✅ (ninguna nueva regresión)
- `test_cts_001_v28.py`: 2/2 PASS ✅ — CTS-001 = PAUSED_KNOWN_DELTA (no reabierto)
- `test_cts_exam_crucero_v28.py`: 2/2 PASS ✅ — anchors estables
- `test_pyg_v28_ingreso_indexado.py`: 7/7 PASS ✅ — PyG anchors estables post-fix
- Golden suite: 25 fail / 71 pass (baseline pre-existente, sin cambio) ✅

**`ACCEPTED_EXCEL_QUIRK` — K38 (`inversion_anual`):** K38 usa referencia rota `#REF!` → efectivamente 0.
K34 no incluye K38. Backend espeja el comportamiento efectivo del Excel (no la intención de diseño original).

---

## VTM-001 — COMPLETED (2026-06-12)

`BACKEND_METRIC_NOT_EXPOSED` resuelto: `ingreso_mensual` ahora expone el valor mensual base (M3) en lugar del acumulado 24m.

- **Excel:** `Vision Tarifas_Modelo_Cobro`!H19 → `Hoja Maestra Escenarios`!C289 = 3,018,108,469.26 (ingreso mensual base, sin rampup)
- **Backend antes:** `ingreso_mensual = ingreso_total` = 67,306,856,754 (acumulado 24m)
- **Backend después:** `ingreso_mensual = pyg_por_mes[2].ingreso_bruto` = 3,076,257,253 (+1.9% HME cache delta — ACCEPTED_ARCHITECTURAL_DELTA)
- **Fuente modificada:** `modules/vision_tarifas/reglas.py:614`
- **Golden anchors actualizados:** `vt_cobranzas_outbound_fte.json` (659,715,695 → 57,873,559), `vt_v27_real_request.json` (38,631,742,871 → 2,057,008,752)
- **Invariant:** `n >= 3` guarda (fallback a `ingreso_total / n` para contratos cortos)
- **Delta:** +1.9% vs Excel H19 = `ACCEPTED_ARCHITECTURAL_DELTA` (HME usa snapshot estático; backend calcula dinámicamente)

**Validación post-fix:**
- `validate-excel-v28`: PASS 6/6 (1 skipped) ✅ — sin regresión
- `test_vision_tarifas_golden_v27.py`: 17 PASS / 11 FAIL (was 16/12 — 1 test fixed: `test_ingreso_mensual_total`) ✅
- `test_vision_imprimible_typed_contract.py`: 0 regresión ✅ (public_mapper usa `cruise_month.ingreso_neto`, no afectado)
- CTS-001: PAUSED_KNOWN_DELTA — sin cambio ✅
- Pre-existing failures: 25 en golden suite (todos previos, sin cambio) ✅

---

## PARAM_VALUE_FIX_P5_ROTACION_SAC — COMPLETED (2026-06-12)

`PARAM_VALUE_MISMATCH` resuelto: rotación SAC alineada con Excel V2-8.

- **Excel:** `Rot, Ausent y Rentabilidad`!F19 = 0.077175 (AVERAGE Sep=0.0609, Oct=0.0719, Nov=0.0931, Dic=0.0828)
- **Backend antes:** 0.09 (OP-Costo fallback, comentario "unchanged" en `_v28_deal_provider.py`)
- **Backend después:** 0.077175
- **Fuente modificada:** `tests/refactor/_v28_deal_provider.py:208` — campo `pct_rotacion_mensual` en `rotacion_ausentismo` SAC
- **Consumer:** `payroll_rotacion_mixin.get_pct_rotacion("SAC")` → `nomina.py` `capacitacion_rotacion`

**Validación post-fix:**
- `validate-excel-v28`: PASS 6/6 (1 skipped) ✅ — sin regresión
- `test_pyg_v28_ingreso_indexado.py`: 7/7 PASS ✅ — sin anchor drift
- `test_cts_001_v28.py`: 2/2 PASS ✅ — CTS-001 = PAUSED_KNOWN_DELTA (sin cambio)
- `test_cts_exam_crucero_v28.py`: 2/2 PASS ✅ — anchors exam/crucero estables
- `test_vision_tarifas_golden_v27.py`: 12 FAIL (KNOWN_PREEXISTING_FAILURE — sin cambio)
- `test_support_fte_v28.py`: 1 FAIL preexistente (`test_e95_supervisor_override_applied` — sin cambio)

**Impacto:** El cambio de rotación afecta `capacitacion_rotacion` (costo de entrenamiento por rotación).
El impacto es menor (~1.4% delta en tasa rotación) y ningún anchor V2-8 fue movido.

**CTS-001:** PAUSED_KNOWN_DELTA — no reabierto.

---

## ANCHOR_UPDATE_PYG — COMPLETED (2026-06-12)

`test_pyg_v28_ingreso_indexado.py`: 7/7 PASS ✅ (era 4 PASS + 3 FAIL)

Anchors actualizados en `TestPYGAbsoluteAnchorsV28` (M1/M7/M19 × ingreso_a/b/c/total):
- Causa: `tasa_ica` 0.01→0.00966 (REQUEST_FIX_P3) + alineación request cadena B/C (preexistente)
- Mecanismo IPC/indexación: INTACTO (ratios M7/M6 y M19/M18 exactos, 4 mechanism tests PASS)
- `validate-excel-v28`: PASS 6/6 (1 skipped) — sin regresión
- Preexistentes: tarifas 12/30 fail (sin cambio), CTS-001 2 fail (PAUSED_KNOWN_DELTA)

---

## OP_CONFIG_PROVIDER_FIX_P4 — COMPLETED (2026-06-12)

`validate-excel-v28`: PASS 6/6 checks (1 skipped) ✅

**Economic component:**
- Error inicial: `ParametrizationError: '20% SMMLV - 80% IPC' for year 2026 not found`
- Causa: active OP (`8992c36d`) tenía solo `IPC` y `SMLV` en OP-Componente — MISSING_EXISTING_FIELD
- Fix: agregadas 6 filas `'20% SMMLV - 80% IPC'` (años 2025-2030, valor=0.06616) al active OP JSON
- Fuente: `v2-8/op.json` (fixture ya tenía los valores correctos)
- Status: ECONOMIC_COMPONENT_2026_FIXED ✅

**tasa_financiacion:**
- Excel: 0.0153 · Backend anterior: 0.0088 (default, config sheet ausente)
- Fix: agregado `config` sheet a active OP con `tasa_financiacion_mensual=0.0153` + `anio_base_indexacion=2025`
- Confirmado: `provider.tasa_mensual_financiacion() = 0.0153` MATCH ✅
- Status: PROVIDER_VALUE_MISMATCH → FIXED

**Impacto en anchors:**
- `TestPYGAbsoluteAnchorsV28`: 3 anchors ahora `ANCHOR_UPDATE_REQUIRED_BUT_DEFERRED`
  (indexación 6.616% ahora aplicada correctamente vs silently 0.0 antes)
- `test_vision_tarifas_golden_v27`: 12 failed preexistentes (sin cambio en conteo)
- `test_cts_001_v28`: 2 failed preexistentes (PAUSED_KNOWN_DELTA — sin cambio)

---

## REQUEST_FIX_P2_P3 — COMPLETED (2026-06-12)

`tasa_ica`: 0.01 → 0.00966 (Tasas!B37 Bogota · Excel fuente).
`porcentaje_acumulado.actual`: ya era 0 en working copy (pre-alineado).
Validación bloqueada por `ParametrizationError: '20% SMMLV - 80% IPC' for year 2026` (preexistente).
Pendiente: OP_CONFIG_TASA_FINANCIACION_PROVIDER_FIX (P4).

---

## V28_ENGINE_FORMULA_MAP_CONTINUATION — COMPLETED (2026-06-12)

Mapa general de fórmulas V2-8 completado. 10 hojas analizadas. 0 cambios funcionales.

**Resultado:** backend implementa correctamente la estructura de fórmulas. Gaps son de **valor** (request/param),
no de estructura. Arquitectura sólida.

**Hallazgos nuevos:**
- VTM-001: fix accesible vía campo backend diferente (pyg_por_mes[2].ingreso_bruto). Sin módulos.
- REQUEST_FIX P2: `porcentaje_acumulado.actual` 0.02→0 (Panel!C75=0).
- REQUEST_FIX P3: `tasa_ica` 0.01→0.00966 (Tasas!B37 Bogota).
- PROVIDER_FIX P4: OP-Config `tasa_financiacion` ausente en storage activo (usa default 0.0088).
- PARAM_VALUE_FIX P5: rotacion SAC provider=0.09 vs Excel=0.077175.

**BASE_INGRESO P&G** = ACCEPTED_ARCHITECTURAL_DELTA. Excel usa HME cached; backend dinámico. Sin acción.

Doc: `docs/refactor/v28_engine_formula_map_continuation.md`

---

## Actualización — CTS-001 pausado como known_delta (2026-06-12)

CTS-001 queda en paridad funcional con residual menor documentado.

No se declara FULL_MATCH porque el umbral `MAX_DELTA = 0.000001` no se cumple.

Se difiere `CTS_SUPPORT_LOADED_MAGNITUDE` hasta completar el mapa general de fórmulas V2-8.

| Componente | Estado |
|------------|--------|
| CTS-001 (total) | `PAUSED_KNOWN_DELTA` — residual -27.53 COP/tx (0.44%) |
| cargos_adicionales | ✅ Cerrado |
| E95 override (Supervisor SAC 9.5) | ✅ Cerrado |
| CAPEX C47 | ✅ EXACT (Δ+0.0000) |
| C38 variable staff commission | ✅ EXACT (Δ+0.0000) |
| C46 OPEX Fijo | ✅ EXACT (Δ=0.000000) |
| CTS_SUPPORT_LOADED_MAGNITUDE | ⏸ DEFERRED |

Siguiente objetivo:
- Completar trazabilidad de fórmulas de hojas intermedias y visiones del motor V2-8.
- Consolidar gaps por tipo: request, parametrización, contrato, módulo, fórmula, known_delta.
- Luego buscar paridad global con todos los gaps consolidados.

Primer frente: `V28_ENGINE_FORMULA_MAP_CONTINUATION` (hojas: Inputs Nomina, Nomina Loaded,
No Payroll, Costo Fijo, Costo Variable, Costo Cadena C, Costos Totales, Pólizas-Financiación,
Vision CTS residuales, Vision P&G, Vision Tarifas).

---


> **Estado:** ⚠️ **V28_FORMULA_PARITY_NOT_ACHIEVED** (strict MAX_DELTA=0.000001) — 2026-06-11 (CTS-001 updated post 22df2dd)  
> **Nota v2:** Full formula coverage gate ejecutado (`scripts/v28_full_formula_coverage_runner.py`). 3030 formulas en scope, 14 checkpoints evaluados, 8 comparables. 1 MATCH (IPC ratio), 6 BLOCKED_BY_ARCHITECTURE_DELTA (HME bases), 4 FORMULA_PARITY_FAIL (CTS A unit mismatch, CTS C ~1%, CTS Ponderado, VT revenue field mapping). Ver `docs/refactor/v28_full_formula_inventory.md` y `v28_full_formula_backend_mapping.md`.  
> **Último commit funcional:** `66e9ae8` (test: adopt SAC/METROCUADRADO as V2-8 canonical deal); `3e4eedd` (PYG-001 indexation)  
> **Rama:** `refactor/modular-pure`  
> **Pendientes activos:** 0  
> **Veredicto:** All technical targets resolved or classified. Full numeric parity NOT CLAIMED due to accepted architectural delta (BASE_INGRESO_MISMATCH).  
> **Generado desde:** `v28_input_mapping.md`, `golden_drift_v28_paso_b.md`, `known_failures_baseline.md`, `audit_polizas_activa_flag.md`, `pyg_001_v28_evidence.md`

---

## CONTRACT_CHANGE_CARGOS_ADICIONALES_APPLIED — 2026-06-12

Implementación del campo `cargos_adicionales: float = 0.0` (Alternativa A aprobada) en el numerador del FTE de soporte de Cadena A.

- **Contrato/DTO/modelo:** `PerfilCadenaAV1` (público) + `PerfilCadenaAInput` (DTO) + `PerfilCadenaA` (dominio). Builder `_perfil_a` + `_construir_perfil_a` propagan el campo. Default 0.0 = legacy.
- **Fórmula:** `fte_base_soporte = fte + cargos_adicionales` SOLO en soporte regular (Excel CCA!E95/F95/G95). `fte_base` (Especialista/salario agentes) intacto → sin doble conteo.
- **Request V2-8:** SAC=12 (E26), Crecimiento=7.384615 (G26), WhatsApp=0 (default).
- **CTS-001:** **-128.4328 → -61.3335** COP/tx (+67.10; 2.063%→0.985%). Residual = E95 override diferido (≈-49) + cap/crucero/exám no cableados (-3.84) + estructural (~-8.5).
- **E95 override (9.5):** DIFERIDO (`E95_OVERRIDE_DEFERRED`). Backend SAC supervisor = 7.1, no 9.5.
- **Gates:** support FTE golden 6/6 · CTS 2/2 · exam/crucero 2/2 · nomina 2/2 · PyG 7/7 (anchors backend refrescados, mecanismo intacto) · validate-excel-v28 6/6 · make all 36 pass + baseline match. Hardcodes nuevos: 0. Baseline NO requerido/ejecutado.

---

## CONTRACT_CHANGE_CARGOS_ADICIONALES_DESIGN_READY — 2026-06-12

Diseño (no implementación) del contract change para `cargos_adicionales` (gap dominante CTS-001).
Detalle: `docs/refactor/contract_design_cargos_adicionales_v28.md`.

- **Excel confirmado (`openpyxl`):** CCA!E26=12 / F26=0 / G26=7.384615 (`SCENARIO_LEVEL_INPUT`); E95=9.5 literal (`PROFILE_LEVEL_OVERRIDE`, override manual, la fórmula daría 7.1).
- **Recomendación:** Alternativa A — `cargos_adicionales: float=0.0` por escenario/perfil-base en `PerfilCadenaAV1` + `PerfilCadenaAInput`; numerador soporte `(fte+cargos_adicionales)/ratio`. Backward compatible (default neutro, `extra="forbid"` no afecta campos nuevos). Alt B (por rol) rechazada; Alt C (override per-rol E95) **DIFERIDA** (`NEEDS_REVIEW`).
- **Riesgo dominante:** doble conteo (solo numerador soporte/cap/crucero, nunca salario de agentes). Impacto contrato LOW, fórmula/goldens MEDIUM, no breaking.
- **Go/No-Go:** GO para `cargos_adicionales`; NEEDS_REVIEW (diferido) para override per-rol.
- Gates: CTS golden 2/2 · exam/crucero 2/2 · validate-excel-v28 6/6 · make all PASS. Baseline NO ejecutado. Hardcodes nuevos: 0.

---

## V28_VISION_CTS_FORMULA_MAP_COMPLETED — 2026-06-12

Mapa fórmula-por-fórmula de `Vision Cost To Serve` (bloque CTS Cadena A C34-C48) → backend.
Detalle: `docs/refactor/v28_vision_cts_formula_map.md`. Estado: `e296c77` (post DIAS_CAP). CTS-001 = 6,096.142357 (-128.43, 2.063%).

| Componente | Celda | Excel | Backend | Delta | Clasificación |
|------------|-------|-------|---------|-------|---------------|
| Total CTS A | C34 | 6,224.575126 | 6,096.142357 | -128.43 | KNOWN_DELTA |
| Payroll | C35 | 5,462.355884 | 5,320.376113 | -141.98 | CONTRACT_GAP (raíz cargos_adic) |
| OPEX Fijo | C46 | 308.138215 | 308.138215 | **0.0** | MATCH_EXACT |
| CAPEX/Inversiones | C47 | 103.043569 | 119.758618 | +16.72 | FORMULA_GAP (amortización) |
| Cap/Crucero (firma) | C39/C40/C43 | — | — | **-6.938% idéntico** | CONTRACT_GAP (FTE soporte) |

**Hallazgo:** `cargos_adicionales` ausente del numerador FTE soporte explica ~97% del residual. Firma -6.938%
idéntica en cap_inicial/cap_rotación/crucero confirma raíz única. **No hay otro gap estructural comparable**
(OPEX exacto; CAPEX +16.72 = frente de fórmula separado, signo opuesto). 0 MAPPING_AMBIGUOUS, 0 métricas no expuestas.
**Decisión:** `CONTRACT_CHANGE_CARGOS_ADICIONALES` = único P0 (contemplar override per-rol E95=9.5).
Gates: CTS golden 2/2 · exam/crucero 2/2 · validate-excel-v28 6/6 · make all PASS. Hardcodes nuevos: 0.

---

## V28_WHAT_IF_GAP_SIMULATION_COMPLETED — 2026-06-11

Simulación what-if (motor) del impacto real de cada gap CTS-001 conocido, sin fixes.
Detalle: `docs/refactor/v28_what_if_gap_simulation.md`. Baseline CTS-001 = 6,093.2443 (-131.33, 2.110%).

| Gap | Impacto medido CTS | Clasificación |
|-----|--------------------|---------------|
| DIAS_CAPACITACION (10→11) | **+2.898 COP/tx** | `APPLY_NOW_REQUEST_SCOPE` (único request-scope que mueve CTS) |
| PCT_ACUMULADO (0.02→0) | **0.0** | `NEEDS_FORMULA_MAP` (P&G/Tarifas, no CTS) |
| COMISION_ROL_STAFF (request) | **0.0 (no consumido)** | `ALREADY_APPLIED_BASELINE` (provider W-override) |
| CRUCERO_FULL_PARITY | +0.7375 solo via approx | `DO_NOT_APPLY_COMPENSATING_GAP` (tarifa escalada = fake) |
| CARGOS_ADICIONALES | ≈ -68 (raíz, no medible) | `NOT_SIMULABLE_WITHOUT_MODULE_CHANGE` + `APPLY_AFTER_CONTRACT_DECISION` |

**Techo request-scope = 2.051%** (-127.70 COP/tx aplicando todos los gaps simulables incl. crucero approx).
El ~97% del residual es payroll soporte (cargos_adicionales + override SAC Supervisor): contrato/módulo, no request.
Gates: CTS golden 4/4 · validate-excel-v28 6/6 · make all PASS. Hardcodes nuevos: 0.

---

## V28_INPUT_FULL_MAPPING_COMPLETED — 2026-06-11

Mapa maestro extremo-a-extremo de inputs V2-8 (Excel → request → contrato → loader/provider →
valor consumido) en `docs/refactor/v28_input_full_mapping.md`. Sustituye la corrección reactiva
delta-por-delta. ~70 inputs revisados: ~48 MATCH, 3 VALUE_MISMATCH, 3 MISSING_IN_REQUEST,
2 PRESENT_NOT_CONSUMED, 3 MAPPING_AMBIGUOUS, 3 EXCEL_SOURCE_OPAQUE.

Hallazgos accionables nuevos:
- **`dias_capacitacion_perfil`**: Excel A!E139=**11** vs request **10** → `INPUT_VALUE_MISMATCH` (P2, request-scope).
- **`porcentaje_acumulado.actual`**: request **0.02** vs Panel!C75=**0** → `INPUT_VALUE_MISMATCH` (P2, request-scope).
- **`comision_rol` staff = 0.0**: Excel A!F44/F51/F62 (Director 3.87M / Jefe Op 1.5M / Supervisor 0.7M) ≠ 0
  → staff variable ausente del deal; provider HR lo simula (`HIGH_DEFAULT_OR_PROVIDER_OVERRIDE`, P1).
- **`pct_ausentismo`**: `PRESENT_NOT_CONSUMED` — no alimenta fórmula de costo verificable.
- **`roles_operativos[]`**: el motor consume `staff_config`, no `roles_operativos` (`BACKEND_NOT_CONSUMING_FIELD`).
- **Panel!L6 "¿Aplica indexación a la tarifa?"=No**: gate de indexación de tarifa de venta, no de costo
  (payroll/tecnológico sí corre). Sin campo backend equivalente — no inventar.

Gates: CTS golden 4/4, exam/crucero golden incluido, validate-excel-v28 6/6 (1 skip), make all PASS.
Siguiente: **V28_FIX_ROADMAP** consolidado (binomio payroll soporte) + quick-wins request-scope (dias_cap, pct_acumulado).

---

## Gate de validación V2-8 — 2026-06-11

**NOTA:** `make validate-excel` (legado) NO era un gate V2-8 real — apuntaba al Excel V2-7
con case `bancamia_whatsapp_only` y pasaba trivialmente con valores Excel = 0.00.

**Nuevo gate V2-8:** `make validate-excel-v28` → `scripts/validate_excel_v28.py`

Checks implementados (6 activos + 1 skip):
1. Input alignment Panel + Condiciones (4 campos vs Excel V2-8 hojas)
2. componente_tecnologico resuelve (engine sin ParametrizationError)
3. Storage OP tiene '20% SMMLV 80% IPC'
4. IPC ratio m7/m6 con V2-7 provider (delta=0.0 — mecanismo exacto)
5. CAPEX-001 activo (cadena_b costo > 0 con items CAPEX)
6. CADENA_C_NULL no regresó (ingreso_bruto_c > 0)
7. HME cache: SKIP (SKIPPED_OLD_EXCEL_CACHE_NOT_COMPARABLE)

Resultado: PASS (6/6, 1 skipped).

---

## Estado real del plan — 2026-06-11 (post Option B + BASE_INGRESO_MISMATCH decision)

**Veredicto: V28_TECHNICAL_SCOPE_CLOSED_WITH_ACCEPTED_DELTA — Deal alineado. Deltas arquitectónicos aceptados. Fórmulas Stage 2 completadas o clasificadas.**

### Objetivo original del plan V2-8

Lograr paridad numérica entre el motor backend y el Excel V2-8 para el deal de referencia. Esto requiere:

1. Inputs alineados (Paso B). ✅ LOGRADO
2. Fórmulas alineadas (Stage 2 Targets). ✅ COMPLETADO/CLASIFICADO:
   - T1 (PYG indexación): CLOSED_WITH_ACCEPTED_DELTA (mecanismo correcto, numeric parity not claimed)
   - T2 (CAPEX-001): COMPLETED (fórmula presente, golden tests 4/4)
   - T3 (Vision Tarifas): COMPLETED (no delta para deal referencia)
3. Deal de referencia alineado (INPUT_DEAL_MISMATCH). ✅ RESUELTO — OPTION_B_DEAL_SWITCH (commit `66e9ae8`)
4. Parity runner pasando sin errores. ✅ Deal aligned: True (confirmado 2026-06-11)
5. Architectural deltas documentados y aceptados. ✅ BASE_INGRESO_MISMATCH classified as ACCEPTED_ARCHITECTURAL_DELTA

### Option B aplicada — Deal canónico V2-8

- **Deal:** SAC / METROCUADRADO COM SAS / Grupo Aval
- **Commit funcional:** `66e9ae8`
- **Parity runner:** `Deal aligned: True` (servicio/cliente/tipo_cliente/duracion confirmados)
- **Tests refactor:** 1 failed (SNAPSHOT-002, pre-existing ACCEPTED_DEBT), 93 passed, 1 skipped
- **SNAPSHOT-001 resuelto:** `test_request_json_after_fix` ya pasa (costo_b anchor actualizado)

### Resoluciones finales (post Option B + BASE_INGRESO_MISMATCH decision)

| ID | Estado | Tipo | Clasificación | Nota |
|----|--------|------|---|---|
| PYG-001 | ✅ CLOSED | Técnico + dato | CLOSED_WITH_ACCEPTED_DELTA | Mecanismo indexación correcto (ratio IPC exacto); numeric parity NOT CLAIMED due to BASE_INGRESO_MISMATCH (architectural). Ver `docs/refactor/pyg_001_v28_evidence.md` |
| CAPEX-001 | ✅ COMPLETED | Técnico + goldens | FORMULA_UPDATE_VALIDATED | Fórmula presente en `reglas.py:182`; golden `test_capex_001_v28_cadena_c.py` 4/4 verdes; SUM(J62:J65)=12,778,653.116 validado |
| BASE_INGRESO_MISMATCH | ✅ CLASSIFIED | Arquitectónico | ACCEPTED_ARCHITECTURAL_DELTA | Backend dynamic ingreso (traceable, auditable, deterministic) is intentionally different from Excel fixed HME!C296 base. If business requires absolute parity, escalate as functional requirement. |
| CADENA_C_NULL | ✅ RESOLVED | Técnico | BUG_FIX | Commit `69b77a9` — entry_data_adapter tarifa_unitaria fix |
| GOLDEN-001 | DEFERRED | Técnico | ACCEPTED_DEBT | 42/63 goldens `_v27` bajo productiva 2026; decidir xfail vs V2-8 paralelos en Stage 3+ |
| SNAPSHOT-002 | DEFERRED | Técnico | ACCEPTED_DEBT | goldens v27 SMMLV divergen bajo productiva 2026; pospuesto Stage 3+ |

### Estado correcto por categoría

- **Paso B (input alignment)**: ✅ COMPLETED
- **Deal identity (INPUT_DEAL_MISMATCH)**: ✅ RESOLVED_BY_OPTION_B (commit `66e9ae8`)
- **Parity runner deal guard**: ✅ Deal aligned: True
- **Stage 2 (formula alignment)**: ✅ COMPLETED/CLASSIFIED:
  - T1 (PYG indexación): CLOSED_WITH_ACCEPTED_DELTA (mecanismo ✓, numeric parity not claimed)
  - T2 (CAPEX-001): COMPLETED (fórmula presente, goldens 4/4)
  - T3 (Vision Tarifas): COMPLETED (no delta)
- **Architectural deltas**: ✅ BASE_INGRESO_MISMATCH — ACCEPTED_ARCHITECTURAL_DELTA (backend dynamic vs Excel fixed)
- **Full numeric parity (objetivo final)**: ❌ NOT CLAIMED — architectural delta accepted (BASE_INGRESO_MISMATCH)
- **Plan V2-8 global**: ✅ CLOSED — ALL TECHNICAL TARGETS RESOLVED OR CLASSIFIED

---

## Inventario consolidado — FINAL

| ID | Target | Tipo | Estado FINAL | Commit / Evidencia | Nota |
|----|--------|------|--|------|------|
| **CAPEX-001** ✅ **COMPLETED** | Stage 2 T2 — Cadena C L11 CAPEX factor | FORMULA_UPDATE | ✅ **COMPLETED** | commit `fde7657`, `test_capex_001_v28_cadena_c.py` | Fórmula `(inversion_anual/12)*(1+tasa_mensual)` ya presente; golden test con valores reales del Excel 4/4 PASSED |
| **PYG-001** ✅ **CLOSED_WITH_ACCEPTED_DELTA** | Stage 2 T1 — P&G ingreso indexado | FORMULA_UPDATE + ARCHITECTURE | ✅ **CLOSED** | commit `3e4eedd`, `pyg_001_v28_evidence.md` | Mecanismo correcto (ratio IPC exacto ✓); numeric parity NOT CLAIMED due to ACCEPTED_ARCHITECTURAL_DELTA (backend dynamic vs Excel fixed HME!C296) |
| **BASE_INGRESO_MISMATCH** ✅ **CLASSIFIED** | Backend dynamic vs Excel fixed base | ARCHITECTURE | ✅ **ACCEPTED_ARCHITECTURAL_DELTA** | `pyg_001_v28_evidence.md` §Decisión final | Backend ingreso is traceable (cost-based, deal-derived), auditable, deterministic. If business requires absolute parity, escalate as functional requirement. |
| **CADENA_C_NULL** ✅ **FIXED** | ingreso_c = 0 | BUG | ✅ **RESOLVED** | commit `69b77a9` | Entry_data_adapter tarifa_proveedor mapping fixed. M1 ingreso_c ≈ 981M. Residual delta ≈7% = BASE_INGRESO_MISMATCH (accepted). |
| **Vision Tarifas T3** ✅ **COMPLETED** | Stage 2 T3 — Vision Tarifas margen | NO_DELTA | ✅ **COMPLETED (no cambio)** | `golden_drift_v28_paso_b.md` | Sin delta para deal referencia (cont_op=cont_com=0) |
| **Paso B — Panel (11 updates)** ✅ **COMPLETED** | pct_rotacion, crucero, tasa_ica, margen_objetivo, contingencia, etc | VALUE_UPDATE | ✅ **COMPLETED** | Commits: a4aaaeb, 01abc18, 58957a3, 8927ee2, 6cd0575, b486fd5, a4f1c73, 3ad1215, 5288e66, 395390e, 1cd9ad7 | 63/63 goldens estables |
| **Paso B — Pólizas (3 EXCEL_LIKELY_BUG + 6 activa flags)** ✅ **COMPLETED** | Cumplimiento/Salarios/Calidad pct; Seriedad/RC/IRF/Responsabilidad/ProtDatos activa | VALUE_UPDATE | ✅ **COMPLETED** | Commits: 4034baa, a04df3b, 246f5af, + audit_polizas_activa_flag.md | Panel como fuente canónica; CONSUMED verificado; 6 flags True→False; goldens sin regresión |
| **INPUT_DEAL_MISMATCH** ✅ **RESOLVED_BY_OPTION_B** | Deal identity — servicio/cliente/tipo_cliente/fecha_inicio | DECISION | ✅ **RESOLVED** | commit `66e9ae8` — deal switch SAC/METROCUADRADO COM SAS / Grupo Aval | Parity runner: Deal aligned: True. SNAPSHOT-001 resuelto. |
| **REQUEST_STRUCTURE_GAP** ✅ **RESOLVED_BY_OPTION_B** | escenarios_comerciales + condiciones cadena_a/b/c structure | STRUCTURE | ✅ **RESOLVED** | commit `66e9ae8` | Canales/perfiles V2-8 adoptados completamente en request.json |
| **SNAPSHOT-001** ✅ **RESOLVED** | test_request_json_after_fix | REGRESSION | ✅ **RESOLVED** | commit `66e9ae8` | Snapshot actualizado; test pasa |
| **SNAPSHOT-002** ⚠️ **ACCEPTED_DEBT** | test_golden_tests_still_pass | REGRESSION | DEFERRED | — | goldens v27 bajo productiva 2026 esperan SMMLV=1,750,905; decision: xfail vs V2-8 paralelos |
| **GOLDEN-001** ⚠️ **ACCEPTED_DEBT** | 42/63 goldens _v27 fallan | REGRESSION | ACCEPTED | `known_failures_baseline.md` | Productiva 2026 activada en commit c775212; decision deferida a Stage 3+ |

---

## Pendientes activos del plan principal

**NINGUNO — Plan V2-8 completado. Todos los targets técnicos resueltos o clasificados.**

| Item | Estado | Nota |
|------|--------|------|
| CAPEX-001 | ✅ COMPLETED | Fórmula presente, golden tests 4/4 PASSED |
| PYG-001 | ✅ CLOSED_WITH_ACCEPTED_DELTA | Mecanismo correcto, numeric parity NOT CLAIMED |
| BASE_INGRESO_MISMATCH | ✅ ACCEPTED_ARCHITECTURAL_DELTA | Backend dynamic ingreso is intentional. Escalate to stakeholder only if absolute parity becomes functional requirement. |
| CADENA_C_NULL | ✅ RESOLVED | Commit `69b77a9` |
| Paso B (inputs) | ✅ COMPLETED | 15 commits aplicados, 63/63 goldens estables |
| Deal identity | ✅ RESOLVED | Option B (commit `66e9ae8`), parity runner: Deal aligned: True |

---

## Parity runner

| Ejecución | Estado | Deal aligned | Nota |
|-----------|--------|:------------:|------|
| 2026-06-11 (reconciliación) | EJECUTADO | False | `INPUT_DEAL_MISMATCH — comparación numérica diferida a Stage 2`. Report: `reports/v28_parity_runner.md` |
| 2026-06-11 (post Option B) | EJECUTADO | **True** | Deal SAC/METROCUADRADO alineado. Anclas V2-8 cache = 0.00 (Excel no recalculado con nuevo deal). Comparación numérica diferida a Stage 2 T1. |

---

## Deuda registrada (ver v28_backlog.md)

**MINIMIZADA — Solo deudas aceptadas persistentes**

| ID | Tema | Estado | Clasificación | Nota |
|----|------|--------|---|---|
| SNAPSHOT-001 | test_request_json_after_fix | ✅ RESOLVED | — | Commit `66e9ae8` |
| SNAPSHOT-002 | test_golden_tests_still_pass | DEFERRED | ACCEPTED_DEBT | Goldens v27 bajo productiva 2026; decision xfail vs V2-8 paralelos en Stage 3+ |
| GOLDEN-001 | 42/63 goldens _v27 fallan | DEFERRED | ACCEPTED_DEBT | Productiva 2026 activada; decision deferida |

---

## Próximo paso — Plan V2-8 COMPLETADO

**Estado final: V28_TECHNICAL_SCOPE_CLOSED_WITH_ACCEPTED_DELTA**

Todos los targets técnicos resolutos o clasificados:

- ✅ CAPEX-001 (commit `fde7657`)
- ✅ PYG-001 (commit `3e4eedd`)
- ✅ CADENA_C_NULL (commit `69b77a9`)
- ✅ BASE_INGRESO_MISMATCH (classified as ACCEPTED_ARCHITECTURAL_DELTA)
- ✅ Deal identity (commit `66e9ae8` — Option B)
- ✅ Paso B / Input alignment (15 commits)

**Si es necesario reabrir:**
- Stakeholder debe escalar BASE_INGRESO_MISMATCH como **requisito funcional** (absolute numeric parity) con justificación de negocio.
- Decision será arquitectónica: ¿hardcodear HME!C296 o documentar divergencia como comportamiento intencional del motor?

---

## Fast-pass lineage (2026-06-12 · `V28_EXCEL_ENGINE_LINEAGE_FAST_PASS_COMPLETED`)

Mapa consolidado Excel→backend en [`v28_excel_engine_lineage_fast_pass.md`](v28_excel_engine_lineage_fast_pass.md):
DAG hoja-a-hoja (4 inputs raíz + 3 parametrización + 11 intermedias → 4 visiones → charts), **Fase 4
parametrización HR/OP/GN ↔ backend** (paridad vía provider W-override; mismatches reales = rotación SAC
PARAM_VALUE + tasa_financiacion MISSING_EXISTING_FIELD) y **Fase 6 charts** (todos display, 0 cambio backend).
0 `BACKEND_MISSING_COMPONENT`.

> ⚠️ **`STOP_DIRTY_WORKTREE_GATE_BLOCK`**: el `request/request.json` sin commitear (WIP `OPEX_REQUEST_ALIGNMENT`)
> deja `cantidad: null` en WhatsApp `opex_fijo.items[3,4]` → rompe el motor (`float(None)`) y hace fallar
> **todos** los gates de motor. En `HEAD` (`6778540`) pasan. Resolver request antes de correr gates.
> Próximo P0 de paridad: `E95_OVERRIDE_DECISION` (≈80% residual CTS-001).
