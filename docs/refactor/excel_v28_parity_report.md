# Excel V2-8 Parity Report — Stage 1 (Harness + V2-7→V2-8 Delta)

**Fecha:** 2026-06-10 · **Rama:** refactor/modular-pure
**Veredicto Stage 1:** `EXCEL_V28_PARITY_PARTIAL` — changeset extraído; correcciones diferidas a Stage 2 (CHECKPOINT antes de editar `modules/**`/YAML/fórmulas/contratos/golden).

---

## 1. Excel canónico usado

- Paridad objetivo: `excel/Nexa - Pricing - Simulador - V2-8.xlsx` (sha256 `48d51055…`)
- Referencia V2-7: `excel/Nexa - Pricing - Simulador - V2-7.xlsx` (sha256 `5fb7174f…`)

## 2. Gate de drift V2-7 (ajuste #2) — **PASS**

El backend está certificado en paridad V2-7. El gate verifica que el V2-7 local sea el
mismo workbook de la certificación.

- Hash certificado (de `tests/parity/excel_oracle_v2_7_full.json::workbook_sha256`):
  `5fb7174f998356c1fdc92315d391cd1f09294a058e4916e9c03f0cb0f10e4db0`
- Hash V2-7 actual: **idéntico** → `V27_DRIFT_DETECTED` NO disparado.
- Nota: `excel_backend_parity_certification_closeout.md` no registraba hash; el oracle JSON
  (fuente numérica real de los tests de paridad V2-7) sí → gate satisfecho con fuente más fuerte.

## 3. request.json usado

- `request/request.json` · backup: `request/request.json.pre_v28_parity.bak` (idéntico).
- Identidad del deal: **Cobranzas / Bancamia / No Grupo Aval / 24m / Bogotá-Toberín**.
- Diff vs backup: sin cambios (Stage 1 no edita request).

## 4. Conjuntos de hojas (ajuste #3)

- **SHEETS_BOTH (23):** todas las hojas existen en ambos workbooks.
- **SHEETS_ONLY_V28 (0):** ninguna → sin candidatos `MISSING_IN_BACKEND` por hoja nueva.
- **SHEETS_ONLY_V27 (0):** ninguna → sin decisión humana por hoja eliminada.

V2-8 no agrega ni elimina hojas; los cambios son intra-hoja.

## 5. Clasificación de hojas (motor / vista)

Poblado en `scripts/excel_map_common.py::SHEET_TYPE`. 17 motor, 6 vista (`Visión P&G`,
`Visión Imprimible`, `Vision Cost To Serve`, `Vision Tarifas_Modelo_Cobro`, `Visiones`,
`Graficos`). Detalle de arquitectura en `structure_audit_lite.md`.

## 6. Metodología de diff y clasificación (ajuste #1)

Ambos workbooks llevan un **deal de ejemplo distinto** cargado, por lo que comparar valores
cacheados es ruido. V2-8 además **insertó/eliminó filas** en varias hojas, lo que retargetea
referencias absolutas sin cambiar lógica. Para aislar la señal real:

1. Fórmulas se comparan exactas (A1) y en **R1C1** (ignora shift uniforme).
2. Si difieren, se compara el **skeleton** (toda referencia enmascarada a `@`):
   skeleton igual → `REFERENCE_RETARGET` (ruido); skeleton distinto → `FORMULA_LOGIC_CHANGED`.
3. `FORMULA_LOGIC_CHANGED` se agrupa por transición de skeleton distinta → **changeset accionable**.

Mapeo a las 4 categorías del ajuste #1:

| Categoría ajuste #1 | Clase del diff | Trato Stage 2 |
|---|---|---|
| **SEMANTIC_CHANGE** | `FORMULA_LOGIC_CHANGED`, `CONSTANT_CHANGED` | candidato a cambio |
| **FORMAT_ONLY** | (sin formato puro detectado; shifts → retarget) | no aplica |
| **COMMENT_OR_LABEL** | `LABEL_CHANGED` | no candidato |
| **STRUCTURAL** | `REFERENCE_RETARGET`, `FORMULA_ADDED/REMOVED`, `DATA_STRUCTURAL` | validar vía runner, no por diff |

## 7. Magnitud del delta V2-7 → V2-8

| Métrica | Valor |
|---|---|
| Celdas con cambio (bruto) | ~75k |
| Ruido de shift (retarget + add/rem + data + label) | ~55k |
| `FORMULA_LOGIC_CHANGED` (celdas) | 18.158 |
| `CONSTANT_CHANGED` (celdas) | 1.653 |
| **Transiciones de fórmula distintas (changeset real)** | **177** |

