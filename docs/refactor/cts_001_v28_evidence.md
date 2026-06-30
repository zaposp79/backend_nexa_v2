# CTS-001 V2-8 Evidence — Cadena A Parity

> **⮕ UPDATE 2026-06-12 (5) — `CTS-001 PAUSED AS KNOWN_DELTA`.** Ver sección "Cierre temporal" más abajo.
> Estado: `CTS-001_FUNCTIONAL_PARITY_WITH_KNOWN_DELTA`. Residual -27.53 COP/tx (0.44%) diferido.
> `FULL_MATCH=NO`. `CTS_SUPPORT_LOADED_MAGNITUDE` diferido hasta completar mapa general de fórmulas V2-8.

> **⮕ UPDATE 2026-06-12 (4) — `CTS_VARIABLE_COMMISSION_STAFF` (C38 EXACT).** Ver `formula_first_diff.md` §P4.
> Diagnóstico previo "aging ≈1.0989" REFUTADO: filas CTS planas 24m (sin aging); agentes ya coinciden (Excel usa
> partición, fijo agente = 130×(W62−D62)). Causa real = comisión variable de STAFF (Supervisor D57×9.5=6,650,000,
> Jefe, Director) que Excel suma a la variable; backend tenía `comision_pct=0` para staff. Fix: poblar salario(=C)
> + comision_pct(=D/C) en `_v28_deal_provider.py` (+ alias accent-stripped). **C38 705.88→775.74 (Δ+0.0000 EXACT)**,
> C37 +49.35→-20.51, total-invariante. `PROVIDER_VALUE_MISMATCH`. Residual = `CTS_SUPPORT_LOADED_MAGNITUDE` (-20.51,
> cargado soporte W ligeramente bajo). Gates: CTS 2/2, validate-excel-v28 6/6, make all verify match, 0 goldens nuevos.

> **⮕ UPDATE 2026-06-12 (3) — `CTS_SALARY_ADDITIVE_STRUCTURE` (split C37/C38).** Ver `formula_first_diff.md` §P3.
> Excel `Inputs de Nomina`!D62 = comisión CRUDA (sin cumplimiento 0.70). El backend aplicaba `× 0.70` a la línea
> de costo variable (`nomina.py:_comisiones`), inflando salario_fijo (carve-out) y reduciendo la variable.
> Fix: removido el 0.70 (variable = comisión cruda Excel D62). **Total-invariante** (C34/C36/PyG/Tarifas/baseline
> sin cambio; solo el split). **C37 +261.11→+49.35 · C38 -281.63→-69.86** (ambos mejoran ~212 individualmente,
> sin compensación falsa). Residual = `CTS_VARIABLE_INDEXATION_AGING` + comisión cruda de staff (Director/Jefe/
> Supervisor en variable Excel; backend la lleva en el cargado) → frente separado, diferido. Gates: 0 fallos
> nuevos en golden suite; CTS 2/2, nomina_variable 2/2, validate-excel-v28 6/6, make all verify baseline match.

> **⮕ UPDATE 2026-06-12 (2) — `E95_OVERRIDE_APPLIED` + `CTS_CAPEX_AMORT_FIXED`.** Ver detalle completo en
> [`formula_first_diff.md`](formula_first_diff.md). El headline `+1.05 COP/tx` previo era **falso** (cancelación
> payroll -74.94 ⊕ CAPEX +75.99). Esta sesión corrige cada componente contra Excel:
> - **E95 override opt-in per-rol** (`fte_soporte_overrides`): Supervisor SAC 7.1→**9.5** (Excel CCA!E95). C35 -74.94→**-24.36**.
> - **CAPEX amortización** (`_build_amortizable_item`): bug de campo (`meses_amortizacion` vs `meses_a_diferir`) +
>   gate `mes≤meses` → todo en mes 1. Fix: precio_mensual del request + cobro plano `meses=meses_contrato`.
>   **C47 182.20→103.0436 (Δ+0.0000 EXACT)**.
> - **CTS-001: +1.05 (falso) → -27.53 COP/tx (0.44%) HONESTO.** Residual = brecha aditiva C37/C38 (salario fijo/variable).
> - Gates: CTS 2/2, exam/crucero 2/2, support FTE 6/6, validate-excel-v28 6/6, make all verify baseline match. Hardcodes: 0.
> - Drift diferido: 4 anchors no_payroll v27 frozen (`SNAPSHOT_REGENERATION_REQUIRED`).

