# CTS-001 — Auditoría estructural del residual (V2-8)

Fecha: 2026-06-11 · Modo: **READ-ONLY diagnóstico** (sin fix de motor, sin re-baseline).
Commit base: `70ecd54` (CTS_INPUT_DEAL_MATCH PARTIAL_BEST).
Patch aplicado: `CTS_SENA_INCLUSION_PROVIDER_PATCH` — ver Fase 2b.
Fuente canónica: `excel/Nexa - Pricing - Simulador - V2-8.xlsx` (sha `48d51055…`).
Provider: `tests/refactor/_v28_deal_provider.py` (active HR + W-override 20 roles staff).
Denominador: Panel!W31 = 221,000 tx/mes. Deal: SAC / METROCUADRADO / Grupo Aval, 24m.

## Estado

```
backend CTS-001 = 6,143.809068 COP/tx  (post SENA/Incl provider patch)
excel   CTS-001 = 6,224.575126 COP/tx  (Vision CTS!C34)
delta           =    -80.766058 COP/tx  (1.298%)   →  MAX_DELTA(0.000001) NO cumplido
```

Pre-patch: CTS = 6,109.624708 COP/tx (1.847%).
Patch aplicado: `CTS_SENA_INCLUSION_PROVIDER_PATCH` (+34.18 COP/tx cerrado, 1.847% → 1.298%).

**Veredicto: `CTS_RESIDUAL_STRUCTURAL_AUDIT_COMPLETED` / `CTS-001_PARTIAL_BEST_IMPROVED`**
NO se declara `CTS-001_FULL_MATCH`.

> **Update 2026-06-11 (sesión `SUPPORT_FTE_MODULE_FIX`):** el frente dominante de soporte
> (Supervisor / numerador FTE) se reclasificó de `REQUIRES_MODULE_SCOPE` →
> **`SUPPORT_FTE_BLOCKED_MISSING_SOURCE`**. La fórmula Excel suma `cargos_adicionales`
> (CCA!E26/E30/E34 = 12 / 0 / 7.3846) al numerador, pero ese insumo **no existe** en el contrato
> de entrada del backend, y SAC Supervisor (E95=9.5) es un **override manual literal**, no la fórmula.
> El fix no es aplicable sin crear campo público nuevo (prohibido) ni hardcodear (prohibido).
> CTS-001 permanece en `PARTIAL_BEST_IMPROVED` (delta sin cerrar). Detalle: `support_fte_input_decision_v28.md` §8-§10.

> **Update 2026-06-11 (sesión `CTS_INPUT_DECISION_CHECKPOINT`):** auditados los frentes request-scope.
> **Crucero** = `CTS_CRUCERO_FIXABLE_WITH_REQUEST` (flag `incluye_crucero` ya en contrato; +10.63).
> **OPEX** = `OPEX_NO_PAYROLL_FIXABLE_WITH_REQUEST` pero backend **+71.95 SOBRE** Excel → enmascara el
> déficit FTE (corregirlo en aislamiento empeora CTS-001). **Decisión:** agotar request-scope antes de
> abrir contrato `cargos_adicionales` → `CONTRACT_CHANGE_CARGOS_ADICIONALES_DEFERRED`.
> Detalle: `cts_001_decision_checkpoint_v28.md`.

---

## 1. Descomposición exacta del residual (verificada)

Split payroll/no-payroll contra anchors Excel `Vision Cost To Serve`:

| Bloque | Backend | Excel | Delta |
|---|---|---|---|
| **Payroll** (C35) | 5,261.906 | 5,462.356 | **-200.449** |
| **No-payroll** (C45) | 847.719 | 762.219 | **+85.499** |
| **CTS-001 total** (C34) | 6,109.625 | 6,224.575 | **-114.950** |

### 1a. Payroll −200.45 (desglose `desglose_a` vs Excel)

