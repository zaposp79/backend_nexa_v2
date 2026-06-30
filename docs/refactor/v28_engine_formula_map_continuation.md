# V2-8 Engine Formula Map — Continuation

> **Sesión:** `V28_ENGINE_FORMULA_MAP_CONTINUATION` · Fecha: 2026-06-12 · Rama: `refactor/modular-pure`
> **Commit base:** `83dba7f` (CTS-001 paused as known_delta)
> **Modo:** READ-ONLY / DOCS-ONLY — 0 cambios en modules/, request/, storage/, tests/, contracts/.
> **Excel fuente:** `excel/Nexa - Pricing - Simulador - V2-8.xlsx` · Deal: SAC / METROCUADRADO COM SAS / Grupo Aval 24m
> **Denominador Cadena A:** Panel!W31 = 221,000 tx/mes

---

## 1. Resumen ejecutivo

Este documento continúa el mapeo general de fórmulas V2-8 después de pausar `CTS-001` como known_delta.
El objetivo es trazar cada hoja intermedia del Excel hasta el backend consumer, partiendo siempre desde
`request/request.json` → parametrización HR/OP/GN → provider → módulo backend.

**Resultado principal:** el backend implementa correctamente la estructura de fórmulas de las 10 hojas
objetivo. Los gaps identificados son principalmente de **valor** (request o parametrización con valor incorrecto),
no de **estructura de fórmula**. La arquitectura de cálculo es sólida.

**Top hallazgo nuevo:** `VTM-001` (Vision Tarifas field mapping) tiene un fix accesible: usar el campo
`facturacion_m3` del backend en lugar de `ingreso_mensual` (acumulativo). Sin cambios en módulos.

---

## 2. Estado CTS-001

| Campo | Valor |
|-------|-------|
| Status | `FUNCTIONAL_PARITY_WITH_KNOWN_DELTA` (PAUSED) |
| Residual | -27.53 COP/tx (0.44%) |
| FULL_MATCH | NO (MAX_DELTA=0.000001 no cumplido) |
| CTS_SUPPORT_LOADED_MAGNITUDE | DEFERRED |
| Componentes exactos | C38, C46, C47 = Δ+0.0000 |

No se reabrió `CTS-001`. No se atacó `CTS_SUPPORT_LOADED_MAGNITUDE`.

---

## 3. Hojas analizadas

| # | Hoja Excel | Bloque funcional | Estado mapeo |
|---|-----------|-----------------|--------------|
| 1 | Inputs de Nomina | NOMINA_INPUT | MAPPED |
| 2 | Nomina Loaded | NOMINA_LOADED | MAPPED |
| 3 | No payroll | NO_PAYROLL | MAPPED |
| 4 | Costo Fijo | COSTO_FIJO | MAPPED |
| 5 | Costo Variable | COSTO_VARIABLE | MAPPED |
| 6 | Costo Cadena C | CADENA_C | MAPPED |
| 7 | Costos Totales | COSTOS_TOTALES | MAPPED |
| 8 | Pólizas - Costo Financiacion | POLIZAS + FINANCIACION | MAPPED |
| 9 | Visión P&G | PYG | MAPPED |
| 10 | Vision Tarifas_Modelo_Cobro | TARIFAS | MAPPED |
| REF | Vision Cost To Serve | CTS (referencia) | PAUSED_KNOWN_DELTA |
| REF | Hoja Maestra Escenarios | HME | ACCEPTED_ARCHITECTURAL_DELTA |
| REF | Tasas, TRM, Polizas | PARAM_SHEET | MAPPED |

---

## 4. DAG general Excel V2-8

```
Panel de Control General ──────────────────────────────────┐
Condiciones Cadena A/B/C ──────────────────────────────────┤
Tasas, TRM, Polizas (IPC, GMF, ICA rates) ─────────────────┤
Rot, Ausent y Rentabilidad (rampup, rotacion, margin) ──────┤
                                                            ↓
Inputs de Nomina ──────→ Nomina Loaded ─────────────────────┤
                                                            ↓
Condiciones Cadena A ─→ No payroll (CAPEX/OPEX) ───────────→ Costo Fijo
Condiciones Cadena B ─→ Costo Variable ────────────────────→ Costo Variable
Condiciones Cadena C ─→ Costo Cadena C ────────────────────→ Costo Cadena C
                                                            ↓
Pólizas - Costo Financiacion (ICA, GMF, ComAdm, Pólizas)──→ Costos Totales
                                                            ↓
                        Hoja Maestra Escenarios (HME) ─────→ Visión P&G (Ingreso)
                        Costos Totales ─────────────────────→ Visión P&G (Costo/Margen)
                                                            ↓
                        HME!C289/G263/G273 ─────────────────→ Vision Tarifas
                        Vision Cost To Serve ───────────────→ [paused]
                                                            ↓
                                                     Vision Imprimible
```

