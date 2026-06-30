# FORMULA_TRACE_RUNTIME_WIRING — CLOSEOUT

**Fecha:** 2026-06-06  
**Secuencia:** PHASE1-11 (completada)  
**Status:** ✅ CERRADO — Cero drift, todos los tests pasan, JSON público intacto

---

## Resumen Ejecutivo

La iniciativa **FORMULA_TRACE_RUNTIME_WIRING** ha completado la conexión de FORMULA_ID internos con trazabilidad runtime a través de 11 fases de evaluación arquitectónica. 

**Resultado:**
- ✅ **6 calculadores** con FORMULA_ID wired a `_audit_trace()` existentes
- ✅ **5 módulos** correctamente omitidos con justificación arquitectónica
- ✅ **50 FORMULA_ID** conectados en total
- ✅ **84 tests** pasando sin cambios
- ✅ **Cero drift** en snapshots, cálculos y outputs públicos

---

## Calculadores con FORMULA_ID Wiring ✅ (6/12)

### PHASE1 — NoPayrollCalculator
- **Archivo:** `modules/pyg/services/nopayroll_calculator.py`
- **FORMULA_ID wired:** 3
- **Cambio:** Conexión a `_audit_trace()` en método `calcular()` (línea 145)
- **Ids:** `BENEFICIO_NETO`, `COSTO_PERSONAL_TOTAL`, `FACTOR_ESCALAMIENTO_PERSONAL`
- **Status:** ✅ Completado (prior session)
- **Validación:** 76/76 tests pass

### PHASE2 — CadenaBCalculator
- **Archivo:** `modules/pyg/services/cadena_b_calculator.py`
- **FORMULA_ID wired:** 7
- **Cambio:** Conexión a `_audit_trace()` en método `calcular()` (línea 138)
- **Ids:** `COMPONENTE_FIJO_B`, `COMPONENTE_VARIABLE_B`, `DESCUENTO_B`, `FACTOR_INDEXACION_B`, `FACTOR_RAMPUP_B`, `FACTURACION_B`, `MARGEN_B`
- **Status:** ✅ Completado (prior session)
- **Validación:** 76/76 tests pass

### PHASE3 — CadenaCCalculator
- **Archivo:** `modules/pyg/services/cadena_c_calculator.py`
- **FORMULA_ID wired:** 8
- **Cambio:** Conexión a `_audit_trace()` en método `calcular()` (línea 142)
- **Ids:** `COMPONENTE_FIJO_C`, `COMPONENTE_VARIABLE_C`, `DESCUENTO_C`, `FACTOR_INDEXACION_C`, `FACTOR_RAMPUP_C`, `FACTURACION_C`, `MARGEN_C`, `MODELO_COBRO_C`
- **Status:** ✅ Completado (prior session)
- **Validación:** 76/76 tests pass

### PHASE4 — CostosFinancierosCalculator
- **Archivo:** `modules/pyg/services/costos_financieros_calculator.py`
- **FORMULA_ID wired:** 8
- **Cambio:** Conexión a `_audit_trace()` en método `calcular()` (línea 105)
- **Ids:** `TASA_MENSUAL_FINANC`, `FACTOR_FINANC`, `INTERES_PURO_COSTO`, `COMISION_ADMON_COSTO`, `COMISION_ESTUDIO_COSTO`, `COMISIONES_TOTALES_COSTO`, `GASTOS_LEGALES_COSTO`, `COSTOS_FINANCIEROS_TOTALES`
- **Status:** ✅ Completado (prior session)
- **Validación:** 76/76 tests pass

### PHASE6 — PyGCalculator
- **Archivo:** `modules/pyg/services/pyg_calculator.py`
- **FORMULA_ID wired:** 9
- **Cambio:** Conexión a `_audit_trace()` en método `calcular_mes()` (línea 161)
- **Ids:** `INGRESO_CADENA_A`, `INGRESO_CADENA_B`, `INGRESO_CADENA_C`, `INGRESO_BRUTO`, `IMPREVISTOS`, `FACTOR_RAMPUP`, `FACTOR_BILLING_A`, `FACTOR_BILLING_B`, `FACTOR_BILLING_C`
- **Status:** ✅ Completado (current session, commit e23259e)
- **Validación:** 76/76 tests pass

