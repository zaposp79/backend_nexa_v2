# Backlog V2-8 — Fuera de sesión actual

---

## ENGINE_RUNTIME_CONTRACT_AUDIT — COMPLETED (2026-06-12)

**Audit performed:** Read-only. No code changes. No golden/storage/request modifications.  
**Doc:** `docs/refactor/engine_runtime_contract_audit.md`  
**Baseline at audit:** golden 99/99 PASS | make verify PASS | 0 functional changes

| Finding | Severity | Recommended fix |
|---------|----------|----------------|
| `ValidationError` NameError bug in `user_input_builders_cadena_a.py:162` | HIGH | Add missing import |
| `IParametrizationProvider.tasa_mensual_financiacion` Protocol/impl mismatch | HIGH | Remove `@property` from Protocol |
| `except Exception: v27_defaults = {}` silently swallows provider failures | MEDIUM | Add ERROR log + re-raise or explicit warning |
| Hardcoded `1423000` salary in volumetria fallback path | MEDIUM | Replace with parametrization lookup |
| GAP-CADENA-A-FASE4 — `panel.margen` vs `get_margen_minimo` unresolved | MEDIUM | Business decision required |
| Engine-level determinism/invariant tests missing | LOW | Add `tests/unit/test_engine_invariants.py` |
| Missing HTTP 422 integration test for ParametrizationError | LOW | Add to `tests/api/` |

**This audit does not reopen V2-8, CTS-001, or CTS-002. V2-8 remains CLOSED / STABLE_FOR_PRODUCTION.**

---


> Deudas y diferidos fuera del foco inmediato del plan V2-8 parity.  
> Registrar aquí cualquier tentación de fix que aparezca durante una sesión.  
> No corregir nada de este backlog sin abrir una sesión explícita para ello.

---

## V2-8 ARCHIVED — 2026-06-12

**V2-8 is stable for production. All work complete. Archive: `v28_archive_index.md`**

**Final validation:** golden 99/99 PASS | make verify PASS | validate-excel-v28 PASS 6/6 | CTS-001 ACCEPTED_DELTA (-0.099%) | CTS-002 EXACT MATCH

### Closed Fronts (Do Not Reopen)

✅ **CTS-001** — CLOSED_ACCEPTED_DELTA (commit 5802a81)  
✅ **CTS-002** — FORMALLY_CLOSED (commit 24743c0)  
✅ **INPUT-PCT-ACUM** — NO_IMPACT (audit complete, 2026-06-12)  
✅ **ROLES-OP-STAFFCONFIG** — CLOSED (audit complete, 2026-06-12)  
✅ **VTM-001** — Vision Tarifas mapping fixed (commit bb077ae)  
✅ **OP Config P4** — economic component + tasa_financiacion (commit 939a36a)  
✅ **Request P2/P3** — tasa_ica, dias_capacitacion aligned (commit b8b3000)  
✅ **PyG anchors** — M1/M7/M19 refreshed (commit 5802a81)  
✅ **V27 fixture regen** — 96/96 PASS (commit 2175069)  
✅ **E95 override** — Supervisor 9.5 wired (commit 5802a81)  
✅ **Director de Performance** — WhatsApp 1.0 override (commit 5802a81)  
✅ **CAPEX C47** — exact match 103.044 (commit 5802a81)  

### Optional Future Work (Not V2-8)

⊘ **Exact-parity residuals** (training/fixed-cost/SENA-Inclusión) — if business escalates as requirement  
⊘ **P&G / Vision Tarifas generalization** — extend override + exclusion mechanisms (next phase, no urgency)  

**Do not resume any of these as V2-8 work. Start as a new phase if needed.**

---

## Triage post-CTS-002 — remaining gaps (2026-06-12)