| Componente | Backend | Excel | Delta | Nota |
|---|---|---|---|---|
| nomina_loaded (C36) | 5,232.910 | 5,405.230 | **-172.320** | AGENTES match; SOPORTE -172.4 |
| examenes | **11.512** | 12.240 | **-0.730** | ✅ MEJORADO (0.016→11.512); residual = fte_examenes gap → ver `cts_exam_crucero_audit_v28.md` |
| crucero | 0.000 | 10.630 | **-10.630** | BLOCKED — `tarifa_crucero` en request.json (fuera de scope) |
| capacitacion_rotacion | 19.176 | 22.670 | -3.494 | menor |
| capacitacion_inicial | 9.804 | 11.590 | -1.786 | menor |

  - nomina_loaded AGENTES: backend **4,189.44** vs Excel **4,189.38** → **MATCH** (260 HC).
  - nomina_loaded SOPORTE: backend **1,043.47** vs Excel **1,215.85** → **-172.38** (todo el gap).

### 1b. No-payroll +85.50 (desglose vs Excel C46-C48) — **CORRIGE doc previo**

| Componente | Backend | Excel | Delta |
|---|---|---|---|
| OPEX Fijo (C46) | 380.090 | 308.138 | **+71.952** |
| Inversiones/CAPEX (C47) | 119.759 | 103.044 | **+16.715** |
| Costos Fijos x Estación (C48) | 347.869 | 351.037 | -3.168 |

> **Corrección:** el doc `cts_input_deal_match_v28.md` atribuía +119.72 a un "CAPEX
> month-1 spike". **Es falso.** Excel también amortiza CAPEX (C47=103.04 ≠ 0); el
> backend solo amortiza +16.72 de más. El verdadero gap dominante de no-payroll es
> **OPEX Fijo +71.95** (backend más alto que Excel), no el CAPEX.

---

## 2. Hallazgo trazable: base salarial SENA / Inclusión — APLICADO

| Concepto | Celda Excel | Valor Excel | Destino provider | Observación |
|---|---|---|---|---|
| Aprendiz SENA base | `Inputs de Nomina`!C59 | 1,750,905 | `_v28_deal_provider.py` `salario` | trazable, APLICADO |
| Inclusión base | `Inputs de Nomina`!C60 | 1,750,905 | `_v28_deal_provider.py` `salario` | trazable, APLICADO |
| Cargado SENA (W) | `Inputs de Nomina`!W59 | 2,494,099.29 | `calcular_aprendiz(1,750,905)` = 2,496,240.94 | residuo fórmula +0.086% |

- El motor (SENA/Inclusión) usa `calcular_aprendiz(get_salario_rol(rol))` — **NO** consulta
  `costo_empresa_override` (a diferencia de los 20 roles regulares y Especialista).
- **Fix aplicado** en `tests/refactor/_v28_deal_provider.py`: `_V28_SENA_INCLUSION_SALARY`
  diccionario + loop de patch + alias rows → CTS **6,109.62 → 6,143.81 (+34.18)**, delta **-80.77 (1.298%)**.
- Residual de fórmula tras parchar base: `calcular_aprendiz(1,750,905)` = 2,496,240.94 vs
  Excel W59 = 2,494,099.29 → **+0.086%** (factor backend 1.42569 vs Excel W/C 1.42446).

**Clasificación: `SENA_INPUT_MISMATCH` (FIXABLE_WITH_PROVIDER, +34.18 COP/tx)** + residuo
`SENA_FORMULA_MISMATCH` (~0.086%, requiere wiring de override o ajuste de fórmula → modules/).

---

## 3. Residual dominante: SOPORTE nomina_loaded −138 (tras fix SENA)

Tras el fix de base SENA/Incl (+34.18), queda −80.77 total; el componente dominante es
el soporte nomina_loaded (~-138 COP/tx). Evidencia:

- Los 20 roles regulares portan **exactamente** el AM (C.Empresa+Comisiones) de Excel vía
  `costo_empresa_override` (verificado: Director AM=32,816,427; Jefe Op=8,065,483; Sup=4,506,462).
  Por tanto el cargado/FTE **coincide** con Excel para esos 20.
- Backend payroll es **plano** en los 24 meses (sin variación de ramp) → ramp NO es la causa.
- **FTE soporte: backend 61.4452** vs Excel `Nomina Loaded`!"Visión por perfiles" ≈ **71.29**
  y "Visión por Canal" ≈ 76.25 → Excel tiene **~10 FTE de soporte MÁS**. A cargado medio de
  soporte (~3.75M/FTE) eso son ~167 COP/tx, consistente con el gap observado.

