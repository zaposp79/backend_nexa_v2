# F4 — Financial Layer Audit (Audit-Only Pass)

> **Status**: Audit-only deliverable. NO code, tests, parametrization, or oracle were modified.
> Date: 2026-05-28. Branch: `refactor/engine-v2`.
> Source of truth: `~/Downloads/Nexa - Pricing - Simulador - V2-7.xlsx`.
> Evidence extracted with `openpyxl(data_only=False)` (formulas) AND `data_only=True` (cached values).

This dossier maps every cell of the Visión P&G financial block (rows 65-70) back to its
master formulas in `Pólizas - Costo Financiacion`, contrasts against the backend
implementation in `calculators/costos_financieros.py` + `domain/financial/calculators.py`,
and proposes (without executing) the surgical changes required to close F4 sub-waves.

---

## 0. EXECUTIVE FINDING — THE ORACLE MESH IS MIS-LABELED

> **This is the single most important finding of the audit.**

`tests/parity/oracle_mesh_mapping.py` labels the rows 65-70 of `Visión P&G` as follows
(checkpoints `pyg.polizas`, `pyg.ica`, `pyg.gmf`, `pyg.financiacion`):

| Mesh checkpoint | Mesh assumes cell | ACTUAL Excel label (B-col) | ACTUAL formula source |
|---|---|---|---|
| `pyg.polizas.contractMx` | row **65** | "**Componente Financiero**" (TOTAL = SUM(C66:C70)) | `=SUM(C66:C70)` |
| `pyg.ica.contractMx` | row **66** | "**ICA**" | `SUMPRODUCT('Pólizas - Costo Financiacion'!J$12:J$83 × …)` |
| `pyg.gmf.contractMx` | row **67** | "**GMF**" | `SUMPRODUCT('Pólizas - Costo Financiacion'!J$93:J$163 × …)` |
| `pyg.financiacion.contractMx` | row **68** | "**Comisión de Administración (1.18%)**" | `SUMPRODUCT('Pólizas - Costo Financiacion'!J$223:J$241+J$281:J$299+J$333:J$351)` |
| (not mapped) | row **69** | "**Pólizas adicionales**" | `SUMPRODUCT('Pólizas - Costo Financiacion'!J$12:J$163+J$198:J$327)` |
| (not mapped) | row **70** | "**Costos Financieros**" (capital charge) | `SUMPRODUCT('Pólizas - Costo Financiacion'!J$378:J$456)` |

**Consequences for the DRIFT_HEATMAP**:
- Backend `pyg.polizas` = `result.pyg_por_mes[i].polizas` is being compared against
  Excel's **Componente Financiero TOTAL** (ICA+GMF+Comisión+Pólizas+Financ.). The
  100% drift is inevitable: row 65 = 158M COP, backend exposes only the "polizas"
  sub-line ≈ 0.
- Backend `pyg.financiacion` is being compared against Excel **Comisión Administración 1.18%**
  (≈53.7M COP). Two completely different concepts.
- Backend `pyg.gmf=689,131` vs Excel `H67=10,318,771`: drift 93.32%. This IS GMF vs
  GMF — the gap is real (see Section 2).
- Backend `pyg.ica=4,287,447` vs Excel `H66=32,239,879`: drift 86.70%. ICA vs ICA — real (see Section 1).

**Honest implication**: any F4 implementation that closes oracle drift on
`COSTOS_FINANCIEROS` requires fixing **BOTH** the backend financial math AND fixing
the oracle mesh mapping. As of today the mesh mis-attributes ~50% of the 28
checkpoints. F4 must produce a correction PR for `oracle_mesh_mapping.py` as well.

This is a hack-class finding per the W16 rules and must be tracked.

---

## 1. ICA (Gross-up + city table)

### 1.1 Excel formula (`data_only=False`)

`Visión P&G!H66`  (array formula, 12 columns C..N covering 12 calendar months):
```
=IFERROR(SUMPRODUCT(
   'Pólizas - Costo Financiacion'!J$12:J$83
   * ('Pólizas - Costo Financiacion'!$B$12:$B$83 = "Activado")
 ),0)
```

H66 → Pólizas!**J**$12:J$83 (`J` = mes col 6 of that sheet, which is **calendar M6 = contract M1**).
I66 → `K`$12:K$83 (calendar M7 / contract M2). N66 → `P`$12:P$83 (calendar M12 / contract M7).

The summed column (`J12..J83`) contains **per channel/cadena** ICA per row. The per-row formula at `Pólizas - Costo Financiacion!E12` (channel 1, Cadena A, month 1) is:

```
= IF('Costos Totales'!E$8 <= ('Panel de Control General'!$C$11 + 'Nomina Loaded'!$C$3 - 1),
     ( ( 'Costos Totales'!E37
         / ( (1-'Panel de Control General'!$C$63)
           * (1-'Panel de Control General'!$C$67)
           * (1-'Panel de Control General'!$C$68)
           * (1-'Panel de Control General'!$C$69)
           * (1+'Panel de Control General'!$C$70)
         )
       )
       + E198          ← Pólizas adicionales del canal/cadena en el mes
       + E378          ← Costo financiación del canal/cadena en el mes
     ) * 'Panel de Control General'!$C$34,
     0)
```

Cell value (cached): `H66 = 32,239,879.67`.

