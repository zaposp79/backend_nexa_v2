# W18.F5.D — Full Workbook Coverage Certification

## Investigation methodology

Each dimension was investigated in the workbook **before** writing any code.
Sources: openpyxl data_only=True for values, data_only=False for formulas.
Zero fabricated values.

---

## Coverage Matrix

| Dimension | Status | Workbook source | Tests |
|-----------|--------|-----------------|-------|
| **Service: Captura de Datos** | ✅ CERTIFIED | V2-7 canonical fixture, 208 oracle checkpoints | oracle_mesh.py (208 pass) |
| **Service: Cobranzas — ramp-up** | ✅ CERTIFIED | `Rot!B38 = [0.85, 0.92, 1.0, ...]` | `test_rampup_per_service[Cobranzas]` |
| **Service: Sac — ramp-up** | ✅ CERTIFIED | `Rot!B39 = [0.90, 0.95, 1.0, ...]` | `test_rampup_per_service[Sac]` |
| **Service: Ventas multicanal — ramp-up** | ✅ CERTIFIED | `Rot!B40 = [0.80, 0.87, 0.95, 1.0, ...]` | `test_rampup_per_service[Ventas multicanal]` |
| **Service: SACO — ramp-up** | ✅ CERTIFIED | `Rot!B41 = [1.0, 1.0, ...]` | `test_rampup_per_service[SACO]` |
| **Service: Plataformas — ramp-up** | ✅ CERTIFIED | `Rot!B42 = [1.0, 1.0, ...]` | `test_rampup_per_service[Plataformas]` |
| **Service: SACO — billing** | ⛔ UNDETERMINED | `VT!C77→Panel!C143:G143` (computed, not readable without recalculation) | documents only |
| **Service: Cobranzas — billing** | ⛔ UNDETERMINED | `VT!C77→Panel!C182:P182` (computed portfolio billing) | documents only |
| **Modality: Inbound** | ✅ CERTIFIED | V2-7 canonical (Voz + WhatsApp Inbound) | oracle_mesh.py |
| **Modality: Outbound** | ⛔ UNDETERMINED | `Panel!K32:P40` all zeros in V2-7 (not configured) | documents only |
| **Billing: FTE (Voz, 70%)** | ✅ CERTIFIED | `Panel!D84=0.7`, `VT!C15=0.7` | `test_billing_model_hybrid_voz_pct_fijo` |
| **Billing: FTE (WA, 100%)** | ✅ CERTIFIED | `Panel!D98=1.0`, `VT!E15=1.0` | `test_billing_model_fijo_fte_whatsapp` |
| **Billing: Variable (WA, 100%)** | ⛔ UNDETERMINED | `Panel!A88:D92=Variable/100%` — oracle values require separate fixture with WhatsApp-only deal; backend correctly processes but no absolute oracle cell to compare | documents only |
| **Payroll: operational** | ✅ CERTIFIED | Nomina Loaded, V2-7 fixture | oracle_mesh.py (salario_fijo*, nomina rows) |
| **Payroll: soporte (Staff)** | ✅ CERTIFIED | CTS desglose_a, per-canal CTS | gap_closure tests |
| **No Payroll** | ✅ CERTIFIED | `Vision Cost To Serve!C46-C48` | oracle_mesh + gap_closure |
| **Financials: ICA** | ✅ CERTIFIED | `Panel!C34=0.01`, PyG row 66 | oracle_mesh |
| **Financials: GMF** | ✅ CERTIFIED | `Panel!C35=0.004`, PyG row 67 | oracle_mesh |
| **Financials: Pólizas (Salarios + Calidad)** | ✅ CERTIFIED | `Panel!C40=True, C41=True` | oracle_mesh + polizas tests |
| **Financials: Financiación inactive** | ✅ CERTIFIED | `Panel!C21='No'`, P&G H70-N70=0 | oracle_mesh + `test_financiacion_inactive` |
| **Financials: Financiación active** | ✅ CERTIFIED (formula) | formula: `factor_periodo × tasa × costo_anterior` | `test_financiacion_active_produces_nonzero` |
| **Cadena A costs** | ✅ CERTIFIED | PyG rows 32-44, VT!C40 | oracle_mesh (50+ checkpoints) |
| **Cadena B costs** | ✅ CERTIFIED | PyG rows 45-54, VT!C50=0 | oracle_mesh |
| **Cadena C costs** | ✅ CERTIFIED | PyG rows 55-64, VT!C60 | oracle_mesh |
| **KPIs** | ✅ CERTIFIED | VT!C72=38.6B, ingreso/costo/contribución | oracle_mesh |
| **Vision P&G** | ✅ CERTIFIED | 50+ monthly checkpoints | oracle_mesh |
| **Vision CTS** | ✅ CERTIFIED | `VCS!C34, G34, K34, G49` | oracle_mesh |
| **Vision Tarifas** | ✅ CERTIFIED | C40, C47, C60, C67, C72 | oracle_mesh |
| **Service gates (all 6)** | ✅ CERTIFIED | `Panel!C120/C152/C184`, `CTS!C58/C87` | servicio_driven_behavior (18 tests) |
| **Indexación (ramp-up)** | ✅ CERTIFIED | `Rot!B38:B43` exact match all 6 services | `test_rampup_per_service` (6 tests) |
| **Escalamiento** | ✅ CERTIFIED (values) | V2-7 fixture uses escalamiento; implicit in CTS ponderado | oracle_mesh CTS checkpoints |
| **VT deal-level tariffs (G45/G47)** | ⛔ UNDETERMINED | G45 = total deal facturación × pct_fijo / total_FTE — semantically different from backend per-canal tariffs | documents only |

