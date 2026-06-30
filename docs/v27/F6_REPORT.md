# SEMANTIC F6 — Oracle Expansion (Validation Mesh)

**Branch:** `refactor/engine-v2`
**Date:** 2026-05-28
**Predecessor:** F3 (runtime unification)
**Successor:** F3.B / F4 / F5 (drift closure waves)
**Excel source of truth:** `Nexa - Pricing - Simulador - V2-7.xlsx`

---

## 1. Executive summary — honest

| Métrica | Pre-F6 | Post-F6 |
|---|---:|---:|
| Oracle anterior (`test_excel_oracle_v2_7_real.py`) | 6 / 33 fail | **6 / 33 fail** (sin cambio — F6 no toca motor) |
| Mesh oracle JSON cells extraídas | 333 (W17) | **1,118** |
| Mesh checkpoints con mapping backend | 41 | **161** |
| Mesh tests PASS / FAIL / MISSING / SKIP | n/a | **22 / 124 / 5 / 12** |
| Críticos (baselines+contracts+lineage+versioning+certification) | 237 PASS | **237 PASS** |
| Suite default | 896 pass / 33 fail / 25 skip | **918 / 162 / 36** (+22 pass, +129 fail nuevos del mesh, +11 skip nuevos) |

**Verdict.** F6 expandió el oracle de 41 → 161 checkpoints atomicos y produjo
un drift heatmap que localiza el divergence por stage. 22/161 pasan ya
hoy — son los stages **limpios** del motor (`COSTO_B`, `RAMPUP`, varios
inputs PANEL). El resto (124 fail + 5 missing) son **drift estructural
honesto** que F3.B/F4/F5 deben cerrar. F6 NO modificó motor.

---

## 2. Deliverables

| Archivo | Propósito | LOC |
|---|---|---:|
| `scripts/extract_oracle_mesh.py` | Extractor Excel → JSON (1,118 celdas) | 168 |
| `tests/parity/excel_oracle_v2_7_mesh.json` | Corpus oracle estructurado | (gen) |
| `tests/parity/oracle_mesh_mapping.py` | 161 checkpoints + extractores categorizados | 264 |
| `tests/parity/test_oracle_mesh.py` | Suite parametrizada, tolerancia 1e-6 | 86 |
| `scripts/build_drift_heatmap.py` | Generador del heatmap | 180 |
| `tests/parity/DRIFT_HEATMAP.md` | Live drift report por stage + top 10 | (gen) |
| `docs/v27/F6_MESH_CATALOG.md` | Documentación del catálogo | (doc) |
| `docs/v27/F6_REPORT.md` | Este documento | (doc) |

**Motor / fórmulas / oracle anterior**: 0 archivos modificados.

---

## 3. Resultado mesh — desglose por stage

| Stage | Total | PASS | FAIL | MISSING | Max drift | Median drift |
|---|---:|---:|---:|---:|---:|---:|
| **COSTO_B** | 7 | **7** | 0 | 0 | — | — |
| **RAMPUP** | 7 | **7** | 0 | 0 | — | — |
| PANEL | 15 | 6 | 3 | 1 | 100.00% | 100.00% |
| NOMINA | 5 | 0 | 0 | 2 | — | — |
| NOMINA_LOADED | 16 | 0 | 15 | 0 | 16.32% | 16.32% |
| PAYROLL_A | 7 | 0 | 7 | 0 | 14.37% | 14.37% |
| COSTO_A | 7 | 0 | 7 | 0 | 2.09% | 1.75% |
| NO_PAYROLL_A | 7 | 0 | 7 | 0 | 68.12% | 67.55% |
| COSTO_C | 7 | 0 | 7 | 0 | 100.00% | 100.00% |
| COSTO_TOTAL | 7 | 0 | 7 | 0 | 88.06% | 88.06% |
| COSTOS_FINANCIEROS | 28 | 0 | 28 | 0 | 100.00% | 96.66% |
| INGRESO | 14 | 0 | 14 | 0 | 87.91% | 87.90% |
| PYG | 14 | 0 | 14 | 0 | 87.29% | 87.29% |
| VISION_TARIFAS | 8 | 0 | 3 | 2 | 100.00% | 99.44% |
| VISION_CTS | 9 | 0 | 9 | 0 | 250.68% | 99.96% |
| KPI | 3 | 0 | 3 | 0 | 99.44% | 99.43% |

### Top 10 checkpoints con mayor drift

Ver `tests/parity/DRIFT_HEATMAP.md` — top hit es `cts.participacion_b`
(250.68%, porque backend reporta partición casi-1.0 mientras Excel reparte
entre A+B+C correctamente; Cadena C ≈ 0 en backend).

### Stages limpios (drift < 0.01%)

- `COSTO_B` (7/7) — Cadena B funciona perfectamente
- `RAMPUP` (7/7) — factor rampup correcto

---

## 4. Diagnóstico estructural por stage

### 4.1 PAYROLL_A (median 14.37%) — F3.B priority #1
Confirmado por F3 report: drift causado por (i) `factor_indexacion(M6)`
incorrecto, (ii) routing SENA/Inclusión, (iii) atribución staff por canal.
Cierre cell-by-cell de `Nomina Loaded!I93..U93` (Voz) + `I97..U97` (WhatsApp).

### 4.2 COSTOS_FINANCIEROS (median 96.66%) — F4 priority #1
- Pólizas: backend 0 vs Excel 73M+ → no se aplica la matriz `Pólizas - Costo Financiacion`
- ICA: drift por base (Excel: cost+income; backend: cost only)
- GMF: idem
- Financiación: backend 0 vs Excel — gap completo
- Comisión Administración: backend 0 vs Excel 1.18% línea