| ID | Gap | Tipo | Status | Acción recomendada |
|----|-----|------|--------|--------------------|
| ~~**E95-WIP**~~ | `test_e95_supervisor_override_applied` — `fte_soporte_overrides: {"Supervisor": 9.5}` restored in request.json; WIP committed (cadena_a contract + mixins + test_support_fte_v28.py). PyG anchors updated (M1/M7/M19 ingreso_a+total). Golden: 24/72 ✅ | REQUEST_VALUE_GAP | ✅ COMPLETED 2026-06-12 | — |
| ~~**V27-FIXTURE-REGEN**~~ | 24 golden failures drifted by OP tasa_financiacion 0.0088→0.0153. `cts_v27_real_request.json` (13 fields) + `vt_v27_real_request.json` (11 fields) updated. Golden: **0/96** ✅. make verify: PASS. No modules/request/storage touched. | PREEXISTING_INFRA_PARAMETRIZATION | ✅ COMPLETED 2026-06-12 | — |
| ~~**CTS-001**~~ | Residual **-20.38 COP/tx (0.327%)** ✅ **CLOSED_ACCEPTED_DELTA**. Decomposition: salary loaded -13.37 (`CTS_SUPPORT_LOADED_MAGNITUDE`) + training/exam -3.85 (`KNOWN_DELTA_TRAINING`) + costos_fijos -3.17 (`KNOWN_DELTA_COSTOS_FIJOS`). OPEX fijo + CAPEX = EXACT MATCH. E95=9.5 = MATCH. Full RCA: `cts_001_resume_from_clean_baseline.md` (2026-06-12). Gate 0.5% ✅. | KNOWN_DELTA | ✅ COMPLETED 2026-06-12 | If deeper closure desired: audit salary loaded per role (CCA rows vs provider W overrides). `business-rules-agent` + opus. |
| ~~**ROLES-OP-STAFFCONFIG**~~ | **RESOLVED**: `roles_excluidos_deal` frozenset wired from `roles_operativos[].incluye_en_deal=False` (request.json). JCR/AFAC/GTR correctly excluded (support mixin applies exclusion). Reconciliation: `roles_op_staffconfig_status_reconciliation.md` (2026-06-12). Full RCA: `cts_001_support_loaded_salary_audit.md`. | BACKEND_NOT_CONSUMING_FIELD | ✅ CLOSED 2026-06-12 | — |
| ~~**CTS-001-UNDERLYING-DEFICIT**~~ | **RESOLVED (RCA + FIX):** -79.46 COP/tx = 99.75% Director de Performance G78 literal. Fixed via `fte_soporte_overrides` channel-level override: `{"Director de Performance": {"WhatsApp": 1.0}}` (request.json Cadena B). CTS-001 final = 6,218.424663 (delta -0.099%, within 0.5% gate). Simultaneous fix of Director override + ROLES-OP-STAFFCONFIG (commit 5802a81). Audit: `cts_001_included_roles_salary_deficit_audit.md` (2026-06-12). | EXCEL_QUIRK (literal G78) | ✅ CLOSED 2026-06-12 | — |
| ~~**INPUT-PCT-ACUM**~~ | `porcentaje_acumulado.actual`=0 (PRE-ALIGNED). Panel!C75=0 (display-only derived cell, 0 downstream refs in Excel). Field removed from engine as DEAD_FIELD_LEGACY (BUSINESS_RULES_FIX_3). **Impact = 0** on P&G, Tarifas, CTS. | NO_IMPACT | ✅ CLOSED 2026-06-12 | Audit: `input_pct_acum_audit_post_v28_closure.md` |

---

## Nuevos gaps — V28_ENGINE_FORMULA_MAP_CONTINUATION (2026-06-12)

Identificados en `docs/refactor/v28_engine_formula_map_continuation.md`.

