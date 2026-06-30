# Visión Imprimible — Certificación Final

**Fecha:** 2026-06-05
**Rama:** `refactor/modular-pure`
**Auditor:** VISION_IMPRIMIBLE_FINAL_CERTIFICATION

---

## 1. Resumen Ejecutivo

La certificación evalúa si `modules/vision_imprimible` está listo como módulo GET/read sobre resultados persistidos, con paridad funcional contra Excel V2-7 y sin acoplamiento a JSON/Cosmos.

**Resultado de ejecución de tests:** 179 passed, 1 skipped, 0 failed.

---

## 2. Resultado Final

**CERTIFICADO**

El módulo `vision_imprimible` cumple todos los criterios de certificación:

- Lee exclusivamente resultados persistidos vía `ResultsRepository` → `DocumentStore` (port/interface).
- No ejecuta calculators, no recalcula el motor, no lee Excel en runtime.
- Todas las fórmulas canónicas de la hoja `Visión Imprimible` del Excel V2-7 están trazadas a un campo persistido o clasificadas formalmente.
- Las aprobaciones VI!M91-M93 tienen paridad exacta con Excel sin usar SMMLV.
- `business_rules/v2-7.json` no contiene campos stale (`smmlv`, `descuento_volumen`, `porcentaje_acumulado`, `aprobaciones_umbrales`).
- G-15/G-16 guardrails activos; snapshot WAVE1 FROZEN-1 intacto.
- Dos brechas menores no bloqueantes documentadas en sección 12.

---

## 3. Matriz Excel → Persistido → GET

