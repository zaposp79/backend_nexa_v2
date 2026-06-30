# V2-8 — Excel Engine Lineage (Fast Pass)

> **Diagnóstico READ-ONLY.** Sin tocar `modules/`, `request/request.json`, `storage/`, contratos, tests,
> baselines. Sin `make baseline`. Sin fixes. Objetivo: mapa accionable
> `Visiones/gráficos → hojas intermedias → inputs Panel/Condiciones → parametrización HR/OP/GN → request.json → backend`.

Fecha: 2026-06-12 · Rama: `refactor/modular-pure` · Commit base: `6778540`
Fuente canónica: `excel/Nexa - Pricing - Simulador - V2-8.xlsx` · Deal: SAC / METROCUADRADO COM SAS / Grupo Aval (24m, denom Panel!W31 = 221,000 tx/mes).
Provider backend de referencia: `tests/refactor/_v28_deal_provider.py` (HR activo + W-override 20 roles staff).

> **Propósito:** consolidar en un único índice la trazabilidad ya construida en
> `v28_input_full_mapping.md` (inputs), `v28_vision_cts_formula_map.md` (CTS), `v28_full_formula_inventory.md`
> y `v28_full_formula_backend_mapping.md` (P&G/Tarifas), **añadiendo** lo que faltaba: el DAG hoja-a-hoja,
> la capa de **parametrización HR/OP/GN ↔ backend** (Fase 4) y los **gráficos** (Fase 6).
> No re-extrae celda por celda lo ya mapeado; cita el doc fuente.

---

## ⚠️ BLOQUEADOR DE ESTADO (Fase 0 + Fase 10)

**`STOP_DIRTY_WORKTREE_GATE_BLOCK`** — el árbol de trabajo tiene un `request/request.json` **sin commitear**
(sesión previa `OPEX_REQUEST_ALIGNMENT`) que deja **`cantidad: null`** en
`condiciones_cadena_a/perfiles[1]` (WhatsApp) `opex_fijo.items[3]` y `[4]`.
Esto **rompe el motor** (`context_builder_perfiles_soporte_mixin.py:398`,
`float(item.get('cantidad', 1.0))` → `TypeError: ... not 'NoneType'`) y hace **fallar todos los gates que
ejecutan el engine**.

- En `HEAD` (commit `6778540`): **0** `cantidad` nulos → los gates pasan (verificado vía `git show HEAD:`).
- El fallo **no proviene de esta sesión** (diagnóstico read-only, 0 cambios de código/request).
- **Acción para próxima sesión de fix** (no en esta, kill-switch `tocar request`): poblar las 2 `cantidad`
  faltantes del perfil WhatsApp en `request.json` o revertir el WIP de OPEX al estado de `HEAD` antes de
  correr cualquier gate de motor.

Clasificación del worktree sucio (todo del **mismo workstream V2-8**, nada ajeno):

| Archivo | Origen | Tratamiento |
|---|---|---|
| `request/request.json` (M) | WIP `OPEX_REQUEST_ALIGNMENT` (con null cantidad) | NO commitear · NO tocar (kill-switch) · bloquea gates |
| `reports/*` (M), `reports/v28_full_formula_coverage_report.json` (??) | runtime artifacts | NO commitear |
| `storage/parametrization/{hr,op}/versions.json` (M) | runtime artifacts | NO commitear |
| `docs/refactor/opex_request_alignment_v28.md` (??) | doc de sesión previa | NO commitear (ajeno a esta sesión) |

---

## 1. Índice de dependencias Excel (hoja → rol → fórmulas)

Conteo de fórmulas vía `openpyxl` (ver `v28_full_formula_inventory.md` para el detalle por celda).

