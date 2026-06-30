# FORMULA_TRACE_RUNTIME_WIRING_PHASE6_PYG

## Objetivo

Conectar FORMULA_ID existentes de PyGCalculator con trazabilidad runtime mínima, replicando el patrón de PHASE1-PHASE4.

## Contexto

PHASE1 (NoPayroll), PHASE2 (Cadena B), PHASE3 (Cadena C), PHASE4 (Costos Financieros) completadas. PHASE5 (Costos Totales) omitido por orquestador puro. Ahora se replica en PyGCalculator:

1. TraceEntry.formula_ids ya existe (campo interno, no serializado)
2. AuditTracer.entry() ya acepta formula_ids
3. Se agregan FORMULA_ID al trace existente de PyGCalculator
4. Patrón validado en 5 calculadores + 0 drift

## Cambios

### PyGCalculator — `modules/pyg/services/pyg_calculator.py`

Conecté los 9 FORMULA_ID existentes al trace en `calcular_mes()` (línea 161):

```python
_audit_trace(
    # ... campos existentes ...
    formula_ids = [
        self.FORMULA_ID.INGRESO_CADENA_A,
        self.FORMULA_ID.INGRESO_CADENA_B,
        self.FORMULA_ID.INGRESO_CADENA_C,
        self.FORMULA_ID.INGRESO_BRUTO,
        self.FORMULA_ID.IMPREVISTOS,
        self.FORMULA_ID.FACTOR_RAMPUP,
        self.FORMULA_ID.FACTOR_BILLING_A,
        self.FORMULA_ID.FACTOR_BILLING_B,
        self.FORMULA_ID.FACTOR_BILLING_C,
    ],
)
```

**Sin cambios funcionales:**
- No cambié ningún cálculo
- Solo agregué el parámetro al trace existente
- FORMULA_ID ya estaban definidos (línea 69-88)

**Nota sobre otros FORMULA_ID:**
- CONTINGENCIA_OP, CONTINGENCIA_COM, MARKUP_INGRESO, DESCUENTO_INGRESO se calculan en `calcular_mes()` pero se asignan directamente a PyGMensual (sin trace)
- ACUM_* (acumuladores) se construyen en `calcular_contrato()` pero sin trace natural
- Siguiendo criterio PHASE1-4 ("agregar formula_ids a traces existentes"), solo se wirea el trace de ingresos

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

Idéntica a PHASE1-PHASE5:

- TraceEntry.formula_ids se almacena en memoria
- Se excluye de la serialización JSON (via `to_dict()`)
- No afecta snapshots, exports ni contratos públicos
- Visible internamente para auditoría y reproducibilidad

## Archivos modificados

- `modules/pyg/services/pyg_calculator.py` — conexión FORMULA_ID al trace (9 IDs)

---

**Status:** PHASE6 COMPLETADO — PyGCalculator wired. Patrón probado en 5 calculadores.

**Cobertura actual (5/12):**
- ✅ NoPayrollCalculator (PHASE1)
- ✅ CadenaBCalculator (PHASE2)
- ✅ CadenaCCalculator (PHASE3)
- ✅ CostosFinancierosCalculator (PHASE4)
- ⏭ CostosTotalesCalculator (omitido: orquestador sin trace)
- ✅ PyGCalculator (PHASE6)

**Próximos candidatos con traces naturales:**
- KPIsCalculator (PHASE7)
- CostToServeCalculator (PHASE8)
- VisionTarifasCalculator (PHASE9)
- VisionPyGBuilder (PHASE10)
- VisionImprimibleBuilder (PHASE11)

**Riesgo:** BAJO — cambio interno, sin cambio de outputs públicos ni fórmulas.
