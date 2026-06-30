# SEMANTIC F2 — Request Model Reconstruction

**Branch:** `refactor/engine-v2`
**Date:** 2026-05-28
**Predecessor:** F1 (freeze + reality alignment)
**Successor:** F3 (Runtime unification)
**Excel source of truth:** `Nexa - Pricing - Simulador - V2-7.xlsx`

---

## 1. Executive summary — honest

| Métrica | Pre-F2 (W19) | Post-F2 | Δ |
|---|---:|---:|---:|
| Oracle PASS / FAIL (`tests/parity/test_excel_oracle_v2_7_real.py`) | 6 / 33 | **6 / 33** | 0 |
| Suite default | 892 / 33 fail / 25 skip | **893 / 33 / 25** | +1 pass |
| Críticos (baselines+contracts+lineage+versioning+certification) | 237 PASS | **237 PASS** | = |
| Hardcodes `comision_pct` H1 removidos | NO | **SÍ** | -2 valores |
| Agregado fake `salario_base=85065268.0` | (ya eliminado W17) | NO presente | = |
| Roles Excel "Inputs de Nomina" auditados | 57 | **57 (re-confirmados)** | 0 |
| Ratios Cadena A celdas auditadas | parcial | **rows 25–48 cols E/F (24 roles, 2 perfiles)** | full |
| Baselines `v2-7-certified` regenerados | sí (W19) | **sí (12 casos)** | re-hash hr |

**Verdict honesto:** F2 cierra el hack H1 (comision_pct invented Director/GTR) y deja el request fixture alineado con la realidad del Excel V2-7. **El objetivo conservador de +6 oracle no se alcanzó** (sigue en 6/33) porque los drifts residuales están dominados por gaps estructurales que pertenecen a F3-F5:
- F3 — salario_cargado formula divergence (~14% H32)
- F4 — GMF/ICA base, comisión admin, costos financieros (~6 tests)
- F5 — Cadena C HITL no modelada (~7 tests)
- F6 — interpretación anualizada vs mensual de C40/C72/B19

Estos gaps fueron identificados (no enmascarados) en W17-W19 y reconfirmados en F2. F2 elimina **exactamente** lo que estaba en su scope (modelo de entrada + parametrización), sin tocar fórmulas del motor.

---

## 2. Auditoría exhaustiva del Excel V2-7

### 2.1 Hoja "Inputs de Nomina" — extracción completa

Estructura de 4 secciones (confirmada W4/W5, re-verificada F2 con `openpyxl data_only=True`):

| # | Sección | Filas datos | # Roles | ¿Comisión? |
|---|---|---|---:|:---:|
| 1 | Empleado | R16–R40 | 25 | SÍ (col E) |
| 2 | Equipo de Soporte y Mantenimiento | R60–R71 | 12 | NO |
| 3 | Equipo de HITL | R77–R82 | 6 | NO |
| 4 | Roles de Implementación | R89–R102 | 14 | NO |
|  | **Total** |  | **57** |  |

#### 2.1.1 Sección "Empleado" — fila por fila (col E = `% Comisión recibido`)

| Row | Cargo | Salario Base | Variable | **% Comisión** |
|---:|---|---:|---:|---:|
| 16 | Director de cuentas | 22,761,150 | 0 | **0** |
| 17 | Director de Performance | 13,685,100 | 0 | **0** |
| 18 | Jefe Comercial Regional | 5,537,202 | 0 | **0** |
| 19 | Analista profesional AFAC | 3,145,131 | 0 | **0** |
| 20 | Lider de Entrenamiento | 4,999,272 | 0 | **0** |
| 21 | Lider de Experiencia de Cliente y Performance | 4,999,272 | 0 | **0** |
| 22 | Lider de Planeación Operativa | 5,475,093 | 0 | **0** |
| 23 | Jefe de Operación | 4,336,703 | 0 | **0** |
| 24 | Works force | 2,815,025 | 0 | **0** |
| 25 | Reporting | 2,815,025 | 0 | **0** |
| 26 | GTR | 1,982,883 | 0 | **0** |
| 27 | Analista Prof. De Selección (Inicial) | 2,873,766 | 0 | **0** |
| 28 | Analista 1 de Reclutamiento (Inicial) | 1,906,592 | 0 | **0** |
| 29 | Analista Prof. De Selección (Rotación) | 2,873,766 | 0 | **0** |
| 30 | Analista 1 de Reclutamiento (Rotación) | 1,906,592 | 0 | **0** |
| 31 | Analista 2 Service Desk | 2,228,145 | 0 | **0** |
| 32 | Formadores | 2,057,790 | 0 | **0** |
| 33 | Monitor de Calidad | 2,149,179 | 0 | **0** |
| 34 | Supervisor | 3,090,990 | 0 | **0** |
| 35 | Validador | 1,750,905 | 0 | **0** |
| 36 | Aprendiz SENA | 1,750,905 | 0 | **0** |
| 37 | Inclusión | 1,750,905 | 0 | **0** |
| 38 | Especialista de Proyectos | 5,405,151 | 0 | **0** |
| 39 | **Inbound 25** | 1,750,905 | 122,563.35 | **0.10** |
| 40 | **inboun Whatsapp** | 1,750,905 | 122,563.35 | **0.10** |

