# V2-8 — Vision CTS Formula Map (Excel → Backend)

> **⮕ UPDATE 2026-06-12 — `CONTRACT_CHANGE_CARGOS_ADICIONALES_APPLIED`.** El gap P0 identificado aquí
> (`cargos_adicionales` ausente del numerador FTE soporte) fue **implementado**. CTS-001 mejoró
> **-128.43 → -61.33 COP/tx (+67.10)**. La firma -6.938% de cap_inicial/cap_rotación/crucero **persiste**
> porque esas líneas NO se cablearon en esta sesión (siguen sobre `fte` de agentes; scope = solo soporte regular).
> El residual lo domina el override manual **E95=9.5 (DIFERIDO)**. Detalle: `cts_001_v28_evidence.md`,
> `contract_design_cargos_adicionales_v28.md`.

Fecha: 2026-06-12 · Rama: `refactor/modular-pure` · Modo: **DIAGNÓSTICO READ-ONLY**
(sin tocar `modules/`, `request/request.json`, `storage/`, contratos, tests; sin `make baseline`; sin fixes).
Commit base: `e296c77` (`DIAS_CAPACITACION_REQUEST_ALIGNMENT_APPLIED`).
Fuente canónica: `excel/Nexa - Pricing - Simulador - V2-8.xlsx`, hoja **`Vision Cost To Serve`**.
Deal: SAC / METROCUADRADO COM SAS / Grupo Aval — 24m. Denominador Cadena A: Panel!W31 = 221,000 tx/mes.
Provider backend: `tests/refactor/_v28_deal_provider.py` (HR activo + W-override 20 roles staff).

> **Objetivo:** mapa fórmula-por-fórmula de `Vision Cost To Serve` (celda Excel → fórmula → componente
> backend → delta actual → clasificación), priorizado por componente CTS. Decide si `cargos_adicionales`
> sigue siendo el único gap estructural grande **antes** de abrir contrato.
> **Regla:** Vision CTS es OUTPUT, no fuente de input. No se inventan campos de request desde esta hoja.

---

## 0. Estructura de la hoja (denominador común)

Toda línea de Cadena A en `Vision Cost To Serve` (columna C) tiene la forma:

```
C_line = SUM( IF(Panel!M17=TRUE, <hoja>!<rango_mensual_M1>, 0),
              IF(Panel!M30=TRUE, <hoja>!<rango_mensual_M2>, 0) )
         / 'Panel'!$C$11    (= 24 meses)
         / 'Panel'!$W$31    (= 221,000 tx/mes)
```

Es decir: **promedio mensual del costo sobre 24 meses, dividido por 221,000 tx/mes**. El backend replica
exactamente esta estructura en `cost_to_serve_calculator.py:329` (`avg_div = (acumulado/numero_meses)/denominador`).

Hojas origen de los rangos: **`Nomina Loaded`** (payroll, filas 115/205/262/311/373/431/479) y
**`No payroll`** (no-payroll, filas 114/193/255). El denominador W31 y el divisor C11 coinciden con backend.

---

## 1. Fórmulas extraídas de Vision CTS (bloque de resultados Cadena A)

