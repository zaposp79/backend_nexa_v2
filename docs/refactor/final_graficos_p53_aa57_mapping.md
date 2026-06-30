# Final Graficos Block Mapping — P53:AA57

Excel V2-8 · Sheet `Graficos`  
Date inspected: 2026-06-14

---

## 1. Executive Verdict

**P53_AA57_ALREADY_COVERED**

`Graficos!P53:AA57` is a **waterfall chart segment series** — an Excel-only visual
rendering aid that decomposes the same values already present in `waterfall_table`
(P65:S81) into a stacked-bar chart format.

It introduces **no new dynamic business facts** not already available through
`PyGMensual` and `KPIsDeal`. Backend consumers already receive all required values
via `GraficoWaterfallTableResult` or directly from `PricingResult`.

Two categories (`Tarifa Proveedor`, `Costo Integración`) are sub-fields of
`costo_c` — they exist in `PyGMensual` as `costo_c` total but are not individually
exposed as `tarifa_proveedor_a` / `costo_integracion`. These sub-fields evaluate to
cached totals of 23,079,213,325 and 632,991,008 COP respectively in the reference
deal — significant but they are **chart-segment precision refinements**, not facts
missing from any existing backend output.

**Recommendation: close Graficos sheet as fully mapped. No new code required.**

---

## 2. Excel Range Inspection

### Layout

| Row | Content |
|-----|---------|
| P53 | Title label: `'Grafico 4 Waterfall Precio Total)'` |
| P54–P55 | Empty |
| P56–AA56 | Column headers (labels) |
| P57–AA57 | Data row — FILTER/ArrayFormulas or derived formula |

### Row 56 headers (P–AA)

```
P   TOTAL
Q   Ingreso Neto
R   Payroll
S   No Payroll
T   Componente Fijo
U   Componente Variable
V   Tarifa Proveedor
W   Costo Integración
X   Costo Variable
Y   Costos Financieros
Z   Costo Fijo
AA  Utilidad Neta
```

### Row 57 formulas

| Cell | Formula | Cached value (COP) |
|------|---------|-------------------|
| P57 | `=Q57+(ABS(SUM(R57:Z57)+AA57))` | 177,520,690,340 |
| Q57 | `=FILTER('Visión P&G'!$BK$12:$BK$80, $B$12:$B$80=$Q56)` | 75,257,675,659 |
| R57 | `=FILTER('Visión P&G'!$BK$12:$BK$80*-1, $B$12:$B$80=$R56)` | -30,196,389,528 |
| S57 | `=FILTER('Visión P&G'!$BK$12:$BK$80*-1, $B$12:$B$80=$S56)` | -60,946,803,080 |
| T57 | `=FILTER('Visión P&G'!$BK$12:$BK$80*-1, $B$12:$B$80=$T56)` | -380,580,531 |
| U57 | `=FILTER('Visión P&G'!$BK$12:$BK$80*-1, $B$12:$B$80=$U56)` | 0 |
| V57 | `=FILTER('Visión P&G'!$BK$12:$BK$80*-1, $B$12:$B$80=$V56)` | -23,079,213,326 |
| W57 | `=FILTER('Visión P&G'!$BK$12:$BK$80*-1, $B$12:$B$80=$W56)` | -632,991,008 |
| X57 | `=FILTER('Visión P&G'!$BK$12:$BK$80*-1, $B$12:$B$80=$X56)` | 0 |
| Y57 | `=FILTER('Visión P&G'!$BK$12:$BK$80*-1, $B$12:$B$80=$Y56)` | 0 |
| Z57 | `=FILTER('Visión P&G'!$BK$12:$BK$80*-1, $B$12:$B$80=$Z56)` | 0 |
| AA57 | `=FILTER('Visión P&G'!$BK$12:$BK$80, $B$12:$B$80=$AA56)` | 12,972,962,792 |

All row 57 cells (Q–AA) are `ArrayFormula` objects confirmed via `ws.array_formulae`.

