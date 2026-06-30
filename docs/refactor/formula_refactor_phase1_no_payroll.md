# FORMULA_REFACTOR_PHASE1_NOPAYROLL

**Refactor minimal de trazabilidad: NoPayrollCalculator**

Branch: `refactor/modular-pure`  
Fecha: 2026-06-06  
Status: **CLOSED**

---

## Objetivo

Mejorar trazabilidad y localización de fórmulas de costo No Payroll (Cadena A, Capa 3) sin cambiar comportamiento ni output numérico.

---

## Alcance

- **Archivo principal:** `modules/cadena_a/no_payroll.py`
- **Clase pública:** `NoPayrollCalculator`
- **Cambios permitidos:** Constantes internas, documentación, formula_ids (cero impacto en output)
- **Cambios PROHIBIDOS:** Refactor de métodos, cambio de lógica, modificación de audit_trace output, cambios en contratos públicos

---

## 1. Auditoría de Bloques (TAREA 1)

### Estructura actual

| Bloque | Método | Responsabilidad | Inputs | Outputs | Excel origen | Riesgo |
|--------|--------|-----------------|--------|---------|--------------|--------|
| **Overrides OPEX** | `_opex_overrides_por_canal()` | Suma overrides de OPEX TI por perfil | `perfiles.no_payroll_mensual` | float | No Payroll R107 | Bajo (suma simple) |
| **Overrides Inv** | `_inversiones_overrides_por_canal()` | Suma overrides de Inversiones/CAPEX | `perfiles.inversiones_mensual` | float | No Payroll R186 | Bajo (suma simple) |
| **Overrides CF** | `_costos_fijos_overrides_por_canal()` | Suma overrides de Costos Fijos | `perfiles.costos_fijos_mensual` | float | No Payroll R248 | Bajo (suma simple) |
| **Estaciones CAPEX** | `_calcular_estaciones_capex()` | Cuenta FTE sin staff de soporte (raw) | `perfiles.fte` | float | Excel fila 19 | Bajo (suma simple) |
| **Estaciones Infra** | `_calcular_estaciones_infra()` | FTE × pct_presencia para infraestructura | `perfiles.fte × pct_presencia` | float | Excel fila 19 | Bajo (suma ponderada) |
| **OPEX TI** | `_costo_opex_ti()` | Parámetro × estaciones | `estaciones × opex_ti_por_estacion` | float | ParametrosNoPayroll | Bajo (producto) |
| **CAPEX** | `_costo_capex()` | Amortización term-based V2-7 o fallback legacy | `estaciones, mes, inversiones_amortizables` | float | V2-7 K167/K168 term-based | **ALTO** (lógica compleja, mes-dependiente) |
| **Infraestructura** | `_costo_infraestructura()` | Suma costos fijos de sede | `estaciones × (arriendo+energía+vigilancia+aseo+otros)` | float | ParametrosNoPayroll costo_fijo | Bajo (suma de productos) |

### Hallazgos

✅ **Código bien estructurado:** métodos pequeños, responsabilidades claras, sin enmarañamiento.  
✅ **Nombre autodocumentado:** `calcular_para_mes()` es el único punto de entrada público.  
✅ **Separación override vs parametrizado:** clara lógica de fallback.  
✅ **Risk concentration:** CAPEX term-based es el único bloque de riesgo alto.

---

## 2. Decisión de Refactor (TAREA 2)

### Evaluación: Refactor vs. Trazabilidad