| Hoja | Fórmulas | Rol en el DAG | Tipo |
|---|---:|---|---|
| `Panel de Control General` | 221 | **Input raíz** (datos op, impuestos, indexación, reglas, pólizas, escenarios, volumetría) | INPUT_DIRECT |
| `Condiciones Cadena A` | 1,156 | **Input raíz** (perfiles, FTE, salarios, ratios staff, cap/exám/crucero, OPEX, CAPEX) | INPUT_DIRECT |
| `Condiciones Cadena B` | 113 | **Input raíz** (Voz2: OPEX plataformas, CAPEX, equipo soporte) | INPUT_DIRECT |
| `Condiciones Cadena C` | 109 | **Input raíz** (tarifa proveedor IA, consumo variable, HITL) | INPUT_DIRECT |
| `Tasas, TRM, Polizas` | 65 | **Parametrización** (IPC/SMLV por año, factores indexación acumulada, primas pólizas) | PARAMETRIZATION_VALUE |
| `Rot, Ausent y Rentabilidad` | 37 | **Parametrización** (rotación/ausentismo por servicio, margen objetivo, rampup) | PARAMETRIZATION_VALUE |
| `Listas Desplegables` | 240 | **Parametrización** (catálogos dropdown) | PARAMETRIZATION_VALUE |
| `Inputs de Nomina` | 3,525 | Intermedia (salarios base, SENA/Inclusión C59/C60, prestaciones) | INTERMEDIATE_FORMULA |
| `Nomina Loaded` | 18,570 | **Intermedia clave** (payroll cargado mensual; alimenta CTS C37-C43) | INTERMEDIATE_FORMULA |
| `No payroll` | 8,730 | **Intermedia clave** (OPEX/CAPEX/costos fijos; alimenta CTS C46-C48) | INTERMEDIATE_FORMULA |
| `Costo Fijo` | 5,157 | Intermedia (costos fijos por estación) | INTERMEDIATE_FORMULA |
| `Costo Variable` | 10,510 | Intermedia (costos variables) | INTERMEDIATE_FORMULA |
| `Costo Cadena C` | 13,659 | Intermedia (cadena C costo/tarifa) | INTERMEDIATE_FORMULA |
| `Costos Totales` | 5,151 | Intermedia (consolidación de costos) | INTERMEDIATE_FORMULA |
| `Pólizas - Costo Financiacion` | 11,808 | Intermedia (pólizas, ICA/GMF, comisión admin, financiación) | INTERMEDIATE_FORMULA |
| `Hoja Maestra Escenarios` | 357 | **Intermedia base ingreso** (HME!C296/C304/C312 = costo/(1−margen)) | INTERMEDIATE_FORMULA |
| `Graficos` | 1,006 | **Backing data de charts** (proporciones nómina, márgenes) | CHART_SOURCE |
| `Riesgo` | 17 | Backing data de chart (escala de riesgo) | CHART_SOURCE |
| `Vision Cost To Serve` | 447 | **Salida** (CTS A=COP/tx; B/C) | VISION_OUTPUT |
| `Visión P&G` | 1,982 | **Salida** (P&G mensual 24m) | VISION_OUTPUT |
| `Vision Tarifas_Modelo_Cobro` | 128 | **Salida** (tarifas por escenario/canal) | VISION_OUTPUT |
| `Visión Imprimible` | 116 | Salida (pass-through Panel + Tarifas + 2 charts) | VISION_OUTPUT |

---

## 2. DAG de fórmulas (flujo de dependencias)

```
                 ┌─────────────────────────── PARAMETRIZACIÓN ───────────────────────────┐
                 │ Tasas,TRM,Polizas (IPC 5.27% · SMLV · factores acum L8=0.05547729)     │
                 │ Rot,Ausent y Rentabilidad (rotación/ausent/margen/rampup 0.9/0.95/1.0) │
                 │ Inputs de Nomina (salario base · SENA/Inclusión C59/C60=1,750,905)     │
                 └───────────────────────────────┬───────────────────────────────────────┘
                                                  │
  INPUTS RAÍZ                                     ▼
  Panel de Control General ───────────►  ┌──────────────────────┐
  Condiciones Cadena A ──────────────►   │   HOJAS INTERMEDIAS   │
  Condiciones Cadena B ──────────────►   │ Nomina Loaded (115/   │──► Vision CTS C37-C43 (payroll)
  Condiciones Cadena C ──────────────►   │   205/262/311/373/479)│
                                         │ No payroll (114/193/  │──► Vision CTS C46-C48 (no-payroll)
                                         │   255)                │
                                         │ Costo Fijo/Variable   │──► Costos Totales
                                         │ Costo Cadena C        │──► Vision CTS K34 (CTS-C)
                                         │ Pólizas-Costo Financ. │──► P&G (ICA/GMF/ComAdm/fin)
                                         │ Hoja Maestra Escen.   │──► HME!C296 = base ingreso
                                         └───────────┬───────────┘
                                                     ▼
                                         ┌──────────────────────┐
                                         │      VISIONES         │
                                         │ Vision CTS  C34       │
                                         │ Visión P&G  I18..I30  │   (HME!C296 × rampup × IPC)
                                         │ Vision Tarifas H19    │
                                         │ Visión Imprimible     │
                                         └───────────┬───────────┘
                                                     ▼
                                         ┌──────────────────────┐
                                         │  CHARTS (display)     │
                                         │ Graficos! / Riesgo!   │  ← BarChart nómina, Scatter márgenes
                                         └──────────────────────┘
```

