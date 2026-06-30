# V2-8 — What-If Gap Simulation (CTS-001)

Fecha: 2026-06-11 · Rama: `refactor/modular-pure` · Modo: **DIAGNÓSTICO READ-ONLY**
(sin tocar `modules/`, `request/request.json` persistente, `storage/`, contratos, tests, `reports/`; sin `make baseline`).
Commit base: `83527e5`. Fuente canónica: `excel/Nexa - Pricing - Simulador - V2-8.xlsx`.
Deal: SAC / METROCUADRADO COM SAS / Grupo Aval — 24m, denominador Panel!W31 = 221,000 tx/mes.

> **Objetivo:** medir el impacto **real medido por el motor** de cada gap conocido de V2-8 sobre `CTS-001`,
> individualmente y en combinación, sin aplicar fixes. Reemplaza la estimación a mano por simulación.
> Mecanismo: copia en memoria de `request.json` + patch temporal de dict + ejecución del motor con el
> provider de test V2-8 (`build_v28_deal_provider`). Runner temporal bajo `/tmp` (eliminado, fuera del repo).

---

## Baseline actual

Reproducido con el provider V2-8 + `request.json` actual (OPEX override + crucero flag aplicados).

| Métrica | Backend actual | Excel V2-8 | Delta | Nota |
|---------|----------------|------------|-------|------|
| **CTS-001** | **6,093.2443** | **6,224.5751** | **-131.3308 (2.110%)** | `OPEX_EXACT_PARITY`; déficit payroll desenmascarado |
| Payroll (desglose_a.nomina) | 5,317.4781 | 5,462.3559 | -144.88 | déficit soporte (cargos_adicionales) |
| No-payroll (desglose_a.no_payroll) | 775.7662 | 762.2192 | +13.55 | CAPEX/inversiones +16.72, costos_fijos -3.17 |
| OPEX Fijo | 308.1382 | 308.1382 | **0.000000 (EXACT)** | `no_payroll_mensual` override |
| Inversiones (CAPEX) | 119.7586 | 103.0436 | +16.72 | reconciliación plazos (P3) |
| Costos Fijos x Estación | 347.8694 | 351.0375 | -3.17 | menor |
| Crucero | 9.8918 | 10.6293 | -0.7375 | residual cargos_adicionales |
| Exámenes | 11.5120 | 12.2418 | -0.7298 | residual fte_examenes (soporte) |

Baseline reproducible: ✔ (coincide con `cts_001_decision_checkpoint_v28.md` y `opex_request_alignment_v28.md`).

---

## Mecanismo de simulación

- `payload = json.loads(request.json)` → `copy.deepcopy` por caso → patch del dict → `UserInputLoader` →
  `SimulationContextBuilder(provider).construir` → `NexaPricingEngine(provider).calcular`.
- Métricas leídas de `resultado.cost_to_serve.desglose_a` y `resultado.pyg_por_mes[0].payroll_a`.
- `git status --short` **no cambió** por preparar/ejecutar simulaciones (todo en memoria + `/tmp`).
- Sin escritura en `request.json`, `modules/`, `storage/`, `contracts`, `tests`. Hardcodes nuevos en motor: **0**.

---

## Simulaciones individuales

Cada caso: A=baseline · B=variante con solo ese gap · C=Δ vs baseline · D=Δ vs Excel. **Medido por el motor.**

| Caso | Cambio simulado | CTS antes | CTS después | Δ CTS | Payroll Δ | No-payroll Δ | PyG payroll_a Δ (M1) | Riesgo | Simulable |
|------|-----------------|-----------|-------------|-------|-----------|--------------|----------------------|--------|-----------|
| **CARGOS_ADICIONALES** | CCA!E26/F26/G26 = 12/0/7.3846 al numerador soporte | 6,093.2443 | — | — | — | — | — | alto | **no** — `NOT_SIMULABLE_WITHOUT_MODULE_CHANGE` |
| **COMISION_ROL_STAFF** | `comision_rol` Director/Jefe Op/Supervisor en request | 6,093.2443 | 6,093.2443 | **0.0000** | 0.0 | 0.0 | 0.0 | bajo | sí (no-op) — `ALREADY_APPLIED_BASELINE` |
| **DIAS_CAPACITACION** | `dias_capacitacion_perfil` 10 → 11 (Excel E139) | 6,093.2443 | **6,096.1424** | **+2.8980** | +2.8980 | 0.0 | +640,466.67 | bajo | **sí** |
| **PCT_ACUMULADO** | `porcentaje_acumulado.actual` 0.02 → 0 (Panel!C75) | 6,093.2443 | 6,093.2443 | **0.0000** | 0.0 | 0.0 | 0.0 | bajo | sí (sin impacto CTS) |
| **CRUCERO_FULL_PARITY** | escalar tarifa crucero a Excel 10.6293 (**APPROXIMATION**) | 6,093.2443 | 6,093.9818 | **+0.7375** | +0.7375 | 0.0 | +163,041.18 | medio | parcial — ver nota |

