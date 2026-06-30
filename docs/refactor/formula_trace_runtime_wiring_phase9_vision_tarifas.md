# FORMULA_TRACE_RUNTIME_WIRING_PHASE9_VISION_TARIFAS

## Objetivo

Evaluar si VisionTarifasCalculator requiere conexión de FORMULA_ID con trazabilidad runtime.

## Contexto

PHASE1-PHASE4, PHASE6-PHASE7 completadas. PHASE5 (Costos Totales), PHASE8 (Cost To Serve) omitidas por falta de _audit_trace(). PHASE9 evalúa VisionTarifasCalculator:

1. TraceEntry.formula_ids ya existe (campo interno, no serializado)
2. AuditTracer.entry() ya acepta formula_ids
3. Patrón de wiring validado en 6 calculadores con cero drift

## Evaluación

### Naturaleza de VisionTarifasCalculator

VisionTarifasCalculator **contiene lógica de cálculo propia** (cálculo de tarifas por canal, facturación, componentes fijo/variable). Produce `ResultadoVisionTarifas` con múltiples métricas.

**PERO:** No tiene `_audit_trace()` existente.

Únicamente posee:
- `_logger.info()` [VT_TRACE] en líneas 151-160, 171-175 (traza de escenarios)
- `_logger.warning()` en línea 361 (advertencia de inversiones)
- `_logger.info()` [VISION_BUILD] en líneas 479-485 para observabilidad (structure log)
- Sin `_audit_trace()` definido en el método principal `calcular()`

### Criterio de PHASE1-7

Las PHASES 1-7 agregaron formula_ids a **traces existentes** sin crear nuevos:

> "Agregar formula_ids en trazas internas donde ya existan puntos naturales (_audit_trace)."

VisionTarifasCalculator no cumple este criterio: no tiene un trace `_audit_trace()` existente.

## Decisión

**PHASE9 se omite — VisionTarifasCalculator no tiene _audit_trace() existente**.

### Razones

1. **Sin trace existente**: `_logger.info()` es observabilidad, no trazabilidad de auditoría (`_audit_trace()`)
2. **Viola criterio PHASE1-7**: crear un trace nuevo contradiría el patrón establecido
3. **Riesgo innecesario**: crear un nuevo punto de auditoría cambiaría la estructura JSON interna sin precedente en el patrón
4. **Complejidad**: el método `calcular()` es extenso (500+ líneas) con múltiples puntos de decisión; agregar trace exigiría identificar UN ÚNICO punto significativo o múltiples, lo cual requiere análisis más profundo

### Alternativa futura (si se necesita)

Si en el futuro se desea auditar el cálculo de Vision Tarifas de forma explícita (diferente del logger.info), se puede:
1. Crear un `_audit_trace()` DOCUMENTADO Y SEPARADO con propósito específico
2. Agregar los 13 FORMULA_ID en ese momento
3. NO como parte de FORMULA_TRACE_RUNTIME_WIRING, sino como iniciativa de trazabilidad de Tarifas

## Validación

**Test Results (sin cambios de código):**

| Suite | Resultado |
|---|---|
| `test_formula_id_guardrails.py` | 8/8 ✅ |
| `test_channel_name_independence.py` | 8/8 ✅ |
| `test_baseline_formula_snapshot_v1.py` | 5/5 ✅ |
| `test_baseline_formula_snapshot_cadena_c_v1.py` | 5/5 ✅ |
| `tests/golden/` | 58/58 ✅ |
| **Total** | **84/84 ✅** |

**Cero drift — No changes made to VisionTarifasCalculator**

---

**Status:** PHASE9 OMITIDO — VisionTarifasCalculator no tiene _audit_trace() existente.

**Cobertura actual (6/12):**
- ✅ NoPayrollCalculator (PHASE1)
- ✅ CadenaBCalculator (PHASE2)
- ✅ CadenaCCalculator (PHASE3)
- ✅ CostosFinancierosCalculator (PHASE4)
- ⏭ CostosTotalesCalculator (omitido: orquestador sin trace)
- ✅ PyGCalculator (PHASE6)
- ✅ KPIsCalculator (PHASE7)
- ⏭ CostToServeCalculator (omitido: sin _audit_trace)
- ⏭ VisionTarifasCalculator (omitido: sin _audit_trace)

**Próximos candidatos con _audit_trace() existente:**
- VisionPyGBuilder (PHASE10) — revisar
- VisionImprimibleBuilder (PHASE11) — revisar

---

**Decisión validada:** Mantener criterio PHASE1-7 = solo agregar formula_ids a _audit_trace() existentes, nunca crear nuevos puntos de auditoría.
