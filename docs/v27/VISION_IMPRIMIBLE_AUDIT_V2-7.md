# AUDITORÍA Y RECONSTRUCCIÓN — VISIÓN IMPRIMIBLE (PARIDAD EXCEL V2-7)

> Fuente: `excel/Nexa - Pricing - Simulador - V2-7.xlsx` · hoja **"Visión Imprimible"** (índice 18, rango `A1:AB119`).
> Método: extracción literal de fórmulas (`data_only=False`) + valores calculados (`data_only=True`).
> Esta auditoría **reemplaza** la versión preliminar de `VISION_IMPRIMIBLE_REVERSE_ENGINEERING.md`, que omitía
> ~15 campos hoy presentes en V2-7 (ver §FASE 5).

**Principio estructural confirmado:** la hoja es **pura composición/presentación**. NO contiene un solo cálculo
propio — todas las celdas calculadas son referencias a otras hojas (`Panel de Control General`,
`Vision Tarifas_Modelo_Cobro`, `Visión P&G`, `Vision Cost To Serve`, `Riesgo`). Por tanto, **no debe recalcularse
nada en backend**: la reconstrucción es un *builder* de composición sobre resultados ya certificados.

---

## FASE 1 — INVENTARIO DE SECCIONES

Numeración literal del Excel (texto de los encabezados de sección):

| # | Sección (texto Excel) | Filas | Subtítulo |
|---|------------------------|-------|-----------|
| 00 | Cabecera / banner | 2-4, S7 | "Visión Final del Deal" + banner de aprobación |
| 01 | `01 · FICHA DEL DEAL` | 7-13 | Información general del contrato |
| 02 | `02 · ECONOMICS` | 15-20 | Pricing |
| 03 | `03 · CONFIGURACIÓN COMERCIAL` | 32-38 | Modelo de cobro y parámetros del deal |
| 04 | `04 · ANÁLISIS GRÁFICO` | 40-69 | Waterfall + Evolución Mensual |
| 05 | `05 · COMPARATIVO DE ESCENARIOS` | 70-79 | Hasta 5 escenarios |
| 06 | `06 · CONTROL Y APROBACIÓN` | 81-95 | Riesgo + alertas de aprobación + 10 preguntas |
| 07 | `07 · CONTINGENCIAS Y AJUSTES` | 97-105 | Aplicado vs mín/máx |
| 08 | `08 · Aprobaciones` | 107-117 | Firmas (inputs libres) |

> Nota: la sección de **Contingencias** del Excel V2-7 es la **07** (no la 06 como decía el doc previo).
> "Gráficos" y "Escenarios" del brief de misión corresponden a las secciones 04 y 05.

---

## FASE 2 — MAPEO EXCEL (evidencia literal)

Leyenda Tipo: **I**=Input · **C**=Calculado · **D**=Derivado (concat/format) · **V**=Visual/literal.
Todas las celdas son de la hoja `Visión Imprimible`; la columna *Origen* indica la hoja referenciada.

### 00 · Cabecera / Banner

| Celda | Label | Fórmula literal | Origen | Tipo |
|-------|-------|-----------------|--------|------|
| O3 | CLIENTE (header) | `=IF('Panel de Control General'!$C$7="Cliente Nuevo",Panel!D6,Panel!C6)` | Panel | D |
| O4 | Resumen | `="Servicio: " & Panel!C5 & "  ·  " & Panel!C12` | Panel | D |
| S7 | Banner aprobación | `=IF(IF(M91="✓  Requerida",1,0)+IF(M92="✓  Requerida",1,0)+IF(M93="✓  Requerida",1,0)<1,"No requiere aprobación","El deal requiere aprobación, por favor revisar (Sección 6)")` | (self) | C |

### 01 · FICHA DEL DEAL (filas 10-13)