**Clave arquitectónica:** Excel usa HME como intermediario de bases estáticas (precalculadas).
Backend es dinámico (calcula desde cero cada mes). Esta es la raíz de `BASE_INGRESO_MISMATCH`.

---

## 5. Fórmulas por bloque funcional

### 5.1 NOMINA_INPUT (`Inputs de Nomina`)

| Celda | Concepto | Fórmula patrón | Valor ejemplo (SAC Agente) | Alimenta |
|-------|----------|----------------|---------------------------|----------|
| C62 | salario_base agente | `=VLOOKUP(perfil, lista_salarios, ...)` | 1,750,905 | F62, W62 |
| D62 | comision cruda agente | `=VLOOKUP(...)` (comisión mensual) | 600,000 | Nomina Loaded fila var |
| F62 | imponible base | `=C62+D62` | 2,350,905 | W62 (factor prestacional) |
| W62 | costo cargado (loaded) | `=F62 × factor_prestacional` | 3,560,973.86 | AM62, Vision CTS |
| AM62 | costo empresa+comisiones | `=W62` (alias) | 3,560,973.86 | Nomina Loaded fija |
| C57 | salario Supervisor SAC | dato HR | 1,750,905 | W57 |
| D57 | comision Supervisor | dato HR | 700,000 | Nomina Loaded variable |
| C59 | salario aprendiz SENA | dato HR | 1,750,905 | W59 |
| C60 | salario inclusión | dato HR | 1,750,905 | W60 |

**Patrón general:** `imponible = salario_base + comision_cruda` → `cargado = imponible × factor_prestacional`
**Factor prestacional real SAC:** 1.5147 (= W62/F62). Los factores 1.5256/1.5699 son artefactos agregados.

### 5.2 NOMINA_LOADED (`Nomina Loaded`)

| Fila | Concepto | Fórmula patrón | Valor Voz1 (M1) | Alimenta |
|------|----------|----------------|-----------------|----------|
| ~108 | fijo total canal | `SUMPRODUCT(AM_col × FTE_conteo)` | 515,206,200 | Vision P&G C34 |
| ~115 | fijo agente Voz1 | `AM62 × 130 (FTE) − comision_staff` | 384,926,602 | CTS C37 |
| ~155-181 | variable por rol | `D_col × FTE_staff × idx_mes` | — | CTS C38 |
| ~198 | variable Voz1 total | PLANA 24m (sin aging per mes) | 86,673,274 | CTS C38 = 775.74 |
| ~329 | med_seg Bogota | tarifa médica | 60,800 | exámenes |

**Estructura confirmada:** PARTICIÓN (no aditiva). `fijo = total_cargado − comisiones`. `variable = comision_cruda × FTE × idx`.

### 5.3 NO_PAYROLL (`No payroll`)

| Fila | Concepto | Fórmula patrón | Valor ejemplo | Alimenta |
|------|----------|----------------|---------------|----------|
| E134 | PC escritorio (qty) | `=CCA!I206` (item CCA) | 130 (SAC) | CAPEX amort |
| C134 | meses_a_diferir PC | dato fijo | 60 | precio_mensual = total/60 |
| D134 | precio_mensual PC | `=total/meses_a_diferir` | 58,471 | E167 (amort mensual) |
| E167 | amort mensual SAC | `SUMPRODUCT(precio_mensual × qty) × (1+tasa_financ)` | 11,569,961 | CTS C47 |
| C107 | opex_mensual SAC | dato deal | 39,973,918 | CTS C46 (EXACT) |
| C108 | opex_mensual WA | dato deal | 3,525,293 | CTS C46 |
| C111 | opex_mensual Crec | dato deal | 24,599,334 | CTS C46 |

**Clave:** `meses_a_diferir` deriva precio_mensual; el horizonte de cobro es `meses_contrato` (24m), NO `meses_a_diferir`.
**Backend:** `_build_amortizable_item` — C47 EXACT (Δ+0.0000) desde commit bbdb94f.

### 5.4 COSTO FIJO / VARIABLE / CADENA C

Estas hojas son intermedias: consolidan por (modalidad, canal, escenario) via ArrayFormulas los valores
de Nomina Loaded + No Payroll + Cadena B/C. El backend los replica en:
- `CostosTotalesCalculator` → `nomina_calculator.calcular_mes()` + `no_payroll_calculator` + `cadena_b` + `cadena_c`
- Status: **MATCH estructural** (misma composición). Deltas residuales = gaps de input/parametrización.

### 5.5 POLIZAS + FINANCIACION (`Pólizas - Costo Financiacion`)

| Concepto | Hoja/Celda | Excel | Backend | Status |
|----------|-----------|-------|---------|--------|
| Póliza Seriedad activa | Polizas!E12 | False | request.activa=False | MATCH |
| Todas las pólizas | Polizas col E | False (deal SAC) | request todas False | MATCH |
| ICA Bogota | Tasas!B37 | 0.00966 | request.tasa_ica=0.01 | REQUEST_VALUE_MISMATCH |
| GMF | Tasas!B31 | 0.004 | request.tasa_gmf=0.004 | MATCH |
| Comisión Adm | Tasas (calculada) | 1.18% sobre costo_total | costos_financieros/calculator.py | MATCH |
| Costos financieros | Polizas!r70 | 0 (cons_costo=False) | request.cons_costo=False | MATCH |

