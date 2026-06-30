# CALCULATION_PERSISTENCE_STEP1_STORAGE_MAP

**Fecha:** 2026-06-06  
**Status:** ✅ MAPEADO — Sin cambios de código  
**Objetivo:** Mapear exactamente qué datos se guardan tras una simulación

---

## Resumen Ejecutivo

**Arquitectura actual de persistencia:**

Tras ejecutar `POST /api/v1/simulation/calculate`, el motor guarda:

1. **PricingResult completo** — `storage/simulation_results/{simulation_id}.json`
   - Contiene todas las visiones (Imprimible, PyG, Tarifas, CostToServe) calculadas
   - Agnóstico JSON/Cosmos vía DocumentStore

2. **Traceabilidad** — `storage/traceability/{simulation_id}.json` (FASE G)
   - Raw request, solicitud normalizada, resultado
   - Escenarios aplicados, pólizas usuario

3. **SimulationSnapshot** — `storage/snapshots/{simulation_id}.json` (FASE 4)
   - Raw input, input normalizado, log de normalización
   - Parametrización, provenance, resultado, panel summary

**Total guardado: 3 documentos JSON por simulación**

---

## Matriz de Persistencia Detallada

### Capa 1: INPUT (Parametrización)

| Dato | Se calcula en | Se guarda hoy | Ubicación/Repositorio | JSON/Cosmos agnóstico | Consumidor | Estado |
|---|---|---|---|---|---|---|
| **Parametrización HR (cargada)** | SimulationContextBuilder | SÍ (en snapshot) | snapshots/{sim_id}.json parametrization_snapshot.hr | ✅ SÍ | Builder, calculadores | PERSISTED_AS_BLOB |
| **Parametrización GN (cargada)** | SimulationContextBuilder | SÍ (en snapshot) | snapshots/{sim_id}.json parametrization_snapshot.gn | ✅ SÍ | Builder, calculadores | PERSISTED_AS_BLOB |
| **Parametrización OP (cargada)** | SimulationContextBuilder | SÍ (en snapshot) | snapshots/{sim_id}.json parametrization_snapshot.op | ✅ SÍ | Builder, calculadores | PERSISTED_AS_BLOB |
| **Metadata + Panel normalizado** | UserInputLoader | SÍ | snapshots/{sim_id}.json normalized_input + panel_summary_data | ✅ SÍ | Debugging, auditoría | PERSISTED |

### Capa 2: NOMINALES (Cálculos de Cadena A)

| Dato | Se calcula en | Se guarda hoy | Ubicación/Repositorio | JSON/Cosmos agnóstico | Consumidor | Estado |
|---|---|---|---|---|---|---|
| **Nomina por perfil (nómina cargada)** | NominaCalculator | NO (solo en memoria) | — | — | PyGCalculator, VisionPyGBuilder | NOT_PERSISTED |
| **Comisiones, capacitación, examenes, etc.** | NominaCalculator | NO (solo en memoria) | — | — | PyGCalculator | NOT_PERSISTED |
| **No Payroll (OPEX_TI, CAPEX, costos fijos)** | NoPayrollCalculator | NO (solo en memoria) | — | — | PyGCalculator, VisionPyGBuilder | NOT_PERSISTED |

**NOTA:** NominaCalculator y NoPayrollCalculator retornan objetos internos que se consumen en PyGCalculator pero NO se persisten directamente. Sus valores aparecen en pyg_por_mes (agregados mensualmente).

### Capa 3: CADENAS (B, C)

| Dato | Se calcula en | Se guarda hoy | Ubicación/Repositorio | JSON/Cosmos agnóstico | Consumidor | Estado |
|---|---|---|---|---|---|---|
| **Cadena B (componentes, descuentos, facturación)** | CadenaBCalculator | NO (solo en memoria) | — | — | PyGCalculator, CostosTotalesCalculator | NOT_PERSISTED |
| **Cadena C (tarifa, opex, inversiones)** | CadenaCCalculator | NO (solo en memoria) | — | — | PyGCalculator, CostosTotalesCalculator | NOT_PERSISTED |
| **Costos Financieros (ICA, GMF, pólizas)** | CostosFinancierosCalculator | NO (solo en memoria) | — | — | PyGCalculator | NOT_PERSISTED |

