# CURRENT ORACLE STATUS — Excel V2-7 ↔ backend_nexa

> **Last measured:** 2026-05-28 (post-WAVE-19, during SEMANTIC F1)
> **Suite:** `tests/parity/test_excel_oracle_v2_7_real.py`
> **Source of truth:** `tests/parity/excel_oracle_v2_7_full.json`
>   (531 cells extracted, 333 non-zero, 41 mapped to a `backend_path`)

---

## Summary

| Metric | Value |
|---|---:|
| Mapped oracle tests | 41 |
| **PASS @ ≤0.01%** | **6** |
| **FAIL** | **33** |
| Helper tests (file loaded / mapping coverage) | 2 PASS |
| Mutation tests | 2 PASS / 2 SKIP (W17) |

Default suite (full repo): **892 passed / 33 failed / 25 skipped /
450 deselected** (`legacy_circular` marker).

---

## Pass list (6 cells — all input echoes or ramp-up zeros)

| Sheet!Cell | Concept | Excel | Backend | Comment |
|---|---|---:|---:|---|
| Visión P&G!H15 | Ramp-up M6 | 0.0 | 0.0 | Trivial (ramp-up table unparsed) |
| Visión P&G!J15 | Ramp-up M8 | 0.0 | 0.0 | Trivial |
| Visión P&G!H45 | (input echo) | match | match | Panel input echo |
| Visión P&G!J45 | (input echo) | match | match | Panel input echo |
| test_oracle_file_loaded | (meta) | — | — | Sanity test |
| test_oracle_mapping_coverage | (meta) | — | — | Sanity test |

*Note:* W17 noted these passes are "trivially identical" — they validate
input propagation, not formula reproduction. Post-W19 the picture is
unchanged; no genuinely-computed oracle cell yet passes at 0.00% drift.

---

## Fail list (33 cells — divergence is real)

Drift figures below combine W17 (initial measurement) and W19 (post
duplicate-staff fix). The "Cause family" column links each failure to
one of the five structural root causes documented in
`docs/v27/SEMANTIC_RECONSTRUCTION_PROGRAM.md §1.3`.

### Vision Tarifas — Modelo Cobro (4 fails)

| Cell | Concept | Excel | Drift pre-W19 | Drift post-W19 | Cause family |
|---|---|---:|---:|---:|---|
| C40 | Cadena A Costo Total | 1,365,353,738.03 | 73.03% | ~2% (payroll formula residual) | F2 (request) + F3 (formula) |
| C50 | Cadena B Costo Total | (~0) | abs vs 0 | abs vs 0 | F4 (Cadena B model) |
| C60 | Cadena C Costo Total | 29,135,528,955.59 | 100.00% | 100.00% | F5 (Cadena C HITL) |
| C72 | Facturación Total | 38,608,712,270.41 | 98.78% | 98.78% | F2 + F4 (Cadena C + financial) |

### Vision Cost To Serve (9 fails)

| Cell | Concept | Excel | Drift | Cause family |
|---|---|---:|---:|---|
| B19 | Ingreso Mensual Promedio | 38,608,712,270.41 | 98.78% | F2 + F4 |
| H19 | CTS Mensual | 30,500,882,693.62 | 85.40% | F5 (Cadena C) |
| C31 | Participación Cadena A | 0.5366 | ~6–250% | F2 + F5 (denominator) |
| G31 | Participación Cadena B | — | ~6–250% | F4 |
| K31 | Participación Cadena C | — | ~6–250% | F5 |
| C34 | CTS Cadena A unit | 5,732.25 | high | F2 + F4 |
| G34 | CTS Cadena B unit | — | high | F4 |
| K34 | CTS Cadena C unit | — | high | F5 |
| G49 | CTS ponderado | 45,688.66 | high | F2 + F5 |

### Visión P&G monthly (M6 = H, M8 = J — 20 fails)

| Cell pair | Concept | Excel (H/M6) | Drift pre-W19 | Drift post-W19 | Cause family |
|---|---|---:|---:|---:|---|
| H/J 18 | Ingreso Bruto | — | ~74% | ~74% | F2 (ramp-up) + F4 |
| H/J 30 | Costo Total | 1,443,351,358.29 | 74.29% | ~74% | F4 + F5 |
| H/J 31 | Costos Cadena A | 173,162,876.56 | 112.68% | **2.08%** | F2 fixed by W19; residual F3 |
| H/J 32 | Payroll Cadena A | 138,607,316.35 | 157.75% | **14.39%** | F3 (salario_cargado formula) |
| H/J 41 | No Payroll A | — | ~68% | ~68% | F4 |
| H/J 55 | Costos Cadena C | — | 100.00% | 100.00% | F5 |
| H/J 66 | ICA | — | ~71% | ~71% | F4 (ICA base) |
| H/J 67 | GMF | 10,318,771.70 | 85.62% | 85.62% | F4 (GMF base = cost+income) |
| H/J 74 | Contribución | 183,326,007.54 | 71.60% / 302.38% sign-flip | **86.50%** | F4 (cascading from costos) |
| H/J 79 | Utilidad Neta | — | ~72–302% | ~86% | F4 (cascading) |

---

## Cell → backend path map (excerpt)

Full mapping: `tests/parity/oracle_mapping.py::CELL_TO_BACKEND`.

| Excel cell | Backend path |
|---|---|
| Vision Tarifas_Modelo_Cobro!C40 | `vision_tarifas.costo_cadena_a_total` |
| Vision Tarifas_Modelo_Cobro!C60 | `vision_tarifas.costo_cadena_c_total` |
| Vision Tarifas_Modelo_Cobro!C72 | `vision_tarifas.facturacion_total` |
| Vision Cost To Serve!H19 | `cost_to_serve.cts_mensual` |
| Vision Cost To Serve!G49 | `cost_to_serve.cts_ponderado` |
| Visión P&G!H31 | `vision_pyg.filas[?key=='costos_cadena_a'].valores[5]` |
| Visión P&G!H32 | `vision_pyg.filas[?key=='payroll_cadena_a'].valores[5]` |
| Visión P&G!H67 | `vision_pyg.filas[?key=='gmf'].valores[5]` |
| Visión P&G!H74 | `vision_pyg.filas[?key=='contribucion'].valores[5]` |

---

## Provenance of the oracle file

- **`tests/parity/excel_oracle_v2_7_full.json`** was extracted in W17
  via `openpyxl data_only=True` from
  `Nexa - Pricing - Simulador - V2-7.xlsx`.
- W18 did NOT modify expected values; only mapping and request fixture
  were touched.
- W19 did NOT modify expected values; only `input/context_builder.py`
  was modified to fix the duplicate-staff bug.
- Baselines (`storage/baselines/v2-7-certified/cases/*/outputs/*.json`)
  were regenerated in W19 because the staff-duplication bug had also
  contaminated them; this is documented in `WAVE19_REPORT.md §6`.

The oracle file is **read-only** for SEMANTIC F1-F6. Adjusting it
would defeat the program.

---

## Reproducing the measurement

```bash
source venv/bin/activate
python -m pytest tests/parity/test_excel_oracle_v2_7_real.py -v --tb=no
# Expected: 6 PASS, 33 FAIL, 0 skipped
```

Full suite:

```bash
python -m pytest --tb=no -q
# Expected: 892 passed, 33 failed, 25 skipped, 450 deselected
```

The 33 failures must NEVER be marked `xfail` or `skip` to clean up
output — they are the empirical signal driving F2-F6.
