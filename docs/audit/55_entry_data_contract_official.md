# Phase 5.5 — Entry Data Contract Official Definition

**Date**: 2026-05-21  
**Status**: ✅ **OFFICIAL ENTRY DATA CONTRACT (PHASE 5.5 CERTIFIED)**  
**Purpose**: Define the EXACT structure that frontend must send, with ZERO metadata, ZERO debugging fields

---

## Executive Summary

The entry_data contract is the **single source of truth** for all pricing calculations. It contains ONLY legitimate business data — no metadata, no debugging fields, no expected values.

**Key Principle**: `entry_data = Frontend sends exactly what backend needs to calculate`

---

## Mandatory Rules (Phase 5.5)

### ✅ ALLOWED
- Fields explicitly defined in this contract
- Nested objects following this structure exactly
- Numerical values (float, int)
- Boolean flags
- String enums from controlled vocabularies

### ❌ STRICTLY FORBIDDEN
- Any field starting with `_` (metadata, debugging)
- Fields not defined in this contract
- Legacy field names or aliases
- Expected values or validation metadata
- Comments or notes
- Internal tracking fields

---

## Official Entry Data Structure

### Root Level (4 Sections)

```json
{
  "panel_de_control": { ... },           // Mandatory: Client configuration
  "condiciones_cadena_a": { ... },       // Optional: Inbound/Outbound operations
  "condiciones_cadena_b": { ... },       // Optional: Infrastructure & OpEx
  "condiciones_cadena_c": { ... }        // Optional: Cross-functional services
}
```

**RULE**: Only these 4 keys are allowed at root level. Any other field is a contract violation.

---

## Section 1: panel_de_control (Mandatory)

Client-level configuration parameters that apply across all chains.

```json
{
  "panel_de_control": {
    // --- Client Identification ---
    "cliente": "string (required)",           // e.g., "Bancamia"
    "tipo_cliente": "string (optional)",      // e.g., "No Grupo Aval" | "Grupo Aval"
    "linea_negocio": "string (required)",     // e.g., "Cobranzas" | "Atención"
    
    // --- Location ---
    "ciudad": "string (optional)",            // e.g., "Bogotá"
    "sede": "string (optional)",              // e.g., "Medellín"
    
    // --- Contract Terms ---
    "fecha_inicio": "ISO 8601 date (optional)",  // e.g., "2026-01-01"
    "meses_contrato": "integer (required)",      // e.g., 12
    
    // --- Financial Parameters ---
    "margen": "float (required)",             // Net margin, e.g., 0.1339 (13.39%)
    "op_cont": "float (required)",            // Operational contingency, e.g., 0.02 (2%)
    "com_cont": "float (optional)",           // Commission contingency, default 0.0
    "markup": "float (optional)",             // Price markup, default 0.0
    "descuento": "float (optional)",          // Discount, default 0.0
    
    // --- Payment Terms ---
    "periodo_pago_dias": "integer (optional)",  // Payment period in days, default 90
    
    // --- Financing ---
    "activa_financiacion": "boolean (optional)",    // Enable financing? default true
    "tasa_mensual_financ": "float (optional)",      // Monthly financing rate, e.g., 0.0153 (1.53%)
    
    // --- Client Attributes ---
    "antiguedad_cliente": "string (optional)",       // "Cliente Nuevo" | "Cliente Existente"
    
    // --- Tax & Indexation ---
    "componente_indexacion_humano": "string (optional)",      // "IPC" | "IPCS" | etc., default "IPC"
    "componente_indexacion_tecnologico": "string (optional)",  // "IPC" | "IPCS" | etc., default "IPC"
    "aplica_ley_1819": "boolean (optional)",                   // Apply fiscal reform? default true
    
    // --- Tax Rates ---
    "tasa_ica": "float (required)",           // ICA municipal tax, e.g., 0.02 (2%)
    "tasa_gmf": "float (required)",           // GMF financial tax, e.g., 0.004 (0.4%)
    
    // --- Operational Rates (Used by Calculators) ---
    "pct_rotacion": "float (optional)",       // Staff turnover %, e.g., 0.085 (8.5%)
    "pct_ausentismo": "float (optional)",     // Absenteeism %, e.g., 0.065 (6.5%)
  }
}
```

### Validation Rules
- `cliente`: Non-empty string, max 100 chars
- `meses_contrato`: Integer in range [1, 60]
- `margen`: Float in range [0, 1]
- `op_cont`: Float in range [0, 0.5]
- `tasa_ica`: Float in range [0, 0.1]
- `tasa_gmf`: Float in range [0, 0.01]
- `tasa_mensual_financ`: Float in range [0, 0.1]