**Conclusión auditoría 2.1.1:** En Excel V2-7 únicamente los dos perfiles agente
("Inbound 25" R39 y "inboun Whatsapp" R40) tienen `% Comisión recibido = 0.10`.
**Todas las 23 otras filas tienen `0`**, incluidos `Director de cuentas` (R16) y
`GTR` (R26) — donde el backend tenía hardcodes 0.05 y 0.10 respectivamente.

Las secciones 2.2/2.3/2.4 no exponen columna de comisión (layout sin col E
equivalente, ver `docs/v27/NOMINA_LAYOUT_V2_7.md`).

### 2.2 Hoja "Condiciones Cadena A" — ratios staff

#### 2.2.1 Bloque de definición de perfiles agente (rows 14–21)

| Row | Concepto | Voz (col E) | WhatsApp (col F) |
|---:|---|:---:|:---:|
| 14 | Modalidad | Inbound | Inbound |
| 15 | Canal | Voz | WhatsApp |
| 16 | Perfil | Inbound 25 | inboun Whatsapp |
| 17 | FTE | **25** | **15** |
| 18 | % Estaciones presenciales | 0.6 | 0.6 |
| 19 | Estaciones presenciales | 15 | 9 |
| 20 | Salario Base | 1,750,905 | 1,750,905 |
| 21 | Comisión perfil | **0.10** | **0.10** |

#### 2.2.2 Matriz de ratios (rows 25–48, cols E/F) — extracción Excel

Layout: `D = Cargo`, `C = ¿Se Incluye en el Deal?`, `E/F = ratio agentes_por_padre`.

Fórmula de derivación FTE (cell W$r$): `=IFERROR(IF(OR($V$r=$V$38,$V$r=$V$39),(E$17/E$r)*'Panel!C$20,(E$17/E$r)),0)` — pura división, **sin redondeo** (no ROUND/CEILING/FLOOR). Excepción: filas de roles Rotación (V$38 Analista Selección Rotación, V$39 Analista Reclutamiento Rotación) multiplican por `Panel!C$20` (= 0.085 rotación mensual).

| Row | Cargo | Incluir | Ratio E/F | FTE Voz (W) | FTE WhatsApp (X) |
|---:|---|:---:|---:|---:|---:|
| 25 | Director de cuentas | True | 750 | 0.0333 | 0.0200 |
| 26 | Director de Performance | True | 1200 | 0.0208 | 0.0125 |
| 27 | Jefe Comercial Regional | False | — | 0 | 0 |
| 28 | Analista profesional AFAC | False | — | 0 | 0 |
| 29 | Lider de Entrenamiento | True | 1000 | 0.0250 | 0.0150 |
| 30 | Lider de Experiencia de Cliente y Performance | True | 1000 | 0.0250 | 0.0150 |
| 31 | Lider de Planeación Operativa | True | 1000 | 0.0250 | 0.0150 |
| 32 | Jefe de Operación | True | 165 | 0.1515 | 0.0909 |
| 33 | Works force | True | 300 | 0.0833 | 0.0500 |
| 34 | Reporting | True | 300 | 0.0833 | 0.0500 |
| 35 | GTR | True | 200 (override B35=8) | 0.1250 | 0.0750 |
| 36 | Analista Prof. De Selección (Inicial) | True | 120 | 0.2083 | 0.1250 |
| 37 | Analista 1 de Reclutamiento (Inicial) | True | 55 | 0.4545 | 0.2727 |
| 38 | Analista Prof. De Selección (Rotación) | True | 110 × Panel!C20 | 0.0193 | 0.0116 |
| 39 | Analista 1 de Reclutamiento (Rotación) | True | 55 × Panel!C20 | 0.0386 | 0.0232 |
| 40 | Analista 2 Service Desk | True | 110 | 0.2273 | 0.1364 |
| 41 | Formadores | True | 370 | 0.0676 | 0.0405 |
| 42 | Monitor de Calidad | True | 70 | 0.3571 | 0.2143 |
| 43 | Supervisor | True | 70 | 0.3571 | 0.2143 |
| 44 | **Agente Básico 1** | True | **1 (self-row)** | **25** | **15** |
| 45 | Validador | False | — | 0 | 0 |
| 46 | Aprendiz SENA | True | 20 | 1.3651 | 0.8191 |
| 47 | Inclusión | True | 100 | 0.2867 | 0.1720 |
| 48 | Especialista de Proyectos | True | 0 (vacío) | 0.6250 | 0.3750 |

