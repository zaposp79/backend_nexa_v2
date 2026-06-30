# PYG_ACTIVE_OWNERSHIP_CONFIRMATION

**Mapeo de archivos PyG activos vs. legacy**

Branch: `refactor/modular-pure`  
Fecha: 2026-06-06  
Status: **CONFIRMADO**

---

## Objetivo

Determinar qué archivos PyG son runtime activo antes de ejecutar FORMULA_REFACTOR_PHASE6_PYG.

---

## 1. Búsqueda de Imports Runtime (TAREA 1)

### Imports en engine.py (composición root)

```
✅ from nexa_engine.modules.pyg.services.costos_totales_calculator import CostosTotalesCalculator
✅ from nexa_engine.modules.pyg.services.pyg_calculator import PyGCalculator
✅ from nexa_engine.modules.pyg.services.kpis_calculator import KPIsCalculator
✅ from nexa_engine.modules.pyg.builders.vision_pyg_builder import VisionPyGBuilder
```

### Imports en app / routers

```
✅ from nexa_engine.modules.pyg.api.vision_router import router as pyg_router
✅ from nexa_engine.modules.pyg.builders.vision_pyg_60m import build_vision_pyg_60m
```

### Imports de modules/vision_pyg en código activo

```
❌ NO ENCONTRADOS (cero referencias en runtime)
```

**Conclusión:** modules/vision_pyg es completamente legacy. modules/pyg es el módulo activo.

---

## 2. Matriz de Archivos Activos vs. Legacy (TAREA 2)