### Notas por caso

- **CARGOS_ADICIONALES** — `NOT_SIMULABLE_WITHOUT_MODULE_CHANGE`. El numerador de soporte
  (`context_builder_perfiles_soporte_mixin`, `fte_agentes/ratio`) vive en `modules/` y no existe ningún
  campo de entrada (`rg cargos_adicionales` = 0 matches). Inyectarlo subiendo `perfiles[].fte` contaminaría
  el payroll de agentes, estaciones y volúmenes (no aísla el efecto). Además SAC Supervisor `E95=9.5` es un
  literal hardcodeado, no fórmula. No simulable de forma limpia sin tocar el motor o el contrato.
- **COMISION_ROL_STAFF** — patch de `roles_operativos[].comision_rol` con los valores Excel
  (Director 3,868,125 / Jefe Op 1,500,000 / Supervisor 700,000) → **Δ = 0.0 medido**. Confirma que el campo
  es `PRESENT_NOT_CONSUMED` (el motor usa `staff_config` + provider HR, no `roles_operativos`). La comisión
  staff **ya está embebida** en el `costo_empresa_override` del provider (W39=32.8M incluye D39=3.86M, etc.).
  → `ALREADY_APPLIED_BASELINE`. No hay palanca de request que lo mueva.
- **DIAS_CAPACITACION** — único gap request-scope con impacto **positivo medido** (+2.898 COP/tx). Mueve
  `capacitacion_inicial` (+0.98) y `capacitacion_rotacion` (+1.92). Mejora directa del headline hacia Excel.
- **PCT_ACUMULADO** — **Δ = 0.0 en CTS** (todas las métricas de CTS sin cambio). `porcentaje_acumulado`
  alimenta el factor billing / P&G, **no** el costo de CTS Cadena A. Corregir 0.02→0 es válido para fidelidad
  Excel del P&G/Tarifas pero **no mueve CTS**. No es un fix de CTS.
- **CRUCERO_FULL_PARITY** — `APPROXIMATION_USED`. La palanca real (cargos_adicionales en el numerador del
  crucero) no es simulable sin módulo. Como `tarifa_crucero` alimenta **solo** la línea de crucero
  (`nomina.py:308`) y el display de la ficha, escalar la tarifa cierra el crucero a 10.6293 en aislamiento
  (+0.7375 COP/tx) **sin** contaminar otras líneas — pero es una aproximación, no un fix legítimo (la tarifa
  Excel es 8,408, no la escalada). Mejora el headline pero **empeora fidelidad de input**.

OPEX_EXACT_PARITY: `ALREADY_APPLIED_BASELINE` (OPEX Fijo = 308.1382, Δ=0.0). No se revierte.

---

## Simulaciones combinadas

| Caso | Gaps incluidos | CTS final | Δ vs Excel | % residual | Mejora/empeora | Observación |
|------|----------------|-----------|------------|------------|----------------|-------------|
| **QUICK_WINS_ONLY** | dias_capacitacion(11) + pct_acumulado(0) | 6,096.1424 | -128.4328 | **2.063%** | mejora +2.898 | pct_acumulado aporta 0; todo viene de dias_cap |
| **REQUEST_SCOPE_ONLY** | dias_capacitacion(11) + pct_acumulado(0) | 6,096.1424 | -128.4328 | **2.063%** | mejora +2.898 | idéntico (solo dias_cap mueve CTS) |
| **CONTRACT_GAPS_ONLY** | cargos_adicionales | — | — | — | — | `NOT_SIMULABLE_WITHOUT_MODULE_CHANGE` |
| **ALL_SIMULABLE_INPUT_GAPS** | dias_cap + pct_acum + crucero(approx) | 6,096.8798 | -127.6953 | **2.051%** | mejora +3.636 | `APPROXIMATION_USED` (crucero) |
| **ALL_KNOWN_GAPS_APPROX** | idem ALL_SIMULABLE | 6,096.8798 | -127.6953 | **2.051%** | mejora +3.636 | `APPROXIMATION_USED` |

> **Hallazgo central:** aun aplicando **todos** los gaps simulables (incl. la aproximación de crucero), el
> residual cae solo de **2.110% → 2.051%** (de -131.33 a -127.70 COP/tx). El **97%** del residual (-127.70)
> es **payroll soporte** (`cargos_adicionales` + override SAC Supervisor E95), que **no es request-scope** —
> requiere decisión de contrato / módulo. No quedan palancas request-scope baratas que muevan el headline.

---

## Matriz de decisión