### 1.2 Formula interpreted (math)

For each (cadena, canal, mes) row that is "Activado":

```
ICA_row = ( costo_row / factor_margenes
          + polizas_adicionales_row
          + costo_financiacion_row
          ) × tasa_ica
```

where:
```
factor_margenes = (1 - margen_A)·(1 - op_cont)·(1 - com_cont)·(1 - markup)·(1 + descuento)
                = (1 - C63)(1 - C67)(1 - C68)(1 - C69)(1 + C70)
```
and `tasa_ica = Panel!C34 = 0.01` (manually overridable single scalar).

**ICA is gross-up**: the base is `costo / factor_margenes` (= ingreso bruto equivalente),
NOT just `costo`. The classical `base × tasa / (1 - tasa)` gross-up identity is
**not** what Excel uses. Excel uses `base = ingreso_bruto_equivalente` directly.

ICA is then summed across all activated rows for the month (cadena A + B + C + every channel).

### 1.3 ICA tasa source — single scalar from Panel

| Source | Value | Notes |
|---|---|---|
| Excel `Panel!C34` | **0.01** (1%) | manual scalar input |
| Excel `Tasas, TRM, Polizas!B29` | **0.01966** | "reference" — not used by P&G |
| Excel `Tasas, TRM, Polizas!F35..F54` | per-city sum (B+C+D+E) | NOT consumed by P&G row 66 |
| Backend `tasa_ica` | comes from `FinancialParametrizationRepository.get_ica(ciudad)` | which reads `op.json:ica.ciudad=Bogota, ica=Tarifa → 0.00966` then transforms |
| Backend actual at runtime | `0.0197` (per DRIFT_HEATMAP row `panel.tasa_ica`) | Bogotá's "ICA" total (Tarifa + S.Bomberil) |
| Drift | 0.01 vs 0.0197 = **+97%** | |

**Excel does NOT consume the per-city ICA matrix in `Tasas, TRM, Polizas!A34:F54` for the P&G calculation.** It only consumes the manual scalar at `Panel!C34=1%`. Backend instead routes through a Bogotá lookup that returns 1.966%, then would re-apply via OP-Poliza rate of 1.966%. This explains:

- mesh `panel.tasa_ica` drift: 96.60% (backend 0.0197 vs Excel 0.01).
- mesh `pyg.ica` drift: 86.70%.

The remaining gap after fixing `tasa_ica` (1.966% → 1.0% would already over-correct…) is structural: the backend also computes ICA on `costo_a` only (not summing pólizas adicionales + costo financiación inside the bracket), AND aggregates over a single deal-level value rather than per (cadena×canal×mes) row.

### 1.4 Backend implementation

File: `calculators/costos_financieros.py:241-255` + `domain/financial/calculators.py:51-68`.

```python
def _calcular_ica(self, costo_operativo, polizas, financiacion, factor_margenes):
    base_ingreso_neto = (
        (costo_operativo / factor_margenes)
        + polizas
        + financiacion
    )
    return base_ingreso_neto * self._panel.tasa_ica
```

The **shape** of the formula matches Excel structurally (cost/margenes + polizas + fin) × tasa_ica.
The **discrepancies** are:

| Aspect | Excel | Backend | Delta |
|---|---|---|---|
| `tasa_ica` source | `Panel!C34` (manual scalar = 0.01) | `op.json:ica` lookup by ciudad (= 0.01966) | Backend reads a different sheet entirely |
| Base scope | per (canal × cadena × mes) row, then SUMPRODUCT | single aggregate `costo_operativo` (= A+B+C) for the deal | Different granularity |
| `polizas` argument | `polizas_adicionales` only (NOT Comisión Admin) | `tasa_polizas × (costo+fin)/factor_margenes` — different formula chain | Different polizas semantics |
| `financiacion` argument | `costo_financiacion` per channel from Pólizas!E378 etc. | single scalar `tasa_mensual × período × costo_op` (or 0) | Different formula |
| `factor_margenes` definition | `(1-C63)·(1-C67)·(1-C68)·(1-C69)·(1+C70)` (5 terms) | identical in `utils.calcular_factor_margenes` | Match (subject to inputs) |

### 1.5 Delta hypothesis explaining 86.70%

1. Backend uses ICA = 1.966% — almost 2× the 1.0% that Excel uses (factor 1.966).
2. Excel multiplies by (cost+polizas+financiacion+commission_admin) which is ~1.46B
   per month aggregated; backend multiplies by ~218M (no Cadena C contribution).
   Ratio ≈ 1/6.7.
3. Combined factor: 1.966 × (1/6.7) ≈ 0.293 → expected backend ≈ 0.293 × 32.24M ≈ 9.45M;
   observed 4.29M. Remaining gap = lack of pólizas adicionales + costo financiación in
   the bracket (Excel has +61.7M+0 inside the bracket, backend has +0+0).

### 1.6 Fix proposal (NOT IMPLEMENTED)

Required changes in `domain/financial/calculators.py::calcular_ica` and the orchestrator:

1. **Tasa source**: `tasa_ica` must come from `Panel!C34` (a user-entered scalar that
   overrides the per-city lookup), not from `op.json:ica`. The per-city ICA matrix in
   `Tasas, TRM, Polizas!A34:F54` is **not consumed** by the P&G calculation. Storage
   should mirror that — the `panel.tasa_ica` extractor must return Panel C34's raw value.
