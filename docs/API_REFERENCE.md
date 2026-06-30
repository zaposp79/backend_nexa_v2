# NEXA Backend API Reference

**Last Updated**: 2026-05-31  
**API Version**: api-v1  
**Base URL**: `/api/v1`  
**Content-Type**: `application/json`

This document comprehensively catalogs all 25+ endpoints of the NEXA pricing engine API. Each endpoint includes request/response schemas, validation rules, error handling, and real examples.

---

## Table of Contents

1. [Simulation Calculation](#simulation-calculation)
2. [Input Parametrization](#input-parametrization)
3. [Parametrization Management](#parametrization-management)
4. [Audit & Traceability](#audit--traceability)
5. [Certification & Versioning](#certification--versioning)
6. [Error Handling](#error-handling)

---

# SIMULATION CALCULATION

## POST /api/v1/simulation/calculate

**Purpose**: Execute the NEXA pricing engine with deal parameters and return a simulation ID for result querying.  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 201 Created

### Request

**Content-Type**: `application/json`

**Query Parameters**:
| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| mode | string | No | Execution mode: "normal" or "certified" | "normal" |

**Body Structure** (Auto-wrapping):

The endpoint accepts TWO request body formats:

**Format 1: Canonical** (recommended)
```json
{
  "user_input": {
    "panel_de_control": { ... },
    "condiciones_cadena_a": { ... },
    "condiciones_cadena_b": { ... },
    "condiciones_cadena_c": { ... },
    "escenarios_comerciales": [ ... ],
    "metadata": { ... }
  }
}
```

**Format 2: Flat** (auto-wrapped to canonical)
```json
{
  "panel_de_control": { ... },
  "condiciones_cadena_a": { ... },
  "condiciones_cadena_b": { ... },
  "condiciones_cadena_c": { ... },
  "escenarios_comerciales": [ ... ],
  "metadata": { ... }
}
```

The endpoint auto-detects flat format and wraps it as Format 1 (no client change needed).

### Request Example

```json
{
  "user_input": {
    "panel_de_control": {
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
      "imprevistos": 0.03
    },
    "condiciones_cadena_a": {
      "perfiles": [
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
          "dias_cap_inicial": 10,
          "dias_cap_rotacion": 10,
          "tmo_segundos": 180.0,
          "modelo_cobro": "Fijo FTE",
          "pct_fijo": 1.0
        }
      ]
    },
    "condiciones_cadena_b": {
      "canales": [
        {
          "nombre": "WhatsApp",
          "modalidad": "Inbound",
          "producto": "WHATSAPP_API",
          "volumen_mensual": 10000.0,
          "activo": true,
          "opex_fijo": 500000.0,
          "tarifa_unitaria": 50.0,
          "pct_escalamiento": 0.1
        }
      ],
      "opex_consumo_variable": [],
      "equipo_sm": [],
      "dispositivos_sm": [],
      "inversion_plataforma": 0.0,
      "fte_equipo_sm": 1.0,
      "amortizar_dispositivos_sm": true
    },
    "condiciones_cadena_c": {
      "canales": [],
      "equipo_transversal": [],
      "inversion_anual": 0.0
    },
    "escenarios_comerciales": [
      {
        "nombre": "Base",
        "canal": "WhatsApp",
        "modalidad": "Inbound",
        "margen": 0.15
      }
    ],
    "metadata": {
      "client_id": "CLI-001",
      "request_id": "REQ-20260531-001",
      "source": "salesforce",
      "notes": "Q2 2026 pricing exercise"
    }
  }
}
```

### Validation Rules

- **At least one chain** (A, B, or C) must be present in `user_input`
- **Cadena A profiles**: If provided, each must have `nombre`, `rol`, `canal`, `modalidad`
- **Scenarios**: Must reference (canal, modalidad) pairs declared in Cadena A (if A is active)
- **Panel dates**: `fecha_inicio` must be valid date string (YYYY-MM-DD format)
- **Numeric ranges**:
  - `meses_contrato`: 1 ≤ x ≤ 120
  - `margen`, `margen_b`, `margen_c`: -1.0 ≤ x ≤ 1.0
  - `op_cont`, `com_cont`, `descuento`, `pct_rotacion`, `pct_ausentismo`: 0.0 ≤ x ≤ 1.0
  - `tasa_ica`, `tasa_gmf`, `tasa_mensual_financ`: 0.0 ≤ x ≤ 1.0
  - FTE values: ≥ 0.0
  - Costs and volumes: ≥ 0.0

### Response

**HTTP Status**: 201 Created

```json
{
  "success": true,
  "data": {
    "simulation_id": "sim-20260531-abc123def456",
    "message": "Calculation completed successfully.",
    "calculated_at": "2026-05-31T14:30:00Z",
    "engine_version": "2.7.1",
    "parametrization_version": "2024-12-15",
    "formula_set": "formula-set-v2-7"
  },
  "error": null
}
```

### Error Handling

| HTTP Status | Code | Message | Cause |
|--------|------|---------|-------|
| 422 | VALIDATION_ERROR | Invalid input: {details} | Panel dates, numeric ranges, missing required fields |
| 400 | DOMAIN_ERROR | Business rule violation: {details} | Chain activation conflicts, scenario references invalid channels |
| 500 | VISION_INCOMPLETE | Missing calculation outputs | Internal engine error; one or more visions not computed |
| 500 | CALCULATION_FAILED | {error details} | Unhandled engine exception |

### Dependencies

- **Requires**: None (pure calculation endpoint)
- **Provides**: `simulation_id` for all GET endpoints below
- **Parametrization Required**:
  - HR module (for salary calculations)
  - GN module (for financial taxes and insurance)
  - OP module (for operational costs)
  - If not available, engine uses built-in defaults

### Examples

**Normal Mode (default)**:
```bash
curl -X POST http://localhost:8000/api/v1/simulation/calculate \
  -H "Content-Type: application/json" \
  -d '{request-body}' \
  --silent | jq .data.simulation_id
```

**Certified Mode** (enforces baseline hashing):
```bash
curl -X POST http://localhost:8000/api/v1/simulation/calculate?mode=certified \
  -H "Content-Type: application/json" \
  -d '{request-body}' \
  --silent | jq .data.simulation_id
```

---

## GET /api/v1/simulation/{simulation_id}/results

**Purpose**: Retrieve the public projection of the canonical `Visión Imprimible` sheet.
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| simulation_id | string | Yes | ID from POST /calculate |

**Query Parameters**: None

### Response

**HTTP Status**: 200 OK

Returns only `data.vision_imprimible`. The persisted technical result is not
exposed by this route; specialized P&G, tariff and CTS routes remain available.

```json
{
  "success": true,
  "data": {
    "vision_imprimible": {
      "ficha_deal": { ... },
      "economics": { ... },
      "analisis_grafico": { ... },
      "comparativo_escenarios": { ... },
      "control_aprobacion": { ... },
      "contingencias_ajustes": [ ... ]
    }
  },
  "error": null
}
```

### Error Handling

| HTTP Status | Code | Message | Cause |
|--------|------|---------|-------|
| 404 | NOT_FOUND | Simulation {simulation_id} not found | Result file does not exist |
| 500 | INTERNAL_ERROR | Failed to load result | Storage/file system error |

### Related Endpoints

- `GET /{simulation_id}/results/vision-imprimible` — Same printable public contract
- `GET /{simulation_id}/results/vision-pyg` — Focused P&L vision
- `GET /{simulation_id}/results/vision-tarifas` — Focused tariff vision
- `GET /{simulation_id}/results/cost-to-serve` — Focused CTS vision

---

## GET /api/v1/simulation/{simulation_id}/results/vision-imprimible

**Purpose**: Retrieve formatted printable vision (9 sections of deal data)  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| simulation_id | string | Yes | ID from POST /calculate |

### Response

**HTTP Status**: 200 OK

The "Visión Imprimible" contains 9 official sections:

```json
{
  "success": true,
  "data": {
    "ficha_deal": {
      "cliente": "Bancamía",
      "fecha_inicio": "2026-06-01",
      "servicio": "Cobranzas",
      "duracion": "12 meses"
    },
    "kpis": { ... },
    "pyg_por_mes": [ ... ],
    "waterfall_promedio": { ... },
    "configuracion_comercial": { ... },
    "reglas_negocio": [ ... ],
    "evaluacion_riesgo": { ... },
    "vision_pyg": { ... },
    "cost_to_serve": { ... },
    "vision_tarifas": { ... },
    "vision_por_servicio": [ ... ],
    "vision_por_canal": [ ... ],
    "detalle_por_canal": [ ... ],
    "estructura_equipo": { ... }
  },
  "error": null
}
```

**Sections**:
1. **ficha_deal** — Client, contract, indexation metadata
2. **kpis** — Deal economics (revenue, costs, margin, contribution)
3. **configuracion_comercial** — Billing model, tarifas, discounts per channel
4. **waterfall_promedio** — Average monthly costs for waterfall chart
5. **vision_pyg** — P&L structured by sections and rows (ingresos, costos, resultados)
6. **evaluacion_riesgo** — Risk score and criteria
7. **reglas_negocio** — Business rules evaluated (contingencies, compliance)
8. **cost_to_serve** — CTS per chain with cost breakdowns
9. **vision_tarifas** — Billing tariffs and costs per channel

**Plus supporting data**:
- **vision_por_servicio** — Rollup by service line
- **vision_por_canal** — Summary by channel (Inbound/Outbound split)
- **detalle_por_canal** — Detailed breakdown per channel
- **estructura_equipo** — Team roster with FTE and costs

### Error Handling

| HTTP Status | Code | Message | Cause |
|--------|------|---------|-------|
| 404 | NOT_FOUND | Simulation {simulation_id} not found | Result file does not exist |

---

## GET /api/v1/simulation/{simulation_id}/results/vision-pyg

**Purpose**: Retrieve structured P&L statement (Profit & Loss)  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| simulation_id | string | Yes | ID from POST /calculate |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": {
    "resumen": {
      "meses_contrato": 12,
      "meses_activos": 12,
      "valor_total_deal": 92000000.0,
      "ingreso_neto_total": 92000000.0,
      "costo_total_contrato": 60000000.0,
      "contribucion_total": 32000000.0,
      "pct_utilidad_promedio": 0.3478,
      "cumple_margen_minimo": true,
      "cliente": "Bancamía",
      "tipo_cliente": "Persona Jurídica",
      "antiguedad_cliente": "1-3 años",
      "linea_negocio": "Cobranzas",
      "ciudad": "Bogota",
      "sede": "Toberin",
      "fecha_inicio": "2026-06-01",
      "fecha_fin": "2027-05-31",
      "duracion_contrato": "12 meses",
      "periodo_pago_dias": 90,
      "divisa": "COP"
    },
    "filas": [
      {
        "key": "ingreso_bruto_a",
        "label": "Ingreso Bruto Cadena A",
        "seccion": "ingresos",
        "tipo": "linea",
        "signo": "+",
        "valores": [8000000.0, 8000000.0, ...],
        "acumulado": 96000000.0,
        "promedio": 8000000.0,
        "excel_row": 3,
        "formula": "SUM(Tarifas!C43)"
      },
      { ... }
    ],
    "filas_detalle": [
      {
        "key": "payroll_a_detail_salario_fijo",
        "label": "Salario Fijo",
        "parent": "payroll_a",
        "seccion": "costos_op",
        "tipo": "linea",
        "signo": "+",
        "valores": [3000000.0, 3000000.0, ...],
        "acumulado": 36000000.0,
        "promedio": 3000000.0,
        "excel_row": 36,
        "formula": "Nomina!C5 * Panel!C11"
      },
      { ... }
    ],
    "puestos_trabajo": 5.0,
    "fechas_meses": ["2026-06-01", "2026-07-01", "2026-08-01", ...],
    "meses_contrato": 12,
    "meses_activos": 12
  },
  "error": null
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| resumen | ResumenEjecutivoPyG | Executive summary (metadata + aggregate KPIs) |
| filas | List[VisionPyGRow] | Main P&L rows: ingresos, costos_op, costos_fin, resultados |
| filas_detalle | List[VisionPyGRowDetalle] | Sub-component breakdown rows (per-cadena detail) |
| puestos_trabajo | float | Number of workstations |
| fechas_meses | List[str] | Calendar date for each month |
| meses_contrato | int | Contract length (months) |
| meses_activos | int | Months with positive net revenue |

Each row in `filas` and `filas_detalle` has:
- **key**: Stable identifier for frontend (snake_case)
- **label**: Human-readable name
- **seccion**: Group: "ingresos", "costos_op", "costos_fin", "resultados", "operativo"
- **tipo**: Role: "linea", "subtotal", "total", "porcentaje", ""
- **signo**: Participation: "+", "-", "=", "%", ""
- **valores**: Array of monthly values (1 per month)
- **acumulado**: Sum (or average for percentages)
- **promedio**: Average over active months
- **excel_row**: Excel source row (for traceability)
- **formula**: Excel formula description

---

## GET /api/v1/simulation/{simulation_id}/results/cost-to-serve

**Purpose**: Retrieve Cost-to-Serve analysis (CTS per chain + channel detail)  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| simulation_id | string | Yes | ID from POST /calculate |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": {
    "cost_to_serve": {
      "cts_cadena_a": 2500.0,
      "cts_cadena_b": 50.0,
      "cts_cadena_c": 0.0,
      "cts_ponderado": 2400.0,
      "participacion_a": 0.85,
      "participacion_b": 0.15,
      "participacion_c": 0.0,
      "fte_cadena_a": 5.0,
      "vol_cadena_b": 10000.0,
      "vol_cadena_c": 0.0,
      "costo_total_acumulado": 60000000.0,
      "desglose_a": {
        "nomina": 3000000.0,
        "no_payroll": 1000000.0,
        "total": 4000000.0,
        "nomina_loaded": 3500000.0,
        "salario_fijo": 2800000.0,
        "salario_variable": 200000.0,
        "capacitacion_inicial": 150000.0,
        "capacitacion_rotacion": 100000.0,
        "examenes": 100000.0,
        "estudios_seguridad": 50000.0,
        "crucero": 0.0,
        "opex_fijo": 600000.0,
        "inversiones": 200000.0,
        "costos_fijos_estacion": 200000.0
      },
      "desglose_b": {
        "componente_fijo": 500000.0,
        "componente_variable": 0.0,
        "total": 500000.0,
        "opex": 500000.0,
        "inversiones": 0.0,
        "soporte_mantenimiento": 0.0,
        "tarifa": 0.0,
        "opex_variable": 0.0,
        "tasa_escalamiento": 0.0,
        "hitl": 0.0
      },
      "canal_view_habilitado": true,
      "canales_detalle": [
        {
          "canal": "WhatsApp",
          "modalidad": "Inbound",
          "fte": 5.0,
          "participacion_cadena_a": 1.0,
          "cts": 2500.0,
          "payroll": 3000000.0,
          "nomina_loaded": 3500000.0,
          "salario_fijo": 2800000.0,
          "salario_variable": 200000.0,
          "capacitacion_inicial": 150000.0,
          "capacitacion_rotacion": 100000.0,
          "examenes": 100000.0,
          "estudios_seguridad": 50000.0,
          "crucero": 0.0,
          "no_payroll": 1000000.0,
          "opex_fijo": 600000.0,
          "inversiones": 200000.0,
          "costos_fijos": 200000.0
        }
      ]
    },
    "vision_por_servicio": [ ... ],
    "vision_por_canal": [ ... ],
    "detalle_por_canal": [ ... ],
    "estructura_equipo": { ... }
  },
  "error": null
}
```

**Response Sections**:
| Section | Description |
|---------|-------------|
| **cost_to_serve** | Main CTS output: cts_a/b/c, participations, desglose_a/b, canales_detalle |
| **vision_por_servicio** | Rollup by service line (Excel CTS rows 23-40) |
| **vision_por_canal** | Summary by channel with Inbound/Outbound split (Excel CTS rows 58-90) |
| **detalle_por_canal** | Detailed breakdown per channel including payroll sub-components |
| **estructura_equipo** | Team roster with roles, FTE, and costs (Excel CTS rows 131-177) |

---

## GET /api/v1/simulation/{simulation_id}/results/vision-tarifas

**Purpose**: Retrieve tariff structure vision (billing models, per-channel tariffs)  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| simulation_id | string | Yes | ID from POST /calculate |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": {
    "canales": [
      {
        "nombre_canal": "WhatsApp",
        "modalidad": "Inbound",
        "producto": "WHATSAPP_API",
        "fte": 5.0,
        "vol_mensual": 10000.0,
        "modelo_cobro": "Fijo FTE",
        "pct_fijo": 1.0,
        "pct_variable": 0.0,
        "componente_fijo": "FTE",
        "componente_variable": "",
        "costo_atribuible": 4500000.0,
        "ingreso_bruto": 8000000.0,
        "facturacion": 8000000.0,
        "tarifa_fijo_fte": 133333.33,
        "tarifa_variable": 0.0,
        "vol_minimo_transaccion": 0.0,
        "payroll_ch": 3000000.0,
        "no_payroll_ch": 1000000.0,
        "costo_cadena_a_ch": 4000000.0,
        "nomina_loaded_ch": 3500000.0,
        "salario_fijo_ch": 2800000.0,
        "salario_variable_ch": 200000.0,
        "capacitacion_inicial_ch": 150000.0,
        "capacitacion_rotacion_ch": 100000.0,
        "examenes_ch": 100000.0,
        "estudios_seguridad_ch": 50000.0,
        "opex_it_ch": 600000.0,
        "inversiones_ch": 200000.0,
        "costos_fijos_ch": 200000.0,
        "cadena_b_atribuible": 500000.0,
        "financieros_atribuible": 300000.0,
        "nomina_agente_basico": 1200000.0,
        "salario_cargado_ch": 1500000.0,
        "tarifa_hora_loggeada": 5000.0,
        "tarifa_hora_pagada": 6000.0
      }
    ],
    "costo_cadena_a_total": 4000000.0,
    "costo_cadena_b_total": 500000.0,
    "costo_cadena_c_total": 0.0,
    "costo_total": 4500000.0,
    "ingreso_mensual": 8000000.0,
    "ingreso_cadena_a": 8000000.0,
    "ingreso_cadena_b": 0.0,
    "ingreso_cadena_c": 0.0,
    "escenarios_detalle": [ ... ],
    "desglose_producto_opex": [ ... ]
  },
  "error": null
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| canales | List[TarifaCanal] | Tariff per channel (see TarifaCanal in DATA_MODEL) |
| costo_cadena_a_total | float | Total Cadena A cost (COP/month) |
| costo_cadena_b_total | float | Total Cadena B cost (COP/month) |
| costo_cadena_c_total | float | Total Cadena C cost (COP/month) |
| costo_total | float | Total all-chain cost (COP/month) |
| ingreso_mensual | float | Average monthly revenue (COP) |
| ingreso_cadena_a | float | Cadena A gross revenue (COP/month) |
| ingreso_cadena_b | float | Cadena B gross revenue (COP/month) |
| ingreso_cadena_c | float | Cadena C gross revenue (COP/month) |
| escenarios_detalle | List[EscenarioTarifasDetalle] | Hierarchical scenario breakdowns |
| desglose_producto_opex | List[DesgloseProductoOpex] | Product-level OPEX breakdown |

---

## GET /api/v1/simulation/{simulation_id}/results/traceability

**Purpose**: Retrieve complete audit trace for the calculation (optional, requires with_lineage=True)  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| simulation_id | string | Yes | ID from POST /calculate |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": {
    "simulation_id": "sim-20260531-abc123def456",
    "engine_version": "2.7.1",
    "formula_set": "formula-set-v2-7",
    "calculated_at": "2026-05-31T14:30:00Z",
    "lineage": {
      "nodes_count": 1245,
      "roots": ["panel.meses_contrato", "panel.margen", "profile.fte"],
      "stages_summary": {
        "inputs": 42,
        "nomina_loader": 18,
        "no_payroll_calculator": 12,
        "cadena_b_calculator": 8,
        "cadena_c_calculator": 6,
        "financial_costs": 15,
        "vision_builders": 125
      }
    },
    "formulas_used": [
      {
        "calculator": "NominaCalculator",
        "formula": "salario_fijo = salario_cargado × fte / meses",
        "stage": "nomina_loader",
        "used_count": 5
      }
    ],
    "parameters_used": {
      "request": {
        "panel": { ... },
        "cadena_a": { ... }
      },
      "parametrization": {
        "hr": "salary_scales_2026",
        "gn": "taxes_ica_gmf_2026",
        "op": "operational_costs_2026"
      },
      "excel_refs": [
        {
          "source_type": "HR",
          "source_id": "salary_scales_2026",
          "value": 1200000.0,
          "sheet": "Inputs",
          "cell": "W39",
          "formula": "Base salary for Agente Basico"
        }
      ]
    }
  },
  "error": null
}
```

### Error Handling

| HTTP Status | Code | Message | Cause |
|--------|------|---------|-------|
| 404 | NOT_FOUND | Lineage for simulation {simulation_id} not found | Trace not generated (require with_lineage=True) |

---

## GET /api/v1/simulation/{simulation_id}/results/vision-pyg

**Purpose**: Retrieve the persisted Vision P&G result for a simulation.  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|-------|------|----------|-------------|
| simulation_id | string | Yes | ID from POST /calculate |

### Response

**HTTP Status**: 200 OK

Returns the structured P&G vision persisted as part of `PricingResult`.

---

# INPUT PARAMETRIZATION

These endpoints expose the current active parametrization used by the pricing engine.

## GET /api/v1/simulation/input/panel/parametros

**Purpose**: Retrieve active Panel default values and constraints  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Query Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| module | string | No | Specific module: "hr", "gn", "op" | (all) |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": {
    "v2_7_defaults": {
      "meses_contrato": 12,
      "margen": 0.15,
      "margen_b": 0.30,
      "margen_c": 0.20,
      "mes_ajuste_indexacion": 6,
      "tasa_interes_mensual": 0.0153,
      "op_cont": 0.05,
      "com_cont": 0.02,
      "markup": 0.1,
      "descuento": 0.05
    },
    "hr_parameters": {
      "pct_aumento_salarial": 0.04,
      "costo_examen_medico": 50000.0,
      "costo_estudio_seg": 30000.0,
      "tarifa_dia_cap": 100000.0
    },
    "gn_parameters": {
      "tasa_ica": 0.0075,
      "tasa_gmf": 0.004,
      "pct_rotacion": 0.15,
      "pct_ausentismo": 0.08
    },
    "op_parameters": {
      "opex_ti_por_estacion": 100000.0,
      "capex_por_estacion": 50000.0,
      "arriendo_por_estacion": 200000.0,
      "energia_por_estacion": 20000.0,
      "vigilancia_por_estacion": 50000.0,
      "aseo_por_estacion": 30000.0
    }
  },
  "error": null
}
```

---

## GET /api/v1/simulation/input/chain-a/parametros

**Purpose**: Retrieve active Cadena A parametrization (HR catalog)  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Response

Returns HR role catalog with salary scales, benefit multipliers, and labor type classifications.

---

## GET /api/v1/simulation/input/chain-b/parametros

**Purpose**: Retrieve active Cadena B parametrization (GN catalog)  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Response

Returns digital platform technology catalog with product types and standard costs.

---

## GET /api/v1/simulation/input/chain-c/parametros

**Purpose**: Retrieve active Cadena C parametrization (OP catalog)  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Response

Returns AI/integration catalog with vendor rates and integration costs.

---

# PARAMETRIZATION MANAGEMENT

## POST /api/v1/parametrization/{module}/upload

**Purpose**: Upload and activate a new parametrization Excel file  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 201 Created

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| module | string | Yes | Module to upload: "hr", "gn", or "op" |

**Body**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| file | file (multipart/form-data) | Yes | Excel file (.xlsx, .xls) |

**Allowed Extensions**: `.xlsx`, `.xls`

### Response

**HTTP Status**: 201 Created

```json
{
  "success": true,
  "data": {
    "version_id": "v20260531-abc123",
    "module": "hr",
    "filename": "HR_2026_Q2.xlsx",
    "uploaded_at": "2026-05-31T14:30:00Z",
    "rows_processed": 250,
    "validation_status": "OK",
    "is_active": true
  },
  "error": null
}
```

### Error Handling

| HTTP Status | Code | Message | Cause |
|--------|------|---------|-------|
| 400 | VALIDATION_ERROR | Invalid file type | File is not .xlsx or .xls |
| 422 | VALIDATION_ERROR | Data validation failed: {details} | Spreadsheet structure invalid |
| 400 | UPLOAD_ERROR | File parsing failed | Excel is corrupted or unreadable |
| 500 | DOMAIN_ERROR | Business rule violation | Parametrization conflicts with existing data |

---

## GET /api/v1/parametrization/{module}/versions

**Purpose**: List all uploaded versions of a parametrization module  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| module | string | Yes | Module: "hr", "gn", or "op" |

**Query Parameters**:
| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| limit | int | No | Max versions to return | 50 |
| offset | int | No | Skip first N versions | 0 |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": [
    {
      "version_id": "v20260531-abc123",
      "module": "hr",
      "filename": "HR_2026_Q2.xlsx",
      "uploaded_at": "2026-05-31T14:30:00Z",
      "is_active": true,
      "rows_processed": 250,
      "validation_status": "OK"
    },
    {
      "version_id": "v20260415-def456",
      "module": "hr",
      "filename": "HR_2026_Q1.xlsx",
      "uploaded_at": "2026-04-15T10:00:00Z",
      "is_active": false,
      "rows_processed": 248,
      "validation_status": "OK"
    }
  ],
  "error": null
}
```

---

## GET /api/v1/parametrization/{module}/active

**Purpose**: Retrieve the currently active parametrization version  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| module | string | Yes | Module: "hr", "gn", or "op" |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": {
    "version_id": "v20260531-abc123",
    "module": "hr",
    "filename": "HR_2026_Q2.xlsx",
    "uploaded_at": "2026-05-31T14:30:00Z",
    "is_active": true,
    "rows_processed": 250,
    "validation_status": "OK",
    "content": { ... }
  },
  "error": null
}
```

### Error Handling

| HTTP Status | Code | Message | Cause |
|--------|------|---------|-------|
| 404 | NOT_FOUND | No active parametrization for {module} | Never uploaded |

---

## GET /api/v1/parametrization/{module}/{version_id}/activate

**Purpose**: Activate a specific parametrization version  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| module | string | Yes | Module: "hr", "gn", or "op" |
| version_id | string | Yes | Version ID from /versions |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": {
    "version_id": "v20260415-def456",
    "module": "hr",
    "filename": "HR_2026_Q1.xlsx",
    "is_active": true,
    "activated_at": "2026-05-31T14:35:00Z",
    "message": "HR parametrization activated. Previous version: v20260531-abc123"
  },
  "error": null
}
```

