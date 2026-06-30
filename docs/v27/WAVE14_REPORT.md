> **⚠️ POST-W17 CONTEXT**: This wave builds infrastructure (lineage / audit
> / versioning / certified mode) atop a motor that has NOT yet achieved
> true parity with Excel V2-7. The infrastructure is sound but operates
> on currently-divergent outputs. See `SEMANTIC_RECONSTRUCTION_PROGRAM.md`.

# WAVE 14 — Versionado formal del motor (FASE 9)

**Estado**: COMPLETADA
**Branch**: `refactor/engine-v2`
**Suite**: 887 passed / 23 skipped / 0 failed / 0 errors / 1 xfailed
**Críticos**: 141 / 141 (paridad inmutable)
**Versioning nuevos**: 26 / 26

---

## 1. Objetivo

Reemplazar los placeholders W10 (`engine_version="engine-v2"`,
`formula_set="formula-set-v2-7"`, `parametrization_hashes={}`) por
metadatos reales tomados de un único `VersionRegistry`, y resolver el
gap W13 donde `/calculate` generaba un UUID que no mapeaba contra el
lineage persistido bajo `panel.cliente`.

---

## 2. Componentes nuevos

```
application/versioning/
  __init__.py
  version_registry.py        ← VersionMetadata + VersionRegistry
tests/versioning/
  __init__.py
  conftest.py
  test_version_registry.py                    (8)
  test_simulation_id_mapping.py               (6)
  test_lineage_includes_real_versions.py      (5)
  test_audit_response_includes_versions.py    (4)
  test_backward_compat_legacy_lineage.py      (3)
docs/v27/
  W10_VERSIONING_STRATEGY.md
  WAVE14_REPORT.md                            (este archivo)
```

### 2.1 Componentes modificados

* `application/lineage/models.py`
  - `LineageNode.engine_version_placeholder` → `engine_version`
  - `LineageNode.formula_set_placeholder` → `formula_set`
  - Properties legacy mantenidas (alias) para callers pre-W14.
  - `from_dict` tolera ambas convenciones de keys.
  - `LineageGraph.version_metadata: Optional[dict]` (nuevo, persistido).
* `infrastructure/lineage/json_lineage_emitter.py`
  - Acepta `version_metadata: VersionMetadata` por constructor.
  - Stampa cada nodo con `engine_version`/`formula_set` reales.
  - El `LineageGraph` resultante incluye `parametrization_hashes` y
    `version_metadata` completos.
* `engine.py`
  - `NexaPricingEngine.__init__` acepta `version_registry`.
  - `_generate_simulation_id(req)` — id determinístico (request →
    metadata → panel → UUID4).
  - El path `with_lineage=True` resuelve un `sim_id` único y lo
    propaga al emitter, al graph, y a `PricingResult.simulation_id`.
* `application/use_cases/audit_simulation.py`
  - `AuditSimulationUseCase(version_registry=...)`.
  - `_resolve_versions(graph)` — precedencia
    `version_metadata > first_node > registry fallback`.
* `api/v1/simulation/calculate_router.py`
  - Usa `resultado.simulation_id` cuando está disponible (engine ya lo
    generó); cae a `ResultsRepository.new_id()` solo si falta.
* `contracts/api_v1/response/simulation_result.py`
  - Campos aditivos: `formula_set`, `parametrization_hashes`.
  - Schemas + OpenAPI regenerados.

---

## 3. simulation_id mapping — fix W13

| Componente                         | Antes (W13)                   | Ahora (W14)                                                       |
|------------------------------------|-------------------------------|-------------------------------------------------------------------|
| `engine.calcular(req, lineage)`    | sim_id = `panel.cliente`       | `_generate_simulation_id(req)` (metadata > panel.simulation_id > UUID4) |
| `JsonLineageEmitter(...)`          | recibía `panel.cliente`        | recibe el id canónico                                              |
| Persistencia lineage               | `storage/lineage/<cliente>/`   | `storage/lineage/<sim_id>/`                                        |
| `PricingResult.simulation_id`      | no set                        | poblado por el engine antes del retorno                            |
| `/calculate` response              | UUID del repo (desconectado)  | usa `resultado.simulation_id` cuando está                          |
| `/audit/simulation/{id}`           | 404 (id mismatch)             | resuelve el mismo id                                               |