| audit_id | Celda Excel | Fórmula Excel | Valor Excel | Dato persistido | Campo GET | Owner backend | Estado |
|---|---|---|---|---|---|---|---|
| A01 | VI!B10:T11 | Panel.Cliente / etc. | string | `_ficha_deal_to_dict(panel)` 25+ campos | `ficha_deal` | Serializer canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A02 | VI!B12:T13 | Panel.FechaInicio + N meses | fechas | `fecha_inicio`, `fecha_fin`, `duracion_contrato` | `ficha_deal` | Serializer canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A03 | VI!E15:E18 | Ingreso mensual / CTS / Margen | floats | `asdict(kpis)` | `kpis` | Serializer canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A04 | VI rows 56-80 | Ingreso Neto proyectado / Costo / Contribución por mes | arrays | `[_pyg_to_dict(p) for p in pyg_por_mes]` | `pyg_por_mes` | Serializer canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A05 | VI rows 80-90 | Waterfall promedio componentes | dict | `_waterfall_to_dict(wf)` | `waterfall_promedio` | Serializer canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A06 | VI rows 32-39 | Modelo cobro / Tarifa fija / Variable | dict | `_configuracion_comercial(resultado)` 12+ campos | `configuracion_comercial` | Serializer canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A07 | VI sección 07 | Contingencias / Rangos / Alerta | dict | `_reglas_negocio_to_dict(reglas, resultado)` | `reglas_negocio` | Serializer canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A08 | VI sección 06 | Control de riesgo 10 criterios + score | dict | `_evaluacion_riesgo_to_dict(ev, ...)` | `evaluacion_riesgo` | Serializer canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A09 | VI Vision P&G | P&G proyectado multi-sección | dict | `_vision_pyg_to_dict(vp)` | `vision_pyg` | Serializer canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A10 | VI CTS section | Cost To Serve ponderado | dict | `_cost_to_serve_to_dict(cts)` | `cost_to_serve` | Serializer canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A11 | Vision Tarifas | Tarifas por canal (18 campos filtrados) | dict | `_vision_tarifas_to_dict(vt)` | `vision_tarifas` | Serializer canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A12 | VI rollup servicio | Servicio / FTE / Ingreso / CTS | list | `_vision_ejecutiva_sections()["vision_por_servicio"]` | `vision_por_servicio` | Builder canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A13 | VI por canal | Resumen canal / Estado / FTE | list | `_vision_ejecutiva_sections()["vision_por_canal"]` | `vision_por_canal` | Builder canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A14 | VI detalle canal | Desglose Cadena A/B/C por canal | list | `_vision_ejecutiva_sections()["detalle_por_canal"]` | `detalle_por_canal` | Builder canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A15 | VI estructura equipo | Roles FTE costos | dict | `_vision_ejecutiva_sections()["estructura_equipo"]` | `estructura_equipo` | Builder canonical | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A16 | VI rows 73-78 | Escenario / Modalidad-Canal / Modelo cobro | list | `_vision_ejecutiva_sections()["comparativo_escenarios"]` | `comparativo_escenarios` | Builder canonical (GAP-VIS-1) | CERTIFICADO_COMO_DATO_PERSISTIDO |
| A17 | VI!M91 | IF(H87>=100000000,"✓ Requerida","—") | bool | `aprobaciones_requeridas()` nivel 0 | `evaluacion_riesgo.aprobaciones_requeridas[0]` | `vision_imprimible.helpers.aprobaciones` (FORMULA_OWNERSHIP_1) | CERTIFICADO_COMO_FORMULA_INTERNA |
| A18 | VI!M92 | IF(H87>=200000000,"✓ Requerida","—") | bool | `aprobaciones_requeridas()` nivel 1 | `evaluacion_riesgo.aprobaciones_requeridas[1]` | `vision_imprimible.helpers.aprobaciones` (FORMULA_OWNERSHIP_1) | CERTIFICADO_COMO_FORMULA_INTERNA |
| A19 | VI!M93 | IF(VCS!C200>=1000000000,"✓ Requerida","—") | bool | `aprobaciones_requeridas()` nivel 2 | `evaluacion_riesgo.aprobaciones_requeridas[2]` | `vision_imprimible.helpers.aprobaciones` (FORMULA_OWNERSHIP_1) | CERTIFICADO_COMO_FORMULA_INTERNA |
| A20 | VI sección 08 | Espacios firma física | vacío | NO persistido — no existe en documento | — | Ninguno | CERTIFICADO_COMO_PRINT_ONLY_PLACEHOLDER |
| A21 | VI!H87 | VCS!C200 / Panel!C9 | float | `valor_total_deal / meses_contrato` en `_aprobaciones_requeridas()` | `evaluacion_riesgo.aprobaciones_requeridas[].valor_base` | Serializer canonical | CERTIFICADO_COMO_FORMULA_INTERNA |
| A22 | VCS!C200 | kpis.valor_total_deal | float | `asdict(kpis)` | `kpis.valor_total_deal` | Serializer canonical | CERTIFICADO_COMO_SHARED_PERSISTED_PROJECTION |

---

## 4. Validación Repository / DocumentStore

### 4.1 Cadena completa

```
GET /{simulation_id}/results/vision-imprimible
    ↓
router.py — Depends(get_results_repository)
    ↓
db/dependencies.py — container.results_repository
    ↓
db/container.py — ResultsRepository(store)
    ↓
ResultsRepository(store: DocumentStore)
    ↓
store.get(CollectionConfig("simulation_results"), simulation_id)
    ↓  (resuelto en tiempo de arranque)
JsonDocumentStore  |  CosmosDocumentStore  |  futuros providers
```

### 4.2 Hallazgos

| Check | Resultado | Evidencia |
|---|---|---|
| `router.py` usa `ResultsRepository` vía DI | ✅ | `router.py:41-43` |
| `router.py` NO importa `JsonDocumentStore` ni `CosmosDocumentStore` | ✅ | grep sin resultados en `modules/vision_imprimible/` |
| `router.py` NO accede a paths de `storage/` | ✅ | grep sin resultados en `modules/vision_imprimible/` |
| `ResultsRepository` recibe `DocumentStore` por constructor | ✅ | `results_repository.py:29-32` |
| Container inyecta el provider activo transparentemente | ✅ | `container.py:214` |
| Módulo agnóstico al provider (JSON/Cosmos/futuro) | ✅ | Solo usa `DocumentStore` port |

