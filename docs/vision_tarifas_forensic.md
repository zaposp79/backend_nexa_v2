# Vision Tarifas — Forensic Analysis

> Auditoría forense: `vision_tarifas.py` vs Excel "Tarifas_Modelo_Cobro" / VCS staffing_escenarios
>
> Last updated: 2026-05-21

---

## 1. Executive Summary

| Metric | Backend | Excel | Delta | Severity |
|--------|---------|-------|-------|----------|
| VT total costo_atribuible | 723,004,198 | 301,965,089 | **139.4%** | CRITICAL |
| KPIs ingreso_mensual | 419,332,701 | 355,764,509 | **17.9%** | CRITICAL |
| KPIs valor_total_deal | 9,258,666,055 | 5,471,188,699 | **69.2%** | CRITICAL |
| WA payroll_ch | 30,017,217 | 30,017,217 | **0.00%** | EXACT |
| WA no_payroll_override | 6,146,008 | 9,173,542 | **33.0%** | FIXTURE |

**Verdict:** The `VisionTarifasCalculator` has 6 structural gaps vs the Excel.
The PyG pipeline is correct (0% baseline match confirmed), but VisionTarifas re-derives
costs incorrectly by blending Cadena A/B/financieros into a single figure per channel.

---

## 2. Architecture Context

### Current flow
```
VisionTarifasCalculator.calcular(pyg_por_mes)
  for each non-soporte profile:
    perfiles_canal = all profiles with same canal (agent + support)
    op_ch   = _costo_op_canal(payroll_ch + no_payroll_ch)
    fin_ch  = proportional financial costs (op_ch / costo_a_total)
    b_ch    = proportional Cadena B (vol_b_ch / L50)
    costo_ch = op_ch + fin_ch + b_ch            ← BLENDED
    ingreso  = costo_ch / factor_billing
    tarifa_fte = ingreso * pct_fijo / fte
```

### Excel structure (VCS staffing_escenarios + VisionTarifas tab)
```
Per scenario (per profile):
  I138 payroll      = agent salary + support staff salary
  I148 no_payroll   = opex_it + inversiones + costos_fijos  ← ALL 3 components
  I153 cadena_a_total = payroll + no_payroll                ← ONLY Cadena A

Separate sections:
  VT_C40 cts_mensual_cadena_a = sum of all scenarios' cadena_a_total ← aggregated A
  VT_C50 cts_mensual_cadena_b = Cadena B total cost                  ← separate B
  VT_C60 cts_mensual_cadena_c = Cadena C total cost                  ← separate C

Tariff:
  H019 = VT_C40 + VT_C50 + VT_C60                                   ← total cost base
  B019 = H019 / ((1-margen) * (1-op_cont))                          ← ingreso mensual
```

---

## 3. Gap Analysis — 6 Structural Differences

### GAP-1: `no_payroll_mensual` override captures only OPEX_IT (33% delta)

**Root cause:** The `no_payroll_mensual` field on `PerfilCadenaA` is used in VisionTarifas
as the channel's full no-payroll cost. But the fixture values only contain the `opex_ti`
component, missing `inversiones` and `costos_fijos_estacion`.

| Channel | Backend Override | Excel Full No-Payroll | Missing |
|---------|-----------------|----------------------|---------|
| WhatsApp (6 FTE) | 6,146,008 | 9,173,542 | inversiones(431,940) + costos_fijos(2,595,594) |
| Correo (10 FTE) | 67,930,372 | ? | Needs extraction |
| WebChat (10 FTE) | 133,423,682 | ? | Needs extraction |

**Fix:** Either:
- (a) Correct fixture `no_payroll_mensual` to include all 3 no-payroll components, OR
- (b) VisionTarifas should compute no_payroll via `NoPayrollCalculator` per-channel instead of relying on the override

**Recommended:** Option (b) — compute from calculator, aligned with how payroll is computed.

### GAP-2: Blended `costo_atribuible` vs Excel's separated cost structure

**Backend:** Each channel gets a single `costo_atribuible = op_ch + fin_ch + cadena_b_ch`
```
WA:     op_ch=36.2M  + fin_ch=5.9M + b_ch=116.9M  = 159.0M
Correo: op_ch=109.4M + fin_ch=18.0M + b_ch=116.9M = 244.3M
WebChat: op_ch=174.1M + fin_ch=28.6M + b_ch=116.9M = 319.6M
TOTAL:                                              = 723.0M
```

