# Contrato de Datos — Visión Imprimible

> **Estado**: Implementado y validado · 98 tests passing · 7/7 Excel match @ 0.00000%  
> **Fecha**: 2026-05-20  
> **Autores**: darwin.minota.quinto@accenture.com

---

## Principio Fundamental

> **El frontend SOLO renderiza. El backend SOLO calcula.**

El backend expone el JSON completo necesario para reconstruir la hoja "Visión Imprimible" del
Excel V2-4. El frontend **nunca** recalcula KPIs, márgenes, contribuciones, scores de riesgo,
tarifas o series temporales. Solo transforma el JSON en HTML/gráficos.

---

## Endpoint

```
POST /api/v1/simulation/calculate
```

**Body:**
```json
{
  "user_input": {
    "panel_de_control": { ... },
    "condiciones_cadena_a": { ... },
    "condiciones_cadena_b": { ... },
    "condiciones_cadena_c": { ... }
  }
}
```

**Response (estructura completa):**

```json
{
  "result_id": "uuid-...",
  "calculated_at": "2026-05-20T...",
  "ficha_deal": { ... },
  "kpis": { ... },
  "pyg_por_mes": [ ... ],
  "waterfall_promedio": { ... },
  "configuracion_comercial": { ... },
  "reglas_negocio": [ ... ],
  "evaluacion_riesgo": { ... },
  "cost_to_serve": { ... },
  "vision_tarifas": { ... },
  "panel": { ... }
}
```

---

## Sección 01 — Ficha del Deal

**Key en JSON**: `ficha_deal`  
**Fuente en Excel**: "Vision Imprimible" fila 11-13

```json
{
  "cliente":                  "Bancamia",
  "linea_negocio":            "Cobranzas",
  "ciudad":                   "Medellín",
  "sede":                     "Medellín",
  "tipo_cliente":             "No Grupo Aval",
  "antiguedad_cliente":       "Cliente Nuevo",
  "fecha_inicio":             "2026-01-01",
  "meses_contrato":           12,
  "periodo_pago_dias":        30,
  "ajuste_precio_tipo":       "IPC",
  "ajuste_precio_frecuencia": "Anual"
}
```

| Campo | Fuente backend | Celda Excel |
|-------|---------------|-------------|
| `cliente` | `panel.cliente` | B11 |
| `linea_negocio` | `panel.linea_negocio` | D11 |
| `ciudad` | `panel.ciudad` | F11 |
| `sede` | `panel.sede` | H11 |
| `tipo_cliente` | `panel.tipo_cliente` | J11 |
| `antiguedad_cliente` | `panel.antiguedad_cliente` | K11 |
| `fecha_inicio` | `panel.fecha_inicio` | B13 |
| `meses_contrato` | `panel.meses_contrato` | F13 |
| `periodo_pago_dias` | `panel.periodo_pago_dias` | H13 |
| `ajuste_precio_tipo` | `panel.indexacion.componente_humano` | J13 |
| `ajuste_precio_frecuencia` | `panel.indexacion.frecuencia` | L13 |

---

## Sección 02 — Economics KPIs

**Key en JSON**: `kpis`  
**Fuente en Excel**: "Vision Imprimible" fila 19

```json
{
  "ingreso_mensual":             355764509.40,
  "costo_mensual_promedio":      401864564.78,
  "facturacion_mensual_proyectada": 355764509.40,
  "pct_utilidad_neta_total":     -0.02,
  "valor_total_deal":            5564538255.66,
  "ingreso_neto_total":          5471188699.14,
  "costo_total_contrato":        ...,
  "contribucion_total":          ...,
  "utilidad_neta_total":         ...,
  "ingreso_bruto_total":         ...,
  "costo_cadena_a_promedio":     ...,
  "margen_minimo_requerido":     ...,
  "cumple_margen_minimo":        false
}
```

| Campo | Celda Excel | Mapeo |
|-------|-------------|-------|
| `ingreso_mensual` | B19 | `kpis.ingreso_mensual` |
| `costo_mensual_promedio` | H19 | `kpis.costo_mensual_promedio` |
| `pct_utilidad_neta_total` | N19 | `kpis.pct_utilidad_neta_total` |
| `valor_total_deal` | T19 | `kpis.valor_total_deal` |

