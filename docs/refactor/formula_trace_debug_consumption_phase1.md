# TRACE_DEBUG_CONSUMPTION_PHASE1

**Fecha:** 2026-06-06  
**Status:** ✅ COMPLETADO  
**Objetivo:** Crear utilidad interna para consultar audit_trace por FORMULA_ID, demostrando que la trazabilidad está operativa sin cambios públicos

---

## Objetivo

Proporcionar un **query helper interno** que permita consultar y verificar que los FORMULA_ID conectados en FORMULA_TRACE_RUNTIME_WIRING PHASE1-7 están almacenados y son accesibles en runtime mediante el `AuditTracer` thread-local, sin impactar:

- ✅ Cálculos públicos (PricingResult, KPIs, visiones)
- ✅ Contratos de API (ApiResponse, campos públicos)
- ✅ Snapshots y baselines
- ✅ Fórmulas de negocio

---

## Contexto

FORMULA_TRACE_RUNTIME_WIRING PHASE1-11 ha completado:
- ✅ 6 calculadores wired con 50 FORMULA_ID
- ✅ 5 módulos omitidos con justificación arquitectónica
- ✅ TraceEntry.formula_ids existe como campo interno no serializado
- ✅ Cero drift en 84/84 tests

**Ahora:** Demostrar que estos FORMULA_ID son **consultables en runtime**.

---

## Solución Implementada

### Utilidad Interna: `collect_formula_ids_by_calculator()`

**Ubicación:** `tests/refactor/test_formula_trace_runtime_query.py`

**Propósito:** Query helper para acceder a FORMULA_ID almacenados en `TraceEntry.formula_ids` durante ejecución de simulación.

```python
def collect_formula_ids_by_calculator(tracer) -> dict[str, list[str]]:
    """
    Extrae FORMULA_ID internos de las entradas de audit_trace,
    agrupadas por calculador.
    
    Returns:
        {"NO_PAYROLL": [...], "CADENA_B": [...], ...}
    """
    by_calc: dict[str, set[str]] = defaultdict(set)
    for entry in tracer.entries:
        if entry.formula_ids:
            for fid in entry.formula_ids:
                prefix = fid.split(".")[0] if "." in fid else fid
                by_calc[prefix].add(fid)
    return {k: sorted(list(v)) for k, v in sorted(by_calc.items())}
```

**Características:**
- ✅ Accede a campo interno `TraceEntry.formula_ids` (no serializado en JSON)
- ✅ Agrupa por prefijo (NO_PAYROLL, CADENA_B, etc.)
- ✅ Retorna diccionario ordenado y accesible para assertions
- ✅ Totalmente INTERNAL — nunca exponible en HTTP ni persistencia pública

### Uso en Tests

**Patrón estándar:**

```python
with audit_context(enabled=True, simulation_id="test_id") as tracer:
    resultado = NexaPricingEngine().calcular(ctx)

# Consultar FORMULA_ID internos
formula_ids_dict = collect_formula_ids_by_calculator(tracer)

# Verificar presencia
assert "NO_PAYROLL" in formula_ids_dict
assert "CADENA_B" in formula_ids_dict
# ...

# Verificar exclusión de JSON público
exported = export_audit_trace(tracer)
for entry in exported["entries"]:
    assert "formula_ids" not in entry  # NO debe estar
```

---

## Tests Creados

### Archivo: `tests/refactor/test_formula_trace_runtime_query.py`

**8 tests ejecutados — 8/8 ✅ PASS**

#### Clase: TestFormulaTraceRuntimeQuery (Crítico)

1. **test_baseline_simulation_with_audit_context_enabled**
   - Verifica que una simulación baseline ejecuta exitosamente con auditoría activada
   - Valida: `len(tracer.entries) > 0`

2. **test_formula_ids_queryable_by_calculator** ✅ CRÍTICO
   - Ejecuta simulación baseline
   - Consulta FORMULA_ID por calculador
   - Verifica presencia de cada categoría wired:
     - ✅ NO_PAYROLL (PHASE1)
     - ✅ CADENA_B (PHASE2)
     - ✅ CADENA_C (PHASE3)
     - ✅ COSTOS_FINANCIEROS (PHASE4)
     - ✅ PYG (PHASE6)
     - ✅ KPIS (PHASE7)

3. **test_each_calculator_has_expected_formula_ids** ✅ CRÍTICO
   - Verifica conteo mínimo de FORMULA_ID por calculador
   - NO_PAYROLL: ≥3 IDs
   - CADENA_B: ≥7 IDs
   - CADENA_C: ≥8 IDs
   - COSTOS_FINANCIEROS: ≥8 IDs
   - PYG: ≥9 IDs
   - KPIS: ≥15 IDs
   - **Total: 50 FORMULA_ID verificados**

4. **test_formula_ids_not_in_exported_json** ✅ CRÍTICO
   - Exporta tracer a JSON (como se usaría en persistencia)
   - Verifica que `formula_ids` NO aparece en ninguna entrada
   - **Confirma:** JSON público intacto, campo interno excluido

5. **test_pricing_result_contract_unchanged** ✅ CRÍTICO
   - Verifica que PricingResult no tiene nuevos campos públicos
   - Valida estructura intacta (kpis, pyg_por_mes, visiones, cost_to_serve)
   - **Confirma:** Contratos públicos sin cambios

