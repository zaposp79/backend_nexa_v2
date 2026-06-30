> **⚠️ POST-W17 CONTEXT**: Claims of certified parity in this report
> were based on circular tests. W17 oracle validation showed the actual
> parity gap is structural. The infrastructure built in this wave is
> still valid, but the parity certification claim is rescinded until
> the Semantic Reconstruction Program completes.

# WAVE 6 — Freeze Baseline V2-7 + Golden Masters

**Fecha**: 2026-05-28
**Branch**: `refactor/engine-v2`
**Fase**: FASE 1 — Prioridad máxima del plan de industrialización
**Estado**: COMPLETADO

---

## 1. Resumen ejecutivo

WAVE 6 cierra la fase de paridad y abre la fase de **industrialización**.
El motor `backend_nexa` ya alcanzó paridad ≤0.01% con Excel V2-7 (39/39 tests
en WAVE 4), pero los outputs eran efímeros: cada cambio futuro podía
introducir drift sin que nadie lo detectara.

Esta wave congela un **baseline certificado e inmutable** del motor
post-WAVE-5 sobre 12 casos canónicos que cubren la matriz representativa
de servicios × modalidades × modelos de cobro × cadenas activas. Sobre ese
baseline se monta una suite de **regression tests** que detecta cualquier
drift — sea por cambio de fórmula, de parametrización, o de adapter.

**Resultado**:
- 12 baselines certificados con SHA-256 en `storage/baselines/v2-7-certified/`.
- 16 regression tests (12 casos + 4 sanity / integridad).
- Parity 39/39 sigue verde — ninguna regresión.
- Suite global: 758 passed (= 742 previo + 16 nuevos), mismos 27 failed y 321 errors.
- Política de hash **ESTRICTA**: cualquier cambio en los hashes de
  `storage/parametrization/v2-7/{hr,gn,op,business_rules}.json` invalida el baseline.

---

## 2. Alcance

### 2.1 Decisiones tomadas (cerradas, no se cuestionan)

| Decisión | Valor |
|---|---|
| Número de casos canónicos | 12 (no 54 completos) |
| Fuente de outputs | Snapshot del motor post-WAVE-5 |
| Hash policy | ESTRICTO (cualquier cambio invalida baseline) |
| Legacy tests | NO se tocan en esta wave — diferidos a WAVE 7 |
| Tolerancia regression | `rel=1e-4 / abs=1e-2` (≤0.01% / 1 cent COP) |

### 2.2 No incluido en WAVE 6 (diferido)

- Reescritura de los 27 failed / 321 errors pre-existentes (WAVE 7).
- Captura de baselines contra Excel directamente (motor ya tiene paridad
  formal en WAVE 4; el baseline V2-7 certificado se ancla al motor).
- Test de canonicalización dedicado (mejora propuesta en CERTIFICACION §4.2).

---

## 3. Los 12 casos canónicos

Cobertura dimensional (ver `storage/baselines/v2-7-certified/INDEX.md`):

| # | case_id | Servicio | Modalidad | Modelo | Cadenas |
|---|---------|----------|-----------|--------|---------|
| 1  | bancamia_sac_inbound_fte    | Sac               | Inbound  | Fijo FTE | A     |
| 2  | sac_outbound_volumen        | Sac               | Outbound | Volumen  | A     |
| 3  | sac_blended_hibrido         | Sac               | Blended  | Híbrido  | A     |
| 4  | cobranzas_outbound_fte      | Cobranzas         | Outbound | Fijo FTE | A     |
| 5  | cobranzas_outbound_volumen  | Cobranzas         | Outbound | Volumen  | A     |
| 6  | ventas_outbound_fte         | Ventas multicanal | Outbound | Fijo FTE | A     |
| 7  | ventas_blended_hibrido      | Ventas multicanal | Blended  | Híbrido  | A     |
| 8  | backoffice_inbound_fte      | Backoffice        | Inbound  | Fijo FTE | A     |
| 9  | es_sac_inbound_fte          | SACO              | Inbound  | Fijo FTE | A     |
| 10 | captura_datos_inbound_fte   | Captura de Datos  | Inbound  | Fijo FTE | A     |
| 11 | plataformas_inbound_fte     | Plataformas       | Inbound  | Fijo FTE | A     |
| 12 | bancamia_full_chains_abc    | Cobranzas         | Blended  | Híbrido  | A,B,C |

Cobertura agregada:
- 7 servicios distintos (5 reales + 2 alias: Backoffice → Captura de Datos).
- 3 modalidades (Inbound, Outbound, Blended).
- 3 modelos de cobro (Fijo FTE, Volumen, Híbrido).
- 2 edge cases ramp-up=0 (Captura de Datos, Plataformas).
- 1 caso con cadenas A+B+C completas (bancamia_full_chains_abc).

