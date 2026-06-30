# FORMULA_TRACE_RUNTIME_WIRING_PHASE7_KPIS

## Objetivo

Conectar FORMULA_ID existentes de KPIsCalculator con trazabilidad runtime mínima, replicando el patrón de PHASE1-PHASE6.

## Contexto

PHASE1 (NoPayroll), PHASE2 (Cadena B), PHASE3 (Cadena C), PHASE4 (Costos Financieros) completadas. PHASE5 (Costos Totales) omitido por orquestador puro. PHASE6 (PyG) completado. Ahora se replica en KPIsCalculator:

1. TraceEntry.formula_ids ya existe (campo interno, no serializado)
2. AuditTracer.entry() ya acepta formula_ids
3. Se agregan FORMULA_ID al trace existente de KPIsCalculator
4. Patrón validado en 6 calculadores + 0 drift

## Cambios

### KPIsCalculator — `modules/pyg/services/kpis_calculator.py`

Conecté los 15 FORMULA_ID existentes al trace en `calcular()` (línea 121):

```python
_audit_trace(
    # ... campos existentes ...
    formula_ids = [
        self.FORMULA_ID.COSTO_MENSUAL_PROMEDIO,
        self.FORMULA_ID.COSTO_CADENA_A_PROMEDIO,
        self.FORMULA_ID.TARIFA_MENSUAL,
        self.FORMULA_ID.FACTURACION_PROYECTADA,
        self.FORMULA_ID.FACTOR_MARGENES,
        self.FORMULA_ID.FACTOR_PERIODO,
        self.FORMULA_ID.COSTOS_FIN_SOBRE_PROMEDIO,
        self.FORMULA_ID.INGRESO_BRUTO_TOTAL,
        self.FORMULA_ID.INGRESO_NETO_TOTAL,
        self.FORMULA_ID.COSTO_TOTAL_CONTRATO,
        self.FORMULA_ID.CONTRIBUCION_TOTAL,
        self.FORMULA_ID.UTILIDAD_NETA_TOTAL,
        self.FORMULA_ID.PCT_UTILIDAD_NETA,
        self.FORMULA_ID.MARGEN_MINIMO_REQUERIDO,
        self.FORMULA_ID.CUMPLE_MARGEN_MINIMO,
    ],
)
```

**Sin cambios funcionales:**
- No cambié ningún cálculo
- Solo agregué el parámetro al trace existente
- FORMULA_ID ya estaban definidos (línea 77-93)

## Validación

**Test Results:**

| Suite | Resultado |
|---|---|
| `test_formula_id_guardrails.py` | 8/8 ✅ |
| `test_baseline_formula_snapshot_v1.py` | 5/5 ✅ |
| `test_baseline_formula_snapshot_cadena_c_v1.py` | 5/5 ✅ |
| `tests/golden/` | 58/58 ✅ |
| **Total** | **76/76 ✅** |

**Cero drift:** Snapshots baseline idénticos. Cálculos y fórmulas sin cambios.

## Estrategia

Idéntica a PHASE1-PHASE6:

- TraceEntry.formula_ids se almacena en memoria
- Se excluye de la serialización JSON (via `to_dict()`)
- No afecta snapshots, exports ni contratos públicos
- Visible internamente para auditoría y reproducibilidad

## Archivos modificados

- `modules/pyg/services/kpis_calculator.py` — conexión FORMULA_ID al trace (15 IDs)

---

**Status:** PHASE7 COMPLETADO — KPIsCalculator wired. Patrón probado en 6 calculadores.

**Cobertura actual (6/12):**
- ✅ NoPayrollCalculator (PHASE1)
- ✅ CadenaBCalculator (PHASE2)
- ✅ CadenaCCalculator (PHASE3)
- ✅ CostosFinancierosCalculator (PHASE4)
- ⏭ CostosTotalesCalculator (omitido: orquestador sin trace)
- ✅ PyGCalculator (PHASE6)
- ✅ KPIsCalculator (PHASE7)

**Próximos candidatos con traces naturales:**
- CostToServeCalculator (PHASE8)
- VisionTarifasCalculator (PHASE9)
- VisionPyGBuilder (PHASE10)
- VisionImprimibleBuilder (PHASE11)

**Riesgo:** BAJO — cambio interno, sin cambio de outputs públicos ni fórmulas.