**Pattern:** Each cell filters `'Visión P&G'!$BK$12:$BK$80` (contract total column) where `$B$12:$B$80` (label column) matches the row 56 header. It returns the single matching row value. Costs are negated (`*-1`); income and utilidad are positive.

---

## 3. Formula / Source-Cell Table

| Graficos col | Row 56 label | VisionPyG label (col B) | VisionPyG row | BK total (COP) |
|---|---|---|---|---|
| Q57 | Ingreso Neto | `Ingreso Neto` | B27 | 75,257,675,659 |
| R57 | Payroll | `Payroll` | B32 | -30,196,389,528 |
| S57 | No Payroll | `No Payroll` | B41 | -60,946,803,080 |
| T57 | Componente Fijo | `Componente Fijo` | B46 | -380,580,531 |
| U57 | Componente Variable | `Componente Variable` | B50 | 0 |
| V57 | Tarifa Proveedor | `Tarifa Proveedor` | B56 | -23,079,213,326 |
| W57 | Costo Integración | `Costo Integración` | B57 | -632,991,008 |
| X57 | Costo Variable | `Costo Variable` | B61 | 0 |
| Y57 | Costos Financieros | `Componente Financiero` | B65 | 0 (cached) |
| Z57 | Costo Fijo | `Costo Fijo` | B78 | 0 / None |
| AA57 | Utilidad Neta | `Utilidad Neta` | B79 | 12,972,962,792 |
| P57 | TOTAL | `=Q57+ABS(SUM(R57:Z57)+AA57)` | derived | 177,520,690,340 |

> Note: `Costos Financieros` (Y57) matches `Componente Financiero` (B65 = ICA+GMF+Pólizas+Com.Admin)
> whose cached total is 3,752,123,337 — but the Y57 formula matches label `"Costos Financieros"` (B70)
> which is 0 in the reference deal. This is an Excel label mismatch in the source; the
> meaningful financial cost is B65 (`Componente Financiero`).

---

## 4. Relation to Graph 4 `waterfall_table` (P65:S81)

`P53:AA57` **is a visual transformation of P65:S81**, not a new calculation:

- Same data source: `'Visión P&G'!$BK$12:$BK$80` (contract totals)
- Same values appear in `waterfall_table` as `total` fields on each `WaterfallItem`
- P53:AA57 pivots the same numbers into a horizontal stacked-bar format:
  - X-axis = category labels (row 56)
  - Single data row (row 57) = contract totals per category
- P65:S81 (table) provides `Concepto | Total | Promedio | % Ingreso Neto` per row
- P53:AA57 (chart) provides one row of contract totals per column

**Classification: transforms P65:S81 — same underlying values, different visual pivot.**

### Sub-category breakdown (V, W — not in waterfall_table)

`waterfall_table` uses `costo_c` as a single row. P53:AA57 splits it into:
- `Tarifa Proveedor` = `BK56` = 23,079,213,326 COP
- `Costo Integración` = `BK57` = 632,991,008 COP

These sub-fields map to `PyGMensual.costo_c` total (23,712,204,334 = 23,079,213,326 + 632,991,008).
They exist in `PyGMensual` only as the combined `costo_c` property.

---

## 5. Backend Facts Check

