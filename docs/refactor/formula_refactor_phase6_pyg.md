# FORMULA_REFACTOR_PHASE6_PYG

## 1. Objetivo

Agregar trazabilidad mínima (clase interna `FORMULA_ID`) a los tres archivos del módulo P&G (Capa 9-10 del pipeline), sin alterar ningún output, contrato público ni lógica de negocio. Continuación directa del patrón establecido en PHASE1-5.

## 2. Alcance

| Archivo | Capa | Responsabilidad |
|---|---|---|
| `modules/pyg/services/pyg_calculator.py` | Capa 9 | Estado de Resultados mensual |
| `modules/pyg/services/kpis_calculator.py` | Capa 10 | KPIs deal-wide |
| `modules/pyg/builders/vision_pyg_builder.py` | Builder | Transforma PyGMensual → VisionPyG |

**NO tocado:** `modules/vision_pyg/` (legacy, dead code — confirmado).

## 3. Auditoría de bloques (TAREA 1)

### pyg_calculator.py (Capa 9)

Método principal: `calcular_mes(perfiles_cadena_a, mes, costo_mes_anterior) -> PyGMensual`
Orquestador: `calcular_contrato(perfiles_cadena_a) -> List[PyGMensual]`

Bloques identificados:
- **Factor ramp-up**: `calcular_rampup(linea_negocio, mes)` — delegado a `shared_calc.utils`
- **Costos operativos**: delegados a `CostosTotalesCalculator.calcular_para_mes()`
- **Costos financieros**: delegados a `CostosFinancierosCalculator.calcular()`
- **Factor billing por cadena**: `ProfitabilityCalculator.calcular_factor_billing()` × 3 (A, B, C con márgenes específicos)
- **Ingreso por cadena**: `ProfitabilityCalculator.calcular_ingreso_desde_costo()` × 3
- **Ingreso bruto**: suma de A + B + C
- **Imprevistos**: `panel.imprevistos × ingreso_bruto` (GAP-PYG-1)
- **Contingencias/markup/descuento**: proporcionales al ingreso_bruto
- **Acumuladores running**: `acum_ingreso_bruto`, `acum_ingreso_neto`, `acum_costo_total`, `acum_costos_financieros`, `acum_contribucion`
- **Guard**: `_mes_dentro_del_contrato(mes)` — retorna PyGMensual vacío si fuera de rango

Evaluación: bien estructurado. Métodos privados claros, audit trace existente, sin mezcla de responsabilidades.

### kpis_calculator.py (Capa 10)

Método principal: `calcular(pyg_contrato: List[PyGMensual]) -> KPIsDeal`

Bloques identificados:
- **Totales aggregation**: `_sumar_totales()` — suma ingreso_bruto, ingreso_neto, costo_total, contribucion, utilidad_neta
- **Tarifa mensual**: `_calcular_tarifa()` — costo_promedio_a + costos_financieros sobre promedio, dividido por factor_margenes
- **Facturación proyectada**: `ingreso_tarifa / factor_periodo`
- **Porcentaje utilidad**: `_pct_utilidad()` — utilidad_neta / ingreso_neto
- **Margen mínimo**: `parametrizacion.get_margen_minimo(linea_negocio)`
- **Cumplimiento**: `panel.margen >= margen_minimo`

Evaluación: bien estructurado. Tres helpers privados con responsabilidades distintas, audit trace existente.

### vision_pyg_builder.py (Builder)

Método principal: `construir(...) -> VisionPyG`
Método secundario: `_build_detalle(...) -> List[VisionPyGRowDetalle]`

Constantes de módulo:
- `_ROW_DEFINITIONS` — 25 filas Excel mapeadas con key/label/seccion/tipo/signo/attr_name/excel_row/formula
- `_DETALLE_PAYROLL_A` — 7 sub-componentes payroll Cadena A (rows 34-40)
- `_DETALLE_NO_PAYROLL_A` — 3 sub-componentes no-payroll Cadena A (rows 42-44)
- `_DETALLE_B` — 6 sub-componentes Cadena B (rows 46-54)
- `_DETALLE_C` — 7 sub-componentes Cadena C (rows 56-64)