2. **Base granularity**: ICA must be computed **per row of `Pólizas - Costo Financiacion`**
   (one per cadena × canal), then summed. That requires the engine to expose `costo_a/b/c` AND
   `costo_per_canal` for each month — today only an aggregate is exposed.
3. **Pólizas inside bracket**: `polizas` here means **only "Pólizas adicionales"
   (row 69, Pólizas!E198..) — NOT the Comisión Admin**. The two must be tracked separately.
4. **Costo financiación in bracket**: `financiacion` must be the capital-charge per channel
   (E378, see Section 5), not the placeholder `0.0` returned today.
5. **Aggregation timing**: ICA per row × SUM at the end, never aggregate-then-multiply
   (which we accidentally do today).

Tests to add: oracle mesh checkpoints `pyg.ica.contractM1..M7` (already exist, drift 86.7%).
After fix, they must converge to 0.00%.

---

## 2. GMF

### 2.1 Excel formula

`Visión P&G!H67`:
```
=IFERROR(SUMPRODUCT(
   'Pólizas - Costo Financiacion'!J$93:J$163
   * ('Pólizas - Costo Financiacion'!$B$93:$B$163 = "Activado")
 ),0)
```

The per-row formula at `Pólizas - Costo Financiacion!E93` matches the ICA per-row
structure exactly (gross-up formula reused), except the multiplying rate is `Panel!$C$35`
(GMF) instead of `Panel!$C$34` (ICA). The cell `C35` itself is a FILTER lookup against
`Tasas, TRM, Polizas!$B$21:$B$31` → row `B30=0.004`.

```
GMF_row = ( costo_row/factor_margenes + polizas_adic_row + costo_financ_row ) × Panel!C35
        = ( costo_row/factor_margenes + polizas_adic_row + costo_financ_row ) × 0.004
```

Cell value: `H67 = 10,318,771.70`.

### 2.2 Tasa GMF

| Source | Value |
|---|---|
| `Tasas, TRM, Polizas!B30` | **0.004** (4×1000) |
| `Panel!C35` | filters B30 → **0.004** |
| `op.json:poliza="GMF"` | **0.004** (matches) |
| Backend `panel.tasa_gmf` | **0.004** (PASS in oracle mesh) |
| Drift in rate | 0% |

### 2.3 Backend implementation

`calculators/costos_financieros.py:257-265`:
```python
def _calcular_gmf(self, costo_operativo, polizas, financiacion):
    return (costo_operativo + polizas + financiacion) * self._panel.tasa_gmf
```

`domain/financial/calculators.py:71-83` identical.

### 2.4 Delta hypothesis (93.32%)

The **rate is correct** (0.004 = 0.004). The drift is entirely in the **base**:

| Element | Excel | Backend |
|---|---|---|
| Base structure | `costo / factor_margenes + polizas_adic + costo_financ` | `costo + polizas + financiacion` |
| Gross-up | **YES** (`/factor_margenes`) | **NO** (backend GMF is flat — no gross-up) |
| Costo scope | per (canal × cadena × mes) row, summed | aggregate (only Cadena A in practice) |
| Pólizas | "Pólizas adicionales" line only | tasa_polizas × (costo+fin) / factor_margenes (different semantics) |
| Financiación | per-channel capital charge | 0 in current run |

Quick numerical check: backend GMF = 689,131 / 0.004 = 172.28M base → matches
`pyg.costo_total = 172.28M` (i.e., just Cadena A no gross-up). Excel GMF base
= 10.32M / 0.004 = 2.58B per month, which is ~1.5B cost grossed up + 61.7M polizas
+ ~53M comm adm + Cadena C contributions. Bases differ by factor ≈ 15×.

### 2.5 Fix proposal (NOT IMPLEMENTED)

Backend must apply gross-up to GMF base, identical to ICA. Both formulas share the
same per-row computation in Excel — the only difference is the multiplying rate at
the end. After ICA fix (Section 1), GMF reduces to the same orchestration with `tasa_gmf`
instead of `tasa_ica`.

Code change site: `domain/financial/calculators.py::calcular_gmf` (currently flat).
Once `calcular_ica` is refactored to per-row, `calcular_gmf` can delegate to the same helper.

---

## 3. Pólizas Adicionales (SUMPRODUCT vector)

> **Naming clarification**: Excel `Visión P&G!H69` is labeled "Pólizas adicionales".
> Mesh oracle DOES NOT currently map this cell (it incorrectly maps `pyg.polizas` to
> row 65 = total Componente Financiero). Excel H65 = SUM(H66:H70).

### 3.1 Excel formula

`Visión P&G!H69`:
```
=IFERROR(
   SUMPRODUCT('Pólizas - Costo Financiacion'!J12:J163 *
              ('Pólizas - Costo Financiacion'!$B$12:$B$163="Activado"))
 + SUMPRODUCT('Pólizas - Costo Financiacion'!J198:J327 *
              ('Pólizas - Costo Financiacion'!$B$198:$B$327="Activado"))
 , 0)
```

Hmm — this formula re-uses the **same** J12:J163 range that H66 (ICA) uses. That means
"Pólizas adicionales" at H69 = ICA range + (rows 198-327, which IS the pólizas block).
This looks like a bug in Excel or a deliberate "total tax + polizas" double-count.
**Documenting as an ambiguity to resolve before implementing F4.C.**

