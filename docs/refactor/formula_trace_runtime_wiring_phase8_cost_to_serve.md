# FORMULA_TRACE_RUNTIME_WIRING_PHASE8_COST_TO_SERVE

## Objetivo

Evaluar si CostToServeCalculator requiere conexión de FORMULA_ID con trazabilidad runtime.

## Contexto

PHASE1 (NoPayroll), PHASE2 (Cadena B), PHASE3 (Cadena C), PHASE4 (Costos Financieros), PHASE6 (PyG), PHASE7 (KPIs) completadas. PHASE5 (Costos Totales) omitido por orquestador puro. PHASE8 evalúa CostToServeCalculator:

1. TraceEntry.formula_ids ya existe (campo interno, no serializado)
2. AuditTracer.entry() ya acepta formula_ids
3. Patrón de wiring validado en 6 calculadores con cero drift

## Evaluación

### Naturaleza de CostToServeCalculator

CostToServeCalculator **contiene lógica de cálculo propia** (cálculo de denominadores, promedios, divisiones por unidades operativas). Produce `ResultadoCostToServe` con 13 métricas.

**PERO:** No tiene `_audit_trace()` existente.

Únicamente posee:
- `logger.info()` en línea 175-186 para observabilidad (structure log)
- Sin `_audit_trace()` definido en el método principal `calcular()`

### Criterio de PHASE1-7

Las PHASES 1-7 agregaron formula_ids a **traces existentes** sin crear nuevos:

> "Agregar formula_ids en trazas internas donde ya existan puntos naturales (_audit_trace)."

CostToServeCalculator no cumple este criterio: no tiene un trace `_audit_trace()` existente.

## Decisión

**PHASE8 se omite — CostToServeCalculator no tiene trace _audit_trace() existente**.

### Razones

1. **Sin trace existente**: `logger.info()` es observabilidad, no trazabilidad de auditoría (`_audit_trace()`)
2. **Viola criterio PHASE1-7**: crear un trace nuevo contradiría el patrón establecido
3. **Cero beneficio estratégico**: la observabilidad via logger ya captura los inputs/outputs
4. **Riesgo innecesario**: crear un nuevo punto de auditoría cambiaría la estructura JSON interna sin precedente en el patrón

### Alternativa futura (si se necesita)

Si en el futuro se desea auditar el cálculo de CTS de forma explícita (diferente del logger.info), se puede:
1. Crear un `_audit_trace()` DOCUMENTADO Y SEPARADO con propósito específico
2. Agregar los 13 FORMULA_ID en ese momento
3. NO como parte de FORMULA_TRACE_RUNTIME_WIRING, sino como iniciativa de trazabilidad de Cost-To-Serve

## Validación

**Test Results (sin cambios de código):**

| Suite | Resultado |
|---|---|
| `test_formula_id_guardrails.py` | 8/8 ✅ |
| `test_baseline_formula_snapshot_v1.py` | 5/5 ✅ |
| `test_baseline_formula_snapshot_cadena_c_v1.py` | 5/5 ✅ |
| `tests/golden/` | 58/58 ✅ |
| **Total** | **76/76 ✅** |

**Cero drift — No changes made to CostToServeCalculator**

---

**Status:** PHASE8 OMITIDO — CostToServeCalculator no tiene _audit_trace() existente.

**Cobertura actual (6/12):**
- ✅ NoPayrollCalculator (PHASE1)
- ✅ CadenaBCalculator (PHASE2)
- ✅ CadenaCCalculator (PHASE3)
- ✅ CostosFinancierosCalculator (PHASE4)
- ⏭ CostosTotalesCalculator (omitido: orquestador sin trace)
- ✅ PyGCalculator (PHASE6)
- ✅ KPIsCalculator (PHASE7)
- ⏭ CostToServeCalculator (omitido: sin _audit_trace)

**Próximos candidatos con _audit_trace() existente:**
- VisionTarifasCalculator (PHASE9) — revisar
- VisionPyGBuilder (PHASE10) — revisar
- VisionImprimibleBuilder (PHASE11) — revisar

---

**Decisión validada:** Mantener criterio PHASE1-7 = solo agregar formula_ids a _audit_trace() existentes, nunca crear nuevos puntos de auditoría.