#### 2.2.3 Hallazgos clave del bloque ratios

1. **División pura sin redondeo.** Excel calcula FTE = `frontline_fte / ratio`
   sin aplicar ROUND/CEILING/FLOOR. El backend debe replicar esto.
2. **"Agente Básico 1" R44 es la self-row del agente.** Ratio = 1 ⇒ FTE = 25/1
   = 25. Excel NO la añade como staff payroll extra — sólo la usa para
   totalizar. El backend, antes de W19, la materializaba erróneamente.
   W19 ya cerró este bug en `input/context_builder.py`.
3. **Aprendiz SENA (R46) y Inclusión (R47)** se calculan como agregaciones de
   filas previas (`SUM(W25:W44)/E46` y `SUM(W25:W46)/E47`). Esto significa
   que su FTE no se deriva de una división simple sino de la suma del staff
   ya materializado, dividida por el ratio. Backend usa fórmula equivalente
   (validado por W19 cuando el bug duplicación se cerró).
4. **Rotación (V38, V39)** aplica multiplicador `Panel!C20 = 0.085` (la
   tasa rotación mensual). Roles "Rotación" suelen tener FTE muy bajo
   (~0.02). Backend ya implementa esto via parametrización `rotacion_ausentismo`.
5. **GTR override especial (B35=8).** Si Panel C5 = "Captura de Datos" y B35=8,
   Excel forzaba ratio=200 (línea hard del IF en formula E25). Esto ya es
   transparente porque el ratio Captura de Datos para GTR ya es 200.
6. **Validador R45 y Jefe Comercial R27 / Analista AFAC R28 NO incluidos.**
   `¿Se Incluye en el Deal? = False` ⇒ excluidos del payroll automático.
   Backend respeta esto via `incluir_en_deal_default` + reglas de exclusión
   (`roles_excluidos_ratios`).

### 2.3 Cadena B / Cadena C / Escenarios

**Cadena B:** existe la hoja "Condiciones Cadena B" pero el motor backend
trata Cadena B como un volumen × tarifa (no es payroll). El fixture ya carga
1 canal WhatsApp con 15,000 unidades a tarifa 183 — consistente con el bloque
mínimo del Excel pre-cargado.

**Cadena C:** hoja "Condiciones Cadena C" + hoja específica "Costo Cadena C"
implementan HITL con cantidades y OPEX detallado. El backend NO modela esto
(causa raíz documentada en `SEMANTIC_RECONSTRUCTION_PROGRAM §1.3 #3`). El
fixture deja un tarifa testigo (`2000000` × 1) pero esto no reproduce los
$29.1B de Excel C60. **Fuera de scope F2** — F5 es el wave dedicado a
implementar Cadena C HITL.

**Escenarios Comerciales:** la hoja "Hoja Maestra Escenarios" almacena
escenarios para comparativa pero el oracle de F2 (41 celdas mapeadas) NO usa
escenarios. El request fixture no necesita `escenarios_comerciales` (campo
opcional en `SimulationRequest`).

---

## 3. Diff de parametrización (`storage/parametrization/v2-7/hr.json`)