### PHASE7 — KPIsCalculator
- **Archivo:** `modules/pyg/services/kpis_calculator.py`
- **FORMULA_ID wired:** 15
- **Cambio:** Conexión a `_audit_trace()` en método `calcular()` (línea 121)
- **Ids:** `COSTO_MENSUAL_PROMEDIO`, `COSTO_CADENA_A_PROMEDIO`, `TARIFA_MENSUAL`, `FACTURACION_PROYECTADA`, `FACTOR_MARGENES`, `FACTOR_PERIODO`, `COSTOS_FIN_SOBRE_PROMEDIO`, `INGRESO_BRUTO_TOTAL`, `INGRESO_NETO_TOTAL`, `COSTO_TOTAL_CONTRATO`, `CONTRIBUCION_TOTAL`, `UTILIDAD_NETA_TOTAL`, `PCT_UTILIDAD_NETA`, `MARGEN_MINIMO_REQUERIDO`, `CUMPLE_MARGEN_MINIMO`
- **Status:** ✅ Completado (current session, commit 3a9461a)
- **Validación:** 76/76 tests pass

---

## Módulos Omitidos con Justificación ⏭ (5/12)

### PHASE5 — CostosTotalesCalculator (Orquestador)
- **Archivo:** `modules/pyg/services/costos_totales_calculator.py`
- **FORMULA_ID definidos:** 5
- **Razón de omisión:** Orquestador puro (sin `_audit_trace()` existente)
- **Naturaleza:** Delega cálculos a subcalculadores; solo suma y agrupa
- **Decisión:** OMITIDO — fuera del patrón FORMULA_TRACE_RUNTIME_WIRING
- **Documentación:** docs/refactor/formula_trace_runtime_wiring_phase5_costos_totales.md
- **Status:** ✅ Evaluado y omitido correctamente

### PHASE8 — CostToServeCalculator (Sin trace)
- **Archivo:** `modules/vision_cost_to_serve/services/cost_to_serve_calculator.py`
- **FORMULA_ID definidos:** 13
- **Razón de omisión:** Sin `_audit_trace()` existente (solo logger.info())
- **Naturaleza:** Calculador con lógica propia, pero sin punto de auditoría
- **Decisión:** OMITIDO — viola criterio "agregar a traces existentes, nunca crear nuevos"
- **Documentación:** docs/refactor/formula_trace_runtime_wiring_phase8_cost_to_serve.md
- **Status:** ✅ Evaluado y omitido correctamente (commit 08c0392)

### PHASE9 — VisionTarifasCalculator (Sin trace)
- **Archivo:** `modules/vision_tarifas/reglas.py`
- **FORMULA_ID definidos:** 13
- **Razón de omisión:** Sin `_audit_trace()` existente (solo logger.info [VT_TRACE])
- **Naturaleza:** Calculador con lógica propia (500+ líneas), pero sin punto de auditoría integrado
- **Decisión:** OMITIDO — viola criterio arquitectónico
- **Documentación:** docs/refactor/formula_trace_runtime_wiring_phase9_vision_tarifas.md
- **Status:** ✅ Evaluado y omitido correctamente (commit 3bb1adb)

### PHASE10 — VisionPyGBuilder (Builder)
- **Archivo:** `modules/pyg/builders/vision_pyg_builder.py`
- **FORMULA_ID definidos:** 11
- **Razón de omisión:** Builder/transformador, no calculador
- **Naturaleza:** Mapea PyGMensual → VisionPyG; solo transformación de datos, sin cálculo
- **Decisión:** OMITIDO — patrón aplica a calculadores solamente
- **Documentación:** docs/refactor/formula_trace_runtime_wiring_phase10_vision_pyg_builder.md
- **Status:** ✅ Evaluado y omitido correctamente (commit 100d382)

