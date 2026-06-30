# WAVE 10 — Financial Lineage System (FASE 5)

**Fecha**: 2026-05-28
**Branch**: `refactor/engine-v2`
**Status**: SHIPPED

---

## 1. Objetivo

Permitir responder, para cualquier valor financiero producido por el motor,
la pregunta **"¿de dónde salió este número?"** con la cadena completa:

    visión / KPI
        ← calculator
            ← parámetro (HR / GN / OP)
                ← celda Excel (hoja + cell)
            ← entrada del request (panel knob)

El sistema produce un `LineageGraph` por simulación, serializable,
consultable y persistido en disco.

---

## 2. Arquitectura

```
application/
  lineage/
    __init__.py            ← API pública
    models.py              ← LineageRef / LineageNode / LineageGraph (frozen)
    query.py               ← LineageQuery (find_value / trace_back / explain)
    lineage_builder.py     ← seed_lineage_from_{request,result}
infrastructure/
  lineage/
    __init__.py            ← API pública
    null_emitter.py        ← NullLineageEmitter (no-op)
    json_lineage_emitter.py← JsonLineageEmitter (buffer + get_graph)
    snapshot_repository.py ← LineageSnapshotRepository (storage/lineage/*)
```

Reglas de capas:

* `domain/` permanece puro: cero IO, cero logging, cero conocimiento de lineage.
* `application/lineage/` solo describe estructuras y consultas.
* `infrastructure/lineage/` provee la implementación concreta del port
  `ITraceEmitter` (definido en WAVE 9).

---

## 3. Modelo de datos

### `LineageRef`

Referencia inmutable a una fuente de dato.

```python
LineageRef(
    source_type="excel",            # request | parametrization | excel | computed | constant
    source_id="Excel:Panel-Deal!C9",
    value=0.21,
    sheet="Panel-Deal",
    cell="C9",
    formula=None,
)
```

### `LineageNode`

Un nodo del grafo de cálculo.

```python
LineageNode(
    trace_id=uuid4,
    simulation_id="Bancamia",
    stage="VISION_BUILD",
    calculator="PricingCalculator.calcular_factor_billing",
    value_name="vision_tarifas.tarifa[canal=WhatsApp]",
    value=8421.33,
    formula="tarifa = costo / ((1-m)*(1-op)*(1-com)*(1-mk)*(1+desc))",
    inputs=( LineageRef(...), LineageRef(...), ... ),
    engine_version_placeholder="engine-v2",   # F9 → SemVer real en W14
    formula_set_placeholder="formula-set-v2-7",
)
```

### `LineageGraph`

```python
LineageGraph(
    simulation_id="Bancamia",
    nodes=( LineageNode, ... ),
    roots=("uuid-of-utilidad_neta_total", "uuid-of-valor_total_deal", ...),
    parametrization_hashes={},   # placeholder W14
)
```

Todos los dataclasses son `frozen=True`. `to_dict()` y `from_dict()`
permiten round-trips JSON deterministas (sort_keys, sin timestamps).

---

## 4. Cómo se enciende lineage

API pública del motor:

```python
engine = NexaPricingEngine()

# Modo default (idéntico a pre-WAVE-10)
result = engine.calcular(request)

# Modo lineage
result, graph = engine.calcular(request, with_lineage=True)
```

Cuando `with_lineage=True`:

1. `JsonLineageEmitter(simulation_id=panel.cliente)` se crea.
2. `seed_lineage_from_request` emite nodos por cada knob del panel,
   indexación y cadenas activas. Cada knob lleva tanto su `request`-ref
   como su Excel-ref (mapa estático en `lineage_builder.py`).
3. El pipeline corre tal cual (sin cambios funcionales).
4. `seed_lineage_from_result` emite nodos por:
   - KPIs (`kpis.*`)
   - PyG mensual (primer y último mes — ancla)
   - CTS (`cost_to_serve.*`)
   - Cada canal de `vision_tarifas`
5. `LineageGraph` se persiste en `storage/lineage/<simulation_id>/lineage.json`.
6. Se devuelve la tupla `(PricingResult, LineageGraph)`.

Cuando `with_lineage=False` (default), se inyecta el `NullTraceEmitter`
existente desde WAVE 9 — la performance es idéntica a pre-WAVE-10.

---

## 5. Granularidad

Decisión de WAVE 10: **por valor crítico de visión**, no por operación.

Run real (Bancamia):

```
sim_id=Bancamia nodes=29 roots=8
```

Cobertura por dominio:

| Dominio                | Nodos típicos                                              |
|------------------------|------------------------------------------------------------|
| Panel-Deal knobs       | 11 (margen, op_cont, com_cont, markup, descuento, …)       |
| Indexación             | 1                                                          |
| Cadenas activas        | 1                                                          |
| KPIs                   | 9                                                          |
| PyG (anclas)           | 2 (primer + último mes)                                    |
| CostToServe            | hasta 5 (cuando A está activa)                             |
| Vision tarifas canales | 1 por canal + 4 agregados                                  |