**Corrección a auditoría previa:** `cts_fte_headcount_audit_v28.md` afirmaba "FTE soporte 61.4
= MATCH Excel". **NO confirmado.** Los agregados de Excel (`Nomina Loaded` filas 232/253)
indican soporte ~71 FTE. El gap soporte NO es el "staff-variable" (ya cerrado por el
override AM), sino una **diferencia de dotación de soporte (FTE)**.

**Clasificación: `STAFFING_FTE_MISMATCH`** (subtipo INPUT_DEAL / parametrización de ratios o
fórmula de derivación de FTE soporte). **REQUIRES_FURTHER_FORENSICS**: la hoja `Nomina Loaded`
tiene layout multi-bloque (columnas escenario C/D/E + timeline mensual J:BK + partición
fijo/variable + sección FTE 229-262) que no permitió extraer el HC limpio por rol en esta
pasada. La extracción cruda dio valores imposibles (SENA HC=308), por lo que NO se reporta
como cifra firme; sí es firme el agregado ~71 vs 61.

---

## 4. Split fijo/variable (informativo — invariante al total)

| | Backend | Excel | Delta |
|---|---|---|---|
| salario_fijo (C37) | 4,738.76 | 4,629.49 | +109.27 |
| salario_variable (C38) | 494.15 | 775.74 | -281.59 |

El split difiere (backend pliega comisión en fijo: `salario_fijo = total_cargado − comisiones`),
pero es **INVARIANTE** al total `nomina_loaded` (documentado en
`cts_variable_split_attribution_v28.md`). NO es causa del residual de CTS-001.

---

## 5. No-payroll: clasificación

| Componente | Delta | Causa probable | Clasificación |
|---|---|---|---|
| OPEX Fijo | +71.95 | backend OPEX 380.09 > Excel 308.14; origen = `no_payroll_mensual` de perfiles (request.json) | `NO_PAYROLL_INPUT_MISMATCH` → BLOCKED (NO TOCAR request.json) |
| CAPEX/Inversiones | +16.72 | backend amortiza +16.72 de más (ambos amortizan) | `CAPEX_AVERAGING_MISMATCH` → REQUIRES_FORENSICS |
| Costos Fijos | -3.17 | menor | known_delta |

---

## 6. Matriz de decisión técnica

| Residual | Δ COP/tx | Causa | Fix sin modules | Requiere modules | Requiere provider/input | Riesgo | Estado |
|---|---|---|---|---|---|---|---|
| SENA/Incl base | +34.18 (**APLICADO**) | base 1,423,500 → 1,750,905 (C59/C60) | **SÍ** (`salario` en provider, trazable) ✅ | no | sí (provider) | bajo | `CTS_SENA_INCLUSION_PROVIDER_PATCH_APPLIED` |
| SENA/Incl fórmula | ~0.18 (0.086%) | `calcular_aprendiz` 1.4257 vs Excel 1.4245; override no consultado para SENA/Incl | no | **sí** (wiring override) | no | medio | `CTS_RESIDUAL_REQUIRES_MODULE_SCOPE` |
| Soporte FTE | ~-138 | Excel soporte ~71 FTE vs backend 61.4 (dotación) | parcial (si es ratio HR) | posible (si es fórmula FTE) | sí (ratios/staffing) | alto | `CTS_RESIDUAL_REQUIRES_MODULE_SCOPE` / forensics |
| examenes | -0.730 (**PARCIAL**) | costo_examen_medico 60,800 + pct_examen_anual 0.28 APLICADOS; residual fte_examenes | **SÍ** ✅ (provider patch) | no | sí (provider) | bajo | `CTS_EXAM_APPLIED` (parcial, -0.73 residual = fte gap) |
| crucero | -10.63 | tarifa_crucero en request.json Panel (fuera scope) | no | no | sí (request — NO TOCAR) | medio | `CTS_CRUCERO_REQUIRES_INPUT_SCOPE` BLOCKED |
| cap inicial/rot | -5.28 | menor | — | — | — | bajo | `CTS_RESIDUAL_KNOWN_DELTA` |
| No-payroll OPEX | +71.95 | request.json `no_payroll_mensual` > Excel | no (request) | no | sí (request — NO TOCAR) | medio | `CTS_RESIDUAL_BLOCKED_MISSING_SOURCE` |
| No-payroll CAPEX | +16.72 | amortización | parcial | posible | posible | medio | forensics |
| No-payroll CostosFijos | -3.17 | menor | — | — | — | bajo | `CTS_RESIDUAL_KNOWN_DELTA` |

