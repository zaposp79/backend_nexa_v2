# FORMULA_TRACE_RUNTIME_WIRING_PHASE1

## Objetivo

Conectar FORMULA_ID existentes con trazabilidad runtime mínima, sin cambiar fórmulas, cálculos, contratos ni snapshots.

## Contexto

Los FORMULA_ID (PHASE 1-10) ya existen en los calculadores (NoPayrollCalculator, CadenaBCalculator, etc.) como constantes internas. Fase 1 de esta iniciativa integra esos IDs con el sistema de auditoría (`audit/trace.py`) de forma que:

1. Los FORMULA_ID queden registrados en el trace interno
2. Sin cambiar el JSON serializado (backward compatible)
3. Sin modificar snapshots baseline
4. Sin cambios en payloads públicos

## Cambios

### 1. TraceEntry — `modules/shared/audit/trace.py`

Agregué un campo `formula_ids: list[str]` **interno** (no serializado):

```python
@dataclass
class TraceEntry:
    # ... existing fields ...
    formula_ids: list[str] = field(default_factory=list, repr=False)
```

Clave: `repr=False` + exclusión manual en `to_dict()` → el campo está en memoria pero **no aparece en JSON**.

### 2. AuditTracer.entry() — `modules/shared/audit/trace.py`

Extendí la firma para aceptar `formula_ids`:

```python
def entry(
    self,
    # ... existing params ...
    formula_ids: list[str] | None = None,
) -> None:
    # ...
    e = TraceEntry(
        # ...
        formula_ids=formula_ids or [],
    )
```

La función `trace()` ya usa `**kwargs`, así que automáticamente pasa `formula_ids` sin cambios.

### 3. NoPayrollCalculator — `modules/cadena_a/no_payroll.py` (PILOTO)

Conecté los FORMULA_ID existentes al trace:

```python
_audit_trace(
    component   = "no_payroll",
    rule        = "NO_PAYROLL.opex_ti + capex + infraestructura",
    # ... otros campos ...
    formula_ids = [
        self.FORMULA_ID.OPEX_TI,
        self.FORMULA_ID.CAPEX,
        self.FORMULA_ID.INFRAESTRUCTURA,
    ],
)
```

No cambié ningún cálculo. Solo agregué el parámetro al trace existente.

## Validación

**Test Results:**

| Suite | Resultado |
|---|---|
| `test_formula_id_guardrails.py` | 8/8 ✅ |
| `test_baseline_formula_snapshot_v1.py` | 5/5 ✅ |
| `test_baseline_formula_snapshot_cadena_c_v1.py` | 5/5 ✅ |
| `tests/golden/` | 58/58 ✅ |
| **Total** | **76/76 ✅** |

**Cero drift:** Los snapshots baseline no cambiaron. Las fórmulas y cálculos son idénticos. Solo el trace interno ahora contiene FORMULA_ID.

## Estrategia de Backward Compatibility

El campo `formula_ids` en TraceEntry:
- Se almacena en memoria (accesible via `trace.entries[i].formula_ids`)
- Se **excluye** de la serialización JSON (`to_dict()` lo popa)
- No afecta snapshots, exports ni contratos públicos

Esto permite:
- Código externo que lee traces sigue viendo el JSON igual
- Código interno que accede a `tracer.entries` ve FORMULA_ID
- Migración gradual: otros calculadores pueden agregarse sin romper nada

## Próximos pasos

1. **PHASE1b:** Repetir patrón en otros calculadores (CadenaBCalculator, CadenaCCalculator, etc.)
2. **PHASE2:** Exponer FORMULA_ID en reportes internos de auditoría (si se necesita)
3. **PHASE3:** Opcional — agregar endpoint de trazabilidad (GET `/audit/trace/{simulation_id}`)

## Archivos modificados

- `modules/shared/audit/trace.py` — TraceEntry + AuditTracer.entry()
- `modules/cadena_a/no_payroll.py` — conexión FORMULA_ID al trace

---

**Status:** PILOTO COMPLETADO — NoPayrollCalculator wired. Listo para replicación a otros calculadores.

**Riesgo:** BAJO — cambio interno, sin cambio de outputs públicos ni fórmulas.
