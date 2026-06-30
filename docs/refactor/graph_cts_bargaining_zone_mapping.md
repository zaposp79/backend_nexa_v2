# CTS Deal Bargaining Zone — Mapping Report

Excel V2-8 · Sheet `Graficos` · Range `P84:Q93`

---

## 1. Executive Verdict

**IMPLEMENTATION_READY**

All Excel formula sources are identified. Every required dynamic value has a confirmed backend equivalent in `PricingResult`. No new business rules need to be invented. The entire range is derived from already-computed KPIs and panel inputs.

---

## 2. Excel Source Map

Range `P84:Q93` — two columns: P = label (static text), Q = value (formula or constant).

| Cell | Label (P col) | Formula (Q col) | Cached value | Business meaning |
|---|---|---|---|---|
| Q84 | `CTS_Deal` | `=R77` | 2 438 857 897 COP | Promedio mensual Costo Total = `Q77 / meses_contrato` |
| Q85 | `Ingreso Deal` | `=R73` | 3 135 736 486 COP | Promedio mensual Ingreso Neto = `Q73 / meses_contrato` |
| Q86 | `Margen Obj` | `='Panel de Control General'!C63` | 0.21 | Margen objetivo del deal (user input) |
| Q87 | `Meta Ingreso` | `=Q84/(1-Q86)` | 3 087 161 895 COP | Precio mínimo para cumplir margen objetivo |
| Q88 | `Eje_max` | `=MAX(Q85,Q87)*1.05` | 3 292 523 310 COP | Y-axis maximum (+5% buffer) |
| Q89 | _(blank)_ | _(empty)_ | — | Separator row |
| Q90 | `Pierde Plata` | `=Q84` | 2 438 857 897 COP | Threshold: below this → losing money |
| Q91 | `No cumple Meta` | `=Q88-Q84` | 853 665 413 COP | Band width: CTS → Meta Ingreso range |
| Q92 | `Zona Segura` | `=Q88-Q87` | 205 361 415 COP | Band width: Meta Ingreso → Eje_max range |
| Q93 | `Marcador` | `=Q85` | 3 135 736 486 COP | Current deal ingreso neto marker |

---

## 3. Formula Dependency Map

```
Q84 = R77 = Q77 / 'Visión P&G'!E6
         Q77 = SUM('Visión P&G'!C30:BJ30) = sum(pyg_por_mes[i].costo_total)
         E6  = 'Panel de Control General'!C11 = panel.meses_contrato

Q85 = R73 = Q73 / 'Visión P&G'!E6
         Q73 = SUM('Visión P&G'!C27:BJ27) = sum(pyg_por_mes[i].ingreso_neto)

Q86 = 'Panel de Control General'!C63 = panel.margen  (Cadena A target margin, user-set)

Q87 = Q84 / (1 - Q86)             ← minimum price to hit target margin
Q88 = MAX(Q85, Q87) * 1.05        ← chart Y-axis upper limit

Q90 = Q84                          ← same as CTS_Deal (Pierde Plata threshold)
Q91 = Q88 - Q84                    ← band: "No cumple Meta"
Q92 = Q88 - Q87                    ← band: "Zona Segura"
Q93 = Q85                          ← same as Ingreso Deal (deal marker)
```

**Key insight:** `R77` and `R73` are simply the per-month averages from the waterfall table (already implemented in Graph 4). The bargaining zone is 100% derived from those averages plus `panel.margen`.

---

## 4. Source Cell Dependency Map

| Excel source | Meaning | Backend field |
|---|---|---|
| `Q77` (Graficos) | Total Costo Total del contrato | `sum(m.costo_total for m in pyg_por_mes)` |
| `Q73` (Graficos) | Total Ingreso Neto del contrato | `sum(m.ingreso_neto for m in pyg_por_mes)` |
| `'Visión P&G'!E6` | `meses_contrato` | `panel.meses_contrato` OR `len(pyg_por_mes)` |
| `'Panel de Control General'!C63` | Margen objetivo (Cadena A) | `solicitud.panel.margen` |

---

## 5. Backend Fact Search