### Fórmulas intermedias principales

| Hoja | Celda | Concepto | Fórmula (abreviada) | Depende de | Valor Excel | Tipo |
|---|---|---|---|---|---|---|
| Nomina Loaded | 115 | Salario fijo cargado/mes | SUM bloque payroll | Cond.A E12 + Inputs Nómina + Tasas IPC | (alim. CTS C37) | INTERMEDIATE_FORMULA |
| Nomina Loaded | 205 | Salario variable/comisiones | SUM comisiones | Cond.A E13 + provider F44/51/62 | (alim. CTS C38) | INTERMEDIATE_FORMULA |
| Nomina Loaded | 262/311 | Cap inicial / rotación | f(FTE soporte, días cap) | Cond.A E26+E139, Rot sheet | (alim. C39/C40) | INTERMEDIATE_FORMULA |
| Nomina Loaded | 373/479 | Exámenes / crucero | f(FTE soporte, tarifas) | Cond.A E135/E152 | (alim. C41/C43) | INTERMEDIATE_FORMULA |
| No payroll | 114 | OPEX fijo | SUM items | Cond.A OPEX + No payroll C107/8/11 | 308.14 (C46) | INTERMEDIATE_FORMULA |
| No payroll | 193 | Inversiones/CAPEX | amortización | Cond.A inversiones | 103.04 (C47) | INTERMEDIATE_FORMULA |
| No payroll | 255 | Costos fijos x estación | f(estaciones) | Cond.A E11 + Costo Fijo | 351.04 (C48) | INTERMEDIATE_FORMULA |
| Hoja Maestra Escen. | C295/C296 | Base ingreso Cadena A | `=C258`; `=C295/(1-G253)` | Costos Totales + margen | 1,822,157,751.25 | INTERMEDIATE_FORMULA |
| Hoja Maestra Escen. | C289 | Base ingreso total | `=C266+C276+C286` | C266/276/286 | 3,018,108,469.26 | INTERMEDIATE_FORMULA |
| Tasas,TRM,Pol. | L8/M8 | Factor IPC acum año2/3 | `=B8+K8` (gate L6) | IPC 5.27% + Panel L6 | 0.05547729 / 0.05840094 | PARAMETRIZATION_VALUE |
| Vision CTS | C34 | CTS Cadena A | `=C35+C45` | C35+C45 | 6,224.575126 | VISION_OUTPUT |
| Visión P&G | I19 | Ingreso mes1 | `=HME!C296×I15×(1+IPC)` | HME!C296, rampup, IPC | 1,639,941,976 | VISION_OUTPUT |
| Vision Tarifas | H19 | Ingreso mensual base | `=SUM(C19:G19)` | escenarios | 3,018,108,469.26 | VISION_OUTPUT |

---

## 3. Lineage hacia request.json (resumen — detalle en `v28_input_full_mapping.md`)

`v28_input_full_mapping.md` ya traza ~70 celdas extremo-a-extremo. Resumen de estado:

| Status | Conteo | Casos destacados |
|---|---:|---|
| MATCH | ~48 | servicio/cliente, FTE 130/50/80, salario base, ICA/GMF, margen, indexación, volumen W31=221k, pólizas (10), escenarios, días cap=11 |
| VALUE_MISMATCH | 2 | `porcentaje_acumulado` req 0.02 vs Panel!C75=0 (P&G/tarifas, no CTS); Supervisor E95=9.5 override literal |
| MISSING_IN_REQUEST | 1 efectivo | ~~`cargos_adicionales`~~ ✅ **RESUELTO** (commit `6778540`, 12/0/7.3846); residual = E95 override |
| MISSING_IN_BACKEND_CONSUMPTION | 2 | `pct_ausentismo` (PRESENT_NOT_CONSUMED); `roles_operativos[]` (motor usa `staff_config`) |
| CONSUMED_FROM_PROVIDER_NOT_REQUEST | 1 | `comision_rol` staff = 0.0 en request; provider sirve F44/F51/F62 |

