# FORMULA_REFACTOR_PHASE5_COSTOS_TOTALES

**Refactor minimal de trazabilidad: CostosTotalesCalculator**

Branch: `refactor/modular-pure`  
Fecha: 2026-06-06  
Status: **CLOSED**

---

## Objetivo

Mejorar trazabilidad y localización de agregaciones de Costos Totales (Capa 7) sin cambiar comportamiento ni output numérico.

---

## Alcance

- **Archivo principal:** `modules/pyg/services/costos_totales_calculator.py`
- **Clase pública:** `CostosTotalesCalculator`
- **Cambios permitidos:** Constantes internas, documentación, formula_ids (cero impacto en output)
- **Cambios PROHIBIDOS:** Refactor de métodos, cambio de delegación, modificación de DTO, cambios en contratos públicos

---

## 1. Auditoría de Bloques (TAREA 1)

### Estructura actual

| Bloque | Responsabilidad | Inputs | Outputs | Riesgo | Notas |
|--------|-----------------|--------|---------|--------|-------|
| **ORQUESTADOR** | Coordina cálculos de 4 cadenas (A payroll, A no-payroll, B, C) | perfiles_a, mes | CostosTotalesMes | Bajo | Patrón orquestador puro, sin lógica |
| **PAYROLL_A** | Delega a NominaCalculator | perfiles_a, mes | nomina.total | Bajo | Capa 2 del pipeline |
| **NO_PAYROLL_A** | Delega a NoPayrollCalculator | perfiles_a, mes | no_payroll.total | Bajo | Capa 3 del pipeline |
| **COSTO_B** | Delega a CadenaBCalculator | mes | cadena_b.total | Bajo | Capas 4-5 del pipeline |
| **COSTO_C** | Delega a CadenaCCalculator (dos variantes) | mes | cadena_c.total (fin) + cadena_c.total_pyg (P&G) | Bajo | Capa 6 del pipeline; nota especial: dual |

### Hallazgos clave

✅ **Patrón orquestador:** Sin lógica de negocio; pura delegación.  
✅ **Inyección de dependencias:** Limpia, sin acoplamiento.  
✅ **Composición:** 4 calculadores especializados correctamente compuestos.  
✅ **DTO claro:** CostosTotalesMes estructura retorno de forma predecible.  
✅ **Variante costo_c:** Documentada (total_pyg para P&G visual, total para base financiera).  

---

## 2. Decisión de Refactor (TAREA 2)

### Evaluación: Refactor vs. Trazabilidad

| Aspecto | Decisión | Justificación |
|---------|----------|---------------|
| **Extraer submétodos** | ❌ NO | Método ya es transparente (5 líneas de delegación) |
| **Crear submódulo** | ❌ NO | Responsabilidad centrada; location es correcta |
| **Cambiar estructura DTO** | ❌ NO | CostosTotalesMes ya está bien definido |
| **Agregar formula_ids internos** | ✅ SÍ | Zero-risk; mejora trazabilidad futura sin cambiar output |

### Cambios realizados

**Único cambio:** Agregué clase interna `CostosTotalesCalculator.FORMULA_ID` con 5 constantes:

```python
class FORMULA_ID:
    """Internal formula identifiers for traceability."""
    PAYROLL_A = "COSTOS_TOTALES.PAYROLL_A"
    NO_PAYROLL_A = "COSTOS_TOTALES.NO_PAYROLL_A"
    COSTO_B = "COSTOS_TOTALES.COSTO_B"
    COSTO_C = "COSTOS_TOTALES.COSTO_C"
    TOTAL_MENSUAL = "COSTOS_TOTALES.TOTAL_MENSUAL"
```

**Implementación:** Constantes internas; NO usadas en runtime para evitar cambios en output.

---

## 3. Trazabilidad Mínima (TAREA 3)

### Formula IDs Agregados

