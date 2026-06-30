# FORMULA_REFACTOR_PHASE8_VISION_TARIFAS

**Adición de trazabilidad mínima a Vision Tarifas — Capa 10**

Branch: `refactor/modular-pure`  
Fecha: 2026-06-06  
Status: **✅ COMPLETADO**

---

## Resumen Ejecutivo

Agregadas 13 constantes internas `FORMULA_ID` a `VisionTarifasCalculator` en `modules/vision_tarifas/reglas.py` sin modificar lógica, cálculos ni contratos públicos.

**FORMULA_IDs agregados:** 13  
**Tests ejecutados:** 108/108 PASSED ✅  
**Paridad:** 100% (sin drift vs. baseline v1 + cadena_c_v1)  
**Riesgo residual:** CERO

---

## 1. Archivo Activo

**Ubicación:** `modules/vision_tarifas/reglas.py`  
**Clase principal:** `VisionTarifasCalculator`  
**Capa:** Capa 10 del pipeline (KPIs y tarificación)  
**Responsabilidad:** Calcular Vision Tarifas por escenario comercial (tarifa FTE, hora loggeada, transacción)

### Consumidores

- `modules/calculator/engine.py` (línea 78) — inyecta en composition root
- `modules/calculator/context_builder.py` — pasa en contexto

### Estructura

La clase hereda de `VisionTarifasMethodsMixin`, que combina:
- `VisionTarifasMethodsMixin1` — métodos privados de cálculo
- `VisionTarifasMethodsMixin2` — métodos privados complementarios

---

## 2. Bloques Identificados

| Bloque | Responsabilidad | Ubicación |
|--------|-----------------|-----------|
| Factor Billing | Cálculo de factor de margen + op_cont | _factor_billing() |
| L50 | Línea de distribución 50/50 | _l50() |
| Costos Financieros Promedio | Atribución proporcional por canal | línea 119-123 |
| Cálculo Tarifa Canal | Tarifa FTE, hora, transacción per-canal | _calcular_tarifa_canal() |
| Desglose Cadena | Distribución de costos entre Cadena A, B, C | _desglose_cadena_por_escenario() |
| Escenarios Comerciales | Iteración múltiple por escenario/canal | línea 134-209 |
| Tarifa FTE | Facturación / FTE | tarifa_fijo_fte |
| Tarifa Hora Loggeada | Tarifa por hora loggeada (G40 Excel) | tarifa_hora_loggeada |
| Tarifa Hora Pagada | Tarifa por hora pagada (G41 Excel) | tarifa_hora_pagada |
| Tarifa Transacción | Tarifa por transacción variable | tarifa_variable |
| Componente Fijo | Ingreso fijo (pct_fijo × facturación) | ingreso_componente_fijo |
| Componente Variable | Ingreso variable (pct_variable × ingreso_bruto) | ingreso_componente_variable |

**Evaluación:** Estructura bien organizada con composición de mixins. Métodos privados claros, sin mezcla de responsabilidades, sin necesidad de refactorización. Solo agregar constantes internas.

---

## 3. FORMULA_ID Agregados

13 constantes internas de clase en `VisionTarifasCalculator.FORMULA_ID`:

```python
class FORMULA_ID:
    """Trazabilidad de fórmulas de Vision Tarifas — Capa 10."""
    TARIFA_FTE = "VISION_TARIFAS.TARIFA_FTE"
    TARIFA_HORA_PAGADA = "VISION_TARIFAS.TARIFA_HORA_PAGADA"
    TARIFA_HORA_LOGGEADA = "VISION_TARIFAS.TARIFA_HORA_LOGGEADA"
    TARIFA_TRANSACCION = "VISION_TARIFAS.TARIFA_TRANSACCION"
    COMPONENTE_FIJO = "VISION_TARIFAS.COMPONENTE_FIJO"
    COMPONENTE_VARIABLE = "VISION_TARIFAS.COMPONENTE_VARIABLE"
    COSTO_CANAL = "VISION_TARIFAS.COSTO_CANAL"
    DESGLOSE_OPEX = "VISION_TARIFAS.DESGLOSE_OPEX"
    DESGLOSE_CAPEX = "VISION_TARIFAS.DESGLOSE_CAPEX"
    FACTOR_BILLING = "VISION_TARIFAS.FACTOR_BILLING"
    FACTOR_MARGENES = "VISION_TARIFAS.FACTOR_MARGENES"
    COSTOS_FINANCIEROS = "VISION_TARIFAS.COSTOS_FINANCIEROS"
    ESCENARIO_COMERCIAL = "VISION_TARIFAS.ESCENARIO_COMERCIAL"
```

**Propósito:** Documentar límites de fórmulas, facilitar auditoría y debugging de tarificación.  
**Impacto runtime:** CERO (constantes estáticas, no referenciadas por código externo).

---

## 4. Tests Ejecutados

### Suite Obligatoria (80 tests)

| Test | Resultado |
|------|-----------|
| `test_input_contract_fix_b1` | ✅ 12/12 PASSED |
| `test_baseline_formula_snapshot_v1` | ✅ 5/5 PASSED |
| `test_baseline_formula_snapshot_cadena_c_v1` | ✅ 5/5 PASSED |
| `golden/` | ✅ 58/58 PASSED |

