# SEMANTIC F3 — Runtime Unification

**Branch:** `refactor/engine-v2`
**Date:** 2026-05-28
**Predecessor:** F2 (request model reconstruction)
**Successor:** F4 (financial layer)
**Excel source of truth:** `Nexa - Pricing - Simulador - V2-7.xlsx`

---

## 1. Executive summary — honest

| Métrica | Pre-F3 | Post-F3 | Δ |
|---|---:|---:|---:|
| Oracle PASS / FAIL (`tests/parity/test_excel_oracle_v2_7_real.py`) | 6 / 33 | **6 / 33** | 0 |
| Suite default | 893 / 33 fail / 25 skip | **896 / 33 / 24** | +3 pass (new mutation tests) |
| Críticos (baselines+contracts+lineage+versioning+certification) | 237 PASS | **237 PASS** | = |
| Mutation tests detectados | **2 / 4** | **4 / 5** (1 nuevo añadido + 2 nuevos passed) | +2 detectados |
| `ProfitabilityCalculator.calcular_ingreso_desde_costo` exercised | NO (SKIP) | **SÍ (PASS)** | runtime unificado |
| `PayrollCalculator.calcular_factor_aumento` exercised | (no test) | **SÍ (PASS)** | nuevo cubierto |
| Calculators con fórmulas dup-runtime resueltos | 0 | **2** (`pyg.py`, `vision_tarifas.py` ingreso path) | unificación parcial |
| Oracle H32 Payroll A drift | 14.39% | **14.39%** (sin cambio) | refactor sin mover paridad, root cause F3-DEFERRED |

**Verdict honesto.** F3 eliminó la divergencia dual-runtime para la cascada
`ingreso = costo / factor_billing × rampup` — el path real ahora ejerce
`domain/profitability/calculators.py`. La mutación que en W17 fue marcada
SKIP (porque domain estaba aislado) ahora se DETECTA. Adicionalmente, el
runtime de `factor_aumento` y `factor_margenes` también está cubierto por
mutation tests F3, dando 4/5 detecciones (el SKIP residual es de
`aplicar_rampup`, gap de **request** no de dominio).

**El target conservador "≥10/41 oracle"** NO se alcanzó porque H32
14.39% no es el calculator (formula `costo_empresa` ya está en
`domain/services/nomina_cargada.py` con drift 0.0000% verificado celda a
celda). El drift residual proviene de la **composición** de perfiles
mensuales y del `factor_indexacion(6)` — F3-DEFERRED a sub-wave dedicado.

---

## 2. Mutation baseline & post-F3

### 2.1 Pre-F3 (W17 baseline reaffirmed)

```
test_mutation_factor_billing_changes_ingreso          PASS
test_mutation_aplicar_rampup_changes_output           SKIP (request V2-7 rampup=0)
test_mutation_ingreso_desde_costo_detected            SKIP ← hallazgo crítico
test_oracle_suite_detects_factor_billing_mutation     PASS
```

Resumen pre-F3: 2/4 detectadas, 1/4 expone dual-runtime (calculators/ usaba
fórmula directa, domain/ aislado), 1/4 expone gap de request.

### 2.2 Post-F3

```
test_mutation_factor_billing_changes_ingreso          PASS
test_mutation_aplicar_rampup_changes_output           SKIP (gap de request, no domain)
test_mutation_ingreso_desde_costo_detected            PASS  ← fijado por F3
test_mutation_factor_aumento_changes_payroll          PASS  ← nuevo F3
test_mutation_factor_margenes_changes_ingreso         PASS  ← nuevo F3
test_oracle_suite_detects_factor_billing_mutation     PASS
```

**5 PASS / 1 SKIP de 6 tests.** Los 4 fórmulas que el contrato F3 declaró
ejercidas (`factor_billing`, `ingreso_desde_costo`, `factor_aumento`,
`factor_margenes`) son ahora detectables. El SKIP de `aplicar_rampup` es
un gap del **request canónico V2-7** (rampup base = 0 en M1-M5 antes del
ramp; F6 mapping wave lo cubrirá).

---

## 3. Auditoría fórmula `costo_empresa` (H32 root cause)