**Excel:** Costs are shown in separate blocks:
```
VT_C40 cts_cadena_a = 42,358,375  ← per-scenario cadena_a costs (payroll + no_payroll)
VT_C50 cts_cadena_b = 259,606,714 ← total cadena B (separate section)
VT_C60 cts_cadena_c = 0           ← total cadena C
TOTAL  H019         = 301,965,089
```

**Impact:** The backend's blended approach makes it impossible for the frontend to
render the Excel's separated cost view. The frontend needs:
1. Per-channel Cadena A cost (payroll + no_payroll)
2. Total Cadena B cost (or per-channel if attributed)
3. Total financial costs
4. Then a combined tariff derivation

**Fix:** Add decomposed fields to `TarifaCanal`:
```python
# New fields for cost decomposition
payroll_ch: float = 0.0           # Payroll del canal (agent + soporte)
no_payroll_ch: float = 0.0        # No-payroll del canal (opex + inv + costos_fijos)
cadena_b_atribuible: float = 0.0  # Cadena B attribution
financieros_atribuible: float = 0.0  # Financial costs attribution
```

### GAP-3: KPIs `ingreso_mensual` formula mismatch (17.9% delta)

**Backend (`KPIsCalculator._calcular_tarifa`):**
```python
costo_promedio_a = sum(m.costo_a for m in pyg_contrato) / n   # ONLY Cadena A = 329.3M
costos_fin = calc_financiero.calcular(costo_promedio_a, mes=1)  # Financial on A only = 26.6M
ingreso_tarifa = (costo_promedio_a + costos_fin.total) / factor_margenes
# = (329.3M + 26.6M) / 0.8488 = 419.3M
```

**Excel (`B019_ingreso_mensual`):**
```
cost_base = VT_C40 + VT_C50 + VT_C60 = 302.0M  # ALL chains included
ingreso   = cost_base / ((1-margen) * (1-op_cont))
# = 302.0M / 0.8488 = 355.8M
```

**Root cause:** Backend tariff uses only Cadena A cost base. Excel uses total cost
(A + B + C) as the tariff base.

**Impact:** 17.9% delta in the primary pricing KPI.

**Fix:** This requires a design decision — the KPIs.ingreso_mensual formula definition
must be aligned with the Excel. The question is whether the backend or the Excel
convention is correct.

### GAP-4: Missing `TarifaCanal` fields vs Excel structure

**Fields in Excel VCS staffing_escenarios NOT in `TarifaCanal`:**

| Excel Field | Description | Backend Status |
|-------------|-------------|----------------|
| `I139_nomina_loaded` | Loaded salary (agent + soporte) | NOT in TarifaCanal |
| `I140_salario_fijo` | Fixed salary component | NOT in TarifaCanal |
| `I141_salario_var` | Variable salary (commissions) | NOT in TarifaCanal |
| `I142_cap_inicial` | Initial training cost | NOT in TarifaCanal |
| `I143_cap_rotacion` | Rotation training cost | NOT in TarifaCanal |
| `I144_examenes` | Medical exams | NOT in TarifaCanal |
| `I145_estudios` | Security studies | NOT in TarifaCanal |
| `I146_crucero` | Cruise delivery | NOT in TarifaCanal |
| `I149_opex_it` | OPEX IT per channel | NOT in TarifaCanal |
| `I150_inversiones` | CapEx per channel | NOT in TarifaCanal |
| `I151_costos_fijos` | Fixed station costs | NOT in TarifaCanal |
| `I158_peso_staff_total` | Total staff weight ratio | NOT in TarifaCanal |
| `I159_peso_staff_sin_agente` | Staff weight excl. agent | NOT in TarifaCanal |
| `I161_staff_cadena_a` | Cadena A staff ratio | NOT in TarifaCanal |
| `I162_staff_cadena_b` | Cadena B staff ratio | NOT in TarifaCanal |
| `I168_nomina_agente_basico` | Base agent salary (no soporte) | NOT in TarifaCanal |

**Impact:** Frontend cannot render the Excel's per-scenario cost breakdown.

### GAP-5: No multi-scenario support (Excel has 3 columns I/J/K)