The actual pólizas-only block lives at rows **198-327** of `Pólizas - Costo Financiacion`.
The per-row formula at `E198`:

```
= LET(
    umbral,    Panel!$C$11 + 'Nomina Loaded'!$C$3,        ← contract length + offset
    margenes,  (1-C63)·(1-C67)·(1-C68)·(1-C69)·(1+C70),    ← factor_margenes
    base_costo,
       IF(E$196 < umbral,
          'Costos Totales'!E37 + E378,                     ← costo del mes + costo financiacion del mes
          FILTER('Costos Totales'!$E37:$BL37, … = umbral-1)
          + FILTER($E378:$BL378, … = umbral-1)),            ← último mes activo (cliff convention)
    SUMPRODUCT($D$173:$D$185 *      ← % de póliza
               $E$173:$E$185 *      ← % atribuible
               ($G$173:$G$185 >= E$196))  ← duración mes
    * base_costo / margenes
)
```

### 3.2 Pólizas master matrix (extracted)

`Pólizas - Costo Financiacion!C173:G185` (Cadena A polizas master):

| Row | Póliza (C) | D=tasa | E=atribución | F=¿extiende? | G=duración (meses) |
|---|---|---:|---:|---:|---:|
| 173 | Póliza de Cumplimiento | 0.0062 | 0.20 | TRUE | 20 |
| 174 | Poliza de Salarios | 0.0119 | 0.10 | TRUE | 41 |
| 175 | Poliza de Calidad | 0.0119 | 0.20 | TRUE | 20 |
| 176-185 | (empty) | 0 | 0 | 0 | 17 (default) |

Effective rate for any month ≤ 20:
`0.0062×0.20 + 0.0119×0.10 + 0.0119×0.20 = 0.00124 + 0.00119 + 0.00238 = 0.00481`.

Por-mes la fórmula = `0.00481 × base_costo / factor_margenes`.

### 3.3 Comisiones master matrix (row 188 only)

`Pólizas - Costo Financiacion!C188:G188`:

| Pólizá (C) | D=tasa | E=atribución | F=¿extiende? | G=duración |
|---|---:|---:|---:|---:|
| Comisión de Administración 1.18% | **0.016756** | **1.0** | FALSE | 17 |

Note: `0.016756` is **not** 0.0118 — it's the Excel-stored rate including downstream
gross-ups already pre-baked (cell formula uses `Panel!G45`, which receives a stored
factor that we did NOT trace deeper here — flagging as **AMBIGUITY**). Effective rate
multiplier is `0.016756 × 1.0 = 0.016756`, applied to `base_costo / factor_margenes`.

### 3.4 Backend implementation

`calculators/costos_financieros.py::_calcular_polizas` (lines 227-239):

```python
def _calcular_polizas(self, costo_operativo, financiacion, tasa_polizas, factor_margenes):
    return tasa_polizas * (costo_operativo + financiacion) / factor_margenes
```

And `tasa_polizas` is computed by `FinancialParametrizationRepository.get_effective_policy_rate(mes)`
which iterates `op.json:poliza` rows with `aplica=True` and `mes_desde ≤ mes`. **As of
today none of the 11 rows in op.json:poliza has `aplica=True`** — so backend returns 0.0.
That's why `pyg.polizas` extractor returns 0.0 in the mesh.

Furthermore, `tasa_polizas` is summed with the same value across **all three cadenas**,
even though Excel maintains separate Cadena A / B / C policy matrices (rows 173-185, 226-238, 280-302).

### 3.5 Delta + fix proposal

1. **Activation flags missing**: `op.json:poliza` rows lack the `aplica` field — port
   the activation logic from `Panel de Control!M17` ("Aplica pólizas?" TRUE) plus
   the cadena-specific Activado flag (`Pólizas!B173`).
2. **Per-cadena polizas matrices missing**: storage must hold three matrices (A, B, C),
   each with the `tasa × atribución × duración` triplets per póliza. Today's
   `op.json:poliza` is a flat list with no cadena, no atribución, no duración.
3. **Per-mes cliff behavior** (the `umbral-1` FILTER): when month > contract length,
   freeze the cost base at the last contract month. Backend doesn't implement this.
4. **Gross-up on polizas** (`base_costo / factor_margenes`): backend does this correctly.
5. **mes_inicio**: when does each póliza kick in? Excel uses `G173` (duración) +
   `D169 = SUM('Listas Desplegables'!$A$51:$BH$51)` = 6 (mes inicio cliff). The
   póliza is active in mes m if `G_row ≥ E$196 (= mes_actual)`. Backend uses
   `mes_desde ≤ mes` which is the **inverse** condition.

Code change sites:
- `repositories/financial_parametrization_repository.py::get_effective_policy_rate` (refactor)
- `storage/parametrization/v2-7/op.json` must carry per-cadena × per-poliza × per-attr rows
- `domain/financial/calculators.py::calcular_polizas` (signature change — needs cadena scope)

Tests to add: 7 new oracle checkpoints `pyg.polizas_adic.contractM1..M7` against
Excel `H69..N69` (= 61,730,314 mes 1, 61,703,887 mes 2+). Today not in the mesh.