#### Clase: TestFormulaTraceDebugQueries (Debugging)

6. **test_print_formula_id_summary**
   - Imprime resumen formateado de FORMULA_ID encontrados
   - Ayuda a visualizar cobertura de trazabilidad
   - Ejemplo de output:
     ```
     FORMULA_ID Runtime Query Results
     ==============================
     Total trace entries: 28
     Calculators with FORMULA_ID wiring:
       CADENA_B: 7 IDs
         - COMPONENTE_FIJO_B
         - COMPONENTE_VARIABLE_B
         - DESCUENTO_B
         ... and 4 more
       CADENA_C: 8 IDs
       ...
     ```

#### Clase: TestFormulaTraceQueryEdgeCases (Robustez)

7. **test_query_helper_handles_empty_traces**
   - Valida que helper no falla con tracer vacío
   - Retorna `{}`

8. **test_query_helper_handles_mixed_entries**
   - Valida que helper tolera mezcla de entradas con/sin formula_ids
   - Agrupa correctamente solo las que tienen IDs

---

## Validación Final ✅

### Test Results

| Suite | Resultado | Detalles |
|---|---|---|
| `test_formula_trace_runtime_query.py` | 8/8 ✅ | Query helper + runtime verification |
| `test_formula_id_guardrails.py` | 8/8 ✅ | Validación de sintaxis FORMULA_ID |
| `test_baseline_formula_snapshot_v1.py` | 5/5 ✅ | Snapshots baseline V1 |
| `test_baseline_formula_snapshot_cadena_c_v1.py` | 5/5 ✅ | Snapshots Cadena C |
| `tests/golden/` | 58/58 ✅ | Golden tests (paridad) |
| **TOTAL** | **84/84 ✅** | Cero drift |

### Confirmaciones

✅ **FORMULA_ID consultables:** collect_formula_ids_by_calculator() recupera 50 IDs en 6 categorías  
✅ **JSON público intacto:** formula_ids excluido de export via to_dict()  
✅ **Contratos sin cambios:** PricingResult structure intacta  
✅ **Cero drift:** Todos los tests pasan sin cambios esperados  

---

## Limits y Restricciones

### In Scope ✅

- Query helper **INTERNO SOLAMENTE** — en test suite, nunca en código productivo
- Acceso a `TraceEntry.formula_ids` internos vía `tracer.entries`
- Validación de presencia/ausencia en JSON serializado
- Debugging y auditoría interna

### Out of Scope ❌

- **NO crear endpoints HTTP** para exponer FORMULA_ID (fuera de alcance)
- **NO agregar formula_ids a API responses** (contratos intactos)
- **NO persistir formula_ids en storage público** (solo en memoria, interno)
- **NO cambiar cálculos, fórmulas ni snapshots**

---

## Uso Futuro de esta Utilidad

Si en el futuro se necesita auditar o debuggear trazabilidad de fórmulas:

1. **Desde tests:** Importar `collect_formula_ids_by_calculator` desde `test_formula_trace_runtime_query.py`
2. **En desarrollo:** Activar `audit_context(enabled=True)` y ejecutar simulación
3. **Exportar:** Usar `export_audit_trace(tracer)` para JSON (sin formula_ids)
4. **Documentar hallazgos:** Agregar casos de test adicionales si se detectan gaps

**Ejemplo para extensión futura:**

```python
# Si alguien descubre que CostToServeCalculator necesita traceabilidad
# (actualmente omitido porque no tiene _audit_trace() existente):
# 1. Crear PHASE12 para agregar trace a CostToServe
# 2. Agregar FORMULA_ID al nuevo trace
# 3. Validar presencia con collect_formula_ids_by_calculator()
```

---

## Archivos Creados/Modificados

| Archivo | Tipo | Cambio |
|---|---|---|
| `tests/refactor/test_formula_trace_runtime_query.py` | NUEVO | 8 tests + query helper |
| `docs/refactor/formula_trace_debug_consumption_phase1.md` | NUEVO | Este documento |

---

## Conclusión

**TRACE_DEBUG_CONSUMPTION_PHASE1 — COMPLETADO**

La utilidad interna demuestra que:

1. ✅ FORMULA_ID wiring de PHASE1-7 está **operativo y consultable en runtime**
2. ✅ TraceEntry.formula_ids se **almacena correctamente en memoria interna**
3. ✅ Campo interno se **excluye de JSON público** (backward compatible)
4. ✅ Contratos públicos **permanecen intactos** (cero impacto)
5. ✅ **Cero drift** en 84/84 tests (validación completa)

**La trazabilidad de fórmulas está lista para auditoría y reproducibilidad interna.**

Para futuras iniciativas:
- **Query helper** disponible en `test_formula_trace_runtime_query.py` para debugging
- **Patrón validado** para acceder a trazas internas sin exponerlas públicamente
- **Extensible:** Fácil agregar más verificaciones si se amplía wiring futuro

---

**Status:** ✅ **CERRADO — 2026-06-06**  
**Responsable:** claude-code (coordinador técnico)  
**Proxima revisión:** Por demanda de auditoría o nuevas iniciativas de trazabilidad
