> **⚠️ POST-W17 CONTEXT**: This wave builds infrastructure (lineage / audit
> / versioning / certified mode) atop a motor that has NOT yet achieved
> true parity with Excel V2-7. The infrastructure is sound but operates
> on currently-divergent outputs. See `SEMANTIC_RECONSTRUCTION_PROGRAM.md`.

# WAVE 13 — Modo Auditoría (`/api/v1/audit/...`)

**Estado**: COMPLETADA — 21 tests verdes, 0 regresiones, paridad intacta.

**Branch**: `refactor/engine-v2`
**Suite**: 861 passed / 23 skipped / 0 failed / 0 errors
**Críticos**: 141 passed (136 originales + 5 nuevos contract tests audit)

---

## 1. Objetivo

Exponer un endpoint HTTP que permita auditar cualquier simulación
ejecutada con `with_lineage=True`. La auditoría incluye:

- Resumen del grafo de lineage (nodos por etapa, raíces).
- Lista de fórmulas únicas usadas por los calculadores.
- Parámetros consumidos por la simulación, segmentados por `source_type`
  (`request`, `parametrization`, `excel`).
- Cadena de trazabilidad (`explain`) para un valor concreto.
- Comparación opcional contra un baseline certificado.

Todo bajo el contrato `api-v1` ya congelado en WAVE 8.

---

## 2. Diseño

### 2.1 Componentes nuevos

```
backend_nexa/
├── api/v1/audit/
│   ├── __init__.py
│   └── audit_router.py             ← FastAPI router (4 endpoints)
├── application/use_cases/
│   └── audit_simulation.py         ← AuditSimulationUseCase + AuditResult
├── contracts/api_v1/response/
│   └── audit.py                    ← AuditResponseV1, AuditValueExplanationV1, ...
├── contracts/api_v1/schema/
│   ├── audit_response.schema.json
│   ├── audit_value_explanation.schema.json
│   └── audit_simulation_summary.schema.json
├── tests/api/
│   ├── conftest.py
│   └── test_audit_endpoint.py      ← 16 tests
└── tests/contracts/
    └── test_audit_contract.py      ← 5 tests
```

### 2.2 Endpoints

| Verbo | Path                                                         | Descripción                                        |
|-------|--------------------------------------------------------------|----------------------------------------------------|
| GET   | `/api/v1/audit/simulations`                                  | Lista simulaciones con lineage persistido          |
| GET   | `/api/v1/audit/simulation/{simulation_id}`                   | Audit envelope completo                            |
| GET   | `/api/v1/audit/simulation/{simulation_id}/explain`           | Cadena de trazabilidad para un `value_name`        |
| GET   | `/api/v1/audit/simulation/{simulation_id}/baseline-diff`     | Diff KPIs vs baseline certificado                  |

Lineage **no** se genera por defecto. Para usar audit, el `/calculate`
inicial debe invocarse con `with_lineage=True`, o el engine debe
ejecutarse programáticamente con ese flag.

### 2.3 Capas

```
HTTP request
   │
   ▼
api/v1/audit/audit_router.py          (FastAPI, traduce DTO ↔ use case)
   │
   ▼
application/use_cases/audit_simulation.py  (AuditSimulationUseCase)
   │
   ├──► application/lineage/query.py    (LineageQuery — desde WAVE 10)
   │
   └──► infrastructure/lineage/snapshot_repository.py  (carga JSON)
```

El use case es **independiente** de FastAPI y se prueba directamente en 9
de los 16 tests. La capa HTTP solo traduce a/desde `AuditResponseV1`.

---

## 3. Contratos (DTOs)

`contracts/api_v1/response/audit.py`:

- `AuditResponseV1` — envelope principal (frozen, `extra=forbid`).
- `AuditValueExplanationV1` — explain endpoint response.
- `AuditSimulationSummaryV1` — list endpoint response.
- `AuditFormulaV1`, `AuditParametersUsedV1`, `AuditLineageSummaryV1`,
  `AuditBaselineComparisonV1`, `LineageRefV1` — building blocks.

Todos usan `model_config = ConfigDict(extra="forbid", frozen=True)` y
están registrados en `scripts/contracts/generate_schemas.py`. Los
JSONSchema commiteados están bajo `contracts/api_v1/schema/` y son
verificados en `tests/contracts/test_audit_contract.py`.

---

## 4. Sample de respuesta — `GET /audit/simulation/Bancamia`

Ejecutado contra el grafo persistido de Bancamia:

```json
{
  "simulation_id": "Bancamia",
  "api_version": "api-v1",
  "engine_version": "engine-v2",
  "formula_set": "formula-set-v2-7",
  "parametrization_hashes": {},
  "lineage": {
    "nodes_count": 29,
    "roots": [
      "52ee7477bbea4b6cb1f73928f67ec206",
      "e00760c36e484ee3a0609b133a1bfb70",
      "be3e4d6b0607479fab7c77fe39b0ff98"
    ],
    "stages_summary": {
      "REQUEST_BUILD": 13,
      "VISION_BUILD": 14,
      "PYG_BUILD": 2
    }
  },
  "formulas": [
    {
      "calculator": "PyGCalculator.calcular_mes",
      "formula": "contribucion = ingreso_neto - costo_total",
      "stage": "PYG_BUILD",
      "used_count": 2
    },
    {
      "calculator": "ContextBuilder",
      "formula": "Panel knob margen (deal=Bancamia)",
      "stage": "REQUEST_BUILD",
      "used_count": 1
    }
  ],
  "parameters_used": {
    "request": {
      "request.panel.margen": 0.18,
      "request.panel.op_cont": 0.025,
      "request.panel.com_cont": 0.0,
      "request.panel.markup": 0.0,
      "request.panel.descuento": 0.0
    },
    "parametrization": {},
    "excel_refs": [
      {"source_id": "Excel:Panel-Deal!C9", "sheet": "Panel-Deal", "cell": "C9", "value": 0.18},
      {"source_id": "Excel:Panel-Deal!C12", "sheet": "Panel-Deal", "cell": "C12", "value": 0.025}
    ]
  },
  "baseline_comparison": null,
  "generated_at": "2026-05-28T..."
}
```

> F9: `engine_version`, `formula_set`, `parametrization_hashes` son
> placeholders literales hasta WAVE 14 (ver `W10_CERTIFIED_MODE.md`).

---

## 5. Sample — `GET /audit/simulation/Bancamia/explain?value_name=request.panel.margen`

```json
{
  "simulation_id": "Bancamia",
  "value_name": "request.panel.margen",
  "value": 0.18,
  "calculator": "ContextBuilder",
  "formula": "Panel knob margen (deal=Bancamia)",
  "stage": "REQUEST_BUILD",
  "explanation": "request.panel.margen = 0.18\n  formula: Panel knob margen (deal=Bancamia)\n  <- ContextBuilder  [REQUEST_BUILD]\n    <- request.panel.margen = 0.18  (request)\n    <- Excel:Panel-Deal!C9 = 0.18  (Excel:Panel-Deal!C9)",
  "refs_chain": [
    {"source_type": "request", "source_id": "request.panel.margen", "value": 0.18, "sheet": null, "cell": null, "formula": null},
    {"source_type": "excel", "source_id": "Excel:Panel-Deal!C9", "value": 0.18, "sheet": "Panel-Deal", "cell": "C9", "formula": null}
  ]
}
```

---

## 6. Tests

| Suite                                            | Tests | Estado |
|--------------------------------------------------|-------|--------|
| `tests/api/test_audit_endpoint.py`               | 16    | passed |
| `tests/contracts/test_audit_contract.py`         | 5     | passed |
| `tests/lineage/` (W10)                           | 32    | passed |
| `tests/contracts/` (api-v1)                      | 54    | passed |
| `tests/parity/` + `tests/baselines/` (críticos)  | 55    | passed |
| **Full suite**                                   | 861   | passed |

Críticos invariantes: 136 → 141 (mantiene paridad + agrega 5 audit
contract tests).

---

## 7. OpenAPI

Re-generado con `scripts/contracts/generate_openapi.py`. Paths nuevos
visibles en `contracts/openapi/api-v1.json`:

- `/api/v1/audit/simulations`
- `/api/v1/audit/simulation/{simulation_id}`
- `/api/v1/audit/simulation/{simulation_id}/explain`
- `/api/v1/audit/simulation/{simulation_id}/baseline-diff`

---

## 8. Restricciones cumplidas

- [x] 136 críticos verdes (141 ahora).
- [x] Suite default ≥840 passed / 0 failed (861 actual).
- [x] ≥10 tests api/audit passing (16).
- [x] Lineage NO se genera por defecto.
- [x] Pydantic strict (`extra="forbid"`, `frozen=True`) en todos los DTOs.
- [x] Endpoints siguen patrón api-v1.
- [x] F9 placeholders documentados.
- [x] No modifica signatures de `engine.calcular()`, calculadores ni use
  cases existentes.

---

## 9. Bloqueos para WAVE 14/15

- **W14 (Versionado formal)**: necesita inyectar SemVer y manifest
  hashes en `JsonLineageEmitter.__init__` y en
  `LineageGraph.parametrization_hashes`. La forma del audit response ya
  los acepta — solo se rellenan los placeholders.
- **W15 (Certified Mode)**: necesita un endpoint adicional
  `POST /api/v1/simulation/calculate?mode=certified` que internamente
  invoca `with_lineage=True` y valida hashes contra el manifest de
  `storage/baselines/v2-7-certified/`. El comparator del
  `baseline-diff` actual es un placeholder simple (compara solo KPIs);
  WAVE 15 lo extenderá a outputs completos.

---

## 10. DEFERRED

- **Persistencia del simulation_id ↔ user-facing-uuid**: hoy el lineage se
  guarda bajo el `panel.cliente` (e.g. `Bancamia`). El `simulation_id`
  generado por `/calculate` es un UUID separado. Para producción se
  requiere un mapping. WAVE 14 lo atacará junto con el versionado.
- **Comparator completo de baseline-diff**: hoy compara KPIs numéricos
  con tolerancia 1e-2. Para Certified Mode (W15) se debe extender a
  visions y outputs estructurados.
- **Audit-mode permissions**: el endpoint actual es público dentro de
  `/api/v1/`. Si se requiere RBAC, se aplica en una capa de middleware
  separada — fuera del alcance de WAVE 13.