---

## 4. Comisión Administración 1.18%

### 4.1 Excel formula

`Visión P&G!H68` (currently labeled "Comisión de Administración (1.18% sobre ventas Gcomercial-Operaciones)"):

```
=IFERROR(
   SUMPRODUCT('Pólizas - Costo Financiacion'!J$223:J$241 ×
              ('Pólizas - Costo Financiacion'!$B$223:$B$241 = "Activado"))
 + SUMPRODUCT('Pólizas - Costo Financiacion'!J$281:J$299 ×
              ('Pólizas - Costo Financiacion'!$B$281:$B$299 = "Activado"))
 + SUMPRODUCT('Pólizas - Costo Financiacion'!J$333:J$351 ×
              ('Pólizas - Costo Financiacion'!$B$333:$B$351 = "Activado"))
 , 0)
```

Three SUMPRODUCT blocks = Cadena A (223-241), Cadena B (281-299), Cadena C (333-351).
Per-row formula at `E223`:

```
= LET( umbral, …,
       margenes, (1-C63)(1-C67)(1-C68)(1-C69)(1+C70),
       base_costo, IF( … same cliff-bracketing as polizas above),
       SUMPRODUCT($D$188 * $E$188 * ($G$188 >= E$196))
         × base_costo / margenes )
```

`D$188 = 0.016756, E$188 = 1.0, G$188 = 17`. So:
```
Comisión_row = 0.016756 × base_costo / factor_margenes  (for mes ≤ 17)
```

Cell value: `H68 = 53,762,544.54`.

### 4.2 Tasa source

Per Excel `Pólizas - Costo Financiacion!D188 = 0.016756`. This is **stored**, not derived
from `Panel!D45 = 0.0118`. The Excel-internal mapping `0.0118 → 0.016756` factor =
`0.0118 × 1.42 ≈ 0.016756`. We could not trace the 1.42 multiplier (gross-up of some
sort against `factor_margenes` reciprocal). **AMBIGUITY — to be resolved in F4.D**.

The `Panel!D45=0.0118` value is human-readable; the stored 0.016756 in `D188` is what
Excel actually consumes. Backend's `tasa_comision_administracion` should match D188's
stored value, not Panel D45.

### 4.3 Backend implementation

`calculators/costos_financieros.py::_calcular_comision_administracion` (lines 267-290):

```python
def _calcular_comision_administracion(self, costo_a, factor_margenes):
    if self._panel.tasa_comision_administracion <= 0:
        return 0.0
    ingreso_bruto_a = costo_a / factor_margenes
    result = ingreso_bruto_a * self._panel.tasa_comision_administracion
    return cop_round(result)
```

Shape is correct (`costo / factor_margenes × tasa`). The two gaps:

1. Backend computes commission **only on Cadena A** (per the W18 BUG-1 fix comment).
   Excel sums Cadena A + B + C (each with its own row at D188 / D? for B / D? for C —
   we did NOT confirm whether B and C have non-zero commission rates).
2. Backend reads `panel.tasa_comision_administracion`. DRIFT_HEATMAP shows
   `panel.com_cont=0.0` (which is a different field — contingencia comercial).
   The value of `tasa_comision_administracion` in the request fixture is currently
   `0.0` (per W18 audit), making the backend output exactly 0 for this line.

### 4.4 Delta + fix proposal

1. Set `tasa_comision_administracion` source to `Pólizas - Costo Financiacion!D188`
   (= 0.016756) NOT `Panel!D45` (= 0.0118). Document the 0.0118 → 0.016756 factor
   resolution as part of F4.D scope.
2. Sum commission contributions from Cadena A + Cadena B + Cadena C (each with their
   own commission row at `D188` analog in their respective master section).
3. The cliff-bracketing behavior (umbral-1 FILTER) must be ported.

Tests to add: 7 oracle checkpoints `pyg.comision_admin.contractM1..M7` against Excel
`H68..N68` (= 53,762,544 mes 1, 53,749,817 mes 2+). Today the mesh INCORRECTLY maps
this cell as `pyg.financiacion`. The mesh mapping must be fixed too.

---

## 5. Costos Financieros (Capital Charge)

### 5.1 Excel formula

`Visión P&G!H70`:
```
=IFERROR(
   SUMPRODUCT('Pólizas - Costo Financiacion'!J378:J456 *
              ('Pólizas - Costo Financiacion'!$B$378:$B$456 = "Activado"))
 , 0)
```

Per-row at `F378` (note: E378 is hardcoded `0`, financiación arranca en F = mes 2):

```
F378 = E$370 × $D$366 × SUMIFS('Costos Totales'!E$10:E$33,
                                'Costos Totales'!$D$10:$D$33, $D378,
                                'Costos Totales'!$C$10:$C$33, $C378)
```

where:
- `D$366 = Panel!L10 = 0.0153` (tasa mensual de financiación)
- `E$370 = IF(E368 < $D$365, E368, $D$365)` — meses transcurridos cappeados al período
  de pago ($D$365 = factor de aumento, depende de Panel!C21 = "No" → returns 0)
- The SUMIFS picks the previous month's cost for that (canal, cadena) row.

**Critical**: with `Panel!C21 = "No"` (no aplica financiación), `D365 = 0`, so
`E370 = MIN(E368, 0) = 0` for all months. **Excel financiación = 0 in this run**.