**NOTA:** Los valores calculados en cada cadena aparecen en pyg_por_mes (agregados por mes) pero NO se guardan en detalle por transacción.

### Capa 4: AGREGACIONES MENSUALES

| Dato | Se calcula en | Se guarda hoy | Ubicación/Repositorio | JSON/Cosmos agnóstico | Consumidor | Estado |
|---|---|---|---|---|---|---|
| **PyG Mensual (pyg_por_mes)** | PyGCalculator | ✅ SÍ | simulation_results/{sim_id}.json["pyg_por_mes"] | ✅ SÍ | VisionPyGBuilder, Evolución gráficos, waterfall | PERSISTED |
| **Costos Totales por Mes** | PyGCalculator | ✅ SÍ (en pyg_por_mes) | simulation_results/{sim_id}.json["pyg_por_mes"][m].costo_total | ✅ SÍ | Evolución, Waterfall | PERSISTED |
| **Ingreso Bruto/Neto por Mes** | PyGCalculator | ✅ SÍ (en pyg_por_mes) | simulation_results/{sim_id}.json["pyg_por_mes"][m].ingreso_bruto/.neto | ✅ SÍ | Evolución, Waterfall | PERSISTED |

### Capa 5: KPIs Y AGREGACIONES DEAL-WIDE

| Dato | Se calcula en | Se guarda hoy | Ubicación/Repositorio | JSON/Cosmos agnóstico | Consumidor | Estado |
|---|---|---|---|---|---|---|
| **KPIs del Deal** | KPIsCalculator | ✅ SÍ | simulation_results/{sim_id}.json["kpis"] | ✅ SÍ | VisionImprimible (sección Economics) | PERSISTED |
| **Tarifa Mensual** | KPIsCalculator | ✅ SÍ (en kpis) | simulation_results/{sim_id}.json["kpis"].tarifa_mensual | ✅ SÍ | Vision Tarifas, Imprimible | PERSISTED |
| **Margen mínimo requerido** | KPIsCalculator | ✅ SÍ (en kpis) | simulation_results/{sim_id}.json["kpis"].margen_minimo | ✅ SÍ | Validación, Imprimible | PERSISTED |
| **Utilidad Neta Total** | KPIsCalculator | ✅ SÍ (en kpis) | simulation_results/{sim_id}.json["kpis"].utilidad_neta | ✅ SÍ | Economics, Imprimible | PERSISTED |

### Capa 6: VISIONES (Transformaciones)

| Dato | Se calcula en | Se guarda hoy | Ubicación/Repositorio | JSON/Cosmos agnóstico | Consumidor | Estado |
|---|---|---|---|---|---|---|
| **Vision Tarifas (escenarios, tarifas)** | VisionTarifasCalculator | ✅ SÍ | simulation_results/{sim_id}.json["vision_tarifas"] | ✅ SÍ | GET /vision-tarifas endpoint, Imprimible | PERSISTED |
| **Vision P&G (estructura tabular)** | VisionPyGBuilder | ✅ SÍ | simulation_results/{sim_id}.json["vision_pyg"] | ✅ SÍ | GET /vision-pyg endpoint, Imprimible | PERSISTED |
| **Cost To Serve (desglose por cadena)** | CostToServeCalculator | ✅ SÍ | simulation_results/{sim_id}.json["cost_to_serve"] | ✅ SÍ | GET /cost-to-serve endpoint, Imprimible | PERSISTED |
| **Vision Imprimible (9 secciones completas)** | VisionImprimibleBuilder | ✅ SÍ (en serialización) | simulation_results/{sim_id}.json (documento completo) | ✅ SÍ | GET /vision-imprimible endpoint | PERSISTED_AS_BLOB |
| **Waterfall Promedio** | engine._calcular_pipeline | ✅ SÍ | simulation_results/{sim_id}.json["waterfall"] | ✅ SÍ | Gráfico de Waterfall, Imprimible | PERSISTED |
| **Reglas de Negocio** | engine._calcular_pipeline | ✅ SÍ | simulation_results/{sim_id}.json["reglas_negocio"] | ✅ SÍ | Validación, Imprimible | PERSISTED |
| **Evaluación de Riesgo** | RiesgoCalculator (opcional) | ✅ SÍ | simulation_results/{sim_id}.json["evaluacion_riesgo"] | ✅ SÍ | Imprimible | PERSISTED |