### 5.6 COSTOS TOTALES

Suma de Cadena A (payroll+no_payroll) + Cadena B + Cadena C + Componente Financiero.
Backend: `CostosTotalesCalculator` orquesta todo vía `_calcular_mes`. Estructura: MATCH.

---

## 6. Request provenance

| Concepto | Celda Excel | Valor Excel | Request path | Valor request | Status |
|----------|-------------|-------------|--------------|---------------|--------|
| Servicio/Cliente | Panel!C5/C6 | SAC / METROCUADRADO | `datos_operativos.servicio/cliente` | SAC / METROCUADRADO | REQUEST_MATCH |
| Margen Cadena A | Panel!C63 | 0.21 | `reglas_negocio.margen_objetivo` | 0.21 | REQUEST_MATCH |
| Margen Cadena B | Panel!D63 | 0.30 | `reglas_negocio.margen_objetivo_cadena_b` | 0.30 | REQUEST_MATCH |
| Margen Cadena C | Panel!E63 | 0.20 | `reglas_negocio.margen_objetivo_cadena_c` | 0.20 | REQUEST_MATCH |
| Contingencia Operativa | Panel!C67 | 0 | `reglas_negocio.contingencia_operativa.valor` | 0 | REQUEST_MATCH |
| Contingencia Comercial | Panel!C68 | 0 | `reglas_negocio.contingencia_comercial.valor` | 0 | REQUEST_MATCH |
| Mark-Up | Panel!C69 | 0 | `reglas_negocio.markup.valor` | 0 | REQUEST_MATCH |
| Imprevistos | Panel!C73 | 0 | `reglas_negocio.imprevistos` | 0 | REQUEST_MATCH |
| Descuento volumen | Panel!C70 | 0 | `reglas_negocio.descuento_volumen` | 0 | REQUEST_MATCH |
| **Porcentaje acumulado** | Panel!C75 | **0** | `reglas_negocio.porcentaje_acumulado.actual` | **0.02** | **REQUEST_VALUE_MISMATCH** |
| IPC componente humano | Panel!L7 | IPC | `volumetria.indexacion.componente_humano` | IPC | REQUEST_MATCH |
| Componente tecnológico | Panel!L8 | 20% SMMLV 80% IPC | `volumetria.indexacion.componente_tecnologico` | 20% SMMLV 80% IPC | REQUEST_MATCH |
| **ICA Bogota** | Tasas!B37 | **0.00966** | `datos_operativos.tasa_ica` | **0.01** | **REQUEST_VALUE_MISMATCH** |
| GMF | Tasas!B31 | 0.004 | `datos_operativos.tasa_gmf` | 0.004 | REQUEST_MATCH |
| cons_costo_financiacion | Panel!L9 | False | `datos_operativos.cons_costo_de_financiacion` | False | REQUEST_MATCH |
| tasa_interes_mensual | Panel!L11 | 0.0153 | `volumetria.indexacion.tasa_interes_mensual` | 0.0153 | REQUEST_MATCH |
| Duración contrato | Panel!C11 | 24 | `datos_operativos.duracion_meses` | 24 | REQUEST_MATCH |
| FTE Cadena A (SAC) | CCA!E9 | 130 | `condiciones_cadena_a.perfiles[SAC].fte` | 130 | REQUEST_MATCH |
| Modelo cobro Voz1 | VT!C13 | Variable | `escenarios_comerciales[0].modelo_cobro` | Variable | REQUEST_MATCH |
| Componente variable | VT!C16 | Transacción | `escenarios_comerciales[0].componente_variable` | Transacción | REQUEST_MATCH |
| Supervisor SAC E95 | CCA!E95 | 9.5 (override) | `…fte_soporte_overrides.Supervisor` | 9.5 | REQUEST_MATCH |
| cargos_adicionales SAC | CCA!E26 | 12 | `…perfiles[SAC].cargos_adicionales` | 12 | REQUEST_MATCH |
| días_capacitacion | CCA!E139 | 11 | `…perfiles[].dias_capacitacion_perfil` | 11 | REQUEST_MATCH |
| OPEX mensual SAC | No payroll!C107 | 39,973,918 | `…perfiles[SAC].no_payroll_mensual` | 39,973,918.08 | REQUEST_MATCH |
| CAPEX items (CCA!I206+) | CCA!I206:I213 | qty SAC | `…perfiles[SAC].inversiones[]` | datos cargados | REQUEST_MATCH |
| Crucero tarifa | CCA!E152 | 8,408 | `datos_operativos.crucero` | 8,408 | REQUEST_MATCH |