### 3.1 Excel V2-7 — fórmula real `Nomina Loaded` + `Inputs de Nomina!W39`

Excel cell `Inputs de Nomina!W39` (C. Empresa de Inbound 25):

```
W39 = M39 + P39 + U39 + V39
    = (T.Haberes + Salud + Pensión + ARL_staff)        # seg_social
    + (Caja + ICBF+Sena)                                # parafiscales
    + (Cesantías + Primas + Int.Cesantía + Vacaciones)  # prestaciones
    + Dotaciones

Componentes (Inbound 25, salario_base=1750905, comision_pct=0.10):
  T.Imponible = C39 + D39 = 1750905 + 122563.35    = 1873468.35
  Aux         = C5 = 249095        (porque T.Imponible < 2 × SMMLV)
  T.Haberes   = F39 + G39          = 2122563.35
  Salud       = 0                  (Ley 1819, F<10×SMMLV)
  Pensión     = (H39-G39)*0.12     = 224816.20
  ARL_staff   = (H39-G39)*0.00522  = 9779.50
  Caja        = (H39-G39)*0.04     = 74938.73
  ICBF+Sena   = 0                  (Ley 1819)
  Cesantías   = H39*0.0833         = 176809.53
  Primas     = H39*0.0833         = 176809.53
  Int.Ces.   = Cesantías*0.12     = 21217.14
  Vacaciones = (H39-G39)*0.0417   = 78123.63
  Dotaciones = C8 = 15375

  W39 = 2,900,432.62
```

### 3.2 Backend — fórmula real `domain/services/nomina_cargada.py::calcular`

Verificación directa con los mismos inputs (1750905, 0.10) + parametrización
de Excel:

```
Backend NominaCargadaService.calcular(1750905.0, 0.10) = 2,900,432.6183
Excel  W39                                              = 2,900,432.62
Drift                                                   = -0.0000%
```

**El cálculo `costo_empresa` per-perfil ya tiene paridad cell-by-cell 0.00%
con Excel.** La fórmula NO es la causa del drift H32.

### 3.3 ¿Dónde está el drift H32 14.39%?

Excel H32 (`Visión P&G!H32 = 138.6M`) es `SUMPRODUCT('Nomina Loaded'!I93:I112 * ("Activado"))`,
o sea la SUMA del salario_fijo por canal (Voz + WhatsApp + Outbound) sin
añadir staff a esa fila — porque el staff está ya implícito en cómo Excel
distribuye costo en `Nomina Loaded`. Los componentes detallados (comisiones,
capacitación, exámenes, seguridad, crucero) suman a través de H34..H40 para
dar el total H32 = 138.6M.

Backend `payroll_a M6 = 158.5M`. Diferencia: **+19.9M** vs Excel.

Desglose por componente (backend, M6):

| Componente | Backend | Pct |
|---|---:|---:|
| Salario fijo | 152,374,196 | 96.1% |
| Comisiones | 5,432,877 | 3.4% |
| Cap_inicial | 0 | 0% |
| Cap_rotación | 0 | 0% |
| Exámenes | 713,041 | 0.45% |
| Seguridad | 0 | 0% |
| **TOTAL** | **158,520,114** | 100% |

El drift está en **Salario fijo**: backend 152.4M vs Excel 131.5M (Excel
I93+I97 en `Nomina Loaded`). Dos causas estructurales:

1. **Factor de indexación** — Backend aplica `factor_indexacion(6) = 1.10818`
   (componente `pct_aumento_salarial = 0.10818, mes_aplicacion = 1`). Excel
   en M6 aplica factor ≈ 1.134 (`I93 / (2900433 × 25) = 82218712 / 72510815 = 1.1339`).
   Diferencia: backend NO replica el cálculo de "Aumento Componente Humano"
   con la lógica exacta de Excel (`80% SMMLV 20% IPC` + mes_aumento = 6).
2. **Composición de perfiles staff** — Backend materializa 43 perfiles
   (Voz + WhatsApp + 22 staff × 2 canales). Excel `Nomina Loaded` I93:I112
   solo agrupa por canal — la atribución de staff por canal en Excel puede
   excluir o atribuir distinto a perfiles SENA/Inclusión (cuyo cálculo usa
   `calcular_aprendiz` con 75% SMMLV y reglas especiales). Backend usa la
   misma `calcular(...)` para SENA, lo que sobre-estima.