**Excel:** Shows up to 3 scenarios side-by-side (I=active, J=scenario 2, K=scenario 3):
```
I137 = "Inbound 10"           (WhatsApp, 6 FTE)
J137 = "Inbound 15 personas"  (Correo, 10 FTE)
K137 = "Inbound 20 personas"  (WebChat, 10 FTE)
```

Each scenario column has the full payroll + no_payroll breakdown.

**Backend:** `ResultadoVisionTarifas.canales` is a flat list of `TarifaCanal` objects.
It doesn't have the concept of "active scenario" vs "alternative scenarios."

**Impact:** Frontend can't display the Excel's columnar scenario comparison.

### GAP-6: No totals, subtotals, or per-direction breakdown

**Excel has (from `vision_por_canal_inbound` section):**

| Excel Section | Description | Backend Status |
|---------------|-------------|----------------|
| Row 71 totals | Sum across all inbound channels | NOT computed |
| Cadena B per-direction (H128-K130) | B cost split by inbound/outbound | NOT computed |
| Componente humano/tecnologico split | Inbound B cost decomposed | NOT computed |
| `C200_valor_total_deal` | Total deal value from VisionTarifas perspective | NOT computed |

**Impact:** Frontend can't render totals rows or directional breakdowns.

---

## 4. Per-Channel Validation — Cadena A Payroll

**Good news:** The per-channel payroll computation is EXACT when using `NominaCalculator`:

| Channel | Backend Payroll | Excel Payroll | Delta |
|---------|----------------|---------------|-------|
| WhatsApp (18 profiles) | 30,017,216.53 | 30,017,216.83 | **0.001%** |
| Correo (18 profiles) | 41,476,240.21 | 41,169,528.00* | ~0.7% |
| WebChat (18 profiles) | 40,628,398.43 | 40,151,686.23* | ~1.2% |

*Excel J138/K138 — slight SMMLV-related delta (documented in CTS forensic)

**This confirms:** The NominaCalculator's per-channel filtering works correctly.
The payroll attribution to channels (agent + support staff grouped by canal) is valid.

---

## 5. VisionTarifas _factor_billing Validation

```python
_factor_billing = (1 - margen) × (1 - op_cont) [× (1 - com_cont) if com_cont > 0]
               = (1 - 0.1339) × (1 - 0.02) × 1.0
               = 0.8661 × 0.98
               = 0.848778
```

**Excel:** `B019 / H019 = 355,764,509 / 301,965,089 = 1.17818`
→ `factor = 1 / 1.17818 = 0.84878` — **EXACT MATCH**

The billing factor itself is correct.

---

## 6. `calcular_factor_margenes` vs `_factor_billing` Discrepancy

**`calcular_factor_margenes` (utils.py):**
```python
factor = (1-margen) × (1-op_cont) × (1-com_cont) × (1-markup) × (1+descuento)
       = (1-0.1339) × (1-0.02) × (1-0) × (1-0) × (1+0)
       = 0.848778  # Matches _factor_billing for this fixture
```

**`_factor_billing` (vision_tarifas.py):**
```python
f = (1-margen) × (1-op_cont)
if com_cont > 0: f *= (1-com_cont)
# Does NOT include markup or descuento!
```

**Risk:** When markup > 0 or descuento > 0, these two functions diverge.
The KPIs calculator uses `calcular_factor_margenes` (includes markup/descuento),
while VisionTarifas uses `_factor_billing` (excludes them).

This is potentially intentional (VisionTarifas shows base tariff before markup/discount
adjustments), but needs confirmation against the Excel formula.

---

## 7. Fixture `no_payroll_mensual` Calibration

Current fixture values vs Excel per-scenario no_payroll:

| Profile | Fixture `no_payroll_mensual` | Excel No-Payroll | Fixture Content |
|---------|---------------------------|-----------------|-----------------|
| Inbound 10 (WA) | 6,146,008 | 9,173,542 | = opex_it ONLY |
| Inbound 15 (Correo) | 67,930,372 | ? | Unknown components |
| Inbound 20 (WebChat) | 133,423,682 | ? | Unknown components |

**Excel WA breakdown (I148-I151):**
```
I148_no_payroll    = 9,173,542.22
  I149_opex_it     = 6,146,008.23  ← matches fixture!
  I150_inversiones = 431,939.70
  I151_costos_fijos = 2,595,594.29
```