---

## Sección 03 — Configuración Comercial

**Key en JSON**: `configuracion_comercial`  
**Fuente en Excel**: "Vision Imprimible" fila 38

```json
{
  "modelo_cobro_principal": "Fijo FTE",
  "pct_fijo_global":         0.5,
  "pct_variable_global":     0.5,
  "tarifa_fija":             0.0,
  "tarifa_variable":         29647042.45,
  "descuento":               0.0,
  "volumen_base_mensual":    7534.89,
  "margen_objetivo":         0.1339,
  "ingreso_mensual":         355764509.40,
  "costo_mensual_total":     401864564.78,
  "valor_total_deal":        5564538255.66
}
```

| Campo | Celda Excel | Derivación |
|-------|-------------|-----------|
| `modelo_cobro_principal` | B38 | `vision_tarifas.canales[0].modelo_cobro` |
| `pct_fijo_global` | C38 | `vision_tarifas.canales[0].pct_fijo` |
| `pct_variable_global` | D38 | `1 - pct_fijo_global` |
| `tarifa_fija` | E38 | `facturacion × pct_fijo` |
| `tarifa_variable` | F38 | `vision_tarifas.canales[0].tarifa_variable` |
| `descuento` | G38 | `panel.descuento` |
| `volumen_base_mensual` | N38 | `cost_to_serve.vol_cadena_b` |
| `margen_objetivo` | O38 | `panel.margen` |

---

## Sección 04 — Análisis Gráfico

### 04a. Waterfall del Precio (promedio mensual de meses activos)

**Key en JSON**: `waterfall_promedio`  
**Fuente en Excel**: "Vision Imprimible" fila 42-55 (chart)

```json
{
  "payroll_a":        30017216.83,
  "no_payroll_a":     9285618.27,
  "costo_b":          358701004.10,
  "costo_c":          0.0,
  "financiacion":     0.0,
  "polizas":          25738337.47,
  "ica":              ...,
  "gmf":              ...,
  "costo_total":      ...,
  "ingreso_bruto":    ...,
  "contingencias":    ...,
  "markup_descuento": 0.0,
  "ingreso_neto":     391274111.39,
  "contribucion":     ...,
  "meses_activos":    12
}
```

**El frontend construye el waterfall con estos datos.** El orden de construcción es:
1. `payroll_a` + `no_payroll_a` + `costo_b` + `costo_c` = Costo Operativo
2. `+ financiacion + polizas + ica + gmf` = Costos Financieros
3. `/ factor_margenes (panel)` → Ingreso Bruto
4. `+ contingencias + markup_descuento` = Ingreso Neto

### 04b. Evolución Mensual (ingreso_neto por mes)

**Key en JSON**: `pyg_por_mes[]`  
**Fuente en Excel**: "Visión P&G" filas C26:BJ26

Cada mes en `pyg_por_mes` contiene:

```json
{
  "mes": 1,
  "rampup": 0.85,
  "payroll_a": 30017216.83,
  "no_payroll_a": 9285618.27,
  "costo_b": 358701004.10,
  "costo_c": 0.0,
  "financiacion": 0.0,
  "polizas": 25738337.47,
  "ica": ...,
  "gmf": ...,
  "ingreso_bruto_a": ...,
  "ingreso_bruto_b": ...,
  "ingreso_bruto_c": 0.0,
  "contingencia_op": ...,
  "contingencia_com": 0.0,
  "markup_ingreso": 0.0,
  "descuento_ingreso": 0.0,
  "ingreso_bruto": ...,
  "ingreso_neto": 391274111.39,
  "costo_a": ...,
  "costos_financieros": ...,
  "costo_total": ...,
  "contribucion": ...,
  "pct_contribucion": ...,
  "utilidad_neta": ...,
  "pct_utilidad_neta": -0.02
}
```

---

## Sección 05 — Comparativo de Escenarios

**Key en JSON**: `vision_tarifas.canales[]`  
**Fuente en Excel**: "Vision Imprimible" filas 74-78

Cada canal en `vision_tarifas.canales` es un "escenario" de pricing:

```json
{
  "nombre_canal": "Inbound 10",
  "modalidad":    "Inbound",
  "producto":     "WhatsApp",
  "fte":          6,
  "vol_mensual":  7534.89,
  "modelo_cobro": "Fijo FTE",
  "componente_fijo":      "FTE",
  "pct_fijo":             0.5,
  "componente_variable":  "Transacción",
  "pct_variable":         0.5,
  "costo_atribuible":     ...,
  "ingreso_bruto":        ...,
  "facturacion":          355764509.40,
  "tarifa_fijo_fte":      29647042.45,
  "tarifa_variable":      29647042.45,
  "vol_minimo_transaccion": 5.09
}
```

| Campo | Celda Excel (Escenario 1) | Fuente |
|-------|--------------------------|--------|
| `modalidad` | C11 | `perfil.modalidad` |
| `producto` | C12 | `perfil.canal` |
| `modelo_cobro` | C13 | `perfil.modelo_cobro` |
| `componente_fijo` | C14 | derivado de `modelo_cobro` |
| `pct_fijo` | C15 | `perfil.pct_fijo` |
| `componente_variable` | C16 | derivado de `modelo_cobro` |
| `pct_variable` | C17 | `1 - pct_fijo` |
| `facturacion` | C19 | `ingreso_bruto × pct_fijo` |
| `tarifa_fijo_fte` | C20 | `facturacion / fte` |
| `tarifa_variable` | C21 | `(ingreso_bruto × pct_variable) / vol_mensual` |

**Nota**: El campo `estado` (Seleccionado/Alternativa) es **responsabilidad del frontend**:
el canal con mayor volumen o FTE es el principal; los demás son alternativos.

---

## Sección 06 — Control de Riesgo

**Key en JSON**: `evaluacion_riesgo`  
**Fuente en Excel**: "Vision Imprimible" filas 86-95 + hoja "Riesgo"

```json
{
  "score_cliente":     2.30,
  "score_operativo":   1.70,
  "score_total":       1.94,
  "clasificacion_total": "Medio",
  "requiere_aprobacion": true,
  "criterios": [
    {
      "id": 1,
      "factor": "Clasificación de oportunidad",
      "categoria": "Cliente",
      "valor_evaluado": "5564538255 COP",
      "calificacion": "Alto",
      "puntaje": 3,
      "peso": 0.30
    },
    {
      "id": 2,
      "factor": "Tipo de cliente",
      "categoria": "Cliente",
      "valor_evaluado": "No Grupo Aval",
      "calificacion": "Alto",
      "puntaje": 3,
      "peso": 0.25
    },
    {
      "id": 3,
      "factor": "Período de pago",
      "categoria": "Cliente",
      "valor_evaluado": "30 días",
      "calificacion": "Bajo",
      "puntaje": 1,
      "peso": 0.25
    },
    {
      "id": 4,
      "factor": "Experiencia con el cliente",
      "categoria": "Cliente",
      "valor_evaluado": "Cliente Nuevo",
      "calificacion": "Alto",
      "puntaje": 3,
      "peso": 0.10
    },
    {
      "id": 5,
      "factor": "Presupuesto de imprevistos",
      "categoria": "Cliente",
      "valor_evaluado": "no",
      "calificacion": "Bajo",
      "puntaje": 1,
      "peso": 0.10
    },
    {
      "id": 6,
      "factor": "Alertas activadas",
      "categoria": "Operativo",
      "valor_evaluado": "2",
      "calificacion": "Medio",
      "puntaje": 2,
      "peso": 0.30
    },
    {
      "id": 7,
      "factor": "Complejidad",
      "categoria": "Operativo",
      "valor_evaluado": "1",
      "calificacion": "Bajo",
      "puntaje": 1,
      "peso": 0.20
    },
    {
      "id": 8,
      "factor": "Capacitaciones",
      "categoria": "Operativo",
      "valor_evaluado": "7.0 días",
      "calificacion": "Bajo",
      "puntaje": 1,
      "peso": 0.20
    },
    {
      "id": 9,
      "factor": "Rotación",
      "categoria": "Operativo",
      "valor_evaluado": "6.5%",
      "calificacion": "Medio",
      "puntaje": 2,
      "peso": 0.20
    },
    {
      "id": 10,
      "factor": "Dependencia de terceros",
      "categoria": "Operativo",
      "valor_evaluado": "0",
      "calificacion": "Bajo",
      "puntaje": 1,
      "peso": 0.10
    }
  ]
}
```