> **⮕ UPDATE 2026-06-12 — `CONTRACT_CHANGE_CARGOS_ADICIONALES_APPLIED` / `CTS-001_PARTIAL_BEST_IMPROVED`.**
> El frente Support FTE (antes `BLOCKED_MISSING_SOURCE`) se **desbloqueó e implementó**: campo
> `cargos_adicionales` en contrato + numerador `(fte+cargos_adicionales)/ratio` en el soporte regular.
>
> | Componente | Antes | Después | Δ |
> |------------|-------|---------|---|
> | **CTS-001 (COP/tx)** | 6,096.142357 (Δ -128.43, 2.063%) | **6,163.241613 (Δ -61.33, 0.985%)** | **+67.10** |
> | nomina (payroll) | 5,320.376 (Δ -141.98) | 5,387.475 (Δ -74.88) | +67.10 |
> | Supervisor SAC FTE | 6.5 (130/20) | **7.1 ((130+12)/20)** | +0.6 |
> | no_payroll | 775.766 (Δ +13.55) | 775.766 (Δ +13.55) | 0 (sin cambio) |
>
> **Residual -61.33 decompuesto:** E95 override (2.4 FTE Supervisor SAC, **DIFERIDO**, ≈-49 COP/tx) +
> cap/crucero/exámenes no cableados (-3.84, siguen sobre fte de agentes) + SENA/Inclusión estructural &
> CAPEX no-payroll (~-8.5). Sin el E95 diferido, el delta estaría ~-12 (dentro de ±20).
> **E95=9.5 NO implementado** (override manual literal, diferido por diseño). Hardcodes nuevos en motor: 0.
> Gates: support FTE golden 6/6 · CTS 2/2 · PyG 7/7 · validate-excel-v28 6/6 · make all baseline match.

**Excel anchor:** Vision Cost To Serve!C34 = 6,224.575126115379 COP/transacción  
**Deal:** SAC / METROCUADRADO COM SAS / Grupo Aval — 24m  
**Provider:** V2-7 (canonical)

> **Update 2026-06-11 (sesión `SUPPORT_FTE_MODULE_FIX`):** el residual restante de CTS-001 está
> dominado por el frente Support FTE, ahora **`SUPPORT_FTE_BLOCKED_MISSING_SOURCE`** (no
> `REQUIRES_MODULE_SCOPE`). Excel usa `(fte_agentes + cargos_adicionales)/ratio` con
> `cargos_adicionales` = CCA!E26/E30/E34 = 12/0/7.3846 — insumo **ausente** del contrato de entrada —
> y un override manual SAC Supervisor (E95=9.5 literal). Sin crear campo público nuevo ni hardcodear,
> el fix no es aplicable; CTS-001 sigue `PARTIAL_BEST_IMPROVED`. Detalle: `support_fte_input_decision_v28.md` §8-§10.

---

## Estado actual (post commit 5a72f81 + baseline regeneration) — 2026-06-11

| Etapa | Commit | Delta backend vs Excel | Denominador | Estado |
|-------|--------|----------------------|-------------|--------|
| Pre fix | — | unknown (unit mismatch: 4,549,186 total vs 6,224.58 COP/tx) | 260 FTE (wrong) | FORMULA_PARITY_FAIL |
| Post ed07c42 | ed07c42 | ~8.44% (-525.07 COP/tx) | 221,000 tx/mes (correct) | CTS-001_UNITS_FIXED |
| Post 22df2dd | 22df2dd | ~8.44% (-525.07 COP/tx) | 221,000 tx/mes (correct) | HR_INFRA_SCALE_FIXED |
| Post 5a72f81 | 5a72f81 | ~3.73% (-232.07 COP/tx) | 221,000 tx/mes (correct) | VARIABLE_COMP_LOAD_APPLIED |
| Post exam/SENA | 6ce1eb7 | 1.113% (-69.27 COP/tx) | 221,000 tx/mes | CTS_EXAM_APPLIED / PARTIAL_BEST |
| CRUCERO_REQUEST_ALIGNMENT | *prior* | 0.954% (-59.38 COP/tx) | 221,000 tx/mes | CTS_CRUCERO_PARTIAL / PARTIAL_BEST_IMPROVED |
| **OPEX_REQUEST_ALIGNMENT** | *this commit* | **2.110% (-131.33 COP/tx)** | 221,000 tx/mes | **OPEX_EXACT_PARITY (0.0 delta OPEX); headline worsened — payroll deficit unmasked** |
| **DIAS_CAPACITACION_REQUEST_ALIGNMENT** | 2026-06-12 | **2.063% (-128.43 COP/tx)** | 221,000 tx/mes | CCA!E139=F139=G139=11 applied; cap_inicial +0.98 / cap_rotacion +1.92 |