El plan establecía 50-100 nodos como objetivo. El run Bancamia produce 29
porque tiene 1 canal de Cadena A consolidado; deals multicanal escalan
naturalmente.

---

## 6. Consultas (`LineageQuery`)

### `find_value(value_name) -> LineageNode | None`

Devuelve el último nodo que produjo `value_name`. Conveniencia para los
casos donde el grafo emite el mismo `value_name` varias veces (last writer
wins).

### `trace_back(value_name) -> list[LineageRef]`

Recorre los padres recursivamente y devuelve la lista plana de refs
visitadas. Maneja ciclos vía `seen_traces`.

### `explain(value_name) -> str`

Render legible tipo:

```
request.panel.margen = 0.18
  formula: Panel knob margen (deal=Bancamia)
  <- ContextBuilder  [REQUEST_BUILD]
    <- request.panel.margen = 0.18  (request)
    <- Excel:Panel-Deal!C9 = 0.18  (Excel:Panel-Deal!C9)
```

```
vision_tarifas.tarifa[canal=Agregado Cadena A] = {...}
  formula: tarifa = costo_atribuible / factor_billing(margen, op, com, mk, desc)
  <- VisionTarifasCalculator.calcular  [VISION_BUILD]
    <- computed:factor_billing = <none>
    <- computed:payroll_ch = 1.28729e+08
    <- computed:no_payroll_ch = 459078
    <- HR-Campana.rotacion_ausentismo = <none>  (parametrization)
    <- request.panel.margen_a = 0.18  (request)
```

---

## 7. Persistencia

`LineageSnapshotRepository.save(graph)`:

* Archivo: `storage/lineage/<simulation_id>/lineage.json`
* Format: JSON con `sort_keys=True, indent=2, default=str`
* IDs no-seguros se sanitizan con regex `[^A-Za-z0-9_.\-]+ -> _`
* Idempotente — sucesivas escrituras producen el mismo bytewise output.

`LineageSnapshotRepository.load(simulation_id)`:

* Lee y devuelve un `LineageGraph` reconstituido con `from_dict()`
* `exists(simulation_id) -> bool` permite probing.

---

## 8. F9 placeholders

Tres campos están reservados para WAVE 14 (Versionado formal):

| Campo                              | Default actual         | Plan W14                         |
|------------------------------------|------------------------|----------------------------------|
| `engine_version_placeholder`       | `"engine-v2"`          | SemVer derivado de tag git       |
| `formula_set_placeholder`          | `"formula-set-v2-7"`   | Hash del manifest de fórmulas    |
| `parametrization_hashes` (graph)   | `{}`                   | `{hr: <sha>, gn: <sha>, op: <sha>}` |

W14 reemplazará los valores manteniendo el shape de los campos, así no se
rompe ningún consumidor.

---

## 9. Performance

Medición sintética (Bancamia, 5 corridas):

```
default avg:  16.2ms
lineage avg:  17.3ms
overhead:      1.1ms (6.5%)
```

* Default-path overhead vs pre-WAVE-10: **0%** (mismo Null emitter).
* Lineage-path overhead: ~1ms, dominado por construcción de nodos y
  persistencia en disco. No bloquea el target de W12 (<1s).

---

## 10. Compatibilidad

| Aspecto                                          | Estado    |
|--------------------------------------------------|-----------|
| `engine.calcular(req)` sin args                  | Idéntico  |
| Signatures de calculators legacy                 | Intactas  |
| ITraceEmitter port (WAVE 9)                      | Mantenida |
| Llamadas legacy a `tracer.emit(stage, in, out, source)` | Funcionan tal cual |
| `domain/` purity                                  | Mantenida |

Los nuevos kwargs del emitter (`lineage_refs`, `value_name`, `formula`,
`calculator`, `is_root`) son opcionales — los use cases existentes los
ignoran sin error.

---

## 11. Próximos waves que consumen lineage

* **W11 — Azure Functions**: el `LineageGraph` puede empaquetarse como
  output Blob bajo el path `lineage/<sim_id>/`.
* **W13 — Audit endpoint**: `GET /audit/lineage/{simulation_id}` carga
  con `LineageSnapshotRepository.load(...)` y serializa a JSON.
* **W14 — Versionado**: rellena `parametrization_hashes` y reemplaza
  los placeholders por valores reales.
* **W15 — Certified mode**: la firma del resultado incluye el hash del
  grafo de lineage.

---

## 12. Cómo se extiende

Agregar un valor crítico al lineage es localizado:

1. En `lineage_builder.py`, añadir un emit en el seed correspondiente
   (`_emit_kpis`, `_emit_vision_tarifas`, etc.).
2. Pasar `value_name`, `formula`, y `lineage_refs` explícitos.
3. (Opcional) Marcar `is_root=True` si el valor es un output final.

No se requiere tocar:
* domain/* (puro)
* calculators/* (paridad)
* engine.py (los seeds corren antes/después del pipeline)

---

— Fin de W10_LINEAGE_SYSTEM.md