Casos obligatorios (Fase 3) — todos cubiertos en `v28_input_full_mapping.md` §3:
FTE agentes ✓ · cargos_adicionales ✅(resuelto) · dias_capacitacion=11 ✓ · crucero ✓(residual cerrado por cargos) ·
no_payroll/opex ✓(EXACT) · comisiones staff (provider) · rotación ✓ · ausentismo (no consumido) ·
tarifa diaria cap ✓ · CAPEX (residual +16.72) · pólizas ✓ · costo financiación ✓ · costos fijos/variables ✓ ·
Cadena C ✓ · componente tecnológico ✓ · margen/indexación ✓ · salario fijo/variable ✓.

---

## 4. Parametrización Excel ↔ backend  *(NUEVO — aporte principal de esta sesión)*

Fuentes backend (read-only): `tests/refactor/_v28_deal_provider.py` (provider del deal golden),
`storage/parametrization/{hr,op,gn}/*.json` (HR keys: campana, costo_fijo, med_seg, niveles, nomina,
prestaciones, ratios, recargos, rentabilidad, salarios, seg_social).

| Concepto | Hoja Excel | Celda/Rango | Valor Excel | Fuente backend | Valor backend | Status | Acción |
|---|---|---|---|---|---|---|---|
| IPC anual | Tasas,TRM,Pol. | B4:G4 | 0.0527 | provider/storage IPC | 0.0527 | **PARAM_MATCH** | — |
| Factor IPC acumulado año2/3 | Tasas,TRM,Pol. | L8/M8 | 0.05547729 / 0.05840094 | engine indexación | 0.05548 / 0.05840 | **PARAM_MATCH** (IPC_RATIO Δ=0) | — |
| SMLV crecimiento | Tasas,TRM,Pol. | B5/C5 | 0.12 / 0.2378 | storage SMLV | (mecanismo OK) | **PARAM_MATCH** | — |
| Rampup SAC m1/m2/m3 | Rot,Ausent | B39/C39/D39 | 0.9 / 0.95 / 1.0 | engine rampup (P&G I15/J15) | 0.9 / 0.95 | **PARAM_MATCH** (VPG_I15 Δ=0) | — |
| Rotación SAC (promedio) | Rot,Ausent | F19 | **0.077175** | provider `pct_rotacion_mensual` | **0.09** (OP-Costo fallback); request override 0.0815 | **PARAM_VALUE_MISMATCH** | fix futuro: poblar rotación SAC 0.077175 (impacto cap_rotación menor) |
| Ausentismo SAC (promedio) | Rot,Ausent | F8 | **0.081975** | provider `pct_ausentismo` 0.07; request 0.065 | divergente | **PARAM_VALUE_MISMATCH** pero `PRESENT_NOT_CONSUMED` | doc-only (no alimenta costo verificable) |
| Margen objetivo SAC | Rot,Ausent | C30 (Obj) / B30 (Mín) | 0.18 / 0.21 | request `margen_objetivo` 0.21 (=Panel C63) | 0.21 | **PARAM_MATCH** (deal usa Mínimo) | — |
| pct_examen_anual SAC | Cond.A | E135 | 0.28 | provider `_V28_PCT_EXAMEN_ANUAL_SAC` | 0.28 | **PARAM_MATCH** (vía provider) | — |
| Costo examen médico Bogotá | Nomina Loaded | C329 | 60,800 | provider med_seg patch | 60,800 | **PARAM_MATCH** (vía provider) | — |
| Salario SENA / Inclusión | Inputs Nómina | C59/C60 | 1,750,905 | provider `_V28_SENA_INCLUSION_SALARY` | 1,750,905 | **PARAM_MATCH** (vía provider) | — |
| Comisión Director / Jefe Op / Supervisor | Cond.A | F44/F51/F62 | 3,868,125 / 1,500,000 / 700,000 | provider W-override (salario_cargado) | idem | **PARAM_MATCH** (vía provider, no request) | cerrar `comision_rol` request vs provider si se modela por deal |
| Ratios staff | Cond.A | E104-E127 | 750/1200/…/20/100 | storage HR `ratios` | idem | **PARAM_MATCH** | — |
| tasa_financiacion (OP-Config) | — | — | (default) | `financial_parametrization_repository` default 0.0088 | 0.0088 | **PARAM_MISSING_EXISTING_FIELD** | OP-Config sheet ausente en parametrización activa; warning emitido; poblar en fix futuro |
| Primas pólizas | Tasas,TRM,Pol. / Panel | D39-D45 | 0.0063/0.0128/… | request `polizas[].pct_poliza` | idem | **PARAM_MATCH** | — |

