# FORMULA_TRACE_RUNTIME_WIRING_PHASE11_VISION_IMPRIMIBLE_BUILDER

## Objetivo

Evaluar si VisionImprimibleBuilder requiere conexión de FORMULA_ID con trazabilidad runtime.

## Contexto

PHASE1-4, PHASE6-7 completadas. PHASE5, PHASE8, PHASE9, PHASE10 omitidas. PHASE11 evalúa VisionImprimibleBuilder (fase final):

1. TraceEntry.formula_ids ya existe (campo interno, no serializado)
2. AuditTracer.entry() ya acepta formula_ids
3. Patrón de wiring validado en 6 calculadores con cero drift

## Evaluación

### Naturaleza de VisionImprimibleBuilder

VisionImprimibleBuilder **es un builder/compositor de datos, NO un calculador**.

Responsabilidades:
- Ensamblar VisionImprimible a partir de resultados ya calculados
- Construir 11 secciones: Ficha, Economics, Configuración, Evolución, Comparativo, Servicios, Canales, Detalles, Equipo
- Composición pura — NO recalcula nada, solo mapea y organiza datos

**Sin lógica de cálculo propia:**
- Todos los métodos son estáticos
- Solo extrae, agrupa y reorganiza datos ya calculados
- Sin `_audit_trace()` existente
- Sin import de `AuditTracer` o `trace as _audit_trace`

Comentario en código (línea 9):
> "Construir la `VisionImprimible` a partir de los resultados ya calculados por los demás calculadores del pipeline. **NO recalcula nada.**"

### Criterio de PHASE1-7

Las PHASES 1-7 agregaron formula_ids a **calculadores con _audit_trace() existente**:

> "Agregar formula_ids en trazas internas de CALCULADORES donde ya existan puntos naturales (_audit_trace)."

VisionImprimibleBuilder no es un calculador: es un compositor. No tiene `_audit_trace()` existente.

## Decisión

**PHASE11 se omite — VisionImprimibleBuilder es un builder/compositor, no un calculador; sin _audit_trace() existente**.

### Razones

1. **Naturaleza arquitectónica diferente**: builder/compositor ≠ calculador
2. **Sin trace existente**: ningún `_audit_trace()` en el código
3. **Viola criterio PHASE1-7**: crear un trace nuevo contradiría el patrón (solo para calculadores con traces naturales)
4. **Cero beneficio estratégico**: el builder no contiene lógica de negocio auditable, solo transformación de datos
5. **Composición pura documentada**: código explícitamente señala que NO recalcula (línea 9)

### Alternativa futura (si se necesita)

Si en el futuro se desea auditar el ensamblaje de la Visión Imprimible como unidad independiente, se puede:
1. Reconceptualizar VisionImprimibleBuilder como "compositor auditado" (cambio arquitectónico mayor)
2. Crear un `_audit_trace()` DOCUMENTADO Y SEPARADO con propósito específico
3. NO como parte de FORMULA_TRACE_RUNTIME_WIRING, sino como iniciativa de trazabilidad de composición

---

## Validación

**Test Results (sin cambios de código):**

| Suite | Resultado |
|---|---|
| `test_formula_id_guardrails.py` | 8/8 ✅ |
| `test_baseline_formula_snapshot_v1.py` | 5/5 ✅ |
| `test_baseline_formula_snapshot_cadena_c_v1.py` | 5/5 ✅ |
| `tests/golden/` | 58/58 ✅ |
| `test_channel_name_independence.py` | 8/8 ✅ |
| **Total** | **84/84 ✅** |

**Cero drift — No changes made to VisionImprimibleBuilder**

---

**Status:** PHASE11 OMITIDO — VisionImprimibleBuilder es compositor (no calculador) sin _audit_trace().

## Resumen de Cobertura Completa (6/12 calculadores + 4 builders omitidos + 2 orquestadores omitidos)

**Calculadores con FORMULA_ID wiring completado:**
- ✅ NoPayrollCalculator (PHASE1)
- ✅ CadenaBCalculator (PHASE2)
- ✅ CadenaCCalculator (PHASE3)
- ✅ CostosFinancierosCalculator (PHASE4)
- ✅ PyGCalculator (PHASE6)
- ✅ KPIsCalculator (PHASE7)

**Omitidos — Sin _audit_trace() existente:**
- ⏭ CostToServeCalculator (PHASE8: sin _audit_trace)
- ⏭ VisionTarifasCalculator (PHASE9: sin _audit_trace)

**Omitidos — Builders/Componentes (NO calculadores):**
- ⏭ VisionPyGBuilder (PHASE10: builder, no calculador)
- ⏭ VisionImprimibleBuilder (PHASE11: compositor, no calculador)

**Omitidos — Orquestadores puros (sin cálculo):**
- ⏭ CostosTotalesCalculator (PHASE5: orquestador sin trace)

---

## Criterio FINAL (PHASE1-11)

**Establecido y validado:**
- Agregar formula_ids **SOLO** a _audit_trace() existentes en CALCULADORES
- Nunca crear nuevos traces
- Nunca wiring en orquestadores, builders, o componentes sin cálculo propio
- Patrón probado: 6 calculadores, 4 builders omitidos, 2 orquestadores omitidos, cero drift

---

**Decisión validada:** FORMULA_TRACE_RUNTIME_WIRING secuencia completada. Cobertura de calculadores alcanzada con precisión arquitectónica.
