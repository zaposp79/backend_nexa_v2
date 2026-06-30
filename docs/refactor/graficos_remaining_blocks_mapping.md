# Graficos Sheet — Remaining Blocks Mapping

Excel V2-8 · Sheet `Graficos`

---

## 1. Covered Blocks

| Graph | Excel Range | Status |
|---|---|---|
| Graph 1 — Bandas Visión Final | `A2:I93` | ✅ Implemented |
| Graph 2 — Ratios Vision Cost To Serve | `P4:BH29` | ✅ Implemented |
| Graph 3 — Ingresos Netos por Mes | `P42:BW47` | ✅ Implemented |
| Graph 4 — Waterfall Table | `P65:S81` | ✅ Implemented — source: `PricingResult.pyg_por_mes` (PyGMensual aggregates) |

---

## 2. Remaining Blocks

| Block | Excel Range | Status |
|---|---|---|
| Graph 4 — Waterfall chart segments | `P53:AA57` | ✅ Covered — visual transform of waterfall_table; no new backend fact (see final_graficos_p53_aa57_mapping.md) |
| CTS Deal bargaining zone | `P84:Q93` | ✅ Implemented — `graph_05_cts_bargaining_zone.py` |

---

## 3. Excel Range / Formulas

### Graph 3 — Ingresos Netos por Mes (`P42:BW47`)

- **P42**: title label `'Grafico 3 (Ingresos Netos por Mes)'`
- **P43/Q43**: x-label / periodos = `'Visión P&G'!$E$6` (meses_contrato)
- **P44/R44**: y-max = `MAX('Visión P&G'!C27:BJ27)`
- **Row 46** (P46:BW46): month index sequence `P46=1`, `Q46=IF(P46+1<=N, P46+1, NA())`
- **Row 47** (P47:BW47): ingreso_neto per month: `=IF('Visión P&G'!$C$27>=0,'Visión P&G'!C$27,NA())`

### Graph 4 — Waterfall Precio Total (`P53:AA57`)

ArrayFormulas — complex. Headers row 56:
`TOTAL | Ingreso Neto | Payroll | No Payroll | Componente Fijo | Componente Variable | Tarifa Proveedor | Costo Integración | Costo Variable | Costos Financieros | Costo Fijo | Utilidad Neta`

Row 57 values use `ArrayFormula` objects referencing P&G sums across multiple rows.

### Graph 4 — Waterfall Table (`P65:S81`)

Columns: `Concepto | Total | Promedio | % sobre ingreso Neto`

Source rows:
- `Q68=SUM('Visión P&G'!C18:BJ18)` → Ingreso Bruto
- `Q73=SUM('Visión P&G'!C27:BJ27)` → Ingreso Neto
- `Q74=SUM('Visión P&G'!C31:BJ31)` → Costos Cadena A
- `Q75=SUM('Visión P&G'!C45:BJ45)` → Costos Cadena B
- `Q76=SUM('Visión P&G'!C55:BJ55)` → Costos Cadena C
- `Q77=SUM('Visión P&G'!C30:BJ30)` → Costo Total
- `Q78=SUM('Visión P&G'!C74:BJ74)` → Contribución
- `Q79=SUM('Visión P&G'!C78:BJ78)` → Costo Fijo
- `Q80=SUM('Visión P&G'!C79:BJ79)` → Utilidad Neta
- `Q81='Visión P&G'!BK80` → % Utilidad Neta (last column)

### CTS Deal Bargaining Zone (`P84:Q93`)

- `Q84=R77` → CTS_Deal (promedio costo total)
- `Q85=R73` → Ingreso Deal (promedio ingreso neto)
- `Q86='Panel de Control General'!C63` → Margen Obj
- `Q87=Q84/(1-Q86)` → Meta Ingreso
- `Q88=MAX(Q85,Q87)*1.05` → Eje_max
- `Q90=Q84` → Pierde Plata threshold
- `Q91=Q88-Q84` → No cumple Meta band
- `Q92=Q88-Q87` → Zona Segura band
- `Q93=Q85` → Marcador (current deal income)

---

## 4. Backend Equivalent Search

### Graph 3 (IMPLEMENTED)
- Source: `resultado.pyg_por_mes[i].ingreso_neto` — already in `PricingResult`
- Function: `build_ingresos_mensuales` in `modules/calculator_motor/formulas/graphics/graph_03_ingresos_mensuales.py`
- Output: `GraficosResult.ingresos_mensuales`

### Graph 4 Waterfall (DEFERRED)
- Source: `resultado.pyg_por_mes` + `resultado.kpis`
- Risk: ArrayFormulas in Excel; requires mapping each P&G row key to waterfall category
- The table version (P65:S81) is simpler — SUM aggregates from backend PyG rows

### CTS Deal Bargaining Zone (✅ IMPLEMENTED)

- Calculator: `modules/calculator_motor/formulas/graphics/graph_05_cts_bargaining_zone.py`
- Model: `GraficoCtsBargainingZoneResult` in `models.py`
- Result path: `PricingResult.datasets_vision.graficos.cts_bargaining_zone`
- Backend facts:
  - `costo_mensual_promedio` → `resultado.kpis.costo_mensual_promedio`
  - `ingreso_neto_total` → `resultado.kpis.ingreso_neto_total`
  - `meses_contrato` → `len(resultado.pyg_por_mes)`
  - `margen_objetivo` → `solicitud.panel.margen`
- Formula mapping:
  - `Q84 = costo_mensual_promedio`
  - `Q85 = ingreso_neto_total / meses_contrato`
  - `Q86 = margen_objetivo`
  - `Q87 = Q84 / (1 - Q86)`
  - `Q88 = MAX(Q85, Q87) * 1.05`
  - `Q90 = Q84`
  - `Q91 = Q88 - Q84`
  - `Q92 = Q88 - Q87`
  - `Q93 = Q85`

---

## 5. Implementation Recommendation

| Block | Recommendation | Risk |
|---|---|---|
| Graph 3 | ✅ DONE | LOW |
| Graph 4 table (P65:S81) | SIMPLE_AND_CLEAR_NEXT_SLICE — SUM aggregates from PyG rows already in backend | LOW |
| CTS bargaining zone (P84:Q93) | ✅ DONE — `graph_05_cts_bargaining_zone.py` | LOW |
| Graph 4 waterfall (P53:AA57) | DEFER_HIGH_RISK — ArrayFormulas, unclear category grouping | HIGH |

---

## 6. Deferred Items

- **Graph 4 Waterfall ArrayFormulas** (`P53:AA57`): waterfall segments use `ArrayFormula` objects; category-to-P&G-row mapping not yet confirmed.
- **Cargos Adicionales** (`AH31:AI33`): SUMIF aggregates for Graph 2 category totals; already noted as deferred in graph_02 implementation.

---

## 7. Checkpoint

```
No storage, Excel, request, golden fixtures, or baselines were modified.
No Graph 1 or Graph 2 formulas were changed.
Implementation was only done if the next slice was clear.
```

Validated: `make verify` ✅ · `pytest tests/api/` 123 passed ✅ · `pytest tests/golden/` 99 passed ✅ · graph unit tests 100 passed ✅
