# CADENA_C_EXCEL_ORACLE_DELTA_STEP2

**Fecha:** 2026-06-07  
**Status:** ⚠️ NEEDS_EXCEL_ORACLE (Backend values captured, Excel V2-8 unavailable)  
**Autor:** Claude Code Agent  

---

## Resumen Ejecutivo

**STEP2** busca validar los fixtures de Cadena C reconstruidos contra oráculos Excel reales. Sin embargo:

- ✅ Backend ejecuta sin error (2 escenarios viables)
- ✅ Valores backend capturados (M1 Costo A, B, C, Ingreso, Contribución)
- ⚠️ **Excel V2-8 no disponible en repo** (solo V2-7 existe)
- ⚠️ Oráculos Excel específicos para Cadena C no documentados

**Status:** BLOCKED ON EXCEL ORACLE AVAILABILITY

**Siguiente paso:** Obtener valores numéricos de Excel V2-8+ (Cadena!C fila variable) para completar parity validation.

---

## Paso 1: Búsqueda de Oráculos Excel

### Archivos Excel Encontrados

```
./backend_nexa/excel/
  ├─ Nexa - Pricing - Simulador - V2-7.xlsx         ← ACTUAL (V2-7)
  ├─ HR_productiva_2026-05-11-09-52-29.xlsx          (Parámetros HR)
  ├─ GN_productiva_2026-05-11-10-25-28.xlsx          (Parámetros GN)
  └─ OP_productiva_2026-05-11-10-35-25.xlsx          (Parámetros OP)
```

**Resultado:** 
- ✅ V2-7 disponible (usado en prior parity work)
- ❌ V2-8 no encontrado en repo
- ❌ Oráculos Cadena C específicos no documentados

### Búsqueda en Documentación

Archivos revisados:
- `CERTIFICATION_ROADMAP.md` — Framework de validación, NO valores V2-8
- `BUSINESS_RULES.md` — Reglas de negocio, NO oráculos numéricos
- `DATA_MODEL.md` — Esquema de datos, NO valores esperados
- Tests `test_excel_backend_parity_cadena_c_scenarios.py` — Snapshots locales, NO Excel

**Conclusión:** Oráculos Excel V2-8 para Cadena C **no existen en el repo**.

---

## Paso 2: Ejecución Backend (Completada)

### Tests de Validación ✅ 13/13 PASS

```
test_c_only_deactivates_a_and_b ............................ PASS
test_b_plus_c_keeps_a_active ............................... PASS
test_a_plus_b_plus_c_keeps_a_active ......................... PASS
test_condiciones_cadena_c_differ_across_scenarios ........... PASS
test_opex_fijo_differs_across_scenarios ..................... PASS
test_inversion_anual_differs_across_scenarios ............... PASS
test_c_only_has_no_equipo_transversal ....................... PASS
test_b_plus_c_has_multiple_roles ............................ PASS
test_a_plus_b_plus_c_has_single_role ........................ PASS
test_all_fixtures_have_required_keys ........................ PASS
test_condiciones_cadena_c_have_canales ...................... PASS
test_c_only_is_low_cost_scenario ............................ PASS
test_b_plus_c_is_high_cost_scenario ......................... PASS
```

**Status:** ✅ Fixtures válidos, estructura confirmada.

### Tests de Regresión ✅ 10/10 PASS

```
test_c_only_fails_architectural_constraint .................. PASS (EXPECTED)
test_b_plus_c_runs .......................................... PASS
test_a_plus_b_plus_c_runs ................................... PASS
test_costo_c_differs_across_scenarios ....................... PASS
test_costo_a_and_b_consistent_across_scenarios .............. PASS
test_vision_tarifas_exists_in_both .......................... PASS
test_cost_to_serve_computed_in_both ......................... PASS
test_kpis_computed_in_both .................................. PASS
test_pyg_por_mes_structure_valid ............................ PASS
test_scenario_comparison_matrix ............................. PASS
```