| Archivo | Categoría | Status | Consumidores | Rol | Acción |
|---------|-----------|--------|-------------|-----|--------|
| **modules/pyg/services/pyg_calculator.py** | RUNTIME_ACTIVO | ✅ ACTIVO | engine.py | Capa 9 — Estado de Resultados mensual | AUDITAR PHASE6 |
| **modules/pyg/services/kpis_calculator.py** | RUNTIME_ACTIVO | ✅ ACTIVO | engine.py | Capa 10 — KPIs del deal | AUDITAR PHASE6 |
| **modules/pyg/services/costos_totales_calculator.py** | RUNTIME_ACTIVO | ✅ ACTIVO | engine.py, PHASE5 | Capa 7 — Agregación costos | YA AUDITADO (PHASE5) |
| **modules/pyg/builders/vision_pyg_builder.py** | BUILDER_ACTIVO | ✅ ACTIVO | engine.py | Construye VisionPyG | AUDITAR PHASE6 |
| **modules/pyg/builders/vision_pyg_60m.py** | BUILDER_ACTIVO | ✅ ACTIVO | vision_router.py | Proyección PyG a 60 meses | REVISAR PHASE6 |
| **modules/pyg/api/vision_router.py** | API_ACTIVO | ✅ ACTIVO | api/v1/router.py | Endpoints GET /{simulation_id}/vision/pyg | NO TOCAR |
| **modules/pyg/services/** (DTOs) | RUNTIME_ACTIVO | ✅ ACTIVO | engine.py | PyGMensual, KPIsDeal models | NO TOCAR (contratos) |
| **modules/vision_pyg/reglas.py** | LEGACY_DEAD_CODE | ❌ INACTIVO | ninguno | Antigua PyGCalculator | ELIMINAR (cleanup) |
| **modules/vision_pyg/kpis.py** | LEGACY_DEAD_CODE | ❌ INACTIVO | ninguno | Antigua KPIsCalculator | ELIMINAR (cleanup) |
| **modules/vision_pyg/costos_totales.py** | LEGACY_DEAD_CODE | ❌ INACTIVO | ninguno | Antigua CostosTotalesCalculator | ELIMINAR (cleanup) |
| **modules/vision_pyg/builder.py** | LEGACY_DEAD_CODE | ❌ INACTIVO | ninguno | Antigua VisionPyGBuilder | ELIMINAR (cleanup) |
| **modules/vision_pyg/vision_pyg_60m.py** | LEGACY_DEAD_CODE | ❌ INACTIVO | ninguno | Antigua proyección 60m | ELIMINAR (cleanup) |
| **modules/vision_pyg/api/router.py** | LEGACY_DEAD_CODE | ❌ INACTIVO | ninguno | Antigua API (no registrada en app) | ELIMINAR (cleanup) |

---

## 3. Análisis de Módulos Activos (TAREA 3)

### modules/pyg/services/pyg_calculator.py

**Responsabilidad:** PyGCalculator — Capa 9 del pipeline  
**Inputs:** panel, costos_totales, costos_financieros, parametrizacion  
**Output:** List[PyGMensual]  
**Líneas:** ~210  
**Complejidad:** Media-Alta (cálculo de ingresos, márgenes, ramp-up)  

```python
class PyGCalculator:
    def calcular(...) -> List[PyGMensual]
```

**Patrón:** Servicio especializado con lógica de negocio propia.  
**Candidato para PHASE6:** ✅ SÍ — Necesita trazabilidad mínima (FORMULA_ID).

---

### modules/pyg/services/kpis_calculator.py

**Responsabilidad:** KPIsCalculator — Capa 10 del pipeline  
**Inputs:** panel, costos_financieros, parametrizacion, pyg_por_mes  
**Output:** KPIsDeal  
**Líneas:** ~150  
**Complejidad:** Media (cálculo de tarifa, margen promedio, facturación)  

```python
class KPIsCalculator:
    def calcular(...) -> KPIsDeal
```

**Patrón:** Servicio especializado que produce KPIs deal-wide.  
**Candidato para PHASE6:** ✅ SÍ — Necesita trazabilidad mínima (FORMULA_ID).

---

### modules/pyg/services/costos_totales_calculator.py

**Responsabilidad:** CostosTotalesCalculator — Capa 7 del pipeline  
**Inputs:** perfiles_a, mes, 4 calculadores  
**Output:** CostosTotalesMes  
**Líneas:** ~95  
**Complejidad:** Baja (orquestador puro)  

```python
class CostosTotalesCalculator:
    def calcular_para_mes(...) -> CostosTotalesMes
```

**Patrón:** Orquestador puro (delegación, sin lógica).  
**Status:** ✅ YA AUDITADO EN PHASE5 — FORMULA_ID agregados, 100% paridad.

---

### modules/pyg/builders/vision_pyg_builder.py

**Responsabilidad:** VisionPyGBuilder — Construye VisionPyG para frontend  
**Inputs:** pyg_por_mes, kpis, perfiles_cadena_a, calculadores  
**Output:** VisionPyG  
**Líneas:** ~379  
**Complejidad:** Media-Alta (mapeo de 25 líneas Excel, detalle per-cadena)  

```python
class VisionPyGBuilder:
    def construir(...) -> VisionPyG
    def _build_detalle(...) -> List[VisionPyGRowDetalle]
```

**Patrón:** Builder que transforma PyGMensual en estructura visual frontend.  
**Candidato para PHASE6:** ✅ SÍ — Necesita trazabilidad (FORMULA_ID para cada sección).

---

### modules/pyg/builders/vision_pyg_60m.py

**Responsabilidad:** build_vision_pyg_60m — Proyecta PyG a 60 meses  
**Inputs:** vision_pyg (N meses)  
**Output:** vision_pyg_60m (60 meses, relleno con 0 después)  
**Líneas:** ~100  
**Complejidad:** Baja (padding, no cálculo)  

```python
def build_vision_pyg_60m(vision_pyg: VisionPyG) -> VisionPyG60M
```

**Patrón:** Transformación simple de datos (padding).  
**Candidato para PHASE6:** ⚠️ REVISAR — Bajo riesgo, podría omitirse si no hay lógica de negocio.

---

## 4. Confirmación de Dead Code (TAREA 4)

### modules/vision_pyg/ — Estado LEGACY CONFIRMADO

**Archivos:** 8 archivos Python (2,426 líneas totales)

1. **reglas.py** — 12K, antigua PyGCalculator
2. **kpis.py** — 8.6K, antigua KPIsCalculator
3. **costos_totales.py** — 3K, antigua CostosTotalesCalculator
4. **builder.py** — 20K, antigua VisionPyGBuilder
5. **vision_pyg_60m.py** — 4.1K, antigua proyección 60m
6. **api/router.py** — 5.1K, antigua API (no registrada)
7. **__init__.py, api/__init__.py** — Empty

**Verificación de referencias en runtime:**

```bash
# Búsqueda en engine.py
❌ No imports de vision_pyg

# Búsqueda en app/routers
❌ modules/vision_pyg/api/router.py NO está registrada

# Búsqueda en tests
✅ tests/unit/test_vision_pyg_60m.py (pero importa modules/pyg, no vision_pyg)
✅ tests/contract/test_vision_pyg_contract.py (pero importa modules/pyg, no vision_pyg)
```

**Conclusión:** ✅ **modules/vision_pyg/ es DEAD CODE confirmado.**

**Recomendación:** Marcar para eliminación en CLEANUP FASE post-PHASE6.

---

## 5. Resumen de Arquitectura PyG (TAREA 5)

### Pipeline de 10 capas — Sección PyG (Capas 7, 9, 10)

```
                                 Pipeline de 10 capas
────────────────────────────────────────────────────────────────
Capa 1   PricingRequest
           ↓
Capa 2   NominaCalculator (Cadena A — Payroll)
           ├─ PHASE1: NoPayrollCalculator (Cadena A — No-Payroll) [AUDITADO]
Capa 3   NoPayrollCalculator
           ├─ PHASE2: CadenaBCalculator (Capas 4-5) [AUDITADO]
Capas 4-5 CadenaBCalculator
           ├─ PHASE4: CadenaCCalculator (Capa 6) [AUDITADO]
Capa 6   CadenaCCalculator
           ↓
Capa 7   CostosTotalesCalculator (Orquestador de costos)
         ├─ PHASE5: Costos Totales [AUDITADO]
         ├─ FORMULA_ID agregados
         ├─ 100% paridad con baseline_v1
           ↓
Capa 8   CostosFinancierosCalculator (ICA, GMF, pólizas, financiación)
         ├─ PHASE3: Costos Financieros [AUDITADO]
         ├─ FORMULA_ID agregados
           ↓
Capa 9   PyGCalculator (Estado de Resultados — P&G mensual)
         ├─ PHASE6: PyG (PENDIENTE)
         ├─ FORMULA_ID por sección: Ingresos, Costos, Financiero, Resultados
           ├─ VisionPyGBuilder (Transforma PyG en visión visual)
           ├─ PHASE6: Builder (PENDIENTE)
           ├─ FORMULA_ID per-cadena detail rows (Cadena A payroll, no-payroll, B, C)
           └─ build_vision_pyg_60m (Proyección 60m — padding)
Capa 10  KPIsCalculator (KPIs deal-wide: tarifa, margen, costo promedio)
         ├─ PHASE6: KPIs (PENDIENTE)
         ├─ FORMULA_ID: costo_promedio_a, tarifa_mensual, facturación, margen_minimo
           ↓
      PricingResult { vision_pyg, vision_imprimible, vision_tarifas, cost_to_serve }
```

---

## 6. Decisión para PHASE6_PYG (TAREA 6)

### Opciones de alcance

| Opción | Archivos | Complejidad | Riesgo | Tiempo | Recomendación |
|--------|----------|-------------|--------|--------|---|
| **OPTION A: Minimal (solo PyGCalculator + KPIsCalculator)** | 2 archivos services | Media | Bajo | 1-2h | ✅ RECOMENDADO |
| **OPTION B: Completo (A + VisionPyGBuilder)** | 3 archivos (2 services + 1 builder) | Alta | Medio | 2-3h | ✅ ALTERNATIVA |
| **OPTION C: Exhaustivo (A + B + vision_pyg_60m)** | 4 archivos | Alta | Medio | 3-4h | ⚠️ OPCIONAL |

### Recomendación: OPTION B (Completo)

**Razón:** VisionPyGBuilder es la interfaz pública que el frontend consume; merece trazabilidad. Capa 9 sin Capa 10 (KPIs) sería incompleto.

**Alcance PHASE6:**
- ✅ **modules/pyg/services/pyg_calculator.py** — PyGCalculator (Capa 9)
- ✅ **modules/pyg/services/kpis_calculator.py** — KPIsCalculator (Capa 10)
- ✅ **modules/pyg/builders/vision_pyg_builder.py** — VisionPyGBuilder

**NO incluir en PHASE6:**
- ❌ modules/pyg/builders/vision_pyg_60m.py (bajo riesgo, pure padding)
- ❌ modules/pyg/api/vision_router.py (no tocar HTTP layer)
- ❌ modules/vision_pyg/ (dejar para CLEANUP FASE)

---

## 7. Validación Esperada para PHASE6 (TAREA 7)

### Tests a ejecutar (mismo patrón PHASE1-5)

```bash
# Contract + fix tests
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_input_contract_fix_b1.py -q
# Expected: 12/12 PASSED

# Baseline snapshot v1 (Cadena A + B)
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_v1.py -q
# Expected: 5/5 PASSED

# Baseline Cadena C v1
PYTHONPATH=$(pwd) pytest backend_nexa/tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py -q
# Expected: 5/5 PASSED

# Golden/Parity
PYTHONPATH=$(pwd) pytest backend_nexa/tests/golden/ -q
# Expected: 58/58 PASSED

# Total: 80+ tests
```

### Criterios de paridad

| Criterio | Baseline | Aceptación |
|----------|----------|-----------|
| Ingreso Bruto A/B/C | baseline_v1 | 100% match |
| Ingreso Neto | baseline_v1 | 100% match |
| Costo Total (costos_op) | baseline_v1 | 100% match |
| Componente Financiero | baseline_v1 | 100% match |
| Contribución | baseline_v1 | 100% match |
| Pct Utilidad Neta | baseline_v1 | 100% match |
| KPIs Deal (tarifa, costo_promedio) | baseline_v1 | 100% match |
| Golden test suite | 58 tests | 0 regresiones |

---

## 8. Siguiente Paso (TAREA 8)

### Después de PHASE6_PYG

1. **CLEANUP FASE** (eliminar dead code vision_pyg)
   - Eliminar modules/vision_pyg/ completamente
   - Verificar no hay referencias orphan
   - Actualizar imports en tests si necesario

2. **FORMULA_REFACTOR_VALIDATION_EXCEL_COMPLETE** (opcional)
   - Comparar outputs contra Excel V2-7 per module
   - Crear fixtures con deals reales
   - Validación manual Excel ↔ código

---

## Cierre

✅ **Confirmación:** modules/pyg/ es runtime activo.  
✅ **Dead code:** modules/vision_pyg/ completamente legacy.  
✅ **PHASE6 scope:** PyGCalculator + KPIsCalculator + VisionPyGBuilder.  
✅ **Riesgo:** Bajo (patrón FORMULA_ID probado en PHASE1-5).  
✅ **Recomendación:** Proceder con FORMULA_REFACTOR_PHASE6_PYG.

---

## Artefactos

- ✅ `docs/refactor/pyg_active_ownership_confirmation.md` — Esta documentación