**Conclusión auditoría 3.3.** El drift H32 NO se cierra modificando
`calculators/nomina.py` ni `domain/services/nomina_cargada.py`. Requiere:
- Recalcular `factor_indexacion(6)` siguiendo la fórmula Excel
  `Aumento Componente Humano` (80% SMMLV + 20% IPC) con mes_aumento = 6
  (no 1).
- Rutear roles SENA/Inclusión por `NominaCargadaService.calcular_aprendiz`
  (no por `calcular`).
- Verificar el agrupamiento Excel `Nomina Loaded I93:I112` para entender
  qué staff suma a qué canal.

Estos tres son cambios **estructurales** que cruzan `context_builder.py` +
`calculators/nomina.py` + `domain/services/nomina_cargada.py`. **Out of F3 scope
limitado por tiempo y restricción "no toques fórmulas para hacer pasar tests".**
Documentado como **F3.B sub-wave** dedicado al closure de H32.

---

## 4. Refactor aplicado en F3

### 4.1 `calculators/pyg.py` — líneas 119-131

**Antes:**
```python
factor_b_a = (1 - m_a) * (1 - op_cont) * (1 - com_cont) * (1 - markup) * (1 + descuento)
factor_b_b = (1 - m_b) * ...  # idem
factor_b_c = (1 - m_c) * ...  # idem
ingreso_cadena_a = (costos_operativos.costo_a / factor_b_a) * factor_rampup if factor_b_a > 0 else 0.0
# ... idem b, c
```

**Después:**
```python
from nexa_engine.domain.profitability.calculators import ProfitabilityCalculator
factor_b_a = ProfitabilityCalculator.calcular_factor_billing(m_a, op_cont, com_cont, markup, descuento)
factor_b_b = ProfitabilityCalculator.calcular_factor_billing(m_b, op_cont, com_cont, markup, descuento)
factor_b_c = ProfitabilityCalculator.calcular_factor_billing(m_c, op_cont, com_cont, markup, descuento)
ingreso_cadena_a = ProfitabilityCalculator.calcular_ingreso_desde_costo(costos_operativos.costo_a, factor_b_a, factor_rampup)
ingreso_cadena_b = ProfitabilityCalculator.calcular_ingreso_desde_costo(costos_operativos.costo_b, factor_b_b, factor_rampup)
ingreso_cadena_c = ProfitabilityCalculator.calcular_ingreso_desde_costo(costos_operativos.costo_c, factor_b_c, factor_rampup)
```

**Efecto.** Mutación `calcular_ingreso_desde_costo * 1.07` ahora se observa
en `vision_tarifas.ingreso_mensual`. Domain runtime confirmado.

### 4.2 `calculators/vision_tarifas.py` — líneas 186 y 249

**Antes:**
```python
# línea 186
ingreso_total = costo_total / factor if factor > 0 else 0.0
# línea 249 (por canal)
ingreso = costo_ch / factor if factor > 0 else 0.0
```

**Después:**
```python
from nexa_engine.domain.profitability.calculators import ProfitabilityCalculator
# línea 186 (factor_rampup=1.0 — ya promediado mensualmente)
ingreso_total = ProfitabilityCalculator.calcular_ingreso_desde_costo(costo_total, factor, 1.0)
# línea 249 (idem por canal)
ingreso = ProfitabilityCalculator.calcular_ingreso_desde_costo(costo_ch, factor, 1.0)
```

### 4.3 `tests/parity/test_mutation_detection.py` — +2 mutation tests F3

- `test_mutation_factor_aumento_changes_payroll` — mutación + 10% en
  `PayrollCalculator.calcular_factor_aumento` debe alterar `payroll_a`.
  Validado: PASS.
- `test_mutation_factor_margenes_changes_ingreso` — mutación + 5% en
  `ProfitabilityCalculator.calcular_factor_margenes` debe alterar
  `ingreso`. Validado: PASS.