Cell value (cached): `H70 = 0` (consistent — financiación not activated for V2-7
pre-loaded scenario).

### 5.2 Backend implementation

`calculators/costos_financieros.py::_calcular_financiacion` (215-225):

```python
def _calcular_financiacion(self, costo_operativo, factor_periodo):
    if not self._panel.activa_financiacion:
        return 0.0
    return factor_periodo * self._panel.tasa_mensual_financ * costo_operativo
```

Shape matches Excel (period × rate × cost). With `activa_financiacion=False` (default),
returns 0. Backend currently returns 0; Excel currently returns 0. **No drift**
for this scenario.

### 5.3 Delta + fix proposal

Conceptually aligned — no immediate fix needed for the V2-7 pre-loaded scenario. But
when `activa_financiacion=True`:

1. Backend uses `costo_operativo_mes_anterior` (correct — Excel uses E$10:E$33 for
   previous month).
2. Excel applies per-row at (canal × cadena), backend at aggregate.
3. The `factor_periodo` from `Panel!D365` is conditioned on `Panel!C21="Si"`, AND
   on the period (30/60/90/120 → 1/2/3/4 meses). Backend reads `panel.periodo_pago`
   directly without checking the activation flag at the period level (separate from
   `activa_financiacion`). This is a latent bug for non-V2-7 scenarios.

Tests to add (when scenario `activa_financiacion=True`): 7 oracle checkpoints
`pyg.costo_financiero.contractM1..M7` against `H70..N70`. NOT in current mesh.

For the V2-7 baseline scenario, the only required action is: the **oracle mesh
`pyg.financiacion` checkpoint must be re-pointed from H68 (Comisión Admin) to H70
(Costo Financiero)**.

---

## 6. No-Payroll Components (rows 41-44)

### 6.1 Excel formula

`Visión P&G!H41 = SUM(H42:H44)`:

| Row | Label | Formula | Source block |
|---|---|---|---|
| 42 | OPEX Fijo | `=IFERROR(SUMPRODUCT('No payroll'!I107:I125*('No payroll'!$A$107:$A$125="Activado")),0)` | Salarios soporte block |
| 43 | Inversiones | `=IFERROR(SUMPRODUCT('No payroll'!I186:I204*('No payroll'!$A$186:$A$204="Activado")),0)` | Costos one-shot (capex) |
| 44 | Costos Fijos | `=IFERROR(SUMPRODUCT('No payroll'!I248:I266*('No payroll'!$A$248:$A$266="Activado")),0)` | Costos infraestructura recurrentes |

Column mapping for `No payroll` sheet: `I = mes 6 calendar = contract mes 1`.

Cell values per month (cached):
- H42 OPEX Fijo: 19,476,084.60 / m (constant)
- H43 Inversiones: 3,251,906.12 (mes 1), 2,651,867.34 (mes 2+) — has capex_inicial cliff
- H44 Costos Fijos: 11,827,569.49 / m (constant)
- H41 TOTAL: 34,555,560.21 (mes 1), 33,955,521.43 (mes 2+)

### 6.2 Backend implementation

`calculators/no_payroll.py::NoPayrollCalculator.calcular_para_mes` returns:
```python
ResultadoNoPayroll(opex_ti, capex, costos_fijos)
```

with:
- `opex_ti = Σ no_payroll_mensual` (per-canal override) or `opex_ti_por_estacion × estaciones_infra`
- `capex = capex_por_estacion × estaciones_capex + (capex_inicial_por_estacion × estaciones_capex if mes==1)`
- `costos_fijos = (arriendo + energia + vigilancia + aseo + otros) × estaciones_infra`

Backend mesh result: `H41 backend = 11,017,864.66` vs Excel = 34,555,560.21 → drift 68.12%.

### 6.3 Delta hypothesis

Backend opex_ti is sourcing from per-perfil override (`no_payroll_mensual`) which is
likely a single 11M value, when Excel aggregates ALL channels with their `Activado`
flag from `Panel!K19:K25` + `M19:M25`. We did NOT enumerate the 19 rows of each
section in this audit (rows 107-125 etc.) — that's F4.F scope.

The `Inversiones` cliff (3.25M mes 1 vs 2.65M mes 2+) is consistent with a one-shot
capex of 600K spread on mes 1. Backend doesn't currently expose this distinction in
the result (capex includes both initial and recurrent in `capex`).

### 6.4 Fix proposal

1. **OPEX Fijo (row 42)**: source must be the full activation matrix of "salarios de
   soporte" canales × cadenas × tarifas in `No payroll` sheet rows 107-125. Backend's
   `_opex_overrides_por_canal` sums only perfiles with `no_payroll_mensual > 0` and
   `es_soporte=False` — this is structurally different.
2. **Inversiones (row 43)**: Excel reads block 186-204. Mapping each row to a backend
   `capex_*_por_estacion` param requires storage extension (currently no parametrization
   ties `Inversiones` to `Pólizas - Costo Financiacion` D169 mes_inicio = 6 logic).
3. **Costos Fijos (row 44)**: block 248-266. The activator flag and "Activado" string
   pattern must be ported. Currently backend constants_per_estacion are flat (no per-canal
   override).