| Celda | Label | Fórmula literal | Origen | Tipo |
|-------|-------|-----------------|--------|------|
| B11 | CLIENTE | `=IF(Panel!$C$7="Cliente Nuevo",Panel!D6,Panel!C6)` | Panel C6/D6 + C7 | D |
| H11 | SERVICIO | `=Panel!C5` | Panel C5 | C |
| N11 | CIUDAD / SEDE | `=Panel!C12 & " · " & Panel!C13` | Panel C12,C13 | D |
| T11 | TIPO DE CLIENTE | `=Panel!C8 & " · " & Panel!C7` | Panel C8,C7 | D |
| B13 | FECHA DE INICIO | `=Panel!C10` | Panel C10 | C |
| H13 | DURACIÓN | `=Panel!C11 & " meses"` | Panel C11 | D |
| N13 | PERIODO DE PAGO | `=Panel!C9 & " días"` | Panel C9 | D |
| T13 | AJUSTE DE PRECIO | `=Panel!L7 & " · " & Panel!L8` | Panel L7,L8 | D |

### 02 · ECONOMICS (filas 18-20)

| Celda | Label | Fórmula literal | Origen | Tipo |
|-------|-------|-----------------|--------|------|
| B19 | INGRESO MENSUAL | `=IFERROR('Vision Tarifas_Modelo_Cobro'!$C$72,0)` | Tarifas C72 | C |
| B20 | (sub) escenario | `='Vision Tarifas_Modelo_Cobro'!C29` | Tarifas C29 | C |
| H19 | COST TO SERVE MENSUAL | `='Visión P&G'!$BK$30/'Visión P&G'!$E$6` | P&G BK30,E6 | C |
| N19 | MARGEN DEL DEAL | `=Panel!C63` | Panel C63 | C |
| N20 | (estado margen) | `=IFS(N19<M101,"⚠  Bajo mínimo",N19>Q101,"✓  Excede máximo",TRUE,"✓  Dentro de rango")` (array) | self | C |
| T19 | VALOR TOTAL DEL CONTRATO | `='Vision Cost To Serve'!C200` | CTS C200 | C |
| T20 | (sub) acumulado | `="Acumulado en " & Panel!C11 & " meses"` | Panel C11 | D |

### 03 · CONFIGURACIÓN COMERCIAL (filas 36-38)

| Celda | Label | Fórmula literal | Origen | Tipo |
|-------|-------|-----------------|--------|------|
| B36 | MODELO DE COBRO | `=IFERROR('Vision Tarifas_Modelo_Cobro'!C33,"-")` | Tarifas C33 | C |
| I36 | COMPONENTE FIJO | `=IFERROR(Tarifas!C34 & " (" & TEXT(Tarifas!D34,"0%") & ")","-")` | Tarifas C34,D34 | D |
| P36 | COMPONENTE VARIABLE | `=IFERROR(Tarifas!C35 & " (" & TEXT(Tarifas!D35,"0%") & ")","-")` | Tarifas C35,D35 | D |
| B38 | TARIFA FIJA | `='Vision Tarifas_Modelo_Cobro'!G47` | Tarifas G47 | C |
| D38 | TARIFA VARIABLE | `='Vision Tarifas_Modelo_Cobro'!G55` | Tarifas G55 | C |
| I38 | DESCUENTO APLICADO | `=Panel!C70` | Panel C70 | C |
| N38 | VOLUMEN BASE / MES | `=Panel!L52` | Panel L52 | C |
| T38 | MARGEN OBJETIVO | `=Panel!C63` | Panel C63 | C |

### 04 · ANÁLISIS GRÁFICO (filas 42-69) — solo data, no render

- **01. WATERFALL** (B42): serie de componentes promedio del deal.
- **02. EVOLUCIÓN MENSUAL — Ingreso Neto proyectado** (B56): serie por mes.

Estos bloques son gráficos embebidos; las **series** se alimentan de `Visión P&G` (mensual) y de los promedios
waterfall. No hay celdas de valor escalar en la hoja para estos gráficos (son objetos chart). Ver §GRÁFICOS.

### 05 · COMPARATIVO DE ESCENARIOS (filas 74-78) — 5 filas (offset +7 entre escenarios)

Patrón por escenario *n* (fila 74 = Esc1, 75 = Esc2 … 78 = Esc5). Bloques Panel `B80/B87/B94/B101/B108`:

| Col | Label | Fórmula (Esc1, fila 74) | Origen | Tipo |
|-----|-------|--------------------------|--------|------|
| B74 | Escenario | `=Panel!B80` | Panel | C |
| D74 | Modalidad - Canal | `=CONCAT(IF(Panel!C81<>"",C81,"")," - ",IF(C82<>"",C82,""))` | Panel C81,C82 | D |
| F74 | MODELO | `=Panel!C83` | Panel C83 | C |
| I74 | COMPONENTE FIJO | `=IFERROR(Panel!C84 & " (" & TEXT(D84,"0%") & ")","-")` | Panel C84,D84 | D |
| M74 | COMPONENTE VARIABLE | `=IFERROR(Panel!C85 & " (" & TEXT(D85,"0%") & ")","-")` | Panel C85,D85 | D |
| Q74 | TARIFA FIJA | `='Vision Tarifas_Modelo_Cobro'!C20` | Tarifas C20 | C |
| T74 | TARIFA VARIABLE | `='Vision Tarifas_Modelo_Cobro'!C21` | Tarifas C21 | C |
| W74 | ESTADO | `=IF(B74=Tarifas!$C$29,"★  SELECCIONADO","Alternativa")` | Tarifas C29 | C |

Esc2→`Panel!B87,C88,C89,C90,C91,C92` + `Tarifas!D20,D21`; Esc3→`Panel!B94…` + `Tarifas!E20,E21`;
Esc4→`Panel!B101…` + `Tarifas!F20,F21`; Esc5→`Panel!B108…` + `Tarifas!G20,G21`.

Nota literal B79: *"el escenario SELECCIONADO usa valores calculados por el motor. Los demás son estimaciones comparativas basadas en CTS + contingencias + markup."*

### 06 · CONTROL Y APROBACIÓN (filas 86-95)

| Celda | Label | Fórmula literal | Origen | Tipo |
|-------|-------|-----------------|--------|------|
| B87 | SCORE GENERAL DEL CLIENTE | `=Riesgo!E17` | Riesgo E17 | C |
| B90 | SCORE GENERAL OPERATIVO | `=Riesgo!E16` | Riesgo E16 | C |
| B92 | SCORE GENERAL DEL DEAL | `=Riesgo!E18` | Riesgo E18 | C |
| H87 | FACTURACIÓN MENSUAL PROYECTADA | `='Vision Cost To Serve'!C200/Panel!C9` | CTS C200 / Panel C9 | C |
| M91 | Estado: Gerencia Financiera (> COP 100 M Mes) | `=IF(H87>=100000000,"✓  Requerida","—  No aplica")` | self/H87 | C |
| M92 | Estado: Gerencia General (> COP 200 M Mes) | `=IF(H87>=200000000,"✓  Requerida","—  No aplica")` | self/H87 | C |
| M93 | Estado: Alta Dirección (> 1.000 SMLV Deal) | `=IF('Vision Cost To Serve'!C200>=1000000000,"✓  Requerida","—  No aplica")` | CTS C200 | C |
| P86:P95 | CRITERIO (10) | `=IFERROR(Riesgo!E3..E12,"-")` | Riesgo E3:E12 | C |
| U86:U95 | CATEGORÍA (10) | `=IFERROR(Riesgo!D3..D12,"-")` | Riesgo D3:D12 | C |
| W86:W95 | NIVEL (10) | `=Riesgo!N3..N12` | Riesgo N3:N12 | C |

### 07 · CONTINGENCIAS Y AJUSTES (filas 101-105) — APLICADO/MÍN/MÁX/ESTADO

| Fila | CONCEPTO | APLICADO | MÍN | MÁX | ESTADO (patrón) |
|------|----------|----------|-----|-----|-----------------|
| 101 | Margen objetivo | `Panel!C63` | `Panel!D63` | `Panel!E63` | `=IF(C63<D63,"⚠ Bajo mínimo",IF(C63>E63,"⚠ Excede máximo","✓ Dentro de rango"))` |
| 102 | Contingencia Operativa | `Panel!C67` | `Panel!D67` | `Panel!E67` | idem (C67/D67/E67) |
| 103 | Contingencia Comercial | `Panel!C68` | `Panel!D68` | `Panel!E68` | idem |
| 104 | Markup (complejidad/horarios) | `Panel!C69` | `Panel!D69` | `Panel!E69` | idem |
| 105 | Descuento por volumen | `Panel!C70` | `Panel!D70` | `Panel!E70` | idem |