### Valores exactos (post 5a72f81 + baseline regeneration)

```
backend  cts_cadena_a = 5,992.502271 COP/tx
excel    cts_cadena_a = 6,224.575126 COP/tx
delta    abs          = -232.072855 COP/tx
delta    pct          = 3.73%
denominator (fte_cadena_a field) = 221,000 tx/mes ✅ matches Excel Panel!W31
```

### Gate results (post-baseline)

- `tests/golden/test_cts_001_v28.py` — 2/2 PASSED (50% tolerance gate)
- `tests/golden/test_nomina_variable_load_v28.py` — 2/2 PASSED
- `make all` — PASS (baseline match, no regression)
- `make validate-excel-v28` — PASS (6/6 checks, 1 skip)
- `tests/refactor/` baseline snapshots (v0, v1, cadena_c_v1) — 9/9 PASSED
- BASELINE_REGENERATED_FOR_VARIABLE_COMP_LOAD: DONE 2026-06-11

---

## Milestones

### CTS-001_UNITS_FIXED (commit ed07c42)

Root cause was the denominator. Backend used 260 FTE as CTS Cadena A denominator instead of
Panel!W31 = 221,000 (monthly transaction volume). This produced a value in a completely wrong
unit (COP/FTE instead of COP/transacción).

Fix: `vol_cadena_a_mensual` per-channel in `request.json` + `UserInputLoader._aplicar_volumenes_a_perfiles`
now prefers explicit value from perfil over the volumetria FTE-based fallback.

After fix: denominator = 221,000 tx/mes. Unit now matches Excel.

### HR_INFRA_SCALE_FIXED (commit 22df2dd)

HR infrastructure legacy scale normalization. Added `_normalizar_costo_cop` whitelist utility
to safely detect and normalize HR legacy scale without touching non-infrastructure cost components
(agua, gas, mantenimiento etc. not multiplied). This prevents over-scaling of operational costs.

Impact on CTS-001: delta unchanged at 8.44%. The HR infra normalization did not move the
CTS Cadena A needle significantly. The residual delta is attributed to parametrization variance
(V2-7 provider values vs V2-8 Excel values).

---

## Residual delta analysis (8.44%)

Candidate root causes:
1. **Parametrization V2-7 vs V2-8** — provider uses V2-7 HR values; Excel V2-8 may have
   updated salario, comisiones, beneficios for SAC line. Most likely cause.
2. **Salario variable / comisiones staff** — no evidence of systematic gap in these fields.
3. **meses_amortizacion** — not the denominator anymore (fixed by ed07c42); amortization
   month count could affect costo_fijo_mensual but not the per-tx normalization.
4. **Rampup treatment** — CTS uses all-month aggregate; Excel may use a different month slice.

**Verdict:** CTS-001 = PARTIAL (blocked by parametrization_v27_vs_v28)

To achieve FULL_MATCH: load V2-8 HR parametrization for SAC line and re-run.

---

## Salary audit (2026-06-11) — root cause IDENTIFIED

The 8.44% residual is NOT a parametrization V2-7/V2-8 gap. Input values match
Excel to within 0.006% (raw commission backend 600,035 vs Excel D62 600,000).