---

## 4. Estructura del baseline

```
storage/baselines/v2-7-certified/
├── manifest.json                  Hashes globales + resumen de los 12 casos.
├── README.md                      Procedimientos de validación y re-certificación.
├── INDEX.md                       Tabla de 12 casos con SHA-256 prefix.
└── cases/<case_id>/
    ├── request.json               Entry data exacto que se le pasa al motor.
    ├── metadata.json              case_id, descripcion, dimensiones.
    ├── parametrization_snapshot.json   SHA-256 de v2-7 params al certificar.
    ├── checksums.json             SHA-256 de cada output JSON.
    └── outputs/
        ├── kpis.json
        ├── vision_tarifas.json
        ├── vision_pyg.json
        ├── cost_to_serve.json
        ├── waterfall.json
        ├── payroll_snapshot.json
        ├── staffing_snapshot.json
        └── simulation_full.json   Serialización completa del PricingResult.
```

### 4.1 Determinismo

El generador es **byte-deterministic**:
- Floats redondeados a 6 decimales antes de serializar.
- `json.dumps(..., sort_keys=True)` para ordenamiento canónico.
- NaN / Inf → `null`.
- Sin timestamps dentro de los archivos per-case (sólo en `manifest.json`).

Verificación: dos ejecuciones consecutivas de `generate_baselines.py`
producen archivos `simulation_full.json` byte-idénticos.

### 4.2 Manifest

`manifest.json` top-level keys:

```
- baseline_version          "v2-7-certified"
- generated_at              ISO-8601 UTC timestamp
- engine_version            "engine-v2-post-wave5"
- git_sha                   HEAD commit SHA
- excel_version             "V2-7"
- checksum_algorithm        "sha256"
- tolerance_policy          "exact_match_for_baseline_drift_detection"
- parametrization_hashes    {hr, gn, op, business_rules} -> SHA-256
- cases                     Lista de 12 dicts con sha de cada output
```

Hashes de parametrización al certificar:

| Archivo | SHA-256 (prefix) |
|---|---|
| hr.json             | `09639db0c513237b...` |
| gn.json             | `01c9482f7bc96703...` |
| op.json             | `5820a03723c398b8...` |
| business_rules.json | `f3b3b1528d8c3075...` |

---

## 5. Suite de regression tests

`tests/baselines/test_v2_7_regression.py` — 16 tests:

1. **12 tests parametrizados** (`test_case_matches_baseline[<case_id>]`):
   Para cada caso carga `request.json`, corre el motor live, y compara
   cada output JSON (kpis, vision_tarifas, vision_pyg, cost_to_serve,
   waterfall, payroll_snapshot, staffing_snapshot, simulation_full)
   contra el archivo frozen. Tolerancia `rel=1e-4 / abs=1e-2`.

   Si falla, reporta hasta 30 diferencias con path dentro del JSON
   (`field.subfield[3]: expected=X actual=Y`).

2. **`test_manifest_hashes_match_current_parametrization`**:
   Recomputa los SHA-256 de `storage/parametrization/v2-7/*.json` y los
   compara con los hashes registrados en `manifest.json`. Si difieren,
   reporta cuál archivo cambió y exige re-certificación.

3. **`test_manifest_has_twelve_cases`**:
   Sanidad: el manifest tiene exactamente 12 casos.

4. **`test_each_case_has_full_output_set`**:
   Sanidad: cada `cases/<id>/outputs/` contiene los 8 archivos JSON esperados.

5. **`test_parity_suite_is_present`**:
   Regression de la regression — si alguien borra `tests/parity/`,
   este test rompe explícitamente.

---

## 6. Helpers y scripts

`scripts/baselines/`:

- **`cases_definition.py`** — fuente de verdad de los 12 casos.
- **`generate_baselines.py`** — regenera todos los baselines (idempotente).
- **`validate_baselines.py`** — wrapper que corre `pytest tests/baselines`.
- **`recompute_hashes.py`** — imprime los SHA-256 actuales de v2-7.
- **`__init__.py`** — package marker.

---

## 7. Resultados de validación

### 7.1 Generación

```
$ python scripts/baselines/generate_baselines.py
Generating V2-7 certified baselines into: storage/baselines/v2-7-certified
  [bancamia_sac_inbound_fte] running engine...
  ... (12 cases) ...
Generated 12 cases.
```

### 7.2 Regression suite

```
$ python -m pytest tests/baselines -v
16 passed in 0.24s
```

### 7.3 Parity intacto

```
$ python -m pytest tests/parity --tb=no -q
39 passed, 2 warnings in 1.26s
```

### 7.4 Global

```
$ python -m pytest --tb=no -q
27 failed, 758 passed, 23 skipped, 65 xfailed, 2 warnings, 321 errors
```