### 08 · APROBACIONES (filas 110-117) — inputs libres (firmas)

| Celda | Label | Tipo |
|-------|-------|------|
| B110 | Nombre de quien elabora el pricing | I (libre) |
| I110 | Quien revisa (Director Senior Comercial) | I (libre) |
| Q110 | Quien revisa (Gerente de Desarrollo de Negocios) | I (libre) |
| H114 | Quien aprueba (Director de Pricing) | I (libre) |
| P114 | Quien aprueba (Gerente General) | I (libre) |

---

## FASE 3 — TRAZABILIDAD (Excel → hoja origen → resultado)

```
Visión Imprimible (presentación)
├── 01 Ficha       ← Panel de Control General (C5..C13, D6, L7, L8)
├── 02 Economics   ← Vision Tarifas (C72, C29)  +  Visión P&G (BK30, E6)  +  Vision CTS (C200)  +  Panel (C63, C11)
├── 03 Config      ← Vision Tarifas (C33, C34/D34, C35/D35, G47, G55)  +  Panel (C70, L52, C63)
├── 04 Gráficos    ← Visión P&G (series mensuales)  +  promedios waterfall
├── 05 Escenarios  ← Panel (B80..C113, bloques +7)  +  Vision Tarifas (C20:G21, C29)
├── 06 Riesgo/Aprob ← Riesgo (E16/E17/E18, E3:E12, D3:D12, N3:N12)  +  Vision CTS (C200)  +  Panel (C9)
├── 07 Contingencias ← Panel (C63..E70)
└── 08 Firmas      ← inputs libres (no calculados)
```

**Agregaciones / transformaciones detectadas:**
- **Concat + TEXT(%)**: `componente fijo/variable` (I36/P36, I74/M74) → `"FTE (70%)"`. La hoja **compone** label+%.
- **División**: facturación mensual proyectada `= CTS!C200 / Panel!C9` (valor total ÷ días de periodo de pago).
- **Reuso transversal**: `Panel!C63` (margen objetivo) aparece 3 veces (N19, T38, fila 101). `CTS!C200` aparece 3 veces (T19, H87, M93).
- **Score deal** `Riesgo!E18 = E17·0.4 + E16·0.6` — verificado numéricamente: `2.1·0.4 + 1.9·0.6 = 1.98` = B92 ✓.

---

## FASE 4 — COMPARACIÓN BACKEND

Backend relevante: `calculators/vision_imprimible.py` (`VisionImprimibleBuilder`),
`domain/models/visions.py` (dataclasses), `adapters/pricing_serializer.py` (contrato JSON),
`calculators/riesgo.py`. El JSON expuesto NO usa `VisionImprimible.ficha` para la ficha — el serializer
construye `ficha_deal` directamente desde `PanelDeControl` (`_ficha_deal_to_dict`).

