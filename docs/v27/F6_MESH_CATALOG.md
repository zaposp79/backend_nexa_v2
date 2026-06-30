# F6 — Oracle Mesh Catalog

> **Status (2026-05-28)**: F6 deliverable. Catálogo de **161 checkpoints**
> distribuidos en 16 stages del pipeline. Cada uno está mapeado a una celda
> Excel V2-7 (verdad) + un extractor del `PricingResult` (backend).
>
> Source files:
> - Catálogo: `tests/parity/oracle_mesh_mapping.py`
> - Oracle JSON (1,118 celdas extraídas): `tests/parity/excel_oracle_v2_7_mesh.json`
> - Suite: `tests/parity/test_oracle_mesh.py`
> - Drift heatmap (live results): `tests/parity/DRIFT_HEATMAP.md`
> - Extractor script: `scripts/extract_oracle_mesh.py`
> - Heatmap builder: `scripts/build_drift_heatmap.py`

---

## Diseño

El mesh detecta drift **en el punto exacto donde aparece** en lugar de
propagado al output final. Por cada celda Excel calculada que es ramificación
de una etapa del pipeline, hay un checkpoint con extractor que devuelve el
valor backend equivalente. Si el backend no expone el valor, el extractor
retorna `None` — eso es una declaración explícita de hueco semántico, no se
oculta con skip.

Tolerancia técnica: `1e-6` (objetivo conceptual: drift 0.00%). Esto cubre
solo error IEEE-754 acumulado; cualquier drift estructural sale a la luz.

## Cobertura por stage

| Stage | Checkpoints | Descripción |
|---|---:|---|
| `PANEL` | 15 | Inputs panel de control echo (tarifas, márgenes, tasas) |
| `NOMINA` | 5 | Costo empresa por perfil (Inputs de Nomina!W) — actualmente NO expuesto |
| `NOMINA_LOADED` | 16 | Salario fijo por canal/mes (Nomina Loaded!I/J/K..) |
| `PAYROLL_A` | 7 | Payroll Cadena A per contract month (Visión P&G!H..N32) |
| `COSTO_A` | 7 | Costo operativo A per mes (Visión P&G!H..N31) |
| `NO_PAYROLL_A` | 7 | No-payroll A per mes (Visión P&G!H..N41) |
| `COSTO_B` | 7 | Costo Cadena B per mes (Visión P&G!H..N45) |
| `COSTO_C` | 7 | Costo Cadena C per mes (Visión P&G!H..N55) |
| `COSTO_TOTAL` | 7 | Costo total operativo per mes (Visión P&G!H..N30) |
| `COSTOS_FINANCIEROS` | 28 | Pólizas + ICA + GMF + Financiación per mes (rows 65-68) |
| `INGRESO` | 14 | Bruto + neto per mes (Visión P&G!H..N18, H..N27) |
| `RAMPUP` | 7 | Factor rampup per mes (Visión P&G!H..N15) |
| `PYG` | 14 | Contribución + utilidad neta per mes (rows 74, 79) |
| `VISION_TARIFAS` | 8 | Totales costo + ingreso (Vision Tarifas_Modelo_Cobro!C40,C50,C60,C72) |
| `VISION_CTS` | 9 | Participación cadena + CTS por cadena + ponderado |
| `KPI` | 3 | KPIs finales (ingreso, facturación, costo mensual promedio) |

**Total mapeado a extractor backend**: 161 checkpoints (149 mapeados, 12
declarados como `_missing` explícito + 5 sin extractor estable).

**Total oracle extracted (sin mapping)**: 1,118 celdas en
`excel_oracle_v2_7_mesh.json` — corpus base para futuras expansiones.

## Convenciones

- `_panel("attr")` — extrae `result.panel.attr`
- `_kpi("attr")` — extrae `result.kpis.attr`
- `_pyg_field("field", contract_idx)` — extrae `result.pyg_por_mes[contract_idx].field`
- `_pyg_prop("prop", contract_idx)` — idem para `@property`
- `_vt("attr")` — extrae `result.vision_tarifas.attr`
- `_cts("attr")` — extrae `result.cost_to_serve.attr`
- `_channel(substr, "attr")` — busca canal cuyo nombre contiene `substr`
- `_missing` — declara explícitamente que el backend no expone el valor

## Calendar-to-contract mapping

El contrato V2-7 inicia en `2026-06-01` (Junio = calendar M6). Columnas Excel:

| Excel col | Calendar month | Contract month | Backend index |
|---|---|---|---|
| C | M1 (Ene) | — | — |
| D | M2 (Feb) | — | — |
| E | M3 (Mar) | — | — |
| F | M4 (Abr) | — | — |
| G | M5 (May) | — | — |
| H | M6 (Jun) | M1 | 0 |
| I | M7 (Jul) | M2 | 1 |
| J | M8 (Ago) | M3 | 2 |
| K | M9 (Sep) | M4 | 3 |
| L | M10 (Oct) | M5 | 4 |
| M | M11 (Nov) | M6 | 5 |
| N | M12 (Dic) | M7 | 6 |

Por eso muchos checkpoints solo cubren columnas H..N (los meses contractuales
activos en este request canónico de 12 meses).

## Cómo extender

1. Identificar la celda Excel (Hoja!Coord) que captura el cómputo intermedio
   relevante.
2. Si no está ya en `excel_oracle_v2_7_mesh.json`, agregar el rango en
   `scripts/extract_oracle_mesh.py` y re-ejecutar.
3. Agregar un `_ck(...)` en `tests/parity/oracle_mesh_mapping.py` con un
   extractor que devuelva el valor backend (o `_missing` si no está expuesto).
4. Re-correr `python scripts/build_drift_heatmap.py` y revisar
   `tests/parity/DRIFT_HEATMAP.md`.

## Stages con observación inmediata

- **PASS al 100%**: `COSTO_B` (7/7), `RAMPUP` (7/7) — backend correctísimo aquí.
- **FAIL al 100%**: `COSTOS_FINANCIEROS`, `INGRESO`, `PYG`, `VISION_CTS`,
  `PAYROLL_A`, `COSTO_A`, `COSTO_C`, `COSTO_TOTAL`, `KPI`, `NO_PAYROLL_A`,
  `NOMINA_LOADED`.

La propagación de drift es estructural: payroll inflado → costo_a inflado →
costo_total inflado → ingreso (vía factor billing) inflado → P&G inflado →
KPIs erradas. Cerrar PAYROLL_A (F3.B) descongesta el resto.
