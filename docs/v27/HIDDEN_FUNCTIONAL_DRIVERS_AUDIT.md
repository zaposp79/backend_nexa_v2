# Hidden Functional Drivers Audit Report — Excel V2-7

## Methodology

Scanned all Excel V2-7 sheets for `IF(...="string", ...)` conditions using openpyxl.
Found 14 unique string literals used as IF conditions across 10 sheets.

## Audit Table

| Literal | Sheet / Cell | Formula Pattern | Classification | Backend |
|---------|-------------|-----------------|----------------|---------|
| `"SAC"` | CTS!C58, CTS!C87 | `IF(C27="SAC","✓ Habilitado","—")` | Semantic relevance gate | `ServicioBehavior.canal_detail_habilitado` |
| `"SACO"` | Panel!C120 | `IF(OR(C5="SACO","Ventas Multicanal"),...)` | Section gate | `ServicioBehavior.seccion_saco_ventas_habilitada` |
| `"SACO"` | VT!C77,C133 | `IF(C5="SACO", Panel!C143:G143, ...)` | Billing mode switch | `ServicioBehavior.vt_billing_mode == "SACO"` |
| `"Cobranzas"` | Panel!C152 | `IF(C5="Cobranzas","✓ Habilitado","—")` | Section gate | `ServicioBehavior.seccion_cobranzas_habilitada` |
| `"Cobranzas"` | VT!C77,C133 | `IF(C5="Cobranzas", Panel!C182:P182, ...)` | Billing mode switch | `ServicioBehavior.vt_billing_mode == "Cobranzas"` |
| `"Captura de Datos"` | Panel!C184 | `IF(C5="Captura de Datos","✓ Habilitado","—")` | Section gate | `ServicioBehavior.seccion_captura_datos_habilitada` |
| `"Cliente Nuevo"` | Panel!C7, P&G!C5, CTS!B11, VT!J3 | `IF(C7="Cliente Nuevo", D6, C6)` | Client name selector | Input field `tipo_cliente` — NOT service-driven |
| `"FTE"` | VT!F45, G45 | `IF(C34="FTE","Tarifa por FTE","Tarifa por minuto loggeado")` | Billing model label + calc | `EscenarioComercial.modelo_cobro` — already implemented |
| `"Tiempo"` | VT!F47, G47 | `IF(C34="Tiempo", G43/E124, 0)` | Time-based tariff calc | `EscenarioComercial.modelo_cobro` |
| `"Transacción"` | VT!C21, D21, etc. | `IF(C16="Transacción", HMS!G31, IF(OR(C16="Resultados","Honorarios"),...))` | Variable rate selector | `EscenarioComercial.componente_variable` |
| `"Resultados"` | VT!C21 (same IF) | same IF | Results-based variable rate | same |
| `"Honorarios"` | VT!H21, C130 | same IF + `IF(OR(C35="Honorarios","Resultados"),"✓ Habilitado","—")` | Fees-based + section gate | same + section visibility |
| `"Inbound"` | VT!C41-C44 | `IF(C31="Inbound", Panel!M17, Panel!M30)` | Cadena A/B chain selector | `EscenarioComercial.modalidad` |
| `"Total"` | VT!C37, D35 | `IF(C29="Total", SUM(all FTE), SUMIFS(...))` | FTE scope selector | `EscenarioComercial.escenario == "Total"` |

## Classification Definitions

| Class | Meaning |
|-------|---------|
| **Semantic relevance gate** | Controls a header/label only; data computes regardless |
| **Section gate** | Controls visibility of a Panel or view section (✓/—) |
| **Billing mode switch** | Selects different data/formula for billing calculation |
| **Client name selector** | Selects display name based on client type |
| **Billing model label + calc** | Changes both a label AND a calculation |
| **Variable rate selector** | Selects which rate applies for variable component |
| **Chain selector** | Selects which cadena's activation flag to check |
| **FTE scope selector** | Selects between total FTE and filtered FTE |

## Previously Misclassified

| Literal | Previous Classification | Corrected Classification |
|---------|------------------------|--------------------------|
| `"SAC"` (CTS!C58/C87) | "cosmetic label" (Phase 2 initial) | Semantic relevance gate keyed on a functional driver |
| `"SACO"` (VT!C77) | Not identified (Phase 2) | Billing mode switch — NEW finding |
| `"Cobranzas"` (VT!C77/C133) | Not identified (Phase 2) | Billing mode switch — NEW finding |

## Dimensions Confirmed NOT Service-Driven

These were suspected to be service-driven but are input-driven:
- **Active chains A/B/C**: `Panel!M17/M30` — literal booleans from `cadenas_activas` input
- **Active channels**: `Panel!L19:L25` volume > 0 — from `volumetria` input
- **Billing model**: `EscenarioComercial.modelo_cobro` (FTE/Tiempo/etc.) — not keyed on service

## UNDETERMINED Items

| Item | Reason |
|------|--------|
| VT!C77 SACO/Cobranzas billing rows | Rendering requires Panel!C143:G143 and C182:P182 input contracts not yet modeled |
| VT!C133 rate multiplier | Same — Panel!C124/C155 source not in current input contract |