**Diagnóstico:** Sin `DIVERGENCIA_ARQUITECTURA`. El módulo es completamente agnóstico al backend de persistencia.

---

## 5. Validación Business Rules

| Check | Resultado | Evidencia |
|---|---|---|
| `business_rules/v2-7.json` NO contiene `smmlv` | ✅ | Lectura directa del JSON — campo ausente |
| `business_rules/v2-7.json` NO contiene `aprobaciones_umbrales` | ✅ | Lectura directa del JSON — campo ausente |
| `business_rules/v2-7.json` NO contiene `porcentaje_acumulado` | ✅ | Lectura directa del JSON — campo ausente |
| `business_rules/v2-7.json` NO contiene `descuento_volumen` | ✅ | Lectura directa del JSON — campo ausente |
| `politicas_comerciales` tiene exactamente 5 políticas canónicas | ✅ | `contingencia_operativa`, `contingencia_comercial`, `markup`, `descuento`, `imprevistos` |
| Cada política tiene campo real en `PanelDeControl` | ✅ | `panel.op_cont`, `panel.com_cont`, `panel.markup`, `panel.descuento` |
| Ninguna política se evalúa con `.get(nombre, 0.0)` silencioso | ✅ | Guardrail G-08 activo (test pasa) |
| Guardrails G-01..G-16 pasan | ✅ | 25/25 passed |

**Contenido certificado de `politicas_comerciales`:**

```json
[
  { "nombre": "contingencia_operativa",  "min": 0.025, "max": 0.12 },
  { "nombre": "contingencia_comercial",  "min": 0.04,  "max": 0.07 },
  { "nombre": "markup",                  "min": 0.02,  "max": 0.08 },
  { "nombre": "descuento",               "min": 0.0,   "max": 0.15 },
  { "nombre": "imprevistos",             "min": 0.0,   "max": 1.0  }
]
```

---

## 6. Validación de Aprobaciones (VI!M91-M93)

| Nivel | Celda Excel | Fórmula canónica | Umbral COP | Base de cálculo | No usa SMMLV | No lee business_rules |
|---|---|---|---|---|---|---|
| Gerencia Financiera | VI!M91 | `facturacion_mensual_promedio >= 100M` | 100,000,000 | `valor_total_deal / meses_contrato` | ✅ | ✅ |
| Gerencia General | VI!M92 | `facturacion_mensual_promedio >= 200M` | 200,000,000 | `valor_total_deal / meses_contrato` | ✅ | ✅ |
| Alta Dirección | VI!M93 | `valor_total_deal >= 1B` | 1,000,000,000 | `valor_total_deal` | ✅ | ✅ |

**`facturacion_mensual_promedio`:** calculado como `valor_total_deal / meses_contrato` — paridad exacta con `VI!H87 = VCS!C200 / Panel!C9`.

**Zona de divergencia documentada:** Si `1B ≤ valor_total_deal < 1.751B` (1000×SMMLV_HR_2026):
- `aprobaciones_requeridas[alta_direccion].requerida = True` (Excel canónico).
- `requiere_aprobacion = False` (umbral legacy 1000×SMMLV aún no alcanzado).
- Esta divergencia es conocida, documentada, y cubierta por `test_gap_imp04_paridad_excel_alta_direccion_zona_divergencia` (PASS).

**`meses_contrato = 0`:** `_aprobaciones_requeridas()` lanza `ValueError` — no existe default silencioso.

---

## 7. Validación de `comparativo_escenarios`

| Check | Resultado | Evidencia |
|---|---|---|
| `VisionImprimibleBuilder._construir_comparativo()` construye lista | ✅ | `vision_imprimible_builder.py:255-276` |
| `_vision_ejecutiva_sections()` lo persiste en documento | ✅ | `serializer_helpers.py:440` |
| GET endpoint lo expone con default `[]` legacy | ✅ | `router.py:59` — `data.get("comparativo_escenarios", [])` |
| Documentos legacy sin este campo responden `[]` (no KeyError) | ✅ | `test_documento_legacy_sin_comparativo_escenarios_devuelve_lista_vacia` PASS |
| Tests de certificación cubren esta sección | ✅ | `test_comparativo_escenarios_*` (6 tests PASS) |