| Sección · Campo Excel | Existe Backend | DTO/clave JSON | Lógica/Fuente backend | Estado |
|------------------------|----------------|----------------|------------------------|--------|
| **01** Cliente | Sí | `ficha_deal.cliente` | `panel.cliente` | Completo |
| **01** Servicio | Sí | `ficha_deal.linea_negocio` | `panel.linea_negocio` | Completo |
| **01** Ciudad/Sede | Sí | `ficha_deal.ciudad`,`.sede` | `panel.ciudad/sede` | Completo |
| **01** Tipo cliente (C8·C7) | Sí | `ficha_deal.tipo_cliente`,`.antiguedad_cliente` | `panel.*` | Completo |
| **01** Fecha inicio | Sí | `ficha_deal.fecha_inicio` | `panel.fecha_inicio` | Completo |
| **01** Duración | Sí | `ficha_deal.meses_contrato`/`duracion_contrato` | derivado | Completo |
| **01** Periodo de pago | Sí | `ficha_deal.periodo_pago_dias` | `panel.periodo_pago_dias` | Completo |
| **01** Ajuste de precio (L7·L8) | Sí | `ficha_deal.ajuste_precio_tipo`,`.ajuste_precio_frecuencia` | `panel.indexacion` | Completo |
| **00/06** Banner aprobación (S7) | **No** | — | — | **No existe** |
| **02** Ingreso mensual (Tarifas!C72) | Parcial | `kpis.ingreso_mensual` / `economics` | `vision_tarifas.ingreso_mensual` | **Parcial** (verificar = C72) |
| **02** CTS mensual (P&G!BK30/E6) | Parcial | `economics.cts_mensual` | `cost_to_serve.cts_ponderado` | **Parcial** (fórmula distinta, ver GAP-IMP-02) |
| **02** Margen del deal (Panel!C63) | Sí | `kpis`/`panel.margen` | `panel.margen` | Completo |
| **02** Estado margen (N20) | **No** | — | comparación con rango C63/D63/E63 | **No existe** |
| **02** Valor total contrato (CTS!C200) | Sí | `kpis.valor_total_deal` | `cost_to_serve` | **Parcial** (verificar = C200) |
| **03** Modelo de cobro | Sí | `configuracion_comercial.modelo_cobro_principal` | canal principal | Completo |
| **03** Componente fijo (label+%) | Parcial | `pct_fijo_global` (float) | — | **Parcial** (sin label compuesto ni `tipo`) |
| **03** Componente variable (label+%) | Parcial | `pct_variable_global` (float) | — | **Parcial** |
| **03** Tarifa fija (Tarifas!G47) | Sí | `configuracion_comercial.tarifa_fija` | canal principal | **Parcial** (verificar = G47) |
| **03** Tarifa variable (Tarifas!G55) | Sí | `configuracion_comercial.tarifa_variable` | canal principal | **Parcial** (verificar = G55) |
| **03** Descuento (Panel!C70) | Sí | `configuracion_comercial.descuento` | `panel.descuento` | Completo |
| **03** Volumen base/mes (Panel!L52) | Parcial | `volumen_base_mensual` | `cost_to_serve.vol_cadena_b` | **Parcial** (fuente distinta a L52) |
| **03** Margen objetivo (Panel!C63) | Sí | `configuracion_comercial.margen_objetivo` | `panel.margen` | Completo |
| **04** Waterfall | Sí | `waterfall_promedio` | `WaterfallPromedio` | Completo |
| **04** Evolución mensual | Sí | `pyg_por_mes` / `EvolucionMensual` | `pyg_por_mes` | Completo |
| **05** Escenario/Modalidad/Modelo | Sí | `comparativo_escenarios[]` | `EscenarioComercial` | Completo |
| **05** Comp. fijo/variable por escenario | Parcial | `escenarios[].componente_*` | `EscenarioComercial` | **Parcial** (no en `ComparativoEscenario`) |
| **05** Tarifa fija/variable por escenario (Tarifas!C20:G21) | **No** | — | — | **No existe** |
| **05** Estado ★ SELECCIONADO (vs Tarifas!C29) | **No** | — | — | **No existe** |
| **06** Score cliente/operativo/deal | Sí | `evaluacion_riesgo.score_cliente/operativo/total` | `RiesgoCalculator` | Completo |
| **06** 10 criterios (E/D/N) | Sí | `evaluacion_riesgo.criterios[]` | `CriterioRiesgo` | Completo |
| **06** Facturación mensual proyectada (CTS!C200/C9) | Parcial | `kpis.facturacion_mensual_proyectada` | calculador | **Parcial** (verificar fórmula = C200/C9) |
| **06** 3 umbrales de aprobación (M91/M92/M93) | Parcial | `evaluacion_riesgo.requiere_aprobacion` (bool único) | umbral 1000·SMMLV | **Parcial** (ver GAP-IMP-04) |
| **07** Contingencias (5× aplicado/mín/máx/estado) | Sí | `reglas_negocio[]` (`ReglaNegocios`) | Panel C63..E70 | Completo |
| **08** Firmas (5 campos libres) | **No** | — | — | **No existe** |

---

## FASE 5 — GAPS