Root cause = **CARGA_PRESTACIONAL_MISMATCH on variable compensation** (two bugs):
1. Backend reports RAW commission; Excel `Nomina Loaded!R205` loads it with carga
   factor **1.5699** (+62.2M/mes, +281.60 COP/tx).
2. `NominaCargadaService` applies cumplimiento 0.7 to commission before loading;
   Excel `Inputs de Nomina!D62`=600,000 loads the full commission (+66.5M/mes,
   +300.84 COP/tx in salario_fijo).

Full breakdown: `docs/refactor/cts_salary_audit_v28.md`.

**No fix applied** — touches NominaCargadaService + NominaCalculator → cascades
into PyG / Vision Tarifas / baseline (out of scope). Requires business decision.

## Fix applied (2026-06-11) — VARIABLE_COMP_LOAD_DECISION = APPLY_PRESTATIONAL_LOAD_LIKE_EXCEL

Decision adopted: the variable commission is loaded COMPLETE with the prestational
factor (like Excel V2-8), and `pct_cumplimiento_variable` (0.70) is applied
downstream in `NominaCalculator._comisiones`, NOT before loading.

Fix (Bug 2): `NominaCargadaService.calcular` (nomina_cargada.py:117)
- Before: `t_imponible = salario_base × (1 + comision_pct × pct_cumplimiento)`
- After:  `t_imponible = salario_base × (1 + comision_pct)`
- Excel anchor: `Inputs de Nomina!F62 = C62 + D62 = 2,350,905` (full commission).

Impact on CTS-001:

| | COP/tx | delta vs Excel | pct |
|---|---|---|---|
| Pre-fix  | 5,699.505252 | -525.069874 | 8.44% |
| Post-fix | 5,992.502271 | -232.072855 | 3.73% |

Residual 3.73% = Bug 1 (variable line reported raw at the per-line CTS split level)
+ secondary examenes/crucero gaps. NOTE: the "carga-factor variance 1.5256 vs 1.5699"
is NOT a real cause — see `docs/refactor/hr_param_factor_prestacional_v28.md`. The
loaded SAC line matches Excel W62 = 3,560,973.86 exactly; the true per-line carga
factor (1.5147) is identical in Excel and backend. 1.5256/1.5699 are aggregate
artifacts (loaded total / raw-commission base), not prestational factors. Closing
the residual requires the per-line variable split rewrite (touches PyG / Vision
Tarifas / baseline — out of scope).

## Classification

- CTS-001_UNITS_FIXED: ✅ (commit ed07c42)
- HR_INFRA_SCALE_FIXED: ✅ (commit 22df2dd)
- CTS_SALARY_AUDIT: ✅ root cause = variable carga + cumplimiento treatment
- VARIABLE_COMP_LOAD_DECISION: ✅ APPLIED (Bug 2 fixed) — CTS-001 8.44% → 3.73%
- HR_PARAM_FACTOR_AUDIT: ✅ NO FACTOR MISMATCH — rates + loaded line match Excel exactly
  (loaded factor 1.5147 == Excel; 1.5256/1.5699 are aggregate artifacts). See
  `docs/refactor/hr_param_factor_prestacional_v28.md`.
- CTS_VARIABLE_SPLIT_AUDIT: ✅ BLOCKED — residual is NOT a variable-split bug.
  The backend defines `salario_fijo = total_cargado − comisiones` (nomina.py:174),
  so `fijo + variable` is INVARIANT to `_comisiones`. Changing the variable split
  CANNOT move `cts_cadena_a` (verified empirically: 5,992.502271 unchanged). The
  residual lives in the payroll SUBTOTAL (backend 5,115.79 vs Excel 5,405.23,
  −289.44): Excel ADDS the raw commission (D62) on top of the full loaded cost
  (AM=W62), the backend folds it INTO the loaded total. Fix requires restructuring
  `_salario_fijo` + payroll subtotal + re-baseline (OUT OF SCOPE).
  See `docs/refactor/cts_variable_split_attribution_v28.md`.
- CTS-001_FULL_MATCH: ❌ NOT ACHIEVED — residual 3.73% = payroll additive-structure
  gap (Excel AM+D additive vs backend partition) + examenes/crucero (NOT a
  prestational factor issue, NOT a variable-split bug).

## ⚠️ Re-baseline pending