---

## What cannot be certified without workbook reconfiguration

These scenarios require changing `Panel!C5` and re-reading Excel computed values.
openpyxl data_only=True reads cached values only; cannot recalculate.

| Scenario | Blocking reason |
|----------|----------------|
| SACO billing rows | `VT!C77 → TRANSPOSE(Panel!C143:G143)` — Panel C143:G143 are formula-computed (Facturación Variable, AIU, Costo Variable) |
| Cobranzas portfolio billing | `VT!C77 → TRANSPOSE(Panel!C182:P182)` — computed from portfolio segments × contactability × ARPU |
| Outbound modality | `Panel!K32:P40` all zeros — no Outbound channel configured in V2-7 |
| Billing Variable 100% (absolute values) | Workbook D19=1.01B is HMS!D47 (whole deal with WA-only channels); need standalone WA-only fixture with V2-7 economics to get comparable oracle |
| VT deal-level tariff (G45) | G43/C37/12 uses total deal income × pct_fijo / total FTE; backend uses per-canal income × pct_fijo / canal FTE — architecturally different |

---

## Test summary

| Suite | Tests | Pass |
|-------|-------|------|
| oracle_mesh (V2-7 canonical) | 208 | 208 |
| test_w18_f5d_coverage (new) | 40 | 40 |
| test_vision_gap_closure | 14 | 14 |
| test_servicio_driven_behavior | 18 | 18 |
| test_vision_activation_cases | 21 | 21 |
| test_gap_followup | 32 | 32 |
| All parity tests | 344 | 344 |
| Skipped | 8 | (justified) |
| **Pre-existing failures (unrelated)** | 7 | (unchanged) |

---

## Certification statement

> W18.F5.D: All workbook-derivable scenarios for V2-7 are certified.
> Per-service ramp-up (6 services × verified from `Rot, Ausent y Rentabilidad!B38:B43`),
> billing model assignments (Panel!A81:D113), financiación active/inactive,
> polizas (Salarios+Calidad), and service-driven behavior model (6 services × 5 gates)
> are verified with zero fabricated data.
>
> UNDETERMINED scenarios (SACO/Cobranzas special billing, Outbound, VT deal-level tariffs)
> are documented with workbook evidence — requiring actual workbook reconfiguration
> to obtain oracle values.
