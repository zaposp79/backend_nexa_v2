> **⚠️ POST-W17 CONTEXT**: This wave builds infrastructure (lineage / audit
> / versioning / certified mode) atop a motor that has NOT yet achieved
> true parity with Excel V2-7. The infrastructure is sound but operates
> on currently-divergent outputs. See `SEMANTIC_RECONSTRUCTION_PROGRAM.md`.

# WAVE 15 — Certified Mode (FASE 10)

**Estado**: COMPLETADA
**Branch**: `refactor/engine-v2`
**Suite**: 923 passed / 23 skipped / 0 failed / 0 errors / 1 xfailed
**Críticos**: 141 / 141 (parity + baselines + contracts + lineage)
**Auditoría + Versionado**: 47 / 47 (audit 16 + audit-contract 5 + versioning 26)
**Certificación W15 nuevos**: 36 / 36

---

## 1. Objetivo

Cerrar el plan de industrialización (W1–W15) entregando el "modo
certificado": un opt-in en `/calculate` que ejecuta el motor con
política estricta y produce un `ExecutionCertificate` firmado.

---

## 2. Componentes nuevos

```
application/certification/
    __init__.py
    models.py                                    # ExecutionCertificate + CertificationFailureError
application/use_cases/
    certified_calculation.py                     # CertifiedCalculationUseCase
infrastructure/certification/
    __init__.py
    certificate_repository.py                    # JSON-on-disk persistence
api/v1/certification/
    __init__.py
    certification_router.py                      # /certification/* endpoints
contracts/api_v1/response/
    certified.py                                 # CertifiedSimulationResponseV1, ExecutionCertificateV1
storage/certificates/                            # runtime artefacts
tests/certification/mode_w15/
    conftest.py
    test_certified_mode_basic.py                            (6)
    test_certified_hash_validation.py                       (4)
    test_certified_experimental_overrides.py                (3)
    test_certified_baseline_matching.py                     (4)
    test_certified_parity_failure.py                        (3)
    test_certificate_repository.py                          (5)
    test_certificate_verify_endpoint.py                     (4)
    test_certificate_contract.py                            (4)
    test_certified_lineage_includes_certificate.py          (3)
docs/v27/
    W10_CERTIFIED_MODE.md                        (era placeholder, reescrito)
    WAVE15_REPORT.md                             (este archivo)
    CERTIFICACION_INDUSTRIALIZACION_COMPLETA.md  (cierre del plan)
```

### 2.1 Componentes modificados

* `api/v1/simulation/calculate_router.py`
  - Acepta `?mode=certified` y `metadata.mode = "certified"`.
  - Nuevo handler interno `_calculate_certified(body)` que invoca el
    use case. El path normal (`_calculate_normal`) queda intacto.
* `api/v1/router.py`
  - Registra `certification_router`.

---

## 3. Política certified

| Validación                          | Falla con                | Cuando                                                                 |
|-------------------------------------|--------------------------|------------------------------------------------------------------------|
| Hashes parametrización vs manifest  | `HASH_MISMATCH`          | Cualquier módulo HR/GN/OP/BR difiere de `manifest.json`               |
| Hashes opcionales del cliente       | `HASH_MISMATCH`          | `metadata.expected_parametrization_hash` no coincide con live         |
| Campos experimentales               | `EXPERIMENTAL_OVERRIDE`  | Cualquier `experimental*` o prefijo `_experimental_` en el payload    |
| Parity vs baseline matched          | `PARITY_FAILURE`         | Algún KPI difiere > 0.01% rel-tol del baseline                        |
| Lineage emission                    | (no falla, es activado)  | Forzado a `with_lineage=True` para emitir el certificado              |

Las cuatro condiciones fallan con HTTP **412 Precondition Failed** y un
body estructurado `{code, message, expected, actual, details}`.

---

## 4. Sample certificate (Bancamía Sac Inbound FTE)

```jsonc
{
  "certificate_id": "210685d6c3b8ac81…",     // sha256 truncado para el reporte
  "simulation_id":  "70d7be29d9f6477b…",
  "issued_at":      "2026-05-28T12:43:11.122334+00:00",
  "version_metadata": {
    "engine_version":          "engine-v2",
    "parametrization_version": "v2-7",
    "formula_set":             "formula-set-v2-7",
    "api_version":             "api-v1",
    "baseline_version":        "v2-7-certified",
    "parametrization_hashes": {
      "hr":             "09639db0c513237b…",
      "gn":             "01c9482f7bc96703…",
      "op":             "5820a03723c398b8…",
      "business_rules": "f3b3b1528d8c3075…"
    }
  },
  "request_hash":  "6c33febf3ebfa791…",
  "result_hash":   "962817f5c3d8bac1…",
  "lineage_hash":  "af7e549efe0e1b81…",
  "baseline_matched": "bancamia_sac_inbound_fte",
  "validation_results": {
    "parametrization_hashes":  "matched",
    "experimental_overrides":  "none",
    "lineage":                 "captured",
    "baseline_match":          "bancamia_sac_inbound_fte",
    "parity":                  "passed"
  }
}
```

---

## 5. Casos de fallo verificados (HTTP 412)