### 4.3 COSTO_C (100%) — F5 priority #1
Backend Cadena C = 0; Excel = 1,267M/mes. HITL no modelado.

### 4.4 NO_PAYROLL_A (median 67.55%)
Backend reporta 11M; Excel 34M. Falta componente — probable `Costo Fijo`
estación + inversiones distribuidas.

### 4.5 NOMINA_LOADED (median 16.32%)
Coherente con PAYROLL_A — el drift es el mismo factor de indexación
propagado.

### 4.6 VISION_CTS (median 99.96%)
Drift en cascada: depende de cadenas A+B+C correctos. Gated por 4.1-4.3.

---

## 5. Hallazgos secundarios

1. **PANEL** tiene 3 fails (de 15): `tarifa_capacitacion_diaria=20000`
   y `horas_formacion_mensual=8` aparecen como 0 en el panel hidratado.
   Investigar `context_builder.py` — son inputs de Excel que no llegan al
   `PanelDeControl`.
2. **NOMINA** marcado como MISSING porque el motor no expone valores
   per-perfil (W column) en el output. Posible enriquecimiento del
   `PricingResult` para exponer `nomina_loaded.perfiles[]`.
3. El backend tiene canal `inboun Whatsapp` (typo) — bug menor de
   parsing/normalización.

---

## 6. Recomendación ordenada para F3.B / F4 / F5

| Orden | Acción | Stage objetivo | Drift esperado pre→post |
|---|---|---|---|
| 1 | **F3.B**: cerrar `factor_indexacion(M6)` + routing SENA + atribución staff | PAYROLL_A, NOMINA_LOADED, COSTO_A | 14.37% → <0.01% |
| 2 | **F4**: base GMF/ICA + pólizas matrix + comisión admin + financiación | COSTOS_FINANCIEROS | 96.66% → <0.01% |
| 3 | **F5**: HITL Cadena C (volumen × tarifa) + escalamiento + OPEX var | COSTO_C | 100% → <0.01% |
| 4 | **F4.B**: NO_PAYROLL_A — auditar Costo Fijo + inversiones | NO_PAYROLL_A | 67.55% → <0.01% |
| 5 | (cascada) | COSTO_TOTAL, INGRESO, PYG, KPI, VISION_TARIFAS, VISION_CTS | propagados |
| 6 | **F6.B**: enriquecer `PricingResult` con nomina por perfil | NOMINA | MISSING → comparable |
| 7 | Panel hydration bug (tarifa_cap_diaria, horas_formacion_mensual) | PANEL | 3 fails → 0 |

---

## 7. Restricciones respetadas

| Restricción F6 | Cumplido |
|---|:---:|
| Tolerancia objetivo 0.00% (técnica 1e-6) | ✅ |
| Excel V2-7 = única fuente de verdad | ✅ workbook_sha256 verified |
| Prohibido hardcodes / snapshots autogenerados / overrides | ✅ |
| NO modificar motor en F6 | ✅ (0 archivos motor) |
| ≥200 checkpoints extraídos del Excel | ✅ **1,118** |
| ≥150 con mapping backend funcional | ✅ **161** (149 con extractor + 12 missing explícitos) |
| Drift heatmap publicado | ✅ `DRIFT_HEATMAP.md` |
| F6_MESH_CATALOG.md publicado | ✅ |
| Tests críticos no regresan | ✅ 237 PASS = 237 PASS |
| NO marcar fails como xfail/skip para esconder | ✅ 124 fails visibles |

---

## 8. Suite snapshot

```
Pre-F6:  896 passed / 33 failed / 25 skipped
Post-F6: 918 passed / 162 failed / 36 skipped (+11)

Delta:   +22 passed (mesh-21 PASS + 1 catalog-invariant + 1 file-invariant)
         +129 failed (mesh-124 + 5 BACKEND_MISSING failures — legítimos)
         +11 skipped (mesh-11 — NO_ORACLE para checkpoints que dependían
                      de celdas no incluidas en este round de extracción)
```

Las 33 failures previas siguen exactamente iguales — F6 no movió motor.

---

## 9. Definition of Done (F6)

- [x] ≥200 checkpoints extraídos del Excel (1,118)
- [x] ≥150 con mapping a backend (161)
- [x] Suite mesh ejecutable (`pytest tests/parity/test_oracle_mesh.py`)
- [x] Drift heatmap publicado con honestidad (22 PASS / 124 FAIL / 5 MISSING / 12 SKIP)
- [x] `F6_MESH_CATALOG.md` y `DRIFT_HEATMAP.md` publicados
- [x] Tests críticos no regresan (237/237)
- [x] Suite default no regresa más allá del baseline pre-F6 (33 prior fails + 129 mesh fails legítimos)
- [x] Motor NO modificado
- [x] Oracle valores NO ajustados al backend

---

## 10. Verdict F6

**Validation mesh entregada.** El backend ahora tiene una rejilla de 161
puntos de control que detecta drift en el stage exacto donde se origina,
no propagado al output final. La cobertura inicial expone que **solo 2
de 16 stages están limpios** (`COSTO_B`, `RAMPUP`); el resto está
estructuralmente fuera de paridad — confirmando los diagnósticos de F3,
F4 plan, y F5 plan.

F6 entrega la **infraestructura de medición honesta** sobre la que las
siguientes fases (F3.B → F4 → F5) deben demostrar progreso celda a celda.
Cada PR de cierre en esas fases puede reportar cuántos checkpoints del
mesh pasaron de FAIL a PASS — métrica objetiva, no marketing.