| ID | Tipo | Descripción | Severidad |
|----|------|-------------|-----------|
| **GAP-IMP-01** | Campo no expuesto | **Comparativo de escenarios incompleto**. Excel filas 74-78 exponen 8 columnas (incl. Tarifa Fija `Tarifas!C20:G20`, Tarifa Variable `C21:G21`, ESTADO ★ SELECCIONADO). El backend `ComparativoEscenario` solo tiene `escenario`, `modalidad_canal`, `modelo_cobro`. **Faltan**: `componente_fijo`, `componente_variable`, `tarifa_fija`, `tarifa_variable`, `estado`. | Alta |
| **GAP-IMP-02** | Inconsistencia fórmula | **CTS mensual**. Excel H19 = `P&G!BK30 / P&G!E6` (acumulado costo total ÷ meses). Backend usa `cost_to_serve.cts_ponderado`. Equivalencia **no verificada** numéricamente. | Media |
| **GAP-IMP-03** | Campo no expuesto | **Estado de margen (N20)** y **banner de aprobación (S7)**: textos de estado derivados que el Excel calcula y muestra. Backend no los expone como strings listos. | Media |
| **GAP-IMP-04** | Inconsistencia regla | **Matriz de aprobación de 3 niveles**. Excel: Gerencia Financiera (`fact_mensual ≥ 100M`), Gerencia General (`fact_mensual ≥ 200M`), Alta Dirección (`deal ≥ 1.000.000.000 COP fijo`). Backend solo tiene `requiere_aprobacion: bool` con umbral `1000 · SMMLV` (≈1.4B, ≠ 1.0B fijo del Excel M93). Falta el desglose por nivel y los 2 umbrales por facturación mensual. | Alta |
| **GAP-IMP-05** | Campo no expuesto | **Componente fijo/variable como label compuesto** (`"FTE (70%)"`). Excel concatena `tipo & " (" & pct% & ")"`. Backend expone solo `pct_fijo_global` (float), sin el `tipo` ni el string compuesto. (Composición posible en frontend, pero falta `tipo`.) | Baja |
| **GAP-IMP-06** | Campo no expuesto | **Volumen base/mes** Excel N38 = `Panel!L52`. Backend `volumen_base_mensual = cost_to_serve.vol_cadena_b`. Fuente distinta — verificar paridad o exponer `Panel!L52`. | Media |
| **GAP-IMP-07** | Campo no expuesto | **Sección 08 — Firmas** (5 campos: elabora / 2 revisan / 2 aprueban). No existe en el contrato. Son inputs libres del documento; requieren campos de captura. | Baja |
| **GAP-IMP-08** | Verificación pendiente | **Paridad de valores escalares 02/03**: `Ingreso mensual = Tarifas!C72`, `Tarifa fija = Tarifas!G47`, `Tarifa variable = Tarifas!G55`, `Valor total = CTS!C200`, `Fact. mensual = CTS!C200/Panel!C9`. Confirmados como fuentes correctas; falta test de paridad numérica contra el oracle. | Media |
| **GAP-IMP-09** | Nomenclatura | `VisionImprimible.ficha` (FichaDelDeal, 4 campos) está **muerto/divergente**: el serializer construye `ficha_deal` desde Panel con ~25 campos, ignorando el dataclass. Limpiar o reconciliar. | Baja |

**Duplicaciones detectadas (sanas, no recalculan):** `Panel!C63` (margen) y `CTS!C200` (valor total) se reusan
varias veces dentro de la hoja; el backend ya los centraliza en `panel.margen` / `kpis.valor_total_deal`.

---

## FASE 6 — REUTILIZACIÓN

| Campo VI | Reutilizable | Exclusivo VI | Fuente backend canónica |
|----------|--------------|--------------|--------------------------|
| Ingreso mensual / Tarifa fija/variable | ✅ Reutilizable | — | `vision_tarifas` (Vision Tarifas_Modelo_Cobro) |
| CTS mensual / Valor total | ✅ Reutilizable | — | `cost_to_serve` (Vision Cost To Serve) |
| Evolución mensual / Waterfall | ✅ Reutilizable | — | `pyg_por_mes` (Visión P&G) |
| Margen / Contingencias / rangos | ✅ Reutilizable | — | `panel` + `reglas_negocio` |
| Scores y 10 criterios de riesgo | ✅ Reutilizable | — | `evaluacion_riesgo` (`RiesgoCalculator`) |
| Comparativo escenarios (modelo/canal) | ✅ Reutilizable | — | `escenarios` (`EscenarioComercial`) |
| Tarifa por escenario (Tarifas!C20:G21) | ✅ Reutilizable | — | `vision_tarifas` (matriz de escenarios) |
| Banner aprobación (S7) / Estado margen (N20) | ❌ | ✅ **Exclusivo VI** | derivar en builder (composición de strings) |
| Matriz 3 niveles de aprobación | ❌ | ✅ **Exclusivo VI** | nueva lógica de composición sobre `kpis`/`cost_to_serve` |
| Firmas (sección 08) | ❌ | ✅ **Exclusivo VI** | inputs libres — captura UI |