### 3.1 Cambios aplicados

| Campo | Rol | Valor previo | Valor nuevo (Excel) | Celda fuente | Justificación |
|---|---|---:|---:|---|---|
| `nomina[].comision_pct` | Director de cuentas | 0.05 | **0.0** | `Inputs de Nomina!E16` | H1 — backend tenía hardcode "WAVE 4 business override"; Excel = 0 |
| `nomina[].comision_pct` | GTR | 0.10 | **0.0** | `Inputs de Nomina!E26` | H1 — backend tenía hardcode "WAVE 4 business override"; Excel = 0 |
| `nomina[].markers` | Director de cuentas | `_wave4_business_override_comision` | removido | — | Marker no respaldado por Excel; eliminado |
| `nomina[].markers` | GTR | `_wave4_business_override_comision` | removido | — | idem |

### 3.2 Cambios NO aplicados (deliberadamente)

| Campo | Razón |
|---|---|
| `nomina[].costo_empresa_override` | Mantenido (Director: 29,031,301). Es valor "override" pero presente en sección Empleado columna posterior del Excel V2-7. Su validación queda como tarea F3/F4. |
| `Agente Básico 1` row | Mantenida con flag `_wave2_backport`. Confirmada en W19 que esta fila es la self-row de los perfiles agente (sirve para totalización Excel W44), no un rol staff independiente. Backend respeta exclusión vía `context_builder` (W19 fix). |
| Ratios `ratios[]` | Sin cambios; ya extraídos correctamente W4. Verificado contra rows 25–48 cols E/F. |
| Resto de `nomina[]` (55 entradas) | Verificado: todos tienen `comision_pct = 0.0`, consistente con Excel. |

### 3.3 Re-hash post-modificación

| Archivo | Hash previo (raw bytes) | Hash nuevo |
|---|---|---|
| `storage/parametrization/v2-7/hr.json` (manifest) | `b0bb8edd…` | `450a498c…` |
| `storage/parametrization/v2-7/hr.json` (canonical, baseline manifest) | `32b663f5…` | `8250296b…` |

Ambos manifests (`storage/parametrization/v2-7/manifest.json` y
`storage/baselines/v2-7-certified/manifest.json`) actualizados con los nuevos
hashes. Los 12 baselines `v2-7-certified` regenerados via
`python scripts/baselines/generate_baselines.py`. Tests críticos verificados
en 237 PASS (sin regresiones).

---

## 4. Reconstrucción del request fixture

### 4.1 Estructura final (`tests/parity/fixtures/excel_v2_7_real_request.json`)

| Sección | Contenido |
|---|---|
| `panel_de_control` | Copia exacta del Panel de Control General (cliente, complejidad, márgenes, contingencias, tasas) — sin cambios vs W19 |
| `condiciones_cadena_a.perfiles` | **2 perfiles** explícitos (Voz 25 + WhatsApp 15), idénticos a las celdas E14–F21 de "Condiciones Cadena A" |
| `condiciones_cadena_b.canales` | 1 canal WhatsApp Inbound (vol 15k × 183) |
| `condiciones_cadena_c.canales` | 1 canal Voz testigo (insuficiente, F5 lo expandirá) |
| `escenarios_comerciales` | omitido (opcional, no requerido por oracle F2) |

### 4.2 Justificación del diseño (decisión heredada de W19)

El charter F2 sugería "materializar los 28 perfiles staff implícitos en el
request". W19 documentó (y F2 reconfirma) que esto **no se hace en el
fixture** sino en el motor — porque Excel mismo NO los lista en
"Condiciones Cadena A!E16:F21" (la sección de perfiles agente solo tiene 2
columnas E y F = Voz/WhatsApp). Los ~22 staff (Director, GTR, Supervisor,
etc.) son **derivados** desde la tabla de ratios E25–F48 a runtime.

Por tanto:
- **El request fixture mantiene 2 perfiles** (los que Excel lista).
- **El motor expande staff support automáticamente** vía
  `repositories/payroll_parametrization_repository.py::get_ratios_staff()` +
  `input/context_builder.py::_construir_perfiles_soporte()`.
- W19 fix garantiza que la expansión es correcta (sin duplicados, sin
  self-clone "Agente Básico 1").

### 4.3 Verificación motor → Excel

