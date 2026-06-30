# FORMULA_TRACE_RUNTIME_WIRING_PHASE2_CADENA_B

## Objetivo

Conectar FORMULA_ID existentes de Cadena B con trazabilidad runtime mínima, replicando el patrón de PHASE1 (NoPayrollCalculator).

## Contexto

PHASE1 completó NoPayrollCalculator. Ahora se replica el mismo patrón en CadenaBCalculator:

1. TraceEntry.formula_ids ya existe (campo interno, no serializado)
2. AuditTracer.entry() ya acepta formula_ids
3. Se agregan FORMULA_ID al trace existente de CadenaBCalculator

## Cambios

### CadenaBCalculator — `modules/cadena_b/reglas.py`

Conecté los 7 FORMULA_ID existentes al trace en `calcular_para_mes()`:

```python
_audit_trace(
    # ... campos existentes ...
    formula_ids = [
        self.FORMULA_ID.OPEX_FIJO,
        self.FORMULA_ID.INVERSIONES,
        self.FORMULA_ID.SOPORTE_MANTENIMIENTO,
        self.FORMULA_ID.COSTO_VARIABLE,
        self.FORMULA_ID.ESCALAMIENTO,
        self.FORMULA_ID.HITL,
        self.FORMULA_ID.FACTOR_PERSONAL,
    ],
)
```

**Sin cambios funcionales:**
- No cambié ningún cálculo
- Solo agregué el parámetro al trace existente
- FORMULA_ID ya estaban definidos (líneas 52-60)

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

Idéntica a PHASE1:

- TraceEntry.formula_ids se almacena en memoria
- Se excluye de la serialización JSON (via `to_dict()`)
- No afecta snapshots, exports ni contratos públicos
- Visible internamente para auditoría y reproducibilidad

## Archivos modificados

- `modules/cadena_b/reglas.py` — conexión FORMULA_ID al trace

---

**Status:** PHASE2 COMPLETADO — CadenaBCalculator wired. Patrón probado en 2 calculadores.

**Próximos pasos:** PHASE3 — CadenaCCalculator, CostosFinancierosCalculator, etc.

**Riesgo:** BAJO — cambio interno, sin cambio de outputs públicos ni fórmulas.