**Conclusión FASE 6:** ~85% de los datos ya existen y son reutilizables sin recálculo. Lo exclusivo de la VI
son **strings de estado derivados** (banner, estado margen, matriz de aprobación) que deben **componerse**
(no calcularse económicamente) en el builder, más los **campos de firma** (captura).

---

## FASE 7 — DISEÑO (solo campos con trazabilidad 100%)

> Principio: el builder **compone**, no recalcula. Solo se añaden campos con celda+fórmula verificada arriba.

### DTOs a extender (sin duplicación)

**`ComparativoEscenario`** (cerrar GAP-IMP-01) — añadir campos provenientes de fuentes ya calculadas:
```python
@dataclass
class ComparativoEscenario:
    escenario: str
    modalidad_canal: str
    modelo_cobro: str
    componente_fijo: str = "-"      # Excel I74: tipo + " (pct%)"  ← EscenarioComercial
    componente_variable: str = "-"  # Excel M74                    ← EscenarioComercial
    tarifa_fija: float = 0.0        # Excel Q74: Tarifas!C20:G20   ← vision_tarifas (matriz esc.)
    tarifa_variable: float = 0.0    # Excel T74: Tarifas!C21:G21   ← vision_tarifas
    estado: str = "Alternativa"     # Excel W74: "★ SELECCIONADO" si == Tarifas!C29
```

**`EconomicsDeal`** (cerrar GAP-IMP-03) — añadir estado de margen y banner:
```python
    estado_margen: str = ""          # Excel N20 (IFS sobre rango margen)
    valor_total_contrato: float = 0.0 # Excel T19 = CTS!C200 (renombrar/alias de valor_total_deal)
```

**Nuevo `AprobacionDeal`** (cerrar GAP-IMP-04) — matriz de 3 niveles + banner:
```python
@dataclass
class NivelAprobacion:
    nivel: str          # "Gerencia Financiera" | "Gerencia General" | "Alta Dirección"
    umbral_label: str   # "> COP 100 M Mes" | "> COP 200 M Mes" | "> 1.000 SMLV Deal"
    requerida: bool     # M91/M92/M93
@dataclass
class AprobacionDeal:
    facturacion_mensual_proyectada: float  # H87 = CTS!C200 / Panel!C9
    niveles: List[NivelAprobacion]
    banner: str         # S7: "No requiere aprobación" | "El deal requiere aprobación…"
```

**Nuevo `FirmasDeal`** (cerrar GAP-IMP-07) — captura UI (inputs libres, default ""):
```python
@dataclass
class FirmasDeal:
    elabora: str = ""
    revisa_director_senior_comercial: str = ""
    revisa_gerente_desarrollo_negocios: str = ""
    aprueba_director_pricing: str = ""
    aprueba_gerente_general: str = ""
```

### Servicios / Builders / Adaptadores
- **Builder**: extender `VisionImprimibleBuilder._construir_comparativo` para poblar tarifas por escenario
  desde la matriz `vision_tarifas` (cols C20:G21) y el flag SELECCIONADO (== escenario activo `Tarifas!C29`).
- **Builder**: nuevo `_construir_aprobacion(kpis, cost_to_serve, panel)` que compone los 3 niveles y el banner
  con los umbrales **literales del Excel** (100M, 200M, 1.000.000.000 COP fijo — NO `1000·SMMLV`).