> **V2-8 es un rework mayor, no un incremento menor.** La compresión 18.158 celdas → 177
> transiciones distintas confirma que una sola edición de patrón se replica sobre grillas.

### Transiciones por hoja

| Hoja | Tipo | Transiciones | LOGIC (celdas) | CONST | Ruido shift |
|------|------|-------------:|---------------:|------:|------------:|
| Condiciones Cadena A | motor | 5 | 95 | 5 | 2141 |
| Condiciones Cadena C | motor | 1 | 22 | 25 | 75 |
| Costo Cadena C | motor | 41 | 4126 | 73 | 10635 |
| Costo Fijo | motor | 22 | 1808 | 138 | 6292 |
| Costo Variable | motor | 1 | 15 | 31 | 18 |
| Costos Totales | motor | 1 | 1440 | 73 | 0 |
| Hoja Maestra Escenarios | motor | 8 | 37 | 59 | 136 |
| Inputs de Nomina | motor | 42 | 543 | 20 | 3613 |
| Listas Desplegables | motor | 3 | 119 | 0 | 242 |
| Nomina Loaded | motor | 24 | 4057 | 85 | 21001 |
| Pólizas - Costo Financiacion | motor | 5 | 5400 | 486 | 3 |
| Riesgo | motor | 1 | 1 | 4 | 4 |
| Tasas, TRM, Polizas | motor | 1 | 5 | 0 | 40 |
| **Visión P&G** | vista | **3** | 420 | 495 | 62 |
| **Vision Tarifas_Modelo_Cobro** | vista | **15** | 29 | 31 | 136 |
| **Vision Cost To Serve** | vista | **2** | 16 | 48 | 221 |
| **Visión Imprimible** | vista | **1** | 1 | 0 | 183 |
| Graficos | vista | 1 | 24 | 13 | 1030 |
| Condiciones Cadena B / No payroll / Panel / Rot,Ausent | motor | 0 | 0 | 3–33 | — |

Detalle celda-a-celda y ejemplos de cada transición: `docs/refactor/excel_v27_v28_diff.{md,json}`.

## 8. Cambios de lógica destacados (muestra del changeset)

- **Costos Totales** (1 transición ×1440 celdas): `=SUMIFS(...)+SUMIFS(...)` →
  `=IF($B<>"",SUMIFS(...),0)+IF($B<>"",SUMIFS(...),0)` — guard de fila vacía.
- **Condiciones Cadena C** J62 (1 transición ×22): `=IF(E62="Total",G62,G62*H62)` →
  `=IFERROR((I62/H62)*(1+'Panel de Control General'!$L$11),0)` — nueva derivación con indexación L11.
- **Condiciones Cadena A** (5 transiciones): bloque de cálculo FTE/salario reescrito con
  guards `IF($C<>TRUE,...)` e indexación a `'Panel de Control General'!$C$20`.
- **Costo Cadena C** (41 transiciones): reorganización profunda de bloques (CAPEX/OPEX/HITL)
  — incluye reubicación de filas y nuevas series con `INDEX/MATCH` sobre `Tasas, TRM, Polizas`.
- **Visión P&G** (3 transiciones + 495 constantes): cambios de anclas `'Condiciones Cadena A'!$E$19`
  → `$E$11` (retarget) y 495 literales — requieren re-derivar el cell-map P&G para V2-8.

## 8b. Triage de las 177 transiciones (Stage 2 prep)

`scripts/triage_v28_transitions.py` clasifica cada transición distinta:
`NEW_FUNCTION` 106 · `DROPPED_FUNCTION` 26 · `CONSTANT_IN_FORMULA` 26 ·
`TRIVIAL_REWRITE` 16 · `LIKELY_LAYOUT_REORG` 3. Detalle:
`docs/refactor/excel_v28_triage.{md,json}`.

**Advertencia de fiabilidad:** en hojas-motor con reorganización profunda
(`Costo Cadena C`, `Nomina Loaded`, `Costo Fijo`, `Inputs de Nomina`) la
etiqueta `NEW_FUNCTION` puede ser un formula *reubicado*, no una regla nueva →
validar numéricamente tras recalcular V2-8. En las hojas estables (vistas +
`Condiciones Cadena C`) el triage es confiable.

### Hallazgos de negocio destacados (confirmados leyendo la fórmula)