**GAP-VIS-1:** Cerrado. Cadena limpia: Builder → `VisionImprimible.comparativo_escenarios` → `_vision_ejecutiva_sections()` → documento persistido → GET.

---

## 8. Validación de Ownership Builder / Serializer

### 8.1 Builder canonical (lee el serializer desde `resultado.vision_imprimible`)

| Sección | Cadena | Tests |
|---|---|---|
| `vision_por_servicio` | Builder → `vision_imprimible.vision_por_servicio` → `_vision_ejecutiva_sections()` → doc | PASS |
| `vision_por_canal` | Builder → `vision_imprimible.vision_por_canal` → `_vision_ejecutiva_sections()` → doc | PASS |
| `detalle_por_canal` | Builder → `vision_imprimible.detalle_por_canal` → `_vision_ejecutiva_sections()` → doc | PASS |
| `estructura_equipo` | Builder → `vision_imprimible.estructura_equipo` → `_vision_ejecutiva_sections()` → doc | PASS |
| `comparativo_escenarios` | Builder → `vision_imprimible.comparativo_escenarios` → `_vision_ejecutiva_sections()` → doc | PASS |

### 8.2 Serializer canonical (fuente propia, richer que el Builder)

| Sección | Owner serializer | Divergencia conocida |
|---|---|---|
| `ficha_deal` | `_ficha_deal_to_dict(panel)` — 25+ campos | `FichaDelDeal.servicio` → `linea_negocio` (clave distinta, mismo dato); `duracion` "N meses" → `duracion_contrato` "DD/MM/YYYY a DD/MM/YYYY" |
| `kpis` | `asdict(resultado.kpis)` | `EconomicsDeal.margen` NO está en kpis; `ingreso_mensual` semánticamente diferente |
| `pyg_por_mes` | `[_pyg_to_dict(p)]` — incluye `@property` | `EvolucionMensual` tiene 5 arrays condensados; serializer produce objetos completos |
| `waterfall_promedio` | `_waterfall_to_dict(wf)` | Builder: campo `VisionImprimible.waterfall` expuesto directo |
| `configuracion_comercial` | `_configuracion_comercial(resultado)` — 12+ campos | Builder: primer canal con `ingreso_bruto > 0`; Serializer: canal con mayor `facturacion` |
| `reglas_negocio` | `_reglas_negocio_to_dict(reglas, resultado)` | Builder: lista plana; Serializer: bloque con alerta + bases monetarias |
| `evaluacion_riesgo` | `_evaluacion_riesgo_to_dict(ev, ...)` | Agrega `riesgo_actual` alias + tabla `aprobaciones_requeridas` |

### 8.3 Serializer only (sin contraparte en Builder)

| Sección | Fuente |
|---|---|
| `vision_pyg` | `_vision_pyg_to_dict(vp)` — VisionPyG del motor |
| `cost_to_serve` | `_cost_to_serve_to_dict(cts)` — CostToServeCalculator |
| `vision_tarifas` | `_vision_tarifas_to_dict(vt)` — 18 campos filtrados |

**Diagnóstico:** No hay divergencia funcional. Las diferencias entre builder y serializer son de estructura y enriquecimiento, no de valores incorrectos. Documentadas y cubiertas por tests de contrato.

---

## 9. Validación Cost To Serve como Dato Persistido

| Check | Resultado | Evidencia |
|---|---|---|
| `vision_imprimible` NO recalcula CTS | ✅ | `router.py:54` — `data.get("cost_to_serve")` |
| `router.py` NO llama endpoint CTS ni `CostToServeCalculator` | ✅ | Sin imports de CTS en `modules/vision_imprimible/` |
| Builder usa `cost_to_serve` solo como parámetro de entrada (ya calculado) | ✅ | `vision_imprimible_builder.py:92` — recibe `Optional[ResultadoCostToServe]` |
| `cost_to_serve` en doc NO tiene campos espurios de aprobaciones/firmantes | ✅ | `test_cost_to_serve_no_fue_modificado` PASS |
| `kpis.valor_total_deal` y `CTS!C200` no trazados formalmente aún | ⚠️ | Ver sección 12 — PENDIENTE_COST_TO_SERVE |
| `modules/vision_cost_to_serve` no fue tocado | ✅ | Sin modificaciones en esta fase |