Secciones en `construir()`:
- Estaciones de trabajo: `Σ(fte × pct_presencia)` para perfiles no-soporte
- Filas principales: loop sobre `_ROW_DEFINITIONS` con valores por mes + acumulado + promedio
- Filas detalle: delegado a `_build_detalle()` con calculadores opcionales
- Fecha fin y duración: calculadas desde `fecha_inicio` + `meses_contrato`
- `ResumenEjecutivoPyG`: header del deal desde `PanelDeControl` + KPIs
- `fechas_meses`: calendario por columna de mes

Evaluación: bien estructurado. Clara separación entre filas de resumen y filas de detalle por cadena.

## 4. Decisión de refactor (TAREA 2)

**Decisión: NO refactorizar. Solo agregar FORMULA_ID.**

Los tres archivos tienen:
- Métodos bien nombrados y aislados
- Lógica clara sin necesidad de submétodos adicionales
- Sin mezcla de responsabilidades
- Audit traces (`_audit_trace`) ya presentes en los calculadores
- Constantes de módulo bien documentadas en `vision_pyg_builder.py`

## 5. Trazabilidad mínima — FORMULA_ID agregados

### pyg_calculator.py (19 constantes)

| Constante | Valor | Descripción |
|---|---|---|
| `INGRESO_CADENA_A` | `PYG.INGRESO_CADENA_A` | costo_a / factor_billing(margen_a) × rampup |
| `INGRESO_CADENA_B` | `PYG.INGRESO_CADENA_B` | costo_b / factor_billing(margen_b) × rampup |
| `INGRESO_CADENA_C` | `PYG.INGRESO_CADENA_C` | costo_c / factor_billing(margen_c) × rampup |
| `INGRESO_BRUTO` | `PYG.INGRESO_BRUTO` | ingreso_a + ingreso_b + ingreso_c |
| `IMPREVISTOS` | `PYG.IMPREVISTOS` | panel.imprevistos × ingreso_bruto |
| `FACTOR_RAMPUP` | `PYG.FACTOR_RAMPUP` | calcular_rampup(linea_negocio, mes) |
| `FACTOR_BILLING_A` | `PYG.FACTOR_BILLING_A` | ProfitabilityCalculator.calcular_factor_billing(margen_a, ...) |
| `FACTOR_BILLING_B` | `PYG.FACTOR_BILLING_B` | ProfitabilityCalculator.calcular_factor_billing(margen_b, ...) |
| `FACTOR_BILLING_C` | `PYG.FACTOR_BILLING_C` | ProfitabilityCalculator.calcular_factor_billing(margen_c, ...) |
| `CONTINGENCIA_OP` | `PYG.CONTINGENCIA_OP` | panel.op_cont × ingreso_bruto |
| `CONTINGENCIA_COM` | `PYG.CONTINGENCIA_COM` | panel.com_cont × ingreso_bruto |
| `MARKUP_INGRESO` | `PYG.MARKUP_INGRESO` | panel.markup × ingreso_bruto |
| `DESCUENTO_INGRESO` | `PYG.DESCUENTO_INGRESO` | panel.descuento × ingreso_bruto |
| `ACUM_INGRESO_BRUTO` | `PYG.ACUM_INGRESO_BRUTO` | running total ingreso_bruto |
| `ACUM_INGRESO_NETO` | `PYG.ACUM_INGRESO_NETO` | running total ingreso_neto |
| `ACUM_COSTO_TOTAL` | `PYG.ACUM_COSTO_TOTAL` | running total costo_total |
| `ACUM_COSTOS_FINANCIEROS` | `PYG.ACUM_COSTOS_FINANCIEROS` | running total costos_financieros |
| `ACUM_CONTRIBUCION` | `PYG.ACUM_CONTRIBUCION` | running total contribucion |

### kpis_calculator.py (15 constantes)

