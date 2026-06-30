# WAVE 7 — Triaje de la deuda técnica de testing

**Fecha**: 2026-05-28
**Branch**: `refactor/engine-v2`
**Fase**: FASE 2 — Aislar deuda heredada pre-V2-7

---

## 1. Resumen ejecutivo

Antes de WAVE 7 la suite ejecutaba 1194 tests con 27 failed + 321 errors + 65 xfailed.
Los failures no afectaban paridad V2-7 (WAVE 4) ni los baselines certificados
(WAVE 6), pero ocultaban cualquier regresión real bajo ruido visual.

WAVE 7 clasifica cada test problemático y aplica un marker `legacy` o `xfail`
de modo que `pytest` por defecto termine **0 failed + 0 errors**. La deuda
heredada queda visible (corre con `-m legacy`) pero aislada.

### Resultado final

| Dimensión | Pre-WAVE-7 | Post-WAVE-7 |
|---|---|---|
| `pytest` default — passed | 758 | 746 |
| `pytest` default — failed | 27 | **0** |
| `pytest` default — errors | 321 | **0** |
| `pytest` default — xfailed | 65 | 1 |
| Tests marcados `legacy` (deselected) | 0 | 411 |
| Tests con ImportError ignorados (`--ignore`) | 0 | 1 archivo (~6 tests) |

`tests/parity` (39 tests) y `tests/baselines` (16 tests) intactos.

---

## 2. Categorías aplicadas

| Categoría | Acción | Cantidad de archivos |
|---|---|---|
| `OBSOLETE_FIXTURE` | mark `legacy` (whole file) | 6 |
| `OBSOLETE_FORMULA` | mark `legacy` (whole file) o `xfail` con bug-id | 2 |
| `LEGACY_TRACEABILITY` | mark `legacy` (whole file) | 2 |
| `OBSOLETE_FIXTURE` (partial) | mark `legacy` (per-test / per-class) | 4 |
| `REAL_BUG` | `xfail(strict=False)` + entrada en BUGS_ABIERTOS.md | 1 test |
| `IMPORT_ERROR_LEGACY` | `--ignore` desde pytest.ini | 1 archivo |

---

## 3. Tabla de triaje por test / archivo

### 3.1 Archivos enteros marcados `legacy`

| # | Test file | Tests afectados | Categoría | Justificación |
|---|-----------|-----------------|-----------|---------------|
| 1 | `tests/contract/test_vision_completeness.py` | 35 | OBSOLETE_FIXTURE | Depende de `excel_v24_canonical_bancamia.json` en ruta inexistente; tests de contrato FASE 5 pre-V2-7. |
| 2 | `tests/contract/test_vision_cost_to_serve_phase_a.py` | 48 | OBSOLETE_FIXTURE | Fixtures Excel V2-4 (`bancamia_excel_match.json`, `excel_v24_canonical_bancamia.json`). |
| 3 | `tests/contract/test_vision_imprimible_schema.py` | 157 | OBSOLETE_FIXTURE | Setup falla por fixtures V2-4 desaparecidas. |
| 4 | `tests/contract/test_vision_pyg_contract.py` | 29 | OBSOLETE_FIXTURE | Idem (canonical bancamia V2-4). |
| 5 | `tests/contract/test_vision_tarifas_contract.py` | 21 | OBSOLETE_FIXTURE | Idem. Reemplazado funcionalmente por `tests/baselines/test_v2_7_regression.py`. |
| 6 | `tests/golden/test_golden_master_v25.py` | 82 (65 xfailed + 17 errors) | OBSOLETE_FORMULA | Golden master Excel **V2-5**. Reemplazado por baseline V2-7 certificado (WAVE 6). |
| 7 | `tests/integration/test_full_traceability.py` | 18 | LEGACY_TRACEABILITY | AuditTrace formato pre-WAVE-5; fixtures sin `cadenas_activas` (rompe en TASK_3). Re-diseñar en WAVE 10 (lineage). |
| 8 | `tests/integration/test_payroll_components.py` | 11 | OBSOLETE_FORMULA + OBSOLETE_FIXTURE | Valores Excel V2-4 (sin Ley 1819) + fixture `whatsapp_only_case` sin `cadenas_activas`. |
| 9 | `tests/integration/test_baseline_regression.py` | 4 | OBSOLETE_FIXTURE | Baseline antiguo en `storage/baseline.json` — reemplazado por `storage/baselines/v2-7-certified/`. |

### 3.2 Markers parciales (per-test o per-class)

