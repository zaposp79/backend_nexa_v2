# Excel V2-7 → V2-8 Diff (Stage 1)
**Generado:** 2026-06-10T21:09:00.880622+00:00
**V2-7:** `excel/Nexa - Pricing - Simulador - V2-7.xlsx` (sha256 `5fb7174f998356c1…`, drift gate PASS)
**V2-8:** `excel/Nexa - Pricing - Simulador - V2-8.xlsx`

## Conjuntos de hojas
- **SHEETS_BOTH** (23): Condiciones Cadena A, Condiciones Cadena B, Condiciones Cadena C, Costo Cadena C, Costo Fijo, Costo Variable, Costos Totales, Graficos, Hoja Maestra Escenarios, Inputs de Nomina, Listas Desplegables, No payroll, Nomina Loaded, Panel de Control General, Pólizas - Costo Financiacion, Riesgo, Rot, Ausent y Rentabilidad, Tasas, TRM, Polizas, Vision Cost To Serve, Vision Tarifas_Modelo_Cobro, Visiones, Visión Imprimible, Visión P&G
- **SHEETS_ONLY_V28** (0): — → candidatos **MISSING_IN_BACKEND**
- **SHEETS_ONLY_V27** (0): — → **requiere decisión humana**

## Metodología de clasificación

Ambos workbooks llevan un deal de ejemplo distinto cargado, por lo que
comparar valores cacheados es ruido. El delta de **lógica** vive en la
fórmula. Además, V2-8 insertó/eliminó filas en varias hojas, lo que
**retarget**ea referencias absolutas (`'Hoja'!$A$51`→`$A$53`) sin
cambiar la lógica. Para aislar la señal real se usa el **skeleton** de
la fórmula (toda referencia enmascarada a `@`):

- **PARITY CANDIDATES** (lógica real, accionables en Stage 2):
  - `FORMULA_LOGIC_CHANGED` — skeleton distinto (cambió funciones/
    operadores/estructura, no solo a qué celda apunta).
  - `CONSTANT_CHANGED` — literal numérico hardcodeado cambió.
- **Ruido de shift de layout** (NO candidatos; validar vía parity
  runner contra valores cacheados V2-8):
  - `REFERENCE_RETARGET` — misma skeleton, distinta celda destino.
  - `FORMULA_ADDED` / `FORMULA_REMOVED` — fórmula aparece/desaparece
    en una coordenada por desplazamiento de bloque.
  - `DATA_STRUCTURAL` / `LABEL_CHANGED` / `VALUE_ONLY` (excluido).

> **Limitación conocida:** un diff por coordenada no puede separar con
> 100% de certeza un FORMULA_ADDED/REMOVED real de uno por shift sin
> alinear filas hoja-por-hoja. Por eso las hojas-motor de grilla grande
> (`Nomina Loaded`, `Costo Cadena C`, `Costo Fijo`, `Pólizas - Costo
> Financiacion`) se validan numéricamente vía runner, no por este diff.

## Resumen de PARITY CANDIDATES por hoja (lógica real)

| Hoja | Tipo | FORMULA_LOGIC_CHANGED | CONSTANT_CHANGED | Parity total | Ruido shift |
|------|------|----------------------:|-----------------:|-------------:|------------:|
| Condiciones Cadena A | motor | 95 | 5 | 100 | 2141 |
| Condiciones Cadena B | motor | 0 | 3 | 3 | 29 |
| Condiciones Cadena C | motor | 22 | 25 | 47 | 75 |
| Costo Cadena C | motor | 4126 | 73 | 4199 | 10635 |
| Costo Fijo | motor | 1808 | 138 | 1946 | 6292 |
| Costo Variable | motor | 15 | 31 | 46 | 18 |
| Costos Totales | motor | 1440 | 73 | 1513 | 0 |
| Graficos | vista | 24 | 13 | 37 | 1030 |
| Hoja Maestra Escenarios | motor | 37 | 59 | 96 | 136 |
| Inputs de Nomina | motor | 543 | 20 | 563 | 3613 |
| Listas Desplegables | motor | 119 | 0 | 119 | 242 |
| No payroll | motor | 0 | 29 | 29 | 2776 |
| Nomina Loaded | motor | 4057 | 85 | 4142 | 21001 |
| Panel de Control General | motor | 0 | 33 | 33 | 144 |
| Pólizas - Costo Financiacion | motor | 5400 | 486 | 5886 | 3 |
| Riesgo | motor | 1 | 4 | 5 | 4 |
| Rot, Ausent y Rentabilidad | motor | 0 | 2 | 2 | 0 |
| Tasas, TRM, Polizas | motor | 5 | 0 | 5 | 40 |
| Vision Cost To Serve | vista | 16 | 48 | 64 | 221 |
| Vision Tarifas_Modelo_Cobro | vista | 29 | 31 | 60 | 136 |
| Visión Imprimible | vista | 1 | 0 | 1 | 183 |
| Visión P&G | vista | 420 | 495 | 915 | 62 |

## Changeset accionable: 177 transiciones de fórmula distintas

Cada transición = un patrón de fórmula que cambió (skeleton V2-7 →
skeleton V2-8), con cuántas celdas la repiten y una celda de ejemplo.
Esta es la lista de trabajo real para Stage 2.

### Condiciones Cadena A (motor) — 5 transiciones distintas

- **G84** ×65 celdas
  - V2-7: `=IF(G$83<>"",E$19,0)`
  - V2-8: `=IF($C84=TRUE,IF(OR($D84=$D$90,$D84=$D$91),((G$9+G$26+G$30+G$34)/G111)*'Panel de Control General'!$C$20,((G$9+G$26+G$30+G$34)/G111)),0)`
- **E29** ×15 celdas
  - V2-7: `=IF(AND($D29=$D$35,$B$35=8,$C$35=TRUE,E$16<>""),200,IF(AND($C29=TRUE,E$16<>""),INDEX('Inputs de Nomina'!$C$110:$H$133,MATCH($D29,'Inputs de Nomina'!$B$110:$B$13`
  - V2-8: `=IF(E28<>"",'Inputs de Nomina'!$C$4,0)`
- **G87** ×13 celdas
  - V2-7: `=(((($E$118*$E$119*(1-$E$120)*E17)*60)*50%)*2%)`
  - V2-8: `=IF($C87=TRUE,IF(OR($D87=$D$90,$D87=$D$91),((G$9+G$26+G$30+G$34)/G114)*'Panel de Control General'!$C$20,((G$9+G$26+G$30+G$34)/G114)),0)`
- **G95** ×1 celdas
  - V2-7: `=SUM(W41:W43)`
  - V2-8: `=IF($C95=TRUE,IF(OR($D95=$D$90,$D95=$D$91),((G$9+G$26+G$30+G$34)/G122)*'Panel de Control General'!$C$20,((G$9+G$26+G$30+G$34)/G122)),0)`
- **E120** ×1 celdas
  - V2-7: `='Panel de Control General'!C19`
  - V2-8: `=IF(AND($D120=$D$114,$B$87=8,$C$87=TRUE,E$8<>""),200,INDEX('Inputs de Nomina'!$C$179:$H$202,MATCH($D120,'Inputs de Nomina'!$B$179:$B$202,0),MATCH('Panel de Cont`

### Condiciones Cadena C (motor) — 1 transiciones distintas

- **J62** ×22 celdas
  - V2-7: `=IF(E62="Total",G62,G62*H62)`
  - V2-8: `=IFERROR((I62/H62)*(1+'Panel de Control General'!$L$11),0)`

### Costo Cadena C (motor) — 41 transiciones distintas