### Capa 7: AUDIT & TRACEABILITY

| Dato | Se calcula en | Se guarda hoy | Ubicación/Repositorio | JSON/Cosmos agnóstico | Consumidor | Estado |
|---|---|---|---|---|---|---|
| **Audit Trace (FORMULA_ID internos)** | AuditTracer (thread-local) | NO (solo en memoria) | — | — | Debugging interno, test queries | NOT_PERSISTED |
| **Traceabilidad contractual (FASE G)** | _trace_writer.write() | ✅ SÍ | traceability/{sim_id}.json | ✅ SÍ | GET /traceability endpoint | PERSISTED |
| **Raw Request (user_input)** | UserInputLoader | ✅ SÍ (en snapshot + traceability) | snapshots/{sim_id}.json + traceability/{sim_id}.json | ✅ SÍ | Auditoría, reproducibilidad | PERSISTED_AS_BLOB |

---

## Análisis por Categoría

### ✅ SÍ se guarda — PERSISTED

Estos datos se guardan en `simulation_results/{sim_id}.json` vía `PricingResult`:

1. **pyg_por_mes** — P&G mensual completo (13 meses)
2. **kpis** — KPIsCalculator output
3. **vision_tarifas** — Escenarios, tarifas, factores
4. **vision_pyg** — Tablas estructuradas P&G
5. **cost_to_serve** — CTS desglosado por cadena
6. **vision_imprimible** — Documento completo (9 secciones)
7. **waterfall** — Promedios y gráfico
8. **reglas_negocio** — Reglas y validaciones
9. **evaluacion_riesgo** — Risk score (si aplica)
10. **panel** — PanelDeControl normalizado

**Total: 10 campos en PricingResult**

### ❌ NO se guarda — NOT_PERSISTED

Estos datos se calculan pero NO se persisten (existen solo en memoria):

1. **Nomina por perfil** — Calculado por NominaCalculator, consumido en PyGCalculator
2. **No Payroll detallado** — Calculado por NoPayrollCalculator, agregado en PyGCalculator
3. **Cadena B detallado** — Calculado por CadenaBCalculator, agregado en PyGCalculator
4. **Cadena C detallado** — Calculado por CadenaCCalculator, agregado en PyGCalculator
5. **Costos Financieros detallado** — Calculado por CostosFinancierosCalculator, agregado en PyGCalculator
6. **Audit Trace internos (FORMULA_ID)** — Almacenado en TraceEntry.formula_ids (memoria, no serializado)

**Total: 6 categorías de datos efímeros**

---

## Flujo de Lectura: Cómo se Accede a Datos Guardados

### POST /calculate → Guarda

```
1. NexaPricingEngine.calcular(solicitud)
   ├─ Calcula 10 capas (transitorios en memoria)
   └─ Retorna PricingResult

2. pricing_result_to_dict(resultado, sim_id)
   └─ Convierte a dict (captura propiedades @property)

3. _results_repo.save(full_dict)
   └─ Guarda en storage/simulation_results/{sim_id}.json

4. _trace_writer.write(...)
   └─ Guarda en storage/traceability/{sim_id}.json

5. _snapshot_repo.save(_snapshot)
   └─ Guarda en storage/snapshots/{sim_id}.json
```

### GET /vision-imprimible, /vision-pyg, /vision-tarifas, /cost-to-serve → Lee

```
1. GET /{simulation_id}/results/vision-imprimible
   └─ router.get_vision_imprimible()
      └─ _results_repo.get(simulation_id)
         └─ DocumentStore.get("simulation_results", id)
            └─ Lee storage/simulation_results/{sim_id}.json

2. Endpoint retorna resultado["vision_imprimible"]
   (ya serializado, no recalcula)

3. Similar para vision-pyg, vision-tarifas, cost-to-serve
   (todos leen del mismo JSON persistido)
```

---

## Qué Visiones LEEN Datos Guardados

### Visiones que CONSUMEN datos guardados (READ_FROM_PERSISTED_RESULT)