| ID | Gap | Tipo | Status | Prioridad |
|----|-----|------|--------|-----------|
| ~~**VTM-001**~~ | Vision Tarifas H19 field mapping — `ingreso_mensual = pyg_por_mes[2].ingreso_bruto` (M3 monthly, +1.9% HME delta ACCEPTED) | BACKEND_METRIC_NOT_EXPOSED | ✅ APPLIED 2026-06-12 | P1 |
| ~~**REQUEST-PCT-ACUM**~~ | `porcentaje_acumulado.actual` ya era 0 en working copy | REQUEST_FIX | ✅ PRE-ALIGNED | P2 |
| ~~**REQUEST-ICA**~~ | `tasa_ica` = 0.00966 (corregido de 0.01 · 2026-06-12) | REQUEST_FIX | ✅ APPLIED | P3 |
| ~~**PROVIDER-TASA-FINANC**~~ | `tasa_financiacion` = 0.0153 (config sheet agregada al active OP · 2026-06-12) | PROVIDER_FIX | ✅ APPLIED | P4 |
| ~~**PARAM-ROTACION-SAC**~~ | rotacion SAC 0.09→0.077175 (Rot!F19 · 2026-06-12) | PARAM_VALUE_FIX | ✅ APPLIED | P5 |
| ~~**CTS-002**~~ | CTS Cadena C delta ~1% (51.28 COP/tx) — 4 fixes aplicados: tecnología + OPEX fijo + inversiones (`ACCEPTED_EXCEL_QUIRK`) + equipo. Delta final 2.24e-6 COP/tx. K34 = MATCH. | MODULE_FORMULA_GAP | ✅ COMPLETED 2026-06-12 | P6 |
| **BASE-INGRESO-PYG** | HME cached vs backend dinámico (~20%) | NOT_IMPLEMENTED_BY_DESIGN | ACCEPTED_ARCHITECTURAL_DELTA | P7 |
| ~~**ECONOMIC-COMPONENT-2026**~~ | `'20% SMMLV - 80% IPC'` añadido al active OP-Componente | MISSING_EXISTING_FIELD | ✅ APPLIED | P4b |
| ~~**ANCHOR-UPDATE-PYG**~~ | `TestPYGAbsoluteAnchorsV28` 12 anchors refreshed (M1/M7/M19 × a/b/c/total) | ANCHOR_UPDATE | ✅ COMPLETED | P4c |
| **V28_ENGINE_FORMULA_MAP_CONTINUATION** | mapa completado | — | ✅ **COMPLETED** | — |

---

## Bloqueador maestro

~~INPUT-001 (INPUT_DEAL_MISMATCH) bloquea PYG-001 y CAPEX-001.~~

**INPUT-001 RESUELTO** por Option B (commit `66e9ae8`, 2026-06-11).
Deal canónico: SAC / METROCUADRADO COM SAS / Grupo Aval.
PYG-001 y CAPEX-001 desbloqueados. Próximo target activo: **PYG-001**.

---

