# V2-8 Full Formula Inventory

> Generated: 2026-06-11 | Branch: refactor/modular-pure | Deal: SAC / METROCUADRADO COM SAS

## Scope Sheets

| Sheet | Total Values | Formulas | In Scope |
|-------|-------------|----------|----------|
| Listas Desplegables | 361 | 240 | No — input catalog |
| Riesgo | 236 | 17 | No — risk assessment UI |
| Graficos | 1466 | 1006 | No — chart data |
| Nomina Loaded | 20986 | 18570 | No — payroll computation |
| Tasas, TRM, Polizas | 313 | 65 | Partial — IPC rates comparable |
| Rot, Ausent y Rentabilidad | 689 | 37 | No — parametrization |
| No payroll | 10037 | 8730 | No — intermediate |
| Costo Fijo | 6838 | 5157 | No — intermediate |
| Costo Variable | 12855 | 10510 | No — intermediate |
| Costo Cadena C | 15976 | 13659 | No — intermediate |
| Costos Totales | 6769 | 5151 | No — intermediate |
| Pólizas - Costo Financiacion | 20032 | 11808 | No — intermediate |
| Inputs de Nomina | 4097 | 3525 | No — input |
| Panel de Control General | 969 | 221 | No — user input |
| Condiciones Cadena A | 1361 | 1156 | No — user input |
| Condiciones Cadena B | 313 | 113 | No — user input |
| Condiciones Cadena C | 337 | 109 | No — user input |
| Visiones | 0 | 0 | No — empty |
| **Visión Imprimible** | **199** | **116** | **Yes** |
| **Vision Cost To Serve** | **1091** | **447** | **Yes** |
| **Vision Tarifas_Modelo_Cobro** | **422** | **128** | **Yes** |
| **Hoja Maestra Escenarios** | **1055** | **357** | **Yes** |
| **Visión P&G** | **3854** | **1982** | **Yes** |

**Total formulas in scope: 3,030**

## Key Formula Catalog — Output Sheets

### Visión P&G (1982 formulas)

The P&G sheet computes monthly P&G over the 24-month contract duration.
Columns C through BJ represent months 1-24.

| Cell | Formula | Cached Value | Type | Comparable |
|------|---------|--------------|------|------------|
| C15 | `=IFERROR(INDEX('Rot...'!...,MATCH(C11,...)))` | 0 | INTERMEDIATE_FORMULA | No — col C = month 0 (pre-contract) |
| I15 | same pattern | 0.9 | INTERMEDIATE_FORMULA | Yes — first active month |
| J15 | same pattern | 0.95 | INTERMEDIATE_FORMULA | Yes — second active month |
| C18 | `=C19+C20+C21+C71` | 0 | INTERMEDIATE_FORMULA | No — month 0 |
| I18 | `=I19+I20+I21+I71` | 2,716,297,622.33 | OUTPUT_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |
| C19 | `=IF(AND(...),HME!C296,0)*C15*(1+IPC_factor)` | 0 | OUTPUT_FORMULA | No |
| I19 | same | 1,639,941,976.12 | OUTPUT_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |
| I27 | `=I18+SUM(I22:I24)-I25-I26` | 2,716,297,622.33 | OUTPUT_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |
| I30 | `=I31+I45+I55` | 2,347,045,235.00 | OUTPUT_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |

**Architectural delta note**: The P&G Ingreso formula is:
`= HME!C296 * rampup_factor * (1 + IPC_rate)`
where `HME!C296` is the **monthly base revenue for Cadena A** computed from cost÷(1-margen).
The backend computes month-by-month without a single base cell, producing equivalent
but structurally different numbers. With rampup and IPC the totals differ by design.

### Hoja Maestra Escenarios (357 formulas)

