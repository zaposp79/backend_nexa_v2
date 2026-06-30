# FORMULA_REFACTOR_PHASE4_CADENA_C

**Refactor minimal de trazabilidad: CadenaCCalculator**

Branch: `refactor/modular-pure`  
Fecha: 2026-06-06  
Status: **CLOSED**

---

## Objetivo

Mejorar trazabilidad y localización de fórmulas de Cadena C (Capa 6) sin cambiar comportamiento ni output numérico.

---

## Alcance

- **Archivo principal:** `modules/cadena_c/reglas.py`
- **Clase pública:** `CadenaCCalculator`
- **Cambios permitidos:** Constantes internas, documentación, formula_ids (cero impacto en output)
- **Cambios PROHIBIDOS:** Refactor de métodos, cambio de lógica, modificación de audit_trace output, cambios en contratos públicos

---

## 1. Auditoría de Bloques (TAREA 1)

### Estructura actual

| Bloque | Método | Responsabilidad | Inputs | Outputs | Riesgo | Notas |
|--------|--------|-----------------|--------|---------|--------|-------|
| **Canales / Tarifa Proveedor** | `_costo_tarifa_proveedor()` | IA provider cost: volume × tariff × factor | canales.volumen_mensual, tarifa_proveedor, factor_ajuste | float | Bajo | H-05 cop_round per-channel |
| **OPEX Fijo Integración** | `_costo_opex_fijo()` | Fixed integration costs per channel | canales.opex_fijo_integ, factor_ajuste | float | Bajo | H-05 cop_round per-channel |
| **OPEX Variable Integración** | `_costo_opex_variable()` | Variable integration costs proportional to volume | canales.opex_var_integ, factor_ajuste | float | Bajo | H-05 cop_round per-channel |
| **Amortización Inversión** | `_costo_amortizacion_inversion()` | Monthly amortization of annual platform investment | inversion_anual, meses=12 | float | Bajo | Lineal, sin factor financiero |
| **Equipo Integración** | `_costo_equipo()` | Specialized personnel + tools (conditional on volume > 0) | costo_equipo_integ, opex_herramientas_integ, factor_ajuste | float | Bajo | H-08 cop_round total |
| **Escalamiento** | `_costo_escalamiento()` | Capacity scaling cost per channel | canales.volumen, pct_escalamiento, costo_escalamiento, factor_ajuste | float | Bajo | H-05 cop_round per-channel |
| **HITL** | `_costo_hitl()` | Human-in-the-Loop team (conditional on volume > 0) | costo_personal_hitl, opex_herramientas_hitl, factor_ajuste | float | Bajo | H-08 cop_round total |
| **Total Mensual** | calcular_para_mes() | Sum of all 7 components, audit trace | todos los anteriores | ResultadoCadenaC | Bajo | audit_trace output intacto |

### Hallazgos clave

✅ **Métodos bien aislados:** Cada componente tiene su propio método privado.  
✅ **Lógica limpia:** Condicionales simples (volumen > 0 para equipo/HITL).  
✅ **H-05/H-08 FIX documentado:** Rounding per-channel y total explícito.  
✅ **audit_trace claro:** Inputs, intermedios, resultado, source documentados.  
✅ **Factor ajuste centralizado:** `_factor_ajuste_tecnologico()` en un lugar.  

---

## 2. Decisión de Refactor (TAREA 2)

### Evaluación: Refactor vs. Trazabilidad