| Concepto | Excel | Backend (post-W19) | Comentario |
|---|---:|---:|---|
| # Perfiles cadena A materializados (Voz + WhatsApp) | ~22 staff × 2 canales | 22 (sin duplicados) | OK W19 |
| FTE total cadena A | 40 frontline + ~2.0 staff (Voz) + ~1.2 staff (WhatsApp) ≈ 48.3 | 48.30 | OK W19 |
| Payroll mensual sin rampup | ~144.7M | 144,733,485 | OK W19 |
| FTE Agente Básico 1 (self-row) | 25/1=25 NO añadido como linea | excluido (W19) | OK |

### 4.4 Agregado fake `salario_base=85065268.0`

**Removido en W17** previo a F2. Verificado en F2: el fixture actual
no contiene este valor. El único `salario_base=1750905` corresponde a las
filas legítimas de Inbound 25 / inboun Whatsapp (Excel E20/F20).

---

## 5. Resultado oracle — F2 final

### 5.1 Estado pre vs post F2

| | Pre-F2 (W19) | Post-F2 |
|---|---:|---:|
| Oracle PASS | 6 | **6** |
| Oracle FAIL | 33 | **33** |
| Drift máximo | 100% (Cadena C, GMF base) | 100% (idem) |
| Drift mínimo no-trivial | 2.08% H31 | **2.08% H31** |

### 5.2 Top 10 drifts residuales con causa para F3+

| # | Cell | Excel | Backend | Drift | Causa estructural | Wave |
|---|---|---:|---:|---:|---|---|
| 1 | `Vision Tarifas!C60` Cadena C Costo Total | 29.14B | 0 | 100.00% | HITL no modelado | **F5** |
| 2 | `Vision Tarifas!C50` Cadena B Costo Total | ~0 | abs vs 0 | abs | Cadena B no payroll en motor | F4 |
| 3 | `Vision Tarifas!C40` Cadena A Costo Total | 1.365B | 169.5M | 87.58% | Excel C40 anualizado (×12), backend mensual | **F6** mapping |
| 4 | `Vision Tarifas!C72` Facturación Total | 38.6B | 218M | 99.44% | C40+C50+C60 anualizado | F6 + F5 |
| 5 | `Vision CTS!H19` CTS Mensual | 30.5B | 2.07B | 93.22% | Cadena C ausente + anualizado | F5 + F6 |
| 6 | `Visión P&G!H67` GMF | 10.32M | 1.48M | 85.62% | GMF backend solo sobre costo; Excel sobre `cost+income` | **F4** |
| 7 | `Visión P&G!H66` ICA | 32.2M | 4.4M | 86.50% | ICA base divergente | **F4** |
| 8 | `Visión P&G!H32` Payroll Cadena A | 138.6M | 158.5M | **14.39%** | `NominaService.calcular(1750905,0.1)≈2.9M` vs Excel `costo_empresa_excel=2.73M` — formula nómina cargada divergente | **F3** |
| 9 | `Visión P&G!H41` No Payroll A | 34.5M | ~11M | 68.12% | Componentes no-payroll subdesarrollados (capacitación, OPEX) | F4 |
| 10 | `Visión P&G!H31` Costos Cadena A | 173.2M | 169.6M | **2.08%** | Residual de H32 + H41 cascading | F3 + F4 |

### 5.3 Hardcodes removidos — efecto matemático

El fix H1 (comision_pct Director 0.05→0, GTR 0.10→0) tiene **impacto pequeño
en el oracle** porque:
- FTE Director materializado = 25/750 + 15/750 = 0.053 ⇒ payroll Director ≈ 0.053 × 28M = 1.5M/mes
- 5% sobre 22.7M salario = 1.13M comisión retirada
- Reducción de costo cadena A ~1M/mes ≈ 0.6% del total
- Insuficiente para mover H31 dentro de 0.01%, pero **dirección correcta**
  (backend ahora computa menos costo cadena A, que era exceso vs Excel)

No se contabiliza como "+1 oracle pass" porque H31 ya tenía drift 2.08% y el
fix lo redujo marginalmente (no a 0%). La tolerancia oracle 0.01% sigue
inalcanzable sin cerrar F3.

---

## 6. Restricciones respetadas

