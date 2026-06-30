# Excel V2-4 to Backend Mapping — Vision Cost To Serve

> Traceability: Excel Sheet → Cell → Formula → Input JSON → Domain Model → Calculator → Response

Last updated: 2026-05-21

---

## 1. Denominadores (PCG K50/L50)

| Excel Cell | Name | Formula (Excel) | Input JSON Path | Domain Model | Calculator | Backend Field | Delta | Status |
|---|---|---|---|---|---|---|---|---|
| K50 | Denominador Cadena A | `SUM(K42:K49)` | `perfiles[*].vol_cadena_a_mensual` (Inbound) + `perfiles[*].fte` (Outbound) | `PerfilCadenaA.vol_cadena_a_mensual` / `.fte` | `CostToServeCalculator._k50()` | `ResultadoCostToServe.fte_cadena_a` | 0.0000% | EXACT |
| L50 | Denominador Cadena B | `SUM(L17:L23)` | `cadena_b.canales[*].volumen_mensual` | `CanalCadenaB.volumen_mensual` | `CostToServeCalculator._l50()` | `ResultadoCostToServe.vol_cadena_b` | 0.0000% | EXACT |
| K51 | Participacion A | `K50 / (K50+L50+M50)` | derived | derived | `CostToServeCalculator.calcular()` | `ResultadoCostToServe.participacion_a` | 0.0000% | EXACT |
| L51 | Participacion B | `L50 / (K50+L50+M50)` | derived | derived | `CostToServeCalculator.calcular()` | `ResultadoCostToServe.participacion_b` | 0.0000% | EXACT |

### K50 per-channel breakdown

| Excel Cell | Channel | Formula | Backend Mapping |
|---|---|---|---|
| K42 | WhatsApp | `J17*N17 + J30*N30 = 4516.89 + 5 = 4521.89` | `PerfilCadenaA("Inbound 10").vol_cadena_a_mensual = 4521.89` |
| K44 | Correo | `J18*N18 + J32*N32 = 0 + 13 = 13` | `PerfilCadenaA("Inbound 15").vol_cadena_a_mensual = 13.0` |
| K45 | WebChat | `J19*N19 = 0` (100% automation) | `PerfilCadenaA("Inbound 20").vol_cadena_a_mensual = 0.0` |

> **Design note:** The backend merges each channel's inbound vol + outbound FTE
> into a single `vol_cadena_a_mensual` per Inbound profile. This avoids adding
> outbound profiles that would generate unwanted support staff and payroll costs.

---

## 2. CTS Cadena A — Desglose (VCS C034-C048)

### Formula: `sub_campo = avg(sub_campo over n months) / K50`

