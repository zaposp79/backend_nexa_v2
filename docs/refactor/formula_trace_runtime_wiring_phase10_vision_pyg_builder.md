# FORMULA_TRACE_RUNTIME_WIRING_PHASE10_VISION_PYG_BUILDER

## Objetivo

Evaluar si VisionPyGBuilder requiere conexión de FORMULA_ID con trazabilidad runtime.

## Contexto

PHASE1-4, PHASE6-7 completadas. PHASE5, PHASE8, PHASE9 omitidas. PHASE10 evalúa VisionPyGBuilder:

1. TraceEntry.formula_ids ya existe (campo interno, no serializado)
2. AuditTracer.entry() ya acepta formula_ids
3. Patrón de wiring validado en 6 calculadores con cero drift

## Evaluación

### Naturaleza de VisionPyGBuilder

VisionPyGBuilder **es un builder/transformador de datos, NO un calculador**.

Responsabilidades:
- Mapear PyGMensual → VisionPyG (tabular frontend model)
- Construir filas (rows) con labels, secciones, valores, acumulados, promedios
- Agregar detalle de sub-componentes por cadena
- Construir resumen ejecutivo con cabecera del deal

**Sin lógica de cálculo propia:**
- No realiza operaciones aritméticas en datos nuevos
- Solo extrae, agrupa y transforma datos ya calculados
- No tiene `_audit_trace()` existente
- No importa `AuditTracer` ni `trace as _audit_trace`

### Criterio de PHASE1-7

Las PHASES 1-7 agregaron formula_ids a **calculadores con _audit_trace() existente**:

> "Agregar formula_ids en trazas internas de CALCULADORES donde ya existan puntos naturales (_audit_trace)."

VisionPyGBuilder no es un calculador: es un presentador/transformador. No tiene `_audit_trace()` existente.

## Decisión

**PHASE10 se omite — VisionPyGBuilder es un builder, no un calculador; sin _audit_trace() existente**.

### Razones

1. **Naturaleza arquitectónica diferente**: builder ≠ calculador
2. **Sin trace existente**: ningún `_audit_trace()` en el código
3. **Viola criterio PHASE1-7**: crear un trace nuevo contradiría el patrón (solo para calculadores con traces naturales)
4. **Cero beneficio estratégico**: el builder no contiene lógica de negocio auditable, solo transformación de datos

### Alternativa futura (si se necesita)

Si en el futuro se desea auditar la construcción de la visión P&G como unidad independiente (diferente de auditar PyGCalculator), se puede:
1. Reconceptualizar VisionPyGBuilder como "calculador de vista" (cambio arquitectónico mayor)
2. Crear un `_audit_trace()` DOCUMENTADO Y SEPARADO con propósito específico
3. NO como parte de FORMULA_TRACE_RUNTIME_WIRING, sino como iniciativa de trazabilidad de visiones

---

## Validación

**Test Results (sin cambios de código):**

| Suite | Resultado |
|---|---|
| `test_formula_id_guardrails.py` | 8/8 ✅ |
| `test_baseline_formula_snapshot_v1.py` | 5/5 ✅ |
| `test_baseline_formula_snapshot_cadena_c_v1.py` | 5/5 ✅ |
| `tests/golden/` | 58/58 ✅ |
| **Total** | **76/76 ✅** |

**Cero drift — No changes made to VisionPyGBuilder**

---

**Status:** PHASE10 OMITIDO — VisionPyGBuilder es builder (no calculador) sin _audit_trace().

**Cobertura actual (6/12 calculadores):**
- ✅ NoPayrollCalculator (PHASE1)
- ✅ CadenaBCalculator (PHASE2)
- ✅ CadenaCCalculator (PHASE3)
- ✅ CostosFinancierosCalculator (PHASE4)
- ⏭ CostosTotalesCalculator (omitido: orquestador sin trace)
- ✅ PyGCalculator (PHASE6)
- ✅ KPIsCalculator (PHASE7)
- ⏭ CostToServeCalculator (omitido: sin _audit_trace)
- ⏭ VisionTarifasCalculator (omitido: sin _audit_trace)
- ⏭ VisionPyGBuilder (omitido: builder, no calculador)

**Próximo candidato con _audit_trace() existente:**
- VisionImprimibleBuilder (PHASE11) — revisar

---

**Decisión validada:** Mantener criterio PHASE1-7 = solo agregar formula_ids a _audit_trace() existentes en CALCULADORES (no builders/transformadores).
