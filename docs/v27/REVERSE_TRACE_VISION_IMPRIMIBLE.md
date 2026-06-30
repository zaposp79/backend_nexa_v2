# Reverse-Trace Visión Imprimible (F2)

> Consolidación desde evidencia capturada (extracción inicial de la hoja + auditorías por hoja).
> Cada celda calculada de `Visión Imprimible` trazada hacia atrás hasta input del Panel / constante.
> **Sin nueva extracción.** Donde la cadena llega a un cálculo ya auditado en otra hoja, se referencia
> el doc correspondiente en lugar de re-expandir. "no documentado" = no presente en evidencia capturada.

Convención: `→` = "depende de / referencia a". Origen final en **negrita** (input / constante / cálculo-hoja).

## 00 · Cabecera / Banner
| Celda VI | Fórmula | Cadena de trazabilidad |
|----------|---------|------------------------|
| O3 | `=IF(Panel!C7="Cliente Nuevo",Panel!D6,Panel!C6)` | → Panel!C7 (`=IF(C6="CLIENTE NUEVO",…)` → **Panel!C6 input**) ; Panel!D6/C6 **input** |
| O4 | `="Servicio: "&Panel!C5&" · "&Panel!C12` | → **Panel!C5 input** (servicio) ; **Panel!C12 input** (ciudad) |
| S7 | `=IF(IF(M91=…)+IF(M92=…)+IF(M93=…)<1,"No requiere…","El deal requiere…")` | → VI!M91/M92/M93 (ver §06) → **self (lógica de conteo)** |

## 01 · Ficha del Deal
| Celda VI | Fórmula | Cadena de trazabilidad |
|----------|---------|------------------------|
| B11 | `=IF(Panel!C7="Cliente Nuevo",Panel!D6,Panel!C6)` | → **Panel!C6/D6/C7 input** |
| H11 | `=Panel!C5` | → **Panel!C5 input** |
| N11 | `=Panel!C12&" · "&Panel!C13` | → **Panel!C12/C13 input** |
| T11 | `=Panel!C8&" · "&Panel!C7` | → **Panel!C8 input** ; Panel!C7 (deriva de C6) |
| B13 | `=Panel!C10` | → **Panel!C10 input** (fecha) |
| H13 | `=Panel!C11&" meses"` | → **Panel!C11 input** |
| N13 | `=Panel!C9&" días"` | → **Panel!C9 input** (=30) |
| T13 | `=Panel!L7&" · "&Panel!L8` | → **Panel!L7/L8 input** (indexación) |

## 02 · Economics
| Celda VI | Fórmula | Cadena de trazabilidad |
|----------|---------|------------------------|
| B19 | `=IFERROR(Tarifas!C72,0)` | → Tarifas!C72 (`=C47+C57+C67`) → C47 (`=C40/factor`) → C40 (`=SUM(C41:C46)`) → SUMPRODUCT(**Nomina Loaded** 15-33, **No payroll** 14-32, **Pólizas** subset) × filtros canal/modalidad ← **Panel!M/S/K matrices** ; factor ← Panel!C63/C67-C70. Detalle: `FORMULA_REGISTRY_CADENA_A.md` |
| B20 | `=Tarifas!C29` | → **Tarifas!C29 input** (dropdown escenario) |
| H19 | `=P&G!BK30/E6` | → P&G!BK30 (`=SUM(BK31+BK45+BK55+BK65)`) → P&G filas 31/45/55/65 → **Costos Totales / Nomina / Cadena B-C / Pólizas** ; E6=`Panel!C11`. **GAP-PYG-01** (BK30 incluye financiero) |
| N19 | `=Panel!C63` | → Panel!C63 (`=FILTER(Rot!B29:B34, Rot!A29:A34=Panel!C5)`) → **Rot/Ausent!B29:B34 input** (margen por servicio) |
| N20 | `=IFS(N19<M101,…,N19>Q101,…,TRUE,…)` | → VI!N19 ; VI!M101/Q101 (=Panel!D63/E63) → **self (lógica estado)**. **GAP-IMP-03** |
| T19 | `=CTS!C200` | → CTS!C200 (`=(C186+D192+D193+D194+D195)-D196`) → C186 (`=SUM(P&G!C31:BJ31,C45:BJ45,C55:BJ55)`) + D19x (`=C186×Panel!C63:C70`). Detalle: `VISION_COST_TO_SERVE` audit |
| T20 | `="Acumulado en "&Panel!C11&" meses"` | → **Panel!C11 input** |

## 03 · Configuración Comercial
| Celda VI | Fórmula | Cadena de trazabilidad |
|----------|---------|------------------------|
| B36 | `=IFERROR(Tarifas!C33,"-")` | → Tarifas!C33 (`=FILTER(Panel!C81:C113,…)`) → **Panel!C81:C113 input** (escenarios) |
| I36 | `=IFERROR(Tarifas!C34&" ("&TEXT(Tarifas!D34,"0%")&")","-")` | → **Tarifas!C34/D34** ← FILTER Panel escenarios |
| P36 | `=IFERROR(Tarifas!C35&" ("&TEXT(Tarifas!D35,"0%")&")","-")` | → **Tarifas!C35/D35** ← FILTER Panel |
| B38 | `=Tarifas!G47` | → Tarifas!G47 (`=IF(C34="Tiempo",G43/E124,0)`) → G43 (`=C72×D34`). **=0 para FTE; real es G45** (GAP-TAR-03) |
| D38 | `=Tarifas!G55` | → Tarifas!G55 (`=CHOOSE(MATCH(C29,…),HME!G31,…G273)`) → **Hoja Maestra Escenarios!G31** (por escenario) |
| I38 | `=Panel!C70` | → **Panel!C70 input** (descuento=0) |
| N38 | `=Panel!L52` | → **Panel!L52** (volumen base) — *no documentado: fórmula de L52 no extraída* |
| T38 | `=Panel!C63` | → Rot!B29:B34 (igual que N19) |

