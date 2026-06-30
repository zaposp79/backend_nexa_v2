# FORMULA_TRACE_RUNTIME_WIRING_PHASE4_COSTOS_FINANCIEROS

## Objetivo

Conectar FORMULA_ID existentes de CostosFinancierosCalculator con trazabilidad runtime mínima, replicando el patrón de PHASE1-PHASE3.

## Contexto

PHASE1 (NoPayroll), PHASE2 (Cadena B), PHASE3 (Cadena C) completadas. Ahora se replica en CostosFinancierosCalculator:

1. TraceEntry.formula_ids ya existe (campo interno, no serializado)
2. AuditTracer.entry() ya acepta formula_ids
3. Se agregan FORMULA_ID al trace existente de CostosFinancierosCalculator
4. Patrón validado en 3 calculadores + 0 drift

## Cambios

### CostosFinancierosCalculator — `modules/costos_financieros/calculators/costos_financieros_calculator.py`

Conecté los 8 FORMULA_ID existentes al trace en `calcular()`:

```python
_audit_trace(
    # ... campos existentes ...
    formula_ids=[
        self.FORMULA_ID.FINANCIACION,
        self.FORMULA_ID.POLIZAS,
        self.FORMULA_ID.ICA,
        self.FORMULA_ID.GMF,
        self.FORMULA_ID.COMISION_ADMINISTRACION,
        self.FORMULA_ID.POLIZAS_PER_CADENA,
        self.FORMULA_ID.ICA_PER_CADENA,
        self.FORMULA_ID.GMF_PER_CADENA,
    ],
)
```

**Sin cambios funcionales:**
- No cambié ningún cálculo
- Solo agregué el parámetro al trace existente
- FORMULA_ID ya estaban definidos (línea 69-78)

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

Idéntica a PHASE1-PHASE3:

- TraceEntry.formula_ids se almacena en memoria
- Se excluye de la serialización JSON (via `to_dict()`)
- No afecta snapshots, exports ni contratos públicos
- Visible internamente para auditoría y reproducibilidad

## Archivos modificados

- `modules/costos_financieros/calculators/costos_financieros_calculator.py` — conexión FORMULA_ID al trace

---

**Status:** PHASE4 COMPLETADO — CostosFinancierosCalculator wired. Patrón probado en 4 calculadores.

**Cobertura actual (4/12):**
- ✅ NoPayrollCalculator (PHASE1)
- ✅ CadenaBCalculator (PHASE2)
- ✅ CadenaCCalculator (PHASE3)
- ✅ CostosFinancierosCalculator (PHASE4)

**Próximos candidatos:**
- CostosTotalesCalculator (5/12)
- PyGCalculator (6/12)
- KPIsCalculator (7/12)
- CostToServeCalculator (8/12)
- VisionTarifasCalculator (9/12)
- VisionPyGBuilder (10/12)
- VisionImprimibleBuilder (11/12)

**Riesgo:** BAJO — cambio interno, sin cambio de outputs públicos ni fórmulas.