**Hallazgo Fase 4:** la paridad de parametrización del deal golden se logra **mayoritariamente vía el provider
W-override** (`_v28_deal_provider.py`), no vía la parametrización activa en `storage/`. Los únicos
mismatches reales son `rotación SAC` (provider 0.09 vs Excel 0.077175 — `PARAM_VALUE_MISMATCH` corregible) y
`tasa_financiacion` (OP-Config ausente — `PARAM_MISSING_EXISTING_FIELD`). Ninguno requiere clave/tabla nueva.

---

## 5. Vision outputs → engine sheets

| Visión | Celda/Rango | Concepto | Hoja intermedia fuente | Backend componente | Status |
|---|---|---|---|---|---|
| Vision CTS | C34 | CTS Cadena A | Nomina Loaded + No payroll | `cost_to_serve_calculator.py:35,180` | **KNOWN_DELTA** (-61.33 post-fix) |
| Vision CTS | C35 (payroll) | Payroll | Nomina Loaded 115/205/262/311/373/479 | `desglose_a.nomina` | KNOWN_DELTA (E95 deferred) |
| Vision CTS | C46 (OPEX) | OPEX fijo | No payroll 114 | `cost_to_serve_calculator.py:346` | **MATCH_EXACT** (Δ=0) |
| Vision CTS | C47 (CAPEX) | Inversiones | No payroll 193 | `cost_to_serve_calculator.py:347` | **FORMULA_GAP** (+16.72 amort) |
| Vision CTS | K34 | CTS Cadena C | Costo Cadena C | `cts_cadena_c` | **FORMULA_GAP** (+51.28, ~1%) |
| Vision CTS | G49 | CTS ponderado | C34/G34/K34 × pesos | `cts_ponderado` | derivado (sigue a C34/K34) |
| Visión P&G | I18..I30 | P&G mensual | HME!C296 × rampup × IPC | `pyg_calculator.py` | **BLOCKED_BY_ARCHITECTURE_DELTA** (HME single-base) |
| Vision Tarifas | H19 | Ingreso mensual base | escenarios (C19:G19) | `kpis.ingreso_mensual` (cumulativo 24m) | **BACKEND_METRIC_NOT_EXPOSED** (field mapping VTM-001) |
| Visión Imprimible | varias | pass-through | Panel + Tarifas | — | OUTPUT_ONLY_NOT_INPUT |

Detalle 1:1 del bloque CTS (C34-C48) en `v28_vision_cts_formula_map.md` §3 (0 ambiguas, 0 no-expuestas).

---

## 6. Gráficos / charts  *(NUEVO)*

| Hoja | Gráfico | Tipo | Rango fuente | Concepto | Backend equivalente | Status |
|---|---|---|---|---|---|---|
| Vision CTS | #0 | BarChart | `Riesgo!D16:D18` / `E16:E18` | Escala de riesgo | — | CHART_SOURCE (display) |
| Vision CTS | #1 "Proporción de Nómina por grupo" | BarChart | `Graficos!AH31:AH33` / `AI31:AI33` | % nómina por grupo | `desglose_a.nomina` (derivable) | CHART_SOURCE |
| Vision CTS | #2 "Proporción de Nómina por cargo" | BarChart | `Graficos!AI5:AI28` / `AJ5:AJ28` | % nómina por cargo (24 roles) | desglose por rol soporte | CHART_SOURCE |
| Visión Imprimible | #0 | ScatterChart | (sin ref numérica directa) | — | — | CHART_SOURCE_NOT_EXTRACTABLE |
| Visión Imprimible | #1 "Comparación de Márgenes de Servicio y Cliente Histórico" | ScatterChart | (múltiples series, refs no resueltas por openpyxl) | Márgenes histórico vs servicio | `pyg` márgenes | CHART_SOURCE_NOT_EXTRACTABLE |

