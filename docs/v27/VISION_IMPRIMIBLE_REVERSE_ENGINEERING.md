# Visión Imprimible — Ingeniería Inversa Excel V2-7

## Estructura Excel (A1:AB119) — 7 secciones

Esta vista es PURA COMPOSICIÓN: no tiene fórmulas propias, solo referencias a otras hojas.

### 01 · FICHA DEL DEAL (filas 7-13)
| Fila | Label | Fórmula Excel | Backend |
|------|-------|---------------|---------|
| 11 | CLIENTE | =IF(Panel!C7="Cliente Nuevo", Panel!D6, Panel!C6) | ficha.cliente |
| 13 | FECHA DE INICIO | =Panel!C10 | ficha.fecha_inicio |
| 13H | DURACIÓN | =Panel!C11 & " meses" | ficha.duracion_meses |
| — | SERVICIO | =Panel!C5 | ficha.linea_negocio |

### 02 · ECONOMICS (filas 15-20)
| Fila | Label | Fórmula Excel | Backend |
|------|-------|---------------|---------|
| 19B | INGRESO MENSUAL | =IFERROR('Vision Tarifas'!C72, 0) | economics.ingreso_mensual |
| 19H | COST TO SERVE MENSUAL | ='Visión P&G'!BK30/'Visión P&G'!E6 | economics.cts_mensual |
| 20 | MARGEN | — | economics.margen |

### 03 · CONFIGURACIÓN COMERCIAL (filas 32-38)
| Fila | Label | Fórmula Excel | Backend |
|------|-------|---------------|---------|
| 36B | MODELO DE COBRO | =IFERROR('Vision Tarifas'!C33, "-") | configuracion.modelo_cobro |
| 36I | COMPONENTE FIJO | =IFERROR(C34 & " (" & TEXT(D34,"0%") & ")", "-") | configuracion.componente_fijo |
| 38B | TARIFA FIJA | ='Vision Tarifas'!G47 | configuracion.tarifa_fija |
| 38D | TARIFA VARIABLE | ='Vision Tarifas'!G55 | configuracion.tarifa_variable |
| 38I | DESCUENTO | =Panel!C70 | configuracion.descuento |

### 04 · ANÁLISIS GRÁFICO (filas 40-67)
- Waterfall: payroll_a → no_payroll → costo_b → costo_c → financieros → ingreso_bruto → ingreso_neto → contribución
- Evolución Mensual: mes × (ingreso_neto, costo_total, contribucion, margen%)

Backend: `WaterfallPromedio` + `EvolucionMensual` ✓

### 05 · COMPARATIVO DE ESCENARIOS (filas 70-78)
| Fila | Col B | Col D | Col I | Backend |
|------|-------|-------|-------|---------|
| 74 | =Panel!B80 (Esc1 label) | CONCAT(modal, " - ", canal) | Comp.fijo + % | comparativo_escenarios[0] |
| 75 | =Panel!B87 (Esc2 label) | … | … | comparativo_escenarios[1] |
| … | offset +7 por escenario | … | … | |
| 78 | =Panel!B108 (Esc5 label) | … | … | comparativo_escenarios[4] |

**Límite Excel**: 5 escenarios hardcoded. Backend: lista dinámica.

### 06 · CONTROL Y APROBACIÓN (filas 81-95)
| Fila | Label | Fórmula | Backend |
|------|-------|---------|---------|
| 87 | SCORE CLIENTE | =Riesgo!E17 | evaluacion_riesgo.score_cliente |
| 90 | SCORE OPERATIVO | =Riesgo!E16 | evaluacion_riesgo.score_operativo |
| 92 | SCORE GENERAL DEAL | =Riesgo!E18 | evaluacion_riesgo.score_total |

### 07 · CONTINGENCIAS Y AJUSTES (filas 97+)
Tabla de reglas: margen, op_cont, com_cont, markup, descuento.
Backend: `reglas_negocio: List[ReglaNegocios]` ✓

## Gaps
| ID | Descripción |
|----|-------------|
| GAP-IMP-01 | Excel tiene 5 filas de escenarios hardcoded; backend expone lista dinámica. Frontend debe manejar hasta N escenarios. |
| GAP-IMP-02 | `economics.cts_mensual` = P&G!BK30 / P&G!E6; backend usa `cost_to_serve.cts_ponderado / meses_contrato` (equivalente) |
| GAP-IMP-03 | COMPONENTE FIJO label: `C34 & " (" & TEXT(D34,"0%") & ")"` — backend expone `componente_fijo` string + `pct_fijo` float; composición en frontend |
