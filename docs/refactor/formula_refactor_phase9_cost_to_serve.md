# FORMULA_REFACTOR_PHASE9_COST_TO_SERVE

**Adición de trazabilidad mínima a Cost To Serve — Capa 9**

Branch: `refactor/modular-pure`  
Fecha: 2026-06-06  
Status: **✅ COMPLETADO**

---

## Resumen Ejecutivo

Agregadas 13 constantes internas `FORMULA_ID` a `CostToServeCalculator` en `modules/vision_cost_to_serve/services/cost_to_serve_calculator.py` sin modificar lógica, cálculos ni contratos públicos.

**FORMULA_IDs agregados:** 13  
**Tests ejecutados:** 110/110 PASSED ✅  
**Paridad:** 100% (sin drift vs. baseline v1 + cadena_c_v1)  
**Riesgo residual:** CERO

---

## 1. Archivo Activo

**Ubicación:** `modules/vision_cost_to_serve/services/cost_to_serve_calculator.py`  
**Clase principal:** `CostToServeCalculator`  
**Capa:** Capa 9 del pipeline (KPIs — Cost To Serve antes de Vision Tarifas)  
**Responsabilidad:** Calcular costo promedio por unidad operativa (FTE, volumen) desagregado por cadena y canal.

### Consumidores

- `modules/calculator/engine.py` (línea 77) — inyecta en composition root
- `modules/calculator/context_builder.py` — pasa en contexto

### Estructura

La clase contiene métodos de cálculo bien aislados:
- Denominadores (Cadena A, B, C)
- Costos por cadena
- Desglose por componentes
- Detalle por canal

---

## 2. Bloques Identificados

| Bloque | Responsabilidad | Ubicación |
|--------|-----------------|-----------|
| Denominador Cadena A | Suma FTE + volumen inbound | _denominador_cadena_a() |
| Denominador Cadena B | Suma volumen + escalamiento | _denominador_cadena_b() |
| Denominador Cadena C | Suma volumen canales C | _denominador_cadena_c() |
| Costo Cadena A | CTS unitario A | línea 120-123 |
| Costo Cadena B | CTS unitario B | línea 124-127 |
| Costo Cadena C | CTS unitario C | línea 129-132 |
| Costo Ponderado | Promedio ponderado por denominadores | línea 138-145 |
| Desglose Cadena A | Sub-componentes (payroll, no-payroll) | _calcular_desglose_a() |
| Desglose Cadena B | Sub-componentes (fijo, variable) | _calcular_desglose_b() |
| Canales Detalle | Breakdown per-canal (FTE, modalidad) | _calcular_canales_detalle() |
| Participación A | % de A en total CTS | línea 176-179 |
| Participación B | % de B en total CTS | línea 180-183 |
| Participación C | % de C en total CTS | línea 184-187 |

**Evaluación:** Estructura excepcional, métodos privados bien separados, sin mezcla de responsabilidades, sin necesidad de refactorización. Solo agregar constantes internas.

---

## 3. FORMULA_ID Agregados

13 constantes internas de clase en `CostToServeCalculator.FORMULA_ID`:

```python
class FORMULA_ID:
    """Trazabilidad de fórmulas de Cost To Serve — Capa 9."""
    DENOMINADOR_CADENA_A = "CTS.DENOMINADOR_CADENA_A"
    DENOMINADOR_CADENA_B = "CTS.DENOMINADOR_CADENA_B"
    DENOMINADOR_CADENA_C = "CTS.DENOMINADOR_CADENA_C"
    COSTO_CADENA_A = "CTS.COSTO_CADENA_A"
    COSTO_CADENA_B = "CTS.COSTO_CADENA_B"
    COSTO_CADENA_C = "CTS.COSTO_CADENA_C"
    COSTO_PONDERADO = "CTS.COSTO_PONDERADO"
    DESGLOSE_CADENA_A = "CTS.DESGLOSE_CADENA_A"
    DESGLOSE_CADENA_B = "CTS.DESGLOSE_CADENA_B"
    CANALES_DETALLE = "CTS.CANALES_DETALLE"
    PARTICIPACION_A = "CTS.PARTICIPACION_A"
    PARTICIPACION_B = "CTS.PARTICIPACION_B"
    PARTICIPACION_C = "CTS.PARTICIPACION_C"
```