### Error Handling

| HTTP Status | Code | Message | Cause |
|--------|------|---------|-------|
| 404 | NOT_FOUND | Version {version_id} not found | ID does not exist |
| 400 | DOMAIN_ERROR | Cannot activate version: {reason} | Version is corrupted or incompatible |

---

## DELETE /api/v1/parametrization/{module}/{version_id}

**Purpose**: Delete a parametrization version (cannot delete active version)  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 204 No Content

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| module | string | Yes | Module: "hr", "gn", or "op" |
| version_id | string | Yes | Version ID to delete |

### Response

**HTTP Status**: 204 No Content (no body)

### Error Handling

| HTTP Status | Code | Message | Cause |
|--------|------|---------|-------|
| 404 | NOT_FOUND | Version {version_id} not found | ID does not exist |
| 400 | DOMAIN_ERROR | Cannot delete active version | Must activate another version first |

---

# AUDIT & TRACEABILITY

## GET /api/v1/audit/simulations

**Purpose**: List all simulations with persisted audit/lineage traces  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Query Parameters**:
| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| limit | int | No | Max simulations to return | 50 |
| offset | int | No | Skip first N results | 0 |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": [
    {
      "simulation_id": "sim-20260531-abc123def456",
      "nodes_count": 1245,
      "roots_count": 42,
      "stages": ["inputs", "nomina_loader", "financial_costs", "vision_builders"],
      "generated_at": "2026-05-31T14:30:00Z"
    }
  ],
  "error": null
}
```

---

## GET /api/v1/audit/simulation/{simulation_id}

**Purpose**: Retrieve complete audit envelope (formulas, parameters, lineage)  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| simulation_id | string | Yes | ID from POST /calculate |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": {
    "simulation_id": "sim-20260531-abc123def456",
    "engine_version": "2.7.1",
    "formula_set": "formula-set-v2-7",
    "parametrization_hashes": {
      "hr": "sha256:abc123...",
      "gn": "sha256:def456...",
      "op": "sha256:ghi789...",
      "business_rules": "sha256:jkl012..."
    },
    "lineage": {
      "nodes_count": 1245,
      "roots": ["panel.meses_contrato", "panel.margen"],
      "stages_summary": { ... }
    },
    "formulas": [
      {
        "calculator": "NominaCalculator",
        "formula": "salario_fijo = salario_cargado × fte / meses",
        "stage": "nomina_loader",
        "used_count": 5
      }
    ],
    "parameters_used": {
      "request": { ... },
      "parametrization": { ... },
      "excel_refs": [ ... ]
    },
    "generated_at": "2026-05-31T14:30:00Z"
  },
  "error": null
}
```