---

## 4. Sample — `VersionRegistry.get_current().to_dict()`

```json
{
  "excel_version": "V2-7",
  "parametrization_version": "v2-7",
  "engine_version": "engine-v2",
  "api_version": "api-v1",
  "formula_set": "formula-set-v2-7",
  "baseline_version": null,
  "parametrization_hashes": {
    "hr": "ca2102d3772370862ee1484f793df1173084eccb5e7eb799bc1d00a2397e3a12",
    "gn": "8edbab73f00e4d373178067eaa748e98283a34e4fbff846f132fcec09f51f3e0",
    "op": "1448015658397c03c1568d4c346a707e46fece7bd31c25a13c01b55f8429bd1b",
    "business_rules": "c6e2e088f1d6ca8f241df7fb7ab81c33f9e75127f54ee4183fe7ce68ec0fb294"
  }
}
```

---

## 5. Tests — counts

| Suite                                        | Tests | Estado |
|----------------------------------------------|------:|--------|
| `tests/versioning/`                          |    26 | passed |
| `tests/parity` + `tests/baselines`           |    55 | passed |
| `tests/contracts` (incluye 5 audit contract) |    54 | passed |
| `tests/lineage` (W10)                        |    32 | passed |
| **Críticos totales**                         |   141 | passed |
| `tests/api/test_audit_endpoint.py`           |    16 | passed |
| **Full suite**                               |   887 | passed |

Comparativa pre-W14: 861 → 887 (+26). 0 regresiones.

---

## 6. Backward compat

* `LineageNode` mantiene `engine_version_placeholder` y
  `formula_set_placeholder` como properties read-only que devuelven el
  valor del campo nuevo.
* `LineageGraph.from_dict` acepta JSONs persistidos con las keys
  antiguas (`*_placeholder`) y los promociona a los campos nuevos.
* `AuditSimulationUseCase` detecta graphs legacy (sin
  `version_metadata`) y rellena los campos vacíos vía
  `VersionRegistry.get_current()` emitiendo un warning estructurado.
* `JsonLineageEmitter` sigue funcionando sin `version_metadata`
  (default = `VersionMetadata()` con literales pre-W14) — preserva los
  32 tests del W10 / 16 tests del W13 sin tocarlos.

---

## 7. Bloqueos para WAVE 15 (Certified Mode)

Ninguno. `VersionMetadata.baseline_version` ya existe; W15 solo debe:

1. Inyectar `baseline_version="v2-7-certified"` al construir el
   registry cuando `mode=certified` en `/calculate`.
2. Validar los hashes del request contra
   `VersionRegistry.compute_parametrization_hashes()` (HTTP 412 si
   divergen).
3. Comparar los outputs vs el baseline (extensión del
   `diff_vs_baseline` actual).

---

## 8. DEFERRED

| ID          | Detalle                                                            | Plan          |
|-------------|--------------------------------------------------------------------|---------------|
| W14-DEF-1   | Endpoint `?expected_parametrization_hash=...` (412 Precondition)   | WAVE 15 (certified mode) — más natural ahí. |
| W14-DEF-2   | Hash determinístico del grafo (firma del certificado completo)     | WAVE 15.      |
| W14-DEF-3   | Versionado de `formula_set` desacoplado de `parametrization_version` | Cuando se introduzcan fórmulas opcionales/experimentales. |
| W14-DEF-4   | Propagar `version_metadata` a `SimulationResultV1` cuando se devuelve sin lineage (path default) | WAVE 11/12 — el envelope api-v1 actualmente solo se emite bajo flag, no tiene tráfico productivo. |

---

## 9. Criterio de éxito — Cumplimiento

| Criterio                                                          | Resultado |
|-------------------------------------------------------------------|-----------|
| 141 críticos intactos                                              | OK (141/141) |
| Suite default ≥861 passed / 0 failed                               | OK (887/0) |
| ≥20 tests versioning passing                                       | OK (26)   |
| `/audit` retorna engine_version/formula_set/hashes reales          | OK        |
| `/calculate` genera simulation_id consultable en `/audit`          | OK        |
| W14 report + W10_VERSIONING_STRATEGY publicados                    | OK        |

**Veredicto**: READY. WAVE 15 (Certified Mode) puede arrancar sin
bloqueos.
