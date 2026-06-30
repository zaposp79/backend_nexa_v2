# Triage de transiciones de fórmula V2-8 (Stage 2 prep)

Clasificación heurística de las transiciones distintas para separar
lógica de negocio real de reubicación de layout, ordenadas por celdas
afectadas. La columna *Backend probable* es un hint a afinar al mapear.

## Distribución por etiqueta

| Etiqueta | Transiciones | Lectura |
|----------|-------------:|---------|
| NEW_FUNCTION | 106 | V2-8 agrega lógica (guard/lookup/indexación) — **revisar** |
| DROPPED_FUNCTION | 26 | V2-8 quita lógica — **revisar** |
| CONSTANT_IN_FORMULA | 26 | cambió literal embebido — **revisar (posible parámetro)** |
| LIKELY_LAYOUT_REORG | 3 | bloque reubicado — validar numéricamente, no por fórmula |
| TRIVIAL_REWRITE | 16 | mismas funciones/operadores — bajo riesgo |

## Por hoja (top transiciones)

### Condiciones Cadena A (motor)
_Backend probable:_ modules/cadena_a/

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| NEW_FUNCTION | 65 | `G84` | +OR  |
| DROPPED_FUNCTION | 15 | `E29` |  −AND,INDEX,MATCH |
| NEW_FUNCTION | 13 | `G87` | +IF,OR  |
| NEW_FUNCTION | 1 | `G95` | +IF,OR −SUM |
| NEW_FUNCTION | 1 | `E120` | +AND,IF,INDEX,MATCH  |

### Condiciones Cadena C (motor)
_Backend probable:_ modules/cadena_c/

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| NEW_FUNCTION | 22 | `J62` | +IFERROR −IF |

### Costo Cadena C (motor)
_Backend probable:_ modules/cadena_c/reglas.py + calculator_motor formulas

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| NEW_FUNCTION | 899 | `E273` | +AND,IF,INDEX,MATCH,MONTH,YEAR  |
| TRIVIAL_REWRITE | 580 | `H366` |   |
| NEW_FUNCTION | 378 | `K248` | +INDEX,MATCH,MONTH,YEAR −IFERROR |
| DROPPED_FUNCTION | 290 | `F307` |  −IFERROR,SUMIFS |
| DROPPED_FUNCTION | 290 | `H403` |  −AND,IF,INDEX,MATCH,MONTH,YEAR |
| NEW_FUNCTION | 177 | `F272` | +EDATE  |
| LIKELY_LAYOUT_REORG | 120 | `E298` |   |
| NEW_FUNCTION | 118 | `F332` | +AND,IF,INDEX,MATCH,MONTH,YEAR  |
| NEW_FUNCTION | 118 | `G338` | +AND,IF,INDEX,MATCH,MONTH,YEAR −EDATE |
| DROPPED_FUNCTION | 117 | `F380` |  −SUM |
| NEW_FUNCTION | 116 | `G315` | +EDATE −SUM |
| NEW_FUNCTION | 116 | `H402` | +EDATE −AND,IF,INDEX,MATCH,MONTH,YEAR |
| … | | _29 transiciones más_ | |

### Costo Fijo (motor)
_Backend probable:_ modules/calculator_motor/formulas/no_payroll/

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| NEW_FUNCTION | 378 | `K110` | +INDEX,MATCH,MONTH,YEAR  |
| NEW_FUNCTION | 360 | `E134` | +AND,IF,IFERROR,INDEX,MATCH,MONTH,YEAR  |
| DROPPED_FUNCTION | 232 | `F172` |  −IFERROR,SUMIFS |
| NEW_FUNCTION | 120 | `E157` | +SUM  |
| NEW_FUNCTION | 117 | `F133` | +EDATE  |
| NEW_FUNCTION | 70 | `F189` | +AND,IF,INDEX,MATCH,MONTH,YEAR  |
| DROPPED_FUNCTION | 60 | `E155` |  −SUMIFS |
| LIKELY_LAYOUT_REORG | 60 | `E156` |   |
| NEW_FUNCTION | 59 | `F188` | +AND,IF,INDEX,MATCH,MONTH,YEAR −EDATE |
| DROPPED_FUNCTION | 58 | `F167` |  −EDATE |
| NEW_FUNCTION | 58 | `F168` | +SUM −IFERROR,SUMIFS |
| DROPPED_FUNCTION | 58 | `F176` |  −SUM |
| … | | _10 transiciones más_ | |