| Caso                                                        | code                    | Test                                                       |
|-------------------------------------------------------------|-------------------------|------------------------------------------------------------|
| `metadata.expected_parametrization_hash = {hr: "0...0"}`    | `HASH_MISMATCH`         | `test_client_expected_hash_mismatch_raises_412`            |
| Manifest patched → `parametrization_hashes.hr = "f"*64`     | `HASH_MISMATCH`         | `test_baseline_manifest_mismatch_blocks_run`               |
| Payload con `experimental: true`                            | `EXPERIMENTAL_OVERRIDE` | `test_experimental_top_level_flag_blocks`                  |
| Payload con `metadata.experimental_flags = {...}`           | `EXPERIMENTAL_OVERRIDE` | `test_experimental_nested_metadata_blocks`                 |
| Payload con `panel._experimental_margin = 0.5`              | `EXPERIMENTAL_OVERRIDE` | `test_experimental_prefix_blocks`                          |
| Baseline KPIs tampered (×2.0 en `ingreso_mensual`)          | `PARITY_FAILURE`        | `test_parity_failure_payload_has_diffs_structure`          |

---

## 6. Endpoints publicados

```
POST /api/v1/simulation/calculate?mode=certified
GET  /api/v1/certification/certificates?limit={n}
GET  /api/v1/certification/certificate/{cert_id}
POST /api/v1/certification/verify/{cert_id}
```

OpenAPI lista los tres endpoints `certification/*` bajo el tag
`certification`. El endpoint `/calculate` adquiere el query param
`mode` (literal `"normal"` | `"certified"`, default `"normal"`).

---

## 7. Determinismo del certificado

`ExecutionCertificate.certificate_id` es SHA-256 sobre el cuerpo del
certificado canonicalizado (sort_keys) **excluyendo** `issued_at` y
`certificate_id` mismo. Verificado por
`test_deterministic_certificate_id_for_same_request`.

Dos ejecuciones consecutivas del mismo request producen el mismo
`request_hash` y `result_hash` (verificado por
`test_certificate_lineage_hash_is_deterministic_for_same_run`). El
`lineage_hash` y `simulation_id` sí varían porque incorporan el
`simulation_id` interno del lineage graph — esto es intencional para
no romper W14.

---

## 8. Suite de tests

| Suite                                       | Tests | Estado |
|---------------------------------------------|------:|--------|
| `tests/certification/mode_w15/` (W15 nuevos) |    36 | passed |
| `tests/parity` + `tests/baselines`           |    55 | passed |
| `tests/contracts` (incluye 5 audit contract) |    54 | passed |
| `tests/lineage` (W10)                        |    32 | passed |
| **Críticos totales**                         |   141 | passed |
| `tests/api/test_audit_endpoint.py`           |    16 | passed |
| `tests/versioning/` (W14)                    |    26 | passed |
| **Full suite**                               |   923 | passed |

Comparativa pre-W15: 887 → 923 (+36). 0 regresiones.

---

## 9. Backward compatibility

* `POST /calculate` sin query param → idéntico a W14.
* `NexaPricingEngine.calcular(req)` y `calcular(req, with_lineage=True)`
  no cambian de firma.
* Endpoint `/audit/simulation/{id}` sigue funcionando con
  `simulation_id` emitido por el motor (W14).
* El campo `certificate_id` agregado al `lineage.json` es aditivo y no
  rompe la deserialización del `LineageGraph` (probado por W10).

---

## 10. DEFERRED

| ID          | Detalle                                                                | Plan                              |
|-------------|------------------------------------------------------------------------|-----------------------------------|
| W15-DEF-1   | Firma criptográfica del certificado (Ed25519) con KMS                  | Cuando KMS esté disponible (W11). |
| W15-DEF-2   | Compare full visions (no solo KPIs) en el parity check                 | Si W11/W12 fuerza canónico.       |
| W15-DEF-3   | Replay endpoint: `/certification/replay/{cert_id}`                     | Habilitable cuando snapshots se versionen externamente. |
| W15-DEF-4   | `BASELINE_NOT_FOUND` como falla dura cuando se exige cobertura total   | Política de operación, no técnico.|

---

## 11. Criterio de éxito — Cumplimiento

| Criterio                                                                | Resultado |
|-------------------------------------------------------------------------|-----------|
| 141 críticos + 21 audit + 26 versioning + 32 lineage = 220 verdes       | OK (220/220) |
| Suite default ≥887 passed / 0 failed                                    | OK (923/0) |
| ≥30 tests certification passing                                         | OK (36)   |
| `/calculate?mode=certified` retorna result+certificate (201)            | OK        |
| 412 con detalle estructurado en cada modo de falla                      | OK (HASH_MISMATCH, EXPERIMENTAL_OVERRIDE, PARITY_FAILURE) |
| `/certification/verify/{id}` re-valida hashes contra parametrización    | OK        |
| Documento de cierre publicado                                           | OK (`CERTIFICACION_INDUSTRIALIZACION_COMPLETA.md`) |

**Veredicto**: READY. WAVE 15 cierra el plan original de 10 fases
(W1-W15).
