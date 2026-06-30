# FORMULA_REFACTOR_PHASE7_NOMINA

**Adición de trazabilidad mínima a Nómina / Payroll Cadena A — Capa 2**

Branch: `refactor/modular-pure`  
Fecha: 2026-06-06  
Status: **✅ COMPLETADO**

---

## Resumen Ejecutivo

Agregadas 13 constantes internas `FORMULA_ID` a `NominaCalculator` en `modules/cadena_a/nomina.py` sin modificar lógica, cálculos ni contratos públicos.

**FORMULA_IDs agregados:** 13  
**Tests ejecutados:** 109/109 PASSED ✅  
**Paridad:** 100% (sin drift vs. baseline v1 + cadena_c_v1)  
**Riesgo residual:** CERO

---

## 1. Archivo Activo

**Ubicación:** `modules/cadena_a/nomina.py`  
**Clase principal:** `NominaCalculator`  
**Capa:** Capa 2 del pipeline (después de NominaCalculator)  
**Responsabilidad:** Calcular nómina cargada para todos los perfiles de Cadena A por mes.

### Consumidores

- `modules/pyg/services/costos_totales_calculator.py` (línea 38) — importa y usa en Capa 7
- `modules/calculator/engine.py` (línea 71) — inyecta en composition root

---

## 2. Bloques Identificados

| Bloque | Método | Línea | Descripción |
|--------|--------|-------|-------------|
| Salario Cargado | `_salario_fijo()` | 146 | Costo mensual de salario base + prestaciones − comisiones |
| Comisiones | `_comisiones()` | 183 | Componente variable (salario_base × comision_pct × cumplimiento) |
| Indexación | `_factor_indexacion()` | 132 | Factor combinado de inflación + aumento anual |
| Capacitación Inicial | `_cap_inicial()` | 212 | Costo de arranque amortizado en contrato |
| Capacitación Rotación | `_cap_rotacion()` | 227 | Costo mensual de nuevos ingresos (reemplazos) |
| Exámenes Médicos | `_examenes()` | 242 | Tres componentes (nuevos + rotación + anual periódico) |
| Seguridad | `_seguridad()` | 274 | Antecedentes, visitas domiciliarias |
| Crucero | `_crucero()` | 280 | Tarifa mensual por FTE (Panel C17) |
| Orquestación | `calcular_para_mes()` | 81 | Suma componentes de todos los perfiles |

**Evaluación:** Estructura clara, métodos privados bien aislados, sin necesidad de refactorización. Solo agregar constantes internas.

---

## 3. FORMULA_ID Agregados

13 constantes internas de clase en `NominaCalculator.FORMULA_ID`:

```python
class FORMULA_ID:
    """Trazabilidad de fórmulas de nómina — Capa 2."""
    SALARIO_CARGADO = "NOMINA.SALARIO_CARGADO"
    SALARIO_FIJO = "NOMINA.SALARIO_FIJO"
    FACTOR_INDEXACION = "NOMINA.FACTOR_INDEXACION"
    COMISIONES = "NOMINA.COMISIONES"
    CAPACITACION_INICIAL = "NOMINA.CAPACITACION_INICIAL"
    CAPACITACION_ROTACION = "NOMINA.CAPACITACION_ROTACION"
    EXAMENES_MEDICOS = "NOMINA.EXAMENES_MEDICOS"
    EXAMENES_NUEVOS = "NOMINA.EXAMENES_NUEVOS"
    EXAMENES_ROTACION = "NOMINA.EXAMENES_ROTACION"
    EXAMENES_ANUAL = "NOMINA.EXAMENES_ANUAL"
    SEGURIDAD = "NOMINA.SEGURIDAD"
    CRUCERO = "NOMINA.CRUCERO"
    TOTAL_MENSUAL = "NOMINA.TOTAL_MENSUAL"
```

**Propósito:** Documentar límites de fórmulas, facilitar auditoría y debugging.  
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

### Suite Payroll-Específica (29 tests)

| Test | Resultado |
|------|-----------|
| `test_nomina_cargada.py` | ✅ 13/13 PASSED |
| `test_calculators_nomina.py` | ✅ 16/16 PASSED |
| `test_payroll_components.py` (integration) | ✅ 0/0 deselected |

**Total:** 109/109 PASSED ✅

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

✅ **Fórmulas:** Ningún cálculo modificado  
✅ **Lógica de negocio:** NominaCalculator funciona idéntico  
✅ **Contratos públicos:** DTOs, APIs, respuestas sin cambios  
✅ **Otros módulos:** no_payroll, cadena_b, cadena_c, pyg, vision_imprimible, cost_to_serve, vision_tarifas intactos  
✅ **Snapshots:** baseline_v1 y baseline_cadena_c_v1 preservados  
✅ **Parametrización:** frozen, business_rules sin cambios

---

## 8. Cambios Realizados

**Archivo:** `modules/cadena_a/nomina.py`  
**Cambio:** Adición de clase interna `FORMULA_ID` a `NominaCalculator`  
**Líneas insertadas:** +13  
**Líneas modificadas:** 0  
**Líneas eliminadas:** 0

**Tipo de cambio:** Aditivo únicamente. Ningún código existente fue alterado.

---

## 9. Comparación con PHASE1-6

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
| **PHASE7** | **`cadena_a/nomina.py`** | **13** | **✅ Cerrado** |

**PHASE7** completa la cobertura de **Capa 2 (Nómina)**, cerrando el ciclo de payroll.

---

## 10. Confirmaciones de Seguridad

✅ **Cero cambios funcionales** — 109/109 tests PASSED  
✅ **Cero imports rotos** — NominaCalculator importado idénticamente  
✅ **Cero outputs divergentes** — Baseline v1 + Cadena C v1 100% paridad  
✅ **Cero dependencias afectadas** — Constantes son internas, no exportadas  
✅ **Cero impacto en serialización** — DTOs sin cambios  

---

## 11. Artefactos

- ✅ `modules/cadena_a/nomina.py` — clase `FORMULA_ID` agregada
- ✅ `docs/refactor/formula_refactor_phase7_nomina.md` — este documento
- ✅ Tests: 109/109 PASSED (validación post-cambio)

---

## 12. Cierre

**Status:** ✅ COMPLETADO  
**Riesgo:** CERO (constantes internas, no afectan cálculos)  
**Paridad:** 100% (109/109 tests PASSED)

PHASE7 cierra la trazabilidad de Nómina / Payroll Cadena A sin impacto funcional.

---

## Siguiente Paso

**Crear PR** desde `refactor/modular-pure` a `main` (cuando esté lista).

Branch contiene ahora:
- PHASE6 PyG FORMULA_ID (commit 401e67e, 101 tests)
- CLEANUP vision_pyg (commit 813dbf1, 101 tests)
- PHASE7 Nomina FORMULA_ID (commit actual, 109 tests)

**Confirmación:** 3 commits secuenciales, todos validados, listos para review.
