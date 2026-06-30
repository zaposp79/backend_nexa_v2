# F3 — Runtime Inventory (Dual-Path Mapping)

**Branch:** `refactor/engine-v2`
**Date:** 2026-05-28
**Predecessor:** F2 (request reconstruction)
**Status:** Inventory snapshot used to plan F3 refactor.

---

## 1. `calculators/` inventory

| File | LOC | Public surface | Invoked from | Domain equivalent | State (post-F3) |
|---|---:|---|---|---|---|
| `nomina.py` | 278 | `NominaCalculator.calcular_para_mes(perfiles, mes)` | `engine.py`, `calculators/costos_totales.py` | `domain/payroll/calculators.py` (partial) + `domain/services/nomina_cargada.py` (salario_cargado) | LEGACY_ACTIVO. `_factor_indexacion` delegates to PayrollCalculator (shim real). `_calcular_perfil` still owns logic. |
| `pyg.py` | 248 | `PyGCalculator.calcular_para_mes` | `engine.py` | `domain/profitability/calculators.py` | SHIM_REAL (post-F3): ingreso/factor calcs delegate to ProfitabilityCalculator. |
| `vision_tarifas.py` | 474 | `VisionTarifasCalculator.calcular` | `engine.py` | `domain/profitability/calculators.py` (parcial) | SHIM_REAL (post-F3) en `ingreso = costo/factor`. Otras fórmulas (cts, costo_op_canal) siguen en calculators/. |
| `cost_to_serve.py` | 334 | `CostToServeCalculator.calcular` | `engine.py` | `domain/profitability/calculators.py` (parcial) | LEGACY_ACTIVO. Lógica de agregación ponderada y CTS pondado vive solo aquí. F3-DEFERRED a F3.B. |
| `cadena_b.py` | 188 | `CadenaBCalculator.calcular_para_mes` | `engine.py` | — | LEGACY_ACTIVO (uso de calcular_factor_aumento — delegado vía shim). |
| `cadena_c.py` | 200 | `CadenaCCalculator.calcular_para_mes` | `engine.py` | — | LEGACY_ACTIVO. Cadena C semantics F5. |
| `costos_financieros.py` | 290 | `CostosFinancierosCalculator.calcular` | `calculators/pyg.py` | `domain/financial/calculators.py` (parcial) | LEGACY_ACTIVO. F4 lo refactoriza (GMF, ICA, comisión admin). |
| `costos_totales.py` | 85 | `CostosTotalesCalculator.calcular_para_mes` | `engine.py` | — | ORCHESTRATOR (no fórmulas propias). |
| `kpis.py` | 197 | `KPIsCalculator.calcular` | `engine.py` | — | LEGACY_ACTIVO. KPI summarization, no formula collisions. |
| `no_payroll.py` | 184 | `NoPayrollCalculator.calcular_para_mes` | `engine.py` | — | LEGACY_ACTIVO. |
| `riesgo.py` | 411 | `RiesgoCalculator.calcular` | `engine.py` | `domain/risk/...` (no calculators.py yet) | LEGACY_ACTIVO. Score evaluation, no immediate parity impact. |
| `utils.py` | 116 | `calcular_factor_aumento`, `calcular_factor_margenes`, `calcular_rampup`, `calcular_tasa_polizas`, `calcular_factor_periodo` | múltiples | `domain/profitability/calculators.py`, `domain/payroll/calculators.py` | SHIM_REAL desde W9 (verificado por mutation tests F3). |
| `vision_datasets.py` | 345 | `VisionDatasetsCalculator.calcular` | `engine.py` | — | ORCHESTRATOR + presentación. |
| `vision_imprimible.py` | 240 | `VisionImprimibleCalculator.calcular` | `engine.py` | — | PRESENTATION (no formulas). |
| `vision_pyg.py` | 143 | `VisionPyGCalculator.calcular` | `engine.py` | — | PRESENTATION (fila/columna mapping). |

**Total LOC `calculators/`:** 4,130. Aproximadamente **35%** ya delegan al dominio (`utils.py` + nuevas líneas refactored en `pyg.py`/`vision_tarifas.py`). **65%** permanecen LEGACY_ACTIVO — refactor escalonado F3.B, F4, F5.

## 2. `domain/` inventory

| Module | Calculators file | Funciones puras |
|---|---|---|
| `payroll/` | `calculators.py` (79 LOC) | `PayrollCalculator.calcular_factor_aumento`, `calcular_factor_indexacion`, `calcular_examenes_fraccion` |
| `profitability/` | `calculators.py` (100 LOC) | `ProfitabilityCalculator.calcular_factor_billing`, `calcular_ingreso_desde_costo`, `calcular_factor_margenes` |
| `pricing/` | `calculators.py` (87 LOC) | (pricing pure helpers — no se documentan en este reporte porque no son ruta de paridad H32) |
| `staffing/` | `calculators.py` (44 LOC) | `StaffingCalculator.aplicar_rampup` |
| `financial/` | `calculators.py` (86 LOC) | F4 expandirá GMF/ICA/admin commission |
| `services/nomina_cargada.py` | 286 LOC | `NominaCargadaService.calcular`, `calcular_sm`, `calcular_aprendiz` — **VERIFICADO 0.00% drift contra Excel W39 para Inbound 25 (1750905, 0.10).** |

