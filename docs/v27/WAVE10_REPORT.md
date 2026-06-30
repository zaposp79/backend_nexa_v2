> **⚠️ POST-W17 CONTEXT**: This wave builds infrastructure (lineage / audit
> / versioning / certified mode) atop a motor that has NOT yet achieved
> true parity with Excel V2-7. The infrastructure is sound but operates
> on currently-divergent outputs. See `SEMANTIC_RECONSTRUCTION_PROGRAM.md`.

# WAVE 10 — Trazabilidad Financiera (FASE 5)

**Fecha**: 2026-05-28
**Branch**: `refactor/engine-v2`
**Foco**: Construir el sistema de lineage que responde
*"¿de dónde salió este número?"* con la cadena completa
visión → calculator → parámetro → hoja Excel.

---

## 1. Resumen ejecutivo

WAVE 10 introduce:

* `application/lineage/` con `LineageRef`, `LineageNode`, `LineageGraph`
  (dataclasses frozen) y `LineageQuery` (find/trace/explain).
* `infrastructure/lineage/` con `JsonLineageEmitter` (concrete
  `ITraceEmitter`), `NullLineageEmitter` y `LineageSnapshotRepository`.
* `application/lineage/lineage_builder.py` que siembra el grafo con los
  ~50-100 valores críticos antes/después del pipeline.
* Refactor mínimo en `engine.py`: nuevo argumento opcional
  `calcular(request, with_lineage=False)`; default behavior intacto.
* 32 tests nuevos bajo `tests/lineage/`.

**Resultado clave**:

* Critical (parity + baselines + contracts): **104 / 104** intactos.
* Default suite: **840 passed** (era 808 + 32 nuevos), 0 failed.
* `engine.calcular(req)` sin args: idéntico funcional y de performance
  vs pre-WAVE-10.
* `engine.calcular(req, with_lineage=True)` produce
  `(PricingResult, LineageGraph)` y persiste a
  `storage/lineage/<sim_id>/lineage.json`.

---

## 2. Estructura creada

```
application/lineage/
  __init__.py
  models.py              ← LineageRef / LineageNode / LineageGraph
  query.py               ← LineageQuery (find_value / trace_back / explain)
  lineage_builder.py     ← seed_lineage_from_request / _from_result

infrastructure/lineage/
  __init__.py
  null_emitter.py        ← NullLineageEmitter
  json_lineage_emitter.py← JsonLineageEmitter
  snapshot_repository.py ← LineageSnapshotRepository

tests/lineage/
  __init__.py
  conftest.py
  test_lineage_emitter.py            (11 tests)
  test_lineage_query.py              (6 tests)
  test_lineage_integration.py        (11 tests)
  test_lineage_paridad_preservada.py (2 tests)
  test_lineage_no_overhead.py        (2 tests)

docs/v27/
  W10_LINEAGE_SYSTEM.md  ← diseño + ejemplos
  WAVE10_REPORT.md       ← este archivo
```

---

## 3. Engine refactor

`engine.py::NexaPricingEngine.calcular(solicitud, with_lineage=False)`:

* `with_lineage=False` (default) → comportamiento idéntico pre-WAVE-10,
  retorna `PricingResult`.
* `with_lineage=True` →
  1. instancia `JsonLineageEmitter(simulation_id=panel.cliente)`,
  2. corre `seed_lineage_from_request`,
  3. ejecuta el pipeline tal cual,
  4. corre `seed_lineage_from_result`,
  5. `LineageSnapshotRepository().save(graph)` (best-effort),
  6. retorna `(PricingResult, LineageGraph)`.

Nada del cuerpo del pipeline cambió. Los use cases siguen llamando
`tracer.emit(stage, inputs, outputs, source)` con la firma WAVE 9; los
nuevos kwargs (`lineage_refs`, `value_name`, etc.) son opcionales.

---

## 4. Tests — counts

```
tests/lineage         32 passed   (NEW)
tests/parity          39 passed
tests/baselines       16 passed
tests/contracts       49 passed
                     ────
Critical             104 passed

Default suite:       840 passed / 0 failed / 0 errors / 23 skipped / 411 deselected / 1 xfailed
```

Distribución de los 32 tests lineage:

| Archivo                             | Tests | Propósito                                       |
|-------------------------------------|------:|-------------------------------------------------|
| test_lineage_emitter.py             |    11 | emit/get_graph/persistencia idempotente         |
| test_lineage_query.py               |     6 | find_value, trace_back, explain, cycles         |
| test_lineage_integration.py         |    11 | end-to-end con Bancamia: grafo, raíces, Excel   |
| test_lineage_paridad_preservada.py  |     2 | PyG + KPIs idénticos con/sin lineage            |
| test_lineage_no_overhead.py         |     2 | latencia bajo control                           |

---

## 5. Sample explain() — Bancamia

```
request.panel.margen = 0.18
  formula: Panel knob margen (deal=Bancamia)
  <- ContextBuilder  [REQUEST_BUILD]
    <- request.panel.margen = 0.18  (request)
    <- Excel:Panel-Deal!C9 = 0.18  (Excel:Panel-Deal!C9)
```

```
vision_tarifas.tarifa[canal=Agregado Cadena A] = {
    tarifa_fijo_fte: 184931296.09,
    ingreso_bruto:   184931296.09,
    facturacion:     184931296.09,
}
  formula: tarifa = costo_atribuible / factor_billing(margen, op, com, mk, desc)
  <- VisionTarifasCalculator.calcular  [VISION_BUILD]
    <- computed:factor_billing
    <- computed:payroll_ch       = 1.28729e+08
    <- computed:no_payroll_ch    = 459078
    <- HR-Campana.rotacion_ausentismo  (parametrization)
    <- request.panel.margen_a    = 0.18  (request)
```