---

## GET /api/v1/audit/simulation/{simulation_id}/explain

**Purpose**: Human-readable explanation of a specific calculated value  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| simulation_id | string | Yes | ID from POST /calculate |

**Query Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| value_name | string | Yes | Field name (e.g., "kpis.ingreso_neto_total") |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": {
    "simulation_id": "sim-20260531-abc123def456",
    "value_name": "kpis.ingreso_neto_total",
    "value": 92000000.0,
    "calculator": "KPIsCalculator",
    "formula": "SUM(pyg_por_mes[*].ingreso_neto)",
    "stage": "kpis_aggregation",
    "explanation": "Sum of monthly net revenues over 12 months. Net revenue = Gross revenue + contingencies - discounts - contingency reserves.",
    "refs_chain": [
      {
        "source_type": "calculated",
        "source_id": "pyg_mes_1.ingreso_neto",
        "value": 7666666.67,
        "sheet": "P&G",
        "cell": "C10",
        "formula": "ingreso_bruto + contingencia_op + contingencia_com + markup - descuento - imprevistos"
      }
    ]
  },
  "error": null
}
```

### Error Handling

| HTTP Status | Code | Message | Cause |
|--------|------|---------|-------|
| 404 | NOT_FOUND | Value {value_name} not found in simulation | Field does not exist or lineage not available |

---

## GET /api/v1/audit/simulation/{simulation_id}/baseline-diff

**Purpose**: Compare simulation KPIs against a certified baseline  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| simulation_id | string | Yes | ID from POST /calculate |

**Query Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| baseline_id | string | Yes | Baseline certificate ID |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": {
    "simulation_id": "sim-20260531-abc123def456",
    "baseline_id": "baseline-v2-7-official",
    "status": "MATCHED",
    "kpi_differences": {
      "costo_mensual_promedio": {
        "current": 5000000.0,
        "baseline": 5000000.0,
        "delta": 0.0,
        "pct_delta": 0.0
      }
    },
    "formula_set_match": true,
    "parametrization_match": true,
    "notes": "All KPIs and formulas match baseline. Certified."
  },
  "error": null
}
```