Comparado con pre-WAVE-6 (742 passed, 27 failed, 321 errors): los 16 nuevos
tests pasan, **cero regresiones**.

---

## 8. SHA-256 de simulation_full.json por caso

(Prefijo de 16 chars — útil para grep rápido si algún caso drifta.)

| # | case_id | sha256 (prefix) |
|---|---------|-----------------|
| 1  | bancamia_sac_inbound_fte    | `91483688d01eb1ea` |
| 2  | sac_outbound_volumen        | `547404dea8c9471b` |
| 3  | sac_blended_hibrido         | `794722a6707f4d12` |
| 4  | cobranzas_outbound_fte      | `b6a744b70e02f57a` |
| 5  | cobranzas_outbound_volumen  | `bbffbae1090a904d` |
| 6  | ventas_outbound_fte         | `4a6b309f330fc35b` |
| 7  | ventas_blended_hibrido      | `0e7571fa422a66fe` |
| 8  | backoffice_inbound_fte      | `a7025ff8e08f30d4` |
| 9  | es_sac_inbound_fte          | `cfdbf00b78cc7e81` |
| 10 | captura_datos_inbound_fte   | `d88ec3ce1364659c` |
| 11 | plataformas_inbound_fte     | `f05544e94b268566` |
| 12 | bancamia_full_chains_abc    | `e6e3e8b07d22b4ac` |

---

## 9. Política de re-certificación

El baseline V2-7 es inmutable salvo decisión explícita. Re-certificar SOLO en
los siguientes escenarios y siempre con revisión independiente:

1. Cambio intencional de parametrización en `storage/parametrization/v2-7/`.
2. Corrección de bug en calculadora con paper trail documentado.
3. Mejora de fórmula con validación contra Excel V2-7 actualizado.

Pasos (también en `storage/baselines/v2-7-certified/README.md`):

```bash
# 1. Confirmar cambio intencional + reviewed.
# 2. Regenerar baselines.
python scripts/baselines/generate_baselines.py
# 3. Validar suite parity sigue verde.
python -m pytest tests/parity tests/baselines --tb=short -v
# 4. Commit del cambio + baseline regenerado en el mismo commit.
# 5. Notar la re-certificación en docs/v27/CERTIFICACION_PARIDAD_V2_7.md.
```

---

## 10. Bloqueos detectados para WAVE 7

WAVE 6 completa sin bloqueos. Hallazgos relevantes para fases siguientes:

| ID | Hallazgo | Acción WAVE 7+ |
|---|---|---|
| W6-OBS-1 | 321 errors en `tests/integration/test_full_traceability.py` y otros legacy. Son pre-WAVE-1 y no afectan paridad V2-7. | WAVE 7 los aísla bajo marca `legacy` o `@pytest.mark.xfail`. |
| W6-OBS-2 | 27 failed pre-existentes — auditorías históricas. | WAVE 7 — clasificar y aislar. |
| W6-OBS-3 | `payroll_snapshot` y `staffing_snapshot` son sintetizados por el generador (no son tipos nativos del motor). | WAVE 9 (clean architecture) puede promoverlos a vistas del dominio. |
| W6-OBS-4 | Excel V2-7 no entra al loop de WAVE 6 — el baseline se ancla al motor. Si el negocio publica un V2-8 hay que añadir una capa de re-paridad antes de re-certificar. | WAVE 8 (contrato API) + WAVE 14 (versionado formal). |

Ningún bloqueo crítico. WAVE 7 puede iniciarse de inmediato.

---

## 11. Archivos creados / modificados

### Nuevos
- `storage/baselines/v2-7-certified/manifest.json`
- `storage/baselines/v2-7-certified/README.md`
- `storage/baselines/v2-7-certified/INDEX.md`
- `storage/baselines/v2-7-certified/cases/<12 dirs>/{request,metadata,checksums,parametrization_snapshot}.json`
- `storage/baselines/v2-7-certified/cases/<12 dirs>/outputs/{kpis,vision_tarifas,vision_pyg,cost_to_serve,waterfall,payroll_snapshot,staffing_snapshot,simulation_full}.json`
- `scripts/baselines/__init__.py`
- `scripts/baselines/cases_definition.py`
- `scripts/baselines/generate_baselines.py`
- `scripts/baselines/validate_baselines.py`
- `scripts/baselines/recompute_hashes.py`
- `tests/baselines/__init__.py`
- `tests/baselines/conftest.py`
- `tests/baselines/test_v2_7_regression.py`
- `docs/v27/WAVE6_REPORT.md` (este documento)

### Modificados
- Ninguno. WAVE 6 es **aditiva**: ningún calculador, dominio, test parity ni archivo de parametrización fue modificado.

---

— Fin del reporte de WAVE 6.
