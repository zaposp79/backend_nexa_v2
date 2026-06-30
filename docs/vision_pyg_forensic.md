# Vision P&G — Forensic Analysis

> Auditoría forense: PyG pipeline output vs Excel "Visión P&G" + frontend parity requirements
>
> Last updated: 2026-05-21

---

## 1. Executive Summary

### What works (pipeline is mathematically complete)

| Component | Fields | Status |
|-----------|--------|--------|
| `PyGMensual` stored fields | 17 | All populated per month |
| `PyGMensual` @property fields | 9 | Correctly derived |
| `KPIsDeal` | 13 | Computed from P&G |
| `WaterfallPromedio` | 15 | Computed from active months |
| `ReglaNegocios[]` | 5 rules | Status/monto evaluated |
| Ramp-up support | months 1..N | Factor from parametrization |
| Serializer coverage | 11 top-level sections | All serialized |

### What's missing (frontend parity gaps)

| Gap | Severity | Description |
|-----|----------|-------------|
| **GAP-PYG-1** | HIGH | No acumulados (running totals over months) |
| **GAP-PYG-2** | HIGH | No structured Vision P&G sections for frontend blocks |
| **GAP-PYG-3** | MEDIUM | No monthly % breakdown per component |
| **GAP-PYG-4** | MEDIUM | No ingreso/costo decomposition labels for rendering |
| **GAP-PYG-5** | LOW | No indexation tracking in output (factor_aumento per month) |
| **GAP-PYG-6** | LOW | No scenario comparison support in PyG |

**Verdict:** The PyG pipeline produces correct numbers. The gap is **structural** —
the output is a flat list of months, not a structured visual model for the frontend.

---

## 2. Current Backend Output Structure

### 2.1 `pyg_por_mes[]` — 26 fields per month

| Field | Type | Source | Excel Column |
|-------|------|--------|-------------|
| `mes` | int | Stored | Row header |
| `rampup` | float | Stored | Ramp-up row |
| `ingreso_bruto_a` | float | Stored | Ingreso Cadena A |
| `ingreso_bruto_b` | float | Stored | Ingreso Cadena B |
| `ingreso_bruto_c` | float | Stored | Ingreso Cadena C |
| `contingencia_op` | float | Stored | Contingencia operativa |
| `contingencia_com` | float | Stored | Contingencia comercial |
| `markup_ingreso` | float | Stored | Markup sobre ingreso |
| `descuento_ingreso` | float | Stored | Descuento sobre ingreso |
| `payroll_a` | float | Stored | Payroll Cadena A |
| `no_payroll_a` | float | Stored | No-payroll Cadena A |
| `costo_b` | float | Stored | Costo Cadena B |
| `costo_c` | float | Stored | Costo Cadena C |
| `ica` | float | Stored | ICA |
| `gmf` | float | Stored | GMF |
| `polizas` | float | Stored | Pólizas |
| `financiacion` | float | Stored | Financiación |
| `ingreso_bruto` | @property | a+b+c | Total ingreso bruto |
| `ingreso_neto` | @property | bruto+contingencias+markup-desc | Total ingreso neto |
| `costo_a` | @property | payroll+nopayroll | Total Cadena A |
| `costos_financieros` | @property | ica+gmf+pol+fin | Total financieros |
| `costo_total` | @property | a+b+c | Total costos operativos |
| `contribucion` | @property | neto-total | Contribución |
| `pct_contribucion` | @property | contrib/neto | % contribución |
| `utilidad_neta` | @property | =contribucion | Utilidad neta |
| `pct_utilidad_neta` | @property | util/neto | % utilidad |

### 2.2 `kpis` — 13 fields