The fixture's `no_payroll_mensual = 6,146,008` is the OPEX IT component only.
It's missing inversiones (432K) and costos_fijos (2.6M).

However, for Correo and WebChat, the fixture values are much larger:
- Correo: 67.9M — way higher than WA's 6.15M (10 FTE at 0.6 pct_presencia)
- WebChat: 133.4M — even higher (10 FTE at 0.6 pct_presencia)

These large values suggest the Correo/WebChat no_payroll_mensual ALREADY includes
the full NoPayrollCalculator output (not just opex_it), making the discrepancy
WA-specific.

---

## 8. Recommended Fix Plan

### Phase VT-1: Decompose `TarifaCanal` (model enrichment)

Add per-channel cost decomposition fields to `TarifaCanal`:

```python
@dataclass
class TarifaCanal:
    # Existing fields...
    
    # NEW: Cost decomposition (Cadena A)
    payroll_ch: float = 0.0              # NominaCalculator total for channel profiles
    no_payroll_ch: float = 0.0           # NoPayrollCalculator total for channel profiles
    costo_cadena_a_ch: float = 0.0       # payroll_ch + no_payroll_ch
    
    # NEW: Payroll sub-components (Excel I139-I146)
    nomina_loaded_ch: float = 0.0        # I139
    salario_fijo_ch: float = 0.0         # I140
    salario_variable_ch: float = 0.0     # I141
    cap_inicial_ch: float = 0.0          # I142
    cap_rotacion_ch: float = 0.0         # I143
    examenes_ch: float = 0.0             # I144
    estudios_seguridad_ch: float = 0.0   # I145
    crucero_ch: float = 0.0              # I146
    
    # NEW: No-payroll sub-components (Excel I149-I151)
    opex_it_ch: float = 0.0              # I149
    inversiones_ch: float = 0.0          # I150
    costos_fijos_ch: float = 0.0         # I151
    
    # NEW: Attribution (separated)
    cadena_b_atribuible: float = 0.0     # Cadena B cost attributed to this channel
    financieros_atribuible: float = 0.0  # Financial costs attributed to this channel
    
    # NEW: Staff weight ratios (Excel I158-I162)
    peso_staff_total: float = 0.0        # I158
    peso_staff_sin_agente: float = 0.0   # I159
    nomina_agente_basico: float = 0.0    # I168 — base agent salary (no soporte)
```

### Phase VT-2: Compute no_payroll per-channel via calculator

Instead of using `no_payroll_mensual` override, compute per-channel no_payroll
through `NoPayrollCalculator.calcular_para_mes(perfiles_canal, mes)`.

This aligns with how payroll is already computed per-channel.

### Phase VT-3: Add totals and summary to `ResultadoVisionTarifas`

```python
@dataclass
class ResultadoVisionTarifas:
    canales: List[TarifaCanal] = field(default_factory=list)
    
    # NEW: Aggregated totals
    costo_cadena_a_total: float = 0.0     # VT_C40
    costo_cadena_b_total: float = 0.0     # VT_C50
    costo_cadena_c_total: float = 0.0     # VT_C60
    costo_total: float = 0.0              # H019
    ingreso_mensual: float = 0.0          # B019
    valor_total_deal: float = 0.0         # C200
```

### Phase VT-4: Fix KPIs ingreso_mensual formula

Align with Excel — use total cost base (A+B+C), not just costo_a:

```python
# CURRENT (wrong):
costo_promedio_a = sum(m.costo_a for m in pyg_contrato) / n

# CORRECTED:
costo_promedio_total = sum(m.costo_total for m in pyg_contrato) / n
```

**WARNING:** This is a pricing formula change. Must be validated against Excel
before implementation. The 17.9% delta affects tariff calculations.

### Phase VT-5: Golden fixture for VisionTarifas

Create `tests/fixtures/excel_v2_4/vision_tarifas/bancamia_12m_canonical.json` with:
- Per-scenario (per-profile) cost decomposition from Excel
- VT_C40/C50/C60 totals
- B019 ingreso_mensual
- Per-channel tariff values
- Staff weight ratios

### Phase VT-6: Contract tests