| Celda | Concepto | Fórmula Excel (abreviada) | Valor Excel | Referencias | Nota |
|-------|----------|---------------------------|-------------|-------------|------|
| **C34** | **Cost To Serve (total A)** | `=C35+C45` | **6,224.575126** | C35, C45 | Payroll + No-payroll |
| **C35** | **Payroll** | `=SUM(C37:C43)` | **5,462.355884** | C37..C43 | incluye cap/exám/crucero |
| C36 | Nomina Loaded (subtotal) | `=SUM(C37:C38)` | 5,405.229652 | C37, C38 | display; NO se suma a C34 |
| C37 | Salario Fijo | `Nomina Loaded!D115:BK115 /C11/W31` | 4,629.486449 | Nomina Loaded!115 | |
| C38 | Salario Variable | `Nomina Loaded!D205:BK205 /C11/W31` | 775.743203 | Nomina Loaded!205 | comisiones cargadas |
| C39 | Capacitación Inicial | `Nomina Loaded!D262:BK262 /C11/W31` | 11.588351 | Nomina Loaded!262 | |
| C40 | Capacitación Rotación | `Nomina Loaded!D311:BK311 /C11/W31` | 22.666815 | Nomina Loaded!311 | |
| C41 | Exámenes Médicos | `Nomina Loaded!D373:BK373 /C11/W31` | 12.241808 | Nomina Loaded!373 | |
| C42 | Estudios de Seguridad | `Nomina Loaded!D431:BK431 /C11/W31` | 0.000000 | Nomina Loaded!431 | flags OFF en deal |
| C43 | Crucero | `Nomina Loaded!D479:BK479 /C11/W31` | 10.629257 | Nomina Loaded!479 | |
| **C45** | **No Payroll** | `=SUM(C46:C48)` | **762.219242** | C46..C48 | |
| C46 | OPEX Fijo | `No payroll!D114:BK114 /C11/W31` | 308.138215 | No payroll!114 | |
| C47 | Inversiones (CAPEX) | `No payroll!D193:BK193 /C11/W31` | 103.043569 | No payroll!193 | amortización |
| C48 | Costos Fijos x Estación | `No payroll!D255:BK255 /C11/W31` | 351.037458 | No payroll!255 | |
| D35..D48 | Participación (%) | `=IFERROR(C_line/$C$34,0)` | — | C34 | ratios display |
| **G49** | **CTS Ponderado** | `=(C34*C31)+(G34*G31)+(K34*K31)` | **4,660.075917** | C34/G34/K34, C31/G31/K31 | mezcla A/B/C |
| C31 | Participación Cadena A | `'Panel'!$W$32` | 0.45010183 | Panel!W32 | peso ponderado |
| G34 | CTS Cadena B | `=G35+G41` | 151.506256 | (otra hoja) | fuera de scope CTS-A |
| K34 | CTS Cadena C | `=SUM(K35,K36,K40)` | 5,278.326745 | Costo Cadena C | fuera de scope CTS-A |

**Bloque "Visión General por Canal" (filas 62-70):** fórmulas array que reparten volumen por canal
(Voz1/Voz2/WhatsApp) y ponderan CTS por canal. Son **OUTPUT_ONLY_NOT_INPUT** (display de mezcla de
canales); no introducen costo nuevo. No se mapean a backend en esta sesión (no afectan C34).

**Bloque "Economics" (B19/H19):** `INGRESO MENSUAL` (Vision Tarifas C75) y `COST TO SERVE MENSUAL`
(suma de costos totales mensuales). Son agregados de presentación; el CTS unitario vive en C34. OUTPUT_ONLY.

Celdas con fórmula/valor relevantes extraídas: **~46** (bloque resultados A = 14 + D-ratios 11 +
ponderado/pesos 5 + Cadena B/C totales 2 + economics 2 + canal 12). El bloque **CTS Cadena A core = 14 celdas**.

---

## 2. Agrupación por componente CTS (Excel vs Backend)

Backend capturado con `build_v28_deal_provider()` + `request.json` actual (post `e296c77`).
Mapeo de campos: backend `nomina`↔C35, `nomina_loaded`↔C36, `salario_fijo`↔C37, `salario_variable`↔C38,
`capacitacion_inicial`↔C39, `capacitacion_rotacion`↔C40, `examenes`↔C41, `estudios_seguridad`↔C42,
`crucero`↔C43, `no_payroll`↔C45, `opex_fijo`↔C46, `inversiones`↔C47, `costos_fijos_estacion`↔C48.

| Grupo | Celda | Excel | Backend | Delta COP/tx | % | Estado |
|-------|-------|-------|---------|--------------|---|--------|
| **Total CTS A** | C34 | 6,224.575126 | 6,096.142357 | **-128.432769** | -2.063% | KNOWN_DELTA |
| **Payroll** | C35 | 5,462.355884 | 5,320.376113 | **-141.979771** | -2.599% | CONTRACT_GAP (raíz) |
| Nomina Loaded | C36 | 5,405.229652 | 5,267.093922 | **-138.135730** | -2.556% | CONTRACT_GAP (raíz) |
| Salario Fijo | C37 | 4,629.486449 | 4,772.947333 | +143.460884 | +3.099% | FORMULA_MISMATCH (split) |
| Salario Variable | C38 | 775.743203 | 494.146589 | -281.596614 | -36.30% | FORMULA_MISMATCH (split) |
| Cap Inicial | C39 | 11.588351 | 10.784314 | -0.804037 | **-6.938%** | CONTRACT_GAP (cargos_adic) |
| Cap Rotación | C40 | 22.666815 | 21.094118 | -1.572697 | **-6.939%** | CONTRACT_GAP (cargos_adic) |
| Exámenes | C41 | 12.241808 | 11.511995 | -0.729813 | -5.962% | CONTRACT_GAP (fte soporte) |
| Estudios Seg | C42 | 0.000000 | 0.000000 | 0.000000 | — | MATCH_EXACT |
| Crucero | C43 | 10.629257 | 9.891765 | -0.737492 | **-6.938%** | CONTRACT_GAP (cargos_adic) |
| **No Payroll** | C45 | 762.219242 | 775.766244 | **+13.547002** | +1.777% | mixto |
| OPEX Fijo | C46 | 308.138215 | 308.138215 | **0.000000** | 0.000% | MATCH_EXACT |
| Inversiones/CAPEX | C47 | 103.043569 | 119.758618 | +16.715048 | +16.22% | FORMULA_MISMATCH (amort) |
| Costos Fijos | C48 | 351.037458 | 347.869412 | -3.168046 | -0.903% | KNOWN_DELTA |