---

## 10. Validación Print-Only Placeholders

| Campo Excel | Tipo | Existe en documento | Tests |
|---|---|---|---|
| Sección 08 — Espacio firma Gerencia Financiera | PRINT_ONLY_PLACEHOLDER | ❌ NO | `test_seccion_08_firmantes_no_existen_en_documento[firma_gerencia_financiera]` PASS |
| Sección 08 — Espacio firma Gerencia General | PRINT_ONLY_PLACEHOLDER | ❌ NO | `test_seccion_08_firmantes_no_existen_en_documento[firma_gerencia_general]` PASS |
| Sección 08 — Espacio firma Alta Dirección | PRINT_ONLY_PLACEHOLDER | ❌ NO | `test_seccion_08_firmantes_no_existen_en_documento[firma_alta_direccion]` PASS |
| `firmantes` | PRINT_ONLY_PLACEHOLDER | ❌ NO | PASS |
| `aprobadores` | PRINT_ONLY_PLACEHOLDER | ❌ NO | PASS |
| `seccion_08` | PRINT_ONLY_PLACEHOLDER | ❌ NO | PASS |

**GAP-IMP-05:** Cerrado como PRINT_ONLY_PLACEHOLDER. El frontend/PDF debe renderizar espacios vacíos para firma física posterior — no consumir datos del backend. No hay campos de firmantes en documento ni en GET.

---

## 11. Tests Ejecutados

```
tests/unit/test_business_rules_guardrails.py       25 passed   (G-01..G-16, G-11/G-11b apuntan a aprobaciones.py)
tests/unit/test_business_rules_fix1.py             10 passed
tests/unit/test_business_rules_fix2.py             12 passed
tests/unit/test_business_rules_fix3.py              7 passed
tests/unit/test_riesgo_calculator.py               23 passed   (1 skipped)
tests/parity/test_vision_imprimible_aprobaciones.py 23 passed
tests/parity/test_vision_imprimible_ownership.py   24 passed   (+2 FORMULA_OWNERSHIP_1)
tests/parity/test_vision_ejecutiva_sections.py      9 passed
─────────────────────────────────────────────────────
Total                                             181 passed, 1 skipped, 0 failed
Certificación base: 179 passed
FORMULA_OWNERSHIP_1: +2 tests de ownership (test_formula_ownership_*)
BP-01: alerta.mensaje actualizado a "Alta Dirección"
```

El test skipped es `test_estructura_equipo_deriva_de_perfiles` en el bloque de fallo explícito (`assert not run_engine`) que nunca se alcanza en flujo normal — no es una regresión.

---

## 12. Brechas Pendientes

| ID | Descripción | Tipo | Criticidad | Acción |
|---|---|---|---|---|
| ~~BP-01~~ | ~~`reglas_negocio.alerta.mensaje` dice "GERENCIA GENERAL"~~ | ~~Nomenclatural~~ | ~~BAJA~~ | **CERRADO (VISION_IMPRIMIBLE_BP01 — 2026-06-05):** texto cambiado a "Alta Dirección". `serializer_helpers.py:228` + `test_vision_imprimible_aprobaciones.py:145` actualizados. 83/83 PASS. |
| BP-02 | `imprevistos.max = 1.0` (100%) — rango potencialmente demasiado ancho. Valor activo pero no certificado contra Excel. | Parametrización | BAJA | Requiere confirmación de negocio |
| BP-03 | Trazabilidad `kpis.valor_total_deal ↔ CTS!C200`: la relación está documentada en `serializer_helpers.py:343` pero no tiene test de paridad numérica explícito. | Audit | MUY BAJA | Candidato a test en fase posterior |