Tests: 7 new oracle checkpoints per row (42, 43, 44 = 21 new checkpoints) or 7
aggregate at row 41 (already in mesh).

---

## 7. Resumen Prioritario

| Componente | Drift mesh | Causa raíz dominante | Esfuerzo | Impacto oracle (tests cerrados) | Sub-wave |
|---|---:|---|---|---:|---|
| ICA | 86.70% | tasa source (1.97%→1.0%) + base scope per-row vs aggregate + missing polizas/financ. in bracket | **M** | 7 PYG-66 + downstream COSTO_FIN | F4.A |
| GMF | 93.32% | missing gross-up + base scope per-row + missing polizas/financ. | **S** (delegates to ICA fix) | 7 PYG-67 | F4.B |
| Pólizas adicionales | 100% (NOT mapped) | storage lacks per-cadena × per-poliza tasa/atrib/duración matrix; aplica flag missing | **L** | 7 PYG-69 + indirect bracket fix for ICA/GMF | F4.C |
| Comisión Admin 1.18% | 100% (mis-labeled as `pyg.financiacion`) | tasa source 0.0 in fixture + storage missing D188=0.016756 + only cadena A computed | **S** | 7 PYG-68 | F4.D |
| Costo Financiación | (0% — both side at 0) | scenario-dependent (activa_financiacion=False) | **M** (preventive) | 7 PYG-70 (latent) | F4.E |
| No-Payroll | 67.55% | sourcing mismatch (per-canal Activado matrix vs per-perfil overrides) | **L** | 7 PYG-41 | F4.F |
| **Oracle mesh re-labeling** | (root H67/H68/H69 mis-mapped) | mesh wrongly maps rows 65/68 | **XS** | precondition for accurate F4 measurement | **F4.PRE** |

**Total est. effort**: XS(2h) + M(8h) + S(2h) + L(12h) + S(2h) + M(4h) + L(10h) ≈ **40 horas**.

---

## 8. Plan de sub-waves (orden recomendado)

### F4.PRE — Mesh re-labeling (PREREQUISITE, 2 horas)

1. Fix `oracle_mesh_mapping.py`:
   - Re-map `pyg.financiacion.contractMx` → `Visión P&G!H70..N70` (currently → H68).
   - Add `pyg.comision_admin.contractMx` → `Visión P&G!H68..N68` (currently mis-labeled).
   - Re-map `pyg.polizas.contractMx` → `Visión P&G!H69..N69` (currently → H65; H65 is TOTAL).
   - Add `pyg.componente_financiero_total.contractMx` → `Visión P&G!H65..N65`.
2. Regenerate `excel_oracle_v2_7_mesh.json` rows where ranges changed.
3. Re-run `scripts/build_drift_heatmap.py`.

**No backend changes**. This is a documentation/mapping correction so subsequent
F4.A/B/C/D/E/F can measure drift truthfully.

### F4.A — ICA refactor (8 horas)

Depends on F4.PRE. Refactor `domain/financial/calculators.py::calcular_ica` to operate
per (cadena × canal × mes) row with the cliff-bracketing umbral. Add `tasa_ica` source
re-routing from `Panel!C34`. Storage `op.json` must surface this scalar at the panel
level (today buried in city table).

Exit: `pyg.ica.contractM1..M7` drift 0.00%.

### F4.B — GMF refactor (2 horas)

Depends on F4.A. Once `calcular_ica` is per-row with gross-up + bracket, `calcular_gmf`
delegates to the same helper substituting `tasa_gmf` for `tasa_ica`.

Exit: `pyg.gmf.contractM1..M7` drift 0.00%.

### F4.D — Comisión Administración (2 horas)

Depends on F4.PRE. Independent of A/B. Wire `tasa_comision_administracion` = 0.016756
(from Excel `Pólizas!D188`, NOT `Panel!D45=0.0118` — the gross-up was pre-baked into
0.016756). Sum Cadena A + B + C contributions.

Exit: `pyg.comision_admin.contractM1..M7` drift 0.00%.

### F4.C — Pólizas adicionales (12 horas, LARGEST)

Depends on F4.A/B/D. Requires storage refactor: `op.json:poliza` must become
3 cadena-scoped matrices each with (poliza, tasa, atribución, duración, aplica).
Refactor `FinancialParametrizationRepository.get_effective_policy_rate` and the
calculator to support cliff-bracketing.

Exit: `pyg.polizas_adic.contractM1..M7` drift 0.00%.

### F4.E — Costo Financiación (4 horas, latent)

Depends on F4.C (because the inner bracket of ICA/GMF feeds back into polizas/comisión
through `costo_financ_row`). For V2-7 pre-loaded the value is 0 — no immediate drift —
but the per-row + cliff structure must be ported so that scenarios with
`activa_financiacion=True` work.

Exit: `pyg.costo_financiero.contractM1..M7` drift 0.00% on a synthetic activation test.

### F4.F — No-Payroll (10 horas)

Independent of F4.A-E. Storage refactor + per-canal × per-cadena Activado-matrix logic
in `NoPayrollCalculator`. Three sub-blocks (OPEX Fijo, Inversiones, Costos Fijos).

Exit: `pyg.no_payroll_a.contractM1..M7` drift 0.00%, ideally + 3×7 sub-line checkpoints.

### Dependency graph