---

## Section 2: condiciones_cadena_a (Optional)

Inbound/Outbound staff operations and payroll.

```json
{
  "condiciones_cadena_a": {
    "perfiles": [
      {
        // --- Profile Identification ---
        "nombre": "string (required)",        // e.g., "Inbound 10"
        "rol": "string (optional)",           // e.g., "Agente Basico"
        
        // --- Channel & Mode ---
        "canal": "string (required)",         // e.g., "WhatsApp" | "Phone" | "Email"
        "modalidad": "string (required)",     // "Inbound" | "Outbound"
        
        // --- Staffing ---
        "fte": "float (required)",            // Full-time equivalents, e.g., 6
        "pct_presencia": "float (optional)",  // Presence %, default 1.0
        
        // --- Compensation ---
        "salario_base": "float (optional)",   // Base salary, e.g., 2450000 COP/month
        "comision_pct": "float (optional)",   // Commission as % of salary, default 0.0
        
        // --- Benefits/Training ---
        "incluye_examenes": "boolean (optional)",    // Include exams? default true
        "incluye_seguridad": "boolean (optional)",   // Include security? default false
        "incluye_crucero": "boolean (optional)",     // Include cruise? default true
        
        // --- Ramp-up ---
        "dias_cap_inicial": "integer (optional)",    // Initial ramp days, default 10
        "dias_cap_rotacion": "integer (optional)",   // Rotation ramp days, default 10
        
        // --- Billing ---
        "modelo_cobro": "string (optional)",      // "Fijo FTE" | "Variable" | "Hibrido"
        "pct_fijo": "float (optional)",           // Fixed % of billing, default 1.0
        "no_payroll_mensual": "float (optional)", // Fixed no-payroll monthly cost
        
        // --- Cascading Costs (Optional) ---
        "cadena_b_mensual": "float (optional)",            // Monthly chain B cost
        "costos_financieros_mensual": "float (optional)",  // Monthly financial cost
        "vol_cadena_a_mensual": "float (optional)",        // Monthly volume metric
      }
    ]
  }
}
```

### Usage by Calculators
- **NominaCalculator**: Reads `fte`, `salario_base`, `comision_pct`, `dias_cap_*`, `incluye_*`
- **NoPayrollCalculator**: Reads `no_payroll_mensual`
- **CostosFinancierosCalculator**: Reads payment terms from panel

---

## Section 3: condiciones_cadena_b (Optional)

Infrastructure, OpEx, support team, equipment costs.

```json
{
  "condiciones_cadena_b": {
    // --- Channels/Products ---
    "canales": [
      {
        "nombre": "string (required)",           // e.g., "WhatsApp Inbound"
        "modalidad": "string (required)",        // "Inbound" | "Outbound"
        "producto": "string (optional)",         // e.g., "WhatsApp" | "Phone"
        "volumen_mensual": "float (optional)",   // Monthly volume, e.g., 1000
        "activo": "boolean (optional)",          // Is active? default true
        "opex_fijo": "float (optional)",         // Fixed OpEx monthly
        "tarifa_unitaria": "float (optional)",   // Cost per unit
        "pct_escalamiento": "float (optional)",  // Escalation rate
        "costo_escalamiento": "float (optional)"// Escalation cost
      }
    ],
    
    // --- Variable OpEx ---
    "opex_consumo_variable": [
      {
        "nombre": "string (required)",        // e.g., "HITL - Human Reviewers"
        "producto": "string (required)",      // e.g., "HITL"
        "modalidad": "string (required)",     // "Inbound" | "Outbound"
        "canal": "string (required)",         // e.g., "WhatsApp"
        "valor_unitario": "float (required)", // Cost per unit
        "cantidad": "float (optional)",       // Quantity, default 1.0
        "tipo_cobro": "string (optional)"    // "Unitario" | "Porcentual"
      }
    ],
    
    // --- Support Team ---
    "equipo_sm": [
      {
        "rol": "string (required)",           // e.g., "Service Owner"
        "activo": "boolean (optional)",       // Is active? default true
        "pct_dedicacion": "float (optional)"  // Dedication %, e.g., 0.05
      }
    ],
    
    // --- Equipment ---
    "dispositivos_sm": [
      {
        "tipo": "string (required)",              // e.g., "Dispositivo Principal"
        "costo_unitario": "float (required)",     // Unit cost
        "cantidad": "float (optional)",           // Quantity
        "meses_amortizacion": "integer (optional)"// Amortization months, default 1
      }
    ],
    
    // --- Infrastructure Totals ---
    "inversion_plataforma": "float (optional)",   // Platform investment
    "fte_equipo_sm": "float (optional)",          // Support team FTEs
    "amortizar_dispositivos_sm": "boolean (optional)"  // Amortize equipment? default true
  }
}
```