| Cell | Formula | Cached Value | Type | Comparable |
|------|---------|--------------|------|------------|
| C258 | ArrayFormula sum | 1,439,504,623.48 | OUTPUT_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |
| C268 | ArrayFormula sum | 15,937,571.97 | OUTPUT_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |
| C278 | ArrayFormula sum | 938,546,206.44 | OUTPUT_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |
| C289 | `=C266+C276+C286` | 3,018,108,469.26 | OUTPUT_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |
| C295 | `=$C$258` | 1,439,504,623.48 | INTERMEDIATE_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |
| C296 | `=C295/(1-$G$253)` | 1,822,157,751.25 | INTERMEDIATE_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |
| C303 | `=+C268` | 15,937,571.97 | INTERMEDIATE_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |
| C304 | `=C303/(1-$G$254)` | 22,767,959.96 | INTERMEDIATE_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |
| C311 | `=+C278` | 938,546,206.44 | INTERMEDIATE_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |
| C312 | `=C311/(1-$G$255)` | 1,173,182,758.05 | INTERMEDIATE_FORMULA | BLOCKED_BY_ARCHITECTURE_DELTA |

**Note**: These ARE the current deal (SAC/METROCUADRADO) after Option B switch.
The ARCHITECTURE_DELTA is that HME stores a *single monthly base* (pre-rampup, pre-IPC)
while the backend computes the full series. The base values match conceptually when
normalized but not numerically at face value.

### Vision Cost To Serve (447 formulas)

| Cell | Formula | Cached Value | Type | Comparable |
|------|---------|--------------|------|------------|
| C34 | `=C35+C45` | 6,224.58 | OUTPUT_FORMULA | Comparable — but unit difference |
| C37 | SUM(IF(panel...nomina...)) | 4,629.49 | INTERMEDIATE_FORMULA | Comparable |
| G34 | `=+G35+G41` | 151.51 | OUTPUT_FORMULA | Comparable |
| K34 | `=SUM(K35,K36,K40)` | 5,278.33 | OUTPUT_FORMULA | Comparable |
| G49 | `=(C34*C31)+(G34*G31)+(K34*K31)` | 4,660.08 | OUTPUT_FORMULA | Comparable — ponderado |

**Unit analysis**: Excel CTS values are **COP per FTE per month** for Cadena A,
**COP per transaction** for Cadenas B and C. Backend stores total costs then derives
per-unit metrics. Backend `cts_cadena_a` is per-FTE but uses different FTE base.

### Vision Tarifas_Modelo_Cobro (128 formulas)

| Cell | Formula | Cached Value | Type | Comparable |
|------|---------|--------------|------|------------|
| H19 | `=C19+D19+E19+F19+G19` | 3,018,108,469.26 | OUTPUT_FORMULA | Comparable — monthly base revenue |
| C19 | ArrayFormula | 2,098,599,983.25 | OUTPUT_FORMULA | Comparable — Esc 1 monthly rev |
| D19 | ArrayFormula | 313,188,543.96 | OUTPUT_FORMULA | Comparable — Esc 2 |
| E19 | ArrayFormula | 606,319,942.04 | OUTPUT_FORMULA | Comparable — Esc 3 |
| C21 | | 7,481.64 | OUTPUT_FORMULA | Comparable — tarifa variable esc 1 |
| H19 | `=C75` (via chain) | | | |

**Note**: Excel H19 = 3,018,108,469 = single monthly base revenue.
Backend `ingreso_mensual` = 64,529,525,326 = cumulative sum over 24 months × rampup × IPC.
For comparison: `3,018,108,469 × 24 months` ≈ `72,434,603,256` (pre-rampup, pre-IPC).

### Visión Imprimible (116 formulas)

Primarily pass-through from Panel de Control General and Vision Tarifas.
Key numeric cells are mirrors of other sheets — not independently comparable.

## Classification Summary

| Type | Count | Description |
|------|-------|-------------|
| USER_INPUT | ~1,800 | Panel/Cadenas pass-through (no comparison needed) |
| PARAMETRIZATION | ~500 | HR/GN/OP lookup chains |
| INTERMEDIATE_FORMULA | ~600 | Internal computation steps |
| OUTPUT_FORMULA | ~100 | Final results backend must reproduce |
| VISUAL_ONLY | ~30 | Labels, text concatenation, formatting |
| BLOCKED_BY_ARCHITECTURE_DELTA | ~50 | Monthly series, HME bases (single-base vs month-by-month) |
| OLD_CACHE_NOT_COMPARABLE | 0 | None (deal aligned via Option B) |