```python
COSTOS_TOTALES.FORMULA_ID.PAYROLL_A              → "COSTOS_TOTALES.PAYROLL_A"
COSTOS_TOTALES.FORMULA_ID.NO_PAYROLL_A           → "COSTOS_TOTALES.NO_PAYROLL_A"
COSTOS_TOTALES.FORMULA_ID.COSTO_B                → "COSTOS_TOTALES.COSTO_B"
COSTOS_TOTALES.FORMULA_ID.COSTO_C                → "COSTOS_TOTALES.COSTO_C"
COSTOS_TOTALES.FORMULA_ID.TOTAL_MENSUAL          → "COSTOS_TOTALES.TOTAL_MENSUAL"
```

### Localización de código

| Formula ID | Método | Línea inicio | Línea fin |
|------------|--------|--------------|-----------|
| PAYROLL_A | calcular_para_mes() | 74 | 74 |
| NO_PAYROLL_A | calcular_para_mes() | 75 | 75 |
| COSTO_B | calcular_para_mes() | 76 | 76 |
| COSTO_C | calcular_para_mes() | 77 | 86 |
| TOTAL_MENSUAL | calcular_para_mes() retorna CostosTotalesMes | 79 | 86 |

---

## 4. Validación Antes/Después (TAREA 4)

### Tests ejecutados

```bash
# Contract + fix tests (12 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_input_contract_fix_b1.py -q
# Result: 12/12 PASSED ✅

# Baseline snapshot v1 guardrails (5 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_v1.py -q
# Result: 5/5 PASSED ✅

# Cadena C baseline guardrails (5 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py -q
# Result: 5/5 PASSED ✅

# Golden/Parity (58 tests)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/golden/ -q
# Result: 58/58 PASSED ✅

# Total: 80/80 PASSED ✅
```

### Validación de paridad

**Baseline v1:** Snapshot oficial post-canonicalization.  
**Baseline Cadena C v1:** Snapshot oficial con Cadena C activa.  
**Test execution:** Motor ejecutado con FORMULA_ID agregados → output coincide bit a bit con baselines.  
**Estado:** ✅ 100% paridad — Cero drift numérico detectado.

**Criterios de validación:**
- ✅ Payroll A intacto (delegado a NominaCalculator)
- ✅ No-Payroll A intacto (delegado a NoPayrollCalculator)
- ✅ Costo B intacto (delegado a CadenaBCalculator)
- ✅ Costo C intacto (delegado a CadenaCCalculator, ambas variantes)
- ✅ Total mensual intacto (suma lógica de 4 componentes)
- ✅ CostosTotalesMes structure intacto
- ✅ Golden/parity sin regresiones

---

## 5. Cambios Realizados

### Archivo modificado

- **`modules/pyg/services/costos_totales_calculator.py`**
  - Agregó clase interna `FORMULA_ID` (líneas 53-58)
  - Sin cambios en método calcular_para_mes, lógica o comportamiento

### Archivos NO modificados

- ✅ `modules/calculator/engine.py` (orquestación intacta)
- ✅ `modules/pyg/` servicios, DTOs, API (intactos)
- ✅ Todos los calculadores de cadenas (Nomina, NoPayroll, CadenaBCalculator, CadenaCCalculator)
- ✅ CTS, Vision Imprimible, P&G, KPIs (visiones intactas)
- ✅ `storage/` (parametrización congelada)
- ✅ DTOs, contratos públicos

---

## 6. Riesgo y Mitigación

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|-----------|
| Drift en output numérico | ❌ Muy baja | Formula IDs son constantes internas; NO usadas en runtime |
| Cambio en delegación | ❌ Cero | Único cambio es agregar clase de constantes |
| Regresión en tests | ❌ Cero | Todos 80 tests pasan |
| Impacto en P&G o Visiones | ❌ Cero | No se tocó ningún cálculo |
| Cambio en CostosTotalesMes DTO | ❌ Cero | No modificado |

---

## 7. Comparación con PHASE1-4