- **Builder**: `_construir_economics` añade `estado_margen` (IFS sobre `panel.margen` vs `panel` D63/E63).
- **Adaptador/serializer**: emitir `comparativo_escenarios` enriquecido, `aprobacion`, `firmas`, `estado_margen`;
  reconciliar/eliminar el dataclass muerto `FichaDelDeal` (GAP-IMP-09).
- **Tests de paridad** (cerrar GAP-IMP-02 / GAP-IMP-08): oracle contra V2-7 para C72/G47/G55/C200/BK30÷E6.

---

## FASE 8 — PLAN DE EJECUCIÓN

| Fase | Alcance | Gaps que cierra | Dependencias |
|------|---------|------------------|--------------|
| **A — Ficha del Deal** | ✅ Ya completo. Solo reconciliar dataclass muerto. | GAP-IMP-09 | — |
| **B — Economics** | Añadir `estado_margen` (N20) + alias `valor_total_contrato`; test paridad C72/C200/BK30÷E6. | GAP-IMP-02, 03, 08 | Oracle V2-7 |
| **C — Gráficos (solo data)** | ✅ Ya completo (`waterfall_promedio` + `pyg_por_mes`). Verificar series. | — | — |
| **D — Escenarios** | Enriquecer `ComparativoEscenario` con tarifa fija/variable por escenario + estado SELECCIONADO. | GAP-IMP-01, 05 | matriz `vision_tarifas` C20:G21 |
| **E — Contingencias** | ✅ Ya completo (`reglas_negocio`). Verificar 5 conceptos vs C63..E70. | — | — |
| **F — Aprobaciones** | Nuevo `AprobacionDeal` (3 niveles + banner S7) con umbrales literales; nuevo `FirmasDeal`. | GAP-IMP-04, 07 | `kpis.facturacion_mensual_proyectada` = CTS!C200/C9 |

**Orden recomendado:** B → D → F (gaps de mayor severidad: comparativo de escenarios y matriz de aprobación),
luego A/C/E (verificación + limpieza). Toda fase debe acompañarse de un test de paridad contra el oracle V2-7,
sin hardcodes y con la celda Excel citada en el `formula`/docstring.

---

## GRÁFICOS (solo data, no render)

### 04.01 · WATERFALL — componentes promedio del deal
```ts
interface ChartData { labels: string[]; series: number[] }
```
- **labels** (orden Excel): `["Payroll A", "No Payroll A", "Costo B", "Costo C", "Financiación", "Pólizas", "ICA", "GMF", "Ingreso Bruto", "Contingencias", "Markup/Desc.", "Ingreso Neto"]`
- **series**: campos de `WaterfallPromedio` (`payroll_a, no_payroll_a, costo_b, costo_c, financiacion, polizas, ica, gmf, ingreso_bruto, contingencias, markup_descuento, ingreso_neto`).
- **Rango origen**: promedios del deal (`Visión P&G` mensual agregada).

### 04.02 · EVOLUCIÓN MENSUAL — Ingreso Neto proyectado
- **labels**: meses del contrato `EvolucionMensual.meses` → `["Mes 1", … , "Mes N"]`.
- **series**: `EvolucionMensual.ingresos_neto` (principal). Series adicionales disponibles: `costos_total`, `contribucion`, `margen_mensual`.
- **Rango origen**: `Visión P&G` columnas C:BJ por fila.

> No se replican imágenes. El backend ya expone `waterfall_promedio` y `pyg_por_mes`/`EvolucionMensual` — el
> frontend arma el render. Solo falta normalizar `labels` (orden literal del Excel).

---

## RESUMEN EJECUTIVO

- La hoja es **100% presentación** (cero fórmulas propias de cálculo) → el backend **no debe recalcular**.
- **~85%** de los datos ya están expuestos en el contrato JSON (`pricing_result_to_dict`).
- **9 gaps**; los 2 de severidad **Alta**: comparativo de escenarios incompleto (GAP-IMP-01) y matriz de
  aprobación de 3 niveles ausente con umbral divergente (GAP-IMP-04).
- Trazabilidad **100% verificada** con celda + fórmula literal para cada campo calculado (FASE 2).
- Diseño propuesto: extender 2 DTOs + 2 DTOs nuevos, todo por **composición** sobre resultados certificados.