### Fórmulas de scoring

```
score_cliente    = SUMPRODUCT(puntaje_i × peso_i)  para criterios categoria="Cliente"
score_operativo  = SUMPRODUCT(puntaje_i × peso_i)  para criterios categoria="Operativo"
score_total      = score_cliente × 0.4 + score_operativo × 0.6

clasificacion_total:
  score < 1.5   → "Bajo"
  1.5 ≤ score < 2.5 → "Medio"
  score ≥ 2.5   → "Alto"

requiere_aprobacion:
  valor_total_deal ≥ 1000 SMMLV (2026) = 1,423,500,000 COP
```

---

## Sección 07 — Contingencias y Reglas de Negocio

**Key en JSON**: `reglas_negocio[]`  
**Fuente en Excel**: "Vision Imprimible" filas 100-105

```json
[
  {
    "nombre":    "margen_objetivo",
    "label":     "Margen objetivo",
    "aplicado":  0.1339,
    "min_valor": null,
    "max_valor": null,
    "status":    "dentro_rango"
  },
  {
    "nombre":    "contingencia_operativa",
    "label":     "Contingencia Operativa",
    "aplicado":  0.02,
    "min_valor": 0.05,
    "max_valor": 0.08,
    "status":    "bajo_minimo"
  },
  {
    "nombre":    "contingencia_comercial",
    "label":     "Contingencia Comercial",
    "aplicado":  0.0,
    "min_valor": 0.04,
    "max_valor": 0.07,
    "status":    "bajo_minimo"
  },
  {
    "nombre":    "markup",
    "label":     "Markup",
    "aplicado":  0.0,
    "min_valor": 0.02,
    "max_valor": 0.08,
    "status":    "bajo_minimo"
  },
  {
    "nombre":    "descuento",
    "label":     "Descuento volumen",
    "aplicado":  0.0,
    "min_valor": 0.0,
    "max_valor": 0.08,
    "status":    "dentro_rango"
  }
]
```

**Lógica de status** (computada en `engine._calcular_reglas_negocio()`):

```
si aplicado < min_valor         → "bajo_minimo"
si aplicado > max_valor         → "excede_maximo"
en otro caso                    → "dentro_rango"
```

**Mapeo frontend** (Visión Imprimible fila 100-105):

| Fila | Item | Status posibles |
|------|------|----------------|
| 100 | Margen objetivo | `dentro_rango` / `excede_maximo` |
| 101 | Contingencia Operativa | `bajo_minimo` / `dentro_rango` / `excede_maximo` |
| 102 | Contingencia Comercial | `bajo_minimo` / `dentro_rango` / `excede_maximo` |
| 103 | Markup | `bajo_minimo` / `dentro_rango` / `excede_maximo` |
| 104 | Descuento | `dentro_rango` / `excede_maximo` |

---

## Cost to Serve

**Key en JSON**: `cost_to_serve`

```json
{
  "cts_cadena_a":     ...,
  "cts_cadena_b":     ...,
  "cts_ponderado":    ...,
  "participacion_a":  ...,
  "participacion_b":  ...,
  "fte_cadena_a":     12.0,
  "vol_cadena_b":     7534.89,
  "desglose_a": {
    "nomina":    ...,
    "no_payroll": ...,
    "total":     ...
  }
}
```

---

## Restricciones del contrato

### ✅ El frontend PUEDE

- Renderizar cualquier campo del JSON sin transformación adicional
- Construir gráficos usando `pyg_por_mes` (series temporales ya calculadas)
- Construir el waterfall usando `waterfall_promedio` (promedios ya calculados)
- Mostrar el semáforo de riesgo con `evaluacion_riesgo.clasificacion_total`
- Mostrar el estado de cada regla con `reglas_negocio[i].status`
- Formatear números en COP con separadores de miles
- Calcular `pct_variable = 1 - pct_fijo` solo para display (ya viene calculado en `pct_variable`)