| ID | Tema | Estado | Cuándo retomarlo |
|----|------|--------|------------------|
| **INPUT-001** | INPUT_DEAL_MISMATCH — servicio/cliente/tipo_cliente (Panel!C5/C6/C8) | ✅ **RESOLVED** — commit `66e9ae8` (Option B: SAC/METROCUADRADO/GrupoAval) | — CERRADO — |
| **STRUCT-001** | REQUEST_STRUCTURE_GAP — escenarios_comerciales + condiciones_cadena_a/b/c | ✅ **RESOLVED** — commit `66e9ae8` (canales/perfiles V2-8 adoptados) | — CERRADO — |
| **SNAPSHOT-001** | `test_request_json_after_fix` (test_input_contract_fix_b1.py) | ✅ **RESOLVED** — commit `66e9ae8` (costo_b anchor actualizado a V2-8) | — CERRADO — |
| **SNAPSHOT-002** | `test_golden_tests_still_pass` (test_formula_id_guardrails.py) | ACCEPTED_DEBT — guardrail falla porque goldens `_v27` esperan SMMLV=1,750,905 pero productiva 2026 tiene SMMLV=2,100,000 | Stage 3 o cuando se decida política de goldens V2-7 vs productiva 2026 |
| GOLDEN-001 | 42/63 goldens `_v27` fallan bajo productiva 2026 activa | ACCEPTED_DEBT — fixtures frozen a SMMLV=1,750,905 | Fase separada: decidir xfail vs goldens V2-8 paralelos |
| **PYG-001** ✅ **CLOSED_WITH_ACCEPTED_DELTA** | Stage 2 Target 1 — P&G ingreso indexado (`PyGCalculator.calcular_mes` × IPC/SMMLV anual) | **CLOSED** — mecanismo implementado (ratio IPC exacto ✓); numeric parity NOT CLAIMED due to ACCEPTED_ARCHITECTURAL_DELTA (BASE_INGRESO_MISMATCH). Ver `docs/refactor/pyg_001_v28_evidence.md`. | — CERRADO — |
| **CAPEX-001** ✅ **COMPLETED** | Stage 2 Target 2 — Cadena C L11 amortización CAPEX con factor financiero (`_costo_amortizacion_inversion`) | **COMPLETED** — fórmula `(inversion_anual/12)*(1+tasa_interes_mensual)` ya presente en `reglas.py:182`. Golden test `test_capex_001_v28_cadena_c.py` creado con valores V2-8 reales (SUM J62:J65=12,778,653.116). 4/4 tests verdes. | — CERRADO — |
| **BASE_INGRESO_MISMATCH** | Backend calcula ingreso dinámicamente desde costos; Excel usa base fija HME!C296=1,822,157,751.25. Delta ≈ 20% Cadena A, 15% Cadena B, 7% Cadena C en M3. | **FORMULA_STRUCTURE_ALIGNED** (Option B-revisada implementada). Fórmula backend ahora = `costo_total_cadena / (1-margen)` donde costo_total incluye ICA+GMF+ComAdm+Pólizas+Fin. Residual delta ~18% = INPUT_DEAL_MISMATCH (Excel cached con deal diferente). IPC-RATIO MATCH (delta=0). Ver `docs/refactor/hme_two_pass_solver_evidence.md`. | CLOSED — delta residual = ACCEPTED_ARCHITECTURAL_DELTA (INPUT_DEAL_MISMATCH) |
| **CADENA_C_NULL** | `ingreso_bruto_c = 0` — root cause: `tarifa_proveedor_canal.valor` → `opex_var_integ` en lugar de `tarifa_proveedor` en el adapter. | ✅ **RESOLVED** — commit `69b77a9`. M1 ingreso_c = 981,238,725. Residual ~7% = BASE_INGRESO_MISMATCH (accepted). | — CERRADO — |
| **REQUEST_COMPONENTE_TECNOLOGICO** | `request.json` tiene `componente_tecnologico: "IPC"` en lugar de `"20% SMMLV 80% IPC"` (Panel!L8 en Excel) | ACCEPTED_CONSTRAINT — request.json no modificable por kill-switch | Sesión de producto para corregir el deal request |
| POLIZA-ICA-001 | ICA discrepancia — Panel!C34=0.01 vs Tasas!B37=0.00966 vs req=0.0097 | DEFERRED — ningún valor coincide exactamente | Revisión con stakeholder de negocio para deal SAC/METROCUADRADO |
| STRUCT-002 | STRUCTURE_EXTENSION no consumidas — datos_operativos.antiguedad, periodo_pago; reglas_negocio.margen_objetivo_cadena_b, descuento_volumen | DEFERRED — loader las ignora (hardcoded) | Evaluar en Stage 3 si motor debe leer estos campos |
| ~~**CTS-001**~~ | CTS Cadena A parity — Excel VCT!C34=6224.575126 vs backend=**6218.424663**, delta=**-6.150 COP/tx (-0.099%)**. All sub-components: C35/C37/C38/C45/C47 aligned. Director de Performance WhatsApp=1.0 via per-channel fte_soporte_overrides. JCR/AFAC/GTR excluded via incluye_en_deal=False. Fix: commit `5802a81`. | ✅ `CLOSED_ACCEPTED_DELTA` — 0.099% < 0.5% gate. Residual (-6.150) = training/fixed-cost known deltas. Final validation: 99/99 golden PASS, verify PASS, validate-excel-v28 PASS 6/6. Docs: `cts_001_resume_from_clean_baseline.md`. | — CERRADO — |
| **CONTRACT-OVERRIDE-PER-ROL** | Supervisor SAC E95=9.5 literal (override manual); la fórmula `(130+12)/20` da 7.1 → residual +2.4 FTE Supervisor (≈+50 COP/tx en payroll). | ✅ **RESOLVED** 2026-06-12 — implementado override opt-in per-rol `fte_soporte_overrides: Dict[str,float]` en `PerfilCadenaAV1` (default vacío = legacy). Request SAC `{"Supervisor": 9.5}` (Excel CCA!E95). Supervisor SAC 7.1→9.5; payroll C35 -74.94→-24.36. 0 hardcodes (9.5 en request). Ver `formula_first_diff.md`. | — CERRADO — |
| **CRUCERO-RESIDUAL-001** | Crucero backend 9.892 vs Excel 10.629, residual -0.737 COP/tx. Root cause: Excel `CCA!E152 = tarifa × (fte_agentes + cargos_adicionales)`, backend solo usa `fte_agentes`. **Simulación: cerrable +0.7375 SOLO via aproximación (escalar tarifa), no fix legítimo.** | BLOCKED — `DO_NOT_APPLY_COMPENSATING_GAP` / misma raíz que `CONTRACT_CHANGE_CARGOS_ADICIONALES` — `v28_what_if_gap_simulation.md` | Se resuelve al agregar `cargos_adicionales` al contrato (no via tarifa) |
| ~~**CTS-002**~~ | CTS Cadena C delta ~1% — Excel K34=5,278.326744 vs backend=5,278.326747, delta=2.24e-6. **K34 = MATCH.** 4 fixes: `2d006cc` (tech indexation) · `ee1e7db` (OPEX fijo) · `cd5bb6d` (inversiones `ACCEPTED_EXCEL_QUIRK`) · `a146370` (equipo transversal) | ✅ COMPLETED 2026-06-12 — CADENA_C_K34_MATCH | — CERRADO — |
| ~~**VTM-001**~~ | Vision Tarifas ingreso field mapping — `reglas.py:614` `ingreso_mensual = pyg_por_mes[2].ingreso_bruto` (M3 monthly, +1.9% HME architectural delta ACCEPTED). Golden fixture updated (H19_ANCHOR_UPDATE_ALLOWED). | ✅ RESOLVED 2026-06-12 | — CERRADO — |
| **INPUT-DIAS-CAP** | `dias_capacitacion_perfil` Excel `Condiciones Cadena A`!E139=**11** vs request.json=**10**. Afecta cap inicial/rotación (`nomina.py:229-257`). **Impacto medido: +2.898 COP/tx** (CTS 2.110%→2.063%). | ✅ **RESOLVED** 2026-06-12 — request.json actualizado (E139=F139=G139=11 confirmado). CTS delta -131.33→-128.43. | — CERRADO — |
| ~~**INPUT-PCT-ACUM**~~ | `reglas_negocio.porcentaje_acumulado.actual`=0 (request aligned). Panel!C75=0 (display-only, no downstream Excel refs). Engine removed field as DEAD_FIELD_LEGACY. Impact=0. | NO_IMPACT | ✅ CLOSED 2026-06-12 | Audit: `input_pct_acum_audit_post_v28_closure.md` |
| **STAFF-COMISION-001** | `comision_rol` staff=0.0 en request; Excel `Condiciones Cadena A`!F44/F51/F62 (Director 3,868,125 / Jefe Op 1,500,000 / Supervisor 700,000). **Patch request medido: Δ=0.0** (campo `PRESENT_NOT_CONSUMED`; comisión ya embebida en provider W-override). | `ALREADY_APPLIED_BASELINE` (vía provider) — `v28_what_if_gap_simulation.md` | Cerrar junto a `cargos_adicionales` si se decide modelarlo por request |
| **ROLES-OP-STAFFCONFIG** | Motor consume `staff_config[]` (activo/ratio_override), NO `roles_operativos[]` del deal. Activación JCR/AFAC/GTR divergente (Excel C79/C80/C87=False vs request incluye_en_deal=true). | OPEN — `BACKEND_NOT_CONSUMING_FIELD` — `v28_input_full_mapping.md` §1 | Reconciliar: emitir `staff_config` o parsear `roles_operativos` |
| **AUSENTISMO-NOT-CONSUMED** | `pct_ausentismo` (Panel!C19=0.065) presente en request/contexto pero no alimenta fórmula de costo verificable. | OPEN — `PRESENT_NOT_CONSUMED` — `v28_input_full_mapping.md` §4 | Confirmar si Excel lo usa en algún costo; si no, doc-only |
| **CTS-CAPEX-AMORT** | CAPEX/Inversiones C47 backend 182.20 vs Excel 103.04, +79.16 COP/tx (no +16.72 — re-medido en deal SAC con OPEX alineado). Root cause: (1) backend leía `meses_amortizacion` (request usa `meses_a_diferir`) → `meses=1` → `precio_mensual=precio_total`; (2) gate `mes≤meses` con meses=1 → todo CAPEX en mes 1 (966M)/24. Excel: amortiza plano `precio/meses_a_diferir × cantidad × (1+L11)` todos los meses del contrato. | ✅ **RESOLVED** 2026-06-12 — `_build_amortizable_item` corregido: precio_mensual del request (= precio/meses_a_diferir), `meses=meses_contrato` (cobro plano). C47 182.20→**103.0436 (Δ+0.0000 EXACT)**. Ver `formula_first_diff.md`. Drift esperado: 4 anchors no_payroll v27 frozen (SNAPSHOT_REGENERATION_REQUIRED, diferido). | — CERRADO — |
| **WORKTREE-REQUEST-NULL** | `request/request.json` sin commitear (WIP `OPEX_REQUEST_ALIGNMENT`) deja `cantidad: null` en `condiciones_cadena_a/perfiles[1]` (WhatsApp) `opex_fijo.items[3]` y `[4]` → `TypeError: float(None)` en `context_builder_perfiles_soporte_mixin.py:398`; rompe **todos** los gates de motor (CTS golden, validate-excel-v28). En `HEAD` `6778540` hay 0 nulos y los gates pasan. Detectado en `v28_excel_engine_lineage_fast_pass.md` §0/§10. | ✅ **RESOLVED** — `cantidad: 0` (WhatsApp no usa Genesys; Excel No payroll sheet WhatsApp Genesys = 0). Gates: CTS 2/2, exam/crucero 2/2, validate-excel-v28 6/6 PASS. | — CERRADO — |
| **PARAM-ROTACION-SAC** | Rotación SAC: `_v28_deal_provider.py:208` → 0.09→**0.077175** (Rot!F19 = AVERAGE B19:E19). Fix aplicado 2026-06-12. | ✅ **RESOLVED** — `PARAM_VALUE_FIX_P5_ROTACION_SAC`. `validate-excel-v28` PASS 6/6, PyG 7/7, CTS/exam/crucero intactos. | — CERRADO — |
| **PARAM-TASA-FINANC-OPCONFIG** | `tasa_financiacion`: OP-Config sheet ausente en parametrización activa → `financial_parametrization_repository.py:177` usa default 0.0088 con WARNING. Detectado en `v28_excel_engine_lineage_fast_pass.md` §4. | OPEN — `PARAM_MISSING_EXISTING_FIELD` | Poblar OP-Config en parametrización (campo existente, sin schema nuevo) |
| **CTS-VARIABLE-INDEXATION-AGING** | C38 Salario Variable backend 705.88 vs Excel 775.74 (-69.86). **Diagnóstico previo (aging ≈1.0989) REFUTADO:** filas CTS planas 24m (sin aging); agentes ya coinciden (Excel usa partición igual que backend, fijo agente=130×(W62−D62)). Causa real = comisión variable de STAFF (Supervisor D57×9.5=6,650,000, Jefe D46, Director D39) que Excel suma a la variable; backend tenía `comision_pct=0` para staff. | ✅ **RESOLVED** 2026-06-12 — `CTS_VARIABLE_COMMISSION_STAFF`. Poblado `salario`(=C)+`comision_pct`(=D/C) staff en `_v28_deal_provider.py` (+ alias accent-stripped). C38 **775.7432 (Δ+0.0000 EXACT)**, C37 +49.35→-20.51, total-invariante. `PROVIDER_VALUE_MISMATCH`. Ver `formula_first_diff.md` §P4. | — CERRADO — |
| **CTS-SUPPORT-LOADED-MAGNITUDE** | Salary loaded residual: **-13.37 COP/tx** (improved from -20.51 at formula_first_diff §P4). Provider patches 20 roles W-column, but aggregate nomina_loaded still -13.37 below Excel C36. Training/exam/crucero -3.85 stable. Costos fijos -3.17 stable. Full decomposition: `cts_001_resume_from_clean_baseline.md`. Total CTS delta = -20.38 (0.327%). | **DEFERRED** — within 3% gate; `PAUSED_KNOWN_DELTA` maintained. | Audit salary loaded per-role (CCA rows vs provider overrides) if further closure desired |
| **V28_ENGINE_FORMULA_MAP_CONTINUATION** | Mapa fórmula-por-fórmula de hojas intermedias y visiones del motor V2-8: Inputs Nomina, Nomina Loaded, No Payroll, Costo Fijo, Costo Variable, Costo Cadena C, Costos Totales, Pólizas/Financiación, Vision CTS (pendientes), Vision P&G, Vision Tarifas. Consolidar gaps por tipo: request, parametrización, contrato, módulo, fórmula, known_delta. Luego buscar paridad global. | **NEXT** — primer frente tras cerrar CTS-001 como known_delta | Iniciar en próxima sesión de fórmulas |