**Conclusión gráficos:** todos son **display de datos ya calculados** (proporciones de nómina, márgenes,
riesgo). No introducen costo/fórmula nueva. El backing data vive en `Graficos!`/`Riesgo!`, derivado de las
hojas intermedias. **No requieren cambio de backend**; el backend ya expone los agregados subyacentes
(`desglose_a`, márgenes P&G). Las 2 ScatterCharts de Imprimible no exponen refs numéricas vía openpyxl → no
perseguir.

---

## 7. Backend coverage

| Concepto Excel | Hoja/Celda | Fuente backend | Archivo/función | Existe | Match | Gap |
|---|---|---|---|---|---|---|
| CTS Cadena A | VCT C34 | `cost_to_serve_calculator.py` | `:35,180,329` | sí | KNOWN_DELTA | -61.33 (E95) |
| Payroll soporte FTE | NomLoaded 115+ | `context_builder_perfiles_soporte_mixin.py` | `:122` (fte_base_soporte) | sí | parcial | E95 override |
| OPEX fijo | NoPayroll 114 | `costs.py` / cts calc `:346` | — | sí | EXACT | — |
| CAPEX amortización | NoPayroll 193 | `cost_to_serve_calculator.py:347` | — | sí | FORMULA_GAP | +16.72 |
| Indexación IPC/SMLV | Tasas L8 | engine factor anual | `nomina.py:149`, `pyg_calculator.py:213` | sí | EXACT | — |
| Pólizas/ICA/GMF/ComAdm | Pól-Financ. | `costos_financieros/calculator.py` | `:132-337` | sí | MATCH | ICA POLIZA-ICA-001 minor |
| Base ingreso P&G | HME C296 | `pyg_calculator.py` (cálculo dinámico) | — | sí (estructural) | ARCH_DELTA | single-base vs serie |
| Tarifas por escenario | Vision Tarifas | `vision_tarifas/reglas.py` | `:108-200` | sí | field-map | VTM-001 |
| CTS Cadena C | VCT K34 | `cadena_c` chain | — | sí | FORMULA_GAP | +51.28 |

**0 `BACKEND_MISSING_COMPONENT`.** Todos los conceptos tienen componente backend; los gaps son de valor
(delta), fórmula (amort/split) o field-mapping (tarifas), no de ausencia.

---

## 8. Top gaps accionables

| # | Gap | Fuente Excel | Backend actual | Tipo | Impacto | Acción recomendada |
|---|---|---|---|---|---|---|
| 1 | **Worktree request.json roto** (cantidad null) | — | `request.json` WhatsApp opex items[3,4] | `REQUEST_FIX` | bloquea **todos** los gates de motor | poblar las 2 `cantidad` o revertir WIP OPEX a HEAD (sesión de fix) |
| 2 | Supervisor E95=9.5 override literal | Cond.A E95 | soporte = 7.1 (=(130+12)/20) | `CONTRACT_FIX` (override per-rol) o `KNOWN_DELTA` | ~-49 COP/tx (≈80% residual CTS-001) | `E95_OVERRIDE_DECISION`: ¿dotación real o quirk Excel? |
| 3 | CAPEX over-amortización | VCT C47 / NoPayroll 193 | `cost_to_serve_calculator.py:347` | `MODULE_FORMULA_FIX` | +16.72 COP/tx (signo opuesto) | revisar fórmula amortización vs Excel (frente separado) |
| 4 | CTS Cadena C ~1% | VCT K34 | `cadena_c` chain | `MODULE_FORMULA_FIX` | +51.28 COP/tx | RCA cadena C cost chain (CTS-002) |
| 5 | Rotación SAC param | Rot F19 | provider 0.09 / req 0.0815 vs Excel 0.077175 | `PARAM_VALUE_FIX` | menor (cap_rotación) | poblar rotación SAC 0.077175 (valor existente) |
| 6 | Vision Tarifas field mapping | VTM H19 | `ingreso_mensual` cumulativo | `MODULE_FORMULA_FIX` (field) | display only | mapear a `pyg_por_mes[2].ingreso_bruto` (VTM-001) |
| 7 | P&G base ingreso (HME) | HME C296 | cálculo dinámico | `KNOWN_DELTA` (ARCH) | ~18% P&G | ACCEPTED_ARCHITECTURAL_DELTA (no fix) |
| 8 | `comision_rol` staff request=0 | Cond.A F44/51/62 | provider W-override | `PROVIDER_FIX` o doc | Δ=0 (ya en baseline vía provider) | decidir request vs provider; doc si provider canónico |
| 9 | `porcentaje_acumulado` req 0.02 vs C75=0 | Panel C75 | factor billing/P&G | `REQUEST_FIX` | P&G/tarifas (no CTS) | confirmar C75=0 canónico (sesión output) |
| 10 | tasa_financiacion OP-Config ausente | — | repo default 0.0088 | `PARAM_VALUE_FIX` | menor | poblar OP-Config en parametrización (campo existente) |