---

## 5. Estado del LEGACY_ACTIVO (post-F3)

| Calculator | Estado | Razón |
|---|---|---|
| `calculators/utils.py` | SHIM_REAL (ya verificado en W9, confirmado por mutation F3) | factor_aumento, factor_margenes, rampup, polizas, factor_periodo todos delegan |
| `calculators/pyg.py` | SHIM_REAL parcial (post-F3 en ingreso path) | Otros cálculos (contribución, costo_total) son orquestación, no fórmulas |
| `calculators/vision_tarifas.py` | SHIM_REAL parcial (post-F3 en ingreso path) | `_costo_op_canal_decomposed`, `_factor_billing` ya usan utils; resto orquesta |
| `calculators/nomina.py` | LEGACY_ACTIVO | `_calcular_perfil` y subrutinas viven solo en este file (F3-DEFERRED a F3.B) |
| `calculators/cost_to_serve.py` | LEGACY_ACTIVO | CTS ponderado complejo, F3.B |
| `calculators/costos_financieros.py` | LEGACY_ACTIVO | F4 lo refactoriza (GMF/ICA/admin) |
| `calculators/cadena_b.py` | LEGACY_ACTIVO (usa shim factor_aumento) | Volumen × tarifa, sin equivalente domain |
| `calculators/cadena_c.py` | LEGACY_ACTIVO | F5 |
| `calculators/no_payroll.py` | LEGACY_ACTIVO | Sin paridad target inmediato |
| `calculators/riesgo.py` | LEGACY_ACTIVO | Sin impacto paridad |

---

## 6. Restricciones respetadas

| Restricción F3 | Cumplido |
|---|:---:|
| NO modificar fórmulas para hacer pasar tests | ✅ Solo se delegó a `domain/` con misma fórmula |
| NO duplicar fórmula entre `domain/` y `calculators/` | ✅ `ingreso = costo / factor_billing` ahora vive en un solo punto |
| NO mantener calculators legacy con su propia lógica donde existe domain equivalente | ✅ En las dos áreas con domain equivalente (`profitability`, `payroll factor_aumento`) se eliminó duplicación |
| NO ajustar oracle | ✅ Oracle JSON intacto |
| NO marcar fails como xfail/skip | ✅ Fails siguen visibles (33) |
| Críticos no regresan | ✅ 237 PASS pre-F3 = 237 PASS post-F3 |
| Mutation testing detecta ≥4/5 | ✅ 4/5 detectadas + 1 SKIP por gap de request |

---

## 7. Oracle pre/post F3

```
Pre-F3 (W19 + F2): 6 PASS / 33 FAIL
Post-F3:           6 PASS / 33 FAIL
```

**Sin movimiento.** Es el resultado correcto y honesto: F3 unificó el
runtime (precondición para todas las siguientes fases) sin tocar fórmulas.
Los drifts restantes pertenecen a:

| Drift | Causa | Owner |
|---|---|---|
| H32 14.39% (Payroll A) | factor_indexacion(M6) + composición SENA/Inclusión | **F3.B** (sub-wave) |
| H67 85.62% (GMF) | GMF base divergente (cost vs cost+income) | **F4** |
| H66 86.50% (ICA) | ICA base divergente | **F4** |
| C40 87.58%, C72 99.44% (anualizado) | Interpretación mensual vs anual | **F6** mapping |
| C60 100% (Cadena C) | HITL no modelado | **F5** |

---

## 8. Archivos modificados

| Archivo | Cambio | LOC delta |
|---|---|---:|
| `calculators/pyg.py` | Delegar factor_b_{a,b,c} e ingreso_cadena_{a,b,c} a `ProfitabilityCalculator` | -3 / +9 |
| `calculators/vision_tarifas.py` | Delegar `ingreso = costo/factor` (dos sitios) a `ProfitabilityCalculator.calcular_ingreso_desde_costo` | -2 / +8 |
| `tests/parity/test_mutation_detection.py` | +2 mutation tests (factor_aumento, factor_margenes) | +58 |
| `docs/v27/F3_RUNTIME_INVENTORY.md` | Nuevo — inventario dual runtime | +110 |
| `docs/v27/F3_REPORT.md` | Este documento | +280 |