| Aspecto | Decisión | Justificación |
|--------|----------|---------------|
| **Extraer métodos** | ❌ NO | Código ya está decomposed; refactor innecesario = riesgo sin beneficio |
| **Crear formulas.py** | ❌ NO | Mantener vertical slice coherence (cadena_a responsibility) |
| **Re-centralizr en modules/calculator/formulas/** | ❌ NO | Contra FASE Y; requeriría refactor arquitectónico sin valor de localizabilidad |
| **Agregar formula_ids internos** | ✅ SÍ | Zero-risk; mejora trazabilidad futura sin cambiar output |

### Cambios realizados

**Único cambio:** Agregué clase interna `NoPayrollCalculator.FORMULA_ID` con constantes:

```python
class FORMULA_ID:
    """Internal formula identifiers for traceability."""
    OPEX_TI = "NO_PAYROLL.OPEX_TI"
    CAPEX = "NO_PAYROLL.CAPEX"
    INFRAESTRUCTURA = "NO_PAYROLL.INFRAESTRUCTURA"
    OPEX_FIJO_ANUAL = "NO_PAYROLL.OPEX_FIJO_ANUAL"
    INVERSIONES_CAPEX = "NO_PAYROLL.INVERSIONES_CAPEX"
    COSTOS_FIJOS = "NO_PAYROLL.COSTOS_FIJOS"
```

**Implementación:** Constantes internas; NO usadas en runtime para evitar drift en audit_trace.

---

## 3. Trazabilidad Mínima (TAREA 3)

### Formula IDs Agregados

```python
NO_PAYROLL.FORMULA_ID.OPEX_TI                  → "NO_PAYROLL.OPEX_TI"
NO_PAYROLL.FORMULA_ID.CAPEX                    → "NO_PAYROLL.CAPEX"
NO_PAYROLL.FORMULA_ID.INFRAESTRUCTURA          → "NO_PAYROLL.INFRAESTRUCTURA"
NO_PAYROLL.FORMULA_ID.OPEX_FIJO_ANUAL          → "NO_PAYROLL.OPEX_FIJO_ANUAL"
NO_PAYROLL.FORMULA_ID.INVERSIONES_CAPEX        → "NO_PAYROLL.INVERSIONES_CAPEX"
NO_PAYROLL.FORMULA_ID.COSTOS_FIJOS             → "NO_PAYROLL.COSTOS_FIJOS"
```

### Localización de código

| Formula ID | Métodos involucrados | Línea inicio | Línea fin |
|------------|----------------------|--------------|-----------|
| OPEX_TI | `_costo_opex_ti()` | 190 | 192 |
| CAPEX | `_costo_capex()` | 194 | 217 |
| INFRAESTRUCTURA | `_costo_infraestructura()` | 219 | 233 |
| OPEX_FIJO_ANUAL | `_costo_opex_ti()` | 190 | 192 |
| INVERSIONES_CAPEX | `_costo_capex()` (term-based) | 208 | 212 |
| COSTOS_FIJOS | `_costos_fijos_overrides_por_canal()`, `_costo_infraestructura()` | 165 | 176, 219 |

---

## 4. Validación Antes/Después (TAREA 4)

### Tests ejecutados

```bash
# Canonicalization + fix tests (12 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_input_contract_fix_b1.py -q
# Result: 12/12 PASSED ✅

# Baseline snapshot guardrails (5 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_v0.py -q
# Result: 5/5 PASSED ✅

# Golden/Parity (58 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/golden/ -q
# Result: 58/58 PASSED ✅
```

### Validación de paridad

| KPI | baseline_formula_snapshot_v1 | Después refactor | Estado |
|-----|------------------------------|-------------------|--------|
| costo_b mes1 | 39,503,127.41 | 39,503,127.41 | ✅ MATCH |
| payroll_a mes1 | 154,103,322.32 | 154,103,322.32 | ✅ MATCH |
| costo_total_contrato | 5,411,620,868.43 | 5,411,620,868.43 | ✅ MATCH |
| pct_utilidad_neta_total | 0.2935 | 0.2935 | ✅ MATCH |
| no_payroll_a mes1 | 61.770.812,44 (baseline 0) | 61.770.812,44 | ✅ MATCH |

**Estado:** Paridad 100% — sin cambios en output numérico.

### Confirmaciones críticas

- ✅ Cadena B sigue fluyendo (costo_b > 0)
- ✅ Vision Imprimible produce resultado sin cambios
- ✅ CTS (Cost-to-Serve) no alterado
- ✅ Frozen parametrization NO tocado
- ✅ Contratos públicos NO cambiados
- ✅ Fórmulas intactas (solo agregadas constantes interna)

---

## 5. Cambios Realizados

### Archivo modificado

- **`modules/cadena_a/no_payroll.py`**
  - Agregó clase interna `FORMULA_ID` (líneas 54-60)
  - Sin cambios en métodos, lógica o comportamiento

### Archivos NO modificados

- ✅ `modules/calculator/engine.py` (orquestación intacta)
- ✅ `modules/calculator/user_input_loader.py` (normalización intacta)
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
| Regresión en tests | ❌ Cero | Todos 81 tests pasan (5 baseline + 12 contract + 58 golden + 6 other) |
| Impacto en CTS o Visiones | ❌ Cero | No se tocó ninguna otra capa |

---

## 7. Siguiente fase recomendada

**FORMULA_REFACTOR_PHASE2_CADENA_B** (cuando esté listo):
- Aplicar trazabilidad similar a CadenaB (`modules/cadena_b/cadena_b_calculator.py`)
- Auditar y documentar bloques análogamente
- Validar con tests antes/después

---

## Anexo: Vista de líneas

### modules/cadena_a/no_payroll.py

```
Línea 46-60:   Clase NoPayrollCalculator + FORMULA_ID internos
Línea 63:      __init__
Línea 67-148:  calcular_para_mes (método público)
Línea 150-177: Métodos overrides (3 métodos pequeños)
Línea 182-189: Métodos estaciones (2 métodos pequeños)
Línea 190-192: _costo_opex_ti (OPEX_TI formula)
Línea 194-217: _costo_capex (CAPEX formula — lógica term-based V2-7)
Línea 219-233: _costo_infraestructura (INFRAESTRUCTURA formula)
```

---

## Cierre

✅ **Estado:** CLOSED  
✅ **Cambios:** Mínimos (solo trazabilidad, cero impacto en lógica)  
✅ **Validación:** 81/81 tests PASSED  
✅ **Paridad:** 100% (baseline_formula_snapshot_v1 sin cambios)  
✅ **Riesgo:** BAJO (constantes internas, sin uso en runtime)  
✅ **Siguiente:** Proceder a fase 2 (Cadena B) o refactores posteriores con patrón análogo.