| Gap | Impacto real CTS (medido) | Requiere request | Requiere contrato | Requiere modules | Riesgo | Recomendación |
|-----|---------------------------|------------------|-------------------|------------------|--------|---------------|
| DIAS_CAPACITACION | **+2.898 COP/tx** | sí | no | no | bajo | `APPLY_NOW_REQUEST_SCOPE` (verificar E139=11 canónico) |
| PCT_ACUMULADO | **0.0 (CTS)** | sí | no | no | bajo | `NEEDS_FORMULA_MAP` para P&G/Tarifas — **no es fix de CTS** |
| COMISION_ROL_STAFF | **0.0 (no consumido)** | n/a | n/a | no | bajo | `ALREADY_APPLIED_BASELINE` (provider W-override) |
| OPEX_EXACT_PARITY | 0.0 (ya en paridad) | — | — | — | — | `ALREADY_APPLIED_BASELINE` |
| CRUCERO_FULL_PARITY | +0.7375 (solo via approx) | no | sí (cargos) | sí | medio | `DO_NOT_APPLY_COMPENSATING_GAP` (tarifa escalada = fake; real = cargos) |
| CARGOS_ADICIONALES | ≈ -68 (raíz dominante, no medible aquí) | no | **sí** | sí | alto | `REQUIRES_MODULE_CHANGE` + `APPLY_AFTER_CONTRACT_DECISION` |

---

## Plan recomendado

1. **Alinear `dias_capacitacion_perfil` 10 → 11** (request-scope) — ✅ **APPLIED 2026-06-12**
   - **Motivo:** único gap request-scope con impacto positivo medido en CTS.
   - **Impacto medido:** +2.898 COP/tx (2.110% → 2.063%). Mueve cap_inicial +0.98 / cap_rotacion +1.92.
   - **Excel confirmado:** CCA!E139=F139=G139=11 (label: "Días de capacitación por perfil").
   - **Estado:** `DIAS_CAPACITACION_REQUEST_ALIGNMENT_APPLIED`. Commit: `feat(v28): align capacitación days in request deal`.

2. **Alinear `porcentaje_acumulado.actual` 0.02 → 0** (request-scope, NO por CTS)
   - **Motivo:** fidelidad Excel del P&G / factor billing (Panel!C75=0). **No mueve CTS** (Δ=0 medido).
   - **Impacto medido:** 0.0 en CTS; impacto en P&G/Tarifas pendiente de mapear (`NEEDS_FORMULA_MAP`).
   - **Riesgo:** bajo. No invocar como mejora de CTS. Validar en una sesión de output (P&G/Tarifas).

3. **Decisión de contrato `cargos_adicionales` + override SAC Supervisor** (P0, raíz del residual)
   - **Motivo:** ~97% del residual (-127.70 COP/tx) es payroll soporte; no es request-scope.
   - **Impacto esperado:** ≈ -68 COP/tx (no simulable aquí — requiere campo de entrada nuevo por escenario
     en `PerfilCadenaAInput`/`CondicionesCadenaAInput` + mecanismo de override per-rol). Cierra además el
     residual de crucero (-0.7375) y parte del de exámenes (misma raíz fte soporte).
   - **Riesgo:** alto (contrato público + módulo + re-baseline). Requiere decisión de negocio.

**No aplicar (anti-recomendaciones):**
- **CRUCERO via tarifa escalada** — mejora el headline (+0.7375) pero empeora la fidelidad de input
  (tarifa real = 8,408). `DO_NOT_APPLY_COMPENSATING_GAP`. El cierre legítimo es vía cargos_adicionales.
- **Revertir OPEX override** para "mejorar" el headline — enmascararía el déficit de payroll. Mantener
  `OPEX_EXACT_PARITY`.

---

## Gates (Fase 7)

| Gate | Resultado |
|------|-----------|
| `tests/golden/test_cts_001_v28.py` | **2/2 PASS** |
| `tests/golden/test_cts_exam_crucero_v28.py` | **2/2 PASS** |
| `make validate-excel-v28` | **PASS (6/6, 1 skip)** |
| `make all` | **PASS** (test 36 pass · verify baseline match · validate-excel 7/7 match) |
| `make baseline` | **NO ejecutado** (prohibido) |

**Side effects:** `make all`/`validate-excel` regeneraron `reports/excel_backend_diff.*` y
`reports/v28_formula_parity_report.*` (ya estaban en estado `M` antes de la sesión). No se commitean.
Ningún cambio accidental en `modules/`, `request/`, `storage/`, `tests/`, `*.py`.

---

## Veredicto

**`V28_WHAT_IF_GAP_SIMULATION_COMPLETED`**

- Mayor impacto real: **DIAS_CAPACITACION** (+2.898 COP/tx), el único request-scope que mueve CTS.
- Mejor quick-win: **DIAS_CAPACITACION**.
- Cambio que NO conviene aplicar solo: **CRUCERO via tarifa escalada** (compensatorio/fake) y **revertir OPEX**.
- Requiere contrato: **CARGOS_ADICIONALES** (+ override SAC Supervisor) — raíz del 97% del residual.
- Requiere modules: numerador de soporte y crucero (cargos_adicionales).
- Conclusión estructural: el techo request-scope es **2.051%** (-127.70 COP/tx). Cerrar más exige decisión
  de contrato/módulo, no más hipótesis de input.

Hardcoded nuevos en motor: **0**. No se modificó motor, request.json, storage ni baseline.