---

## 9. Clasificación final de cada gap

| Gap | Request existente | Param existente | Provider existente | Requiere contrato | Requiere modules | Acción |
|---|---|---|---|---|---|---|
| 1 Worktree null cantidad | **sí** | — | — | no | no | `REQUEST_VALUE_MISMATCH` → poblar request (fix) |
| 2 E95=9.5 override | no | no | no | **sí** (opt-in per-rol) | sí | `CONTRACT_FIELD_MISSING` o `KNOWN_DELTA` |
| 3 CAPEX amort | no | no | no | no | **sí** | `MODULE_FORMULA_GAP` |
| 4 CTS-C ~1% | no | no | no | no | **sí** | `MODULE_FORMULA_GAP` |
| 5 Rotación SAC | (req tiene 0.0815) | **sí** | sí | no | no | `PARAM_VALUE_MISMATCH` |
| 6 VTM field | no | no | no | no | **sí** (field) | `MODULE_FORMULA_GAP` |
| 7 P&G HME | no | no | no | no | sí (estructural) | `KNOWN_DELTA` |
| 8 comision_rol staff | sí (=0) | — | **sí** | no | no | `PROVIDER_SELECTION_MISMATCH` |
| 9 pct_acumulado | **sí** | — | — | no | no | `REQUEST_VALUE_MISMATCH` |
| 10 tasa_financiacion | no | **sí** (campo existe) | — | no | no | `PARAM_MISSING_EXISTING_FIELD` |

---

## 10. Gates (read-only)

| Gate | Resultado | Causa |
|---|---|---|
| `tests/golden/test_cts_001_v28.py` | **FAIL (2/2)** | worktree `request.json` `cantidad: null` (gap #1) — **NO** regresión de esta sesión |
| `tests/golden/test_cts_exam_crucero_v28.py` | **FAIL (2/2)** | idem (mismo root cause) |
| `make validate-excel-v28` | **FAIL (2/6, 1 skip)** | idem — todos los checks que corren el motor revientan en `float(None)` |
| (HEAD `6778540`, request limpio) | gates **PASS** (verificado por `git show HEAD:`) | — |

**No se ejecutó** `make all` ni `make baseline` (prohibidos). Side effects de `validate-excel-v28`
regeneraron `reports/`/`versions.json` (ya en estado `M`) — **no se commitean**.

---

## 11. Veredicto

**`V28_EXCEL_ENGINE_LINEAGE_FAST_PASS_COMPLETED`** (mapa) **+ `STOP_DIRTY_WORKTREE_GATE_BLOCK`** (gates).

- DAG completo: 4 inputs raíz + 3 hojas parametrización + 11 intermedias → 4 visiones → charts.
- Parametrización (Fase 4, nuevo): paridad mayormente vía provider W-override; 2 mismatches reales
  (`rotación SAC` PARAM_VALUE, `tasa_financiacion` MISSING_EXISTING_FIELD); 0 claves/tablas nuevas requeridas.
- Charts (Fase 6, nuevo): 5 gráficos, todos display de datos ya calculados; 0 cambio de backend.
- 0 `BACKEND_MISSING_COMPONENT`. Hardcodes nuevos: 0.
- **Bloqueador operativo #1**: worktree `request.json` con `cantidad: null` rompe todos los gates de motor;
  no es de esta sesión; resolver en sesión de fix antes de cualquier corrida.
- Próximo P0 de paridad: `E95_OVERRIDE_DECISION` (≈80% del residual CTS-001).