**Storage / parametrización: 0 archivos modificados** (F3 no toca datos).
**Oracle / fixtures: 0 archivos modificados** (F3 no toca verdad).

---

## 9. Tests críticos — verificación

```
tests/baselines           12 passed
tests/contracts           49 passed
tests/lineage             32 passed
tests/versioning          26 passed
tests/certification      118 passed
────────────────────────
Total                    237 passed, 0 failed
```

Default suite: **896 passed / 33 failed / 24 skipped / 450 deselected /
1 xfailed**. Mejora neta vs pre-F3: **+3 pass** (los 2 nuevos mutation tests
F3 + el que pasó de SKIP a PASS).

---

## 10. F3-DEFERRED (work plan para sub-wave F3.B)

1. **H32 14.39% root cause closure**:
   - Auditar fórmula Excel `Aumento Componente Humano` (`Panel!L6`) y replicar
     en backend (probable: el factor_aumento aplica desde mes_aumento=6 ó 13,
     no desde 1).
   - Ruteo SENA/Inclusión: usar `NominaCargadaService.calcular_aprendiz` en
     lugar de `calcular` para estos perfiles.
   - Verificar agrupamiento por canal de `Nomina Loaded I93:I112` para
     entender atribución correcta de staff support por canal.
2. **Refactor `_calcular_perfil`** a `domain/payroll/calculators.py`:
   - Extraer firmas puras: `calcular_salario_fijo`, `calcular_capacitacion_inicial`,
     `calcular_capacitacion_rotacion`, `calcular_examenes`, `calcular_seguridad`.
   - `calculators/nomina.py` se vuelve shim de orquestación que hidrata
     argumentos primitivos y suma.
3. **Refactor `cost_to_serve.py`** — CTS ponderado a `domain/profitability/calculators.py`.

---

## 11. Verdict F3

**Runtime unificado parcialmente.** Las fórmulas de profitability
(`factor_billing`, `ingreso_desde_costo`, `factor_margenes`) y payroll
(`factor_aumento`) ahora tienen un único hogar canónico en `domain/` y son
ejercidas por el runtime real. Mutation testing eleva la cobertura de
detección de 2/4 a 4/5 mutaciones críticas.

**El objetivo H32 → <1%** NO se alcanzó, y es honesto reportar que el root
cause documentado en F2 ("salario_cargado formula divergence") fue
**refutado** en F3: la fórmula `costo_empresa` tiene paridad 0.0000% con
Excel W39 verificada celda a celda. El drift es estructural en la
composición mensual (factor de indexación + atribución SENA/Inclusión) y
queda asignado a F3.B sub-wave.

F3 entrega **la precondición necesaria** para F4 (la financial layer ahora
puede modificarse en `domain/` con confianza de que el runtime la ejerce)
sin comprometer paridad ni introducir hardcodes.

---

## 12. Single execution path — scorecard final

| Fórmula | Single path | Evidencia |
|---|---|---|
| `factor_billing` | ✅ | mutation PASS |
| `ingreso_desde_costo` | ✅ | mutation PASS (era SKIP) |
| `factor_aumento` | ✅ | mutation PASS (nuevo) |
| `factor_margenes` | ✅ | mutation PASS (nuevo) |
| `aplicar_rampup` | ⚠ runtime exercise no observable (request V2-7 rampup canónico = 0) | SKIP — gap request, F6 |
| `salario_cargado` | ✅ | verificado 0.0000% drift contra Excel W39 |
| `_calcular_perfil` (composición mensual) | ❌ NO unificado (vive en `calculators/`) | F3.B sub-wave |
| `cost_to_serve_ponderado` | ❌ NO unificado | F3.B |
| `costos_financieros` (GMF/ICA/admin) | ❌ NO unificado | F4 |

**Veredict.** Single execution path **parcialmente logrado**: las fórmulas
core del path income/billing están unificadas; las fórmulas de composición
(payroll detail, CTS, financiera) están identificadas y planificadas pero
no refactorizadas en F3 — F3.B/F4/F5 los cubren respectivamente.