| Aspecto | PHASE1 | PHASE2 | PHASE3 | PHASE4 | PHASE5 |
|--------|--------|--------|--------|--------|--------|
| Módulo | NoPayroll | CadenaBCalculator | CostosFinancieros | CadenaCCalculator | CostosTotalesCalculator |
| Capa | 3 | 4-5 | 8 | 6 | 7 |
| Complejidad | Media | Media | Alta | Media | **Baja (orquestador)** |
| Métodos/Bloques | 8 | 8 | 5+per-cadena | 7 | **1 orquestador** |
| Riesgos | 1 Alto | 3 Medios | 3 Medios | 2 Bajos | **0 (puro)** |
| Decisión | NO refactorizar | NO refactorizar | NO refactorizar | NO refactorizar | **NO refactorizar** |
| FORMULA_IDs | 8 | 7 | 8 | 8 | **5** |
| Tests total | 81 | 75 | 90 | 80 | **80 (mismo suite)** |
| Paridad | 100% | 100% | 100% | 100% | **100%** |

---

## 8. Notas sobre Capa 7 — Costos Totales

### Pipeline de 10 capas

Costos Totales es el coordinador que suma:
- Capa 1: Entrada
- Capa 2: NominaCalculator (payroll Cadena A)
- Capa 3: NoPayrollCalculator (infraestructura Cadena A)
- Capa 4-5: CadenaBCalculator (plataforma digital)
- Capa 6: CadenaCCalculator (integración IA)
- **Capa 7: CostosTotalesCalculator ← PHASE5 aquí**
- Capa 8: CostosFinancierosCalculator (financiación, pólizas, ICA, GMF)
- Capa 9: PyGCalculator (Estado de Resultados)
- Capa 10: KPIsCalculator + visiones (CTS, tarifas, imprimible)

### Orquestador puro

Capa 7 es especial: no calcula, solo coordina. Es el punto de agregación antes de que los costos financieros (Capa 8) se apliquen. Nota la distinción:

```
Capa 7 output: CostosTotalesMes (payroll_a, no_payroll_a, costo_b, costo_c)
                           ↓
Capa 8 input:  Costos operativos (CostosTotalContrato)
```

Capa 8 (Costos Financieros) agrega ICA/GMF/pólizas/financiación a estos costos operativos.

### Variante costo_c

Notación importante: CadenaCCalculator retorna dos valores:
- `total_pyg` — Para P&G visual (Capa 9)
- `total` — Para base financiera (Capa 8)

La diferencia refleja cómo Cadena C se divide entre visiones (algunas componentes van a P&G, otras a financiación). CostosTotalesCalculator preserva ambas:
```python
costo_c = cadena_c.total_pyg      # P&G row 55
costo_c_fin = cadena_c.total      # ICA/GMF base (Capa 8)
```

---

## 9. Siguiente fase recomendada

Opciones:

1. **FORMULA_REFACTOR_PHASE6_PyG** (Capa 9)
   - Auditar `modules/vision_pyg/reglas.py` y `builder.py`
   - Aplicar trazabilidad análoga

2. **CLEANUP FASE** (Dead code)
   - Eliminar métodos no consumidos en `modules/vision_pyg/{kpis.py, costos_totales.py, reglas.py}`
   - Usar `cleanup-agent`

3. **FORMULA_REFACTOR_VALIDATION_EXCEL_COMPLETE**
   - Comparar outputs contra Excel V2-7 per module
   - Crear fixtures con deals reales

---

## Cierre

✅ **Estado:** CLOSED  
✅ **Cambios:** Mínimos (solo trazabilidad, cero impacto en lógica)  
✅ **Validación:** 80/80 tests PASSED  
✅ **Paridad:** 100% (sin drift contra baselines v1 y cadena_c_v1)  
✅ **Riesgo:** BAJO (constantes internas, sin uso en runtime, no alteran output)  

---

## Artefactos

- ✅ `modules/pyg/services/costos_totales_calculator.py` — FORMULA_ID agregados
- ✅ `docs/refactor/formula_refactor_phase5_costos_totales.md` — Esta documentación