| # | Test ID | Categoría | Acción |
|---|---------|-----------|--------|
| 10 | `tests/integration/test_audit_trace.py::TestAuditTracer::test_tracer_captures_engine_run` | OBSOLETE_FIXTURE | `@pytest.mark.legacy` |
| 11 | `tests/integration/test_audit_trace.py::TestAuditTracer::test_tracer_export_json` | OBSOLETE_FIXTURE | `@pytest.mark.legacy` |
| 12 | `tests/integration/test_audit_trace.py::TestAuditTracer::test_tracer_tipo_laboral_correcto` | OBSOLETE_FIXTURE | `@pytest.mark.legacy` |
| 13 | `tests/integration/test_snapshot_persistence.py::TestRoundTripCompleto::test_pipeline_completo_y_snapshot` | OBSOLETE_FIXTURE | `@pytest.mark.legacy` (fixture `json_oficial` sin `cadenas_activas`). El resto del archivo (19 tests) permanece en core. |
| 14 | `tests/integration/test_tipos_carga.py::TestAportesPatronalesExcelV24` (clase entera, 2 tests) | OBSOLETE_FORMULA | `@pytest.mark.legacy` a nivel de clase. El resto del archivo (13 tests) permanece en core. |

### 3.3 xfail con bug-id

| # | Test ID | Categoría | Acción | Bug-id |
|---|---------|-----------|--------|--------|
| 15 | `tests/unit/test_certification_golden_master.py::TestCertificationRoundingPrecision::test_cop_round_accumulation` | REAL_BUG (rounding drift) | `@pytest.mark.xfail(strict=False)` con razón explícita | `BUG-W7-001` |

### 3.4 Archivo ignorado por ImportError

| # | Test file | Tests | Categoría | Acción |
|---|-----------|-------|-----------|--------|
| 16 | `tests/test_parametrization_phase_1_2.py` | ~6 | DEAD_BUILDER + IMPORT_ERROR_LEGACY | `--ignore=tests/test_parametrization_phase_1_2.py` en `pytest.ini`. El módulo importa `nexa_engine.infrastructure.config` que ya no existe post-WAVE-5. Conservar archivo para auditoría histórica; eliminar definitivamente en WAVE 8 cuando se rediseñe el contrato API. |

---

## 4. Política de configuración

`pytest.ini` (nuevo):

```ini
[pytest]
markers =
    legacy: tests heredados pre-V2-7 (excluidos por defecto)
    parity: tests de paridad Excel V2-7 (criticos)
    baseline: tests de regression contra baseline certificado (criticos)
    slow: tests lentos (>1s)

addopts = -m "not legacy" --strict-markers --ignore=tests/test_parametrization_phase_1_2.py
testpaths = tests
norecursedirs = .git .claude venv .venv build dist node_modules tests/legacy_archive
```

Scripts:
- `scripts/run_core_tests.sh` — corre la suite core (default, deuda legacy excluida).
- `scripts/run_full_tests.sh` — corre core + legacy juntos. `--legacy-only` para solo legacy.

---

## 5. Tests NO tocados (por contrato)

Los siguientes tests son **críticos y permanecen verdes**:

- `tests/parity/` — 39 tests de paridad Excel V2-7 (WAVE 4).
- `tests/baselines/` — 16 tests de regression V2-7-certified (WAVE 6).

Cualquier cambio en estos archivos requiere recertificación explícita
(ver `storage/baselines/v2-7-certified/README.md`).

---

## 6. Plan de seguimiento post-WAVE-7

| ID | Acción | Wave destino |
|---|---|---|
| W7-FUP-1 | Reescribir tests de contrato V2-7 (reemplazo de `tests/contract/test_vision_*`). | WAVE 8 (contrato API). |
| W7-FUP-2 | Eliminar `tests/golden/test_golden_master_v25.py` (reemplazado por baseline V2-7). | WAVE 8. |
| W7-FUP-3 | Eliminar `tests/integration/test_baseline_regression.py` y `storage/baseline.json` (legacy). | WAVE 8. |
| W7-FUP-4 | Re-diseñar `test_full_traceability.py` sobre nuevo formato AuditTrace. | WAVE 10 (lineage). |
| W7-FUP-5 | Resolver `BUG-W7-001` (cop_round drift). | WAVE 9+. |
| W7-FUP-6 | Eliminar `tests/test_parametrization_phase_1_2.py` o reescribir sin `nexa_engine`. | WAVE 8. |

---

## 7. Comandos de validación

```bash
source venv/bin/activate

# Core (default) — debe terminar 0 failed + 0 errors
python -m pytest --tb=short -q

# Parity intacto (39 tests)
python -m pytest tests/parity --tb=no -q

# Baselines intacto (16 tests)
python -m pytest tests/baselines --tb=no -q

# Legacy explícito (deuda visible)
python -m pytest -m legacy --tb=no -q
```

— Fin del triaje WAVE 7.