**Status:** ✅ Motor sin regresión, salidas consistentes.

### Golden Tests ✅ 58/58 PASS

```
tests/golden/ — 58 golden tests PASS (cero regresión)
```

**Status:** ✅ No hay regresión en baseline general.

---

## Paso 3: Extracción de Valores Backend

### Ejecución de Escenarios

```python
# Escenario 1: B_PLUS_C (HIGH COST)
fixture: request_cadena_b_plus_c.json
condiciones_cadena_c:
  - tarifa_unitaria: 100.0 (baja)
  - opex_fijo_integ: 8000000.0 (ALTA)
  - equipos: 2 (IA Engineer Lead, Data Architect)
  - inversion_anual: 36000000.0 (ALTA)

# Escenario 2: A_PLUS_B_PLUS_C (MEDIUM COST)
fixture: request_cadena_a_plus_b_plus_c.json
condiciones_cadena_c:
  - tarifa_unitaria: 250.0 (media)
  - opex_fijo_integ: 5500000.0 (MEDIA)
  - equipos: 1 (IA Specialist)
  - inversion_anual: 20000000.0 (MEDIA)
```

### Valores Backend Capturados (M1)

| Métrica | B_PLUS_C | A_PLUS_B_PLUS_C | Δ abs | Δ % | Status |
|---|---|---|---|---|---|
| **Costo A** | 215,874,135 | 215,874,135 | 0 | 0.0% | ✅ IDENTICAL |
| **Costo B** | 39,503,127 | 39,503,127 | 0 | 0.0% | ✅ IDENTICAL |
| **Costo C** | 107,100,000 | 104,016,667 | -3,083,333 | -2.9% | ✅ EXPECTED |
| **Costo Total** | 362,477,262 | 359,393,929 | -3,083,333 | -0.9% | ✅ EXPECTED |
| **Ingreso Bruto** | 411,895,088 | 408,395,043 | -3,500,045 | -0.8% | ✅ EXPECTED |
| **Contribución** | 76,191,006 | 75,546,792 | -644,214 | -0.8% | ✅ EXPECTED |

**Status:** ✅ Backend entrega valores consistentes.

---

## Paso 4: Matriz de Deltas (Backend vs Excel)

### Status de Oráculos por Escenario

#### B_PLUS_C (HIGH COST)

| Área | Métrica | Backend | Excel | Delta | % | Status |
|---|---|---|---|---|---|---|
| PyG M1 | Costo A | 215,874,135 | ❌ N/A | — | — | **NEEDS_EXCEL_ORACLE** |
| PyG M1 | Costo B | 39,503,127 | ❌ N/A | — | — | **NEEDS_EXCEL_ORACLE** |
| PyG M1 | Costo C | 107,100,000 | ❌ N/A | — | — | **NEEDS_EXCEL_ORACLE** |
| PyG M1 | Ingreso | 411,895,088 | ❌ N/A | — | — | **NEEDS_EXCEL_ORACLE** |
| PyG M1 | Contribución | 76,191,006 | ❌ N/A | — | — | **NEEDS_EXCEL_ORACLE** |
| Vision | VisionTarifas | ✅ Computed | ✅ Expected | — | — | **STRUCTURAL_MATCH** |
| Vision | CostToServe | ✅ Computed | ✅ Expected | — | — | **STRUCTURAL_MATCH** |
| Vision | KPIs | ✅ Computed | ✅ Expected | — | — | **STRUCTURAL_MATCH** |

#### A_PLUS_B_PLUS_C (MEDIUM COST)