**Reconciliación:** Payroll -141.98 + No-payroll +13.55 = **-128.43** = delta C34. ✔ exacto.

### Hallazgo central — firma de `cargos_adicionales`

**Cap Inicial (-6.938%), Cap Rotación (-6.939%) y Crucero (-6.938%) tienen delta porcentual IDÉNTICO.**
Las tres líneas escalan con el **FTE de soporte**: Excel cuenta el numerador como
`(fte_agentes + cargos_adicionales)/ratio` (CCA!E26/F26/G26 = 12/0/7.3846), backend usa solo
`fte_agentes/ratio`. El -6.94% es la **proporción exacta de FTE soporte que falta** por no sumar
`cargos_adicionales`. Es la huella estructural única: confirma que `cargos_adicionales` es la raíz común
de los deltas de cap/crucero **y** del grueso del payroll (`nomina_loaded` -138.14).

Exámenes (-5.96%) comparte la raíz (FTE soporte) con un mix de base ligeramente distinto.

### Nota sobre el split fijo/variable (C37/C38)

`salario_fijo` +143.46 / `salario_variable` -281.60 → net `nomina_loaded` -138.14. El backend pliega la
comisión de forma distinta (`salario_variable = comisiones`; `nomina_loaded = salario_fijo + comisiones`),
por lo que el **split** diverge fuerte pero el **neto** (-138.14) es la cifra estructural real. Documentado
como invariante de allocation en `cts_variable_split_attribution_v28.md`; **no** es un gap independiente del
neto. El neto -138.14 es atribuible a la dotación/costo de soporte (cargos_adicionales).

---

## 3. Mapa Vision CTS → backend (archivo / función)

| Celda/Grupo | Concepto | Backend equivalente | Archivo:línea | Match |
|-------------|----------|---------------------|---------------|-------|
| C34 | Total CTS A | `cts_cadena_a = (payroll+no_payroll)/denominador` | `cost_to_serve_calculator.py:35,180` | MATCH_WITH_TOLERANCE |
| C35 | Payroll | `desglose_a.nomina` (avg_payroll_a/den) | `cost_to_serve_calculator.py:281,334` | KNOWN_DELTA |
| C36 | Nomina Loaded | `avg_div(salario_fijo+comisiones)` | `cost_to_serve_calculator.py:337` | FORMULA_MISMATCH (split) |
| C37 | Salario Fijo | `avg_div(salario_fijo_acumulado)` | `cost_to_serve_calculator.py:338` | FORMULA_MISMATCH (split) |
| C38 | Salario Variable | `avg_div(comisiones_acumuladas)` | `cost_to_serve_calculator.py:339` | FORMULA_MISMATCH (split) |
| C39 | Cap Inicial | `nomina.py` capacitacion_inicial | `formulas/payroll/nomina.py:229-257` | CONTRACT_GAP (numerador FTE) |
| C40 | Cap Rotación | `nomina.py` capacitacion_rotacion | `formulas/payroll/nomina.py:229-257` | CONTRACT_GAP (numerador FTE) |
| C41 | Exámenes | `nomina.py` examenes | `formulas/payroll/nomina.py` | CONTRACT_GAP (fte soporte) |
| C43 | Crucero | `nomina.py:308` `tarifa_crucero*fte*idx` | `formulas/payroll/nomina.py:304-308` | CONTRACT_GAP (numerador FTE) |
| C45 | No Payroll | `desglose_a.no_payroll` | `cost_to_serve_calculator.py:285,335` | MATCH_WITH_TOLERANCE |
| C46 | OPEX Fijo | `avg_div(opex_ti_acumulado)` | `cost_to_serve_calculator.py:346` | MATCH_EXACT |
| C47 | Inversiones/CAPEX | `avg_div(capex_acumulado)` | `cost_to_serve_calculator.py:347` | FORMULA_MISMATCH (amort) |
| C48 | Costos Fijos | `avg_div(costos_fijos_acumulados)` | `cost_to_serve_calculator.py:348` | KNOWN_DELTA |
| G49 | CTS Ponderado | `cts_ponderado` (mezcla A/B/C) | `cost_to_serve_calculator.py` | OUT_OF_SCOPE (A-only) |
| Canal 62-70 | Mezcla por canal | `_calcular_canales_detalle` | `cost_to_serve_calculator.py:355` | OUTPUT_ONLY_NOT_INPUT |