```
F4.PRE ──┬─→ F4.A (ICA) ──→ F4.B (GMF)
         ├─→ F4.D (Comisión)
         └─→ F4.C (Pólizas) ──→ F4.E (Costo Financ)

F4.F (No-Payroll) independent
```

Recommended execution order: **PRE → D → A → B → C → E → F** (D first because S-effort
unlocks quick win on mesh + does not block A/B/C). F4.F can run in parallel.

---

## 9. AMBIGUITIES (must resolve before implementing each sub-wave)

| # | Sub-wave | Ambiguity |
|---|---|---|
| Q1 | F4.A | `Panel!C34` (manual scalar) vs city-table-driven `op.json:ica` lookup — which is canonical? Excel says C34. |
| Q2 | F4.A | Excel ICA includes `+E198` (polizas adic) and `+E378` (costo financ) in the bracket. Are these the SAME polizas/financ that we then add as separate P&G lines (H69, H70)? If yes, the bracket double-counts within ICA's gross-up. Confirm semantics with PO. |
| Q3 | F4.C | `Visión P&G!H69` formula adds J12:J163 (ICA range!) + J198:J327 (polizas range). Is this intentional in V2-7 or a regression bug in the Excel template? |
| Q4 | F4.D | Excel stores `D188 = 0.016756` but Panel D45 = 0.0118. What gross-up factor produces 0.016756? (0.0118 / 0.7039 ≈ 0.016756 → 0.7039 ≈ factor_margenes for the default deal). Confirm. |
| Q5 | F4.PRE | `pyg.financiacion` in the codebase — is it Comisión Admin (current mis-labeling) or Costo Financiación (Excel H70)? The two are semantically distinct. |
| Q6 | F4.F | Excel rows 107-125 (No payroll OPEX) — we did NOT enumerate the 19 rows. F4.F must inventory them and map each to a backend constant. |

---

## 10. UNEXPECTED FINDINGS

1. **Oracle mesh is structurally mis-labeled** — `pyg.polizas`, `pyg.financiacion`
   point at wrong cells. This was not flagged in W17/W19. Single biggest discovery.

2. **Excel uses `Panel!C34 = 0.01` for ICA, NOT the city ICA table.** The 100-row city
   ICA matrix (`Tasas, TRM, Polizas!A34:F54`) is not consumed by the P&G calculation
   at all — it's a reference table. Backend has been routing through this wrong source
   the entire time.

3. **`D188 = 0.016756` is pre-grossed**. The Panel D45 = 0.0118 stored value gets
   multiplied by a `1/factor_margenes`-like factor before reaching D188. Backend's
   `tasa_comision_administracion` semantics must match D188 (post-gross-up) or
   `Panel!D45` (pre-gross-up) — these are different by ~1.42×.

4. **Excel `H69` (Pólizas adicionales) formula range overlaps with H66 (ICA)**:
   `SUMPRODUCT(J12:J163,…) + SUMPRODUCT(J198:J327,…)` — the first SUMPRODUCT is
   identical to the H66 range. Either Excel double-counts ICA inside "Pólizas
   adicionales", or this is a regression from V2-5 → V2-7. Documented as Q3.

5. **`Panel!C21 = "No"` disables `Costo Financiación` entirely** — `D365 = 0` so
   `E370 = 0` for all months. The full capital-charge stack is dormant in the V2-7
   pre-loaded scenario. This explains the 0/0 alignment in row 70.

6. **`activa_financiacion` and `panel.tasa_mensual_financ = 0.0153` are decoupled in
   the backend** — the boolean gates everything to 0, but `0.0153 = Panel!L10` is
   already correct in storage. Setting the boolean True would unmask the latent drift
   in row 70.

7. **`Pólizas - Costo Financiacion` per-row formulas use Excel 365 LET + FILTER +
   IFERROR + array spilling**. Cannot be implemented as pure pandas vectorization
   trivially — needs careful per-canal × per-cadena dispatch with month bracketing.

---

## 11. References

- Excel: `~/Downloads/Nexa - Pricing - Simulador - V2-7.xlsx`
  - `Visión P&G` rows 18-79
  - `Pólizas - Costo Financiacion` rows 12-456 (ICA, GMF, Comm, Pólizas, Financ blocks)
  - `Panel de Control General` C9, C11, C16-C21, C34, C35, D45, C63-C70, L10, K19:M25
  - `Tasas, TRM, Polizas` A20:F54 (Pólizas catalog + city ICA matrix)
  - `No payroll` rows 107-125, 186-204, 248-266

- Backend:
  - `calculators/costos_financieros.py` (lines 47-291)
  - `calculators/no_payroll.py` (lines 47-185)
  - `domain/financial/calculators.py` (lines 25-86)
  - `repositories/financial_parametrization_repository.py` (lines 56-275)

- Storage (read-only for this audit):
  - `storage/parametrization/v2-7/op.json` (sheets: ica, poliza, config, componente)
  - `storage/parametrization/v2-7/gn.json`

- Tests:
  - `tests/parity/oracle_mesh_mapping.py` (lines defining COSTOS_FINANCIEROS checkpoints — F4.PRE target)
  - `tests/parity/excel_oracle_v2_7_mesh.json`
  - `tests/parity/DRIFT_HEATMAP.md`

---

*Audit-only deliverable. No engine, test, parametrization, or oracle modification performed.*