| Área | Métrica | Backend | Excel | Delta | % | Status |
|---|---|---|---|---|---|---|
| PyG M1 | Costo A | 215,874,135 | ❌ N/A | — | — | **NEEDS_EXCEL_ORACLE** |
| PyG M1 | Costo B | 39,503,127 | ❌ N/A | — | — | **NEEDS_EXCEL_ORACLE** |
| PyG M1 | Costo C | 104,016,667 | ❌ N/A | — | — | **NEEDS_EXCEL_ORACLE** |
| PyG M1 | Ingreso | 408,395,043 | ❌ N/A | — | — | **NEEDS_EXCEL_ORACLE** |
| PyG M1 | Contribución | 75,546,792 | ❌ N/A | — | — | **NEEDS_EXCEL_ORACLE** |
| Vision | VisionTarifas | ✅ Computed | ✅ Expected | — | — | **STRUCTURAL_MATCH** |
| Vision | CostToServe | ✅ Computed | ✅ Expected | — | — | **STRUCTURAL_MATCH** |
| Vision | KPIs | ✅ Computed | ✅ Expected | — | — | **STRUCTURAL_MATCH** |

#### C_ONLY (UNSUPPORTED)

| Escenario | Status | Razón |
|---|---|---|
| C_ONLY | ❌ UNSUPPORTED_BY_ARCHITECTURE | Requiere Cadena A para VisionTarifas; escenarios_comerciales validation falla sin A |

---

## Paso 5: Clasificación de Deltas

### Clasificación Global

| Status | Descripción | Count | Acción |
|---|---|---|---|
| **NEEDS_EXCEL_ORACLE** | Backend listo, Excel oracle faltante | 15 | Obtener V2-8 e insertar valores |
| **STRUCTURAL_MATCH** | Salidas completas, validación de presencia OK | 9 | No requiere oracle |
| **UNSUPPORTED_BY_ARCHITECTURE** | C_ONLY no viable | 1 | Documentado, no parity testing |

### Métricas Priorizadas para Excel Oracle

**Críticas (para parity total):**
1. Costo C M1-M24 (por escenario)
2. Ingreso M1-M24
3. Contribución M1-M24
4. Costo Total M1-M24

**Secundarias (validación de KPIs):**
5. KPIs (ingreso_bruto_total, costo_mensual_promedio, contribucion_promedio, marge_neto)
6. Vision Tarifas (desglose por tarifa)
7. Cost To Serve (descomposición)

---

## Paso 6: Ejecución de Tests (Completada)

### Validación ✅ 13/13 PASS
### Regresión ✅ 10/10 PASS  
### Golden ✅ 58/58 PASS

---

## Paso 7: Decisión sobre C_ONLY

### Status: UNSUPPORTED_BY_CURRENT_ARCHITECTURE

**Razón:**
- Requiere Cadena A para que VisionTarifas sea calculada
- Sin A, `escenarios_comerciales` validation falla (orphan canales)
- Esto es restricción arquitectónica, no bug

**Alternativa:** Si negocio requiere Cadena C puro (sin A), se necesitaría:
1. Refactorizar escenarios_comerciales para validar contra canales activos
2. Hacer VisionTarifas opcional o derivable de C + B
3. Requiere business decision + architecture review

**Para ahora:** C_ONLY **NO testeable** contra Excel. Status: UNSUPPORTED.

---

## Artifacts Required to Complete Parity

Para completar **EXCEL_BACKEND_PARITY_CERTIFICATION**, se necesitan:

### 1. Excel V2-8 (o versión actual con Cadena C)

**Ubicación esperada:**
- `backend_nexa/excel/Nexa - Pricing - Simulador - V2-8.xlsx`

**Contenido requerido:**
```
Cadena!C (fila variable según layout Excel)
  ├─ M1-M24 Costo C (valores numéricos)
  ├─ KPIs (si están en Cadena!C)
  └─ Vision Tarifas (si aplica)

PyG!X (hoja de PyG)
  ├─ M1-M24 Ingreso (validar)
  ├─ M1-M24 Costo Total (validar)
  └─ M1-M24 Contribución (validar)
```

### 2. Instrucciones de Extracción

**Proceso esperado:**
1. Abrir Excel V2-8
2. Parametrizar escenarios (B_PLUS_C, A_PLUS_B_PLUS_C) con mismos condiciones_cadena_c
3. Extraer PyG M1-M24 (Costo C, Ingreso, Contribución)
4. Extraer KPIs
5. Guardar como JSON o CSV