| Constante | Valor | Descripción |
|---|---|---|
| `COSTO_MENSUAL_PROMEDIO` | `KPIS.COSTO_MENSUAL_PROMEDIO` | costo_total_contrato / meses_contrato |
| `COSTO_CADENA_A_PROMEDIO` | `KPIS.COSTO_CADENA_A_PROMEDIO` | Σ(costo_a per mes) / meses_contrato |
| `TARIFA_MENSUAL` | `KPIS.TARIFA_MENSUAL` | (costo_promedio_a + costos_fin) / factor_margenes |
| `FACTURACION_PROYECTADA` | `KPIS.FACTURACION_PROYECTADA` | ingreso_tarifa / factor_periodo |
| `FACTOR_MARGENES` | `KPIS.FACTOR_MARGENES` | calcular_factor_margenes(panel) |
| `FACTOR_PERIODO` | `KPIS.FACTOR_PERIODO` | calcular_factor_periodo(panel, parametrizacion) |
| `COSTOS_FIN_SOBRE_PROMEDIO` | `KPIS.COSTOS_FIN_SOBRE_PROMEDIO` | CostosFinancierosCalculator.calcular(costo_promedio_a) |
| `INGRESO_BRUTO_TOTAL` | `KPIS.INGRESO_BRUTO_TOTAL` | Σ ingreso_bruto per mes |
| `INGRESO_NETO_TOTAL` | `KPIS.INGRESO_NETO_TOTAL` | Σ ingreso_neto per mes |
| `COSTO_TOTAL_CONTRATO` | `KPIS.COSTO_TOTAL_CONTRATO` | Σ costo_total per mes |
| `CONTRIBUCION_TOTAL` | `KPIS.CONTRIBUCION_TOTAL` | Σ contribucion per mes |
| `UTILIDAD_NETA_TOTAL` | `KPIS.UTILIDAD_NETA_TOTAL` | Σ utilidad_neta per mes |
| `PCT_UTILIDAD_NETA` | `KPIS.PCT_UTILIDAD_NETA` | utilidad_neta_total / ingreso_neto_total |
| `MARGEN_MINIMO_REQUERIDO` | `KPIS.MARGEN_MINIMO_REQUERIDO` | parametrizacion.get_margen_minimo(linea_negocio) |
| `CUMPLE_MARGEN_MINIMO` | `KPIS.CUMPLE_MARGEN_MINIMO` | panel.margen >= margen_minimo |

### vision_pyg_builder.py (15 constantes)

| Constante | Valor | Descripción |
|---|---|---|
| `FILAS_INGRESOS` | `VISION_PYG.FILAS_INGRESOS` | Excel rows 18-27 |
| `FILAS_COSTOS_OP` | `VISION_PYG.FILAS_COSTOS_OP` | Excel rows 30-64 |
| `FILAS_COSTOS_FIN` | `VISION_PYG.FILAS_COSTOS_FIN` | Excel rows 65-70 |
| `FILAS_RESULTADOS` | `VISION_PYG.FILAS_RESULTADOS` | Excel rows 74-80 |
| `FILAS_OPERATIVO` | `VISION_PYG.FILAS_OPERATIVO` | Excel row 15 |
| `RESUMEN_EJECUTIVO` | `VISION_PYG.RESUMEN_EJECUTIVO` | ResumenEjecutivoPyG (deal header) |
| `ESTACIONES_TRABAJO` | `VISION_PYG.ESTACIONES_TRABAJO` | Σ(fte × pct_presencia) para no-soporte |
| `FECHAS_MESES` | `VISION_PYG.FECHAS_MESES` | Calendario por columna de mes |
| `DETALLE_PAYROLL_A` | `VISION_PYG.DETALLE_PAYROLL_A` | Sub-componentes payroll Cadena A (rows 34-40) |
| `DETALLE_NO_PAYROLL_A` | `VISION_PYG.DETALLE_NO_PAYROLL_A` | Sub-componentes no-payroll Cadena A (rows 42-44) |
| `DETALLE_CADENA_B` | `VISION_PYG.DETALLE_CADENA_B` | Sub-componentes Cadena B (rows 46-54) |
| `DETALLE_CADENA_C` | `VISION_PYG.DETALLE_CADENA_C` | Sub-componentes Cadena C (rows 56-64) |
| `DETALLE_FIN_POR_CADENA` | `VISION_PYG.DETALLE_FIN_POR_CADENA` | ICA/GMF/Pólizas desglosados por cadena |
| `CONTRIBUCION_POR_PUESTO` | `VISION_PYG.CONTRIBUCION_POR_PUESTO` | Excel C75 = contribucion / estaciones |
| `PROMEDIO_ACTIVOS` | `VISION_PYG.PROMEDIO_ACTIVOS` | promedio sobre meses con ingreso_neto > 0 |