### Resumen de fixability

- **Sin modules (provider/test, trazable):** SENA/Incl base → **+34.18** ✅ APLICADO (CTS 6,109.62 → 6,143.81, 1.847% → 1.298%).
- **Requiere modules/:** wiring de `costo_empresa_override` para SENA/Incl (cerraría a exacto);
  fórmula de derivación de FTE soporte; crucero (tarifa_crucero en request.json).
- **Requiere input/request (NO TOCAR):** OPEX Fijo no-payroll (+71.95); cargado de staff base.
- **known_delta:** cap inicial/rotación, costos fijos estación (residuos menores).

---

## 7. Conclusión

El residual CTS-001 (-80.77 post-patch) NO es un único bug. Composición actualizada:

```
Payroll   -166.27 = soporte FTE ~-138 (dotación) + SENA/Incl base ✅ CERRADO
                    + examenes -0.73 (parcial, ✅ MEJORADO 0.016→11.512) + crucero -10.63 (BLOCKED) + cap -5.28
No-payroll +85.50 = OPEX +71.95 (request) + CAPEX +16.72 + costos_fijos -3.17
Neto       -80.77  (1.298%)
```

Histórico de mejora:
```
Pre-INPUT_DEAL_MATCH:  5,992.50 (3.729%, delta -232.07)
Post-INPUT_DEAL_MATCH: 6,109.62 (1.847%, delta -114.95)  — all-staff W-override
Post-SENA_INCL_PATCH:  6,143.81 (1.298%, delta  -80.77)
Post-CTS_EXAM_PATCH:   6,155.30 (1.113%, delta  -69.27)  ← ESTADO ACTUAL
```

- **SENA/Incl base `+34.18` ✅ APLICADO** (provider, trazable Excel C59/C60).
- El gap dominante restante (**soporte FTE ~-138** y **OPEX +71.95**) exige **modules/** (fórmula FTE)
  o **request.json** (OPEX, staffing) — ambos fuera de scope.
- CTS-001 permanece **PARTIAL_BEST_IMPROVED** (1.298%), lejos de MAX_DELTA=0.000001.

No se modificó motor. No se regeneró baseline. Gates: PASS.

---

## 8. CORRECCIÓN (2026-06-11, post-6ce1eb7) — REFUTA §3 "soporte ~71 FTE"

La afirmación de §3 ("Excel soporte ≈ 71 FTE vs backend 61.4, gap dotación ~-138 COP/tx") es
**FALSA**. Extracción limpia del bloque FTE por rol de Excel (`Condiciones Cadena A`!E77:G100,
E/F/G = SAC/WhatsApp/Crecimiento):

```
Excel  soporte total = 59.5526 FTE   (excl. agentes 260 + validador 0)
Backend soporte total = 61.4452 FTE
delta = +1.8925 FTE   →  BACKEND TIENE MÁS, NO MENOS
```

El gap de COSTO soporte (-172 COP/tx) **no es conteo** sino **mezcla**: Excel concentra en
Supervisor (16.37 vs backend 13.0, **-3.37 FTE caro ≈ -68 COP/tx**) porque su numerador es
`(FTE_agentes + cargos_adicionales CCA!E26)/ratio`; backend usa `fte_agentes/ratio`. Backend
compensa el conteo activando GTR/JCR/AFAC (que Excel desactiva, C-flag=False) — roles baratos.

**Ratios coinciden** (no es ratio mismatch). **Reclasificación: `SUPPORT_FTE_FORMULA_BUG`
(REQUIRES_MODULE_SCOPE)**, no STAFFING_FTE_MISMATCH de dotación. Matriz completa y trazabilidad
por rol: `docs/refactor/support_fte_input_decision_v28.md`.

Crucero: corregido — `request.json datos_operativos.crucero=8408` (tarifa SÍ existe); backend=0
porque falta el flag `incluye_crucero` en perfiles. `CTS_CRUCERO_INPUT_DECISION_REQUIRED` (no BLOCKED).
