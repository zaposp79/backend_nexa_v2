# Vision Cost To Serve — Frontend Contract V1

**Endpoint:** `GET /api/v1/simulation/{simulation_id}/results/cost-to-serve`

## Overview

This endpoint returns the **Cost To Serve (CTS)** breakdown with charts for the frontend to render without runtime dependency on Excel. The response is a fully self-contained API contract that includes:

- **cost_to_serve**: CTS metrics by cadena (A, B, C) with detailed breakdowns
- **vision_por_servicio**: CTS rollup per service (SAC, Technical Support, etc.)
- **vision_por_canal**: CTS rollup per channel (Chat, Email, Phone, etc.)
- **detalle_por_canal**: Per-channel cost details for staffing and ops
- **estructura_equipo**: Team structure with FTE, roles, and payroll
- **charts**: Chart configurations and availability status

## Response Structure

### ApiResponse Wrapper

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "charts_version": "1.0"
  }
}
```

**Fields:**
- `success` (boolean): Always `true` on 200-level responses
- `data` (object): Response payload (see sections below)
- `error` (null | ErrorDetail): `null` on success
- `meta` (object): Metadata about API version and charts version

### error (on 4xx/5xx)

```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND|VALIDATION_ERROR|INTERNAL_SERVER_ERROR",
    "message": "Human-readable error description"
  }
}
```

---

## Data Sections

### 1. cost_to_serve

**Type:** Object  
**Required fields:**
- `cts_cadena_a`, `cts_cadena_b`, `cts_cadena_c` (number): CTS per cadena in COP/month
- `cts_ponderado` (number): Weighted average CTS
- `participacion_a`, `participacion_b`, `participacion_c` (number): % contribution by cadena
- `fte_cadena_a` (number): Full-time equivalent count for Cadena A
- `vol_cadena_b`, `vol_cadena_c` (number): Monthly transaction/ticket volume
- `costo_total_acumulado` (number): Sum of all CTS
- `canal_view_habilitado` (boolean): Whether channel-level detail is available

**Optional sections:**
- `desglose_a` (object): Payroll + OpEx breakdown for Cadena A
  - Fields: `nomina`, `no_payroll`, `nomina_loaded`, `salario_fijo`, `salario_variable`, `capacitacion_inicial`, `capacitacion_rotacion`, `examenes`, `estudios_seguridad`, `crucero`, `opex_fijo`, `inversiones`, `costos_fijos_estacion`
- `desglose_b` (object): Cadena B cost breakdown
  - Fields: `componente_fijo`, `componente_variable`, `opex`, `inversiones`, `soporte_mantenimiento`, `tarifa`, `opex_variable`, `tasa_escalamiento`, `hitl`
- `canales_detalle` (array): Per-channel cost details (only if `canal_view_habilitado=true`)

### 2. vision_por_servicio

**Type:** Array of objects  
**Each object represents one service (e.g., "SAC", "Soporte Técnico")**

**Fields:**
- `servicio` (string): Service name
- `ingreso_mensual` (number): Monthly revenue
- `cts_ponderado` (number): CTS for this service
- `costo_mensual` (number): Total monthly cost
- `margen` (number): Gross margin (ingreso - costo)
- `contribucion_total` (number): Total contribution to P&L
- `fte_total` (number): Total FTE assigned to service
- `volumen_mensual` (number): Transactions/tickets per month
- `meses_contrato` (number): Contract duration in months
- `cadenas_activas` (array[string]): Which cadenas are active for this service

**Use:** Frontend can display service-level KPIs and economics.

### 3. vision_por_canal

**Type:** Array of objects  
**Each object represents one channel (e.g., "Chat", "Email", "Phone")**

**Fields:**
- `canal` (string): Channel name
- `modalidad` (string): "Inbound" | "Outbound" | "Blended"
- `modelo_cobro` (string): Billing model (e.g., "Por transacción", "Por volumen", "Por minuto")
- `estado` (string): "Activo" | "Inactivo"
- `fte` (number): FTE allocated to this channel
- `participacion_cadena_a` (number): % of channel effort in Cadena A
- `volumen_mensual` (number): Monthly transaction count
- `facturacion` (number): Total monthly billing
- `ingreso_bruto` (number): Gross income (may differ from facturacion)
- `costo_atribuible` (number): Cost allocated to this channel
- `pct_fijo` (number): % of cost that is fixed (vs variable)
- `pct_variable` (number): % of cost that is variable

**Use:** Frontend can render channel KPI cards, channel-by-channel economics.

### 4. detalle_por_canal

**Type:** Array of objects  
**Per-channel operational details (same structure as canales_detalle in cost_to_serve)**

**Fields:** Mirrors `cost_to_serve.canales_detalle` structure for backward compatibility.

### 5. estructura_equipo

**Type:** Object  
**Team structure and payroll breakdown**

**Fields:**
- `roles` (array[object]): Individual role assignments
  - Each role: `{ rol, cargo_tipo, canal, modalidad, fte, es_soporte, salario_cargado_unitario, costo_mensual }`
- `por_cargo` (array[object]): Aggregated by role type
  - Each: `{ cargo_tipo, fte, costo_mensual }`
- `fte_total` (number): Total FTE
- `fte_agentes` (number): FTE for agents (non-support)
- `fte_soporte` (number): FTE for support roles
- `costo_total_mensual` (number): Total payroll + benefits

**Use:** Frontend can render team structure org charts, staffing dashboards.

---

## Charts Section

### 5. charts.configurations

**Type:** Array of chart objects  
**Each object is a complete chart configuration ready for frontend rendering**

**Chart object structure:**

```json
{
  "id": "cts_por_cadena_stacked",
  "title": "CTS Ponderado por Cadena",
  "type": "bar_stacked|bar_horizontal|pie|bar_grouped",
  "source": "pricing_result.cost_to_serve",
  "x_axis": { "field": "...", "format": "string|number|currency|percentage" },
  "y_axis": { "field": "...", "format": "..." },
  "series": [
    { "name": "Series Name", "value_field": "field_name" }
  ],
  "data": [...]
}
```

**Field definitions:**
- `id` (string): Unique chart identifier (snake_case)
- `title` (string): Display title for chart
- `type` (string): Chart type — supported by frontend renderer
  - `bar_stacked`: Stacked bar chart
  - `bar_horizontal`: Horizontal bar chart
  - `bar_grouped`: Grouped (side-by-side) bars
  - `pie`: Pie/donut chart
- `source` (string): Semantic path to data source (informational for debugging)
- `x_axis`, `y_axis` (object): Axis configuration
  - `field` (string): Field name from data array
  - `format` (string): Formatting hint — `string`, `number`, `currency`, `percentage`
- `series` (array[object]): Series definitions for multi-series charts
  - `name` (string): Series label
  - `value_field` (string): Field name in data to plot
- `data` (array[object]): Raw data points — format depends on chart type

### Charts Available (V1.0)

| Chart ID | Title | Type | Data Source | Use Case |
|---|---|---|---|---|
| `cts_por_cadena_stacked` | CTS Ponderado por Cadena | bar_stacked | cost_to_serve | View CTS breakdown by cadena A/B/C |
| `vision_por_canal_fte` | FTE por Canal | bar_horizontal | vision_por_canal | Staffing distribution by channel |
| `vision_por_servicio_economics` | Economics por Servicio | bar_grouped | vision_por_servicio | Service profitability comparison |
| `fte_estructura_pie` | Distribución FTE — Agentes vs Soporte | pie | estructura_equipo | Team composition (agents vs support) |
| `nomina_por_cargo` | Participación Nómina por Cargo | bar_horizontal | estructura_equipo.por_cargo | Payroll breakdown by role |
| `desglose_b_por_componente` | Desglose Cadena B — Componentes | bar_horizontal | cost_to_serve.desglose_b | Cadena B cost structure |

### Charts Not Yet Implemented (Gaps)

| Gap ID | Title | Reason | Required Source |
|---|---|---|---|
| `nomina_por_grupo` | Nómina por Grupo (Ops, QA, HR, etc.) | Semantic group mapping not persisted | `grupo_semantico` field in estructura_equipo |
| `detalle_canal_waterfall` | Waterfall: A → B → Financiero → CTS | Waterfall structure not yet computed | Structured waterfall fact in cost_to_serve |
| `risk_heatmap` | Risk Heatmap (Total, Cliente, Operativo) | Risk evaluation not in CTS endpoint | `evaluacion_riesgo` field |
| `comparativo_escenarios` | Scenario Comparison by Channel | Scenario variants not persisted per channel | `escenarios_comerciales[]` per channel |

### 5. charts.data_status

**Type:** Object  
**Status of chart availability and data gaps**

```json
{
  "available_charts": 6,
  "missing_charts": 4,
  "missing_upstream_data": [
    {
      "chart_id": "nomina_por_grupo",
      "reason": "missing_semantic_group_mapping",
      "required_source": "grupo_semantico persisted in estructura_equipo.por_cargo"
    }
  ]
}
```

**Fields:**
- `available_charts` (int): Count of charts ready to render
- `missing_charts` (int): Count of charts blocked by missing data
- `missing_upstream_data` (array[object]): Details on why charts are blocked
  - `chart_id` (string): Chart ID that requires this data
  - `reason` (string): Why this chart is blocked (semantic identifier)
  - `required_source` (string): Where the data should come from to unblock

---

## Frontend Implementation Guide

### Reading Configuration

1. **Check availability first:**
   ```javascript
   const { available_charts, missing_charts, missing_upstream_data } = data.charts.data_status;
   if (available_charts > 0) {
     // Safe to render charts
   }
   ```

2. **Iterate through configurations:**
   ```javascript
   data.charts.configurations.forEach(chart => {
     renderChart(chart.id, chart.title, chart.type, chart.data);
   });
   ```

3. **Apply axis formatting:**
   - `x_axis.format` and `y_axis.format` guide how to format labels:
     - `currency`: Format as COP with thousands separator
     - `percentage`: Display as % (0.5 → "50%")
     - `number`: Plain number with decimals
     - `string`: No formatting

4. **Render series:**
   - For `bar_stacked` and `bar_grouped`: Loop through `series` to know which fields to render
   - For `pie`: Use first series name and `data[i].label` as pie slice label
   - Field names in `series[].value_field` tell you which field in data to use

### Handling Gaps

```javascript
if (missing_charts > 0) {
  // Display notification: "Some charts are pending upstream features"
  missing_upstream_data.forEach(gap => {
    console.warn(`Chart ${gap.chart_id}: ${gap.reason}`);
    // Optionally show disabled state or grayed-out placeholder
  });
}
```

### No Runtime Excel Dependency

- This endpoint is **self-contained**. Frontend does NOT need Excel to render.
- The endpoint reads from persisted simulation results (storage/simulation_results/{id}.json).
- Charts configurations are **pure data** — no formulas, no Excel references.
- If upstream data becomes available (e.g., semantic groups for "nomina_por_grupo"), the endpoint will include the chart without frontend changes.

---

## Data Formats & Currency

- **Currency values:** All amounts in COP (Colombian Peso), monthly basis unless specified
- **Numbers:** Decimal precision to 2 places (e.g., `270.75`)
- **Percentages:** Stored as decimals (0.556 = 55.6%)
- **Dates:** ISO 8601 (yyyy-mm-dd) where applicable

---

## Error Responses

### 404 Not Found

```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Simulation 'sim_xyz' not found"
  }
}
```

### 500 Internal Server Error

```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "Failed to load simulation result"
  }
}
```

---

## Version History

### V1.0 (Current)

- Endpoint: `GET /api/v1/simulation/{id}/results/cost-to-serve`
- 6 charts available (cts, canal_fte, servicio_economics, fte_pie, nomina_cargo, desglose_b)
- 4 gaps documented (nomina_grupo, waterfall, risk_heatmap, scenarios)
- Full backward compatibility with pre-chart responses
- Meta field: `charts_version: "1.0"`

---

## Testing

See [`docs/api/vision_cost_to_serve_response_v1.example.json`](vision_cost_to_serve_response_v1.example.json) for a complete example response.

To validate the contract locally:

```bash
# JSON validation
python -m json.tool docs/api/vision_cost_to_serve_response_v1.example.json

# Contract tests
PYTHONPATH=$(pwd) pytest tests/api/test_cost_to_serve_endpoint.py -v
PYTHONPATH=$(pwd) pytest tests/vision_cost_to_serve/ -v
```

---

## Support & Questions

- Backend owner: `vision_cost_to_serve` module (modules/vision_cost_to_serve/)
- Chart mapper: `ChartsMapper` in modules/vision_cost_to_serve/helpers/charts_mapper.py
- Formula owner: `CostToServeCalculator` in modules/calculator_motor/formulas/cts/
- For gaps/features: Refer to `missing_upstream_data` in response; gaps are documented with required sources.