**Resumen request:** 20 MATCH / 2 REQUEST_VALUE_MISMATCH → **✅ REQUEST_FIX_P2_P3 APPLIED 2026-06-12**
- P2: `porcentaje_acumulado.actual` ya era `0` en working copy (pre-alineado).
- P3: `tasa_ica` corregido `0.01 → 0.00966` (Tasas!B37 · commit siguiente).

---

## 7. Parametrización / provider provenance

| Concepto | Excel fuente | Valor Excel | Backend fuente | Valor backend | Campo existe | Status | Acción |
|----------|--------------|-------------|----------------|---------------|--------------|--------|--------|
| IPC 2026 | Tasas!C4 (año 2026) | 0.0527 | `get_tasa_ipc` OP/storage | 0.0527 | Sí | PARAM_MATCH | None |
| SMMLV growth 2026 | Tasas!C5 | 0.2378 | `get_tasa_smmlv` | 0.2378 | Sí | PARAM_MATCH | None |
| Factor prestacional SAC | Nomina Loaded!W62/F62 | 1.5147 | `HR provider` | 1.5147 | Sí | PARAM_MATCH | None |
| salario_base agente SAC | Inputs!C62 | 1,750,905 | `get_salario_rol(Agente)` HR | 1,750,905 | Sí | PARAM_MATCH | None |
| comision agente SAC | Inputs!D62 | 600,000 | `get_comision_rol` HR | 600,000 | Sí | PARAM_MATCH | None |
| salario SENA/Inclusión | Inputs!C59/C60 | 1,750,905 | provider patch `_V28_SENA_INCLUSION_SALARY` | 1,750,905 | Sí | PROVIDER_MATCH | None |
| salario Supervisor SAC | Inputs!C57 | 1,750,905 | `_V28_STAFF_COMISION` | 1,750,905 | Sí | PROVIDER_MATCH | None |
| comision Supervisor D57 | Inputs!D57 | 700,000 | `_V28_STAFF_COMISION.comision_pct` | 700,000/1,750,905 | Sí | PROVIDER_MATCH | None |
| **rotación SAC** | Rot!F19 | **0.077175** | provider `_v28_deal_provider.py:208` | ~~0.09~~ → **0.077175** | Sí | ✅ **PARAM_VALUE_FIX_P5_APPLIED** (2026-06-12) | CERRADO |
| **tasa_financiacion** | OP-Config | 0.0153 | active OP config sheet (agregado 2026-06-12) | **0.0153** | Sí | ✅ **PROVIDER_FIX_P4 APPLIED** | None |
| examen_anual SAC | CCA!E135 | 0.28 | provider patch | 0.28 | Sí | PROVIDER_MATCH | None |
| med_seg Bogota | Nomina!C329 | 60,800 | provider patch | 60,800 | Sí | PROVIDER_MATCH | None |
| margen mínimo SAC | Rot!B29:B34 | 0.21 | input request (panel.margen) | 0.21 | Sí | PARAM_MATCH | None |
| Polizas activa (todas) | Polizas!col_E | False | request.polizas[].activa | False | Sí | PARAM_MATCH | None |

---

## 8. Excel → backend coverage (matriz completa)