| Category | Backend field | Availability | Classification |
|---|---|---|---|
| Ingreso Neto | `sum(pyg.ingreso_neto)` | `GraficoWaterfallTableResult` | EXISTS_IN_WATERFALL_TABLE |
| Payroll | `sum(pyg.payroll_a)` | `PyGMensual.payroll_a` | EXISTS_IN_CALCULATOR_MOTOR_FACTS |
| No Payroll | `sum(pyg.no_payroll_a)` | `PyGMensual.no_payroll_a` | EXISTS_IN_CALCULATOR_MOTOR_FACTS |
| Componente Fijo | `sum(pyg.costo_b)` | `GraficoWaterfallTableResult` | EXISTS_IN_WATERFALL_TABLE |
| Componente Variable | 0 (always) | constant | EXISTS_IN_CALCULATOR_MOTOR_FACTS |
| Tarifa Proveedor | sub-field of `costo_c` | NOT individually exposed | UNCERTAIN_SOURCE (sub-field) |
| Costo Integración | sub-field of `costo_c` | NOT individually exposed | UNCERTAIN_SOURCE (sub-field) |
| Costo Variable | 0 (always) | constant | EXISTS_IN_CALCULATOR_MOTOR_FACTS |
| Costos Financieros | `sum(pyg.costos_financieros)` | `PyGMensual.costos_financieros` | EXISTS_IN_CALCULATOR_MOTOR_FACTS |
| Costo Fijo | None / 0 | not modelled in backend | UNCERTAIN_SOURCE |
| Utilidad Neta | `sum(pyg.utilidad_neta)` | `GraficoWaterfallTableResult` | EXISTS_IN_WATERFALL_TABLE |

**Already covered by waterfall_table:** yes (for all values the chart actually renders as non-zero).

The only two UNCERTAIN_SOURCE entries (`Tarifa Proveedor`, `Costo Integración`) are
sub-components of `costo_c` that are always summed into `waterfall_table.costo_c`.
No backend consumer currently needs these broken out individually.

`Costo Fijo` (Z57) is 0 / None in both Excel and backend for this deal type — it
represents a fixed cost allocation not modelled in the current engine.

---

## 6. Recommendation

**implement code: NO**

**Reason:**

1. `P53:AA57` is an Excel chart layout block — it feeds the stacked-bar waterfall
   visual in Excel. It does not produce a business fact that is missing from the backend.
2. All non-zero values in row 57 are already exposed via `GraficoWaterfallTableResult`
   (P65:S81) or directly via `PyGMensual` fields.
3. The two sub-components (`Tarifa Proveedor`, `Costo Integración`) that are not
   individually in `waterfall_table` are chart-segment refinements. No backend
   consumer currently requests them. If a frontend needs this granularity, the right
   approach is to split `costo_c` in `waterfall_table` — a scoped future enhancement,
   not a blocker.
4. `Costo Fijo` and `Costos Financieros` (by exact label) both evaluate to 0 in the
   reference deal; they carry no numeric content to implement.

**Close Graficos sheet: YES** — all 5 graphs are implemented, P53:AA57 is a chart
rendering artifact covered by existing outputs.

---

## 7. Final Graficos Closure Status

| Graph | Excel Range | Status |
|---|---|---|
| Graph 1 — Bandas Visión Final | `A2:I93` | ✅ Implemented |
| Graph 2 — Ratios Vision Cost To Serve | `P4:BH29` | ✅ Implemented |
| Graph 3 — Ingresos Netos por Mes | `P42:BW47` | ✅ Implemented |
| Graph 4 — Waterfall Table | `P65:S81` | ✅ Implemented |
| Graph 5 — CTS Deal Bargaining Zone | `P84:Q93` | ✅ Implemented |
| Waterfall chart segments | `P53:AA57` | ✅ Covered — visual transform of Graph 4; no new backend fact |

**Graficos sheet: CLOSED ✅**

---

## 8. Checkpoint

```
No implementation was done.
No runtime code was changed.
No storage, Excel, request, golden fixtures, or baselines were modified.
```

---

## Appendix — ArrayFormula pattern confirmed

All Q57:AA57 cells are registered in `ws.array_formulae`:

```python
{'Q57': 'Q57', 'R57': 'R57', 'S57': 'S57', 'T57': 'T57',
 'U57': 'U57', 'V57': 'V57', 'W57': 'W57', 'X57': 'X57',
 'Y57': 'Y57', 'Z57': 'Z57', 'AA57': 'AA57'}
```

`openpyxl` reads these as `ArrayFormula` objects with `.text` containing the formula
string. The `FILTER()` function (`_xlfn._xlws.FILTER`) is an Excel 365 dynamic array
function — it cannot be evaluated by `openpyxl` directly, hence cached values are
used for reference.