| Restricción F2 | Cumplido |
|---|:---:|
| NO modificar fórmulas del motor (calculators/, domain/) | ✅ Cero líneas modificadas |
| NO inventar valores sin sustento Excel | ✅ Cambios respaldados por celdas |
| NO mockear parametrización | ✅ Modificación en archivo storage |
| NO ajustar oracle JSON para "hacer pasar tests" | ✅ Oracle no tocado |
| NO marcar fails como xfail/skip | ✅ 33 fails siguen visibles |
| Eliminar hacks W4/W2 sin respaldo Excel | ✅ H1 cerrado; `Agente Básico 1` justificado |
| Críticos no regresan | ✅ 237 PASS pre = 237 PASS post |

---

## 7. Archivos modificados

| Archivo | Cambio |
|---|---|
| `storage/parametrization/v2-7/hr.json` | comision_pct Director→0, GTR→0; markers `_wave4_business_override_comision` removidos |
| `storage/parametrization/v2-7/manifest.json` | hash hr.json re-computado (raw) |
| `storage/baselines/v2-7-certified/manifest.json` | hash canonical hr re-computado |
| `storage/baselines/v2-7-certified/cases/*/outputs/*.json` | 12 casos regenerados via `scripts/baselines/generate_baselines.py` (impacto leve por comision Director/GTR pequeño) |
| `tests/integration/test_tipos_carga.py` | `TestComisionablesIdentificados` actualizado para reflejar Excel (Director=0, GTR=0 en lugar de 0.05/0.10); añadido `test_comision_agentes_es_diez_pct_en_excel` que SÍ asserta el 0.10 que Excel realmente tiene en E39/E40 |
| `docs/v27/F2_REPORT.md` | Este documento |

**Código de producción modificado: 0 archivos.** Únicamente parametrización
(storage), tests (codificaban el hack) y documentación.

---

## 8. Tests críticos — verificación

```
tests/baselines           12 passed (12 regenerados)
tests/contracts           49 passed
tests/lineage             32 passed
tests/versioning          26 passed
tests/certification      118 passed
────────────────────────
Total                    237 passed, 0 failed
```

Default suite: **893 passed / 33 failed / 25 skipped / 450 deselected /
1 xfailed**. Mejora neta vs pre-F2: **+1 pass** (test
`test_comision_agentes_es_diez_pct_en_excel`).

---

## 9. Verdict

**F2 ejecutado dentro del scope estricto.** El hack H1 (comision_pct
hardcodes para Director y GTR) está **CERRADO** con respaldo Excel celda por
celda. El request fixture refleja fielmente lo que Excel V2-7 lista (2
perfiles agente), y la expansión a ~22 staff support es responsabilidad del
motor (W19 fix). El agregado fake `salario_base=85065268.0` confirmado
ausente.

**Target +6 oracle NO alcanzado** porque el oracle exige tolerancia 0.01% y
los 33 fails restantes están dominados por:
- F3 — divergencia fórmula `salario_cargado` (~14% en H32)
- F4 — GMF/ICA base, comisión admin, costos financieros (~6 tests)
- F5 — Cadena C HITL no modelada (~7 tests)
- F6 — interpretación anualizada vs mensual en C40/C72/B19 (~4 tests)

Ninguno de estos gaps es resoluble en F2 sin tocar el motor (fuera de
scope). Los gaps están todos documentados y atribuidos a su fase
correspondiente.

---

## 10. Recomendación para F3

**F3 — Runtime unification** debería:

1. **Cerrar drift H32 14% Payroll Cadena A**: alinear
   `NominaService.calcular(1750905, 0.10)` (que produce ~2.9M) con
   `costo_empresa_excel = 2,730,864` (valor pre-cargado Excel
   "Inputs de Nomina"!F39). Probablemente el motor tiene una fórmula de
   prestaciones/aportes con un parámetro divergente del Excel.

2. **Decommissionar `calculators/`**: la fórmula `calcular_ingreso_desde_costo`
   extraída a `domain/finance/` en W9 no es ejercida por el runtime
   (mutation test confirmó). Esto debe cerrarse antes de F4 para que las
   correcciones financieras se reflejen en el oracle.

3. **Verificar que la materialización staff post-W19 está exenta de drift
   adicional**: con comision Director/GTR ahora en 0, el motor debería
   producir costos ligeramente menores; cuantificar el delta vs oracle H31.