| Aspecto | Decisión | Justificación |
|---------|----------|---------------|
| **Extraer submétodos por canal** | ❌ NO | Lógica ya está per-channel con cop_round; extra métodos = ruido |
| **Crear cadena_c_formulas.py** | ❌ NO | Mantener vertical slice coherence (cadena_c responsibility) |
| **Re-centralizar en modules/calculator/formulas/** | ❌ NO | Contra FASE Y; requeriría refactor arquitectónico sin valor |
| **Agregar formula_ids internos** | ✅ SÍ | Zero-risk; mejora trazabilidad futura sin cambiar output |

### Cambios realizados

**Único cambio:** Agregué clase interna `CadenaCCalculator.FORMULA_ID` con 8 constantes:

```python
class FORMULA_ID:
    """Internal formula identifiers for traceability."""
    CANALES = "CADENA_C.CANALES"
    EQUIPO_TRANSVERSAL = "CADENA_C.EQUIPO_TRANSVERSAL"
    INVERSION_ANUAL = "CADENA_C.INVERSION_ANUAL"
    OPEX_FIJO_INTEGRACION = "CADENA_C.OPEX_FIJO_INTEGRACION"
    OPEX_VARIABLE_INTEGRACION = "CADENA_C.OPEX_VARIABLE_INTEGRACION"
    ESCALAMIENTO = "CADENA_C.ESCALAMIENTO"
    HITL = "CADENA_C.HITL"
    TOTAL_MENSUAL = "CADENA_C.TOTAL_MENSUAL"
```

**Implementación:** Constantes internas; NO usadas en runtime para evitar drift en audit_trace.

---

## 3. Trazabilidad Mínima (TAREA 3)

### Formula IDs Agregados

```python
CADENA_C.FORMULA_ID.CANALES                        → "CADENA_C.CANALES"
CADENA_C.FORMULA_ID.EQUIPO_TRANSVERSAL             → "CADENA_C.EQUIPO_TRANSVERSAL"
CADENA_C.FORMULA_ID.INVERSION_ANUAL                → "CADENA_C.INVERSION_ANUAL"
CADENA_C.FORMULA_ID.OPEX_FIJO_INTEGRACION          → "CADENA_C.OPEX_FIJO_INTEGRACION"
CADENA_C.FORMULA_ID.OPEX_VARIABLE_INTEGRACION      → "CADENA_C.OPEX_VARIABLE_INTEGRACION"
CADENA_C.FORMULA_ID.ESCALAMIENTO                   → "CADENA_C.ESCALAMIENTO"
CADENA_C.FORMULA_ID.HITL                           → "CADENA_C.HITL"
CADENA_C.FORMULA_ID.TOTAL_MENSUAL                  → "CADENA_C.TOTAL_MENSUAL"
```

### Localización de código

| Formula ID | Métodos involucrados | Línea inicio | Línea fin |
|------------|----------------------|--------------|-----------|
| CANALES | `_costo_tarifa_proveedor()` | 130 | 138 |
| EQUIPO_TRANSVERSAL | `_costo_equipo()` + equipo_transversal (ParametrosCadenaC) | 164 | 176 |
| INVERSION_ANUAL | `_costo_amortizacion_inversion()` | 154 | 162 |
| OPEX_FIJO_INTEGRACION | `_costo_opex_fijo()` | 140 | 145 |
| OPEX_VARIABLE_INTEGRACION | `_costo_opex_variable()` | 147 | 152 |
| ESCALAMIENTO | `_costo_escalamiento()` | 178 | 186 |
| HITL | `_costo_hitl()` | 188 | 200 |
| TOTAL_MENSUAL | calcular_para_mes() | 57 | 117 |

---

## 4. Validación Antes/Después (TAREA 4)

### Tests ejecutados

```bash
# Contract + fix tests (12 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_input_contract_fix_b1.py -q
# Result: 12/12 PASSED ✅

# Baseline snapshot v1 guardrails (5 tests) — Cadena A + B
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_v1.py -q
# Result: 5/5 PASSED ✅

# Cadena C baseline guardrails (5 tests) — Cadena C con costo > 0
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py -q
# Result: 5/5 PASSED ✅

# Golden/Parity (58 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/golden/ -q
# Result: 58/58 PASSED ✅

# Total: 80/80 PASSED ✅
```

### Validación de paridad contra baseline_cadena_c_v1

**Baseline v1 Cadena C:** Snapshot oficial con Cadena C activa (request_cadena_c_active.json).  
**Test fixture:** `test_baseline_formula_snapshot_cadena_c_v1.py` (sigue patrón de v1 oficial).  
**Validación:** Motor ejecutado con FORMULA_ID agregados → output coincide bit a bit con baseline (ignora timestamps).  
**Estado:** ✅ 100% paridad — Cero drift numérico detectado.

**Criterios de validación:**
- ✅ Tarifa proveedor intacta (vol × tarifa × factor)
- ✅ OPEX fijo/variable intactos (per-channel + H-05 rounding)
- ✅ Amortización inversión intacta (inversion_anual / 12)
- ✅ Equipo integración intacto (conditional on volumen > 0)
- ✅ Escalamiento intacto (vol × pct × costo × factor + H-05)
- ✅ HITL intacto (conditional on volumen > 0)
- ✅ Total mensual intacto (suma de 7 componentes)
- ✅ costo_c mes1 = 101,200,000.0 validado
- ✅ costo_c total = 2,491,534,080.0 validado
- ✅ Golden/parity sin regresiones

---

## 5. Cambios Realizados

### Archivo modificado

- **`modules/cadena_c/reglas.py`**
  - Agregó clase interna `FORMULA_ID` (líneas 53-61)
  - Sin cambios en métodos, lógica o comportamiento

### Archivos NO modificados

- ✅ `modules/calculator/engine.py` (orquestación intacta)
- ✅ `modules/cadena_c/` servicios, DTOs, API (intactos)
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
| Regresión en tests | ❌ Cero | Todos 80 tests pasan (12 + 5 + 5 + 58) |
| Impacto en CTS o Visiones | ❌ Cero | No se tocó ningún cálculo ni audit_trace |
| Cambio en ParametrosCadenaC | ❌ Cero | No modificado |

---

## 7. Comparación con PHASE1, PHASE2, PHASE3

| Aspecto | PHASE1 (NoPayroll) | PHASE2 (CadenaBCalculator) | PHASE3 (CostosFinancieros) | PHASE4 (CadenaCCalculator) |
|--------|-------------------|---------------------------|--------------------------|--------------------------|
| Métodos privados | 8 | 8 | 5 + per-cadena logic | 7 + factor ajuste |
| Complejidad promedio | Baja (sumas simples) | Media (condicionales, indexación, rounding) | Alta (gross-up, per-cadena, contractual) | Media (rounding H-05/H-08, condicionales) |
| Riesgos identificados | 1 Alto (CAPEX term-based) | 3 Medios (rounding H-05/H-08) | 3 Medios (gross-up, per-cadena, contractual) | 2 Bajos (rounding H-05/H-08, condicionales) |
| Decisión | NO refactorizar | NO refactorizar | NO refactorizar | NO refactorizar |
| Cambios | Agregar constantes FORMULA_ID (8) | Agregar constantes FORMULA_ID (7) | Agregar constantes FORMULA_ID (8) | Agregar constantes FORMULA_ID (8) |
| Tests afectados | 81 total | 75 total | 90 total | **80 total** (mismo que Cadena C baseline) |
| Paridad | 100% | 100% | 100% | **100%** |

---

## 8. Notas para fase futura

### Cadena C es Capa 6 (integración IA)

En el pipeline de 10 capas:
- Capa 1: Entrada
- Capa 2: Nómina Cadena A
- Capa 3: NoPayroll Cadena A
- Capa 4-5: Cadena B (Digital)
- **Capa 6: Cadena C (IA) ← PHASE4 aquí**
- Capa 7: Costos Totales
- Capa 8: Costos Financieros
- Capa 9: P&G
- Capa 10: KPIs

### Baseline Cadena C es técnico, no certificación Excel final

El snapshot `baseline_formula_snapshot_cadena_c_v1.json` es un guardrail de regresión, no una validación de certificación contra Excel V2-7. Para certificación completa de Cadena C, requeriría:
- Request fixture con datos reales de deal
- Comparación manual con Excel V2-7 módulo Cadena C
- Validación de factor_ajuste_tecnologico (Excel: se aplica en mes >= mes_aplicacion_aumento)
- Validación de pólizas contractuales si aplican

### Archivos de preparación de baseline

Para una futura auditoría Excel completa de Cadena C, estos artefactos ya existen:
- `tests/refactor/request_cadena_c_active.json` — Fixture activo
- `tests/refactor/baseline_formula_snapshot_cadena_c_v1.json` — Snapshot oficial
- `tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py` — Test guardrails

---

## 9. Siguiente fase recomendada

Opciones:

1. **FORMULA_REFACTOR_PHASE5_COSTOS_TOTALES** (Capa 7)
   - Auditar `modules/vision_costos_totales/` o centralizado en `modules/calculator/`
   - Aplicar trazabilidad análoga

2. **FORMULA_REFACTOR_PHASE6_PyG** (Capa 9)
   - Auditar `modules/vision_pyg/`
   - Aplicar trazabilidad análoga

3. **CLEANUP FASE** (Dead code)
   - Eliminar métodos sin consumidores en `modules/vision_pyg/{kpis.py, costos_totales.py, reglas.py}`
   - Usar `cleanup-agent`

4. **FORMULA_REFACTOR_VALIDATION_EXCEL_COMPLETE**
   - Crear fixtures con deals reales
   - Comparar outputs contra Excel V2-7 per module
   - Para cada Cadena: request + Excel extract + validación

---

## Cierre

✅ **Estado:** CLOSED  
✅ **Cambios:** Mínimos (solo trazabilidad, cero impacto en lógica)  
✅ **Validación:** 80/80 tests PASSED  
✅ **Paridad:** 100% (sin drift contra baseline_formula_snapshot_cadena_c_v1)  
✅ **Riesgo:** BAJO (constantes internas, sin uso en runtime, no alteran audit_trace)  
✅ **Cadena C:** costo_c mes1 = 101,200,000.0, total = 2,491,534,080.0  

---

## Artefactos

- ✅ `modules/cadena_c/reglas.py` — FORMULA_ID agregados
- ✅ `docs/refactor/formula_refactor_phase4_cadena_c.md` — Esta documentación