- **E273** ×899 celdas
  - V2-7: `=E$271*$D273`
  - V2-8: `=IF(AND(E$159>=$D$3,$D$4>=E$159),$D273,0)*(IF(MONTH(E$160)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
- **H366** ×580 celdas
  - V2-7: `=IF(AND(H$364>=$D$3,$D$4>=H$364),$E366,0)*(IF(MONTH(H$365)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$5,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
  - V2-8: `=IF(AND(H$362>=$D$3,$D$4>=H$362),$G366*$F366,0)*(IF(MONTH(H$363)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MAT`
- **K248** ×378 celdas
  - V2-7: `=IFERROR(IF(AND(K$232>='Nomina Loaded'!$C$3,K$232<=($I248+'Nomina Loaded'!$C$3-1),K$232<=$D$3+'Panel de Control General'!$C$11-1),$J248,0),0)`
  - V2-8: `=IF(AND(K$134>=$D$3,$D$4>=K$134),$D248,0)*(IF(MONTH(K$135)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
- **F307** ×290 celdas
  - V2-7: `=SUMIFS(M$234:M$262,$E$234:$E$262,$C307,$D$234:$D$262,$C$306)+IFERROR(G295,0)`
  - V2-8: `=E$298*$D307`
- **H403** ×290 celdas
  - V2-7: `=IF(AND(H$396>=$D$3,$D$4>=H$396),$G403*$F403,0)*(IF(MONTH(H$397)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MAT`
  - V2-8: `=G$396*$D403`
- **F272** ×177 celdas
  - V2-7: `=F$271*$D272`
  - V2-8: `=EDATE(E272,1)`
- **E298** ×120 celdas
  - V2-7: `=E$294*$D298`
  - V2-8: `=(F$346+E$354)*$D298`
- **F332** ×118 celdas
  - V2-7: `=(G$380+F$388)*$D332`
  - V2-8: `=IF(AND(F$330>=$D$3,$D$4>=F$330),$E332,0)*(IF(MONTH(F$331)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$5,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
- **G338** ×118 celdas
  - V2-7: `=EDATE(F338,1)`
  - V2-8: `=IF(AND(G$330>=$D$3,$D$4>=G$330),$E338,0)*(IF(MONTH(G$331)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$5,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
- **F380** ×117 celdas
  - V2-7: `=SUM(F366:F379)`
  - V2-8: `=D380*E380`
- **G315** ×116 celdas
  - V2-7: `=SUM(G307:G314)`
  - V2-8: `=EDATE(F315,1)`
- **H402** ×116 celdas
  - V2-7: `=IF(AND(H$396>=$D$3,$D$4>=H$396),$G402*$F402,0)*(IF(MONTH(H$397)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MAT`
  - V2-8: `=EDATE(G402,1)`
- **F306** ×115 celdas
  - V2-7: `=EDATE(E306,1)`
  - V2-8: `=E$298*$D306`
- **F410** ×61 celdas
  - V2-7: `=D410*E410`
  - V2-8: `=SUM(F403:F409)`
- **F312** ×58 celdas
  - V2-7: `=SUMIFS(M$234:M$262,$E$234:$E$262,$C312,$D$234:$D$262,$C$306)+IFERROR(G300,0)`
  - V2-8: `=SUM(F305:F311)`
- **H365** ×58 celdas
  - V2-7: `=EDATE(G365,1)`
  - V2-8: `=IF(AND(H$362>=$D$3,$D$4>=H$362),$G365*$F365,0)*(IF(MONTH(H$363)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MAT`
- **H371** ×58 celdas
  - V2-7: `=IF(AND(H$364>=$D$3,$D$4>=H$364),$E371,0)*(IF(MONTH(H$365)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$5,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
  - V2-8: `=SUM(H364:H370)`
- **H380** ×58 celdas
  - V2-7: `=SUM(H366:H379)`
  - V2-8: `=IF(AND(H$373>=$D$3,$D$4>=H$373),$G380*$F380,0)*(IF(MONTH(H$374)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MAT`
- **H410** ×58 celdas
  - V2-7: `=IF(AND(H$407>=$D$3,$D$4>=H$407),$G410*$F410,0)*(IF(MONTH(H$408)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MAT`
  - V2-8: `=SUM(H403:H409)`
- **G431** ×58 celdas
  - V2-7: `=(H$472+G$479)*$D431`
  - V2-8: `=EDATE(F431,1)`
- **I374** ×57 celdas
  - V2-7: `=IF(AND(I$364>=$D$3,$D$4>=I$364),$E374,0)*(IF(MONTH(I$365)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$5,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
  - V2-8: `=EDATE(H374,1)`
- **I397** ×56 celdas
  - V2-7: `=EDATE(H397,1)`
  - V2-8: `=(J$438+I$445)*$D397`
- **K247** ×54 celdas
  - V2-7: `=IFERROR(IF(AND(K$232>='Nomina Loaded'!$C$3,K$232<=($I247+'Nomina Loaded'!$C$3-1),K$232<=$D$3+'Panel de Control General'!$C$11-1),$J247,0),0)`
  - V2-8: `=EDATE(J247,1)`
- **K255** ×54 celdas
  - V2-7: `=IFERROR(IF(AND(K$232>='Nomina Loaded'!$C$3,K$232<=($I255+'Nomina Loaded'!$C$3-1),K$232<=$D$3+'Panel de Control General'!$C$11-1),$J255,0),0)`
  - V2-8: `=SUM(K248:K254)`
- **F366** ×10 celdas
  - V2-7: `=IF(AND(F$364>=$D$3,$D$4>=F$364),$E366,0)*(IF(MONTH(F$365)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$5,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
  - V2-8: `=D366*E366`
- **G366** ×10 celdas
  - V2-7: `=IF(AND(G$364>=$D$3,$D$4>=G$364),$E366,0)*(IF(MONTH(G$365)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$5,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
  - V2-8: `=IF(ISNUMBER('Condiciones Cadena C'!D127)=TRUE,'Condiciones Cadena C'!D127,0)`
- **E339** ×7 celdas
  - V2-7: `=INDEX($F339:$BM339,MATCH('Nomina Loaded'!$C$3,$F$337:$BM$337,0))/IF(MONTH('Panel de Control General'!$C$10)>='Panel de Control General'!$L$9,INDEX('Tasas, TRM,`
  - V2-8: `=IFERROR(D339*INDEX('Inputs de Nomina'!$AK$158:$AK$171,MATCH($C339,'Inputs de Nomina'!$B$158:$B$171,0)),0)`
- **E307** ×5 celdas
  - V2-7: `=SUMIFS(L$234:L$262,$E$234:$E$262,$C307,$D$234:$D$262,$C$306)+IFERROR(F295,0)`
  - V2-8: `=INDEX($F307:$BM307,MATCH('Nomina Loaded'!$C$3,$F$303:$BM$303,0))/IF(MONTH('Panel de Control General'!$C$10)>='Panel de Control General'!$L$10,INDEX('Tasas, TRM`
- **E366** ×5 celdas
  - V2-7: `=IFERROR(D366*INDEX('Inputs de Nomina'!$AK$89:$AK$102,MATCH($C366,'Inputs de Nomina'!$B$89:$B$102,0)),0)`
  - V2-8: `=INDEX('Condiciones Cadena C'!$C$125:$C$131,MATCH(C366,'Condiciones Cadena C'!$B$125:$B$131,0))`
- **E375** ×5 celdas
  - V2-7: `=IFERROR(D375*INDEX('Inputs de Nomina'!$AK$89:$AK$102,MATCH($C375,'Inputs de Nomina'!$B$89:$B$102,0)),0)`
  - V2-8: `=INDEX('Condiciones Cadena C'!$C$134:$C$141,MATCH(C375,_xlfn.ANCHORARRAY('Condiciones Cadena C'!$B$134),0))`
- **G403** ×5 celdas
  - V2-7: `=IF('Condiciones Cadena C'!$F$122="Input Calculado",'Vision Cost To Serve'!$C$98,'Condiciones Cadena C'!$G$122)`
  - V2-8: `=F$396*$D403`
- **E409** ×3 celdas
  - V2-7: `=INDEX('Condiciones Cadena C'!$C$132:$C$139,MATCH(C409,_xlfn.ANCHORARRAY('Condiciones Cadena C'!$B$132),0))`
  - V2-8: `=INDEX($F409:$BM409,MATCH('Nomina Loaded'!$C$3,$F$401:$BM$401,0))/IF(MONTH('Panel de Control General'!$C$10)>='Panel de Control General'!$L$10,INDEX('Tasas, TRM`
- **E332** ×2 celdas
  - V2-7: `=(F$380+E$388)*$D332`
  - V2-8: `=IFERROR(D332*INDEX('Inputs de Nomina'!$AK$158:$AK$171,MATCH($C332,'Inputs de Nomina'!$B$158:$B$171,0)),0)`
- **G402** ×2 celdas
  - V2-7: `=IF('Condiciones Cadena C'!$F$122="Input Calculado",'Vision Cost To Serve'!$C$98,'Condiciones Cadena C'!$G$122)`
  - V2-8: `=EDATE(F402,1)`
- **E403** ×2 celdas
  - V2-7: `=INDEX('Condiciones Cadena C'!$C$123:$C$129,MATCH(C403,'Condiciones Cadena C'!$B$123:$B$129,0))`
  - V2-8: `=INDEX($F403:$BM403,MATCH('Nomina Loaded'!$C$3,$F$401:$BM$401,0))/IF(MONTH('Panel de Control General'!$C$10)>='Panel de Control General'!$L$10,INDEX('Tasas, TRM`
- **E306** ×1 celdas
  - V2-7: `=EDATE(D306,1)`
  - V2-8: `=INDEX($F306:$BM306,MATCH('Nomina Loaded'!$C$3,$F$303:$BM$303,0))/IF(MONTH('Panel de Control General'!$C$10)>='Panel de Control General'!$L$10,INDEX('Tasas, TRM`
- **E354** ×1 celdas
  - V2-7: `=INDEX($F354:$BM354,MATCH('Nomina Loaded'!$C$3,$F$348:$BM$348,0))/IF(MONTH('Panel de Control General'!$C$10)>='Panel de Control General'!$L$9,INDEX('Tasas, TRM,`
  - V2-8: `=IF(AND(E$352>=$D$3,$D$4>=E$352),$D354,0)*(IF(MONTH(E$353)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
- **G365** ×1 celdas
  - V2-7: `=EDATE(F365,1)`
  - V2-8: `=IF(ISNUMBER('Condiciones Cadena C'!D126)=TRUE,'Condiciones Cadena C'!D126,0)`
- **G380** ×1 celdas
  - V2-7: `=SUM(G366:G379)`
  - V2-8: `=IF(ISNUMBER('Condiciones Cadena C'!D139)=TRUE,'Condiciones Cadena C'!D139,0)`
- **G410** ×1 celdas
  - V2-7: `=IF('Condiciones Cadena C'!$F$131="Input Calculado",'Vision Cost To Serve'!$C$98,'Condiciones Cadena C'!$G$131)`
  - V2-8: `=SUM(G403:G409)`
- **E437** ×1 celdas
  - V2-7: `=INDEX($F437:$BM437,MATCH('Nomina Loaded'!$C$3,$F$435:$BM$435,0))/IF(MONTH('Panel de Control General'!$C$10)>='Panel de Control General'!$L$9,INDEX('Tasas, TRM,`
  - V2-8: `=D437*IFERROR(INDEX('Inputs de Nomina'!$AK$146:$AK$151,MATCH($C437,'Inputs de Nomina'!$B$146:$B$151,0)),0)`

### Costo Fijo (motor) — 22 transiciones distintas

- **K110** ×378 celdas
  - V2-7: `=IFERROR(IF(AND(K$93>='Nomina Loaded'!$C$3,K$93<=($I110+'Nomina Loaded'!$C$3-1),K$93<=$D$3+'Panel de Control General'!$C$11-1),$J110,0),0)`
  - V2-8: `=IFERROR(IF(AND(K$108>=$D$3,$D$4>=K$108),$D110,0),0)*(IF(MONTH(K$109)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0`
- **E134** ×360 celdas
  - V2-7: `=E$132*$D134`
  - V2-8: `=IFERROR(IF(AND(E$108>=$D$3,$D$4>=E$108),$D134,0),0)*(IF(MONTH(E$109)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0`
- **F172** ×232 celdas
  - V2-7: `=SUMIFS(M$95:M$123,$E$95:$E$123,$C172,$D$95:$D$123,$C$167)+IFERROR(G160,0)`
  - V2-8: `=E$156*$D172`
- **E157** ×120 celdas
  - V2-7: `=E$155*$D157`
  - V2-8: `=SUM(E155:E156)`
- **F133** ×117 celdas
  - V2-7: `=F$132*$D133`
  - V2-8: `=EDATE(E133,1)`
- **F189** ×70 celdas
  - V2-7: `=(G$233+F$240)*$D189`
  - V2-8: `=IF(AND(F$185>=$D$3,$D$4>=F$185),$E189,0)*(IF(MONTH(F$186)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$5,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
- **E155** ×60 celdas
  - V2-7: `=SUMIFS(K$95:K$123,$E$95:$E$123,$C155,$D$95:$D$123,$C$154)`
  - V2-8: `=(F$199+E$206)*$D155`
- **E156** ×60 celdas
  - V2-7: `=E$155*$D156`
  - V2-8: `=(F$199+E$206)*$D156`
- **F188** ×59 celdas
  - V2-7: `=EDATE(E188,1)`
  - V2-8: `=IF(AND(F$185>=$D$3,$D$4>=F$185),$E188,0)*(IF(MONTH(F$186)>=$D$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($D$5,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
- **F167** ×58 celdas
  - V2-7: `=EDATE(E167,1)`
  - V2-8: `=E$155*$D167`
- **F168** ×58 celdas
  - V2-7: `=SUMIFS(M$95:M$123,$E$95:$E$123,$C168,$D$95:$D$123,$C$167)+IFERROR(G156,0)`
  - V2-8: `=SUM(F161:F167)`
- **F176** ×58 celdas
  - V2-7: `=SUM(F168:F175)`
  - V2-8: `=E$156*$D176`
- **G171** ×57 celdas
  - V2-7: `=SUMIFS(N$95:N$123,$E$95:$E$123,$C171,$D$95:$D$123,$C$167)+IFERROR(H159,0)`
  - V2-8: `=EDATE(F171,1)`
- **K109** ×54 celdas
  - V2-7: `=IFERROR(IF(AND(K$93>='Nomina Loaded'!$C$3,K$93<=($I109+'Nomina Loaded'!$C$3-1),K$93<=$D$3+'Panel de Control General'!$C$11-1),$J109,0),0)`
  - V2-8: `=EDATE(J109,1)`
- **K117** ×54 celdas
  - V2-7: `=IFERROR(IF(AND(K$93>='Nomina Loaded'!$C$3,K$93<=($I117+'Nomina Loaded'!$C$3-1),K$93<=$D$3+'Panel de Control General'!$C$11-1),$J117,0),0)`
  - V2-8: `=SUM(K110:K116)`
- **E172** ×4 celdas
  - V2-7: `=SUMIFS(L$95:L$123,$E$95:$E$123,$C172,$D$95:$D$123,$C$167)+IFERROR(F160,0)`
  - V2-8: `=INDEX($F172:$BM172,MATCH('Nomina Loaded'!$C$3,$F$170:$BM$170,0))/IF(MONTH('Panel de Control General'!$C$10)>='Panel de Control General'!$L$10,INDEX('Tasas, TRM`
- **E161** ×3 celdas
  - V2-7: `=E$155*$D161`
  - V2-8: `=INDEX($F161:$BM161,MATCH('Nomina Loaded'!$C$3,$F$159:$BM$159,0))/IF(MONTH('Panel de Control General'!$C$10)>='Panel de Control General'!$L$10,INDEX('Tasas, TRM`
- **E189** ×2 celdas
  - V2-7: `=(F$233+E$240)*$D189`
  - V2-8: `=IFERROR(IF('Condiciones Cadena B'!$C85=TRUE,INDEX('Inputs de Nomina'!$AK$129:$AK$140,MATCH($C189,'Inputs de Nomina'!$B$129:$B$140,0)),0),0)*$D189`
- **D150** ×1 celdas
  - V2-7: `=SUMIFS(K$95:K$123,$E$95:$E$123,$C150,$D$95:$D$123,$C$143)+IFERROR(E139,0)`
  - V2-8: `=IF('Panel de Control General'!N17=TRUE,'Panel de Control General'!$N$26,0)`
- **D151** ×1 celdas
  - V2-7: `=SUM(D144:D150)`
  - V2-8: `=IF('Panel de Control General'!N30=TRUE,'Panel de Control General'!$N$40,0)`
- **E167** ×1 celdas
  - V2-7: `=EDATE(D167,1)`
  - V2-8: `=INDEX($F167:$BM167,MATCH('Nomina Loaded'!$C$3,$F$159:$BM$159,0))/IF(MONTH('Panel de Control General'!$C$10)>='Panel de Control General'!$L$10,INDEX('Tasas, TRM`
- **E176** ×1 celdas
  - V2-7: `=SUM(E168:E175)`
  - V2-8: `=INDEX($F176:$BM176,MATCH('Nomina Loaded'!$C$3,$F$170:$BM$170,0))/IF(MONTH('Panel de Control General'!$C$10)>='Panel de Control General'!$L$10,INDEX('Tasas, TRM`

### Costo Variable (motor) — 1 transiciones distintas

- **G125** ×15 celdas
  - V2-7: `=IF('Condiciones Cadena B'!$F$123="Input Calculado",'Vision Cost To Serve'!$C$98,'Condiciones Cadena B'!$G$123)`
  - V2-8: `=IF(ISNUMBER('Condiciones Cadena B'!D124)=TRUE,'Condiciones Cadena B'!D124,0)`

### Costos Totales (motor) — 1 transiciones distintas

- **E10** ×1440 celdas
  - V2-7: `=SUMIFS('Nomina Loaded'!F:F,'Nomina Loaded'!$D:$D,$B10)+SUMIFS('No payroll'!F:F,'No payroll'!$D:$D,$B10)`
  - V2-8: `=IF($B10<>"",SUMIFS('Nomina Loaded'!F:F,'Nomina Loaded'!$D:$D,$B10),0)+IF($B10<>"",SUMIFS('No payroll'!F:F,'No payroll'!$D:$D,$B10),0)`

### Graficos (vista) — 1 transiciones distintas

- **AC5** ×24 celdas
  - V2-7: `=SUM(N5:AB5)`
  - V2-8: `=IF(AC$4<>"",(SUMIFS('Nomina Loaded'!O$43:O$66,'Nomina Loaded'!$B$43:$B$66,$P5)+SUMIFS('Nomina Loaded'!O$155:O$178,'Nomina Loaded'!$B$155:$B$178,$P5)),0)`

### Hoja Maestra Escenarios (motor) — 8 transiciones distintas

- **G11** ×12 celdas
  - V2-7: `='Panel de Control General'!$C$63+SUM(G6:G9)`
  - V2-8: `='Panel de Control General'!$C$63`
- **G13** ×6 celdas
  - V2-7: `=+'Panel de Control General'!$E$63+SUM(G6:G9)`
  - V2-8: `=+'Panel de Control General'!$E$63`
- **G21** ×6 celdas
  - V2-7: `=IFERROR(IF(C10="FTE",G19/C13/'Panel de Control General'!C11,G19/L26/'Panel de Control General'!C11),0)`
  - V2-8: `=IFERROR(IF(C10="FTE",G19/C13,G19/L26),0)`
- **G33** ×5 celdas
  - V2-7: `=IF(C11="Transacción",(SUM(C16,C26,C36)*D11)/G31,(G29+G31)/'Vision Tarifas_Modelo_Cobro'!$C$133)`
  - V2-8: `=IF(C11="Transacción",(SUM(C16,C26,C36)*D11)/G31,(G31)/'Vision Tarifas_Modelo_Cobro'!$C$140)`
- **G71** ×4 celdas
  - V2-7: `=IF(C58="Tiempo",G67/L72/'Panel de Control General'!C11,0)`
  - V2-8: `=IF(C58="Tiempo",G67/L72,0)`
- **G23** ×2 celdas
  - V2-7: `=IFERROR(IF(C10="Tiempo",G19/L24/'Panel de Control General'!C11,0),0)`
  - V2-8: `=IFERROR(IF(C10="Tiempo",G19/L24,0),0)`
- **G226** ×1 celdas
  - V2-7: `=IFERROR(IF(C204="Transacción",(SUM(C209,C219,C229)*D204)/G224,(G222+G224)/'Vision Tarifas_Modelo_Cobro'!$C$133),0)`
  - V2-8: `=IF(C204="Transacción",(SUM(C209,C219,C229)*D204)/G224,(G224)/'Vision Tarifas_Modelo_Cobro'!$C$140)`
- **G273** ×1 celdas
  - V2-7: `=IF(C253="Transacción",G271/IF(G277<>"",(G277*'Panel de Control General'!L52)+SUM('Panel de Control General'!N52:O52),SUM('Panel de Control General'!M52:O52))/'`
  - V2-8: `=IF(C253="Transacción",G271/IF(G277<>"",(G277*'Panel de Control General'!V31)+SUM('Panel de Control General'!X31:Y31),SUM('Panel de Control General'!W31:Y31)),I`

### Inputs de Nomina (motor) — 42 transiciones distintas

- **F60** ×32 celdas
  - V2-7: `=SUM(D60:E60,AJ60)`
  - V2-8: `=SUM(C60:D60)`
- **G60** ×32 celdas
  - V2-7: `=+IF(D60>10*$C$4,D60*$I$13*70%,0)`
  - V2-8: `=+IF(AND(F60<(2*$C$4),F60>0),$C$5,0)`
- **H60** ×32 celdas
  - V2-7: `=+IF((F60-E60)>$C$4*10,(F60-E60)*$J$13*70%,(F60-E60)*$J$13)`
  - V2-8: `=SUM(F60:G60,AL60)`
- **M60** ×32 celdas
  - V2-7: `=+IF($F60>$C$4*10,$F60*O$13*70%,0)`
  - V2-8: `=SUM(H60:L60)`
- **N60** ×32 celdas
  - V2-7: `=SUM(L60:M60)`
  - V2-8: `=+IF((H60-G60)>$C$4*10,(H60-G60)*N$36*70%,(H60-G60)*N$36)`
- **O60** ×32 celdas
  - V2-7: `=+IF($F60>10*$C$4,0,$F60*Q$13)`
  - V2-8: `=+IF($F60>$C$4*10,$F60*O$36*70%,0)`
- **P60** ×32 celdas
  - V2-7: `=+IF($F60>10*$C$4,0,$F60*R$13)`
  - V2-8: `=SUM(N60:O60)`
- **R60** ×32 celdas
  - V2-7: `=+IF((F60-E60)>=$C$4*10,((F60-E60)*70%)*$T$13,(F60-E60)*$T$13)`
  - V2-8: `=+IF($H60>10*$C$4,0,$H60*R$36)`
- **S60** ×32 celdas
  - V2-7: `=SUM(O60:R60)`
  - V2-8: `=$S$36*Q60`
- **T60** ×32 celdas
  - V2-7: `=+IF(AND((D60-E60)<(2*$C$4),D60>0),$C$8,0)`
  - V2-8: `=+IF((H60-G60)>=$C$4*10,((H60-G60)*70%)*$T$36,(H60-G60)*$T$36)`
- **U60** ×32 celdas
  - V2-7: `=+K60+N60+S60+T60`
  - V2-8: `=SUM(Q60:T60)`
- **AB60** ×32 celdas
  - V2-7: `=(A60/220)*AC60*(1+$AD$13)`
  - V2-8: `=(C60/220)*AC60*($AB$36)`
- **AJ60** ×32 celdas
  - V2-7: `=V60+X60+Z60+AB60+AD60+AF60+AH60`
  - V2-8: `=(C60/220)*AK60*(1+$AJ$36)`
- **V61** ×31 celdas
  - V2-7: `=(A61/220)*W61*($X$13)`
  - V2-8: `=+IF(AND((F61-G61)<(2*$C$4),F61>0),$C$8,0)`
- **AK77** ×20 celdas
  - V2-7: `=U77`
  - V2-8: `=IFERROR(INDEX('Condiciones Cadena A'!#REF!,MATCH($B77,'Condiciones Cadena A'!#REF!,0)),0)`
- **C39** ×13 celdas
  - V2-7: `=IFERROR(INDEX('Condiciones Cadena A'!$E$20:$S$20,MATCH($B39,'Condiciones Cadena A'!$E$16:$S$16,0)),0)`
  - V2-8: `=INDEX('Condiciones Cadena A'!$E$44:$E$66,MATCH(B39,'Condiciones Cadena A'!$D$44:$D$66,0))`
- **D39** ×13 celdas
  - V2-7: `=E39*C39*$C$6`
  - V2-8: `=IFERROR(INDEX('Condiciones Cadena A'!$F$44:$F$66,MATCH(B39,'Condiciones Cadena A'!$D$104:$D$127,0)),0)`
- **D60** ×12 celdas
  - V2-7: `=C60`
  - V2-8: `=IFERROR(INDEX('Condiciones Cadena A'!$F$44:$F$66,MATCH(B60,'Condiciones Cadena A'!$D$104:$D$127,0)),0)`
- **AK62** ×10 celdas
  - V2-7: `=U62`
  - V2-8: `=IFERROR(INDEX('Condiciones Cadena A'!$E$15:$S$21,MATCH(AK$38,'Condiciones Cadena A'!$D$15:$D$21,0),MATCH($B62,'Condiciones Cadena A'!$E$8:$S$8,0)),0)`
- **C66** ×6 celdas
  - V2-7: `=2513000*(1+23%)`
  - V2-8: `=IFERROR(INDEX('Condiciones Cadena A'!$E$12:$S$12,MATCH($B66,'Condiciones Cadena A'!$E$8:$S$8,0)),0)`
- **C16** ×1 celdas
  - V2-7: `=18505000*(1+23%)`
  - V2-8: `=4749000*(1+'Tasas, TRM, Polizas'!$B$4)`
- **C17** ×1 celdas
  - V2-7: `=13000000*(1+'Tasas, TRM, Polizas'!$B$4)`
  - V2-8: `=5201000*(1+'Tasas, TRM, Polizas'!$B$4)`
- **C18** ×1 celdas
  - V2-7: `=5260000*(1+'Tasas, TRM, Polizas'!$B$4)`
  - V2-8: `=4119600*(1+'Tasas, TRM, Polizas'!$B$4)`
- **C19** ×1 celdas
  - V2-7: `=2987680*(1+'Tasas, TRM, Polizas'!$B$4)`
  - V2-8: `=2674100*(1+'Tasas, TRM, Polizas'!$B$4)`
- **C20** ×1 celdas
  - V2-7: `=4749000*(1+'Tasas, TRM, Polizas'!$B$4)`
  - V2-8: `=2674100*(1+'Tasas, TRM, Polizas'!$B$4)`
- **C21** ×1 celdas
  - V2-7: `=4749000*(1+'Tasas, TRM, Polizas'!$B$4)`
  - V2-8: `=1612100*(1+23%)`
- **C22** ×1 celdas
  - V2-7: `=5201000*(1+'Tasas, TRM, Polizas'!$B$4)`
  - V2-8: `=2729900*(1+'Tasas, TRM, Polizas'!$B$4)`
- **C23** ×1 celdas
  - V2-7: `=4119600*(1+'Tasas, TRM, Polizas'!$B$4)`
  - V2-8: `=1550074.685248*(1+23%)`
- **C24** ×1 celdas
  - V2-7: `=2674100*(1+'Tasas, TRM, Polizas'!$B$4)`
  - V2-8: `=2729900*(1+'Tasas, TRM, Polizas'!$B$4)`
- **C25** ×1 celdas
  - V2-7: `=2674100*(1+'Tasas, TRM, Polizas'!$B$4)`
  - V2-8: `=1550074.685248*(1+23%)`
- **C26** ×1 celdas
  - V2-7: `=1612100*(1+23%)`
  - V2-8: `=1811500*(1+23%)`
- **C27** ×1 celdas
  - V2-7: `=2729900*(1+'Tasas, TRM, Polizas'!$B$4)`
  - V2-8: `=1673000*(1+23%)`
- **C28** ×1 celdas
  - V2-7: `=1550074.685248*(1+23%)`
  - V2-8: `=1747300*(1+23%)`
- **C29** ×1 celdas
  - V2-7: `=2729900*(1+'Tasas, TRM, Polizas'!$B$4)`
  - V2-8: `=2513000*(1+23%)`
- **C30** ×1 celdas
  - V2-7: `=1550074.685248*(1+23%)`
  - V2-8: `=1423500*(1+23%)`
- **C31** ×1 celdas
  - V2-7: `=1811500*(1+23%)`
  - V2-8: `=1423500*(1+23%)`
- **C32** ×1 celdas
  - V2-7: `=1673000*(1+23%)`
  - V2-8: `=1423500*(1+23%)`
- **C33** ×1 celdas
  - V2-7: `=1747300*(1+23%)`
  - V2-8: `=5134560*(1+'Tasas, TRM, Polizas'!$B$4)`
- **AM39** ×1 celdas
  - V2-7: `=W39`
  - V2-8: `=+W39`
- **C63** ×1 celdas
  - V2-7: `=1811500*(1+23%)`
  - V2-8: `=IFERROR(INDEX('Condiciones Cadena A'!$E$12:$S$12,MATCH($B63,'Condiciones Cadena A'!$E$8:$S$8,0)),0)`
- **C64** ×1 celdas
  - V2-7: `=1673000*(1+23%)`
  - V2-8: `=IFERROR(INDEX('Condiciones Cadena A'!$E$12:$S$12,MATCH($B64,'Condiciones Cadena A'!$E$8:$S$8,0)),0)`
- **C65** ×1 celdas
  - V2-7: `=1747300*(1+23%)`
  - V2-8: `=IFERROR(INDEX('Condiciones Cadena A'!$E$12:$S$12,MATCH($B65,'Condiciones Cadena A'!$E$8:$S$8,0)),0)`

### Listas Desplegables (motor) — 3 transiciones distintas

- **B52** ×59 celdas
  - V2-7: `=A52+1`
  - V2-8: `=IF(B54>=MATCH($B$50,$A$55:$BH$55,0),B54-MATCH($B$50,$A$55:$BH$55,0)+1,"")`
- **B53** ×59 celdas
  - V2-7: `=EDATE(A53,1)`
  - V2-8: `=IF(AND(MONTH($B$50)=MONTH(B$55),YEAR($B$50)=YEAR(B$55)),B$54,0)`
- **B50** ×1 celdas
  - V2-7: `=IF(B52>=MATCH($B$48,$A$53:$BH$53,0),B52-MATCH($B$48,$A$53:$BH$53,0)+1,"")`
  - V2-8: `='Panel de Control General'!$C$10`

### Nomina Loaded (motor) — 24 transiciones distintas

- **F89** ×1186 celdas
  - V2-7: `=SUM(F72:F88)`
  - V2-8: `=IF(AND(F$85>=$C$4,$C$5>=F$85),$E89,0)*(IF(MONTH(F$86)>=$C$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($C$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEAR(F$`
- **G86** ×1000 celdas
  - V2-7: `=IF(AND(G$70>=$C$4,$C$5>=G$70),$E86,0)*(IF(MONTH(G$71)>=$C$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($C$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEAR(G$`
  - V2-8: `=EDATE(F86,1)`
- **F92** ×753 celdas
  - V2-7: `=EDATE(E92,1)`
  - V2-8: `=IF(AND(F$85>=$C$4,$C$5>=F$85),$E92,0)*(IF(MONTH(F$86)>=$C$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($C$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEAR(F$`
- **F81** ×606 celdas
  - V2-7: `=IF(AND(F$70>=$C$4,$C$5>=F$70),$E81,0)*(IF(MONTH(F$71)>=$C$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($C$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEAR(F$`
  - V2-8: `=SUM(F69:F80)`
- **F104** ×128 celdas
  - V2-7: `=EDATE(E104,1)`
  - V2-8: `=SUM(F87:F103)`
- **F169** ×120 celdas
  - V2-7: `=IF(AND(F$70>=$C$4,$C$5>=F$70),$E169,0)*(IF(MONTH(F$71)>=$C$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($C$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEAR(F`
  - V2-8: `=IFERROR(IF($B169=$B$63,INDEX('Inputs de Nomina'!$D$39:$D$76,MATCH(F$42,'Inputs de Nomina'!$B$39:$B$76,0)),INDEX('Inputs de Nomina'!$D$39:$D$76,MATCH($B169,'Inp`
- **D140** ×98 celdas
  - V2-7: `=IFERROR(IF($B140=$B$63,INDEX('Inputs de Nomina'!$D$16:$D$51,MATCH(D$42,'Inputs de Nomina'!$B$16:$B$51,0)),INDEX('Inputs de Nomina'!$D$16:$D$51,MATCH($B140,'Inp`
  - V2-8: `=IF(AND(D$118>=$C$4,$C$5>=D$118),$C140,0)*(IF(MONTH(D$119)>=$C$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($C$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
- **D212** ×34 celdas
  - V2-7: `=IFERROR(INDEX('Condiciones Cadena A'!$E$64:$T$64,MATCH(D211,_xlfn.ANCHORARRAY('Condiciones Cadena A'!$E$63),0)),"")`
  - V2-8: `=IF(AND(D$118>=$C$4,$C$5>=D$118),$C212,0)*(IF(MONTH(D$119)>=$C$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($C$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
- **F228** ×32 celdas
  - V2-7: `=IF(AND(F$215>=$C$4,$C$5>=F$215),$E228,0)*(IF(MONTH(F$216)>=$C$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($C$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
  - V2-8: `=IFERROR(INDEX('Condiciones Cadena A'!$E$139:$T$139,MATCH(F227,'Condiciones Cadena A'!$E$138:$T$138,0)),"")`
- **D379** ×28 celdas
  - V2-7: `=IFERROR(IF(INDEX('Condiciones Cadena A'!$E71:$T71,MATCH(D$378,'Condiciones Cadena A'!$E$63:$T$63,0))=TRUE,$C373*INDEX('Condiciones Cadena A'!$E$17:$S$17,MATCH(`
  - V2-8: `=IF(AND(D$118>=$C$4,$C$5>=D$118),$C379,0)*(IF(MONTH(D$119)>=$C$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($C$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEA`
- **C165** ×15 celdas
  - V2-7: `=SUM(C$140:C$163)`
  - V2-8: `=IFERROR(IF($B165=$B$63,INDEX('Inputs de Nomina'!$D$39:$D$76,MATCH(C$42,'Inputs de Nomina'!$B$39:$B$76,0)),INDEX('Inputs de Nomina'!$D$39:$D$76,MATCH($B165,'Inp`
- **G168** ×11 celdas
  - V2-7: `=EDATE(F168,1)`
  - V2-8: `=IFERROR(IF($B168=$B$63,INDEX('Inputs de Nomina'!$D$39:$D$76,MATCH(G$42,'Inputs de Nomina'!$B$39:$B$76,0)),INDEX('Inputs de Nomina'!$D$39:$D$76,MATCH($B168,'Inp`
- **E169** ×10 celdas
  - V2-7: `=IFERROR(INDEX($C$165:$BE$165,MATCH(D169,_xlfn.ANCHORARRAY($C$139),0)),0)`
  - V2-8: `=IFERROR(IF($B169=$B$63,INDEX('Inputs de Nomina'!$D$39:$D$76,MATCH(E$42,'Inputs de Nomina'!$B$39:$B$76,0)),INDEX('Inputs de Nomina'!$D$39:$D$76,MATCH($B169,'Inp`
- **C120** ×8 celdas
  - V2-7: `=IF(B120<>"",INDEX($C$43:$Q$66,MATCH($B$63,$B$43:$B$66,0),MATCH($B120,$C$42:$Q$42,0)),0)+IF(B120<>"",INDEX($C$140:$Q$163,MATCH($B$159,$B$140:$B$163,0),MATCH($B1`
  - V2-8: `=SUMIFS($E$87:$E$103,$B$87:$B$103,$B$119,$C$87:$C$103,$B120)`
- **E93** ×7 celdas
  - V2-7: `=IF(AND(E$91>=$C$4,$C$5>=E$91),$C93,0)*(IF(MONTH(E$92)>=$C$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($C$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEAR(E$`
  - V2-8: `=IFERROR(INDEX($C$83:$R$83,MATCH(D93,$C$42:$Q$42,0)),0)`
- **C140** ×7 celdas
  - V2-7: `=IFERROR(IF($B140=$B$159,INDEX('Inputs de Nomina'!$D$16:$D$51,MATCH(C$139,'Inputs de Nomina'!$B$16:$B$51,0)),INDEX('Inputs de Nomina'!$D$16:$D$51,MATCH($B140,'I`
  - V2-8: `=IF(B140<>"",INDEX($C$43:$Q$66,MATCH($B$63,$B$43:$B$66,0),MATCH($B140,$C$42:$Q$42,0)),0)+IF(B140<>"",INDEX($C$155:$Q$178,MATCH($B$174,$B$155:$B$178,0),MATCH($B1`
- **E185** ×5 celdas
  - V2-7: `=IF(AND(E$91>=$C$4,$C$5>=E$91),$C185,0)*(IF(MONTH(E$92)>=$C$7,INDEX('Tasas, TRM, Polizas'!$B$8:$G$17,MATCH($C$6,'Tasas, TRM, Polizas'!$A$8:$A$17,0),MATCH(YEAR(E`
  - V2-8: `=IFERROR(INDEX($C$181:$BE$181,MATCH(D185,_xlfn.ANCHORARRAY($C$154),0)),0)`
- **E81** ×2 celdas
  - V2-7: `=IFERROR(INDEX($C$68:$R$68,MATCH(D81,$C$42:$Q$42,0)),0)`
  - V2-8: `=SUM(E69:E80)`
- **C379** ×2 celdas
  - V2-7: `=IFERROR(IF(INDEX('Condiciones Cadena A'!$E71:$T71,MATCH(C$378,'Condiciones Cadena A'!$E$63:$T$63,0))=TRUE,$C373*INDEX('Condiciones Cadena A'!$E$17:$S$17,MATCH(`
  - V2-8: `=SUMIFS($E$345:$E$361,$B$345:$B$361,$B$376,$C$345:$C$361,$B379)`
- **E92** ×1 celdas
  - V2-7: `=EDATE(D92,1)`
  - V2-8: `=IFERROR(INDEX($C$83:$R$83,MATCH(D92,$C$42:$Q$42,0)),0)`
- **E100** ×1 celdas
  - V2-7: `=SUM(E93:E99)`
  - V2-8: `=IFERROR(INDEX($C$83:$R$83,MATCH(D100,$C$42:$Q$42,0)),0)`
- **E189** ×1 celdas
  - V2-7: `=SUM(E182:E188)`
  - V2-8: `=IFERROR(INDEX($C$181:$BE$181,MATCH(D189,_xlfn.ANCHORARRAY($C$154),0)),0)`
- **E193** ×1 celdas
  - V2-7: `=EDATE(D193,1)`
  - V2-8: `=IFERROR(INDEX($C$181:$BE$181,MATCH(D193,_xlfn.ANCHORARRAY($C$154),0)),0)`
- **C212** ×1 celdas
  - V2-7: `=IFERROR(INDEX('Condiciones Cadena A'!$E$64:$T$64,MATCH(C211,_xlfn.ANCHORARRAY('Condiciones Cadena A'!$E$63),0)),"")`
  - V2-8: `=SUMIFS($E$185:$E$194,$B$185:$B$194,$B$209,$C$185:$C$194,$B212)`

### Pólizas - Costo Financiacion (motor) — 5 transiciones distintas

- **E93** ×2280 celdas
  - V2-7: `=IF('Costos Totales'!E$8<=('Panel de Control General'!$C$11+'Nomina Loaded'!$C$3-1),('Costos Totales'!E37+E198+E378)*'Panel de Control General'!$C$35,0)`
  - V2-8: `=IF(E$91<=('Panel de Control General'!$C$11+'Nomina Loaded'!$C$3-1),('Costos Totales'!E37+E198+E378+E223)*'Panel de Control General'!$C$35,0)`
- **E23** ×1860 celdas
  - V2-7: `=IF('Costos Totales'!E$8<=('Panel de Control General'!$C$11+'Nomina Loaded'!$C$3-1),(('Costos Totales'!E48/((1-'Panel de Control General'!$C$63)*(1-'Panel de Co`
  - V2-8: `=IF(E$21<=('Panel de Control General'!$C$11+'Nomina Loaded'!$C$3-1),(('Costos Totales'!E48+E209+E389+E234)/((1-'Panel de Control General'!$C$63)*(1-'Panel de Co`
- **E12** ×420 celdas
  - V2-7: `=IF('Costos Totales'!E$8<=('Panel de Control General'!$C$11+'Nomina Loaded'!$C$3-1),(('Costos Totales'!E37/((1-'Panel de Control General'!$C$63)*(1-'Panel de Co`
  - V2-8: `=IF(E$10<=('Panel de Control General'!$C$11+'Nomina Loaded'!$C$3-1),((('Costos Totales'!E37+E198+E378+E223)/((1-'Panel de Control General'!$C$63)*(1-'Panel de C`
- **E65** ×420 celdas
  - V2-7: `=IFERROR(IF('Costos Totales'!E$8<=('Panel de Control General'!$C$11+'Nomina Loaded'!$C$3-1),(('Costos Totales'!E91/((1-'Panel de Control General'!$E$63)*(1-'Pan`
  - V2-8: `=IFERROR(IF(E$63<=('Panel de Control General'!$C$11+'Nomina Loaded'!$C$3-1),(('Costos Totales'!E91+E308+E438+E333)/((1-'Panel de Control General'!$E$63)*(1-'Pan`
- **E145** ×420 celdas
  - V2-7: `=IFERROR(IF('Costos Totales'!E$8<=('Panel de Control General'!$C$11+'Nomina Loaded'!$C$3-1),('Costos Totales'!E91+E308+E438)*'Panel de Control General'!$C$35,0)`
  - V2-8: `=IFERROR(IF(E$143<=('Panel de Control General'!$C$11+'Nomina Loaded'!$C$3-1),('Costos Totales'!E91+E308+E438+E333)*'Panel de Control General'!$C$35,0),0)`

### Riesgo (motor) — 1 transiciones distintas

- **L11** ×1 celdas
  - V2-7: `=AVERAGE('Condiciones Cadena A'!E65:T65)`
  - V2-8: `='Panel de Control General'!C20`

### Tasas, TRM, Polizas (motor) — 1 transiciones distintas

- **C13** ×5 celdas
  - V2-7: `=B13+(C4*50%+C5*50%)`
  - V2-8: `=IF('Panel de Control General'!$L$6="No",100%,IF(YEAR('Panel de Control General'!$C$10)=C$7,100%,B13+K13))`

### Vision Cost To Serve (vista) — 2 transiciones distintas

- **I159** ×15 celdas
  - V2-7: `=IF(I137<>"",(I139+$I$129+$I$132-I168)/($I$128+$I$131+I153),0)`
  - V2-8: `=SUM(I154:I158,I153)`
- **K38** ×1 celdas
  - V2-7: `=IFERROR(SUM(IF('Panel de Control General'!O17=TRUE,'Costo Cadena C'!D290:BK290,0),IF('Panel de Control General'!O30=TRUE,'Costo Cadena C'!D315:BK315,0))/'Panel`
  - V2-8: `=IFERROR(SUM(IF('Panel de Control General'!O17=TRUE,'Costo Cadena C'!#REF!,0),IF('Panel de Control General'!O30=TRUE,'Costo Cadena C'!#REF!,0))/'Panel de Contro`

### Vision Tarifas_Modelo_Cobro (vista) — 15 transiciones distintas

- **D143** ×5 celdas
  - V2-7: `=IF(C143=0,0,C143+$G$53)`
  - V2-8: `=C143/$C$140`
- **D150** ×5 celdas
  - V2-7: `=IFERROR(((($C$40+$C$50+$C$60)*$D$35)+D77)/C150,0)`
  - V2-8: `=C150/$C$140`
- **D157** ×5 celdas
  - V2-7: `=IFERROR(((($C$40+$C$50+$C$60)*$D$35)+D84)/C157,0)`
  - V2-8: `=IFERROR(D80/C157,0)`
- **G36** ×2 celdas
  - V2-7: `=+'Panel de Control General'!D63+SUM(G30:G33)`
  - V2-8: `=+'Panel de Control General'!D63`
- **D124** ×2 celdas
  - V2-7: `=C121*(1-C124)`
  - V2-8: `=C124/(($C$114/6)*60)`
- **D21** ×1 celdas
  - V2-7: `=IF(D16="Transacción",'Hoja Maestra Escenarios'!G79,IF(OR(D16="Resultados",D16="Honorarios"),'Hoja Maestra Escenarios'!G81,0))`
  - V2-8: `=IFERROR(IF(D16="Transacción",'Hoja Maestra Escenarios'!G79,IF(OR(D16="Resultados",D16="Honorarios"),'Hoja Maestra Escenarios'!G81,0)),0)`
- **G35** ×1 celdas
  - V2-7: `='Panel de Control General'!$C$63+SUM(G30:G33)`
  - V2-8: `='Panel de Control General'!$C$63`
- **G45** ×1 celdas
  - V2-7: `=IFERROR(IF(C34="FTE",G43/C37/12,G43/E126),0)`
  - V2-8: `=IFERROR(IF(C34="FTE",G43/C37,G43/E133),0)`
- **G57** ×1 celdas
  - V2-7: `=IFERROR(IF(C35="Transacción",(SUM(C40,C50,C60)*D35)/G55,(G53+G55)/C133/'Panel de Control General'!$C$11),0)`
  - V2-8: `=IFERROR(IF(C35="Transacción",(SUM(C40,C51,C62)*D35)/G55,(G55)/C140),0)`
- **C121** ×1 celdas
  - V2-7: `=$C$107*$C$109*C37`
  - V2-8: `=((C115/4)/6)*60`
- **D121** ×1 celdas
  - V2-7: `=C121*60`
  - V2-8: `=C121/(($C$114/6)*60)`
- **C125** ×1 celdas
  - V2-7: `='Panel de Control General'!$C$19`
  - V2-8: `=SUM(C120:C124)`
- **C133** ×1 celdas
  - V2-7: `=IF('Panel de Control General'!$C$5="SACO",'Panel de Control General'!$C$124,IF('Panel de Control General'!$C$5="Cobranzas",'Panel de Control General'!$C$155,0)`
  - V2-8: `=SUM(D120:D122)`
- **C137** ×1 celdas
  - V2-7: `=+C78`
  - V2-8: `=IF(OR(C35="Honorarios",C35="Resultados"),"✓ Habilitado","— Deshabilitado")`
- **C140** ×1 celdas
  - V2-7: `=+C81`
  - V2-8: `=IF('Panel de Control General'!$C$5="SACO",'Panel de Control General'!$C$124,IF('Panel de Control General'!$C$5="Cobranzas",'Panel de Control General'!$C$155,0)`

### Visión Imprimible (vista) — 1 transiciones distintas

- **T13** ×1 celdas
  - V2-7: `='Panel de Control General'!L7 & " · " & 'Panel de Control General'!L8`
  - V2-8: `='Panel de Control General'!K7&" · "&'Panel de Control General'!L7 & " · " & 'Panel de Control General'!L9`

### Visión P&G (vista) — 3 transiciones distintas

- **C19** ×180 celdas
  - V2-7: `=IFERROR((C31/(1-'Panel de Control General'!$C$63))*C$15,0)`
  - V2-8: `=IF(AND(C$12>=SUM('Listas Desplegables'!$A$53:$BH$53),C12<=$K$5),'Hoja Maestra Escenarios'!$C$296,0)*C$15*(1+INDEX('Tasas, TRM, Polizas'!$J$8:$O$16,MATCH('Panel`
- **C22** ×180 celdas
  - V2-7: `=C$18*'Panel de Control General'!$C67`
  - V2-8: `=IF(AND(C$12>=SUM('Listas Desplegables'!$A$53:$BH$53),C12<=$K$5),SUMIFS('Hoja Maestra Escenarios'!$D$295:$D$316,'Hoja Maestra Escenarios'!$B$295:$B$316,$B22),0)`
- **C25** ×60 celdas
  - V2-7: `=C$18*'Panel de Control General'!$C70`
  - V2-8: `=IF(AND(C$12>=SUM('Listas Desplegables'!$A$53:$BH$53),C12<=$K$5),-SUMIFS('Hoja Maestra Escenarios'!$D$295:$D$316,'Hoja Maestra Escenarios'!$B$295:$B$316,$B25),0`


## CONSTANT_CHANGED por hoja (literales numéricos)

### Condiciones Cadena A (motor) — 5 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `E9` | 3600 | 130 |
| `E60` | 0.28 | 2057790 |
| `E64` | 10 | 1750905 |
| `F64` | 10 | 0 |
| `E135` | 752 | 0.28 |

### Condiciones Cadena B (motor) — 3 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `H8` | 183 | 250 |
| `C79` | 0 | 3 |
| `D124` | 1000 | 8374.816517707553 |

### Condiciones Cadena C (motor) — 25 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `G9` | 2000000 | 5130.66 |
| `H9` | 30 | 170000 |
| `G29` | 5000 | 117 |
| `H29` | 2 | 190000 |
| `G62` | 10000 | 60 |
| `H62` | 2 | 24 |
| `G63` | 5000 | 143 |
| `H63` | 4 | 12 |
| `G64` | 4000000 | 60 |
| `H64` | 5 | 24 |
| `G65` | 70000000 | 143 |
| `H65` | 10 | 12 |
| `C89` | 3 | 1 |
| `C125` | 0.03 | 0 |
| `C126` | 0.03 | 0 |
| `C127` | 0.03 | 0 |
| `C128` | 0.03 | 0 |
| `C129` | 0.03 | 0 |
| `C139` | 0.1 | 0 |
| `D155` | 200 | 4000 |
| `D156` | 300 | 560 |
| `D157` | 700 | 200 |
| `D158` | 1000 | 300 |
| `C166` | 300000 | 1000000 |
| `C167` | 100000 | 2000 |

### Costo Cadena C (motor) — 73 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `E95` | 200 | 5130.66 |
| `D136` | 13300000 | 22230000 |
| `D190` | 31120000 | 0 |
| `E246` | 0 | 1 |
| `F246` | 0 | 2 |
| `G246` | 0 | 3 |
| `H246` | 0 | 4 |
| `I246` | 0 | 5 |
| `J246` | 0 | 6 |
| `D248` | 0 | 44370.19173587001 |
| `D249` | 0 | 6442713.062500002 |
| `D273` | 0 | 6442713.062500002 |
| `F330` | 2 | 1 |
| `G330` | 3 | 2 |
| `H330` | 4 | 3 |
| `I330` | 5 | 4 |
| `J330` | 6 | 5 |
| `K330` | 7 | 6 |
| `L330` | 8 | 7 |
| `M330` | 9 | 8 |
| `N330` | 10 | 9 |
| `O330` | 11 | 10 |
| `P330` | 12 | 11 |
| `Q330` | 13 | 12 |
| `R330` | 14 | 13 |
| `S330` | 15 | 14 |
| `T330` | 16 | 15 |
| `U330` | 17 | 16 |
| `V330` | 18 | 17 |
| `W330` | 19 | 18 |
| … | _43 más_ | … |

### Costo Fijo (motor) — 138 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `D41` | 0.0625 | 0 |
| `D42` | 0 | 1 |
| `D45` | 0.9375000000000001 | 0 |
| `D54` | 0 | 2500000 |
| `D57` | 2745000 | 0 |
| `D97` | 0 | 1 |
| `E97` | 0 | 44370.19173587001 |
| `D99` | 0 | 1 |
| `E108` | 0 | 1 |
| `F108` | 0 | 2 |
| `G108` | 0 | 3 |
| `H108` | 0 | 4 |
| `I108` | 0 | 5 |
| `J108` | 0 | 6 |
| `D111` | 0 | 6487083.254235872 |
| `D134` | 0 | 6442713.062500002 |
| `D137` | 0.9375000000000001 | 0 |
| `D166` | 1 | 0 |
| `F193` | 1 | 0 |
| `G193` | 2 | 0 |
| `H193` | 3 | 0 |
| `I193` | 4 | 0 |
| `J193` | 5 | 0 |
| `K193` | 6 | 0 |
| `L193` | 7 | 0 |
| `M193` | 8 | 0 |
| `N193` | 9 | 0 |
| `O193` | 10 | 0 |
| `P193` | 11 | 0 |
| `Q193` | 12 | 0 |
| … | _108 más_ | … |

### Costo Variable (motor) — 31 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `D68` | 0.0625 | 0 |
| `D69` | 0 | 1 |
| `D72` | 0.9375000000000001 | 0 |
| `D163` | 0.0625 | 0 |
| `D164` | 0 | 1 |
| `D167` | 0.9375000000000001 | 0 |
| `I229` | 2745000 | 0 |
| `J229` | 2745000 | 2500000 |
| `K229` | 2745000 | 2500000 |
| `L229` | 2745000 | 2500000 |
| `M229` | 2745000 | 2500000 |
| `N229` | 2745000 | 2500000 |
| `O229` | 2745000 | 2500000 |
| `P229` | 2745000 | 2500000 |
| `Q229` | 2745000 | 2500000 |
| `R229` | 2745000 | 2500000 |
| `S229` | 2745000 | 2500000 |
| `T229` | 2745000 | 2500000 |
| `U229` | 0 | 2500000 |
| `V229` | 0 | 2500000 |
| `W229` | 0 | 2500000 |
| `X229` | 0 | 2500000 |
| `Y229` | 0 | 2500000 |
| `Z229` | 0 | 2500000 |
| `AA229` | 0 | 2500000 |
| `AB229` | 0 | 2500000 |
| `AC229` | 0 | 2500000 |
| `AD229` | 0 | 2500000 |
| `AE229` | 0 | 2500000 |
| `AF229` | 0 | 2500000 |
| … | _1 más_ | … |

### Costos Totales (motor) — 73 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `J91` | 2388351900.4211397 | 0 |
| `K91` | 2388351900.4211397 | 897359916.8110665 |
| `L91` | 2388351900.4211397 | 897359916.8110665 |
| `M91` | 2388351900.4211397 | 897359916.8110665 |
| `N91` | 2388351900.4211397 | 897359916.8110665 |
| `O91` | 2388351900.4211397 | 897359916.8110665 |
| `P91` | 2388351900.4211397 | 897359916.8110665 |
| `Q91` | 2388351900.4211397 | 897359916.8110665 |
| `R91` | 2388351900.4211397 | 897359916.8110665 |
| `S91` | 2388351900.4211397 | 897359916.8110665 |
| `T91` | 2388351900.4211397 | 897359916.8110665 |
| `U91` | 2388351900.4211397 | 897359916.8110665 |
| `V91` | 0 | 897359916.8110665 |
| `W91` | 0 | 897359916.8110665 |
| `X91` | 0 | 897359916.8110665 |
| `Y91` | 0 | 897359916.8110665 |
| `Z91` | 0 | 897359916.8110665 |
| `AA91` | 0 | 897359916.8110665 |
| `AB91` | 0 | 897359916.8110665 |
| `AC91` | 0 | 897359916.8110665 |
| `AD91` | 0 | 897359916.8110665 |
| `AE91` | 0 | 897359916.8110665 |
| `AF91` | 0 | 897359916.8110665 |
| `AG91` | 0 | 897359916.8110665 |
| `AH91` | 0 | 897359916.8110665 |
| `K92` | 0 | 6442713.062500002 |
| `L92` | 0 | 6442713.062500002 |
| `M92` | 0 | 6442713.062500002 |
| `N92` | 0 | 6442713.062500002 |
| `O92` | 0 | 6442713.062500002 |
| … | _43 más_ | … |

### Graficos (vista) — 13 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `I4` | 0.29 | 0.16639538606602855 |
| `G6` | 0.246050430724433 | 0.1290963868509044 |
| `G7` | 0.30141898043105164 | 0.17167343287370324 |
| `G8` | 0.3160097800969248 | 0.2687274317268652 |
| `G9` | 0.3366198729738946 | 0.9607696580623769 |
| `Q57` | -32940000 | 75257675658.50368 |
| `R57` | 0 | -30196389528.18749 |
| `S57` | -24000000 | -60946803079.94689 |
| `T57` | -347688589.26 | -380580531.12934923 |
| `U57` | -14837633191.432436 | 0 |
| `V57` | 0 | -23079213325.75493 |
| `W57` | 0 | -632991008.1595488 |
| `X57` | 2073457581.885048 | 0 |

### Hoja Maestra Escenarios (motor) — 59 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `D10` | 0.7 | 0 |
| `D11` | 0.3 | 1 |
| `C17` | 1039554872.6578202 | 608306715.7407951 |
| `C18` | 289917559.96154934 | 90333518.48525381 |
| `C19` | 16909711.32937049 | 9102540.065656664 |
| `C20` | 5350268.274279499 | 2876402.660747506 |
| `C21` | 13621325.806878582 | 14818247.803407187 |
| `C22` | 0 | 5642183.157420497 |
| `G31` | 32285.15207263698 | 7481.639868997668 |
| `C37` | 471078158.65180844 | 25147716.81106655 |
| `C38` | 28189144646.401875 | 872212200 |
| `C39` | 359975980.95932484 | 11541394.57006553 |
| `C40` | 115330169.57867627 | 3693246.2624209686 |
| `C41` | 290005629.50863683 | 18795203.45760779 |
| `C42` | 0 | 7156445.336568255 |
| `C65` | 623732923.5946921 | 213756690.9060841 |
| `C66` | 118148735.97692966 | 22683815.869679496 |
| `C67` | 9436077.346255204 | 3080568.6255026013 |
| `C68` | 2985594.743514535 | 973459.6856588224 |
| `C69` | 7601003.622101831 | 5014933.07789202 |
| `C70` | 0 | 1909481.5610498388 |
| `C75` | 32940000 | 0 |
| `C77` | 472834.87714285724 | 0 |
| `C78` | 132665.3794285714 | 0 |
| `C79` | 380927.5714285714 | 0 |
| `G79` | 3210.398337562283 | 7369.14221074808 |
| `D106` | 1 | 0 |
| `D107` | 0 | 1 |
| `C113` | 623732923.5946921 | 385117243.6676597 |
| `C114` | 118148735.97692966 | 55433118.20202694 |
| … | _29 más_ | … |

### Inputs de Nomina (motor) — 20 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `C77` | 2810479.0999999996 | 1750905 |
| `C79` | 10299800 | 1750905 |
| `C80` | 3000000 | 0 |
| `C81` | 4200000 | 0 |
| `C82` | 30000000 | 0 |
| `C110` | 750 | 0 |
| `C111` | 1200 | 0 |
| `C112` | 800 | 0 |
| `C113` | 400 | 0 |
| `C114` | 1000 | 0 |
| `C115` | 1000 | 0 |
| `C116` | 1000 | 0 |
| `C117` | 165 | 0 |
| `C118` | 300 | 0 |
| `C119` | 300 | 0 |
| `C120` | 120 | 0 |
| `C121` | 55 | 0 |
| `C129` | 50 | 2810479.0999999996 |
| `C130` | 1 | 2810479.0999999996 |
| `C131` | 20 | 10299800 |

### No payroll (motor) — 29 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `C42` | 675000 | 3510000 |
| `D42` | 405000 | 1350000 |
| `E42` | 0 | 2160000 |
| `C43` | 4510000 | 2340000 |
| `D43` | 2706000 | 900000 |
| `E43` | 0 | 1440000 |
| `C44` | 450000 | 3621832.8300000005 |
| `D44` | 270000 | 1275293.2500000005 |
| `E44` | 0 | 2228820.2030769233 |
| `C45` | 637646.6250000002 | 28203500 |
| `D45` | 382587.9750000001 | 0 |
| `E45` | 0 | 17356000 |
| `C46` | 451250 | 2298585.25 |
| `D46` | 270750 | 0 |
| `E46` | 0 | 1414514 |
| `C47` | 604750 | 0 |
| `D47` | 362850 | 0 |
| `C48` | 5231600 | 0 |
| `C49` | 3500 | 0 |
| `C50` | 523450 | 0 |
| `C51` | 1200000 | 0 |
| `C52` | 791700 | 0 |
| `C140` | 1 | 12 |
| `D140` | 95706 | 10000 |
| `C141` | 12 | 1 |
| `D141` | 10000 | 95706 |
| `E228` | 7392230.93206786 | 38789639.102455966 |
| `E229` | 4435338.5592407165 | 14919091.962483063 |
| `E230` | 0 | 23870547.139972903 |

### Nomina Loaded (motor) — 85 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `F70` | 1 | 0 |
| `G70` | 2 | 0 |
| `H70` | 3 | 0 |
| `I70` | 4 | 0 |
| `J70` | 5 | 0 |
| `K70` | 6 | 0 |
| `L70` | 7 | 0 |
| `M70` | 8 | 0 |
| `N70` | 9 | 0 |
| `O70` | 10 | 0 |
| `P70` | 11 | 0 |
| `Q70` | 12 | 0 |
| `E229` | 0 | 80 |
| `E230` | 0 | 7.384615384615385 |
| `E236` | 2 | 801025.641025641 |
| `E247` | 2 | 0 |
| `F264` | 1 | 3 |
| `G264` | 2 | 4 |
| `H264` | 3 | 5 |
| `I264` | 4 | 6 |
| `J264` | 5 | 7 |
| `K264` | 6 | 8 |
| `L264` | 7 | 9 |
| `M264` | 8 | 10 |
| `N264` | 9 | 11 |
| `O264` | 10 | 12 |
| `P264` | 11 | 13 |
| `Q264` | 12 | 14 |
| `R264` | 13 | 15 |
| `S264` | 14 | 16 |
| … | _55 más_ | … |

### Panel de Control General (motor) — 33 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `O9` | 752.8150134048257 | 850 |
| `L10` | 0.0153 | 6 |
| `C11` | 12 | 24 |
| `L19` | 29820.375335120643 | 280500 |
| `M19` | 25 | 130 |
| `N19` | 1000 | 0 |
| `O19` | 10000 | 170000 |
| `P19` | 0.6311246965746651 | 0.3939393939393939 |
| `Q19` | 0.033534118493212264 | 0 |
| `R19` | 0.3353411849321226 | 0.6060606060606061 |
| `L20` | 0 | 168000 |
| `M20` | 0 | 80 |
| `N20` | 0 | 100000 |
| `P20` | 0 | 0.40476190476190477 |
| `Q20` | 0 | 0.5952380952380952 |
| `L23` | 26292.225201072382 | 42500 |
| `M23` | 15 | 50 |
| `P23` | 0.42948914040991126 | 1 |
| `Q23` | 0.5705108595900888 | 0 |
| `C28` | 0.6 | 1 |
| `O32` | 0 | 10000 |
| `E40` | 0.1 | 0.2 |
| `E42` | 0.4 | 0.1 |
| `E44` | 0.4 | 0.1 |
| `D68` | 0.04 | 0.01 |
| `E68` | 0.07 | 0.03 |
| `D85` | 0.3 | 1 |
| `D159` | 0.5782983970406905 | 0.6103575832305795 |
| `J169` | 6 | 8 |
| `K169` | 7 | 9 |
| … | _3 más_ | … |

### Pólizas - Costo Financiacion (motor) — 486 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `G173` | 20 | 30 |
| `E174` | 0.1 | 0.2 |
| `G174` | 41 | 30 |
| `G175` | 20 | 30 |
| `G176` | 17 | 30 |
| `G177` | 17 | 30 |
| `G178` | 17 | 30 |
| `G179` | 17 | 30 |
| `G180` | 17 | 30 |
| `G181` | 17 | 30 |
| `G182` | 17 | 30 |
| `G183` | 17 | 30 |
| `G184` | 17 | 30 |
| `G185` | 17 | 30 |
| `G188` | 17 | 30 |
| `J198` | 676646.0900103067 | 0 |
| `K198` | 674362.7145904517 | 5642183.1574204955 |
| `L198` | 674362.7145904517 | 5642183.1574204955 |
| `M198` | 674362.7145904517 | 5642183.1574204955 |
| `N198` | 674362.7145904517 | 5642183.1574204955 |
| `O198` | 674362.7145904517 | 5642183.1574204955 |
| `P198` | 674362.7145904517 | 5642183.1574204955 |
| `Q198` | 674362.7145904517 | 5642183.1574204955 |
| `R198` | 674362.7145904517 | 5642183.1574204955 |
| `S198` | 674362.7145904517 | 5642183.1574204955 |
| `T198` | 674362.7145904517 | 5642183.1574204955 |
| `U198` | 674362.7145904517 | 5642183.1574204955 |
| `V198` | 674362.7145904517 | 5642183.1574204955 |
| `W198` | 674362.7145904517 | 5642183.1574204955 |
| `X198` | 674362.7145904517 | 5642183.1574204955 |
| … | _456 más_ | … |

### Riesgo (motor) — 4 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `N4` | 3 | 1 |
| `N10` | 1 | 2 |
| `E16` | 1.8999999999999997 | 2.1 |
| `E17` | 2.1 | 1.6 |

### Rot, Ausent y Rentabilidad (motor) — 2 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `B52` | 25796.9891200828 | 30284.6590649943 |
| `C52` | 29859.23707 | 33011.52272727273 |

### Vision Cost To Serve (vista) — 48 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `C64` | 26292.225201072382 | 280500 |
| `E64` | 4121564.7753978986 | 5374155.647892685 |
| `C65` | 0 | 168000 |
| `C68` | 29820.375335120643 | 42500 |
| `E68` | 4431574.775397899 | 4728810.135515272 |
| `C95` | 0.42948914040991126 | 0.3939393939393939 |
| `J95` | 0.5705108595900888 | 0 |
| `P95` | 0 | 0.6060606060606061 |
| `P99` | 0 | 5130.66 |
| `J100` | 183 | 0 |
| `C101` | 3288748.491163134 | 3963124.618464324 |
| `P101` | 0 | 130.76470588235296 |
| `C102` | 122563.34999999998 | 666717.4930069927 |
| `C103` | 16666.666666666668 | 10012.820512820517 |
| `P103` | 0 | 16.902038937239258 |
| `C104` | 17000.000000000004 | 19585.076923076922 |
| `C105` | 11796.40102960103 | 10658.296791208792 |
| `C107` | 8408 | 9184.123076923077 |
| `C110` | 293145.86500000005 | 307491.67753846163 |
| `C111` | 67546.76425578346 | 88999.70232921427 |
| `C112` | 295689.2372827144 | 298381.8392496613 |
| `I140` | 82218712.2790783 | 515206200.4003619 |
| `J140` | 49331227.36744701 | 179038684.54677695 |
| `K140` | 0 | 328871620.2458548 |
| `I141` | 3064083.75 | 86673274.09090906 |
| `J141` | 1838450.2499999998 | 32462420.454545457 |
| `K141` | 0 | 52303553.28671328 |
| `I142` | 416666.6666666667 | 1301666.6666666672 |
| `J142` | 250000 | 458333.33333333343 |
| `K142` | 0 | 801025.6410256405 |
| … | _18 más_ | … |

### Vision Tarifas_Modelo_Cobro (vista) — 31 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `C15` | 0.7 | 0 |
| `E15` | 1 | 0 |
| `C17` | 0.3 | 1 |
| `E17` | 0 | 1 |
| `H17` | 0.5 | 1 |
| `D34` | 0.7 | 0 |
| `D35` | 0.3 | 1 |
| `C41` | 1039554872.6578202 | 608306715.7407951 |
| `C42` | 289917559.96154934 | 90333518.48525381 |
| `C43` | 16909711.32937049 | 9102540.065656664 |
| `C44` | 5350268.274279499 | 2876402.660747506 |
| `C45` | 13621325.806878582 | 14818247.803407187 |
| `C46` | 0 | 5642183.157420497 |
| `C63` | 359975980.95932484 | 25147716.81106655 |
| `C64` | 115330169.57867627 | 872212200 |
| `C65` | 0 | 11541394.57006553 |
| `C66` | 0 | 3693246.2624209686 |
| `B80` | 4 | 1 |
| `B81` | 5 | 2 |
| `B82` | 6 | 3 |
| `B83` | 7 | 4 |
| `B84` | 8 | 5 |
| `B85` | 9 | 6 |
| `B86` | 10 | 7 |
| `B87` | 11 | 8 |
| `B88` | 12 | 9 |
| `C115` | 5 | 8 |
| `C116` | 5 | 4.33 |
| `C124` | 0 | 5 |
| `H143` | 5 | 1 |
| … | _1 más_ | … |

### Visión P&G (vista) — 495 constantes

| Celda | V2-7 | V2-8 |
|-------|------|------|
| `H34` | 131549939.64652532 | 0 |
| `I34` | 131549939.64652532 | 1023116505.1929936 |
| `J34` | 131549939.64652532 | 1023116505.1929936 |
| `K34` | 131549939.64652532 | 1023116505.1929936 |
| `L34` | 131549939.64652532 | 1023116505.1929936 |
| `M34` | 131549939.64652532 | 1023116505.1929936 |
| `N34` | 131549939.64652532 | 1023116505.1929936 |
| `O34` | 131549939.64652532 | 1079876236.2553718 |
| `P34` | 131549939.64652532 | 1079876236.2553718 |
| `Q34` | 131549939.64652532 | 1079876236.2553718 |
| `R34` | 131549939.64652532 | 1079876236.2553718 |
| `S34` | 131549939.64652532 | 1079876236.2553718 |
| `T34` | 0 | 1079876236.2553718 |
| `U34` | 0 | 1079876236.2553718 |
| `V34` | 0 | 1079876236.2553718 |
| `W34` | 0 | 1079876236.2553718 |
| `X34` | 0 | 1079876236.2553718 |
| `Y34` | 0 | 1079876236.2553718 |
| `Z34` | 0 | 1079876236.2553718 |
| `AA34` | 0 | 1082867474.082359 |
| `AB34` | 0 | 1082867474.082359 |
| `AC34` | 0 | 1082867474.082359 |
| `AD34` | 0 | 1082867474.082359 |
| `AE34` | 0 | 1082867474.082359 |
| `AF34` | 0 | 1082867474.082359 |
| `H35` | 4902534 | 0 |
| `I35` | 4902534 | 171439247.8321678 |
| `J35` | 4902534 | 171439247.8321678 |
| `K35` | 4902534 | 171439247.8321678 |
| `L35` | 4902534 | 171439247.8321678 |
| … | _465 más_ | … |