**Total FORMULA_ID agregados: 49 constantes (19 + 15 + 15)**

## 6. Validación (TAREA 4)

Todos los comandos ejecutados desde directorio padre `/Users/darwin.minota.quinto/Projects/NEXA`:

```bash
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_input_contract_fix_b1.py -q
# 12 passed, 1 warning

PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_v1.py -q
# 5 passed, 1 warning

PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py -q
# 5 passed, 1 warning

PYTHONPATH=$(pwd) pytest backend_nexa/tests/golden/ -q
# 58 passed, 82 deselected, 1 warning

PYTHONPATH=$(pwd) pytest backend_nexa/tests/unit/test_vision_pyg_60m.py backend_nexa/tests/contract/test_vision_pyg_contract.py -q
# 21 passed, 29 deselected, 1 warning
```

**Total validado: 101 tests PASSED, 0 FAILED**

## 7. Cambios realizados

| Archivo | Cambio | Líneas insertadas |
|---|---|---|
| `modules/pyg/services/pyg_calculator.py` | Clase `FORMULA_ID` interna en `PyGCalculator` | +20 líneas |
| `modules/pyg/services/kpis_calculator.py` | Clase `FORMULA_ID` interna en `KPIsCalculator` | +17 líneas |
| `modules/pyg/builders/vision_pyg_builder.py` | Clase `FORMULA_ID` interna en `VisionPyGBuilder` | +17 líneas |

Cambios exclusivamente aditivos. Ningún código existente fue modificado ni eliminado.

## 8. Comparación con PHASE1-5

| Fase | Archivo | FORMULA_IDs |
|---|---|---|
| PHASE1 | `cadena_a/no_payroll.py` | ~10 |
| PHASE2 | `cadena_b/reglas.py` | ~9 |
| PHASE3 | `costos_financieros/calculators/costos_financieros_calculator.py` | ~12 |
| PHASE4 | `cadena_c/reglas.py` | ~11 |
| PHASE5 | `pyg/services/costos_totales_calculator.py` | ~10 |
| **PHASE6** | `pyg/services/pyg_calculator.py` | **19** |
| **PHASE6** | `pyg/services/kpis_calculator.py` | **15** |
| **PHASE6** | `pyg/builders/vision_pyg_builder.py` | **15** |

PHASE6 es la más amplia por abarcar 3 archivos y cubrir tanto el motor (Capas 9-10) como el builder de presentación.

## 9. Riesgo y mitigación

**Riesgo:** NINGUNO. Las constantes de `FORMULA_ID` son atributos de clase estáticos, no participan en ningún cálculo, no son referenciadas por código externo y no modifican ningún output.

**Mitigación:** 101 tests ejecutados post-cambio confirman paridad completa.

## 10. Confirmación: modules/vision_pyg/ NO tocado

`modules/vision_pyg/` es módulo legacy (dead code, confirmado en pyg_active_ownership_confirmation.md). No fue leído, modificado ni referenciado en esta fase.

## 11. Cierre y artefactos

**Estado:** CERRADO

**Artefactos generados:**
- `/backend_nexa/modules/pyg/services/pyg_calculator.py` — clase `FORMULA_ID` agregada
- `/backend_nexa/modules/pyg/services/kpis_calculator.py` — clase `FORMULA_ID` agregada
- `/backend_nexa/modules/pyg/builders/vision_pyg_builder.py` — clase `FORMULA_ID` agregada
- `/backend_nexa/docs/refactor/formula_refactor_phase6_pyg.md` — este documento

**Precondiciones satisfechas:** PHASE1-5 cerradas, gate 80/80 intacto, paridad baseline v1 + cadena_c_v1 confirmada.