### PHASE11 — VisionImprimibleBuilder (Compositor)
- **Archivo:** `modules/vision_imprimible/builders/vision_imprimible_builder.py`
- **FORMULA_ID definidos:** 10
- **Razón de omisión:** Compositor/assembler, no calculador
- **Naturaleza:** Ensambla 11 secciones de VisionImprimible; código explícitamente señala "NO recalcula nada"
- **Decisión:** OMITIDO — patrón aplica a calculadores con cálculo propio
- **Documentación:** docs/refactor/formula_trace_runtime_wiring_phase11_vision_imprimible_builder.md
- **Status:** ✅ Evaluado y omitido correctamente (commit c42365b)

---

## Criterio Arquitectónico (Validado)

### Patrón Establecido

**Regla FORMULA_TRACE_RUNTIME_WIRING:**

```
Agregar formula_ids ÚNICAMENTE a _audit_trace() existentes en CALCULADORES
que contengan lógica de cálculo propia.
```

**Definiciones:**

| Término | Descripción | ¿Aplica FORMULA_TRACE_RUNTIME_WIRING? |
|---|---|---|
| **Calculador** | Contiene lógica de cálculo propia; computa nuevos valores a partir de inputs; tiene `_audit_trace()` | ✅ SÍ |
| **Orquestador** | Delega cálculos a subcalculadores; solo suma/agrupa; sin lógica de negocio | ❌ NO |
| **Builder** | Transforma datos ya calculados; mapea estructuras; no realiza cálculos | ❌ NO |
| **Compositor** | Ensambla/agrupa resultados de otros calculadores; pura composición | ❌ NO |

### Aplicación en Práctica

**Aplicó wiring:**
- ✅ NoPayroll, CadenaBCalculator, CadenaCCalculator, CostosFinancierosCalculator, PyGCalculator, KPIsCalculator
- Razón: Todos contienen `_audit_trace()` existente + lógica de cálculo propia

**No aplicó wiring:**
- ❌ CostosTotalesCalculator (orquestador, sin trace)
- ❌ CostToServeCalculator (calculador pero sin trace)
- ❌ VisionTarifasCalculator (calculador pero sin trace)
- ❌ VisionPyGBuilder (builder, no calculador)
- ❌ VisionImprimibleBuilder (compositor, no calculador)

---

## Validación Final ✅

### Test Results (Cero drift)

| Suite | Resultado | Detalles |
|---|---|---|
| `test_formula_id_guardrails.py` | 8/8 ✅ | Valida sintaxis, nombres y referencias FORMULA_ID |
| `test_channel_name_independence.py` | 8/8 ✅ | Valida independencia de nombres de canal |
| `test_baseline_formula_snapshot_v1.py` | 5/5 ✅ | Valida snapshots baseline V1 idénticos |
| `test_baseline_formula_snapshot_cadena_c_v1.py` | 5/5 ✅ | Valida snapshots baseline Cadena C idénticos |
| `tests/golden/` | 58/58 ✅ | Golden tests (paridad, comportamiento, cálculos) |
| **TOTAL** | **84/84 ✅** | **Cero drift, cero cambios esperados** |

**Fecha de validación:** 2026-06-06  
**Resultado:** Todos los tests pasan sin cambios

---

## Confirmación de Integridad 🔒

### Snapshots y Baselines

✅ **Cero drift en snapshots:**
- `tests/golden/*.json` — idénticos post-wiring
- `tests/refactor/test_baseline_formula_snapshot_v1.py` — assertions pasan sin cambios
- `tests/refactor/test_baseline_formula_snapshot_cadena_c_v1.py` — assertions pasan sin cambios

### Contratos Públicos

✅ **JSON público intacto:**
- `ApiResponse` structure sin cambios
- `PricingResult` fields sin cambios
- `VisionImprimible`, `VisionPyG`, `VisionTarifas`, `CostToServeResult` sin cambios
- Ningún `formula_ids` visible en serialización JSON (excluido via `to_dict()`)

### Cálculos y Fórmulas

✅ **Sin cambios funcionales:**
- Todos los cálculos idénticos pre/post-wiring
- No hay cambios en valores computados
- Business rules intactas
- Paridad Excel mantendida

### Storage Interno (TraceEntry)

