# FORMULA_TRACE_RUNTIME_WIRING_PHASE5_COSTOS_TOTALES

## Objetivo

Evaluar si CostosTotalesCalculator requiere conexión de FORMULA_ID con trazabilidad runtime.

## Contexto

PHASE1 (NoPayroll), PHASE2 (Cadena B), PHASE3 (Cadena C), PHASE4 (Costos Financieros) completadas. PHASE5 evalúa CostosTotalesCalculator:

1. TraceEntry.formula_ids ya existe (campo interno, no serializado)
2. AuditTracer.entry() ya acepta formula_ids
3. Patrón validado en 4 calculadores con cero drift

## Evaluación

### Naturaleza de CostosTotalesCalculator

CostosTotalesCalculator **es un orquestador puro**, no un calculador:

```python
def calcular_para_mes(self, perfiles_a, mes):
    nomina      = self._nomina.calcular_para_mes(perfiles_a, mes)
    no_payroll  = self._no_payroll.calcular_para_mes(perfiles_a, mes)
    cadena_b    = self._cadena_b.calcular_para_mes(mes)
    cadena_c    = self._cadena_c.calcular_para_mes(mes)
    
    return CostosTotalesMes(
        payroll_a    = nomina.total,
        no_payroll_a = no_payroll.total,
        costo_b      = cadena_b.total,
        costo_c      = cadena_c.total_pyg,
        costo_c_fin  = cadena_c.total,
    )
```

- **No contiene lógica de cálculo propia**: solo delega en otros calculadores
- **No tiene trace natural existente**: ningún _audit_trace()
- **No realiza transformaciones de negocio**: simple agregación de valores

### Criterio de PHASE1-4

Las PHASES 1-4 agregaron formula_ids a **traces existentes** sin crear nuevos puntos de auditoría:

> "Agregar formula_ids en trazas internas donde ya existan puntos naturales."

CostosTotalesCalculator no cumple este criterio: no tiene trace natural.

## Decisión

**PHASE5 se omite — CostosTotalesCalculator no requiere tracing**.

### Razones

1. **No es un calculador**: es un orquestador que delega todo el cálculo a otros módulos
2. **No tiene lógica de negocio**: simple lectura y reempaquet de objetos
3. **No tiene trace natural**: crear uno violaría el criterio (nuevo punto de auditoría)
4. **Cero valor añadido**: los traces de sus dependencias (Nomina, NoPayroll, CadenabCalculator, CadenaCCalculator) ya capturan toda la trazabilidad

### Alternativa futura (si se necesita)

Si en el futuro se desea auditar la agregación, se puede crear un trace **explícitamente documentado y separado**, no como parte de FORMULA_TRACE_RUNTIME_WIRING.

## Validación

**Test Results:**

| Suite | Resultado |
|---|---|
| `test_formula_id_guardrails.py` | 8/8 ✅ |
| `test_baseline_formula_snapshot_v1.py` | 5/5 ✅ |
| `test_baseline_formula_snapshot_cadena_c_v1.py` | 5/5 ✅ |
| `tests/golden/` | 58/58 ✅ |
| **Total** | **76/76 ✅** |

**Cero drift — No changes made to CostosTotalesCalculator**

---

**Status:** PHASE5 OMITIDO — CostosTotalesCalculator es orquestador sin trace natural.

**Cobertura actual (4/12):**
- ✅ NoPayrollCalculator (PHASE1)
- ✅ CadenaBCalculator (PHASE2)
- ✅ CadenaCCalculator (PHASE3)
- ✅ CostosFinancierosCalculator (PHASE4)
- ⏭ CostosTotalesCalculator (omitido: orquestador sin trace)

**Próximos candidatos con traces naturales:**
- PyGCalculator (PHASE6) — tiene traces
- KPIsCalculator (PHASE7) — tiene traces
- CostToServeCalculator (PHASE8) — tiene traces
- VisionTarifasCalculator (PHASE9) — tiene traces
- VisionPyGBuilder (PHASE10) — tiene traces
- VisionImprimibleBuilder (PHASE11) — tiene traces

---

**Decisión validada:** Mantener criterio de PHASE1-4 = solo agregar formula_ids a traces existentes, no crear nuevos.