| Field | Source |
|-------|--------|
| `costo_mensual_promedio` | `sum(costo_total) / n` |
| `costo_cadena_a_promedio` | `sum(costo_a) / n` |
| `ingreso_mensual` | `(costo_a_avg + fin_on_avg) / factor_margenes` |
| `facturacion_mensual_proyectada` | `ingreso_mensual / factor_periodo` |
| `ingreso_bruto_total` | `sum(ingreso_bruto)` |
| `ingreso_neto_total` | `sum(ingreso_neto)` |
| `costo_total_contrato` | `sum(costo_total)` |
| `contribucion_total` | `sum(contribucion)` |
| `utilidad_neta_total` | `sum(utilidad_neta)` |
| `pct_utilidad_neta_total` | `util_total / neto_total` |
| `valor_total_deal` | `= ingreso_neto_total` |
| `margen_minimo_requerido` | From parametrization |
| `cumple_margen_minimo` | `panel.margen >= min` |

### 2.3 `waterfall_promedio` — 15 fields

All averaged over active months (ingreso_neto > 0). Already structured for
frontend waterfall chart rendering.

---

## 3. Gap Analysis — Frontend Parity

### GAP-PYG-1: No Acumulados (Running Totals) — HIGH

**Excel P&G** has columns for cumulative sums: `acum_ingreso_neto`, `acum_costo_total`,
`acum_contribucion`. These are essential for progress-tracking charts.

**Backend output:** Only `pyg_por_mes[]` with per-month values and `kpis` with final totals.
No intermediate running totals.

**Current month 3 example:**
```
Acum ingreso_neto:  2,179,370,660
Acum costo_total:   2,040,828,983
Acum contribucion:    138,541,678
```

These values are NOT in the output; they must be computed by the frontend.

**Fix options:**
- (a) Add `acum_ingreso_neto`, `acum_costo_total`, `acum_contribucion` to `PyGMensual`
  (computed in `PyGCalculator.calcular_contrato`)