| Vision | Lee desde | Datos utilizados | Cálculo nuevo |
|---|---|---|---|
| **VisionImprimible** | simulation_results.json | pyg_por_mes, kpis, vision_tarifas, cost_to_serve, waterfall, panel | NO — solo ensambla |
| **VisionPyG** | simulation_results.json | pyg_por_mes (mensual crudo) | SÍ — estructura tabular |
| **VisionTarifas** | simulation_results.json | vision_tarifas (ya calculado) | NO — solo presenta |
| **CostToServe** | simulation_results.json | cost_to_serve (ya calculado) | NO — solo presenta |

---

## Qué Visiones RECALCULAN (RECALCULATED_BY_VISION)

### NO — Ninguna visión recalcula en el flujo actual

Todas las visiones consumen datos ya calculados. Incluso VisionPyGBuilder solo transforma pyg_por_mes (datos mensuales crudos) en estructura tabular, sin recálculos aritméticos.

---

## Datos Intermedios (Cálculos por Persona/Transacción)

### ❓ UNKNOWN_NEEDS_CHECK

Los siguientes datos se calculan pero **desconocemos si se persisten o solo se agregan a PyGMensual**:

1. **Nomina detallada por perfil** — ¿Se guarda en algún lado? (Necesita verificación en NominaCalculator)
2. **Cadena B por transacción** — ¿Se guarda o solo suma por mes? (Necesita verificación en CadenaBCalculator)
3. **Cadena C por transacción** — ¿Se guarda o solo suma por mes? (Necesita verificación en CadenaCCalculator)
4. **Desglose por canal en Vision Tarifas** — ¿Se guardan datos por canal o solo resumen?

**Recomendación:** Estos requieren inspección en STEP2.

---

## Riscos Identificados

### ✅ CONTROLADO — Datos guardados

| Riesgo | Mitigación | Estado |
|---|---|---|
| Pérdida de cálculos intermedios | No hay recuperación de cálc. intermedios; se recalculan todo if needed | MITIGATED |
| Inconsistencia si se persisten datos parciales | Persistimos PricingResult completo (transacción atómica) | MITIGATED |
| Cognición sobre qué está guardado | Esta matriz documenta estado actual | DOCUMENTED |

### ⚠️ RIESGO POTENCIAL — Paso 2

Si en STEP2 se decide cambiar persistencia:
- ¿Guardar datos por perfil/transacción (granular)?
- ¿Cambiar de PricingResult blob a múltiples colecciones?
- ¿Visiones lean datos guardados o recalcen?

**Esto requiere decisión arquitectónica explícita.**

---

## Paso 2 Recomendado

### CALCULATION_PERSISTENCE_STEP2_REFACTOR_STRATEGY

Basado en este mapeo, STEP2 debería:

1. **Validar qué datos intermedios faltan**
   - Inspeccionar NominaCalculator: ¿qué persiste?
   - Inspeccionar CadenaBCalculator: ¿qué persiste?
   - Inspeccionar CadenaCCalculator: ¿qué persiste?

2. **Decidir arquitectura objetivo**
   - ¿Guardar detalles por perfil/transacción (normalizados)?
   - ¿O mantener agregación por mes (PyGMensual)?

3. **Rediseñar persistencia si aplica**
   - Si objetivo es "datos granulares": crear colecciones Facts
   - Si objetivo es "solo PyGMensual": documentar por qué no se guardandetalles

4. **Evaluar impacto en visiones**
   - ¿Visiones pueden leer datos granulares y recalcular?
   - ¿O mantener modelo actual (vision = transformación)?

---

## Conclusión

**STEP1 MAPEO COMPLETADO:**

- ✅ Se identificó qué se guarda hoy (PricingResult completo + Traceability + Snapshot)
- ✅ Se identificó qué NO se guarda (datos intermedios por perfil/transacción)
- ✅ Se identificó que visiones consumen datos guardados (no recalculan)
- ✅ Se documentó flujo de lectura (agnóstico JSON/Cosmos)
- ✅ Matriz completa con estados y ubicaciones
- ✅ Riesgos identificados para STEP2

**Readiness para STEP2:** LISTA — sin cambios de código, solo mapeo.

---

**Status:** ✅ **CERRADO — 2026-06-06**  
**Próximo paso:** CALCULATION_PERSISTENCE_STEP2_REFACTOR_STRATEGY (decisión arquitectónica)
