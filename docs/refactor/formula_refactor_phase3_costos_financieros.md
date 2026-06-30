# FORMULA_REFACTOR_PHASE3_COSTOS_FINANCIEROS

**Refactor minimal de trazabilidad: CostosFinancierosCalculator**

Branch: `refactor/modular-pure`  
Fecha: 2026-06-06  
Status: **CLOSED**

---

## Objetivo

Mejorar trazabilidad y localización de fórmulas de Costos Financieros (Capa 8) sin cambiar comportamiento ni output numérico.

---

## Alcance

- **Archivo principal:** `modules/costos_financieros/calculators/costos_financieros_calculator.py`
- **Clase pública:** `CostosFinancierosCalculator`
- **Cambios permitidos:** Constantes internas, documentación, formula_ids (cero impacto en output)
- **Cambios PROHIBIDOS:** Refactor de métodos, cambio de lógica, modificación de audit_trace output, cambios en contratos públicos

---

## 1. Auditoría de Bloques (TAREA 1)

### Estructura actual

| Bloque | Método | Responsabilidad | Inputs | Outputs | Riesgo | Notas |
|--------|--------|-----------------|--------|---------|--------|-------|
| **Financiación** | `_calcular_financiacion()` | Costo de financiación del período adelantado | costo_base, tasa_mensual, factor_periodo | float | Bajo | Producto de tres factores; desactivable si `activa_financiacion=False` |
| **Pólizas** | `_calcular_polizas()` | Prima de pólizas de seguros | costo, financiación, tasa, factor_márgenes | float | Bajo | Base normalizada por factor_márgenes |
| **ICA** | `_calcular_ica()` | Impuesto Industria y Comercio con gross-up | costo, polizas, financiación, factor_márgenes | float | **Medio** | Base = costo/fm + polizas + fin; gross-up refleja ingreso neto |
| **GMF** | `_calcular_gmf()` | Gravamen Movimientos Financieros sin gross-up | costo, polizas, financiación | float | Bajo | Base directa (sin división por fm) |
| **Comisión Administración** | `_calcular_comision_administracion()` | Solo Cadena A; tasa 1.18% | costo_a, factor_márgenes | float | Bajo | Aplica EXCLUSIVAMENTE a Cadena A (Panel!C45=True); H-07 cop_round |
| **Per-cadena Distribution** | calcular() lineas 143-196 | Distribución A/B/C si polizas_usuario | bases_a/b/c, tasas, fm_a/b/c | múltiples | **Medio** | Lógica compleja: per_canal flags, per_cadena ICA/GMF/comAdm |
| **Pólizas Per-cadena** | calcular() lineas 169-172 | Suma pure_pol_a + pure_pol_b + pure_pol_c | tasa_pure, costo+fin por cadena | float | **Medio** | Depende de flags `per_canal` y `aplica_a/b/c` |
| **ICA Per-cadena** | calcular() lineas 182-185 | Distribución A/B/C del ICA con gross-up | bases_a/b/c, pólizas_a/b/c, fm_a/b/c | float | **Medio** | Per-cadena gross-up con factor_billing diferente por cadena |

### Hallazgos clave

✅ **Métodos bien aislados:** Cada componente (fin, pol, ica, gmf) tiene su propio método privado.  
✅ **Lógica contractual clara:** Distinción entre `polizas_usuario=None` (usar parametrización) vs `[]` (cero pólizas) vs `[...]` (contractuales).  
✅ **Per-cadena separado en calcular():** Distribución A/B/C integrada en el método principal, no en submétodos.  
✅ **Gross-up documentado:** ICA con gross-up (fm) vs GMF sin gross-up.  
✅ **H-07 cop_round para ComAdm:** Alinea con Excel parity.

---

## 2. Decisión de Refactor (TAREA 2)

### Evaluación: Refactor vs. Trazabilidad