### Error Handling

| HTTP Status | Code | Message | Cause |
|--------|------|---------|-------|
| 404 | NOT_FOUND | Baseline {baseline_id} not found | Certificate ID does not exist |
| 400 | MISMATCH | KPI differences detected | Current simulation diverges from baseline |

---

# CERTIFICATION & VERSIONING

## GET /api/v1/certification/certificates

**Purpose**: List all execution certificates (certified mode results)  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Query Parameters**:
| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| limit | int | No | Max certificates to return | 50 |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": [
    {
      "certificate_id": "cert-20260531-abc123",
      "simulation_id": "sim-20260531-abc123def456",
      "formula_set": "formula-set-v2-7",
      "parametrization_hashes": {
        "hr": "sha256:abc123...",
        "gn": "sha256:def456...",
        "op": "sha256:ghi789...",
        "business_rules": "sha256:jkl012..."
      },
      "issued_at": "2026-05-31T14:30:00Z",
      "baseline_version": "v2-7-official"
    }
  ],
  "error": null
}
```

---

## GET /api/v1/certification/certificate/{certificate_id}

**Purpose**: Retrieve a specific execution certificate  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| certificate_id | string | Yes | Certificate ID from /certificates |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": {
    "certificate_id": "cert-20260531-abc123",
    "simulation_id": "sim-20260531-abc123def456",
    "formula_set": "formula-set-v2-7",
    "parametrization_hashes": {
      "hr": "sha256:abc123...",
      "gn": "sha256:def456...",
      "op": "sha256:ghi789...",
      "business_rules": "sha256:jkl012..."
    },
    "baseline_hash": "sha256:baseline123...",
    "baseline_matches": true,
    "kpis_certified": {
      "costo_mensual_promedio": 5000000.0,
      "ingreso_neto_total": 92000000.0,
      "contribucion_total": 32000000.0
    },
    "issued_at": "2026-05-31T14:30:00Z",
    "signature": "sig_20260531_abc123...",
    "notes": "Q2 2026 official pricing. Baseline matched."
  },
  "error": null
}
```

