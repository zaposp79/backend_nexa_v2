# CAPEX-001 V2-8 Evidence

> **Estado:** COMPLETED — 2026-06-11  
> **Commit de cierre:** (en curso)

## Hipótesis original

`_costo_amortizacion_inversion` en `CadenaCCalculator` debía aplicar factor `(1 + tasa_mensual_financ)` per Condiciones Cadena C!J62.

## Evidencia Excel V2-8

**Hoja:** `Condiciones Cadena C`  
**Fórmula en J62:J83:**
```
=IFERROR((I62/H62)*(1+'Panel de Control General'!$L$11),0)
```

donde:
- `I` = valor_total (F×G = precio_unitario × cantidad)
- `H` = meses_a_diferir
- `Panel!L11` = tasa_interes_mensual = `0.0153`

**Valores cacheados (data_only=True):**

| Celda | valor_total (I) | meses (H) | J (mensual con factor) |
|-------|-----------------|-----------|------------------------|
| J62 | 150,000,000 | 24 | 6,345,625.00 |
| J63 | 516,516 | 12 | 43,701.56 |
| J64 | 150,000,000 | 24 | 6,345,625.00 |
| J65 | 516,516 | 12 | 43,701.56 |
| J66..J83 | 0 | — | 0 |
| **SUM** | | | **12,778,653.116** |

## Estado del backend

**Archivo:** `modules/cadena_c/reglas.py:175-182`

```python
def _costo_amortizacion_inversion(self) -> float:
    """
    EXCEL V2-8: Condiciones Cadena C!J62 = IFERROR((I62/H62)*(1+Panel!$L$11),0)
    Diferencia vs V2-7: incluye factor (1+tasa_interes_mensual) de Panel!L11.
    """
    return self._parametros.inversion_anual / 12 * (1 + self._parametros.tasa_interes_mensual)
```

La fórmula **ya era correcta** en la implementación V2-8. El factor estaba presente.

## Cadena de transformación

1. **Adapter** `_c_calcular_inversion`: suma `valor_total/meses` por item, multiplica por 12 → `inversion_anual`
2. **Reglas** `_costo_amortizacion_inversion`: `inversion_anual / 12 * (1 + tasa)` = `sum(I/H) * (1 + tasa)` ✓

Neto: `(150M/24 + 516516/12 + 150M/24 + 516516/12) * (1+0.0153) = 12,778,653.116` — coincide con Excel.

## Test creado

**Archivo:** `tests/golden/test_capex_001_v28_cadena_c.py`

- `test_formula_unit_single_item_24_months` — J62 = 6,345,625.00 ✓
- `test_formula_unit_single_item_12_months` — J63 = 43,701.56 ✓
- `test_formula_sum_all_v28_items` — SUM(J62:J65) = 12,778,653.116 ✓
- `test_zero_inversion_returns_zero` — edge case ✓

Resultado: **4/4 PASSED**

## Veredicto

CAPEX-001 = **COMPLETED**. No se requirió ningún cambio de código — la fórmula ya era correcta. Solo faltaba el test que pineara los valores numéricos de Excel V2-8.