### Costo Variable (motor)
_Backend probable:_ modules/cadena_b/reglas.py

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| NEW_FUNCTION | 15 | `G125` | +ISNUMBER  |

### Costos Totales (motor)
_Backend probable:_ modules/pyg/services/costos_totales_calculator.py

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| NEW_FUNCTION | 1440 | `E10` | +IF  |

### Graficos (vista)
_Backend probable:_ modules/<vision>/ (datos de gráfico embebidos en domain models)

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| NEW_FUNCTION | 24 | `AC5` | +IF,SUMIFS −SUM |

### Hoja Maestra Escenarios (motor)
_Backend probable:_ modules/panel/ escenarios_comerciales + config operaciones.yaml

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| DROPPED_FUNCTION | 12 | `G11` |  −SUM |
| DROPPED_FUNCTION | 6 | `G13` |  −SUM |
| TRIVIAL_REWRITE | 6 | `G21` |   |
| TRIVIAL_REWRITE | 5 | `G33` |   |
| TRIVIAL_REWRITE | 4 | `G71` |   |
| TRIVIAL_REWRITE | 2 | `G23` |   |
| DROPPED_FUNCTION | 1 | `G226` |  −IFERROR |
| TRIVIAL_REWRITE | 1 | `G273` |   |

### Inputs de Nomina (motor)
_Backend probable:_ modules/cadena_a/ (staffing/payroll) + parametrización

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| TRIVIAL_REWRITE | 32 | `F60` |   |
| NEW_FUNCTION | 32 | `G60` | +AND  |
| NEW_FUNCTION | 32 | `H60` | +SUM −IF |
| NEW_FUNCTION | 32 | `M60` | +SUM −IF |
| NEW_FUNCTION | 32 | `N60` | +IF −SUM |
| CONSTANT_IN_FORMULA | 32 | `O60` |   |
| NEW_FUNCTION | 32 | `P60` | +SUM −IF |
| CONSTANT_IN_FORMULA | 32 | `R60` |   |
| DROPPED_FUNCTION | 32 | `S60` |  −SUM |
| DROPPED_FUNCTION | 32 | `T60` |  −AND |
| NEW_FUNCTION | 32 | `U60` | +SUM  |
| CONSTANT_IN_FORMULA | 32 | `AB60` |   |
| … | | _30 transiciones más_ | |

### Listas Desplegables (motor)
_Backend probable:_ parametrización / catálogos

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| NEW_FUNCTION | 59 | `B52` | +IF,MATCH  |
| NEW_FUNCTION | 59 | `B53` | +AND,IF,MONTH,YEAR −EDATE |
| DROPPED_FUNCTION | 1 | `B50` |  −IF,MATCH |