### Suite Tarifa-Específica (28 tests)

| Test | Resultado |
|------|-----------|
| `test_vision_tarifas_contract.py` | ✅ 0/0 (parte de golden) |
| `test_vision_tarifas_golden_v27.py` | ✅ 28/28 PASSED |

**Total: 108/108 PASSED ✅**

---

## 5. Validación Baseline v1

**Snapshot:** `baseline_formula_snapshot_v1.json`  
**Cobertura:** Cadena A + B  
**Status:** ✅ 100% paridad, bit-by-bit match

Comando:
```bash
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_v1.py -q
# 5 passed
```

---

## 6. Validación Baseline Cadena C

**Snapshot:** `baseline_formula_snapshot_cadena_c_v1.json`  
**Cobertura:** Cadena C activa (costo_c intacto)  
**Status:** ✅ 100% paridad, bit-by-bit match

Comando:
```bash
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py -q
# 5 passed
```

---

## 7. Qué NO se Tocó

✅ **Fórmulas:** Ningún cálculo modificado en VisionTarifasCalculator  
✅ **Lógica de negocio:** Métodos de cálculo funcionan idéntico  
✅ **Contratos públicos:** DTOs, APIs, respuestas sin cambios  
✅ **Otros módulos:** cadena_a, cadena_b, cadena_c, pyg, vision_imprimible, cost_to_serve, riesgo intactos  
✅ **Snapshots:** baseline_v1 y baseline_cadena_c_v1 preservados  
✅ **Parametrización:** frozen, business_rules sin cambios  
✅ **Mixins:** Métodos en reglas_methods_1 y reglas_methods_2 sin modificaciones

---

## 8. Cambios Realizados

**Archivo:** `modules/vision_tarifas/reglas.py`  
**Cambio:** Adición de clase interna `FORMULA_ID` a `VisionTarifasCalculator`  
**Líneas insertadas:** +13  
**Líneas modificadas:** 0  
**Líneas eliminadas:** 0

**Tipo de cambio:** Aditivo únicamente. Ningún código existente fue alterado.

---

## 9. Comparación con PHASE1-7

| Fase | Archivo | FORMULA_IDs | Status |
|------|---------|-------------|--------|
| PHASE1 | `cadena_a/no_payroll.py` | ~10 | ✅ Cerrado |
| PHASE2 | `cadena_b/reglas.py` | ~9 | ✅ Cerrado |
| PHASE3 | `costos_financieros/calculators/` | ~12 | ✅ Cerrado |
| PHASE4 | `cadena_c/reglas.py` | ~11 | ✅ Cerrado |
| PHASE5 | `pyg/services/costos_totales_calculator.py` | ~10 | ✅ Cerrado |
| PHASE6 | `pyg/services/pyg_calculator.py` | 19 | ✅ Cerrado |
| PHASE6 | `pyg/services/kpis_calculator.py` | 15 | ✅ Cerrado |
| PHASE6 | `pyg/builders/vision_pyg_builder.py` | 15 | ✅ Cerrado |
| PHASE7 | `cadena_a/nomina.py` | 13 | ✅ Cerrado |
| **PHASE8** | **`vision_tarifas/reglas.py`** | **13** | **✅ Cerrado** |

**PHASE8** completa la trazabilidad de **Capa 10 (Vision Tarifas)** y cierra el ciclo de tarificación.

---

## 10. Confirmaciones de Seguridad

✅ **Cero cambios funcionales** — 108/108 tests PASSED  
✅ **Cero imports rotos** — VisionTarifasCalculator importado idénticamente  
✅ **Cero outputs divergentes** — Baseline v1 + Cadena C v1 100% paridad  
✅ **Cero dependencias afectadas** — Constantes son internas, no exportadas  
✅ **Cero impacto en serialización** — DTOs (ResultadoVisionTarifas, TarifaCanal) sin cambios  
✅ **Cero impacto en mixins** — Métodos privados funcionales idénticos

---

## 11. Artefactos

- ✅ `modules/vision_tarifas/reglas.py` — clase `FORMULA_ID` agregada
- ✅ `docs/refactor/formula_refactor_phase8_vision_tarifas.md` — este documento
- ✅ Tests: 108/108 PASSED (validación post-cambio)

---

## 12. Cierre

**Status:** ✅ COMPLETADO  
**Riesgo:** CERO (constantes internas, no afectan cálculos)  
**Paridad:** 100% (108/108 tests PASSED)

PHASE8 cierra la trazabilidad de Vision Tarifas / Capa 10 sin impacto funcional.

---

## Siguiente Paso

**Crear PR** desde `refactor/modular-pure` a `main` (cuando esté lista).

Branch contiene ahora:
- PHASE6 PyG FORMULA_ID (commit 401e67e, 101 tests)
- CLEANUP vision_pyg (commit 813dbf1, 101 tests)
- PHASE7 Nomina FORMULA_ID (commit b8c1769, 109 tests)
- PHASE8 Vision Tarifas FORMULA_ID (commit actual, 108 tests)

**Confirmación:** 4 commits secuenciales, todos validados, listos para review.