| Required value | Classification | Backend path |
|---|---|---|
| `costo_total_promedio_mensual` | `EXISTS_IN_PRICING_RESULT` | `resultado.kpis.costo_total_contrato / len(pyg_por_mes)` OR `resultado.kpis.costo_mensual_promedio` |
| `ingreso_neto_promedio_mensual` | `EXISTS_IN_PRICING_RESULT` | `resultado.kpis.ingreso_neto_total / panel.meses_contrato` |
| `meses_contrato` | `EXISTS_IN_PRICING_RESULT` | `len(resultado.pyg_por_mes)` or `panel.meses_contrato` |
| `margen_objetivo` | `EXISTS_IN_PRICING_RESULT` | `solicitud.panel.margen` |
| `meta_ingreso` | derived — formula only | `cts_deal / (1 - margen_objetivo)` — no new business rule |
| `eje_max` | derived — formula only | `max(ingreso_deal, meta_ingreso) * 1.05` — no new business rule |
| `pierde_plata` | alias of `cts_deal` | same as `costo_total_promedio_mensual` |
| `no_cumple_meta` | derived — band | `eje_max - cts_deal` |
| `zona_segura` | derived — band | `eje_max - meta_ingreso` |
| `marcador` | alias of `ingreso_deal` | same as `ingreso_neto_promedio_mensual` |

**Missing facts:** None.
**Uncertain facts:** None.

---

## 6. Missing / Uncertain Facts

None. All values resolve to confirmed backend fields or are pure arithmetic derivations.

Note: `resultado.kpis.costo_mensual_promedio` already stores `costo_total_contrato / meses_contrato` (see `kpis_calculator.py:76`). Use it directly — no re-computation needed.

---

## 7. Implementation Recommendation

**Implement now: YES**

### Calculator location
```
modules/calculator_motor/formulas/graphics/graph_05_cts_bargaining_zone.py
```

### Function signature
```python
def build_cts_bargaining_zone(
    *,
    pyg_por_mes: list[PyGMensual],
    margen_objetivo: float,          # solicitud.panel.margen
    costo_mensual_promedio: float,   # resultado.kpis.costo_mensual_promedio
) -> GraficoCTSBargainingZoneResult:
```

### Derivations (pure arithmetic — no new business rules)
```python
meses             = len(pyg_por_mes)
ingreso_neto_tot  = sum(m.ingreso_neto for m in pyg_por_mes)
ingreso_deal      = ingreso_neto_tot / meses if meses else 0.0   # R73
cts_deal          = costo_mensual_promedio                        # R77 = kpis already computed

meta_ingreso  = cts_deal / (1 - margen_objetivo) if margen_objetivo < 1 else cts_deal
eje_max       = max(ingreso_deal, meta_ingreso) * 1.05
pierde_plata  = cts_deal
no_cumple_meta = eje_max - cts_deal
zona_segura    = eje_max - meta_ingreso
marcador       = ingreso_deal
```

### Suggested model
```python
@dataclass(frozen=True)
class GraficoCTSBargainingZoneResult:
    cts_deal: float           # promedio costo total mensual
    ingreso_deal: float       # promedio ingreso neto mensual
    margen_objetivo: float    # panel.margen (Cadena A target)
    meta_ingreso: float       # precio mínimo para cumplir margen
    eje_max: float            # chart Y-axis upper limit
    pierde_plata: float       # = cts_deal (threshold label)
    no_cumple_meta: float     # band: cts → meta
    zona_segura: float        # band: meta → eje_max
    marcador: float           # = ingreso_deal (current deal marker)
    excel_trace: str = "Graficos!P84:Q93"
```

### Result path
```
PricingResult.datasets_vision.graficos.cts_bargaining_zone
```

### Wiring
```
VisionDatasetsBuilder._build_graficos()
  → build_cts_bargaining_zone(
        pyg_por_mes=resultado.pyg_por_mes,
        margen_objetivo=solicitud.panel.margen,
        costo_mensual_promedio=resultado.kpis.costo_mensual_promedio,
    )
  → graficos.cts_bargaining_zone = result
```

### Tests needed
```
tests/unit/test_graph_05_cts_bargaining_zone.py
- cts_deal = kpis.costo_mensual_promedio (direct pass-through)
- ingreso_deal = sum(ingreso_neto) / meses
- meta_ingreso = cts_deal / (1 - margen_objetivo)
- eje_max = max(ingreso_deal, meta_ingreso) * 1.05
- pierde_plata = cts_deal
- no_cumple_meta = eje_max - cts_deal
- zona_segura = eje_max - meta_ingreso
- marcador = ingreso_deal
- margen_objetivo = 1.0 does not raise (guard division by zero)
- excel_trace = "Graficos!P84:Q93"
- Graph 1/2/4 unit tests still pass
```

---

## 8. Deferred Items

| Block | Range | Status |
|---|---|---|
| Graph 4 — Waterfall ArrayFormulas | `P53:AA57` | DEFERRED_HIGH_RISK — ArrayFormulas, category grouping unclear |

The CTS bargaining zone (`P84:Q93`) is now confirmed and can be implemented.

---

## 9. Checkpoint

```
No implementation was done.
No runtime code was changed.
No storage, Excel, request, golden fixtures, or baselines were modified.
Only docs/refactor/graph_cts_bargaining_zone_mapping.md was created.
```