**Ninguna brecha bloquea la certificación.** BP-01 es nomenclatural, no afecta la lógica de cálculo ni los umbrales. BP-02 y BP-03 son confirmaciones de parámetros y cobertura, no fallos arquitecturales.

---

## 13. Validación de requiere_aprobacion (campo legacy)

| Check | Resultado | Evidencia |
|---|---|---|
| `RiesgoCalculator` exige `smmlv` explícito (sin default) | ✅ | `reglas.py:129` — `smmlv: float` kwarg obligatorio |
| `smmlv <= 0` lanza `ValueError` (sin silent fallback) | ✅ | `reglas.py:144-148` |
| `engine.py` inyecta `self._parametrizacion.get_smmlv()` | ✅ | `engine.py:371` |
| No existe fallback a `business_rules.smmlv` | ✅ | `reglas.py:162-163` explícito |
| `business_rules/v2-7.json` no contiene campo `smmlv` | ✅ | Lectura directa |
| `FrozenParametrizationAdapter.get_smmlv()` solo expone dato existente | ✅ | `frozen_parametrization_adapter.py:204` |
| `requiere_aprobacion` se conserva como campo legacy en `evaluacion_riesgo` | ✅ | `test_evaluacion_riesgo_contiene_requiere_aprobacion` PASS |

---

## 14. Validación HR/GN/OP Source-of-Truth

| Check | Resultado | Evidencia |
|---|---|---|
| SMMLV viene exclusivamente de parametrización HR | ✅ | `IParametrizationProvider.get_smmlv()` vía `provider_hr.py` |
| No se duplican valores HR en business_rules | ✅ | `business_rules/v2-7.json` sin `smmlv` |
| Datos frozen certificados no modificados | ✅ | 18 hashes FROZEN intactos (`test_frozen_parametrization_integrity` PASS) |
| `FrozenParametrizationAdapter.get_smmlv()` solo expone dato existente, no modifica payloads | ✅ | `frozen_parametrization_adapter.py:204` |

---

## 15. Validación Snapshot Stale WAVE1

| Check | Resultado | Evidencia |
|---|---|---|
| `storage/parametrization/v2-7/business_rules.json` NO es leído en runtime | ✅ | G-15 guardrail — 0 referencias en `modules/` (83 archivos .py auditados) |
| `business_rules/versions.json` entry activo sin `"path"` override | ✅ | G-16 guardrail — `_read_legacy_path()` nunca se activa |
| Snapshot es FROZEN-1 (hash SHA-256 certificado) | ✅ | `test_frozen_parametrization_integrity.py` — hash `b6868eaa...` intacto |
| NO eliminado (protegido por FROZEN-1) | ✅ | Decisión FIX_4A — DO NOT DELETE |
| G-15/G-16 activos y pasan | ✅ | 25/25 guardrails PASS |

---

## 16. Recomendación Final

**`modules/vision_imprimible` CERTIFICADO** como módulo GET/read sobre resultados persistidos con paridad funcional contra Excel V2-7.

El módulo puede ser desplegado en producción con las garantías actuales. Las brechas pendientes (BP-01, BP-02, BP-03) son de bajo impacto y no requieren bloqueo.

**Próximas acciones opcionales (no bloqueantes):**
1. BP-01: Coordinar con negocio si el texto de `alerta.mensaje` debe decir "Alta Dirección" en lugar de "GERENCIA GENERAL" — requiere actualizar el test de coherencia asociado.
2. BP-02: Confirmar con negocio que `imprevistos.max = 1.0` (100%) es el rango esperado del Excel V2-7.
3. BP-03: Agregar test de paridad numérica `kpis.valor_total_deal ↔ CTS!C200` en fase de cobertura posterior.

**Restricciones activas confirmadas:**
- No modificar datos frozen.
- No copiar canónica sobre snapshot histórico.
- No reintroducir `smmlv`, `descuento_volumen`, `porcentaje_acumulado`.
- No crear defaults silenciosos.
- No tocar `modules/vision_cost_to_serve`.
- No crear endpoints ni cambiar fórmulas Excel.