Following the CTS forensic methodology:
1. EXACT match tests for payroll per-channel
2. EXACT match tests for _factor_billing
3. Tolerance tests for no_payroll per-channel
4. Structural tests for new decomposed fields
5. Totals consistency tests

---

## 9. Current `TarifaCanal` Fields — Validation Status

| Field | Backend Computation | Excel Equivalent | Status |
|-------|-------------------|-----------------|--------|
| `nombre_canal` | perfil.nombre | I137 scenario name | CORRECT |
| `modalidad` | perfil.modalidad | — | CORRECT |
| `producto` | perfil.canal | — | CORRECT |
| `fte` | perfil.fte | Agent FTE only | CORRECT |
| `vol_mensual` | vol_canal_b(canal) | Channel volume from Cadena B | CORRECT |
| `modelo_cobro` | perfil.modelo_cobro | — | CORRECT |
| `pct_fijo` | perfil.pct_fijo | — | CORRECT |
| `pct_variable` | 1 - pct_fijo | — | CORRECT |
| `componente_fijo` | _componentes_label() | — | CORRECT |
| `componente_variable` | _componentes_label() | — | CORRECT |
| `costo_atribuible` | op_ch + fin_ch + b_ch | **BLENDED** — not in Excel | STRUCTURAL GAP |
| `ingreso_bruto` | costo_ch / factor_billing | B019 / n_canales | FORMULA DIFFERS |
| `facturacion` | ingreso × pct_fijo | — | DEPENDS ON ABOVE |
| `tarifa_fijo_fte` | facturacion / fte | — | DEPENDS ON ABOVE |
| `tarifa_variable` | (ingreso × pct_var) / vol | — | DEPENDS ON ABOVE |
| `vol_minimo_transaccion` | costo_var / tarifa_var | — | DEPENDS ON ABOVE |

---

## 10. Comparison with CTS Forensic Results

The CTS forensic showed 12 EXACT, 3 NEAR, 5 DOCUMENTED fields. VisionTarifas is in
much worse shape because it has **structural** gaps, not just calibration deltas:

| Dimension | CTS | Vision Tarifas |
|-----------|-----|---------------|
| Denominators | EXACT (K50, L50) | N/A (VT has no denominators) |
| Per-channel payroll | — | EXACT (30M WA match) |
| Per-channel no_payroll | — | FIXTURE GAP (33% on WA) |
| Cost decomposition | 13 sub-fields | NOT IMPLEMENTED |
| Total aggregations | 5 fields | NOT IMPLEMENTED |
| Tariff formula | — | FORMULA MISMATCH (17.9%) |
| Multi-scenario | — | NOT IMPLEMENTED |
| Factor billing | — | EXACT (0.848778) |

**CTS was a calibration exercise. VisionTarifas requires structural redesign.**

---

## 11. Appendix — Raw Backend Output (Golden Fixture)

```
Canal: Inbound 10
  mod=Inbound prod=WhatsApp fte=6.0
  modelo=Fijo FTE pct_fijo=1.0
  costo_atr=159,059,882.52
  ingreso=187,398,686.72
  facturacion=187,398,686.72
  tarifa_fte=31,233,114.45

Canal: Inbound 15 personas
  mod=Inbound prod=Correo fte=10.0
  modelo=Fijo FTE pct_fijo=1.0
  costo_atr=244,338,296.11
  ingreso=287,870,675.38
  facturacion=287,870,675.38
  tarifa_fte=28,787,067.54

Canal: Inbound 20 personas
  mod=Inbound prod=WebChat fte=10.0
  modelo=Fijo FTE pct_fijo=1.0
  costo_atr=319,606,019.48
  ingreso=376,548,425.47
  facturacion=376,548,425.47
  tarifa_fte=37,654,842.55
```

### PyG Mes 2 (cruising month):
```
payroll_a      = 112,121,855.17
no_payroll_a   = 217,114,432.99
costo_a        = 329,236,288.16
costo_b        = 350,863,434.66
costo_total    = 680,099,722.82
cos_financieros = 55,031,033.51
```

### Excel VCS Economics:
```
B019_ingreso_mensual    = 355,764,509.40
H019_cts_mensual_total  = 301,965,088.76
VT_C40_cadena_a         = 42,358,375.19
VT_C50_cadena_b         = 259,606,713.58
```