**Propósito:** Documentar límites de fórmulas, facilitar auditoría de costo unitario por cadena/canal.  
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

### Suite CTS-Específica (30 tests)

| Test | Resultado |
|------|-----------|
| `test_cost_to_serve_golden_v27.py` | ✅ 30/30 PASSED |

**Total: 110/110 PASSED ✅**

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
**Cobertura:** Cadena C activa (costo_c_fin intacto)  
**Status:** ✅ 100% paridad, bit-by-bit match

Comando:
```bash
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py -q
# 5 passed
```

---

## 7. Qué NO se Tocó

✅ **Fórmulas:** Ningún cálculo modificado en CostToServeCalculator  
✅ **Lógica de negocio:** Métodos funcionan idéntico  
✅ **Contratos públicos:** DTOs (ResultadoCostToServe, CanalCTSDetalle, DesgloseCTSCadenaA/B), APIs sin cambios  
✅ **Otros módulos:** cadena_a, cadena_b, cadena_c, pyg, vision_imprimible, vision_tarifas, riesgo intactos  
✅ **Snapshots:** baseline_v1 y baseline_cadena_c_v1 preservados  
✅ **Parametrización:** frozen, business_rules sin cambios  
✅ **Helpers:** servicio_catalogo.py sin cambios

---

## 8. Cambios Realizados

**Archivo:** `modules/vision_cost_to_serve/services/cost_to_serve_calculator.py`  
**Cambio:** Adición de clase interna `FORMULA_ID` a `CostToServeCalculator`  
**Líneas insertadas:** +17 (clase + docstring + 13 constantes)  
**Líneas modificadas:** 0  
**Líneas eliminadas:** 0

**Tipo de cambio:** Aditivo únicamente. Ningún código existente fue alterado.

---

## 9. Comparación con PHASE1-8

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
| PHASE8 | `vision_tarifas/reglas.py` | 13 | ✅ Cerrado |
| **PHASE9** | **`vision_cost_to_serve/services/cost_to_serve_calculator.py`** | **13** | **✅ Cerrado** |

**PHASE9** completa la trazabilidad de **Capa 9 (Cost To Serve)** y cierra el ciclo de cost attribution.

---

## 10. Confirmaciones de Seguridad

✅ **Cero cambios funcionales** — 110/110 tests PASSED  
✅ **Cero imports rotos** — CostToServeCalculator importado idénticamente  
✅ **Cero outputs divergentes** — Baseline v1 + Cadena C v1 100% paridad  
✅ **Cero dependencias afectadas** — Constantes son internas, no exportadas  
✅ **Cero impacto en serialización** — DTOs (ResultadoCostToServe, CanalCTSDetalle, DesgloseCTSCadenaA/B) sin cambios  
✅ **Cero impacto en denominadores** — Métodos de cálculo funcionan idéntico

---

## 11. Artefactos

- ✅ `modules/vision_cost_to_serve/services/cost_to_serve_calculator.py` — clase `FORMULA_ID` agregada
- ✅ `docs/refactor/formula_refactor_phase9_cost_to_serve.md` — este documento
- ✅ Tests: 110/110 PASSED (validación post-cambio)

---

## 12. Cierre

**Status:** ✅ COMPLETADO  
**Riesgo:** CERO (constantes internas, no afectan cálculos)  
**Paridad:** 100% (110/110 tests PASSED)

PHASE9 cierra la trazabilidad de Cost To Serve / Capa 9 sin impacto funcional.

---

## Siguiente Paso

**Crear PR** desde `refactor/modular-pure` a `main` (cuando esté lista).

Branch contiene ahora:
- PHASE6 PyG FORMULA_ID (commit 401e67e, 101 tests)
- CLEANUP vision_pyg (commit 813dbf1, 101 tests)
- PHASE7 Nomina FORMULA_ID (commit b8c1769, 109 tests)
- PHASE8 Vision Tarifas FORMULA_ID (commit 08f79e4, 108 tests)
- PHASE9 Cost To Serve FORMULA_ID (commit actual, 110 tests)

**Confirmación:** 5 commits secuenciales, todos validados, listos para review.
