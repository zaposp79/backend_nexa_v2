# Plan macro de industrialización — WAVES 9 a 15

**Fecha**: 2026-05-28
**Branch base**: `refactor/engine-v2` (post-WAVE 8)

Este documento es el roadmap de las 10 fases solicitadas, mapeadas a 7
waves de ingeniería. Su objetivo es llevar al motor NEXA de "paridad
funcional V2-7" a "cloud-native, auditable, certificado y versionado".

---

## Mapa de fases ↔ waves

| Fase usuario | Wave  | Foco                                          | Estado     |
|--------------|-------|-----------------------------------------------|------------|
| FASE 4       | W9    | Clean Architecture (core financiero puro)     | ✓ COMPLETE |
| FASE 5       | W10   | Trazabilidad financiera (lineage)             | NEXT       |
| FASE 6       | W11   | Cloud-native real (Azure Functions ready)     | pending    |
| FASE 7       | W12   | Performance (1 request < 1s)                  | pending    |
| FASE 8       | W13   | Modo auditoría (`/audit/simulation/{id}`)     | pending    |
| FASE 9       | W14   | Versionado formal del motor                   | pending    |
| FASE 10      | W15   | Certified Mode (`mode=certified`)             | pending    |

---

## W9 — Clean Architecture (entregado)

Ver `WAVE9_REPORT.md`. Resumen:
* `domain/` puro: profitability, pricing, payroll, staffing, financial, risk, shared.
* `application/`: ports (IParametrizationProvider, ILogger, ITraceEmitter), use_cases (6), orchestrators, services.
* `infrastructure/`: logging.StructuredLogger, parametrization.json_provider.
* `interfaces/`: stubs http/excel/cli/azure.
* 104 tests críticos intactos; 808 default (+13 nuevos); 0 regresiones.

## W10 — Lineage (FASE 5)

Objetivo: cada `PricingResult` viene acompañado de un grafo de stages
(`tracer.emit(...)`), serializable y consultable.

Pasos:
1. Reemplazar `NullTraceEmitter` por `JsonLineageEmitter` en
   `infrastructure/persistence/`.
2. Adjuntar `lineage` al `PricingResult` (campo nuevo, opcional, no
   rompe contrato V1).
3. Endpoint `/audit/lineage/{simulation_id}`.
4. Tests: cada stage emitido por los use cases ya construye trazas con
   `stage/inputs/outputs/source` — solo hay que enchufar el sink.

## W11 — Cloud-native (FASE 6)

Objetivo: motor desplegable como Azure Function HTTP-triggered.

Pasos:
1. `interfaces/azure/function_app.py` — function-binding HTTP que recibe
   payload y delega a `CalculateSimulationUseCase`.
2. `infrastructure/storage/blob_loader.py` — para leer
   `storage/parametrization/{version}/` desde Blob Storage (env-driven).
3. Cold-start optimizations: provider singleton + pre-load JSON.
4. CI: deploy preview con `func azure functionapp publish`.

## W12 — Performance (FASE 7)

Objetivo: 1 request end-to-end <1s.

Pasos:
1. Profile actual con `cProfile` y `py-spy`.
2. Pre-load + cache de `IParametrizationProvider`.
3. Vectorizar loops mensuales con `numpy` solo donde haya hot-path
   demostrable.
4. Migrar `calculators/nomina.py` y `vision_tarifas.py` a use cases
   (W9-DEF-1, W9-DEF-3) para poder optimizar sin tocar paridad.

## W13 — Modo auditoría (FASE 8)

Objetivo: `GET /audit/simulation/{id}` devuelve la trace completa de
inputs, parametrización (versión), stages y outputs.

Pasos:
1. `infrastructure/persistence/snapshot_repository.py` — guarda
   `(simulation_id, request_payload, parametrization_version, result,
   lineage)`.
2. Endpoint en `api/v1/audit_router.py`.
3. Reglas de retención + RBAC.

## W14 — Versionado formal (FASE 9)

Objetivo: motor expone `engine_version` y todo `PricingResult` lo lleva.

Pasos:
1. Reorganizar `repositories/*` a `infrastructure/repositories/`
   (cierra W9-DEF-5).
2. Saneo de `domain/models/` y `domain/services/` (W9-DEF-7).
3. `engine_version` SemVer derivado de tag git + parametrization
   manifest hash.

## W15 — Certified Mode (FASE 10)

Objetivo: `POST /calculate?mode=certified` corre la simulación contra
una parametrización marcada `frozen: true` y firma el resultado con
hash determinístico.

Pasos:
1. Pin `parametrization_version=v2-7` por defecto en certified mode.
2. Validar manifest.signature.
3. Devolver `result_hash` (SHA-256 sobre el JSON canónico del result).
4. Tests: dos invocaciones idénticas → mismo hash.

---

## Criterios transversales

* **Paridad inmutable**: los 39+16+49=104 tests críticos deben seguir
  verdes en cada wave.
* **APIs públicas estables**: cambios solo aditivos en `api/v1/`.
* **Strangler**: archivos legacy se mantienen como shims hasta que
  toda la lógica viva en `domain/` + `application/`.
* **Observabilidad**: cada wave añade tags de log nuevos solo si
  agregan información, nunca por "ruido".

— Fin del plan macro.