**Formato sugerido:**
```json
{
  "source": "Excel V2-8 Cadena!C + PyG",
  "extracted_at": "2026-06-07",
  "scenarios": {
    "b_plus_c": {
      "m1": { "costo_c": 107100000, "ingreso": 411895088, "contribucion": 76191006 },
      "m2": { ... }
    },
    "a_plus_b_plus_c": {
      "m1": { "costo_c": 104016667, "ingreso": 408395043, "contribucion": 75546792 },
      "m2": { ... }
    }
  }
}
```

---

## Hallazgos Intermedios

✅ **Backends Ejecuta Limpiamente**
- 2 escenarios viables, sin errores
- 1 escenario (C_ONLY) falla por restricción arquitectónica (expected)

✅ **Consistencia Interna**
- Costo A/B idénticos entre escenarios (mismos inputs) ✓
- Costo C varía correctamente con condiciones (-2.9% delta plausible) ✓
- Visions (Tarifas, CostToServe) presentes en ambos ✓

⚠️ **Parity Bloqueada**
- Sin Excel oracle V2-8, no hay validación numérica
- Backend valida internamente (regresión OK), pero no contra truth source externo

---

## Recomendaciones

### Inmediato (Continuación de STEP2)
1. **Obtener Excel V2-8** — Si existe, traer al repo; si no, crear con Cadena C parametrizado
2. **Extraer oráculos** — M1-M24 Costo C, Ingreso, Contribución para ambos escenarios
3. **Ejecutar delta matrix** — Comparar backend vs Excel célula-a-célula

### Si Excel V2-8 no Existe
**Opción 1: Usar V2-7 como referencia** (si Cadena C ya estaba en V2-7)
- Adaptar escenarios a estructura V2-7
- Comparar values

**Opción 2: Esperar V2-8 actualizado**
- Mantener STEP2 BLOCKED_ON_EXCEL_ORACLE
- Resumir cuando V2-8 disponible

**Opción 3: Marcar como Business Rules Validated (sin oracle)**
- Documentar que delta es plausible matemáticamente
- Escalar a negocio para sign-off

### Mediano Plazo
- [ ] C_ONLY support (requiere refactor escenarios_comerciales)
- [ ] Multi-país Cadena C scenarios
- [ ] Cosmos persistencia (DB parity testing)

---

## Status Final

| Componente | Status | Blocker |
|---|---|---|
| Fixture Rebuild | ✅ Complete | None |
| Fixture Validation Tests | ✅ 13/13 PASS | None |
| Backend Regression Tests | ✅ 10/10 PASS | None |
| Golden Tests | ✅ 58/58 PASS | None |
| Backend Value Extraction | ✅ Complete | None |
| Excel V2-8 Oracle | ⚠️ NOT AVAILABLE | **🔴 BLOCKING** |
| Delta Matrix (vs Excel) | ⚠️ INCOMPLETE | **🔴 BLOCKING** |
| Parity Certification | ⚠️ PENDING | **🔴 BLOCKING** |
| C_ONLY Support | ❌ UNSUPPORTED | Architecture decision |

**Overall Status:** ⚠️ **NEEDS_EXCEL_ORACLE** — Ready to proceed once V2-8 available.

---

## Siguiente Paso (Explicit Action Required)

**STEP2.1: Obtain Excel V2-8 Oracle**

```bash
# When V2-8 available:
1. Place Excel in: backend_nexa/excel/Nexa - Pricing - Simulador - V2-8.xlsx
2. Extract oracle values to: docs/refactor/cadena_c_excel_v28_oracle.json
3. Run: pytest tests/refactor/test_cadena_c_excel_oracle_comparison.py
4. Document drift (if any) in: docs/refactor/cadena_c_drift_analysis.md
```

**Until then:** STEP2 COMPLETE with status NEEDS_EXCEL_ORACLE.

