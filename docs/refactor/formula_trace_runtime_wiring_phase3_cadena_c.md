# FORMULA_TRACE_RUNTIME_WIRING_PHASE3_CADENA_C

## Objetivo

Conectar FORMULA_ID existentes de Cadena C con trazabilidad runtime mínima, replicando el patrón de PHASE1-PHASE2.

## Contexto

PHASE1 (NoPayroll) y PHASE2 (Cadena B) completados. Ahora se replica en CadenaCCalculator:

1. TraceEntry.formula_ids ya existe (campo interno, no serializado)
2. AuditTracer.entry() ya acepta formula_ids
3. Se agregan FORMULA_ID al trace existente de CadenaCCalculator
4. Cadena C tiene baseline propio: `test_baseline_formula_snapshot_cadena_c_v1.py`

## Cambios

### CadenaCCalculator — `modules/cadena_c/reglas.py`

Conecté los 8 FORMULA_ID existentes al trace en `calcular_para_mes()`:

```python
_audit_trace(
    # ... campos existentes ...
    formula_ids = [
        self.FORMULA_ID.CANALES,
        self.FORMULA_ID.OPEX_FIJO_INTEGRACION,
        self.FORMULA_ID.OPEX_VARIABLE_INTEGRACION,
        self.FORMULA_ID.INVERSION_ANUAL,
        self.FORMULA_ID.EQUIPO_TRANSVERSAL,
        self.FORMULA_ID.ESCALAMIENTO,
        self.FORMULA_ID.HITL,
        self.FORMULA_ID.TOTAL_MENSUAL,
    ],
)
```

**Sin cambios funcionales:**
- No cambié ningún cálculo
- Solo agregué el parámetro al trace existente
- FORMULA_ID ya estaban definidos (línea 52-61)

## Validación

**Test Results:**

| Suite | Resultado |
|---|---|
| `test_formula_id_guardrails.py` | 8/8 ✅ |
| `test_baseline_formula_snapshot_v1.py` | 5/5 ✅ |
| `test_baseline_formula_snapshot_cadena_c_v1.py` | 5/5 ✅ |
| `tests/golden/` | 58/58 ✅ |
| **Total** | **76/76 ✅** |

**Cero drift:** 
- Snapshot de Cadena B (v1) idéntico
- Snapshot de Cadena C (v1) idéntico
- Cálculos y fórmulas sin cambios

## Estrategia

Idéntica a PHASE1-PHASE2:

- TraceEntry.formula_ids se almacena en memoria
- Se excluye de la serialización JSON (via `to_dict()`)
- No afecta snapshots, exports ni contratos públicos
- Visible internamente para auditoría y reproducibilidad

## Archivos modificados

- `modules/cadena_c/reglas.py` — conexión FORMULA_ID al trace

---

**Status:** PHASE3 COMPLETADO — CadenaCCalculator wired. Patrón probado en 3 calculadores.

**Cobertura actual:**
- ✅ NoPayrollCalculator (PHASE1)
- ✅ CadenaBCalculator (PHASE2)
- ✅ CadenaCCalculator (PHASE3)

**Próximos pasos:** Extender a CostosFinancierosCalculator, CostosTotalesCalculator, PyGCalculator, etc.

**Riesgo:** BAJO — cambio interno, sin cambio de outputs públicos ni fórmulas.