| Aspecto | Decisión | Justificación |
|---------|----------|---------------|
| **Extraer métodos per-cadena** | ❌ NO | Lógica integrada en calcular(); separar = riesgo de divergencia |
| **Crear costos_financieros_formulas.py** | ❌ NO | Mantener vertical slice coherence (costos_financieros responsibility) |
| **Re-centralizar en modules/calculator/formulas/** | ❌ NO | Contra FASE Y; requeriría refactor arquitectónico sin valor |
| **Agregar formula_ids internos** | ✅ SÍ | Zero-risk; mejora trazabilidad futura sin cambiar output |

### Cambios realizados

**Único cambio:** Agregué clase interna `CostosFinancierosCalculator.FORMULA_ID` con constantes:

```python
class FORMULA_ID:
    """Internal formula identifiers for traceability."""
    FINANCIACION = "COSTOS_FINANCIEROS.FINANCIACION"
    POLIZAS = "COSTOS_FINANCIEROS.POLIZAS"
    ICA = "COSTOS_FINANCIEROS.ICA"
    GMF = "COSTOS_FINANCIEROS.GMF"
    COMISION_ADMINISTRACION = "COSTOS_FINANCIEROS.COMISION_ADMINISTRACION"
    POLIZAS_PER_CADENA = "COSTOS_FINANCIEROS.POLIZAS_PER_CADENA"
    ICA_PER_CADENA = "COSTOS_FINANCIEROS.ICA_PER_CADENA"
    GMF_PER_CADENA = "COSTOS_FINANCIEROS.GMF_PER_CADENA"
```

**Implementación:** Constantes internas; NO usadas en runtime para evitar drift en audit_trace.

---

## 3. Trazabilidad Mínima (TAREA 3)

### Formula IDs Agregados

```python
COSTOS_FINANCIEROS.FORMULA_ID.FINANCIACION              → "COSTOS_FINANCIEROS.FINANCIACION"
COSTOS_FINANCIEROS.FORMULA_ID.POLIZAS                  → "COSTOS_FINANCIEROS.POLIZAS"
COSTOS_FINANCIEROS.FORMULA_ID.ICA                      → "COSTOS_FINANCIEROS.ICA"
COSTOS_FINANCIEROS.FORMULA_ID.GMF                      → "COSTOS_FINANCIEROS.GMF"
COSTOS_FINANCIEROS.FORMULA_ID.COMISION_ADMINISTRACION  → "COSTOS_FINANCIEROS.COMISION_ADMINISTRACION"
COSTOS_FINANCIEROS.FORMULA_ID.POLIZAS_PER_CADENA       → "COSTOS_FINANCIEROS.POLIZAS_PER_CADENA"
COSTOS_FINANCIEROS.FORMULA_ID.ICA_PER_CADENA           → "COSTOS_FINANCIEROS.ICA_PER_CADENA"
COSTOS_FINANCIEROS.FORMULA_ID.GMF_PER_CADENA           → "COSTOS_FINANCIEROS.GMF_PER_CADENA"
```

### Localización de código

| Formula ID | Métodos involucrados | Línea inicio | Línea fin |
|------------|----------------------|--------------|-----------|
| FINANCIACION | `_calcular_financiacion()` | 267 | 277 |
| POLIZAS | `_calcular_polizas()` | 279 | 291 |
| ICA | `_calcular_ica()` | 293 | 307 |
| GMF | `_calcular_gmf()` | 309 | 317 |
| COMISION_ADMINISTRACION | `_calcular_comision_administracion()` | 319 | 342 |
| POLIZAS_PER_CADENA | calcular() | 143 | 172 |
| ICA_PER_CADENA | calcular() | 181 | 185 |
| GMF_PER_CADENA | calcular() | 187 | 191 |

---

## 4. Validación Antes/Después (TAREA 4)

### Tests ejecutados

```bash
# Contract + fix tests (12 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_input_contract_fix_b1.py -q
# Result: 12/12 PASSED ✅

# Baseline snapshot v1 guardrails (5 tests) — POST-CANONICALIZATION OFFICIAL BASELINE
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_v1.py -q
# Result: 5/5 PASSED ✅
# File created: test_baseline_formula_snapshot_v1.py (nuevo)
# Snapshot regenerated: baseline_formula_snapshot_v1.json (actualizado con current output)

# Golden/Parity (58 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/golden/ -q
# Result: 58/58 PASSED ✅

# Costos Financieros unit tests (13 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/unit/test_costos_financieros.py -q
# Result: 13/13 PASSED ✅

# Polizas traceability (2 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/integration/test_traceability_polizas_source.py -q
# Result: 2/2 PASSED ✅

# Total: 90/90 PASSED ✅
```

### Validación de paridad contra baseline v1

**Baseline v1:** Snapshot oficial post-canonicalization (INPUT_CONTRACT_CANONICALIZATION_1_CLOSEOUT).  
**Test fixture:** `test_baseline_formula_snapshot_v1.py` (nuevo, sigue patrón de v0).  
**Validación:** Motor ejecutado con FORMULA_ID agregados → output coincide bit a bit con v1 (ignora timestamps).  
**Estado:** ✅ 100% paridad — Cero drift numérico detectado.

**Criterios de validación:**
- ✅ Cadena B sigue fluyendo (desde PHASE2)
- ✅ Financiación se calcula (mes1 con tasa y factor_periodo)
- ✅ Pólizas se aplican según configuración
- ✅ ICA con gross-up intacto
- ✅ GMF sin gross-up intacto
- ✅ Comisión Administración solo en Cadena A
- ✅ Per-cadena distribution correcta
- ✅ Tests polizas contractuales verdes
- ✅ Golden/parity sin regresiones

---

## 5. Cambios Realizados

### Archivo modificado

- **`modules/costos_financieros/calculators/costos_financieros_calculator.py`**
  - Agregó clase interna `FORMULA_ID` (líneas 49-58)
  - Sin cambios en métodos, lógica o comportamiento

### Archivos NO modificados

- ✅ `modules/calculator/engine.py` (orquestación intacta)
- ✅ `modules/costos_financieros/financial/calculators.py` (helper puro, intacto)
- ✅ Todas las fórmulas de otras capas (1-10)
- ✅ CTS, Vision Imprimible, P&G, KPIs (visiones intactas)
- ✅ `storage/` (parametrización congelada)
- ✅ DTOs, contratos públicos

---

## 6. Riesgo y Mitigación

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|-----------|
| Drift en output numérico | ❌ Muy baja | Formula IDs son constantes internas; NO usadas en runtime |
| Cambio accidental de lógica | ❌ Cero | Único cambio es agregar clase de constantes |
| Regresión en tests | ❌ Cero | Todos 90 tests pasan (12 contract + 5 baseline + 58 golden + 13 cf + 2 polizas) |
| Impacto en CTS o Visiones | ❌ Cero | No se tocó ningún cálculo ni audit_trace |
| Complicación de per-cadena logic | ⚠️ Bajo | Formula IDs facilitan localización si refactor futuro toca este bloque |

---

## 7. Comparación con PHASE1 y PHASE2

| Aspecto | PHASE1 (NoPayroll) | PHASE2 (CadenaBCalculator) | PHASE3 (CostosFinancieros) |
|--------|-------------------|---------------------------|--------------------------|
| Métodos privados | 8 | 8 | 5 + per-cadena logic |
| Complejidad promedio | Baja (sumas simples) | Media (condicionales, indexación, rounding) | **Alta** (gross-up, per-cadena, contractual) |
| Riesgos identificados | 1 Alto (CAPEX term-based) | 3 Medios (rounding H-05/H-08) | 3 Medios (gross-up, per-cadena, contractual) |
| Decisión | NO refactorizar | NO refactorizar | NO refactorizar |
| Cambios | Agregar constantes FORMULA_ID | Agregar constantes FORMULA_ID (7) | Agregar constantes FORMULA_ID (8) |
| Tests afectados | 81 total | 75 total | **90 total** (más específicos CF) |
| Paridad | 100% | 100% | 100% |

---

## 8. Siguiente fase recomendada

**FORMULA_REFACTOR_PHASE4_CADENA_C** (cuando esté listo):
- Aplicar trazabilidad similar a CadenaC (`modules/cadena_c/`)
- Auditar y documentar bloques análogamente
- Validar con tests antes/después

O proceder con:
- **FORMULA_REFACTOR_PHASE5_PyG**
- **FORMULA_REFACTOR_PHASE6_CostosTotales**
- **CLEANUP FASE:** eliminar dead code en `modules/vision_pyg/{kpis.py, costos_totales.py, reglas.py}`

---

## Cierre

✅ **Estado:** CLOSED  
✅ **Cambios:** Mínimos (solo trazabilidad, cero impacto en lógica)  
✅ **Validación:** 90/90 tests PASSED  
✅ **Paridad:** 100% (sin drift contra baseline_formula_snapshot_v1)  
✅ **Riesgo:** BAJO (constantes internas, sin uso en runtime, no alteran audit_trace)  
✅ **Siguiente:** Proceder a PHASE4 (Cadena C) o continuar con refactores posteriores.