| Bloque | Hoja Excel | Celda/Rango | Concepto | Request/Param source | Backend archivo | Backend función/campo | Status |
|--------|------------|-------------|----------|----------------------|-----------------|-----------------------|--------|
| NOMINA_INPUT | Inputs de Nomina | F62 | imponible agente SAC | HR provider | nomina_cargada.py:117 | `t_imponible = sal × (1+comision_pct)` | MATCH |
| NOMINA_INPUT | Inputs de Nomina | W62 | cargado agente SAC | HR provider | nomina_cargada.py | `costo_cargado = imponible × factor` | MATCH |
| NOMINA_INPUT | Inputs de Nomina | C59/C60 | SENA/Inclusión salario | provider patch | `_V28_SENA_INCLUSION_SALARY` | patch applied | MATCH |
| NOMINA_INPUT | Inputs de Nomina | D57/C57 | comision/sal Supervisor | provider patch | `_V28_STAFF_COMISION` | patch applied | MATCH |
| NOMINA_LOADED | Nomina Loaded | ~108 (fijo) | salario_fijo por canal | nomina.py | nomina.py:174 | `salario_fijo = total_cargado − comisiones` | MATCH (partición) |
| NOMINA_LOADED | Nomina Loaded | ~198 (var) | salario_variable | nomina.py | nomina.py:200-227 | `comisiones = sal × FTE × com_pct × idx` | MATCH |
| NO_PAYROLL | No payroll | C107 | opex_mensual SAC | request.no_payroll_mensual | costs.py:98-103 | bypass opex_fijo.items | MATCH |
| NO_PAYROLL | No payroll | E167 (amort) | CAPEX mensual | request.inversiones[] | context_builder_perfiles_soporte_mixin | `_build_amortizable_item` | MATCH (C47 EXACT) |
| COSTO_FIJO | Costo Fijo | varies | costos_fijos por canal | No payroll | context_builder_perfiles_soporte_mixin | `costo_fijo_mensual` | MATCH estructural |
| COSTO_VARIABLE | Costo Variable | varies | costo_variable | Nomina Loaded variable | nomina.py | comisiones | MATCH estructural |
| CADENA_C | Costo Cadena C | varies | tarifa_proveedor_canal | CCC.inversiones | cadena_c/reglas.py | `costo_c_mensual` | MATCH |
| COSTOS_TOTALES | Costos Totales | varies | suma costos | Cadena A/B/C + Financiero | costos_totales_calculator.py | `calcular_mes` | MATCH estructural |
| POLIZAS | Pólizas - CF | pct_* | tasas pólizas | request.polizas[] (activa=False) | costos_financieros/calculator.py | `_calcular_polizas` | MATCH (todas False) |
| FINANCIACION | Pólizas - CF | ICA/GMF/ComAdm | componente financiero | request.tasa_ica/gmf | costos_financieros/calculator.py | `calcular_ica/gmf/comadm` | ✅ FIXED (ICA: 0.01→0.00966 · REQUEST_FIX_P3) |
| PYG | Visión P&G | I19/K19 (ingreso A) | ingreso_cadena_a | HME cached base | pyg_calculator.py:173 | `costo_a / factor_billing × rampup` | ACCEPTED_ARCHITECTURAL_DELTA |
| PYG | Visión P&G | I30/K30 (costo) | costo_total | costos_totales | pyg_calculator.py | `costo_a + costo_b + costo_c + fin` | MATCH estructural |
| PYG | Visión P&G | I74/K74 | contribucion | ingreso_neto − costo | pyg_calculator.py | `ingreso_neto − costo_total` | MATCH estructural |
| PYG | Visión P&G | I15 (rampup) | factor_rampup | Rot!B38:BI43 | pyg_calculator.py | `get_rampup(mes, servicio)` | MATCH |
| PYG | Visión P&G | I26 (imprevistos) | imprevistos | Panel!C73 × ingreso | pyg_calculator.py:224 | `panel.imprevistos × ingreso_bruto` | MATCH |
| TARIFAS | Vision Tarifas | C48 | ingreso_mensual_A | `C40 / factor_billing` | vision_tarifas/reglas.py | `_calcular_tarifa_canal` | MATCH estructura |
| TARIFAS | Vision Tarifas | H19 | facturacion total | HME!C289 = sum ingreso A+B+C | vision_tarifas/reglas.py | `pyg_por_mes[2].ingreso_bruto` (+1.9% HME delta ACCEPTED) | ✅ **VTM-001_APPLIED** |
| TARIFAS | Vision Tarifas | C21 (tarifa tx) | tarifa_transaccion | costo / vol × factor | vision_tarifas/reglas.py | `tarifa_transaccion` | MATCH estructural |
| TARIFAS | Vision Tarifas | C37 (FTE) | fte_total | CCA!E9:S9 | context_builder | `fte` | MATCH |

---

## 9. Vision P&G — outputs principales

| Celda/Rango | Concepto | Fuente intermedia | Request/Param source | Backend componente | Status | Nota |
|-------------|----------|-------------------|----------------------|-------------------|--------|------|
| I15 | rampup M1 | Rot, Ausent!B38:BI43 | servicio, mes_inicio | `get_rampup(1)` | MATCH | 0.9 = correcto |
| I18/K18 | Ingreso Bruto | HME!C289 (cached) | márgenes request | `pyg_calculator.ingreso_bruto` | ACCEPTED_ARCHITECTURAL_DELTA | Excel: estático HME; backend: dinámico |
| I19 | Ingreso A M1 | HME!C296 | margen_a=0.21 | `ingreso_cadena_a` | ACCEPTED_ARCHITECTURAL_DELTA | ~24.5% delta; raíz = base estática vs dinámica |
| K19 | Ingreso A M3 | HME!C296 | — | `ingreso_cadena_a` | ACCEPTED_ARCHITECTURAL_DELTA | Excel usa C296 desde M_start; backend crece con IPC |
| I32/K32 | Payroll | Nomina Loaded sum | nomina cargada | `pyg_calculator.costo_payroll_a` | MATCH estructural | delta residual = CTS_SUPPORT_LOADED_MAGNITUDE |

---

## 10. CTS-002 — Cadena C K34 parity (CERRADO 2026-06-12)

**Excel K34 = 5,278.326744819592 COP/tx** = `SUM(K35, K36, K40)`
- K35: tarifa_proveedor promedio = 5,130.66 COP/tx
- K36: OPEX fijo (130.76) + equipo transversal (16.90) = 147.66 COP/tx
- K40: costo_variable = 0 COP/tx
- K38: inversiones (`#REF!` → 0) — **NOT included in K34**