## 04 · Análisis Gráfico (charts)
| Gráfico | Fuente | Trazabilidad |
|---------|--------|--------------|
| Waterfall (chartEx1) | `Graficos!N56:X56` / `N57:X57` (named `_xlchart.v1.0/v1.1`) | → Graficos ← promedios P&G. `waterfall_promedio` backend |
| Evolución (chart1) | `Graficos!M46:BT47`, `O43:O44` | → Graficos ← P&G mensual (`pyg_por_mes`) |
| Comparación Márgenes (chart2) | `VI!N19:S19`, `Graficos!I4/I5/G6:G9` | → VI!N19 (margen) + Graficos histórico (sin backend) |

## 05 · Comparativo de Escenarios (filas 74-78, offset +7)
| Col | Fórmula (Esc1) | Trazabilidad |
|-----|----------------|--------------|
| B74 | `=Panel!B80` | → **Panel!B80 input** (label escenario) |
| F74 | `=Panel!C83` | → **Panel!C83 input** (modelo) |
| D74 | `=CONCAT(IF(Panel!C81<>"",C81),"-",IF(C82<>"",C82))` | → **Panel!C81/C82 input** |
| I74/M74 | `=IFERROR(Panel!C84&"("&TEXT(D84)&")")` / `…C85/D85` | → **Panel!C84/D84, C85/D85 input** |
| Q74/T74 | `=Tarifas!C20` / `=Tarifas!C21` | → Tarifas!C20 (`=HME!G21`) / C21 (`=IF(C16="Transacción",HME!G31,…)`) → **HME** (offset +48/escenario) |
| W74 | `=IF(B74=Tarifas!C29,"★ SELECCIONADO","Alternativa")` | → VI!B74 ; **Tarifas!C29 input** |

## 06 · Control y Aprobación
| Celda VI | Fórmula | Trazabilidad |
|----------|---------|--------------|
| B87 | `=Riesgo!E17` | → **Riesgo!E17** (score cliente) ← criterios E3:E12 (RiesgoCalculator) |
| B90 | `=Riesgo!E16` | → **Riesgo!E16** (score operativo) |
| B92 | `=Riesgo!E18` | → Riesgo!E18 (`=E17×0,4+E16×0,6`) → **self** (verificado 2,1×0,4+1,9×0,6=1,98) |
| H87 | `=CTS!C200/Panel!C9` | → CTS!C200 (ver T19) ÷ **Panel!C9 input** |
| M91/M92 | `=IF(H87>=100000000/200000000,"✓ Requerida","—")` | → VI!H87 → **self (umbral literal)**. **GAP-IMP-04** |
| M93 | `=IF(CTS!C200>=1000000000,…)` | → CTS!C200 → **self (umbral 1,0 B fijo)** |
| P86:P95 / U / W | `=IFERROR(Riesgo!E3:E12,"-")` / `D3:D12` / `N3:N12` | → **Riesgo!E3:E12, D3:D12, N3:N12** (10 criterios) ← RiesgoCalculator |

## 07 · Contingencias (filas 101-105)
| Concepto | APLICADO / MÍN / MÁX | Trazabilidad |
|----------|----------------------|--------------|
| Margen objetivo (101) | `Panel!C63/D63/E63` | → C63 (Rot!B29:B34) ; **D63/E63 input** |
| Cont. Operativa (102) | `Panel!C67/D67/E67` | → **Panel!C67-E67 input** |
| Cont. Comercial (103) | `Panel!C68/D68/E68` | → **Panel input** |
| Markup (104) | `Panel!C69/D69/E69` | → **Panel input** |
| Descuento (105) | `Panel!C70/D70/E70` | → **Panel input** |
| ESTADO (U101:U105) | `=IF(C<D,"⚠ Bajo",IF(C>E,"⚠ Excede","✓ Dentro"))` | → self (comparación) |

## 08 · Aprobaciones (firmas)
| Celda | Tipo | Trazabilidad |
|-------|------|--------------|
| B110, I110, Q110, H114, P114 | **input libre** (vacío) | sin origen (captura UI). **GAP-IMP-07** |

## Resumen de orígenes finales
- **Inputs Panel**: C5-C13, C63(→Rot), C67-C70/C73, C81:C113, L7/L8/L52, M/S/K matrices.
- **Constantes/lógica self**: S7, N20, M91-M93, W74-78, U101-105.
- **Cálculo en otra hoja (referenciado, no re-expandido)**: Tarifas (B19/B36/B38/D38/escenarios), P&G (H19), CTS (T19/H87), Riesgo (scores/criterios).
- **No documentado**: fórmula de `Panel!L52` (volumen base) no extraída; tabla destino de indexación `INDEX('Ta…')` no extraída.
