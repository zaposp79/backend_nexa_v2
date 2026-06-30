# NEXA Backend Data Model Reference

**Last Updated**: 2026-05-31  
**API Version**: api-v1  
**Engine Version**: 2.7 (FASE 10+)

This document comprehensively catalogs every DTO, domain model, and result structure used by the NEXA pricing engine. Each model is documented with field definitions, validation rules, and examples extracted from actual code.

---

## Table of Contents

1. [Request DTOs (Input Contracts)](#request-dtos-input-contracts)
2. [Domain Models (Internal Representation)](#domain-models-internal-representation)
3. [Result Models (Calculation Outputs)](#result-models-calculation-outputs)
4. [Vision Models (Formatted Display)](#vision-models-formatted-display)
5. [Response DTOs (API Output)](#response-dtos-api-output)
6. [Enums & Value Objects](#enums--value-objects)

---

# REQUEST DTOs (Input Contracts)

## EntryDataV1

**Location**: `contracts/api_v1/request/entry_data.py`  
**Purpose**: Root request DTO for `POST /api/v1/simulation/calculate`. Frozen, strict, with cross-field validators.  
**Version**: api-v1

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| panel | PanelDeControlRequestV1 | Yes | Deal master parameters | User input | (see PanelDeControlRequestV1) |
| cadena_a | CadenaARequestV1? | No | Cadena A (payroll) configuration | User input | null |
| cadena_b | CadenaBRequestV1? | No | Cadena B (digital) configuration | User input | null |
| cadena_c | CadenaCRequestV1? | No | Cadena C (AI) configuration | User input | null |
| cadenas_activas | Set[str] | No | Which chains are active: {"A", "B", "C"} | Inferred from data shape | {"A"} |
| escenarios | List[EscenarioComercialV1] | No | Commercial scenarios (aliases: escenarios_comerciales) | User input | [] |
| metadata | ContractMetadataV1? | No | Optional request metadata (client_id, request_id, etc.) | User input | null |

**Validations**:
- At least one chain (A, B, or C) must be active; raises `ValueError` if all omitted
- `escenarios` must reference (canal, modalidad) pairs declared in `cadena_a.perfiles` (if any)
- When chain B is active, `panel.margen_b` should be set (soft check, defaults to 0.30)
- Legacy `panel.cadenas_activas` dict lifted to top-level `cadenas_activas` set automatically

**Examples**:
```json
{
  "panel": {
    "cliente": "Bancamía",
    "linea_negocio": "Cobranzas",
    "meses_contrato": 12,
    "margen": 0.15
  },
  "cadena_a": {
    "perfiles": [
      {
        "nombre": "Agente Básico",
        "rol": "Agente Basico",
        "canal": "WhatsApp",
        "modalidad": "Inbound",
        "fte": 5.0,
        "salario_base": 1200000.0
      }
    ]
  },
  "cadenas_activas": ["A"],
  "escenarios": [
    {
      "nombre": "Base",
      "canal": "WhatsApp",
      "modalidad": "Inbound",
      "margen": 0.15
    }
  ]
}
```

---

## ContractMetadataV1

**Location**: `contracts/api_v1/request/entry_data.py`  
**Purpose**: Optional metadata block accompanying every request  
**Version**: api-v1

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| client_id | str? | No | External client identifier | User input | "CLI-001" |
| request_id | str? | No | Request correlation ID for audit trail | User input | "REQ-20260531-001" |
| submitted_at | datetime? | No | Request submission timestamp (UTC) | User input | "2026-05-31T14:30:00Z" |
| source | str? | No | Source system or integration (e.g., "salesforce", "powerbi") | User input | "salesforce" |
| notes | str? | No | Free-text notes/comments about the request | User input | "Renegotiation scenario" |

**Validations**: None (all optional)

---

## PanelDeControlRequestV1

**Location**: `contracts/api_v1/request/panel.py`  
**Purpose**: Master deal parameters (frozen, strict)  
**Version**: api-v1

| Field | Type | Required | Constraints | Description | Origin | Example |
|-------|------|----------|-------------|-------------|--------|---------|
| cliente | str | Yes | (none) | Client name | User input | "Bancamía" |
| tipo_cliente | str | Yes | (none) | Client type (e.g., "Persona Jurídica") | User input | "Persona Jurídica" |
| linea_negocio | str | Yes | (none) | Service line (e.g., "Cobranzas", "SAC") | User input | "Cobranzas" |
| ciudad | str | Yes | (none) | City | User input | "Bogota" |
| sede | str | Yes | (none) | Office location | User input | "Toberin" |
| fecha_inicio | str | Yes | (none) | Contract start date (YYYY-MM-DD) | User input | "2026-06-01" |
| meses_contrato | int | No | 1 ≤ x ≤ 120 | Contract term in months | User input | 12 |
| margen | float | No | -1.0 ≤ x ≤ 1.0 | Margin on revenue (Cadena A) | User input | 0.15 |
| op_cont | float | No | 0.0 ≤ x ≤ 1.0 | Operational contingency (%) | User input | 0.05 |
| com_cont | float | No | 0.0 ≤ x ≤ 1.0 | Commercial contingency (%) | User input | 0.02 |
| markup | float | No | -1.0 ≤ x ≤ 10.0 | Markup on costs | User input | 0.1 |
| descuento | float | No | 0.0 ≤ x ≤ 1.0 | Volume discount (%) | User input | 0.05 |
| periodo_pago_dias | int | No | 0 ≤ x ≤ 365 | Payment term (days) | User input | 90 |
| activa_financiacion | bool | No | (none) | Enable financing costs | User input | true |
| antiguedad_cliente | str | No | (none) | Client tenure (e.g., "1-3 años") | User input | "1-3 años" |
| componente_indexacion_humano | str | No | (none) | Payroll indexation component (e.g., "IPC") | User input | "IPC" |
| componente_indexacion_tecnologico | str | No | (none) | Technology indexation component | User input | "IPC" |
| tasa_ica | float? | No | 0.0 ≤ x ≤ 1.0 | ICA tax rate (Colombia) | Excel/User | 0.0075 |
| tasa_gmf | float? | No | 0.0 ≤ x ≤ 1.0 | GMF tax rate (Colombia) | Excel/User | 0.004 |
| tasa_mensual_financ | float? | No | 0.0 ≤ x ≤ 1.0 | Monthly financing rate | Excel/User | 0.0153 |
| pct_rotacion | float? | No | 0.0 ≤ x ≤ 1.0 | Staff turnover rate (%) | Excel/User | 0.15 |
| pct_ausentismo | float? | No | 0.0 ≤ x ≤ 1.0 | Absence rate (%) | Excel/User | 0.08 |
| aplica_ley_1819 | bool | No | (none) | Legacy flag (ignored, retained for back-compat) | Excel | true |
| margen_b | float? | No | 0.0 ≤ x ≤ 1.0 | Margin target for Cadena B (V2-7) | User input | 0.30 |
| margen_c | float? | No | 0.0 ≤ x ≤ 1.0 | Margin target for Cadena C (V2-7) | User input | 0.20 |
| mes_ajuste_indexacion | int? | No | 1 ≤ x ≤ 12 | Month to apply annual indexation (V2-7) | User input | 6 |
| tasa_interes_mensual | float? | No | 0.0 ≤ x ≤ 1.0 | Monthly interest rate for financing (V2-7) | User input | 0.0153 |
| imprevistos | float? | No | 0.0 ≤ x ≤ 1.0 | Contingency reserve (% of gross revenue) — V2-5 new | User input | 0.03 |

**Validations**:
- `meses_contrato`: Must be between 1 and 120 inclusive
- All float ranges enforced via Pydantic `Field(ge=..., le=...)`

**Examples**:
```json
{
  "cliente": "Bancamía",
  "tipo_cliente": "Persona Jurídica",
  "linea_negocio": "Cobranzas",
  "ciudad": "Bogota",
  "sede": "Toberin",
  "fecha_inicio": "2026-06-01",
  "meses_contrato": 12,
  "margen": 0.15,
  "op_cont": 0.05,
  "com_cont": 0.02,
  "markup": 0.1,
  "descuento": 0.05,
  "periodo_pago_dias": 90,
  "activa_financiacion": true,
  "componente_indexacion_humano": "IPC",
  "componente_indexacion_tecnologico": "IPC",
  "tasa_ica": 0.0075,
  "tasa_gmf": 0.004,
  "tasa_mensual_financ": 0.0153,
  "pct_rotacion": 0.15,
  "pct_ausentismo": 0.08,
  "margen_b": 0.30,
  "margen_c": 0.20,
  "mes_ajuste_indexacion": 6,
  "tasa_interes_mensual": 0.0153,
  "imprevistos": 0.03
}
```

---

## PerfilCadenaAV1

**Location**: `contracts/api_v1/request/cadena_a.py`  
**Purpose**: Single operator profile within Cadena A (frozen)  
**Version**: api-v1

| Field | Type | Required | Constraints | Description | Origin | Example |
|-------|------|----------|-------------|-------------|--------|---------|
| nombre | str | Yes | (none) | Profile name (e.g., "Agente Básico") | User input | "Agente Básico" |
| rol | str | Yes | (none) | Role/title (e.g., "Agente Basico", "Supervisor") | HR catalog | "Agente Basico" |
| canal | str | Yes | (none) | Channel name (e.g., "WhatsApp", "Voz") | User input | "WhatsApp" |
| modalidad | str | No | (none) | Modality: "Inbound" or "Outbound" | User input | "Inbound" |
| fte | float | No | ≥ 0.0 | Full-time equivalent headcount | User input | 5.0 |
| pct_presencia | float | No | 0.0 ≤ x ≤ 1.0 | Presence ratio (e.g., 0.8 = 80% scheduled) | User input | 1.0 |
| comision_pct | float | No | 0.0 ≤ x ≤ 1.0 | Commission as % of gross (in mixed models) | User input | 0.05 |
| salario_base | float? | No | ≥ 0.0 | Base monthly salary in COP | User input | 1200000.0 |
| incluye_examenes | bool | No | (none) | Include medical/security exams cost | User input | true |
| incluye_seguridad | bool | No | (none) | Include security/background checks | User input | false |
| incluye_crucero | bool | No | (none) | Include "crucero" (cruise/retainer) cost | User input | false |
| no_payroll_mensual | float | No | ≥ 0.0 | Non-payroll monthly cost per agent | User input | 0.0 |
| dias_cap_inicial | int | No | 0 ≤ x ≤ 365 | Initial training days (amortized over contract) | User input | 10 |
| dias_cap_rotacion | int | No | 0 ≤ x ≤ 365 | Annual turnover training days | User input | 10 |
| tmo_segundos | float | No | ≥ 0.0 | Average handling time (seconds/call) | User input | 180.0 |
| modelo_cobro | ModeloCobroLiteral | No | (enum) | Billing model (see enums section) | User input | "Fijo FTE" |
| pct_fijo | float | No | 0.0 ≤ x ≤ 1.0 | Fixed component % in hybrid billing | User input | 1.0 |
| vol_cadena_a_mensual | float | No | ≥ 0.0 | Monthly volume handled by Cadena A (K50 in Excel) | Computed | 1000.0 |

**Validations**:
- `fte` ≥ 0.0
- `pct_presencia` in [0.0, 1.0]
- `comision_pct` in [0.0, 1.0]
- `salario_base` ≥ 0.0 if provided
- `dias_cap_inicial`, `dias_cap_rotacion` in [0, 365]

**Examples**:
```json
{
  "nombre": "Agente Básico",
  "rol": "Agente Basico",
  "canal": "WhatsApp",
  "modalidad": "Inbound",
  "fte": 5.0,
  "pct_presencia": 1.0,
  "comision_pct": 0.05,
  "salario_base": 1200000.0,
  "incluye_examenes": true,
  "incluye_seguridad": false,
  "incluye_crucero": false,
  "no_payroll_mensual": 0.0,
  "dias_cap_inicial": 10,
  "dias_cap_rotacion": 10,
  "tmo_segundos": 180.0,
  "modelo_cobro": "Fijo FTE",
  "pct_fijo": 1.0,
  "vol_cadena_a_mensual": 1000.0
}
```

---

## CadenaARequestV1

**Location**: `contracts/api_v1/request/cadena_a.py`  
**Purpose**: Cadena A (payroll/HR) configuration (frozen)  
**Version**: api-v1

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| perfiles | List[PerfilCadenaAV1] | No | Operator profiles | User input | (see PerfilCadenaAV1) |

---

## CanalCadenaBV1

**Location**: `contracts/api_v1/request/cadena_b.py`  
**Purpose**: Digital platform channel (frozen)  
**Version**: api-v1

| Field | Type | Required | Constraints | Description | Origin | Example |
|-------|------|----------|-------------|-------------|--------|---------|
| nombre | str | Yes | (none) | Channel name (e.g., "WhatsApp", "API") | User input | "WhatsApp" |
| modalidad | str | Yes | (none) | Modality/integration type | User input | "Inbound" |
| producto | str | Yes | (none) | Product code (e.g., "WHATSAPP_API") | User input | "WHATSAPP_API" |
| volumen_mensual | float | No | ≥ 0.0 | Monthly transaction volume | User input | 10000.0 |
| activo | bool | No | (none) | Is this channel active | User input | true |
| opex_fijo | float | No | ≥ 0.0 | Fixed monthly operational expense (COP) | User input | 500000.0 |
| tarifa_unitaria | float | No | ≥ 0.0 | Cost per transaction (COP) | User input | 50.0 |
| pct_escalamiento | float | No | 0.0 ≤ x ≤ 1.0 | Escalation % for volumes above baseline | User input | 0.1 |
| costo_escalamiento | float | No | ≥ 0.0 | Fixed cost for escalation | User input | 0.0 |

---

## ItemOpexConsumoV1

**Location**: `contracts/api_v1/request/cadena_b.py`  
**Purpose**: Variable consumption item (e.g., API credits, tokens)  
**Version**: api-v1

| Field | Type | Required | Constraints | Description | Origin | Example |
|-------|------|----------|-------------|-------------|--------|---------|
| nombre | str | Yes | (none) | Item name (e.g., "Token IA") | User input | "Token IA" |
| producto | str | Yes | (none) | Product type | User input | "OpenAI GPT" |
| modalidad | str | Yes | (none) | Modalidad/integration type | User input | "API" |
| canal | str | Yes | (none) | Associated channel | User input | "WhatsApp" |
| valor_unitario | float | No | ≥ 0.0 | Cost per unit (COP) | User input | 0.001 |
| cantidad | float | No | ≥ 0.0 | Monthly quantity consumed | User input | 1000000.0 |
| tipo_cobro | str | No | (none) | Billing type (e.g., "Unitario", "Fijo") | User input | "Unitario" |

---

## MiembroEquipoSMV1

**Location**: `contracts/api_v1/request/cadena_b.py`  
**Purpose**: Support & Maintenance team member  
**Version**: api-v1

| Field | Type | Required | Constraints | Description | Origin | Example |
|-------|------|----------|-------------|-------------|--------|---------|
| rol | str | Yes | (none) | Role (e.g., "Senior Engineer") | HR catalog | "Senior Engineer" |
| activo | bool | No | (none) | Is this role active | User input | true |
| pct_dedicacion | float | No | 0.0 ≤ x ≤ 1.0 | Allocation % (e.g., 0.5 = 50% of time) | User input | 1.0 |

---

## DispositivoSMV1

**Location**: `contracts/api_v1/request/cadena_b.py`  
**Purpose**: Technology device for S&M team (amortized)  
**Version**: api-v1

| Field | Type | Required | Constraints | Description | Origin | Example |
|-------|------|----------|-------------|-------------|--------|---------|
| tipo | str | Yes | (none) | Device type (e.g., "Laptop", "Server") | User input | "Laptop" |
| costo_unitario | float | No | ≥ 0.0 | Unit cost in COP | User input | 3000000.0 |
| cantidad | float | No | ≥ 0.0 | Number of units | User input | 2.0 |
| meses_amortizacion | int | No | 1 ≤ x ≤ 360 | Amortization period (months) | User input | 36 |

**Computed Properties**:
```python
costo_mensual = (costo_unitario * cantidad) / meses_amortizacion
```

---

## CadenaBRequestV1

**Location**: `contracts/api_v1/request/cadena_b.py`  
**Purpose**: Cadena B (digital platform) complete configuration (frozen)  
**Version**: api-v1

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| canales | List[CanalCadenaBV1] | No | Digital channels | User input | [] |
| opex_consumo_variable | List[ItemOpexConsumoV1] | No | Variable consumption items | User input | [] |
| equipo_sm | List[MiembroEquipoSMV1] | No | Support & Maintenance team | User input | [] |
| dispositivos_sm | List[DispositivoSMV1] | No | Devices for S&M team | User input | [] |
| inversion_plataforma | float | No | Platform investment (capex) | User input | 0.0 |
| fte_equipo_sm | float | No | FTE equivalent for S&M team | User input | 1.0 |
| amortizar_dispositivos_sm | bool | No | Amortize S&M devices | User input | true |

---

## CanalCadenaCV1

**Location**: `contracts/api_v1/request/cadena_c.py`  
**Purpose**: AI/Integration channel (frozen)  
**Version**: api-v1

| Field | Type | Required | Constraints | Description | Origin | Example |
|-------|------|----------|-------------|-------------|--------|---------|
| nombre | str | Yes | (none) | Channel name (e.g., "OpenAI") | User input | "OpenAI" |
| modalidad | str | Yes | (none) | Modality/integration type | User input | "API" |
| volumen_mensual | float | No | ≥ 0.0 | Monthly transaction volume | User input | 5000.0 |
| activo | bool | No | (none) | Is this channel active | User input | true |
| opex_fijo_integ | float | No | ≥ 0.0 | Fixed integration opex (COP) | User input | 300000.0 |
| opex_var_integ | float | No | ≥ 0.0 | Variable integration opex | User input | 0.0 |
| pct_escalamiento | float | No | 0.0 ≤ x ≤ 1.0 | Escalation % | User input | 0.05 |
| costo_escalamiento | float | No | ≥ 0.0 | Escalation fixed cost | User input | 0.0 |

---

## MiembroEquipoTransversalV1

**Location**: `contracts/api_v1/request/cadena_c.py`  
**Purpose**: Cross-functional team member (Cadena C)  
**Version**: api-v1

| Field | Type | Required | Constraints | Description | Origin | Example |
|-------|------|----------|-------------|-------------|--------|---------|
| rol | str | Yes | (none) | Role (e.g., "IA Specialist") | HR catalog | "IA Specialist" |
| activo | bool | No | (none) | Is this role active | User input | true |
| pct_dedicacion | float | No | 0.0 ≤ x ≤ 1.0 | Allocation % | User input | 0.5 |

---

## CadenaCRequestV1

**Location**: `contracts/api_v1/request/cadena_c.py`  
**Purpose**: Cadena C (AI/Integration) complete configuration (frozen)  
**Version**: api-v1

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| canales | List[CanalCadenaCV1] | No | AI/Integration channels | User input | [] |
| equipo_transversal | List[MiembroEquipoTransversalV1] | No | Cross-functional team | User input | [] |
| inversion_anual | float | No | Annual investment (capex) | User input | 0.0 |

---

## EscenarioComercialV1

**Location**: `contracts/api_v1/request/escenarios.py`  
**Purpose**: Commercial billing scenario (frozen)  
**Version**: api-v1

| Field | Type | Required | Constraints | Description | Origin | Example |
|-------|------|----------|-------------|-------------|--------|---------|
| nombre | str | Yes | (none) | Scenario name | User input | "Base" |
| canal | str | Yes | (none) | Referenced channel | User input | "WhatsApp" |
| modalidad | str | Yes | (none) | Referenced modality | User input | "Inbound" |
| modelo_cobro | str? | No | (none) | Billing model override | User input | "Fijo FTE" |
| margen | float? | No | -1.0 ≤ x ≤ 1.0 | Margin override for this scenario | User input | 0.18 |
| parametros | Dict[str, Any] | No | (none) | Extra parameters (flexible) | User input | {} |

**Notes**: Extra fields allowed (frozen=True but extra="allow")

---

# DOMAIN MODELS (Internal Representation)

## PanelDeControl

**Location**: `domain/models/panel.py`  
**Purpose**: Internal master deal parameters (mirrors PanelDeControlRequestV1 with calculated defaults)  
**Version**: internal

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| cliente | str | Yes | Client name | User input | "Bancamía" |
| tipo_cliente | str | Yes | Client type | User input | "Persona Jurídica" |
| linea_negocio | str | Yes | Service line | User input | "Cobranzas" |
| fecha_inicio | str | Yes | Start date (YYYY-MM-DD) | User input | "2026-06-01" |
| meses_contrato | int | Yes | Contract term (months) | User input | 12 |
| margen | float | Yes | Cadena A margin | User input | 0.15 |
| op_cont | float | Yes | Operational contingency (%) | User input | 0.05 |
| com_cont | float | Yes | Commercial contingency (%) | User input | 0.02 |
| markup | float | Yes | Markup on costs | User input | 0.1 |
| descuento | float | Yes | Volume discount (%) | User input | 0.05 |
| tasa_ica | float | Yes | ICA tax rate | Excel/default | 0.0075 |
| tasa_gmf | float | Yes | GMF tax rate | Excel/default | 0.004 |
| activa_financiacion | bool | Yes | Enable financing costs | User input | true |
| periodo_pago_dias | int | Yes | Payment term (days) | User input | 90 |
| tasa_mensual_financ | float | Yes | Monthly financing rate | User input | 0.0153 |
| ciudad | str | No | City | User input | "Bogota" |
| sede | str | No | Office | User input | "Toberin" |
| antiguedad_cliente | str | No | Client tenure | User input | "1-3 años" |
| pct_ausentismo | float | No | Absence rate (%) | Excel/default | 0.08 |
| horas_formacion_mensual | int | No | Monthly training hours | Excel/default | 0 |
| indexacion | Indexacion? | No | Indexation config | Computed | (see Indexacion) |
| aplica_ley_1819 | bool | No | Legacy Ley 1819 flag (ignored) | User input | true |
| imprevistos | float | No | Contingency reserve (%) — V2-5 | User input | 0.03 |
| margen_b | float | No | Cadena B margin target — V2-7 | User input | 0.30 |
| margen_c | float | No | Cadena C margin target — V2-7 | User input | 0.20 |
| mes_ajuste_indexacion | int | No | Month for annual indexation — V2-7 | User input | 6 |
| tasa_interes_mensual | float | No | Monthly interest rate — V2-7 | User input | 0.0153 |
| tasa_comision_administracion | float | No | Admin fee rate — V2-5 | User input | 0.0 |
| complejidad_especialista | str | No | Project specialist complexity ("BAJA", "MEDIA", "ALTA") | HR catalog | "ALTA" |
| cadenas_activas | CadenasActivas | No | Active chains state | Computed | (see CadenasActivas) |
| tarifa_diaria_capacitacion | float | No | Daily training rate (COP) | User input | 0.0 |
| tarifa_crucero | float | No | Monthly retainer per agent (COP) — V2-7 | User input | 0.0 |

**Validations**: All numeric ranges enforced during deserialization

---

## PerfilCadenaA

**Location**: `domain/models/panel.py`  
**Purpose**: Internal operator profile (mirrors PerfilCadenaAV1 with computed fields)  
**Version**: internal

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| nombre | str | Yes | Profile name | User input | "Agente Básico" |
| modalidad | str | Yes | Modality (Inbound/Outbound) | User input | "Inbound" |
| canal | str | Yes | Channel name | User input | "WhatsApp" |
| fte | float | Yes | FTE headcount | User input | 5.0 |
| pct_presencia | float | No | Presence ratio | User input | 1.0 |
| salario_base | float | No | Base salary (COP) | User input | 1200000.0 |
| salario_cargado | float | No | Loaded salary (with payroll taxes) — Computed | Computed | 1500000.0 |
| comision_pct | float | No | Commission % | User input | 0.05 |
| dias_cap_inicial | int | No | Initial training days | User input | 10 |
| dias_cap_rotacion | int | No | Annual training days | User input | 10 |
| tmo_segundos | float | No | Handling time (seconds) | User input | 180.0 |
| incluye_examenes | bool | No | Include medical exams | User input | true |
| incluye_seguridad | bool | No | Include security checks | User input | false |
| incluye_crucero | bool | No | Include retainer cost | User input | false |
| es_soporte | bool | No | Is support staff (no workstation) | Computed | false |
| fte_examenes | float | No | FTE for exams (base + supervisors) — Computed | Computed | 5.5 |
| modelo_cobro | str | No | Billing model (Vision Tarifas) | User input | "Fijo FTE" |
| pct_fijo | float | No | Fixed % in hybrid billing | User input | 1.0 |
| no_payroll_mensual | float | No | Non-payroll cost (COP/month) | User input | 0.0 |
| cadena_b_mensual | float | No | Cadena B cost attribution (COP/month) — From Excel | Excel | 0.0 |
| costos_financieros_mensual | float | No | Financial costs attribution (COP/month) — From Excel | Excel | 0.0 |
| tipo_carga | str | No | Labor type (HR catalog) | HR catalog | "EMPLEADO_ESTANDAR" |
| vol_cadena_a_mensual | float | No | Monthly volume (denominator for CTS) | Computed | 1000.0 |
| cargo_tipo | str | No | Cargo classification (HR-derived) | HR catalog | "DESCONOCIDO" |
| opex_fijo_mensual | float | No | Per-channel IT opex (COP/month) | Computed | 0.0 |
| inversiones_amortizables | List[dict] | No | Term-based CAPEX items (V2-7) | User input | [] |

---

## ParametrosNomina

**Location**: `domain/models/panel.py`  
**Purpose**: Payroll calculation parameters (shared across profiles)  
**Version**: internal

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| mes_inicio | int | Yes | Contract start month (1-12) | Computed | 6 |
| mes_fin | int | Yes | Contract end month (1-12) | Computed | 5 |
| pct_aumento_salarial | float | Yes | Annual salary increase (%) | Excel | 0.04 |
| mes_aplicacion_aumento | int | Yes | Month to apply increase | Excel | 1 |
| tarifa_dia_cap | float | Yes | Training day rate (COP) | User input | 100000.0 |
| costo_examen_medico | float | Yes | Medical exam cost (COP) | Excel | 50000.0 |
| costo_estudio_seg | float | No | Security study cost (COP) | Excel | 0.0 |
| factor_indexacion_base | float | No | Indexation factor for year 1 | Computed | 1.0 |
| meses_contrato | int | No | Contract length (for amortization) | User input | 12 |
| tarifa_crucero | float | No | Monthly retainer per agent (COP) — V2-7 | User input | 0.0 |

---

## ParametrosNoPayroll

**Location**: `domain/models/panel.py`  
**Purpose**: Non-payroll costs per workstation  
**Version**: internal

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| opex_ti_por_estacion | float | Yes | IT opex per station (COP/month) | Excel | 100000.0 |
| capex_por_estacion | float | Yes | CAPEX per station (COP, amortized) | Excel | 50000.0 |
| arriendo_por_estacion | float | Yes | Rent per station (COP/month) | Excel | 200000.0 |
| energia_por_estacion | float | Yes | Utilities per station (COP/month) | Excel | 20000.0 |
| vigilancia_por_estacion | float | Yes | Security per station (COP/month) | Excel | 50000.0 |
| aseo_por_estacion | float | Yes | Cleaning per station (COP/month) | Excel | 30000.0 |
| otros_fijos_por_estacion | float | No | Other fixed costs per station | Excel | 0.0 |
| capex_inicial_por_estacion | float | No | Initial CAPEX per station | Excel | 0.0 |
| inversiones_amortizables | List[dict] | No | Term-based amortizable items (V2-7 Excel K167/K168) | Excel | [] |

**Note**: When `inversiones_amortizables` is non-empty, it replaces the single `capex_por_estacion` value. Each item has:
```python
{"precio_mensual": float, "cantidad": float, "meses": int, "factor": float}
```

---

## ParametrosCadenaB

**Location**: `domain/models/panel.py`  
**Purpose**: Cadena B (digital platform) complete parameters  
**Version**: internal

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| canales | List[CanalCadenaB] | No | Digital channels | User input | [] |
| opex_consumo_variable | List[ItemOpexConsumoB] | No | Variable consumption items | User input | [] |
| equipo_sm | List[MiembroEquipo] | No | S&M team members | User input | [] |
| dispositivos_sm | List[DispositivoSM] | No | S&M devices | User input | [] |
| costo_personal_sm | float | No | Total S&M payroll (COP/month) — Computed | Computed | 0.0 |
| opex_herramientas_sm | float | No | S&M tools opex (COP/month) — Computed | Computed | 0.0 |
| costo_personal_hitl | float | No | HITL payroll (COP/month) — Computed | Computed | 0.0 |
| opex_herramientas_hitl | float | No | HITL tools opex (COP/month) — Computed | Computed | 0.0 |
| inversion_mensual | float | No | Monthly platform investment (COP) — Computed | Computed | 0.0 |
| pct_aumento_personal | float | No | Annual tech team salary increase (%) | Excel | 0.05 |
| mes_aplicacion_aumento | int | No | Month to apply tech increase | Excel | 1 |

---

## ParametrosCadenaC

**Location**: `domain/models/panel.py`  
**Purpose**: Cadena C (AI/Integration) complete parameters  
**Version**: internal

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| canales | List[CanalCadenaC] | No | AI/Integration channels | User input | [] |
| equipo_transversal | List[MiembroEquipo] | No | Cross-functional team | User input | [] |
| costo_equipo_integ | float | No | Integration team payroll (COP/month) — Computed | Computed | 0.0 |
| opex_herramientas_integ | float | No | Integration tools opex (COP/month) — Computed | Computed | 0.0 |
| costo_personal_hitl | float | No | HITL payroll (COP/month) — Computed | Computed | 0.0 |
| opex_herramientas_hitl | float | No | HITL tools opex (COP/month) — Computed | Computed | 0.0 |
| inversion_anual | float | No | Annual investment (COP) | User input | 0.0 |
| pct_aumento_tecnologico | float | No | Annual tech salary increase (%) | Excel | 0.05 |
| mes_aplicacion_aumento | int | No | Month to apply increase | Excel | 1 |

---

## ParametrosCalculo

**Location**: `domain/models/panel.py`  
**Purpose**: Technical calculation parameters  
**Version**: internal

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| pct_rotacion | float | Yes | Staff turnover rate (%) | Panel | 0.15 |
| pct_examen_anual | float | Yes | Annual exam rate (%) | Excel | 1.0 |
| pct_cumplimiento_variable | float | No | Variable component fulfillment (%) | Excel | 0.70 |

---

## PricingRequest

**Location**: `domain/models/panel.py`  
**Purpose**: Complete facade object grouping all calculation inputs  
**Version**: internal

| Field | Type | Required | Description | Origin | Example |
|-------|------|----------|-------------|--------|---------|
| panel | PanelDeControl | Yes | Master parameters | User input | (see PanelDeControl) |
| perfiles_cadena_a | List[PerfilCadenaA] | Yes | Operator profiles | User input | [] |
| parametros_nomina | ParametrosNomina | Yes | Payroll parameters | Computed | (see ParametrosNomina) |
| parametros_no_payroll | ParametrosNoPayroll | Yes | Non-payroll parameters | Excel | (see ParametrosNoPayroll) |
| cadena_b | ParametrosCadenaB | Yes | Cadena B parameters | User input | (see ParametrosCadenaB) |
| cadena_c | ParametrosCadenaC | Yes | Cadena C parameters | User input | (see ParametrosCadenaC) |
| parametros_calculo | ParametrosCalculo | Yes | Calculation parameters | Excel | (see ParametrosCalculo) |
| polizas_usuario | List[PolizaContractual]? | No | User-provided insurance policies | User input | [] |
| escenarios | List[EscenarioComercial] | No | Commercial billing scenarios | User input | [] |
| cadenas_activas | CadenasActivas | No | Active chains state | Computed | (see CadenasActivas) |

---

# RESULT MODELS (Calculation Outputs)

## ResultadoNomina

**Location**: `domain/models/results.py`  
**Purpose**: Monthly payroll costs for a profile  
**Version**: internal

| Field | Type | Description | Computed From |
|-------|------|-------------|--------|
| salario_fijo | float | Fixed monthly salary (COP) | profile.salario_cargado × fte × 1/months |
| comisiones | float | Variable commissions (COP) | (gross - target_costs) × commission_pct |
| capacitacion_inicial | float | Initial training cost (COP) | días_cap × tarifa_día / meses_contrato |
| capacitacion_rotacion | float | Annual turnover training (COP) | rotation_rate × tarifa_día |
| examenes | float | Medical/security exams (COP) | exam_cost × fte × multiplier |
| seguridad | float | Security/background studies (COP) | study_cost × fte |
| crucero | float | Retainer/cruise fee (COP/month) — V2-7 | tarifa_crucero × fte |

**Computed Properties**:
```python
total = salario_fijo + comisiones + capacitacion_inicial + capacitacion_rotacion + examenes + seguridad + crucero
```

---

## ResultadoNoPayroll

**Location**: `domain/models/results.py`  
**Purpose**: Monthly non-payroll costs per workstation  
**Version**: internal

| Field | Type | Description | Computed From |
|-------|------|-------------|--------|
| opex_ti | float | IT operational expense (COP) | param.opex_ti_por_estacion |
| capex | float | Amortized capital expense (COP) | param.capex_por_estacion or inversiones_amortizables |
| costos_fijos | float | Fixed costs (rent, utilities, cleaning, security) (COP) | sum(arriendo + energia + vigilancia + aseo + otros) |

**Computed Properties**:
```python
total = opex_ti + capex + costos_fijos
```

---

## ResultadoCadenaB

**Location**: `domain/models/results.py`  
**Purpose**: Monthly Cadena B (digital platform) costs  
**Version**: internal

| Field | Type | Description | Computed From |
|-------|------|-------------|--------|
| opex_fijo | float | Fixed operational expense (COP) | channel.opex_fijo summed |
| inversiones | float | Investments/capex (COP) | platform_investment / meses |
| soporte_mantenimiento | float | Support & maintenance costs (COP) | s&m team + devices |
| costo_variable | float | Usage-based costs (COP) | channel.tarifa × volume |
| escalamiento | float | Escalation costs (COP) | above-baseline volume × escalation_pct |
| hitl | float | Human-in-the-loop costs (COP) | hitl team payroll |

**Computed Properties**:
```python
total = opex_fijo + inversiones + soporte_mantenimiento + costo_variable + escalamiento + hitl
```

---

## ResultadoCadenaC

**Location**: `domain/models/results.py`  
**Purpose**: Monthly Cadena C (AI/Integration) costs  
**Version**: internal

| Field | Type | Description | Computed From |
|-------|------|-------------|--------|
| tarifa_proveedor | float | Vendor fees (COP) | channel.tarifa × volume |
| opex_fijo_integ | float | Fixed integration opex (COP) | channel.opex_fijo_integ |
| opex_var_integ | float | Variable integration opex (COP) | channel.opex_var_integ |
| inversiones | float | Investments/capex (COP) | investment / meses |
| equipo_integ | float | Integration team payroll (COP) | team member costs |
| escalamiento | float | Escalation costs (COP) | above-baseline volume × escalation_pct |
| hitl | float | Human-in-the-loop costs (COP) | hitl team payroll |

**Computed Properties**:
```python
total = tarifa_proveedor + opex_fijo_integ + opex_var_integ + inversiones + equipo_integ + escalamiento + hitl
total_pyg = tarifa_proveedor + opex_fijo_integ + inversiones + escalamiento  # excludes hitl, equipo_integ, opex_var_integ
```

**Note**: `total_pyg` is used for P&G display; the excluded components flow into financial costs

---

## CostosTotalesMes

**Location**: `domain/models/results.py`  
**Purpose**: Total monthly cost breakdown across all chains  
**Version**: internal

| Field | Type | Description | Computed From |
|-------|------|-------------|--------|
| mes | int | Month number (1-N) | (iteration index) |
| payroll_a | float | Cadena A payroll (COP) | sum(ResultadoNomina.total per profile) |
| no_payroll_a | float | Cadena A non-payroll (COP) | ResultadoNoPayroll.total × fte_cadena_a |
| costo_b | float | Cadena B total (COP) | ResultadoCadenaB.total |
| costo_c | float | Cadena C P&G display (COP) | ResultadoCadenaC.total_pyg |
| costo_c_fin | float | Cadena C full financial (COP) | ResultadoCadenaC.total |

**Computed Properties**:
```python
costo_a = payroll_a + no_payroll_a
total = costo_a + costo_b + costo_c
total_fin = costo_a + costo_b + costo_c_fin
```

---

## CostosFinancierosMes

**Location**: `domain/models/results.py`  
**Purpose**: Monthly financial costs (taxes, insurance, financing)  
**Version**: internal

| Field | Type | Description | Computed From |
|-------|------|-------------|--------|
| financiacion | float | Financing cost (COP) | total_cost × tasa_mensual_financ |
| polizas | float | Insurance premiums (COP) | sum(policy rate × applicable base) |
| polizas_a | float | Cadena A insurance (COP) | (subset of polizas) |
| polizas_b | float | Cadena B insurance (COP) | (subset of polizas) |
| polizas_c | float | Cadena C insurance (COP) | (subset of polizas) |
| ica | float | ICA tax (COP) | applicable_base × tasa_ica |
| ica_a | float | ICA on Cadena A (COP) | (subset of ica) |
| ica_c | float | ICA on Cadena C (COP) | (subset of ica) |
| gmf | float | GMF tax (COP) | applicable_base × tasa_gmf |
| gmf_a | float | GMF on Cadena A (COP) | (subset of gmf) |
| gmf_c | float | GMF on Cadena C (COP) | (subset of gmf) |
| comision_administracion | float | Admin fee (COP) — V2-5 | gross_revenue × tasa_comision_administracion |
| comision_admin_cadena_a | float | Admin fee attributed to Cadena A (COP) — V2-5 | (subset of comision_administracion) |
| costo_financiero_vt_cadena_a | float | Cadena A financial subtotal for Vision Tarifas (COP) | polizas_a_vt + ica_a_vt + gmf_a_vt |

**Computed Properties**:
```python
total = financiacion + polizas + ica + gmf + comision_administracion
```

---

## PyGMensual

**Location**: `domain/models/results.py`  
**Purpose**: Monthly income statement (Profit & Loss)  
**Version**: internal

**Income Fields**:
| Field | Type | Description | Computed From |
|-------|------|-------------|--------|
| mes | int | Month number | (iteration index) |
| rampup | float | Ramp-up factor (0..1) | (smoothing curve) |
| ingreso_bruto_a | float | Cadena A gross revenue (COP) | (pricing formula) |
| ingreso_bruto_b | float | Cadena B gross revenue (COP) | (pricing formula) |
| ingreso_bruto_c | float | Cadena C gross revenue (COP) | (pricing formula) |
| contingencia_op | float | Operational contingency (COP) | ingreso_bruto × op_cont |
| contingencia_com | float | Commercial contingency (COP) | ingreso_bruto × com_cont |
| markup_ingreso | float | Markup adjustment (COP) | ingreso_bruto × markup |
| descuento_ingreso | float | Volume discount (COP) | ingreso_bruto × descuento |

**Cost Fields**:
| Field | Type | Description | Computed From |
|-------|------|-------------|--------|
| payroll_a | float | Cadena A payroll (COP) | ResultadoNomina.total × fte |
| no_payroll_a | float | Cadena A non-payroll (COP) | ResultadoNoPayroll.total × estaciones |
| costo_b | float | Cadena B cost (COP) | ResultadoCadenaB.total |
| costo_c | float | Cadena C cost P&G (COP) | ResultadoCadenaC.total_pyg |
| costo_c_fin | float | Cadena C cost financial (COP) | ResultadoCadenaC.total |
| ica | float | ICA tax (COP) | CostosFinancierosMes.ica |
| ica_a | float | ICA on Cadena A (COP) | (subset) |
| ica_c | float | ICA on Cadena C (COP) | (subset) |
| gmf_a | float | GMF on Cadena A (COP) | (subset) |
| gmf_c | float | GMF on Cadena C (COP) | (subset) |
| gmf | float | Total GMF (COP) | CostosFinancierosMes.gmf |
| polizas | float | Insurance (COP) | CostosFinancierosMes.polizas |
| polizas_a | float | Insurance on Cadena A (COP) | (subset) |
| polizas_b | float | Insurance on Cadena B (COP) | (subset) |
| polizas_c | float | Insurance on Cadena C (COP) | (subset) |
| financiacion | float | Financing cost (COP) | CostosFinancierosMes.financiacion |
| imprevistos_ingreso | float | Contingency reserve (COP) — V2-5 | ingreso_bruto × panel.imprevistos |
| comision_administracion | float | Admin fee (COP) — V2-5 | CostosFinancierosMes.comision_administracion |
| comision_admin_cadena_a | float | Admin fee attributed to Cadena A (COP) — V2-5 | (subset) |
| costo_financiero_vt_cadena_a | float | Cadena A financial sub-total (COP) | (Vision Tarifas attribution) |

**Accumulators** (updated during iteration):
| Field | Type | Description |
|-------|------|-------------|
| acum_ingreso_bruto | float | Year-to-date gross revenue |
| acum_ingreso_neto | float | Year-to-date net revenue |
| acum_costo_total | float | Year-to-date total costs |
| acum_costos_financieros | float | Year-to-date financial costs |
| acum_contribucion | float | Year-to-date contribution |

**Computed Properties**:
```python
ingreso_bruto = ingreso_bruto_a + ingreso_bruto_b + ingreso_bruto_c
ingreso_neto = ingreso_bruto + contingencia_op + contingencia_com + markup_ingreso - descuento_ingreso - imprevistos_ingreso
costo_a = payroll_a + no_payroll_a
costos_financieros = ica + gmf + polizas + financiacion + comision_administracion
costo_operativo = costo_a + costo_b + costo_c
costo_total = costo_a + costo_b + costo_c
contribucion = ingreso_neto - costo_total
pct_contribucion = contribucion / ingreso_neto if ingreso_neto else 0.0
utilidad_neta = contribucion
pct_utilidad_neta = utilidad_neta / ingreso_neto if ingreso_neto else 0.0
```

---

## KPIsDeal

**Location**: `domain/models/results.py`  
**Purpose**: Deal-level aggregate KPIs  
**Version**: internal

| Field | Type | Description | Computed From |
|-------|------|-------------|--------|
| costo_mensual_promedio | float | Average monthly cost (COP) | sum(monthly costs) / meses_activos |
| costo_cadena_a_promedio | float | Average monthly Cadena A cost (COP) | sum(costo_a per month) / meses_activos |
| ingreso_mensual | float | Average monthly revenue (COP) | ingreso_bruto_total / meses_activos |
| facturacion_mensual_proyectada | float | Projected monthly revenue (COP) | (from tariffs × volume) |
| ingreso_bruto_total | float | Total gross revenue (COP) | sum(ingreso_bruto per month) |
| ingreso_neto_total | float | Total net revenue (COP) | sum(ingreso_neto per month) |
| costo_total_contrato | float | Total contract cost (COP) | sum(costo_total per month) |
| contribucion_total | float | Total contribution (COP) | ingreso_neto_total - costo_total_contrato |
| utilidad_neta_total | float | Total net profit (COP) | contribucion_total |
| pct_utilidad_neta_total | float | Net profit margin (0..1) | utilidad_neta_total / ingreso_neto_total |
| valor_total_deal | float | Deal total value (COP) | ingreso_neto_total |
| margen_minimo_requerido | float | Minimum required margin (0..1) | (from business rules) |
| cumple_margen_minimo | bool | Does deal meet minimum margin | pct_utilidad_neta_total ≥ margen_minimo_requerido |

---

## PricingResult

**Location**: `domain/models/results.py`  
**Purpose**: Complete calculation output (root object returned by engine)  
**Version**: internal

| Field | Type | Required | Description | Origin |
|-------|------|----------|-------------|--------|
| kpis | KPIsDeal | Yes | Aggregate KPIs | Computed |
| pyg_por_mes | List[PyGMensual] | Yes | Monthly P&L statements (1 per contract month) | Computed |
| panel | PanelDeControl | Yes | Master parameters (for reference) | Input |
| cost_to_serve | ResultadoCostToServe? | No | Cost-to-serve analysis | Computed |
| vision_tarifas | ResultadoVisionTarifas? | No | Tariff structure breakdown | Computed |
| waterfall | WaterfallPromedio? | No | Average cost waterfall | Computed |
| reglas_negocio | List[ReglaNegocios] | No | Business rules evaluated | Computed |
| evaluacion_riesgo | EvaluacionRiesgo? | No | Risk assessment | Computed |
| vision_pyg | VisionPyG? | No | Structured P&G vision | Computed |
| vision_imprimible | VisionImprimible? | No | Formatted printable vision | Computed |
| datasets_vision | DatasetsVision? | No | Auxiliary data for frontend | Computed |
| audit_trace | Dict? | No | Calculation audit trail | Computed |

---

# VISION MODELS (Formatted Display)

## DesgloseCTSCadenaA

**Location**: `domain/models/visions.py`  
**Purpose**: Cost-to-Serve sub-components for Cadena A  
**Version**: internal

| Field | Type | Description | Excel Reference |
|-------|------|-------------|--------|
| nomina | float | Total payroll (aggregate, backward-compat) | C036 |
| no_payroll | float | Total non-payroll (aggregate) | C046 |
| nomina_loaded | float | Payroll with employer taxes | C036 |
| salario_fijo | float | Fixed salary | C037 |
| salario_variable | float | Variable compensation | C038 |
| capacitacion_inicial | float | Initial training | C039 |
| capacitacion_rotacion | float | Turnover training | C040 |
| examenes | float | Medical/security exams | C041 |
| estudios_seguridad | float | Security studies | C042 |
| crucero | float | Retainer fee (non-zero for cruise services) — GAP-CTS-HIER-1 | Row 43 |
| opex_fijo | float | Fixed IT opex | C046 |
| inversiones | float | Amortized investments | C047 |
| costos_fijos_estacion | float | Station fixed costs (rent, utilities, etc.) | C048 |

**Computed Property**:
```python
total = nomina + no_payroll
```

---

## DesgloseCTSCadenaB

**Location**: `domain/models/visions.py`  
**Purpose**: Cost-to-Serve sub-components for Cadena B (per unit volume)  
**Version**: internal

| Field | Type | Description | Excel Reference |
|-------|------|-------------|--------|
| componente_fijo | float | Fixed component | G035 |
| componente_variable | float | Variable component | G041 |
| opex | float | Fixed opex | G036 |
| inversiones | float | Investments | G037 |
| soporte_mantenimiento | float | Support & maintenance | G038 |
| tarifa | float | Vendor tariff | G042 |
| opex_variable | float | Variable opex | G043 |
| tasa_escalamiento | float | Escalation rate | G044 |
| hitl | float | Human-in-the-loop cost | G045 |

**Computed Property**:
```python
total = componente_fijo + componente_variable
```

---

## CanalCTSDetalle

**Location**: `domain/models/visions.py`  
**Purpose**: Per-channel CTS detail (Excel CTS rows 90-125)  
**Version**: internal

| Field | Type | Description | Formula |
|-------|------|-------------|---------|
| canal | str | Channel name | (user input) |
| modalidad | str | Modality (Inbound/Outbound) | (user input) |
| fte | float | FTE per channel (denominator) | Panel!M19:M25 |
| participacion_cadena_a | float | Cadena A volume % | Panel!P19:P25 |
| cts | float | Cost to serve per FTE | SUMPRODUCT(costs) / fte / meses |
| payroll | float | Payroll per FTE | (sum of salary components) / fte / meses |
| nomina_loaded | float | Payroll with taxes | (sum with employer contributions) / fte / meses |
| salario_fijo | float | Fixed salary per FTE | (base × fte) / fte / meses |
| salario_variable | float | Variable salary per FTE | (commissions) / fte / meses |
| capacitacion_inicial | float | Initial training per FTE | (days × rate) / fte / meses |
| capacitacion_rotacion | float | Turnover training per FTE | (annual × turnover_rate) / fte / meses |
| examenes | float | Exams per FTE | (exam_cost × multiplier) / fte / meses |
| estudios_seguridad | float | Security studies per FTE | (study_cost) / fte / meses |
| crucero | float | Retainer per FTE | (monthly fee) / fte / meses |
| no_payroll | float | Non-payroll per FTE | (opex_ti + capex + fixed_costs) / fte / meses |
| opex_fijo | float | IT opex per FTE | (opex_ti) / fte / meses |
| inversiones | float | Investments per FTE | (capex) / fte / meses |
| costos_fijos | float | Fixed costs per FTE | (rent + utilities + cleaning + security) / fte / meses |

**Activation Logic**:
- Channel only emitted when `fte > 0`
- If FTE=0, displays "No Activado" in Excel

---

## ResultadoCostToServe

**Location**: `domain/models/visions.py`  
**Purpose**: Complete Cost-to-Serve analysis  
**Version**: internal

| Field | Type | Description | Computed From |
|-------|------|-------------|--------|
| cts_cadena_a | float | CTS for Cadena A (COP/unit) | (sum payroll + non-payroll) / fte / meses |
| cts_cadena_b | float | CTS for Cadena B (COP/unit) | (total cadena b cost) / volume |
| cts_ponderado | float | Weighted CTS across all chains (COP/unit) | sum(cts_cadena_x × participacion_x) |
| participacion_a | float | Cadena A volume share (0..1) | volume_a / total_volume |
| participacion_b | float | Cadena B volume share (0..1) | volume_b / total_volume |
| participacion_c | float | Cadena C volume share (0..1) | volume_c / total_volume |
| fte_cadena_a | float | Total FTE for Cadena A | sum(profile.fte) |
| vol_cadena_b | float | Total monthly volume for Cadena B | sum(channel.volumen) |
| vol_cadena_c | float | Total monthly volume for Cadena C | sum(channel.volumen) |
| cts_cadena_c | float | CTS for Cadena C (COP/unit) | (total cadena c cost) / volume |
| costo_total_acumulado | float | Total accumulated cost (COP) | sum(all monthly costs) |
| desglose_a | DesgloseCTSCadenaA | Payroll/non-payroll breakdown | (see DesgloseCTSCadenaA) |
| desglose_b | DesgloseCTSCadenaB | Component breakdown (per unit) | (see DesgloseCTSCadenaB) |
| canal_view_habilitado | bool | Show channel-detail section (Excel C58/C87 gate) | (SAC service check) |
| canales_detalle | List[CanalCTSDetalle] | Per-channel CTS breakdown | (see CanalCTSDetalle) |

---

## TarifaCanal

**Location**: `domain/models/visions.py`  
**Purpose**: Tariff structure for a single channel  
**Version**: internal

| Field | Type | Description | Excel Section |
|-------|------|-------------|--------|
| nombre_canal | str | Channel name | Inputs!C39-C44 |
| modalidad | str | Modality (Inbound/Outbound) | (derived) |
| producto | str | Product type | (user input) |
| fte | float | FTE for this channel | Panel!M19:M25 |
| vol_mensual | float | Monthly volume/transactions | Panel!N19:N25 |
| modelo_cobro | str | Billing model (Fijo FTE, Híbrido, Variable) | Inputs!R39-R44 |
| pct_fijo | float | Fixed component % | Inputs!S39-S44 |
| pct_variable | float | Variable component % (1 - pct_fijo) | Computed |
| componente_fijo | str | Fixed component type (e.g., "FTE") | Inputs!T39-T44 |
| componente_variable | str | Variable component type (e.g., "Transacción") | Inputs!U39-U44 |
| costo_atribuible | float | Total attributable cost (COP/month) | (from vision tarifas) |
| ingreso_bruto | float | Gross revenue (COP/month) | (pricing formula) |
| facturacion | float | Invoice amount (COP/month) | (pricing formula) |
| tarifa_fijo_fte | float | Fixed tariff per FTE (COP) | facturacion × pct_fijo / fte |
| tarifa_variable | float | Variable tariff per unit (COP) | facturacion × pct_variable / vol |
| vol_minimo_transaccion | float | Minimum transaction volume for pricing | (from business rules) |
| payroll_ch | float | Payroll cost attributed to channel (COP/month) | (profile allocation) |
| no_payroll_ch | float | Non-payroll cost attributed to channel (COP/month) | (station allocation) |
| costo_cadena_a_ch | float | Total Cadena A cost for channel (COP/month) | payroll_ch + no_payroll_ch |
| nomina_loaded_ch | float | Payroll with taxes (COP/month) | (payroll breakdown) |
| salario_fijo_ch | float | Fixed salary component (COP/month) | (payroll breakdown) |
| salario_variable_ch | float | Variable salary component (COP/month) | (payroll breakdown) |
| capacitacion_inicial_ch | float | Initial training cost (COP/month) | (payroll breakdown) |
| capacitacion_rotacion_ch | float | Turnover training cost (COP/month) | (payroll breakdown) |
| examenes_ch | float | Exam costs (COP/month) | (payroll breakdown) |
| estudios_seguridad_ch | float | Security study costs (COP/month) | (payroll breakdown) |
| opex_it_ch | float | IT opex attributed to channel (COP/month) | (allocation formula) |
| inversiones_ch | float | Investments attributed to channel (COP/month) | (allocation formula) |
| costos_fijos_ch | float | Fixed costs attributed to channel (COP/month) | (allocation formula) |
| cadena_b_atribuible | float | Cadena B cost attributed to channel (COP/month) | (allocation) |
| financieros_atribuible | float | Financial costs attributed to channel (COP/month) | (allocation) |
| nomina_agente_basico | float | Agent salary (Inputs!W39-W40) | (HR catalog) |
| salario_cargado_ch | float | Loaded salary per FTE for this channel (COP) | (HR derived) |
| tarifa_hora_loggeada | float | Tariff per logged hour (COP) | (time-based pricing) |
| tarifa_hora_pagada | float | Tariff per paid hour (COP) | (time-based pricing) |

---

## EscenarioTarifasDetalle

**Location**: `domain/models/visions.py`  
**Purpose**: Hierarchical billing scenario detail (Excel Reverse-Engineering)  
**Version**: internal

| Field | Type | Description | Excel Rows |
|-------|------|-------------|--------|
| meta | EscenarioTarifasResumen | Scenario summary | B10:H21 |
| reglas_business | ReglasBusiness | Margins and contingencies | F29:G37 |
| cadena_a | DesgloseCadenaTarifas | Cadena A cost breakdown | B40:C47 |
| cadena_b | DesgloseCadenaTarifas | Cadena B cost breakdown | B50:C57 |
| cadena_c | DesgloseCadenaTarifas | Cadena C cost breakdown | B60:C67 |
| tarifas | TarifasEscenario | Billing calculations | G43:G57 |
| componente_fijo | ComponenteFijo? | Fixed component detail (time-based) | Rows 104-127 |
| componente_variable | ComponenteVariable? | Variable component detail (commission) | Rows 130-143 |
| tarifas_venta | List[TarifaXVenta] | Monthly sales targets | Rows 149-161 |

---

## ResultadoVisionTarifas

**Location**: `domain/models/visions.py`  
**Purpose**: Complete Vision Tarifas output  
**Version**: internal

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| canales | List[TarifaCanal] | Tariff per channel | (see TarifaCanal) |
| costo_cadena_a_total | float | Total Cadena A cost (COP/month) | sum(costo_a per month) |
| costo_cadena_b_total | float | Total Cadena B cost (COP/month) | sum(costo_b per month) |
| costo_cadena_c_total | float | Total Cadena C cost (COP/month) | sum(costo_c per month) |
| costo_total | float | Total all-chain cost (COP/month) | costo_a + costo_b + costo_c |
| ingreso_mensual | float | Average monthly revenue (COP) | ingreso_bruto_total / meses_activos |
| ingreso_cadena_a | float | Cadena A gross revenue (COP/month) | (pricing formula) |
| ingreso_cadena_b | float | Cadena B gross revenue (COP/month) | (pricing formula) |
| ingreso_cadena_c | float | Cadena C gross revenue (COP/month) | (pricing formula) |
| escenarios_detalle | List[EscenarioTarifasDetalle] | Hierarchical scenario breakdowns | (see EscenarioTarifasDetalle) |
| desglose_producto_opex | List[DesgloseProductoOpex] | Product-level OPEX breakdown | (see DesgloseProductoOpex) |

---

## VisionPyG

**Location**: `domain/models/visions.py`  
**Purpose**: Structured P&L statement for frontend rendering  
**Version**: internal

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| resumen | ResumenEjecutivoPyG | Executive summary (metadata + KPIs) | (see ResumenEjecutivoPyG) |
| filas | List[VisionPyGRow] | Main P&L rows (ingresos, costos, resultados) | (see VisionPyGRow) |
| meses_contrato | int | Contract length (months) | panel.meses_contrato |
| meses_activos | int | Months with positive net revenue | (computed) |
| filas_detalle | List[VisionPyGRowDetalle] | Sub-component breakdown rows (per-cadena) | (see VisionPyGRowDetalle) |
| puestos_trabajo | float | Number of workstations (Excel row 14) | (derived from profiles) |
| fechas_meses | List[str] | Calendar dates for each month | (computed) |

---

## VisionImprimible

**Location**: `domain/models/visions.py`  
**Purpose**: Formatted printable report with all sections  
**Version**: internal

Contains multiple sub-sections for:
- Deal card (client, service, duration)
- Economics (revenue, CTS, margin, contribution)
- Commercial configuration (billing model, tariffs, channels)
- Monthly evolution (month-by-month P&L)
- Scenario comparison
- Risk assessment
- P&G statement

(Detailed structure in visions.py)

---

# RESPONSE DTOs (API Output)

## KpisV1

**Location**: `contracts/api_v1/response/kpis.py`  
**Purpose**: Top-level KPIs for simulation result (api-v1)  
**Version**: api-v1

All monetary values in COP; percentages as 0..1.

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| costo_mensual_promedio | float | COP/month | Average monthly cost |
| costo_cadena_a_promedio | float | COP/month | Average Cadena A cost |
| ingreso_mensual | float | COP/month | Average monthly revenue |
| facturacion_mensual_proyectada | float | COP/month | Projected revenue |
| ingreso_bruto_total | float | COP | Total gross revenue |
| ingreso_neto_total | float | COP | Total net revenue |
| costo_total_contrato | float | COP | Total contract cost |
| contribucion_total | float | COP | Total contribution |
| utilidad_neta_total | float | COP | Total net profit |
| pct_utilidad_neta_total | float | 0..1 | Net profit margin % |
| valor_total_deal | float | COP | Deal total value |
| margen_minimo_requerido | float | 0..1 | Minimum required margin |
| cumple_margen_minimo | bool | — | Does deal meet minimum margin |

---

## CostToServeV1

**Location**: `contracts/api_v1/response/visions.py`  
**Purpose**: Cost-to-Serve vision response (api-v1)  
**Version**: api-v1

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| cts_cadena_a | float | COP/unit | Cadena A CTS |
| cts_cadena_b | float | COP/unit | Cadena B CTS |
| cts_cadena_c | float | COP/unit | Cadena C CTS |
| cts_ponderado | float | COP/unit | Weighted CTS |
| participacion_a | float | 0..1 | Cadena A volume share |
| participacion_b | float | 0..1 | Cadena B volume share |
| participacion_c | float | 0..1 | Cadena C volume share |
| fte_cadena_a | float | headcount | Total FTE (Cadena A) |
| vol_cadena_b | float | transactions/month | Total volume (Cadena B) |
| costo_total_acumulado | float | COP | Total accumulated cost |
| desglose_a | CostToServeDesgloseAV1? | — | Cadena A breakdown (optional) |
| desglose_b | CostToServeDesgloseBV1? | — | Cadena B breakdown (optional) |
| canal_view_habilitado | bool | — | Show channel detail section |
| canales_detalle | List[CanalCTSDetalleV1] | — | Per-channel breakdown |

---

## VisionTarifasV1

**Location**: `contracts/api_v1/response/visions.py`  
**Purpose**: Tariff structure vision response (api-v1)  
**Version**: api-v1

(Same structure as ResultadoVisionTarifas, serialized to JSON)

---

## VisionPyGV1

**Location**: `contracts/api_v1/response/visions.py`  
**Purpose**: P&L statement vision response (api-v1)  
**Version**: api-v1

(Same structure as VisionPyG, serialized to JSON with monthly data arrays)

---

## SimulationResultV1

**Location**: `contracts/api_v1/response/simulation_result.py`  
**Purpose**: Unified simulation result envelope (api-v1)  
**Version**: api-v1

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| simulation_id | str | Yes | Unique result identifier | "sim-20260531-abc123" |
| api_version | Literal["api-v1"] | No | API version tag | "api-v1" |
| engine_version | str | No | Pricing engine version | "2.7.1" |
| parametrization_version | str | No | Parametrization version | "2024-12-15" |
| baseline_version | str? | No | Baseline hash (certified mode only) | "v2-7-baseline" |
| formula_set | str | No | Active formula set version | "formula-set-v2-7" |
| parametrization_hashes | Dict[str, str] | No | SHA-256 of parametrization JSONs | {"hr": "abc123...", "gn": "def456...", "op": "ghi789...", "business_rules": "jkl012..."} |
| visions | VisionsBundleV1 | No | All vision outputs | (see VisionsBundleV1) |
| kpis | KpisV1 | No | Aggregate KPIs | (see KpisV1) |
| generated_at | datetime | No | Timestamp (UTC) | "2026-05-31T14:30:00Z" |

---

## VisionsBundleV1

**Location**: `contracts/api_v1/response/visions.py`  
**Purpose**: Container for all vision outputs  
**Version**: api-v1

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| cost_to_serve | CostToServeV1? | No | Cost-to-serve vision |
| vision_tarifas | VisionTarifasV1? | No | Tariff structure vision |
| vision_pyg | VisionPyGV1? | No | P&L statement vision |
| vision_imprimible | VisionImprimibleV1? | No | Printable report vision |
| traceability | Dict? | No | Audit trace (optional) |

---

# ENUMS & VALUE OBJECTS

## ModeloCobroLiteral

**Location**: `contracts/api_v1/request/cadena_a.py`  
**Purpose**: Billing model enumeration  
**Values**:
- `"Fijo FTE"` — Fixed per FTE (agents)
- `"Variable"` — Usage-based (transactions)
- `"Híbrido"` / `"Hibrido"` — Hybrid fixed+variable
- `"Volumen"` / `"Por Volumen"` — Volume-based
- `"Por Comisión"` / `"Por Comision"` — Commission-based

---

## CargoTipo

**Location**: `domain/models/panel.py`  
**Purpose**: Cargo classification (HR-derived)  
**Values** (from HR catalog):
- `"DESCONOCIDO"` — Unknown/unclassified
- `"OPERATIVO"` — Operational agent
- `"SUPERVISORY"` — Supervisor/lead
- `"STAFF"` — Support staff
- (others from HR-clasificacion_cargos)

---

## TipoCarga

**Location**: `domain/models/panel.py`  
**Purpose**: Labor type enumeration (from HR catalog)  
**Values**:
- `"EMPLEADO_ESTANDAR"` — Standard employee
- `"APRENDIZ_SENA"` — SENA apprentice
- `"EQUIPO_SOPORTE_MANTENIMIENTO"` — Support & maintenance
- `"SOPORTE_COMISIONABLE"` — Commissioned support
- `"IMPLEMENTACION_PROYECTOS"` — Project implementation

---

## Indexacion

**Location**: `domain/models/panel.py`  
**Purpose**: Salary/cost indexation configuration  
**Version**: internal

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| componente_humano | str | Payroll indexation component (e.g., "IPC") | "" |
| componente_tecnologico | str | Technology indexation component | "" |
| frecuencia | str | Frequency (e.g., "Anual") | "Anual" |
| mes_aplicacion | int | Month to apply indexation (1-12) | 1 |

---

## CadenasActivas

**Location**: `domain/models/panel.py`  
**Purpose**: Contract-level chain activation state  
**Version**: internal

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| cadena_a | bool | Is Cadena A active | false |
| cadena_b | bool | Is Cadena B active | false |
| cadena_c | bool | Is Cadena C active | false |

**Methods**:
```python
def is_active(cadena: str) -> bool:
    return getattr(self, cadena, False)
```

---

## PolizaContractual

**Location**: `domain/models/panel.py`  
**Purpose**: User-provided insurance policy definition  
**Version**: internal

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| nombre | str | Yes | Policy name (e.g., "Responsabilidad Civil") |
| activa | bool | Yes | Is this policy active |
| pct_poliza | float | Yes | Insurance premium rate (0..1) |
| pct_atribuible | float | Yes | Attributable portion (0..1) |
| aplica_extension | bool | No | Extend beyond contract term |
| meses_extension | int? | No | Extension months |
| aplica_a | bool | No | Apply to Cadena A |
| aplica_b | bool | No | Apply to Cadena B |
| aplica_c | bool | No | Apply to Cadena C |
| per_canal | bool | No | Per-channel attribution (V2-7) |
| is_comision_administracion | bool | No | Is admin fee (vs. insurance) |

**Computed Properties**:
```python
tasa_efectiva = pct_poliza * pct_atribuible if activa else 0.0
```

---

## EscenarioComercial

**Location**: `domain/models/panel.py`  
**Purpose**: Commercial billing scenario definition  
**Version**: internal

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| escenario | int | Yes | Scenario number (1-5) |
| modalidad | str | Yes | Modality (Inbound/Outbound) |
| canal | str | Yes | Channel name |
| modelo_cobro | str | Yes | Billing model |
| componente_fijo_tipo | str? | No | Fixed component type |
| componente_fijo_pct | float | No | Fixed component % |
| componente_variable_tipo | str? | No | Variable component type |
| componente_variable_pct | float | No | Variable component % |

---

## ItemOpexConsumoB

**Location**: `domain/models/panel.py`  
**Purpose**: Variable consumption item (Cadena B)  
**Version**: internal

| Field | Type | Description |
|-------|------|-------------|
| nombre | str | Item name (e.g., "Token IA") |
| producto | str | Product type |
| modalidad | str | Modality/integration |
| canal | str | Channel |
| valor_unitario | float | Unit cost (COP) |
| cantidad | float | Monthly quantity |
| tipo_cobro | str | Billing type (default: "Unitario") |

**Computed Property**:
```python
total_mensual = valor_unitario * cantidad
```

---

## MiembroEquipo

**Location**: `domain/models/panel.py`  
**Purpose**: Team member (S&M, HITL, Transversal)  
**Version**: internal

| Field | Type | Description |
|-------|------|-------------|
| rol | str | Role/title |
| activo | bool | Is active |
| pct_dedicacion | float | Allocation % (0..1) |
| fte_equivalente | float | Computed FTE — calculated in context_builder |

---

## DispositivoSM

**Location**: `domain/models/panel.py`  
**Purpose**: S&M team device (amortized)  
**Version**: internal

| Field | Type | Description |
|-------|------|-------------|
| tipo | str | Device type |
| costo_unitario | float | Unit cost (COP) |
| cantidad | float | Quantity |
| meses_amortizacion | int | Amortization period (months) |

**Computed Property**:
```python
costo_mensual = (costo_unitario * cantidad) / meses_amortizacion
```

---

## PolizaConfiguracion

**Location**: `domain/models/panel.py`  
**Purpose**: Parametrized insurance policy (from storage)  
**Version**: internal

| Field | Type | Description |
|-------|------|-------------|
| nombre | str | Policy name |
| activa | bool | Is active |
| porcentaje_poliza | float | Premium rate (0..1) |
| porcentaje_atribuible | float | Attributable portion (0..1) |
| aplica_a | bool | Apply to Cadena A (default: true) |
| aplica_b | bool | Apply to Cadena B (default: false) |
| aplica_c | bool | Apply to Cadena C (default: false) |
| se_extiende | bool | Extend beyond contract |
| meses_extension | int | Extension months |

**Computed Properties**:
```python
tasa_efectiva = porcentaje_poliza * porcentaje_atribuible if activa else 0.0
tasa_efectiva_a = tasa_efectiva if aplica_a else 0.0
tasa_efectiva_b = tasa_efectiva if aplica_b else 0.0
```

---

## ReglaNegocios

**Location**: `domain/models/visions.py`  
**Purpose**: Business rule evaluation result  
**Version**: internal

| Field | Type | Description |
|-------|------|-------------|
| nombre | str | Rule identifier |
| label | str | Display name |
| aplicado | float | Applied value |
| min_valor | float? | Minimum allowed |
| max_valor | float? | Maximum allowed |
| status | str | Validation status ("OK", "WARNING", "FAIL") |
| monto | float? | Impact in COP |

---

## WaterfallPromedio

**Location**: `domain/models/visions.py`  
**Purpose**: Average cost waterfall for visualization  
**Version**: internal

| Field | Type | Description |
|-------|------|-------------|
| payroll_a | float | Average Cadena A payroll (COP/month) |
| no_payroll_a | float | Average Cadena A non-payroll (COP/month) |
| costo_b | float | Average Cadena B cost (COP/month) |
| costo_c | float | Average Cadena C cost (COP/month) |
| financiacion | float | Average financing (COP/month) |
| polizas | float | Average insurance (COP/month) |
| ica | float | Average ICA tax (COP/month) |
| gmf | float | Average GMF tax (COP/month) |
| costo_total | float | Average total cost (COP/month) |
| ingreso_bruto | float | Average gross revenue (COP/month) |
| contingencias | float | Average contingency (COP/month) |
| markup_descuento | float | Average markup/discount (COP/month) |
| ingreso_neto | float | Average net revenue (COP/month) |
| contribucion | float | Average contribution (COP/month) |
| meses_activos | int | Months with positive net revenue |

---

## VisionPyGRow

**Location**: `domain/models/visions.py`  
**Purpose**: P&L statement row with semantic metadata  
**Version**: internal

| Field | Type | Description |
|-------|------|-------------|
| key | str | Unique identifier (snake_case, stable for frontend) |
| label | str | Display name |
| seccion | str | Section: "ingresos", "costos_op", "costos_fin", "resultados", "operativo" |
| tipo | str | Role: "linea", "subtotal", "total", "porcentaje", "" |
| signo | str | Participation: "+", "-", "=", "%", "" |
| valores | List[float] | Monthly values (1 per contract month) |
| acumulado | float | Sum of all months (or average for percentages) |
| promedio | float | Average over active months |
| excel_row | int? | Excel source row (for traceability) |
| formula | str? | Formula description |

---

## VisionPyGRowDetalle

**Location**: `domain/models/visions.py`  
**Purpose**: Sub-component breakdown row (hierarchical P&L)  
**Version**: internal

| Field | Type | Description |
|-------|------|-------------|
| key | str | Unique identifier |
| label | str | Display name |
| parent | str | Parent row key (e.g., "payroll_a") |
| seccion | str | Section identifier |
| tipo | str | Row type |
| signo | str | Participation sign |
| valores | List[float] | Monthly values |
| acumulado | float | Sum/average |
| promedio | float | Average over active months |
| excel_row | int? | Source row |
| formula | str? | Formula description |

---

## ResumenEjecutivoPyG

**Location**: `domain/models/visions.py`  
**Purpose**: Executive summary for P&L vision  
**Version**: internal

| Field | Type | Description |
|-------|------|-------------|
| meses_contrato | int | Contract length |
| meses_activos | int | Months with positive net revenue |
| valor_total_deal | float | Total deal value (COP) |
| ingreso_neto_total | float | Total net revenue (COP) |
| costo_total_contrato | float | Total cost (COP) |
| contribucion_total | float | Total contribution (COP) |
| pct_utilidad_promedio | float | Average margin % |
| cumple_margen_minimo | bool | Meets minimum margin |
| cliente | str | Client name |
| tipo_cliente | str | Client type |
| antiguedad_cliente | str | Client tenure |
| linea_negocio | str | Service line |
| ciudad | str | City |
| sede | str | Office |
| fecha_inicio | str | Start date |
| fecha_fin | str | End date |
| duracion_contrato | str | Duration text |
| periodo_pago_dias | int | Payment term |
| divisa | str | Currency (default: "COP") |

---

## EndOfDocumentation

This comprehensive data model reference covers:
- 30+ DTOs (request, domain, result)
- 15+ vision models (hierarchical display structures)
- All enums and value objects
- Validation rules and constraints
- Computed properties and formulas
- Excel cell references where applicable

For API endpoint definitions and usage examples, see `API_REFERENCE.md`.