El backend **anota cada campo con su celda Excel** (`# C036`..`# C048` en `cost_to_serve_calculator.py:336-348`).
El mapeo es 1:1, sin celdas ambiguas en el bloque core de Cadena A. La estructura denominador (C11/W31) coincide.

---

## 4. Comparación Excel vs backend (componentes expuestos)

| Componente | Excel | Backend | Delta | % | Clasificación |
|------------|-------|---------|-------|---|---------------|
| CTS-001 total (COP/tx) | 6,224.575126 | 6,096.142357 | -128.432769 | -2.063% | KNOWN_DELTA |
| Payroll | 5,462.355884 | 5,320.376113 | -141.979771 | -2.599% | CONTRACT_GAP |
| No-payroll | 762.219242 | 775.766244 | +13.547002 | +1.777% | mixto |
| OPEX | 308.138215 | 308.138215 | 0.000000 | 0.000% | MATCH_EXACT |
| CAPEX/Inversiones | 103.043569 | 119.758618 | +16.715048 | +16.22% | FORMULA_MISMATCH |
| Costos fijos | 351.037458 | 347.869412 | -3.168046 | -0.903% | KNOWN_DELTA |
| Exámenes | 12.241808 | 11.511995 | -0.729813 | -5.962% | CONTRACT_GAP |
| Crucero | 10.629257 | 9.891765 | -0.737492 | -6.938% | CONTRACT_GAP |
| Cap. inicial | 11.588351 | 10.784314 | -0.804037 | -6.938% | CONTRACT_GAP |
| Cap. rotación | 22.666815 | 21.094118 | -1.572697 | -6.939% | CONTRACT_GAP |
| Denominador (tx/mes) | 221,000 | 221,000 | 0 | 0% | MATCH_EXACT |

Todos los componentes están expuestos vía `ResultadoCostToServe.desglose_a`. **0 `BACKEND_METRIC_NOT_EXPOSED`.**

---

## 5. Gaps estructurales Vision CTS

| Gap | Celda(s) | Delta COP/tx | Tipo | Requiere request | Requiere contrato | Requiere modules | Prioridad |
|-----|----------|--------------|------|------------------|-------------------|------------------|-----------|
| **Support FTE / cargos_adicionales** | C35/C36/C39/C40/C41/C43 | **≈ -138 (payroll) + ≈ -3.1 (cap/cruc/exám)** | CONTRACT_GAP + MODULE_GAP | no | **sí** | sí (numerador FTE) | **P0_BLOCKS_CTS_FULL_MATCH** |
| CAPEX over-amortización | C47 | +16.72 (signo opuesto) | FORMULA_GAP | no | no | sí (fórmula amort) | P2_MEDIUM_DELTA |
| Split fijo/variable | C37/C38 | net 0 (invariante) | FORMULA_GAP | no | no | sí (allocation) | P4_DOC_ONLY |
| OPEX Fijo | C46 | 0.0 (exacto) | INPUT_ALREADY_MAPPED | — | — | — | — (cerrado) |
| Costos fijos estación | C48 | -3.17 | KNOWN_DELTA | no | no | posible | P3_LOW_DELTA |
| CTS Ponderado / canal | G49, 62-70 | — | OUTPUT_ONLY_NOT_INPUT | — | — | — | P4_DOC_ONLY |