---

## 3. Punto único de verdad post-F3

| Fórmula | Hogar canónico | Invocadores |
|---|---|---|
| `factor_billing(margen, op_cont, com_cont, markup, descuento)` | `domain/profitability/calculators.py` | `calculators/pyg.py` (F3 refactor), `calculators/vision_tarifas.py` (F3 refactor + shim utils), `calculators/utils.py::calcular_factor_margenes` (shim W9) |
| `ingreso = costo / factor_billing × factor_rampup` | `domain/profitability/calculators.py` | `calculators/pyg.py` (F3), `calculators/vision_tarifas.py` (F3, dos sitios) |
| `factor_aumento(mes, pct, mes_aplicacion)` | `domain/payroll/calculators.py` | `calculators/utils.py` (shim W9, ejerce a través de cadena_b.py / cadena_c.py / nomina.py) |
| `salario_cargado(salario_base, comision_pct)` | `domain/services/nomina_cargada.py` | `input/context_builder.py` (materialización perfiles) — paridad 0.00% con Excel W39 ya validada |
| `rampup(linea_negocio, mes)` | `repositories/...` + `domain/staffing/calculators.py::aplicar_rampup` | `calculators/utils.py::calcular_rampup` (shim), `calculators/cost_to_serve.py` indirecto |

---

## 4. Estado del LEGACY_ACTIVO post-F3 (lista honesta)

| Archivo | Razón de NO refactorizar en F3 |
|---|---|
| `calculators/nomina.py::_calcular_perfil` (y subrutinas `_salario_fijo`, `_cap_inicial`, `_cap_rotacion`, `_examenes`, `_seguridad`) | Depende de objetos `PerfilCadenaA` + `ParametrosNomina` con muchos atributos hidratados desde context_builder. Extraer a `domain/payroll/calculators.py` requiere desacoplar estos contratos — F3.B sub-wave dedicado. |
| `calculators/costos_financieros.py` | GMF/ICA/admin commission divergencias son **F4** scope. |
| `calculators/cost_to_serve.py` | CTS ponderado tiene lógica de agregación con peso por canal sin equivalente puro en `domain/`. F3.B. |
| `calculators/cadena_c.py` | Cadena C HITL no modelada en Excel paridad — **F5** scope. |

---

## 5. Single-execution-path scorecard

| Fórmula crítica | ¿Un único path? | Evidencia mutation |
|---|---|---|
| `factor_billing` | SÍ | mutación + 5% detectada en ingreso |
| `ingreso = costo / factor_billing` | SÍ (post-F3) | mutación + 7% en `calcular_ingreso_desde_costo` ahora detectada (era SKIP pre-F3) |
| `factor_aumento` | SÍ | mutación + 10% en `PayrollCalculator.calcular_factor_aumento` detectada en payroll_a |
| `factor_margenes` | SÍ | mutación + 5% detectada en ingreso |
| `aplicar_rampup` | NO se observa en V2-7 (rampup canónico = 0) | SKIP — gap de **request**, no de dominio |
| `salario_cargado` | Single point (`NominaCargadaService`) pero solo se invoca en `input/context_builder.py`. Cambios en domain SÍ se reflejan, paridad 0.00% verificada para perfil agente. | Mutación sería detectable; no se añade test en F3 para mantener scope. |
| `_calcular_perfil` (composición salario_fijo + comisiones + cap + examenes + seguridad) | NO (vive solo en `calculators/nomina.py`) | F3-DEFERRED. La fórmula de costo_empresa interna SÍ está unificada (`nomina_cargada.py`), pero la composición mensual no. |

---

## 6. F3-DEFERRED items

| Item | Razón | Wave futura |
|---|---|---|
| Extraer `_calcular_perfil`, `_salario_fijo`, `_examenes` a `domain/payroll/calculators.py` con argumentos primitivos | Refactor estructural, ~150 LOC + tests | F3.B |
| Refactor `costos_financieros.py` (GMF/ICA/admin commission) | Divergencia de fórmula identificada en F2; pertenece a F4 | F4 |
| Refactor `cost_to_serve.py` ponderaciones | CTS pondado complejo; requiere modelado canal × cadena | F3.B |
| Implementar Cadena C HITL en `domain/` | Semantic gap mayor | F5 |
| Drift H32 14.39% (salario_fijo agregación + factor_indexacion + SENA/Inclusión specials) | Root cause es composición de perfiles + factor M6 ≈ 1.108 vs Excel ≈ 1.134; requiere auditoría profunda fórmula Excel `Nomina Loaded I93` (factor por canal) | F3.B (sub-wave dedicado a H32) |