- (b) Add a separate `acumulados[]` list in `PricingResult`
- (c) Let frontend compute (simplest, since it's just running sums)

**Recommended:** Option (a) — add 3 fields to PyGMensual, computed in the contrato loop.
This follows the "frontend solo renderiza" principle.

### GAP-PYG-2: No Structured Vision P&G Sections — HIGH

**Excel "Visión P&G"** is organized into visual blocks:

```
RESUMEN EJECUTIVO
  Meses contrato | Valor total deal | Margen promedio | Utilidad neta

INGRESOS
  Ingreso Cadena A      mes1  mes2  ...  acum
  Ingreso Cadena B      mes1  mes2  ...  acum
  Ingreso Cadena C      mes1  mes2  ...  acum
  Ingreso Bruto         mes1  mes2  ...  acum
  (+) Contingencia Op   mes1  mes2  ...  acum
  (+) Contingencia Com  mes1  mes2  ...  acum
  (+) Markup            mes1  mes2  ...  acum
  (-) Descuento         mes1  mes2  ...  acum
  = INGRESO NETO        mes1  mes2  ...  acum

COSTOS OPERATIVOS
  Payroll A             mes1  mes2  ...  acum
  No-payroll A          mes1  mes2  ...  acum
  Costo B               mes1  mes2  ...  acum
  Costo C               mes1  mes2  ...  acum
  = COSTO TOTAL         mes1  mes2  ...  acum

COSTOS FINANCIEROS
  ICA                   mes1  mes2  ...  acum
  GMF                   mes1  mes2  ...  acum
  Pólizas               mes1  mes2  ...  acum
  Financiación          mes1  mes2  ...  acum
  = TOTAL FINANCIEROS   mes1  mes2  ...  acum

RESULTADOS
  Contribución          mes1  mes2  ...  acum
  % Contribución        mes1  mes2  ...  acum
  Utilidad Neta         mes1  mes2  ...  acum
  % Utilidad Neta       mes1  mes2  ...  acum
```

**Backend output:** A flat list `pyg_por_mes[]`. The frontend must group these fields
into visual blocks and apply labels.

**Fix:** Create a `VisionPyG` dataclass that structures `pyg_por_mes` into labeled sections:

```python
@dataclass
class VisionPyGRow:
    """One row of the Vision P&G table (a line item across all months)."""
    key: str              # e.g. "ingreso_bruto_a"
    label: str            # e.g. "Ingreso Cadena A"
    seccion: str          # e.g. "ingresos"
    tipo: str             # "linea" | "subtotal" | "total"
    signo: str            # "+" | "-" | "="
    valores: List[float]  # one per month
    acumulado: float      # running total at contract end
    promedio: float       # average over active months

@dataclass
class VisionPyG:
    filas: List[VisionPyGRow]  # ordered as in the Excel
    meses_contrato: int
    meses_activos: int
    resumen_ejecutivo: ResumenEjecutivoPyG
```

### GAP-PYG-3: No Monthly % Breakdown — MEDIUM

**Excel** shows percentage columns alongside absolute values:
- `% payroll_a / costo_total` per month
- `% costo_b / costo_total` per month
- `% contribucion / ingreso_neto` per month (already in `pct_contribucion`)

**Backend** only computes 2 %s: `pct_contribucion` and `pct_utilidad_neta`.

**Fix:** Add percentage fields to `PyGMensual` or compute in the `VisionPyG` builder.

### GAP-PYG-4: No Labels for Frontend Rendering — MEDIUM

**Backend** fields use code names (`payroll_a`, `no_payroll_a`).
**Frontend** needs display labels ("Nómina Cadena A", "Infraestructura y TI").

**Fix:** The `VisionPyGRow.label` field from GAP-PYG-2 solves this.

### GAP-PYG-5: No Indexation Tracking — LOW

**Backend** applies indexation via `factor_aumento` inside `NominaCalculator`,
but the factor is not surfaced in `PyGMensual`. For contracts >12 months,
the frontend can't show when/how costs change.

**Fix:** Add `factor_indexacion_humano` and `factor_indexacion_tecnologico` to `PyGMensual`.

### GAP-PYG-6: No Scenario Comparison — LOW

**Excel** supports what-if scenarios (different margins, FTE counts).
**Backend** computes a single result per request.

**Fix:** This is an API-level feature, not a data model gap. The frontend can
call `/calculate` multiple times with different inputs and compare client-side.

---

## 4. Numerical Validation — PyG Pipeline

### 4.1 Monthly P&G Consistency

```
Mes  1: ramp=0.85  ing_neto=669,120,976  costo_op=680,629,537  contrib=-11,508,561  pct=-1.72%
Mes  2: ramp=0.92  ing_neto=723,661,307  costo_op=680,099,723  contrib= 43,561,584  pct= 6.02%
Mes  3: ramp=1.00  ing_neto=786,588,377  costo_op=680,099,723  contrib=106,488,654  pct=13.54%
Mes 12: ramp=1.00  ing_neto=786,588,377  costo_op=680,099,723  contrib=106,488,654  pct=13.54%
```

**Invariants verified:**
- Month 1 costs are slightly higher (no_payroll_a differs in first month)
- Months 3-12 are constant (no indexation for 12-month contract)
- Ramp-up correctly reduces revenue in months 1-2
- Month 1 has negative contribution (costs > revenue during ramp-up)
- Month 1 financiacion = 0 (no prior month → convention Excel V2-4)

### 4.2 Revenue Formula

```python
ingreso_bruto_a = costo_a × (1 + margen) × rampup
               = 329,236,288 × 1.1339 × 1.0
               = 373,321,027  ← MATCHES mes 3

ingreso_bruto_b = costo_b × (1 + margen) × rampup
               = 350,863,435 × 1.1339 × 1.0
               = 397,844,049  ← MATCHES mes 3
```

### 4.3 Financial Costs Formula

```
Mes 2 (base = costo_total_mes_1 = 680,629,537):
  financiacion = factor_periodo(1) × tasa(0.0153) × 680,629,537 = 10,413,632  ✅
  polizas = tasa_polizas × (costo_op + fin) / factor_margenes
  ica = (costo_op/factor_margenes + polizas + fin) × tasa_ica
  gmf = (costo_op + polizas + fin) × tasa_gmf
```

### 4.4 Acumulados Totals

```
After 12 months:
  acum_ingreso_neto  = 9,258,666,055  = KPIs.ingreso_neto_total  ✅
  acum_costo_total   = 8,161,726,488  = KPIs.costo_total_contrato  ✅
  acum_contribucion  = 1,096,939,568  = KPIs.contribucion_total  ✅
  pct_utilidad_total = 11.85%         = KPIs.pct_utilidad_neta_total ✅
```

### 4.5 Revenue Decomposition (per chain)

```
Mes 3 (cruising):
  Cadena A: 373,321,027 (48.4% of total)
  Cadena B: 397,844,049 (51.6% of total)
  Cadena C: 0
  Total:    771,165,076
```

**Revenue split is consistent with cost split** (costo_a=329M ≈ 48.4%, costo_b=351M ≈ 51.6%).

---

## 5. Excel Comparison — Known Divergences

### 5.1 `H019_cts_mensual_total` vs `KPIs.costo_mensual_promedio`

| Metric | Excel | Backend | Delta |
|--------|-------|---------|-------|
| Monthly cost base | 301,965,089 | 680,143,874 | 125.2% |

**Root cause:** This is the SAME issue as VisionTarifas GAP-3. The Excel's
"CTS mensual total" (H019) is **not** the same as `costo_total`. It's the
cost-to-serve metric from the VCS tab (CTS_weighted × total_denominator),
which uses a different aggregation logic.

The backend's `costo_mensual_promedio = sum(costo_total) / 12` is the
**actual P&G cost average**, including all chains. These are different metrics.

### 5.2 `B019_ingreso_mensual` vs `KPIs.ingreso_mensual`

| Metric | Excel | Backend | Delta |
|--------|-------|---------|-------|
| Monthly tariff | 355,764,509 | 419,332,701 | 17.9% |

**Root cause:** See VisionTarifas GAP-3 — different cost base for tariff derivation.

### 5.3 `T019_valor_total_deal` vs `KPIs.valor_total_deal`

| Metric | Excel | Backend | Delta |
|--------|-------|---------|-------|
| Total deal value | 5,471,188,699 | 9,258,666,055 | 69.2% |

**Root cause:** `valor_total_deal = ingreso_neto_total`. Since revenue is higher
in the backend (due to higher cost base), the total deal value is proportionally higher.

### 5.4 P&G Structure — What Matches

Despite the aggregate KPI deltas, the **P&G formulas themselves are correct**:

| Formula | Status | Verification |
|---------|--------|-------------|
| `ingreso = costo × (1+margen) × rampup` | EXACT | Traced per-month |
| `contingencia = ingreso_bruto × pct` | EXACT | op=2%, com=0% |
| `financiacion = factor × tasa × costo_anterior` | EXACT | M1=0, M2=10.4M |
| `polizas = tasa × (costo+fin) / factor_margenes` | EXACT | Calibrated |
| `ica = (costo/factor + pol + fin) × tasa_ica` | EXACT | Gross-up applied |
| `gmf = (costo + pol + fin) × tasa_gmf` | EXACT | No gross-up |
| `ingreso_neto = bruto + cont_op + cont_com + markup - desc` | EXACT | Signs correct |
| `contribucion = ingreso_neto - costo_total` | EXACT | Definition match |

---

## 6. Recommended Implementation Plan

### Phase PYG-1: Add acumulados to `PyGMensual` (model enrichment)

```python
@dataclass
class PyGMensual:
    # ... existing 17 stored fields ...
    
    # NEW: Acumulados (computed in calcular_contrato loop)
    acum_ingreso_neto: float = 0.0
    acum_costo_total: float = 0.0
    acum_contribucion: float = 0.0
    acum_ingreso_bruto: float = 0.0
    acum_costos_financieros: float = 0.0
```

Modify `PyGCalculator.calcular_contrato()`:
```python
for mes in range(1, n + 1):
    pyg = self.calcular_mes(perfiles_cadena_a, mes, costo_anterior)
    acum_neto += pyg.ingreso_neto
    acum_costo += pyg.costo_total
    acum_contrib += pyg.contribucion
    pyg.acum_ingreso_neto = acum_neto
    pyg.acum_costo_total = acum_costo
    pyg.acum_contribucion = acum_contrib
    resultados.append(pyg)
```

### Phase PYG-2: Create `VisionPyG` structured model

```python
@dataclass
class VisionPyGRow:
    key: str           # field name for data binding
    label: str         # display label in Spanish
    seccion: str       # "resumen" | "ingresos" | "costos_op" | "costos_fin" | "resultados"
    tipo: str          # "linea" | "subtotal" | "total" | "porcentaje"
    signo: str         # "+" | "-" | "=" | "%"
    valores: List[float]
    acumulado: float
    promedio: float

@dataclass
class ResumenEjecutivoPyG:
    meses_contrato: int
    valor_total_deal: float
    ingreso_neto_total: float
    costo_total_contrato: float
    contribucion_total: float
    pct_utilidad_promedio: float
    cumple_margen_minimo: bool

@dataclass
class VisionPyG:
    resumen: ResumenEjecutivoPyG
    filas: List[VisionPyGRow]
    meses_contrato: int
    meses_activos: int
```

### Phase PYG-3: Implement `VisionPyGBuilder`

```python
class VisionPyGBuilder:
    """Transforms pyg_por_mes into structured VisionPyG for frontend rendering."""
    
    ROWS = [
        # (key, label, seccion, tipo, signo, attr_name)
        ("rampup", "Factor Ramp-up", "operativo", "linea", "", "rampup"),
        ("ingreso_bruto_a", "Ingreso Cadena A", "ingresos", "linea", "+", "ingreso_bruto_a"),
        ("ingreso_bruto_b", "Ingreso Cadena B", "ingresos", "linea", "+", "ingreso_bruto_b"),
        ("ingreso_bruto_c", "Ingreso Cadena C", "ingresos", "linea", "+", "ingreso_bruto_c"),
        ("ingreso_bruto", "INGRESO BRUTO", "ingresos", "subtotal", "=", "ingreso_bruto"),
        ("contingencia_op", "Contingencia Operativa", "ingresos", "linea", "+", "contingencia_op"),
        ("contingencia_com", "Contingencia Comercial", "ingresos", "linea", "+", "contingencia_com"),
        ("markup_ingreso", "Markup", "ingresos", "linea", "+", "markup_ingreso"),
        ("descuento_ingreso", "Descuento", "ingresos", "linea", "-", "descuento_ingreso"),
        ("ingreso_neto", "INGRESO NETO", "ingresos", "total", "=", "ingreso_neto"),
        
        ("payroll_a", "Nómina Cadena A", "costos_op", "linea", "+", "payroll_a"),
        ("no_payroll_a", "Infraestructura y TI", "costos_op", "linea", "+", "no_payroll_a"),
        ("costo_b", "Cadena B (Digital)", "costos_op", "linea", "+", "costo_b"),
        ("costo_c", "Cadena C (IA)", "costos_op", "linea", "+", "costo_c"),
        ("costo_total", "COSTO OPERATIVO TOTAL", "costos_op", "total", "=", "costo_total"),
        
        ("ica", "ICA", "costos_fin", "linea", "+", "ica"),
        ("gmf", "GMF", "costos_fin", "linea", "+", "gmf"),
        ("polizas", "Pólizas", "costos_fin", "linea", "+", "polizas"),
        ("financiacion", "Financiación", "costos_fin", "linea", "+", "financiacion"),
        ("costos_financieros", "COSTOS FINANCIEROS TOTAL", "costos_fin", "total", "=", "costos_financieros"),
        
        ("contribucion", "CONTRIBUCIÓN", "resultados", "total", "=", "contribucion"),
        ("pct_contribucion", "% Contribución", "resultados", "porcentaje", "%", "pct_contribucion"),
        ("utilidad_neta", "UTILIDAD NETA", "resultados", "total", "=", "utilidad_neta"),
        ("pct_utilidad_neta", "% Utilidad Neta", "resultados", "porcentaje", "%", "pct_utilidad_neta"),
    ]
    
    def construir(self, pyg_por_mes, kpis) -> VisionPyG:
        filas = []
        for key, label, seccion, tipo, signo, attr_name in self.ROWS:
            valores = [getattr(m, attr_name) for m in pyg_por_mes]
            acum = sum(valores)
            activos = [v for i, v in enumerate(valores) if pyg_por_mes[i].ingreso_neto > 0]
            promedio = sum(activos) / len(activos) if activos else 0
            filas.append(VisionPyGRow(key, label, seccion, tipo, signo, valores, acum, promedio))
        ...
```

### Phase PYG-4: Serializer update

Add `vision_pyg` to `pricing_result_to_dict()` and `PricingResult`.

### Phase PYG-5: Contract tests

- Test acumulados correctness (running sums)
- Test VisionPyGRow counts (24 rows expected)
- Test section grouping
- Test labels match expected
- Test promedio = waterfall values (must be consistent)

### Phase PYG-6: Golden fixture for VisionPyG

Extract per-month P&G values from the Excel "Visión P&G" sheet for
the bancamia canonical case. Create `tests/fixtures/excel_v2_4/vision_pyg/bancamia_12m_canonical.json`.

---

## 7. Priority Matrix

| Phase | Effort | Impact | Dependency |
|-------|--------|--------|------------|
| PYG-1 (acumulados) | Small | High | None |
| PYG-2 (VisionPyG model) | Medium | High | None |
| PYG-3 (VisionPyGBuilder) | Medium | High | PYG-2 |
| PYG-4 (serializer) | Small | High | PYG-3 |
| PYG-5 (tests) | Medium | Medium | PYG-1..4 |
| PYG-6 (fixture) | Medium | Medium | Excel access |

### vs VisionTarifas priority:

| Phase | Effort | Impact | Status |
|-------|--------|--------|--------|
| VT-1 (decompose TarifaCanal) | Medium | Critical | READY |
| VT-2 (no_payroll per-channel) | Small | High | READY |
| VT-3 (totals/summary) | Small | High | READY |
| VT-4 (KPIs formula fix) | Small | **Critical** | NEEDS DECISION |
| VT-5 (golden fixture) | Medium | Medium | Needs Excel |
| VT-6 (contract tests) | Medium | Medium | VT-1..5 |

**Recommended execution order:**
1. PYG-1 (acumulados) — quick win, high impact
2. VT-1 + VT-2 + VT-3 (TarifaCanal decomposition) — critical structural fix
3. PYG-2 + PYG-3 + PYG-4 (VisionPyG) — frontend-ready structured output
4. VT-4 (KPIs formula) — requires design decision
5. PYG-5 + VT-6 (tests) — validation layer

---

## 8. Appendix — Full Monthly P&G Data (Golden Fixture)

```
M 1: ramp=0.85  ing_neto=   669,120,976  costo=   680,629,537  contrib=  -11,508,561  (-1.72%)
M 2: ramp=0.92  ing_neto=   723,661,307  costo=   680,099,723  contrib=   43,561,584  ( 6.02%)
M 3: ramp=1.00  ing_neto=   786,588,377  costo=   680,099,723  contrib=  106,488,654  (13.54%)
M 4: ramp=1.00  ing_neto=   786,588,377  costo=   680,099,723  contrib=  106,488,654  (13.54%)
M 5: ramp=1.00  ing_neto=   786,588,377  costo=   680,099,723  contrib=  106,488,654  (13.54%)
M 6: ramp=1.00  ing_neto=   786,588,377  costo=   680,099,723  contrib=  106,488,654  (13.54%)
M 7: ramp=1.00  ing_neto=   786,588,377  costo=   680,099,723  contrib=  106,488,654  (13.54%)
M 8: ramp=1.00  ing_neto=   786,588,377  costo=   680,099,723  contrib=  106,488,654  (13.54%)
M 9: ramp=1.00  ing_neto=   786,588,377  costo=   680,099,723  contrib=  106,488,654  (13.54%)
M10: ramp=1.00  ing_neto=   786,588,377  costo=   680,099,723  contrib=  106,488,654  (13.54%)
M11: ramp=1.00  ing_neto=   786,588,377  costo=   680,099,723  contrib=  106,488,654  (13.54%)
M12: ramp=1.00  ing_neto=   786,588,377  costo=   680,099,723  contrib=  106,488,654  (13.54%)

Acumulados:
  ingreso_neto_total  = 9,258,666,055
  costo_total_contrato = 8,161,726,488
  contribucion_total   = 1,096,939,568
  % utilidad neta      = 11.85%
```
