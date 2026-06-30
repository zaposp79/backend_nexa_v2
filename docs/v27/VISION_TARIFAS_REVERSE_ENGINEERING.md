# Visión Tarifas_Modelo_Cobro — Ingeniería Inversa Excel V2-7

## Estructura Excel (A1:S180)

### Header (filas 2-4)
Título + info cliente/servicio del Panel.

### Resumen Resultado Escenarios (filas 7-22)
Tabla de 6 columnas: Escenario 1-5 + Total

| Fila | Label | Fórmula representativa | Backend |
|------|-------|------------------------|---------|
| 10 | Headers (Esc1..Esc5, Total) | array formula vs Panel!A81:D113 | EscenarioComercial[] |
| 11-17 | Atributos escenario (Modalidad, Canal, Modelo...) | INDEX/MATCH contra Panel | EscenarioComercial.{campo} |
| 19 | Facturación [Directo] | ='Hoja Maestra Escenarios'!C47 | TarifaCanal.facturacion |
| 20 | Tarifa Componente Fijo | ='Hoja Maestra Escenarios'!G21 | TarifaCanal.tarifa_fijo_fte |
| 21 | Tarifa Componente Variable | =IF(C16="Transacción", HMS!G31, IF(OR(C16="Resultados","Honorarios"), HMS!G33, 0)) | TarifaCanal.tarifa_variable (condicional) |

### Modelo de Cobro Detalle (filas 25-72)
| Fila | Label | Fórmula | Backend |
|------|-------|---------|---------|
| 29 | Total Márgenes/Reglas | =SUM(G30:G32)+G35-G33 | panel.op_cont + com_cont + markup - descuento |
| 37 | FTE | =IF(C29="Total", SUM(CondicionesA!E17:S17), SUMIFS(..., modal, canal)) | perfil_agente.fte |
| 40 | CADENA A Total | =SUM(C41:C46) | TarifaCanal.costo_cadena_a_ch |
| 47 | Ingreso - Cadena A | =C40/((1-G35)(1-G30)(1-G31)(1-G32)(1+G33)) | TarifaCanal.ingreso_bruto |
| 50 | CADENA B Total | =SUM(C51:C56) | TarifaCanal.cadena_b_atribuible |
| 57 | Ingreso - Cadena B | =C50/factor_b | — (no expuesto separado) |
| 60 | CADENA C Total | =SUM(C61:C66) | — |
| 67 | Ingreso - Cadena C | =C60/factor_c | — |
| 72 | Facturación Total | =IFERROR(C47,0)+IFERROR(C57,0)+C67 | ResultadoVisionTarifas.ingreso_mensual |

### Factor denominador (para filas 47/57/67)
```
(1-margen_a) × (1-cont_op) × (1-cont_com) × (1-markup) × (1+descuento)
```

## Reglas de activación condicional

| Elemento | Condición | Comportamiento |
|----------|-----------|----------------|
| Tarifa Variable (row 21) | C16 = tipo componente variable | Si no aplica → 0 |
| Label "Tarifa por FTE / minuto" (row 45) | C34 = "FTE" o "Tiempo" | Label cambia dinámicamente |
| Vol Mínimo Transacción (row 57) | C35 = "Transacción" | IFERROR → 0 si no transaccional |
| FTE (row 37) | Escenario = "Total" | SUM all; sino SUMIFS por modal+canal |

## Gaps
| ID | Descripción |
|----|-------------|
| GAP-VT-01 | "Hoja Maestra Escenarios" no es una vista del backend; es hoja de cálculo intermedia de Excel. Backend lo computa inline. |
| GAP-VT-02 | Canal "Correo/Outbound" skipped si no hay perfil → `continue` en VisionTarifasCalculator (correcto, no un bug) |
| GAP-VT-03 | `voz_payroll_annual` fallback a todos los canales si no hay "voz" (fix aplicado 2026-05-29) |