The fix increases total loaded payroll (payroll_a month 1: 1,072,244,866 →
1,136,997,207, +6%, toward Excel). This breaks frozen reproducibility snapshots:
`test_baseline_formula_snapshot_v0/v1` and PyG/KPI anchors (7 FAIL). These are
INTENTIONAL — they require `make baseline` regeneration AFTER `make validate-excel`
confirms the move is toward Excel parity. NOT regenerated in this commit (requires
explicit approval per CLAUDE.md re-baseline policy).

---

## AUDITORÍA ESTRUCTURAL DEL RESIDUAL (2026-06-11, post-70ecd54) — CORRIGE secciones previas

Tras el override W de los 20 roles staff (commit 70ecd54), el residual cambió de naturaleza.
Descomposición verificada (CTS 6,109.62 vs Excel 6,224.58, -114.95):

- **Payroll -200.45**: soporte nomina_loaded ~-138 (FTE) + SENA/Incl base -34.18 (FIXABLE
  provider) + examenes -12.22 + crucero -10.63 + cap -5.28. AGENTES = MATCH exacto.
- **No-payroll +85.50** (corrige doc INPUT_DEAL_MATCH): OPEX Fijo **+71.95** (dominante,
  backend>Excel), Inversiones/CAPEX **+16.72** (NO +119.72 — Excel también amortiza C47=103.04),
  Costos Fijos -3.17.

Hallazgos clave:
- **SENA/Incl base**: Excel `Inputs de Nomina`!C59/C60 = **1,750,905** vs backend 1,423,500.
  Parchar `salario` en provider (trazable) → CTS +34.18 → 6,143.81 (1.298%). FIXABLE_WITH_PROVIDER.
- **Soporte FTE**: backend 61.44 vs Excel `Nomina Loaded` "Visión por perfiles" ≈ 71.29.
  **Refuta** la afirmación previa "FTE soporte 61.4 = MATCH". El gap soporte NO es staff-variable
  (cerrado por override AM) sino dotación de FTE. Requiere modules/ o staffing input.
- **examenes ≈ 0** en backend (no se computa) vs Excel 12.24 → CTS-EXAM.

Matriz completa y clasificación: `docs/refactor/cts_residual_structural_audit_v28.md`.
Veredicto: `CTS_RESIDUAL_STRUCTURAL_AUDIT_COMPLETED`. Solo +34.18 fixable sin modules/request.

## SENA/INCLUSIÓN PROVIDER PATCH APLICADO (2026-06-11, post-9a15573)

Fix aplicado en `tests/refactor/_v28_deal_provider.py`:
- `_V28_SENA_INCLUSION_SALARY` dict con `aprendiz sena`=1,750,905 / `inclusion`=1,750,905
- Fuente: Excel `Inputs de Nomina`!C59/C60 (verificado con openpyxl)
- Loop de patch en `_patch_all_staff` + alias rows para engine lookup

CTS-001 post-patch:
```
backend = 6,143.809068 COP/tx
Excel   = 6,224.575126 COP/tx
delta   =   -80.766058 COP/tx  (1.298%)  →  PARTIAL_BEST_IMPROVED
```

Residual remanente −80.77 = soporte FTE ~-138 + examenes -12.22 + crucero -10.63 + cap -5.28
                            + no-payroll +85.50 (OPEX/CAPEX). Todo fuera de scope.
Estado: `CTS_SENA_INCLUSION_PROVIDER_PATCH_APPLIED` / `CTS-001_PARTIAL_BEST_IMPROVED`.

---

## SUPPORT FTE — AUDITORÍA DE DECISIÓN (2026-06-11, post-6ce1eb7) — REFUTA "soporte ~71 FTE"

CTS-001 actual: backend 6,155.30 vs Excel 6,224.58 → **-69.27 COP/tx (1.113%)** (post exam patch).

La hipótesis "Excel soporte ~71 FTE vs backend 61.4 (gap dotación -138)" es **FALSA**. Bloque FTE
limpio de Excel (`Condiciones Cadena A`!E77:G100):

```
Excel soporte = 59.5526 FTE  ·  Backend = 61.4452 FTE  ·  delta = +1.89 (backend MÁS)
```