✅ **Formula_ids almacenado correctamente:**
- `TraceEntry.formula_ids` — existe (campo opcional)
- Almacenamiento en memoria — sin impacto en disco
- Exclusión en JSON — `to_dict()` popea el campo antes de serializar
- Auditoría interna — accesible para trazabilidad sin comprometer contratos públicos

---

## Límites de la Solución Actual

### En Alcance ✅

- **Wiring en calculadores existentes** — 6 calculadores con formula_ids conectados
- **Trazabilidad interna** — formula_ids disponible en memoria para auditoría
- **Cero impacto público** — JSON y contratos intactos
- **Backward compatible** — todos los tests pasan sin cambios

### Fuera de Alcance ❌

1. **Nuevos puntos de auditoría**
   - CostToServeCalculator, VisionTarifasCalculator sin `_audit_trace()` existente
   - Crear nuevos traces requeriría decisión arquitectónica separada
   - **Recomendación:** Si en el futuro se desea auditar estos componentes, crear iniciativa separada de "Auditoría Extendida"

2. **Builders y Compositores**
   - VisionPyGBuilder, VisionImprimibleBuilder no incluyen cálculo
   - FORMULA_TRACE_RUNTIME_WIRING aplica solo a calculadores
   - **Recomendación:** Si se desea trazabilidad de composición, crear iniciativa separada de "Trazabilidad de Visiones"

3. **Orquestadores puros**
   - CostosTotalesCalculator no tiene lógica de cálculo propia
   - **Recomendación:** No aplica trazabilidad de fórmulas; solo delegación

---

## Commits Relacionados

### PHASE1-4 (Prior Session)
- NoPayroll, CadenaBCalculator, CadenaCCalculator, CostosFinancierosCalculator wired

### Current Session

| Phase | Commit | Status |
|---|---|---|
| PHASE5 | (prior) | Omitido — Orquestador |
| PHASE6 | e23259e | PyGCalculator wired (9 IDs) |
| PHASE7 | 3a9461a | KPIsCalculator wired (15 IDs) |
| PHASE8 | 08c0392 | CostToServeCalculator omitido — sin trace |
| PHASE9 | 3bb1adb | VisionTarifasCalculator omitido — sin trace |
| PHASE10 | 100d382 | VisionPyGBuilder omitido — builder |
| PHASE11 | c42365b | VisionImprimibleBuilder omitido — compositor |
| CLOSEOUT | (este commit) | Documentación final + validación |

---

## Métricas Finales

| Métrica | Valor |
|---|---|
| **Calculadores totales en pipeline** | 12 |
| **Con FORMULA_ID wiring** | 6 (50%) |
| **FORMULA_ID conectados** | 50 total |
| **Fases evaluadas** | 11 |
| **Fases completadas (wired)** | 6 |
| **Fases omitidas (documentadas)** | 5 |
| **Tests ejecutados** | 84 |
| **Tests pasando** | 84 (100%) |
| **Drift detectado** | 0 |
| **Archivos modificados (productivo)** | 6 |
| **Archivos documentados (omisión)** | 5 |

---

## Conclusión

**FORMULA_TRACE_RUNTIME_WIRING — SECUENCIA COMPLETADA CON ÉXITO.**

La iniciativa ha alcanzado su objetivo:

1. ✅ **Conectar FORMULA_ID existentes con trazabilidad runtime** — 6 calculadores wired con 50 FORMULA_ID total
2. ✅ **Mantener cero impacto en outputs públicos** — JSON intacto, contratos sin cambios
3. ✅ **Validar mediante tests** — 84/84 tests pasan sin cambios
4. ✅ **Documentar límites arquitectónicos** — 5 omisiones justificadas y documentadas

**El patrón FORMULA_TRACE_RUNTIME_WIRING está listo para auditoría y reproducibilidad interna.**

Para futuras iniciativas de trazabilidad:
- **Auditoría extendida** — crear nuevo patrón para CostToServe / VisionTarifas si se necesita traceabilidad
- **Trazabilidad de visiones** — crear patrón separado para builders si se necesita auditar composición

---

**Status:** ✅ **CERRADO — 2026-06-06**  
**Responsable:** claude-code (coordinador técnico)  
**Proxima revisión:** Por demanda de auditoría o nuevas iniciativas de trazabilidad