### ❌ El frontend NUNCA DEBE

- Recalcular `kpis.ingreso_mensual`, `pct_utilidad_neta_total` u otro KPI
- Recalcular scores de riesgo
- Recalcular tarifas (`tarifa_fijo_fte`, `tarifa_variable`)
- Recalcular el waterfall (promedios, componentes)
- Determinar el status de reglas de negocio (debe usar `status` del backend)
- Aplicar factor_margenes u otras fórmulas financieras
- Truncar `pyg_por_mes` a menos de `panel.meses_contrato` meses
- Asumir que el primer canal en `vision_tarifas.canales` es siempre WhatsApp

---

## Gaps y Deuda Técnica

| Ítem | Prioridad | Descripción |
|------|-----------|-------------|
| Min/max reglas en storage | Media | `_calcular_reglas_negocio()` usa umbrales hardcodeados (CALIBRADO_EXCEL). Migrar a `storage/parametrization/gn/` cuando se implemente gestión de políticas comerciales. |
| Score riesgo vs Excel exacto | Media | `RiesgoCalculator` alinea con el Excel en el caso de referencia (score_total=1.94). Criterio 5 (presupuesto imprevistos) y Criterio 9 (rotación via pct_ausentismo como proxy) necesitan validación en más casos. |
| Escenario `estado` (frontend) | Baja | El campo `estado` (Seleccionado/Alternativa) en Sección 05 es responsabilidad del frontend (no hay información en backend sobre cuál escenario es "principal"). |
| Sección 08 (Firmas) | N/A | UI-only — no requiere datos del backend. |
| `SMMLV_2026` en RiesgoCalculator | Media | Hardcodeado como 1,423,500 COP. Debería leerse de `storage/parametrization/hr/`. |

---

## Fuentes de datos — trazabilidad completa

| Sección | Fuente backend | Hoja Excel origen |
|---------|---------------|-------------------|
| 01 Ficha | `panel.*` | Panel de Control General |
| 02 Economics | `kpis.*` | Vision Cost To Serve |
| 03 Config comercial | `vision_tarifas.canales[0]` + `panel` | Vision Tarifas_Modelo_Cobro |
| 04 Waterfall | `waterfall_promedio` ← `pyg_por_mes` | Visión P&G (promediado) |
| 04 Evolución | `pyg_por_mes[].ingreso_neto` | Visión P&G C26:BJ26 |
| 05 Escenarios | `vision_tarifas.canales[]` | Hoja Maestra Escenarios |
| 06 Riesgo | `evaluacion_riesgo` | Riesgo B3:N18 |
| 07 Contingencias | `reglas_negocio[]` | Panel de Control General B66:E70 |
| CTS | `cost_to_serve.*` | Vision Cost To Serve |

---

## Cambios implementados en este sprint

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `domain/models.py` | Nuevos: `ReglaNegocios`, `WaterfallPromedio`, `CriterioRiesgo`, `EvaluacionRiesgo`. Enriquecido: `TarifaCanal` (`pct_variable`, `tarifa_variable`, `componente_fijo`, `componente_variable`, `vol_minimo_transaccion`). `PricingResult` recibe 3 nuevos campos opcionales. |
| `calculators/riesgo.py` | **Nuevo** — `RiesgoCalculator` con 10 criterios y scoring calibrado contra Excel V2-4 |
| `calculators/vision_tarifas.py` | Enriquecido — `TarifaCanal` ahora incluye los campos de facturación variable |
| `engine.py` | Integra `RiesgoCalculator`, `_calcular_waterfall()`, `_calcular_reglas_negocio()` |
| `adapters/pricing_serializer.py` | Nuevo `ficha_deal`, `waterfall_promedio`, `configuracion_comercial`, `reglas_negocio`, `evaluacion_riesgo` en la respuesta |

### Invariantes preservados

- ✅ 98 tests passing (63 unit + 35 integration) — sin regresiones
- ✅ Baseline match. Sin drift.
- ✅ Excel V2-4 validation: 7/7 @ 0.00000% delta
- ✅ Ninguna fórmula matemática del pipeline modificada