---

## Section 4: condiciones_cadena_c (Optional)

Cross-functional services, transversal team, strategic initiatives.

```json
{
  "condiciones_cadena_c": {
    "canales": [
      {
        "nombre": "string (required)",           // e.g., "Strategic Initiative"
        "modalidad": "string (required)",        // e.g., "Strategic"
        "volumen_mensual": "float (optional)",   // Monthly volume
        "activo": "boolean (optional)",          // Is active? default true
        "opex_fijo_integ": "float (optional)",   // Fixed integrated OpEx
        "opex_var_integ": "float (optional)",    // Variable integrated OpEx
        "pct_escalamiento": "float (optional)",  // Escalation %
        "costo_escalamiento": "float (optional)"// Escalation cost
      }
    ],
    
    "equipo_transversal": [
      {
        "rol": "string (required)",         // e.g., "Director" | "Manager"
        "activo": "boolean (optional)",     // Is active? default true
        "pct_dedicacion": "float (optional)"// Dedication %
      }
    ],
    
    "inversion_anual": "float (optional)"   // Annual investment, default 0
  }
}
```

---

## Phase 5.5 Migration Summary

### What Was Removed
50 POLLUTION fields across 8 test cases:
- Metadata: `_comment`, `_scenario`, `_source`, `_note`
- Validation data: `_k50_expected`, `_cts_ponderado_expected`, etc.
- Excel references: `_excel_payroll_mes1`, `_excel_polizas_mes1`, etc.

### What Was Preserved
All legitimate business data exactly as defined above.

### New Structure
```
test_cases/
├── input/
│   ├── bancamia_whatsapp_only.json        ← CLEAN: exactly contract
│   ├── bancamia_excel_match.json
│   ├── bancamia_canonical_k50.json
│   └── ...
├── expected/
│   ├── bancamia_whatsapp_only.expected.json    ← Metadata + validation
│   ├── bancamia_excel_match.expected.json
│   └── ...
├── audit/
│   ├── bancamia_whatsapp_only.audit.json
│   ├── migration_summary.json
│   └── ...
└── [excel/ snapshots/ — future use]
```

---

## Validation Rules (user_input_loader.py)

The UserInputLoader applies three levels of validation:

### Level 1: POLLUTION Detection (Phase 5.5)
```python
if any(field.startswith("_") for field in data.keys()):
    raise ValueError("POLLUTION fields detected: entry_data must not contain metadata")
```

### Level 2: Contract Enforcement (Phase 5.5)
```python
allowed_roots = {"panel_de_control", "condiciones_cadena_a", "condiciones_cadena_b", "condiciones_cadena_c"}
if not set(data.keys()).issubset(allowed_roots):
    raise ValueError("Unknown entry_data sections")
```

### Level 3: Type Validation
Fields are validated against types defined in domain/user_inputs.py

---

## Fields Not Yet Implemented (Future)

The following business concepts are NOT yet in entry_data contract (identified but not migrated):

- `reglas_negocio`: Business rules configuration (currently in storage/)
- `contingencia_operativa`: Operational contingency handling
- `escenarios_comerciales`: Commercial scenario definitions
- `polizas`: Insurance policies beyond ICA/GMF
- `cadenas_activas`: Explicit chain activation flags
- `indexacion`: Dynamic indexation rules

**Action**: Once needed, these will be added to contract following Phase 5.5 process.

---

## Backward Compatibility

The old structure (test_cases/\*.json with POLLUTION fields) is **NO LONGER SUPPORTED**.

- Old files remain in test_cases/ for reference only
- New code paths read only from test_cases/input/
- UserInputLoader enforces contract — violations throw errors
- Migration is ONE-WAY: no fallback to old structure

---

## Certification

✅ **This contract is CERTIFIED as of Phase 5.5**

It represents:
- The EXACT interface between Frontend and Backend
- The single source of truth for all pricing calculations
- The foundation for Phases 6-11 (auditoría, estandarización, migración)

Any deviation from this contract is a **CRITICAL BLOCKER** that must be resolved before proceeding.

---

**Status**: 🟢 **PHASE 5.5 COMPLETE — ENTRY DATA CONTRACT OFFICIAL**