**Composición del residual -128.43:**
```
Payroll  -141.98 = nomina_loaded -138.14 (cargos_adicionales/soporte)
                   + cap_inicial -0.80 + cap_rot -1.57 + crucero -0.74 + exámenes -0.73  (misma raíz FTE soporte)
No-payroll +13.55 = OPEX 0.0 (EXACT) + CAPEX +16.72 (over-amort) + costos_fijos -3.17
Neto       -128.43  (2.063%)
```

El **~97%** del déficit (payroll) tiene **una sola raíz: `cargos_adicionales` ausente del numerador de FTE
soporte**. El único otro gap real (CAPEX +16.72) tiene **signo opuesto** (enmascara, no agrava) y es de fórmula
de amortización, no de input.

---

## 6. Decisión antes de contract change

| Pregunta | Respuesta | Evidencia | Riesgo |
|----------|-----------|-----------|--------|
| ¿`cargos_adicionales` sigue siendo el gap estructural principal? | **SÍ** | Payroll -141.98 (~97% del residual); firma -6.938% idéntica en cap_inicial/cap_rot/crucero confirma raíz única FTE soporte; CCA!E26/F26/G26 = 12/0/7.3846 ausente del contrato | alto |
| ¿Hay otro gap comparable antes de abrir contrato? | **NO** | Único otro gap real = CAPEX +16.72 (FORMULA_GAP de amortización, ~13% magnitud, signo opuesto). OPEX = EXACT. Resto = known_delta menor | bajo |
| ¿El contrato debe cubrir overrides manuales tipo Supervisor SAC E95=9.5? | **PENDIENTE** | `cargos_adicionales` (12/0/7.3846) cubre el numerador agregado, pero E95=9.5 es un override **literal por rol** en Excel (no derivado de la fórmula). Cerrar 100% exige AMBOS: campo `cargos_adicionales` por escenario **y** mecanismo de override per-rol | medio |

**Conclusión:** `cargos_adicionales` **sigue siendo el único gap estructural grande** de Vision CTS Cadena A.
No existe otro frente comparable que justifique posponer la decisión de contrato. El diseño del contrato debe
contemplar (1) `cargos_adicionales` por escenario en `PerfilCadenaAInput`/`CondicionesCadenaAInput`, y (2) un
mecanismo de override per-rol para casos literales tipo SAC Supervisor E95=9.5. El CAPEX +16.72 es un frente
**separado de fórmula** (amortización), tratable después y sin contrato nuevo.

> No se diseña el contrato en esta sesión. Solo se informa la decisión: `CONTRACT_CHANGE_CARGOS_ADICIONALES`
> queda como **único P0** para cerrar CTS-001 Cadena A.

---

## 7. Gates

| Gate | Resultado |
|------|-----------|
| `tests/golden/test_cts_001_v28.py` | **2/2 PASS** |
| `tests/golden/test_cts_exam_crucero_v28.py` | **2/2 PASS** |
| `make validate-excel-v28` | **PASS (6/6, 1 skip)** |
| `make all` | **PASS** (test 36 pass · verify baseline match · validate-excel 7/7 match) |
| `make baseline` | **NO ejecutado** (prohibido) |

**Side effects:** `make all`/`validate-excel` regeneraron `reports/*` y `storage/parametrization/*/versions.json`
(ya en estado `M` antes de la sesión). No se commitean. Sin cambios en `modules/`, `request/`, `tests/`, `*.py`.
Hardcoded nuevos: **0**. Excel leído con `openpyxl` `read_only=True` (formulas + data_only).

---

## 8. Veredicto

**`V28_VISION_CTS_FORMULA_MAP_COMPLETED`**

- Mapa 1:1 completo del bloque CTS Cadena A (14 celdas core C34-C48) → backend `cost_to_serve_calculator.py`
  (campos anotados con celda Excel) + `nomina.py` (numeradores de payroll). 0 celdas `MAPPING_AMBIGUOUS`,
  0 `BACKEND_METRIC_NOT_EXPOSED`.
- **Raíz única confirmada:** `cargos_adicionales` ausente del numerador FTE soporte explica ~97% del residual
  (-128.43 COP/tx). Firma -6.938% idéntica en cap_inicial/cap_rotación/crucero.
- **No hay otro gap estructural comparable.** OPEX = paridad exacta; CAPEX +16.72 es FORMULA_GAP de
  amortización (signo opuesto, ~13%, sin contrato).
- **Decisión:** abrir `CONTRACT_CHANGE_CARGOS_ADICIONALES` (único P0); contemplar override per-rol (E95=9.5).