1. **Visión P&G — cambio de modelo de ingreso/contingencias (ALTO impacto).**
   V2-7 derivaba ingreso como cost-gross-up por margen y contingencias como
   `%·base` del Panel; V2-8 los lee de la tabla **'Hoja Maestra Escenarios'**
   con gate de rango de fechas:
   - C19 ×180: `=IFERROR((C31/(1-Panel!$C$63))*C$15,0)` →
     `=IF(AND(mes∈rango), 'Hoja Maestra Escenarios'!$C$296,0)*C$15*(1+…)`
   - C22 ×180 / C25 ×60: `=C$18*Panel!$C67` →
     `=IF(AND(mes∈rango), ±SUMIFS('Hoja Maestra Escenarios'!$D$295:$D$31…),0)`
   - Impacto backend: `modules/pyg/` (ingreso/contingencias) + alimentación
     desde `escenarios_comerciales` (Hoja Maestra Escenarios). Es el cambio de
     mayor superficie y debe triagearse contra el motor antes que las vistas.
2. **Vision Tarifas — derivación de tarifa simplificada.**
   D143/D150 ×5: `=IFERROR(((C40+C50+C60)*D35+D77)/C150,0)` → `=C150/$C$140`
   (tarifa = base / denominador único C140). Impacto: `modules/vision_tarifas/`.
3. **Condiciones Cadena C — nueva indexación L11.**
   J62 ×22: `=IF(E62="Total",G62,G62*H62)` →
   `=IFERROR((I62/H62)*(1+'Panel de Control General'!$L$11),0)`. Impacto:
   `modules/cadena_c/` + nuevo parámetro de indexación (Panel L11).
4. **Costos Totales — guard de fila vacía** (1 transición ×1440):
   `SUMIFS(...)` → `IF($B<>"",SUMIFS(...),0)`. Defensivo; bajo impacto numérico
   salvo filas vacías. Impacto: `modules/pyg/services/costos_totales_calculator.py`.

### Mapeo backend de los hallazgos destacados (read-only, confirmado en código)

| # | Cambio V2-8 | Owner backend actual (V2-7) | Acción Stage 2 |
|---|-------------|------------------------------|----------------|
| 1 | P&G ingreso/contingencias → tabla 'Hoja Maestra Escenarios' con gate de fechas | `modules/pyg/services/pyg_calculator.py:209-213` — `ingreso_bruto_a=ingreso_cadena_a`, `contingencia_op=panel.op_cont*ingreso_bruto`, `contingencia_com=panel.com_cont*ingreso_bruto` (modelo %·base V2-7) | Re-cablear `PyGCalculator.calcular_mes` para leer ingreso/contingencias desde `escenarios_comerciales` con gate de mes. **Hoy `escenarios`/`lns` solo los consume `vision_imprimible` (display), NO el motor P&G** → wiring nuevo en motor |
| 2 | Tarifa = base/`C140` (denominador único) | `modules/vision_tarifas/reglas.py:117` `calcular()` (usa denominador Excel para tarifa) | Ajustar derivación de tarifa al nuevo denominador V2-8 |
| 3 | Cadena C J62 `(I62/H62)*(1+Panel!L11)` (nueva indexación) | `modules/cadena_c/reglas.py:151` `_costo_tarifa_proveedor` / `factor_ajuste` | Incorporar factor de indexación Panel!L11 al ajuste de Cadena C |
| 4 | Costos Totales guard `IF($B<>"",SUMIFS,0)` | `modules/pyg/services/costos_totales_calculator.py` | Guard defensivo de fila vacía (bajo impacto) |

> Estas 4 acciones tocan `modules/**` → **gated por CHECKPOINT**. Requieren además
> el V2-8 recalculado con el deal de request.json para validar numéricamente.

## 9. Hallazgo bloqueante para paridad numérica: INPUT_DEAL_MISMATCH

`scripts/excel_parity_runner.py` ejecuta el motor sobre request.json y antepone un guard:

| Campo | request.json | V2-8 cargado |
|---|---|---|
| servicio | Cobranzas | **SAC** |
| cliente | Bancamia | **METROCUADRADO COM SAS** |
| tipo_cliente | No Grupo Aval | **Grupo Aval** |
| duracion_meses | 24 | 24 |

→ **INPUT_DEAL_MISMATCH**. Una comparación numérica backend(request.json) vs celdas
cacheadas V2-8 NO es válida. Además, las celdas P&G en coordenadas V2-7 (C26/C31/…) leen 0
en V2-8 → el **cell-map P&G está obsoleto** para V2-8.

**Prerrequisito Stage 2:** alinear inputs — (a) construir un request que reproduzca el deal
de V2-8 (METROCUADRADO/SAC/Grupo Aval), o (b) re-ingresar el deal de request.json en V2-8 y
recalcular en Excel para refrescar el cache de valores. Sin esto no hay veredicto numérico.