### Nomina Loaded (motor)
_Backend probable:_ modules/calculator_motor/formulas/payroll/ + cadena_a

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| NEW_FUNCTION | 1186 | `F89` | +AND,IF,INDEX,MATCH,MONTH,YEAR −SUM |
| NEW_FUNCTION | 1000 | `G86` | +EDATE −AND,IF,INDEX,MATCH,MONTH,YEAR |
| NEW_FUNCTION | 753 | `F92` | +AND,IF,INDEX,MATCH,MONTH,YEAR −EDATE |
| NEW_FUNCTION | 606 | `F81` | +SUM −AND,IF,INDEX,MATCH,MONTH,YEAR |
| NEW_FUNCTION | 128 | `F104` | +SUM −EDATE |
| NEW_FUNCTION | 120 | `F169` | +IFERROR −AND,MONTH,YEAR |
| NEW_FUNCTION | 98 | `D140` | +AND,MONTH,YEAR −IFERROR |
| NEW_FUNCTION | 34 | `D212` | +AND,IF,MONTH,YEAR −ANCHORARRAY,IFERROR |
| NEW_FUNCTION | 32 | `F228` | +IFERROR −AND,IF,MONTH,YEAR |
| NEW_FUNCTION | 28 | `D379` | +AND,MONTH,YEAR −IFERROR |
| NEW_FUNCTION | 15 | `C165` | +IF,IFERROR,INDEX,MATCH −SUM |
| NEW_FUNCTION | 11 | `G168` | +IF,IFERROR,INDEX,MATCH −EDATE |
| … | | _12 transiciones más_ | |

### Pólizas - Costo Financiacion (motor)
_Backend probable:_ modules/calculator_motor/formulas/costos_financieros/

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| TRIVIAL_REWRITE | 2280 | `E93` |   |
| TRIVIAL_REWRITE | 1860 | `E23` |   |
| TRIVIAL_REWRITE | 420 | `E12` |   |
| TRIVIAL_REWRITE | 420 | `E65` |   |
| TRIVIAL_REWRITE | 420 | `E145` |   |

### Riesgo (motor)
_Backend probable:_ modules/calculator_motor/formulas/risk/ + config/business_rules/riesgo.yaml

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| DROPPED_FUNCTION | 1 | `L11` |  −AVERAGE |

### Tasas, TRM, Polizas (motor)
_Backend probable:_ parametrización + costos_financieros

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| NEW_FUNCTION | 5 | `C13` | +IF,YEAR  |

### Vision Cost To Serve (vista)
_Backend probable:_ modules/vision_cost_to_serve/services/cost_to_serve_calculator.py

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| NEW_FUNCTION | 15 | `I159` | +SUM −IF |
| TRIVIAL_REWRITE | 1 | `K38` |   |

### Vision Tarifas_Modelo_Cobro (vista)
_Backend probable:_ modules/vision_tarifas/reglas.py + dto

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| DROPPED_FUNCTION | 5 | `D143` |  −IF |
| DROPPED_FUNCTION | 5 | `D150` |  −IFERROR |
| TRIVIAL_REWRITE | 5 | `D157` |   |
| DROPPED_FUNCTION | 2 | `G36` |  −SUM |
| CONSTANT_IN_FORMULA | 2 | `D124` |   |
| NEW_FUNCTION | 1 | `D21` | +IFERROR  |
| DROPPED_FUNCTION | 1 | `G35` |  −SUM |
| CONSTANT_IN_FORMULA | 1 | `G45` |   |
| TRIVIAL_REWRITE | 1 | `G57` |   |
| CONSTANT_IN_FORMULA | 1 | `C121` |   |
| CONSTANT_IN_FORMULA | 1 | `D121` |   |
| NEW_FUNCTION | 1 | `C125` | +SUM  |
| … | | _3 transiciones más_ | |

### Visión Imprimible (vista)
_Backend probable:_ modules/vision_imprimible/builders/

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| TRIVIAL_REWRITE | 1 | `T13` |   |

### Visión P&G (vista)
_Backend probable:_ modules/pyg/ (builders/vision_pyg_builder.py) + motor pyg/services

| Etiqueta | Celdas | Ejemplo | Funcs +/− |
|----------|-------:|---------|-----------|
| NEW_FUNCTION | 180 | `C19` | +AND,IF,INDEX,MATCH,SUM,YEAR −IFERROR |
| NEW_FUNCTION | 180 | `C22` | +AND,IF,SUM,SUMIFS  |
| NEW_FUNCTION | 60 | `C25` | +AND,IF,SUM,SUMIFS  |