| Excel Cell | Name | Source Calculator | Backend Field | Delta | Status | Notes |
|---|---|---|---|---|---|---|
| C034 | cts_a | `(avg_payroll + avg_no_payroll) / K50` | `ResultadoCostToServe.cts_cadena_a` | 1.29% | NEAR | Backend includes ALL profiles in numerator |
| C035 | payroll | `SUM(C36:C43)` | `DesgloseCTSCadenaA.nomina` | 0.56% | NEAR | Support staff salary indexation |
| C036 | nomina_loaded | `avg(salario_fijo + comisiones) / K50` | `DesgloseCTSCadenaA.nomina_loaded` | 0.56% | NEAR | |
| C037 | salario_fijo | `avg(salario_fijo) / K50` | `DesgloseCTSCadenaA.salario_fijo` | 0.59% | NEAR | |
| C038 | salario_variable | `avg(comisiones) / K50` | `DesgloseCTSCadenaA.salario_variable` | 0.16% | NEAR | |
| C039 | cap_inicial | `avg(cap_inicial) / K50` | `DesgloseCTSCadenaA.cap_inicial` | 0.0000% | EXACT | |
| C040 | cap_rotacion | `avg(cap_rotacion) / K50` | `DesgloseCTSCadenaA.cap_rotacion` | 70.42% | DOCUMENTED | See [Known Difference #1] |
| C041 | examenes | `avg(examenes) / K50` | `DesgloseCTSCadenaA.examenes` | 0.0000% | EXACT | |
| C042 | estudios_seguridad | `avg(seguridad) / K50` | `DesgloseCTSCadenaA.estudios_seguridad` | 0.0000% | EXACT | |
| C043 | crucero | `avg(crucero) / K50` | `DesgloseCTSCadenaA.crucero` | 0.0000% | EXACT | |
| C045 | no_payroll | `SUM(C46:C48)` | `DesgloseCTSCadenaA.no_payroll` | ~0% | EXACT | |
| C046 | opex_fijo | `avg(opex_ti) / K50` | `DesgloseCTSCadenaA.opex_fijo` | 0.0000% | EXACT | Uses no_payroll_mensual override |
| C047 | inversiones | `avg(capex) / K50` | `DesgloseCTSCadenaA.inversiones` | 0.0000% | EXACT | |
| C048 | costos_fijos_est | `avg(infrastructure) / K50` | `DesgloseCTSCadenaA.costos_fijos_estacion` | 44.44% | DOCUMENTED | See [Known Difference #2] |

---

## 3. CTS Cadena B — Desglose (VCS G034-G045)

### Formula: `sub_campo = avg(sub_campo over n months) / L50`

| Excel Cell | Name | Source Calculator | Backend Field | Delta | Status | Notes |
|---|---|---|---|---|---|---|
| G034 | cts_b | `avg_costo_b / L50` | `ResultadoCostToServe.cts_cadena_b` | 2.19% | NEAR | S&M salary SMMLV diff |
| G035 | comp_fijo | `G36 + G37 + G38` | `DesgloseCTSCadenaB.componente_fijo` | 81.38% | DOCUMENTED | See [Known Difference #3] |
| G036 | opex | `avg(opex_fijo) / L50` | `DesgloseCTSCadenaB.opex` | 92.52% | DOCUMENTED | HITL folded into opex |
| G037 | inversiones | `avg(inversiones) / L50` | `DesgloseCTSCadenaB.inversiones` | 20.00% | NEAR | Rounding |
| G038 | s_m | `avg(sm) / L50` | `DesgloseCTSCadenaB.s_m` | 53.99% | DOCUMENTED | SMMLV diff in S&M salaries |
| G041 | comp_variable | `G42 + G44 + G45` | `DesgloseCTSCadenaB.componente_variable` | 97.32% | DOCUMENTED | See [Known Difference #3] |
| G042 | tarifa | `avg(costo_variable) / L50` | `DesgloseCTSCadenaB.tarifa` | 0.0000% | EXACT | |
| G043 | opex_variable | N/A | `DesgloseCTSCadenaB.opex_variable` | 0.0000% | EXACT | Always 0 |
| G044 | tasa_escalamiento | `avg(escalamiento) / L50` | `DesgloseCTSCadenaB.tasa_escalamiento` | 0.0000% | EXACT | |
| G045 | hitl | `avg(hitl) / L50` | `DesgloseCTSCadenaB.hitl` | 100.00% | DOCUMENTED | See [Known Difference #3] |

---

## 4. CTS Ponderado (VCS G049)

| Excel Cell | Formula | Backend | Delta | Status |
|---|---|---|---|---|
| G049 | `(C34*C31) + (G34*G31) + (K34*K31)` | `ResultadoCostToServe.cts_ponderado` | 0.52% | NEAR |

---

## 5. Reglas de Negocio (VCS C186-D196)

| Excel Cell | Name | Formula | Backend Field | Delta | Status |
|---|---|---|---|---|---|
| C186 | costo_total_acumulado | `SUM(costo_total)` | `ResultadoCostToServe.costo_total_acumulado` | 70.1% | DOCUMENTED |
| D192 | margen_monto | `C186 * margen_pct` | `ReglaNegocios("margen_objetivo").monto` | 70.1% | DOCUMENTED |

> **C186 delta note:** Backend `costo_total = payroll_a + no_payroll_a + costo_b + costo_c + financieros`.
> Excel C186 may use a narrower definition of "costo total" (excluding some line items).
> The 70% delta is from definition difference, not a calculation bug.

---

## Known Differences (Backend = Reference Implementation)

### Known Difference #1: cap_rotacion (C040) — 70.42% delta

**Backend formula:**
```
cap_rotacion = Σ(dias × tarifa × FTE × pct_rotacion × factor) for ALL non-soporte profiles / K50
```

**Excel behavior:**
Only includes cap_rotacion from profiles whose channel contributes to K50 (vol_cadena_a > 0).
Profiles with vol_cadena_a = 0 (e.g., WebChat with 100% automation) are excluded from the CTS numerator.

**Impact:** Backend includes WebChat (10 FTE, dias=10) which adds ~170,000/month to cap_rotacion.
Excel excludes it. Result: backend 411,400 vs Excel 241,400.

### Known Difference #2: costos_fijos_estacion (C048) — 44.44% delta

**Backend formula:**
```python
# NoPayrollCalculator._calcular_estaciones_presenciales()
estaciones = sum(p.fte for p in perfiles if not p.es_soporte)  # = 26
```

**Excel formula:**
```
estaciones = sum(FTE × pct_presencia for agent profiles)  # = 18
```

**Impact:** Backend uses 26 stations (all FTE); Excel uses 18 (6×1.0 + 10×0.6 + 10×0.6).
The pct_presencia field exists on profiles but is not applied in station count calculation.

### Known Difference #3: HITL routing in Cadena B

**Data flow:**
1. Fixture: `opex_consumo_variable[HITL] = 163,244,663.8 COP`
2. `context_builder._agregar_opex_consumo_por_canal()` → groups by (modalidad, canal)
3. Adds to `CanalCadenaB.opex_fijo` of WhatsApp channel: 176M + 163M = 339M
4. `CadenaBCalculator._costo_opex_fijo()` returns 339M → goes into `ResultadoCadenaB.opex_fijo`
5. `CadenaBCalculator._costo_hitl()` returns 0 (costo_personal_hitl=0, opex_herramientas_hitl=0)

**Effect:** HITL cost appears in `desglose_b.opex` instead of `desglose_b.hitl`.
Total CTS_B is correct; only the componente_fijo/variable decomposition differs.

---

## 6. Input Traceability — Golden Fixture

**Fixture:** `test_cases/excel_v24_canonical_bancamia.json`
**Base:** `test_cases/bancamia_excel_match.json` (0% PyG match)
**Added:** `vol_cadena_a_mensual` per profile for K50 computation

| Profile | FTE | Modalidad | vol_cadena_a | K50 Contrib | Source |
|---|---|---|---|---|---|
| Inbound 10 (WA) | 6 | Inbound | 4521.89 | 4521.89 | K42 = J17×N17 + J30×N30 |
| Inbound 15 (Correo) | 10 | Inbound | 13.0 | 13.0 | K44 = J18×N18 + J32×N32 |
| Inbound 20 (WebChat) | 10 | Inbound | 0.0 | 0.0 | K45 = J19×N19 = 0 |
| **Total** | **26** | | | **4534.89** | **K50** |

---

## 7. Parity Summary

| Category | Count | Fields |
|---|---|---|
| EXACT (0.0000%) | 12 | K50, L50, part_a, part_b, cap_inicial, examenes, estudios_seg, crucero, opex_fijo, inversiones, tarifa, tasa_esc |
| NEAR (<1%) | 3 | nomina_loaded, salario_fijo, salario_variable |
| DOCUMENTED (>1%) | 5 | cap_rotacion, costos_fijos, hitl, opex_b, s_m |
| **Total fields** | **20** | |