El gap de costo soporte (-172 COP/tx) es de **mezcla, no de conteo**: causa dominante =
`SUPPORT_FTE_FORMULA_BUG` — Excel numerador `(FTE_agentes + cargos_adicionales CCA!E26)/ratio`,
backend `fte_agentes/ratio` → Supervisor backend 13.0 vs Excel 16.37 (-3.37 FTE caro ≈ -68 COP/tx).
Ratios coinciden. **REQUIRES_MODULE_SCOPE** (`context_builder_perfiles_soporte_mixin`).

Crucero corregido: `request.json crucero=8408` (tarifa existe); falta flag `incluye_crucero` en
perfiles → `CTS_CRUCERO_INPUT_DECISION_REQUIRED` (no BLOCKED). OPEX +71.95 → request scope.

Matriz completa: `docs/refactor/support_fte_input_decision_v28.md`. Gates PASS, 0 hardcodes nuevos.

---

## CORRECCIÓN FINAL (2026-06-11, FTE/headcount/staff-variable audit)

El residual −289.44 COP/tx del `nomina_loaded` (5,115.79 backend vs 5,405.23 Excel) NO es
agente, conteo, FTE ni ramp. Descomposición exacta (÷221,000):

| Bloque | Backend | Excel | Delta |
|---|---|---|---|
| Cargado AGENTES (AM×260) | 4,189.44 | 4,189.38 | ≈0 MATCH |
| Cargado SOPORTE (staff) | 926.35 | 1,215.85 | **+289.50** |

El 100% del delta es el COSTO CARGADO de SOPORTE: Excel embebe la comisión variable de
Director de cuentas (D=3,868,125), Jefe de Operación (D=1,500,000) y Supervisor (D=700,000)
en su AM (loaded); el backend NO la incluye porque `request.json` lleva `comision_rol=0.0`
en los 72 roles operativos. El 0.70 (`pct_cumplimiento_variable`) NO mueve el total cargado
(invariante: `nomina_loaded = total_cargado`); solo reclasifica fijo↔variable.

**Clasificación: BLOCKED_MISSING_PARAMETRIZATION_SOURCE** (STAFF_VARIABLE_NOT_IN_LOADED_COST
+ INPUT_DEAL_MISMATCH en bases de staff). No hay fix de motor trazable sin tocar el deal de
entrada (prohibido). Evidencia completa: `docs/refactor/cts_fte_headcount_audit_v28.md`.

---

## Cierre temporal — CTS-001 known_delta

**Estado**: `CTS-001_FUNCTIONAL_PARITY_WITH_KNOWN_DELTA`
**Residual**: -27.53 COP/tx aprox (0.44%)
**FULL_MATCH**: NO
**Motivo**: residual menor en `CTS_SUPPORT_LOADED_MAGNITUDE` (cargado soporte W ~20.51 COP/tx bajo).
**Decisión**: diferido hasta completar mapa general de fórmulas V2-8.
**Fecha**: 2026-06-12

Componentes cerrados:
- `cargos_adicionales`: aplicado (campo en contrato + numerador FTE soporte)
- `E95 override` (Supervisor SAC 9.5): aplicado via `fte_soporte_overrides` en request
- `CAPEX C47`: exacto (Δ+0.0000)
- `C38 variable staff commission`: exacto (Δ+0.0000)
- `C46 OPEX Fijo`: exacto (Δ=0.000000)

Residual decompuesto (post commit b31427f):
- C36 Nomina Loaded: -20.51 COP/tx (`CTS_SUPPORT_LOADED_MAGNITUDE`)
- C35 Payroll: -24.36 = C36 + cap/exám/crucero (-3.85)
- C34 Total CTS: -27.53 = C35 + costos_fijos (-3.17)

Notas:
- No se declara `CTS-001_FULL_MATCH` porque `MAX_DELTA = 0.000001` no se cumple.
- No se continuará persiguiendo `CTS-001` hasta completar el mapa general de fórmulas V2-8.
- El residual queda como known_delta **temporal**, no como aceptación permanente.
- Diferido en backlog: `CTS_SUPPORT_LOADED_MAGNITUDE` (estado: DEFERRED).