## 10. Doble path de carga (nota solicitada por el usuario)

Existen dos rutas para alimentar el motor:

| Path | Cómo | Uso actual |
|---|---|---|
| `UserInputLoader().cargar(ruta)` | lee archivo `test_cases/input/<case>.json` | `scripts/validate_excel.py` (V2-7), golden tests |
| `UserInputLoader().cargar_desde_dict(data)` | dict en memoria (request.json / body REST) | endpoint `POST /simulation/calculate`, runner V2-8 |

Ambos convergen en `_construir()` → mismo `UserInput`. La diferencia es solo el origen
(archivo vs dict) y validaciones de borde. **Recomendación Stage 2:** NO unificar las firmas
(son contratos distintos: archivo de test vs body REST), pero **sí unificar el deal de
referencia** — el runner V2-8 y los golden deberían apuntar al mismo deal canónico para que
la paridad sea comparable. La fragmentación de hoy es de *datos de ejemplo*, no de código.

### Anomalía menor observada (no bloqueante)

Primer `calcular()` en proceso frío falló una vez en `_calcular_reglas_negocio`
(`get_politicas_comerciales()` devolvió forma inesperada); corridas siguientes 3/3 OK y
deterministas. Posible estado de cache frío en el provider de parametrización. Registrado
para vigilancia; no afecta Stage 1.

## 11. Constantes cambiadas (CONSTANT_CHANGED) — 1.653 celdas

Concentradas en `Pólizas - Costo Financiacion` (486), `Visión P&G` (495), `Costo Fijo`
(138), `Costo Cadena C` (73), `Costos Totales` (73). Candidatas a `BUSINESS_RULE_MISMATCH` /
`HARDCODED_PARAM` — pero su validación depende de alinear el deal (muchas son inputs del
deal cargado, no parámetros de negocio). Clasificación fina diferida a Stage 2 tras alineación.

## 12. Mapeo config → Excel (preliminar)

Business rules viven en `modules/shared/config/business_rules/` (NO en `config/business_rules/`
como asume el prompt). Inventario en `scripts/excel_map_common.py::CONFIG_FILES_INVENTORY`:
`riesgo.yaml`, `margenes.yaml`, `politicas_comerciales.yaml`, `operaciones.yaml`, +
`calculator_motor/constants/global_constants.py`. `CONFIG_TO_EXCEL_MAP` se poblará en Stage 2.

## 13. Decisiones tomadas

1. **Arquitectura: parity only, defer structural** (confirmado con usuario). Frontera híbrida
   motor↔vista preservada; violaciones inventariadas en `structure_audit_lite.md`.
2. **Gate drift V2-7:** ante ausencia de hash en el closeout, se usó el hash del oracle JSON
   (fuente numérica real) → PASS. No kill-switch.
3. **Diff por valores cacheados descartado** como señal de paridad (deal distinto por
   workbook). Señal real = transición de skeleton de fórmula.
4. **Parity runner numérico diferido** a Stage 2 por `INPUT_DEAL_MISMATCH`; runner actual
   solo reporta con guard explícito (no emite veredicto numérico).
5. **Cell-map P&G V2-7 declarado obsoleto** para V2-8 (lee 0 en coords viejas).

## 14. Diferido a Stage 2

- Alinear deal de referencia (request ↔ V2-8) — **prerrequisito** de todo lo numérico.
- Re-derivar cell-maps V2-8 por hoja de vista (P&G primero).
- Triage de las 177 transiciones: cuáles son lógica de negocio real vs reorganización de
  layout; mapear cada una a `modules/<motor|vista>:archivo:función`.
- Clasificar las 1.653 constantes en `CONSTANT_CHANGED` (input del deal vs parámetro YAML).
- Implementar correcciones en capas canónicas (motor primero), tests V2-8 espejo,
  re-apuntar `make validate-excel` a V2-8, Phase 6 limpieza de Excels viejos.

## 15. Artefactos Stage 1

- `scripts/excel_map_common.py`, `scripts/excel_diff_v27_v28.py`,
  `scripts/excel_map_vision_pyg.py`, `scripts/excel_parity_runner.py`
- `docs/refactor/excel_v27_v28_diff.{md,json}` (changeset completo)
- `docs/refactor/structure_audit_lite.md`, `docs/refactor/adapters_inventory.md`
- `reports/v28_parity_runner.md`
- Backups: `request/request.json.pre_v28_parity.bak`, `.parity_backup/v28/`