---

## 6. Performance

5 corridas warm sobre Bancamia:

```
default avg:  16.2ms
lineage avg:  17.3ms
overhead:      1.1ms (6.5%)
```

* Default-path: 0% overhead vs pre-WAVE-10 (mismo `NullTraceEmitter`).
* Lineage-path: ~1ms, dentro del presupuesto W12 (<1s/req).

---

## 7. Decisiones tomadas

| Decisión                                                 | Rationale                                       |
|----------------------------------------------------------|-------------------------------------------------|
| Granularidad: valores críticos, no operación matemática  | Mantiene 50-100 nodos legibles vs 10K+ noise    |
| F9 placeholders strings literales hoy                    | W14 los hará dinámicos sin cambiar shape        |
| Persistencia best-effort (warn-log, no raise)            | Lineage no debe bloquear el resultado del deal  |
| LineageRef.source_type whitelist enforced en __post_init__ | Falla rápido si alguien inventa nuevo tipo    |
| LineageGraph + nodes son frozen dataclasses              | Imposibilita mutación post-build                |
| Default `with_lineage=False`                              | Backwards-compatible 100%                       |
| Persistencia bajo `storage/lineage/<sim_id>/lineage.json` | Mismo patrón que `storage/snapshots/` etc.     |

---

## 8. Compatibilidad

| Aspecto                                          | Estado            |
|--------------------------------------------------|-------------------|
| `engine.calcular(req)` sin args                  | Idéntico funcional + performance |
| Firma `ITraceEmitter.emit` (WAVE 9)              | Intacta           |
| Calculators legacy signatures                    | Intactas          |
| `domain/` purity                                  | Mantenida (no IO añadido) |
| Callsites WAVE 9 sin lineage kwargs              | Funcionan tal cual |

---

## 9. Bloqueos para waves siguientes

* **W11 (cloud-native)**: ninguno. El `LineageSnapshotRepository`
  acepta `base_dir` inyectable, así un adapter de Blob Storage solo
  necesita sustituir el directorio raíz.
* **W12 (perf)**: ninguno. Overhead default = 0%; lineage path está
  bajo el target.
* **W13 (audit endpoint)**: ninguno. `GET /audit/lineage/{sim_id}` solo
  necesita instanciar `LineageSnapshotRepository().load(sim_id)` y
  serializar `graph.to_dict()`.
* **W14 (versionado)**: ninguno. Tres placeholders (`engine_version`,
  `formula_set`, `parametrization_hashes`) ya viven en los modelos.

---

## 10. Tareas DEFERRED

| ID          | Detalle                                                      | Plan                                        |
|-------------|--------------------------------------------------------------|---------------------------------------------|
| W10-DEF-1   | Lineage por mes para cada `PyGMensual` (24 nodos × deal)     | W13 — cuando se construya el viewer audit  |
| W10-DEF-2   | Lineage de nodos intermedios (factor_billing, polizas calc)  | W12 — cuando se refactoricen los calcs huge|
| W10-DEF-3   | Excel cell map exhaustivo HR/GN/OP                           | W14 — necesita manifest del versionado     |
| W10-DEF-4   | Hash determinístico del grafo (firma para certificado)       | W15 — Certified mode                        |
| W10-DEF-5   | Compresión gzip del snapshot                                  | W11 — Blob Storage acepta gzip nativamente  |

---

## 11. Archivos creados/modificados

### Nuevos

* `application/lineage/__init__.py`
* `application/lineage/models.py`
* `application/lineage/query.py`
* `application/lineage/lineage_builder.py`
* `infrastructure/lineage/__init__.py`
* `infrastructure/lineage/null_emitter.py`
* `infrastructure/lineage/json_lineage_emitter.py`
* `infrastructure/lineage/snapshot_repository.py`
* `tests/lineage/__init__.py`
* `tests/lineage/conftest.py`
* `tests/lineage/test_lineage_emitter.py`
* `tests/lineage/test_lineage_query.py`
* `tests/lineage/test_lineage_integration.py`
* `tests/lineage/test_lineage_paridad_preservada.py`
* `tests/lineage/test_lineage_no_overhead.py`
* `docs/v27/W10_LINEAGE_SYSTEM.md`
* `docs/v27/WAVE10_REPORT.md`

### Modificados

* `engine.py` — `calcular()` acepta `with_lineage=False`.

### NO modificados

* `domain/*` (sigue puro)
* `calculators/*` (paridad inmutable)
* `application/use_cases/*` (signaturas WAVE 9 intactas)
* `application/ports/trace_emitter.py` (port WAVE 9 intacto)

---

## 12. Criterio de éxito — Cumplimiento

| Criterio                                                          | Resultado |
|-------------------------------------------------------------------|-----------|
| 104 críticos intactos                                              | ✓ 104 / 104 |
| Suite default ≥ 808 passed / 0 failed                              | ✓ 840 passed |
| ≥ 15 tests lineage passing                                         | ✓ 32 / 32 |
| `engine.calcular(req, with_lineage=True)` retorna grafo            | ✓ (PricingResult, LineageGraph) |
| `explain()` devuelve cadenas legibles                              | ✓ verificado en logs y test |
| Persistencia en storage/lineage/ funciona                          | ✓ idempotente, sort_keys |
| W10_LINEAGE_SYSTEM.md publicado                                    | ✓ |
| Default behavior unchanged                                          | ✓ paridad bit-exacta con/sin lineage |
| Performance default overhead ≤ 1%                                   | ✓ 0% (Null emitter idéntico) |

**Veredicto**: **READY**. WAVE 10 entrega lineage financiero completo,
auditable y consultable sin afectar la paridad ni la API pública. WAVE 11
(cloud-native) puede comenzar sin bloqueos.

— Fin de WAVE 10.