---

## POST /api/v1/certification/verify/{certificate_id}

**Purpose**: Verify a certificate against current parametrization (ensure reproducibility)  
**Version**: api-v1  
**Status**: Active  
**HTTP Status**: 200 OK

### Request

**Path Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| certificate_id | string | Yes | Certificate ID to verify |

### Response

**HTTP Status**: 200 OK

```json
{
  "success": true,
  "data": {
    "certificate_id": "cert-20260531-abc123",
    "status": "VALID",
    "verification_results": {
      "formula_set_match": true,
      "hr_parametrization_match": true,
      "gn_parametrization_match": true,
      "op_parametrization_match": true,
      "business_rules_match": true
    },
    "warnings": [],
    "verified_at": "2026-05-31T15:00:00Z"
  },
  "error": null
}
```

### Error Handling

| HTTP Status | Code | Message | Cause |
|--------|------|---------|-------|
| 404 | NOT_FOUND | Certificate {certificate_id} not found | ID does not exist |
| 400 | VERIFICATION_FAILED | Parametrization mismatch | Current environment differs from certified one |

---

# ERROR HANDLING

All endpoints return a consistent error response structure:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { ... }
  }
}
```

## Common Error Codes

| Code | HTTP Status | Meaning |
|------|--------|---------|
| VALIDATION_ERROR | 422 | Request validation failed (invalid JSON, missing fields, type mismatch, range violation) |
| DOMAIN_ERROR | 400 | Business rule violation (chain activation conflicts, invalid scenario references, policy conflict) |
| NOT_FOUND | 404 | Resource not found (simulation_id, certificate_id, version_id) |
| CALCULATION_FAILED | 500 | Engine calculation error (unhandled exception, insufficient parametrization) |
| VISION_INCOMPLETE | 500 | One or more output visions not computed |
| INTERNAL_ERROR | 500 | Server-side error (file I/O, storage corruption, etc.) |
| UPLOAD_ERROR | 400 | File upload failed (corrupted file, unsupported format) |
| VERIFICATION_FAILED | 400 | Certificate verification failed (parametrization mismatch) |

## Validation Error Details

When status code is 422, the error response includes a `details` field with per-field information:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": {
      "panel.meses_contrato": ["Must be between 1 and 120"],
      "panel.margen": ["Must be between -1.0 and 1.0"],
      "cadena_a.perfiles[0].fte": ["Must be >= 0.0"]
    }
  }
}
```

---

## End of API Reference

This comprehensive API reference covers:
- 8 Calculation endpoints (POST calculate, GET results, GET visions, GET traceability)
- 4 Input parametrization endpoints (GET panel/chain-a/b/c defaults)
- 6 Parametrization management endpoints (upload, versions, activate, delete)
- 4 Audit & traceability endpoints (list, audit envelope, explain, baseline diff)
- 3 Certification endpoints (list, get, verify)
- **27 total endpoints** with full request/response examples and error handling

For data structure definitions, see `DATA_MODEL.md`.