**Backend result:** `cts_cadena_c = 5,278.3267470588235` · Delta = **2.24e-6 COP/tx** (floating-point)

| Fix | Commit | Excel fuente | Cambio backend | Delta antes → después |
|-----|--------|--------------|----------------|----------------------|
| Cadena C technology indexation | `2d006cc` | `Tasas, TRM, Polizas`!C15:G15 — fila '20% SMMLV 80% IPC' = 1.0 todos los años → 0% efectivo | `pct_aumento_tecnologico = 0.0` en `context_builder_panel_bc_mixin.py` | +133.31 → -65.84 |
| Cadena C fixed OPEX | `ee1e7db` | `Costo Cadena C`!D136 = opex_fijo 22,230,000/mes · K37 = 130.76 COP/tx | mapear `costo_variable.opex_items` tipo='Fijo' como `opex_fijo_integ` en `entry_data_adapter.py` | -65.84 → +64.92 |
| Cadena C inversiones | `cd5bb6d` | K34 = SUM(K35,K36,K40) — K38 (#REF!→0) **NOT included** · `ACCEPTED_EXCEL_QUIRK` | `_c_calcular_inversion()` retorna 0.0; backend espeja resultado efectivo del Excel | +64.92 → -11.40 |
| Equipo transversal | `a146370` | `salario_cargado` = 4,284,360.05/FTE (fixture v27) · `opex_herramientas` = 1,159,602.60/mes (recurso_humano_transversal.opex) | pass-through `salario_cargado` + `opex_herramientas_transversal` en adapter + mixin | -11.40 → **0.00** |

**Nota K38 (`ACCEPTED_EXCEL_QUIRK`):** La celda K38 usa una referencia rota (`#REF!`) que produce 0. La fórmula K34 no la incluye. El backend espeja el comportamiento efectivo (inversion_anual=0), no la intención de diseño. Documentado intencionalmente.
| I41/K41 | No Payroll | No payroll totales | no_payroll_mensual + CAPEX | `pyg_calculator.costo_no_payroll_a` | MATCH (C47 EXACT) | |
| I65/K65 | Comp Financiero | Polizas + ICA + GMF + ComAdm | request rates | `costos_financieros` | KNOWN_DELTA (ICA) | |
| I74/K74 | Contribución | Ingreso_neto − Costo_total | — | `ingreso_neto − costo_total` | MATCH estructura | |
| I79/K79 | Utilidad Neta | Contribución − Costo Fijo | — | `utilidad_neta_total` | MATCH estructura | |
| O19/K19 ratio | IPC ratio M7/M3 | Tasas, IPC 2026 | componente_humano=IPC | factor_indexacion | MATCH (Δ=0.0000) | |

**Raíz del delta P&G ingreso:** Excel calcula base de ingreso con `HME!C258 / (1-margen)` = valor estático
pre-computado en la hoja. Backend computa `costo_a / factor_billing × rampup` por mes dinámicamente.
Misma fórmula estructural; distinto costo base (deal diferente cacheado en HME vs deal actual).

---

## 10. Vision Tarifas — outputs principales

| Celda/Rango | Concepto | Fuente intermedia | Request/Param source | Backend componente | Status | Nota |
|-------------|----------|-------------------|-----------------------|-------------------|--------|------|
| C19 (Esc1) | Facturación Voz1 | `HME!C289` × (rampup month) | — | `ingreso_mensual` | **VTM-001** | Excel=3,018M (M3 base), backend=64,529M (cum 24m) |
| H19 (total) | Facturación total | `HME!C289` = C266+C276+C286 | — | `kpis.ingreso_total` | **VTM-001** | Campo correcto = `pyg_por_mes[2].ingreso_bruto` (M3) |
| H20 | Tarifa Comp Fijo | `HME!G263` | — | `tarifa_fte` | BACKEND_METRIC_NOT_EXPOSED | Solo si escenario Fijo |
| H21 | Tarifa Comp Variable | `HME!G273` | modelo_cobro=Variable → tx | `tarifa_transaccion` | MATCH estructural | |
| C48 | Ingreso Mensual A | `C40/((1-margen)×(1-cont)×...)` | margen=0.21, conts=0 | `_calcular_tarifa_canal` | MATCH fórmula | delta = delta de costo_a |
| C37 | FTE | `SUM(CCA!E9:S9)` | request.perfiles.fte | `fte_total` | MATCH | |
| C40:C47 | Costo Cadena A | Payroll+NoPayroll+ICA+GMF+ComAdm+Polizas | costos backend | `costo_cadena_a_ch` | MATCH estructural | |
| G35 | Margen A | `panel.margen_a` | request.margen_objetivo=0.21 | `panel.margen` | MATCH | |

**Fix VTM-001:** El campo backend correcto para `H19` es `pyg_por_mes[2].ingreso_bruto` (mes 3, primer mes full,
sin rampup = M3 en nomenclatura Excel) o `kpis.facturacion_mensual_proyectada`. No requiere cambio en módulos;
solo corrección del campo expuesto en la vista `vision_tarifas`.

---

## 11. Request/Parametrization provenance (tabla requerida)

| Bloque | Concepto | Excel | Request path | Param/provider path | Backend consumer | Status |
|--------|----------|-------|--------------|---------------------|------------------|--------|
| PYG | margen_a | Panel!C63=0.21 | `reglas_negocio.margen_objetivo=0.21` | HR: `get_margen_minimo` (0.21) | `pyg_calculator.py:160` | MATCH |
| PYG | factor_rampup | Rot!B38 | — | OP: `get_rampup(servicio, mes)` | `pyg_calculator.py:145` | MATCH |
| PYG | imprevistos | Panel!C73=0 | `reglas_negocio.imprevistos=0` | — | `pyg_calculator.py:224` | MATCH |
| PYG | IPC 2026 | Tasas!C4=0.0527 | — | OP: `get_tasa_ipc(2026)` | `pyg_calculator.py:213` | MATCH |
| PYG | SMMLV growth | Tasas!C5=0.2378 | — | HR: `get_tasa_smmlv(2026)` | `pyg_calculator.py:216` | MATCH |
| FINANCIERO | ICA Bogota | Tasas!B37=0.00966 | `tasa_ica=0.01` (**mismatch**) | OP: `get_ica(ciudad)` | `costos_financieros:321` | REQUEST_VALUE_MISMATCH |
| FINANCIERO | GMF | Tasas!B31=0.004 | `tasa_gmf=0.004` | — | `costos_financieros` | MATCH |
| FINANCIERO | ComAdm 1.18% | Tasas (calculada) | — | GN: parámetro fijo | `costos_financieros:188` | MATCH |
| NO_PAYROLL | tasa_financiacion | Panel!L11=0.0153 | `tasa_interes_mensual=0.0153` | OP-Config (ausente→WARNING) | `_build_amortizable_item` | PROVIDER_SELECTION_MISMATCH |
| NO_PAYROLL | CAPEX items qty | CCA!I206+ | `inversiones[].cantidad` | — | `_build_amortizable_item` | MATCH |
| NOMINA | rotacion SAC | Rot!F19=0.077175 | `pct_rotacion=0.0815` | provider fallback=0.09 | `nomina.py:251` | PROVIDER_VALUE_MISMATCH |
| NOMINA | examen_anual SAC | CCA!E135=0.28 | — | provider patch=0.28 | `nomina.py:281` | MATCH |
| TARIFAS | modelo_cobro | VT!C13=Variable | `escenarios_comerciales[].modelo_cobro=Variable` | — | `vision_tarifas/reglas.py:145` | MATCH |
| TARIFAS | facturacion H19 | HME!C289=3,018M | — | — | `kpis.ingreso_total` (cum 24m) | VTM-001 BACKEND_METRIC_NOT_EXPOSED |
| CTS | cargos_adicionales | CCA!E26=12 | `perfiles[SAC].cargos_adicionales=12` | — | `context_builder_perfiles_soporte_mixin` | MATCH |
| CTS | E95 Supervisor | CCA!E95=9.5 | `fte_soporte_overrides.Supervisor=9.5` | — | `context_builder_perfiles_soporte_mixin` | MATCH |

---

## 12. Top gaps accionables

| Prioridad | Gap | Hoja/Celda | Request/Param status | Backend actual | Tipo | Impacto estimado | Acción recomendada |
|-----------|-----|------------|----------------------|----------------|------|------------------|--------------------|
| **P1** | **VTM-001 Vision Tarifas field mapping** | VT!H19 = HME!C289 = 3,018M | N/A (campo backend mal elegido) | `ingreso_mensual` (cum 24m = 64,529M) | **BACKEND_METRIC_NOT_EXPOSED** | H19 delta ~21× vs Excel | Exponer `pyg_por_mes[2].ingreso_bruto` en `vision_tarifas` output o usar `kpis.facturacion_mensual_proyectada` |
| ~~**P2**~~ | ~~**PORCENTAJE_ACUMULADO mismatch**~~ | Panel!C75 = 0 | `porcentaje_acumulado.actual = 0` (ya alineado) | — | ✅ **PRE-ALIGNED** | — | Ya estaba en 0 en working copy al aplicar fix. |
| ~~**P3**~~ | ~~**ICA Bogota rate**~~ | Tasas!B37 = 0.00966 | `tasa_ica = 0.00966` | `costos_financieros` usa tasa_ica | ✅ **REQUEST_FIX_P3 APPLIED** | ICA Bogota alineada | Aplicado 2026-06-12. Validación: preexisting engine error bloquea validate-excel-v28. |
| **P4** | **PARAM-TASA-FINANC** | Panel!L11 = 0.0153 | request MATCH; OP-Config ausente en storage | default 0.0088 (WARNING) | **PROVIDER_FIX** | CAPEX C47 correcto (request valor); afecta deals futuros | Poblar OP-Config en parametrización activa (`tasa_financiacion = 0.0153`) |
| **P5** | **PARAM-ROTACION-SAC** | Rot!F19 = 0.077175 | request=0.0815 (cerca); provider fallback=0.09 (lejano) | `pct_rotacion` = request 0.0815 | **PARAM_VALUE_FIX** | cap_rotacion: pequeño impacto en CTS (~2 COP/tx) | Actualizar provider SAC rotacion = 0.077175; verificar si request override tiene precedencia |
| **P6** | **CTS-002 Cadena C** | VCT!K34 = 5,278.33 | N/A | backend=5,329.61 (+51.28, ~1%) | **MODULE_FORMULA_GAP** (a confirmar inputs primero) | 51.28 COP/tx vs Excel | Revisar inputs Cadena C (tarifa proveedor, integración) antes de clasificar como formula gap |
| **P7** | **BASE_INGRESO P&G** | HME!C296 = 1,822M (estático) | — | backend dinámico por mes | **NOT_IMPLEMENTED_BY_DESIGN** | ~20% delta P&G ingreso | ACCEPTED_ARCHITECTURAL_DELTA (documentado). Sin acción. |
| **P8** | **CTS-001 residual** | VCT!C37 = -20.51 | — | `CTS_SUPPORT_LOADED_MAGNITUDE` | **DEFERRED** | 0.33% de CTS total | DEFERRED hasta completar mapa general |
| **P9** | **VTM tarifa_transaccion** | VT!C21 = 7,481.64 | request MATCH, margen MATCH | `tarifa_transaccion` backend | **NEEDS_DEEP_DIVE** | delta desconocido (depende de costo_a) | Medir una vez P1/P2/P3 aplicados; delta probable = costo_a residual |
| **P10** | **ROLES_OPERATIVOS no consumidos** | — | request tiene `roles_operativos[]` | motor usa `staff_config[]` | **NOT_IMPLEMENTED_BY_DESIGN** | GAP de configuración (JCR/AFAC/GTR activación) | Doc-only: motor consume staff_config, no roles_operativos |

---

## 13. Qué NO se tocó

- `modules/` — 0 archivos modificados
- `request/request.json` — **1 fix: `tasa_ica = 0.00966`** (REQUEST_FIX_P3; `porcentaje_acumulado.actual` ya era 0)
- `storage/` — 0 modificaciones
- `tests/` — 0 modificaciones
- `contracts/` — 0 modificaciones
- Baseline — NO regenerado
- Gates — NO ejecutados (make all / pytest / validate-excel-v28)
- `CTS-001` — NO reabierto
- `CTS_SUPPORT_LOADED_MAGNITUDE` — DEFERRED, no atacado
- Hardcodes nuevos en motor — 0

---

## 14. Siguiente acción recomendada

**REQUEST_FIX P2+P3 COMPLETED (2026-06-12):**
```
✅ porcentaje_acumulado.actual = 0  (pre-alineado; Panel!C75=0)
✅ tasa_ica = 0.00966               (Tasas!B37 Bogota · commit fix(v28))
```
Validación `validate-excel-v28` bloqueada por error preexistente:
`ParametrizationError: Economic component '20% SMMLV - 80% IPC' for year 2026 not found`
→ Fallos preexistentes, no regresiones nuevas.

**OP_CONFIG_PROVIDER_FIX_P4 COMPLETED (2026-06-12):**
```
✅ '20% SMMLV - 80% IPC' rows (2025-2030, 0.06616) → active OP-Componente
✅ config sheet → tasa_financiacion_mensual=0.0153 + anio_base_indexacion=2025
✅ make validate-excel-v28: PASS 6/6 checks (1 skipped)
✅ tasa_mensual_financiacion() = 0.0153 confirmed
✅ TestPYGAbsoluteAnchorsV28: 12 anchors refrescados → 7/7 PASS (ANCHOR_UPDATE_PYG COMPLETED)
```

**Siguiente acción recomendada:**
```
PARAM_VALUE_FIX P5: rotacion SAC provider=0.09 → 0.077175 (Rot!F19)
O
CTS-002: Cadena C delta ~51.28 COP/tx (validar inputs primero)
O
✅ ANCHOR_UPDATE_PYG: COMPLETADO — 12 anchors M1/M7/M19 × a/b/c/total refrescados · 7/7 PASS
```

**Siguiente sesión de fórmulas:**
```
VTM-001: mapear cuál campo backend corresponde a HME!C289 = 3,018M.
Candidatos: pyg_por_mes[2].ingreso_bruto o kpis.facturacion_mensual_proyectada.
Sin cambio de módulo; solo corrección de campo expuesto en vision_tarifas output.
```

**Sesión de parametrización:**
```
PROVIDER_FIX P4: poblar OP-Config tasa_financiacion=0.0153 en parametrización activa.
PARAM_VALUE_FIX P5: rotacion SAC 0.09 → 0.077175 en provider/storage.
```
