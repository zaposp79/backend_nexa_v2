# FORMULA_REFACTOR_PHASE2_CADENA_B

**Refactor minimal de trazabilidad: CadenaBCalculator**

Branch: `refactor/modular-pure`  
Fecha: 2026-06-06  
Status: **CLOSED**

---

## Objetivo

Mejorar trazabilidad y localización de fórmulas de Cadena B (Plataforma Digital, Capas 4-5) sin cambiar comportamiento ni output numérico.

---

## Alcance

- **Archivo principal:** `modules/cadena_b/reglas.py`
- **Clase pública:** `CadenaBCalculator`
- **Cambios permitidos:** Constantes internas, documentación, formula_ids (cero impacto en output)
- **Cambios PROHIBIDOS:** Refactor de métodos, cambio de lógica, modificación de rounding (H-05/H-08), cambios en contratos públicos

---

## 1. Auditoría de Bloques (TAREA 1)

### Estructura actual

| Bloque | Método | Responsabilidad | Inputs | Outputs | Riesgo | Notas |
|--------|--------|-----------------|--------|---------|--------|-------|
| **Factor Personal** | `_factor_ajuste_personal()` | Incremento salarial anual | mes, pct_aumento, mes_aplicacion | float | Bajo | Usa calcular_factor_aumento() |
| **Volúmenes** | `_volumenes_por_modalidad()` | Suma por modalidad Inbound/Outbound | canales | (vol_ib, vol_ob) | Bajo | Suma simple |
| **OPEX Fijo** | `_costo_opex_fijo()` | OPEX fijo de plataforma | canales.opex_fijo | float | Bajo | Σ(opex_fijo_canal) |
| **CAPEX** | `_costo_inversiones()` | Inversiones amortizadas | inversion_mensual (param) | float | Bajo | Parámetro directo |
| **Soporte Mantenimiento** | `_costo_sm()` | Equipo S&M (personal + herramientas) | vol_ib, vol_ob, factor | float | **Medio** | Condicional (vol>0), indexación personal, H-08 cop_round |
| **Costo Variable** | `_costo_variable()` | Costos por volumen y tarifa | canales | float | **Medio** | Σ(vol × tarifa), H-05 cop_round **por canal antes de sumar** |
| **Escalamiento** | `_costo_escalamiento()` | Escalamiento de capacidad | canales | float | **Medio** | Σ(vol × pct_esc × costo_esc), H-05 cop_round **por canal** |
| **HITL** | `_costo_hitl()` | Equipo HITL (personal + herramientas) | vol_ib, vol_ob, factor | float | **Medio** | Condicional (vol>0), indexación, H-08 cop_round |

### Hallazgos clave

✅ **Código bien decomposed:** Cada método tiene responsabilidad clara y única.  
✅ **Documentación de fixes:** H-05 (variable/escalamiento) y H-08 (SM/HITL) referenciados para paridad Excel.  
✅ **Rounding strategy:** `cop_round()` aplicado por canal (H-05) o total (H-08) según especificación.  
✅ **Factor reutilizado:** `factor_personal` se calcula una sola vez y se pasa a SM/HITL.  
✅ **Sin enmarañamiento:** Separación clara entre cálculos de helpers (factor, volúmenes) y componentes de costo.

---

## 2. Decisión de Refactor (TAREA 2)

### Evaluación: Refactor vs. Trazabilidad

| Aspecto | Decisión | Justificación |
|---------|----------|---------------|
| **Extraer métodos** | ❌ NO | Código ya está decomposed; refactor innecesario |
| **Crear cadena_b_formulas.py** | ❌ NO | Mantener vertical slice coherence (cadena_b responsibility) |
| **Re-centralizar en modules/calculator/formulas/** | ❌ NO | Contra FASE Y; requeriría refactor arquitectónico sin valor |
| **Reorganizar por tipo (opex/capex/sm/var/esc/hitl)** | ❌ NO | Orden actual (cálculo > componentes) es lógico; cambiar = riesgo de drift con cop_round |
| **Agregar formula_ids internos** | ✅ SÍ | Zero-risk; mejora trazabilidad futura sin cambiar output |

### Cambios realizados

**Único cambio:** Agregué clase interna `CadenaBCalculator.FORMULA_ID` con constantes:

```python
class FORMULA_ID:
    """Internal formula identifiers for traceability."""
    OPEX_FIJO = "CADENA_B.OPEX_FIJO"
    INVERSIONES = "CADENA_B.INVERSIONES"
    SOPORTE_MANTENIMIENTO = "CADENA_B.SOPORTE_MANTENIMIENTO"
    COSTO_VARIABLE = "CADENA_B.COSTO_VARIABLE"
    ESCALAMIENTO = "CADENA_B.ESCALAMIENTO"
    HITL = "CADENA_B.HITL"
    FACTOR_PERSONAL = "CADENA_B.FACTOR_PERSONAL"
```

**Implementación:** Constantes internas; NO usadas en runtime para evitar drift en audit_trace (aprendizaje de PHASE1).

---

## 3. Trazabilidad Mínima (TAREA 3)

### Formula IDs Agregados

```python
CADENA_B.FORMULA_ID.OPEX_FIJO                  → "CADENA_B.OPEX_FIJO"
CADENA_B.FORMULA_ID.INVERSIONES                → "CADENA_B.INVERSIONES"
CADENA_B.FORMULA_ID.SOPORTE_MANTENIMIENTO      → "CADENA_B.SOPORTE_MANTENIMIENTO"
CADENA_B.FORMULA_ID.COSTO_VARIABLE             → "CADENA_B.COSTO_VARIABLE"
CADENA_B.FORMULA_ID.ESCALAMIENTO               → "CADENA_B.ESCALAMIENTO"
CADENA_B.FORMULA_ID.HITL                       → "CADENA_B.HITL"
CADENA_B.FORMULA_ID.FACTOR_PERSONAL            → "CADENA_B.FACTOR_PERSONAL"
```

### Localización de código

| Formula ID | Métodos involucrados | Línea inicio | Línea fin |
|------------|----------------------|--------------|-----------|
| FACTOR_PERSONAL | `_factor_ajuste_personal()` | 127 | 133 |
| VOLUMENES | `_volumenes_por_modalidad()` | 135 | 140 |
| OPEX_FIJO | `_costo_opex_fijo()` | 142 | 144 |
| INVERSIONES | `_costo_inversiones()` | 146 | 148 |
| SOPORTE_MANTENIMIENTO | `_costo_sm()` | 150 | 164 |
| COSTO_VARIABLE | `_costo_variable()` | 166 | 175 |
| ESCALAMIENTO | `_costo_escalamiento()` | 177 | 185 |
| HITL | `_costo_hitl()` | 187 | 200 |

---

## 4. Validación Antes/Después (TAREA 4)

### Tests ejecutados

```bash
# Contract + fix tests (12 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_input_contract_fix_b1.py -q
# Result: 12/12 PASSED ✅

# Baseline snapshot guardrails (5 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_v0.py -q
# Result: 5/5 PASSED ✅

# Golden/Parity (58 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/golden/ -q
# Result: 58/58 PASSED ✅

# Total: 75/75 PASSED
```

### Validación de paridad

| KPI | baseline_formula_snapshot_v1 | Después refactor | Estado |
|-----|------------------------------|-------------------|--------|
| costo_b mes1 | 39,503,127.41 | 39,503,127.41 | ✅ MATCH |
| payroll_a mes1 | 154,103,322.32 | 154,103,322.32 | ✅ MATCH |
| costo_total_contrato | 5,411,620,868.43 | 5,411,620,868.43 | ✅ MATCH |
| pct_utilidad_neta_total | 0.2935 | 0.2935 | ✅ MATCH |

**Estado:** Paridad 100% — sin cambios en output numérico.

### Confirmaciones críticas

- ✅ Cadena B sigue fluyendo (costo_b mes1 = 39,503,127.41)
- ✅ Vision Imprimible produce resultado sin cambios
- ✅ CTS (Cost-to-Serve) no alterado
- ✅ Frozen parametrization NO tocado
- ✅ Contratos públicos NO cambiados
- ✅ Rounding (H-05/H-08) intacto
- ✅ Audit trace output IDÉNTICO

---

## 5. Cambios Realizados

### Archivo modificado

- **`modules/cadena_b/reglas.py`**
  - Agregó clase interna `FORMULA_ID` (líneas 54-62)
  - Sin cambios en métodos, lógica o comportamiento

### Archivos NO modificados

- ✅ `modules/calculator/engine.py` (orquestación intacta)
- ✅ `modules/cadena_a/` (Cadena A intacta)
- ✅ `modules/cadena_c/` (Cadena C intacta)
- ✅ CTS, Vision Imprimible, P&G, KPIs (visiones intactas)
- ✅ `storage/` (parametrización congelada)
- ✅ DTOs, contratos públicos

---

## 6. Riesgo y Mitigación

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|-----------|
| Drift en output numérico | ❌ Muy baja | Formula IDs son constantes internas; NO usadas en runtime |
| Cambio accidental de lógica/rounding | ❌ Cero | Único cambio es agregar clase de constantes |
| Regresión en tests | ❌ Cero | Todos 75 tests pasan (12 contract + 5 baseline + 58 golden) |
| Impacto en CTS o Visiones | ❌ Cero | No se tocó ningún cálculo ni audit_trace |
| Complicación futura | ⚠️ Bajo | Formula IDs facilitan localización si se necesita refactor futuro |

---

## 7. Diferencias vs. PHASE1_NOPAYROLL

| Aspecto | PHASE1 (NoPayroll) | PHASE2 (CadenaBCalculator) |
|--------|-------------------|---------------------------|
| Métodos privados | 8 (overrides, estaciones, costos) | 8 (factor, volúmenes, 6 costos) |
| Complejidad promedio | Baja (sumas simples) | Media (condicionales, indexación, rounding) |
| Riesgos identificados | 1 Alto (CAPEX term-based) | 3 Medios (SM, variable, escalamiento - por rounding) |
| Decisión | NO refactorizar | NO refactorizar |
| Cambios | Agregar constantes FORMULA_ID | Agregar constantes FORMULA_ID (7 vs 6) |
| Tests afectados | 81 total (5+12+58+6) | 75 total (5+12+58) — no hay tests B específicos |
| Paridad | 100% | 100% |

---

## 8. Siguiente fase recomendada

**FORMULA_REFACTOR_PHASE3_CADENA_C** (cuando esté listo):
- Aplicar trazabilidad similar a CadenaC (`modules/cadena_c/`)
- Auditar y documentar bloques análogamente
- Validar con tests antes/después

O proceder con:
- **FORMULA_REFACTOR_PHASE4_COSTOS_FINANCIEROS**
- **FORMULA_REFACTOR_PHASE5_PyG**
- **Cleanup FASE:** eliminar dead code `modules/vision_pyg/{kpis,costos_totales,reglas}.py`

---

## Cierre

✅ **Estado:** CLOSED  
✅ **Cambios:** Mínimos (solo trazabilidad, cero impacto en lógica)  
✅ **Validación:** 75/75 tests PASSED  
✅ **Paridad:** 100% (baseline_formula_snapshot_v1 sin cambios)  
✅ **Riesgo:** BAJO (constantes internas, sin uso en runtime, no alteran audit_trace)  
✅ **Siguiente:** Proceder a PHASE3 (Cadena C) o continuar con refactores posteriores.

